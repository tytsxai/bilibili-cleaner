const app = {
    // 安全警告: SESSDATA 和 bili_jct 存储在 localStorage 中
    // 生产环境建议使用 HttpOnly Cookie 或后端 session 管理
    state: {
        qrcodeKey: null,
        pollInterval: null,
        user: {
            mid: null,
            sessdata: null,
            bili_jct: null
        },
        isProcessing: false
    },

    init: function() {
        this.loadUserFromStorage();
        if (this.state.user.sessdata && this.state.user.mid) {
            this.showDashboard();
        } else {
            this.initLogin();
        }

        // Bind refresh event for expired QR code
        document.getElementById('qrcode-expired').addEventListener('click', () => {
            this.initLogin();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });
    },

    loadUserFromStorage: function() {
        const stored = localStorage.getItem('bili_cleaner_user');
        if (stored) {
            try {
                this.state.user = JSON.parse(stored);
            } catch (e) {
                console.error('Failed to parse user data');
                localStorage.removeItem('bili_cleaner_user');
            }
        }
    },

    saveUserToStorage: function() {
        localStorage.setItem('bili_cleaner_user', JSON.stringify(this.state.user));
    },

    logout: function() {
        this.state.user = { mid: null, sessdata: null, bili_jct: null };
        localStorage.removeItem('bili_cleaner_user');
        this.stopPolling();
        this.switchView('login-view');
        this.initLogin();
        this.log('已退出登录', 'info');
    },

    switchView: function(viewId) {
        document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
        document.getElementById(viewId).classList.remove('hidden');
    },

    // --- Authentication ---

    initLogin: async function() {
        this.stopPolling();
        const img = document.getElementById('qrcode-img');
        const loading = document.getElementById('qrcode-loading');
        const expired = document.getElementById('qrcode-expired');
        const status = document.getElementById('login-status');

        img.classList.add('hidden');
        expired.classList.add('hidden');
        loading.classList.remove('hidden');
        status.textContent = '正在获取二维码...';

        try {
            const res = await fetch('/api/qrcode');
            const data = await res.json();
            
            if (data.qrcode_key && data.image) {
                this.state.qrcodeKey = data.qrcode_key;
                img.src = `data:image/png;base64,${data.image}`;
                img.classList.remove('hidden');
                loading.classList.add('hidden');
                status.textContent = '请使用哔哩哔哩App扫码';
                
                this.startPolling();
            } else {
                throw new Error('Invalid QR code response');
            }
        } catch (err) {
            console.error(err);
            status.textContent = '获取二维码失败，请刷新页面重试';
            loading.textContent = 'Error';
        }
    },

    startPolling: function() {
        this.state.pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/qrcode/poll/${this.state.qrcodeKey}`);
                const json = await res.json();
                const data = json.data;

                if (!data) return;

                // Status handling based on typical Bilibili API response
                // code 0: success
                // code 86101: waiting for scan
                // code 86090: scanned, waiting for confirm
                // code 86038: expired
                
                if (data.code === 0) {
                    this.stopPolling();
                    document.getElementById('login-status').textContent = '登录成功！跳转中...';
                    this.handleLoginSuccess(data.url);
                } else if (data.code === 86090) {
                    document.getElementById('login-status').textContent = '已扫码，请在手机上确认';
                } else if (data.code === 86038) {
                    this.stopPolling();
                    document.getElementById('qrcode-expired').classList.remove('hidden');
                    document.getElementById('login-status').textContent = '二维码已过期';
                }
            } catch (err) {
                console.error('Poll error', err);
            }
        }, 3000);
    },

    stopPolling: function() {
        if (this.state.pollInterval) {
            clearInterval(this.state.pollInterval);
            this.state.pollInterval = null;
        }
    },

    handleLoginSuccess: function(url) {
        try {
            // Parse URL to get credentials
            // URL format: https://.../...?DedeUserID=...&SESSDATA=...&bili_jct=...
            const urlObj = new URL(url);
            const params = new URLSearchParams(urlObj.search);
            
            const mid = params.get('DedeUserID');
            const sessdata = params.get('SESSDATA');
            const bili_jct = params.get('bili_jct');

            if (mid && sessdata && bili_jct) {
                this.state.user = { mid, sessdata, bili_jct };
                this.saveUserToStorage();
                this.showDashboard();
                this.log(`登录成功，欢迎用户 UID: ${mid}`, 'success');
            } else {
                throw new Error('Missing credentials in login URL');
            }
        } catch (e) {
            console.error(e);
            alert('登录解析失败，请重试');
            this.initLogin();
        }
    },

    showDashboard: function() {
        this.switchView('dashboard-view');
        document.getElementById('user-mid').textContent = this.state.user.mid;
    },

    // --- Cleaning Logic ---

    clean: async function(type) {
        if (this.state.isProcessing) return;
        
        const confirmMsg = {
            'followings': '确定要取消所有关注吗？此操作不可恢复。',
            'favorites': '确定要删除所有收藏夹内容吗？此操作不可恢复。',
            'dynamics': '确定要删除所有动态吗？此操作不可恢复。',
            'history': '确定要清空观看历史吗？',
            'comments': '确定要删除所有评论吗？此操作不可恢复。',
            'all': '警告！这将清空关注、收藏、动态、评论和历史记录！确定要继续吗？'
        };

        if (!confirm(confirmMsg[type])) return;

        this.setProcessing(true);
        this.log(`开始执行任务: ${type}...`, 'info');

        try {
            const endpoint = `/api/clean/${type}`;
            const headers = {
                'Content-Type': 'application/json',
                'SESSDATA': this.state.user.sessdata,
                'bili_jct': this.state.user.bili_jct
            };
            
            const body = (type === 'history') ? null : JSON.stringify({ mid: parseInt(this.state.user.mid) });

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: headers,
                body: body
            });

            const result = await res.json();

            if (res.ok && result.success) {
                if (type === 'all') {
                    const c = result.counts;
                    this.log(`全部清理完成! 总计: ${result.total}`, 'success');
                    this.log(`详情: 关注-${c.followings}, 收藏-${c.favorites}, 动态-${c.dynamics}, 历史-${c.history}`, 'success');
                } else {
                    this.log(`清理完成! 成功处理数量: ${result.count}`, 'success');
                }
            } else {
                this.log(`任务失败: ${result.error || result.message || 'Unknown error'}`, 'error');
            }

        } catch (err) {
            console.error(err);
            this.log(`请求发生错误: ${err.message}`, 'error');
        } finally {
            this.setProcessing(false);
        }
    },

    setProcessing: function(processing) {
        this.state.isProcessing = processing;
        document.querySelectorAll('button.btn-primary, button.btn-danger').forEach(btn => {
            btn.disabled = processing;
            if (processing) {
                btn.style.opacity = '0.7';
            } else {
                btn.style.opacity = '1';
            }
        });
    },

    // --- Logging ---

    log: function(message, type = 'normal') {
        const container = document.getElementById('log-container');
        const placeholder = container.querySelector('.log-placeholder');
        if (placeholder) placeholder.remove();

        const div = document.createElement('div');
        div.className = 'log-entry';
        
        const time = new Date().toLocaleTimeString();
        const typeClass = type === 'success' ? 'log-success' : (type === 'error' ? 'log-error' : (type === 'info' ? 'log-info' : ''));
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'log-time';
        timeSpan.textContent = `[${time}]`;

        const msgSpan = document.createElement('span');
        msgSpan.className = typeClass;
        msgSpan.textContent = message;

        div.appendChild(timeSpan);
        div.appendChild(msgSpan);
        
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    },

    clearLog: function() {
        const container = document.getElementById('log-container');
        container.innerHTML = '<div class="log-placeholder">准备就绪，等待指令...</div>';
    }
};

// Start the app
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
