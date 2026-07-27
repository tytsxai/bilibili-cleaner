// 凭据存放在 sessionStorage 而不是 localStorage：
// sessionStorage 仅限当前标签页，关闭即清除；localStorage 会把 SESSDATA 长期
// 留在浏览器 profile 里，任何一次 XSS 或共用电脑都能取走。
// 后端刻意不落盘任何凭据，所以浏览器侧的留存时间就是真实暴露窗口。
// 主题偏好不敏感，仍用 localStorage 以便跨标签页保持。
const CREDENTIALS_STORAGE = window.sessionStorage;

const app = {
    state: {
        qrcodeKey: null,
        pollInterval: null,
        user: {
            mid: null,
            sessdata: null,
            bili_jct: null
        },
        isProcessing: false,
        theme: 'light'
    },

    init: function() {
        this.initTheme();
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

        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.toggleTheme();
        });
    },

    // --- Theme ---

    initTheme: function() {
        const saved = localStorage.getItem('bili_cleaner_theme');
        if (saved) {
            this.state.theme = saved;
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            this.state.theme = 'dark';
        }
        this.applyTheme();
    },

    toggleTheme: function() {
        this.state.theme = this.state.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('bili_cleaner_theme', this.state.theme);
        this.applyTheme();
    },

    applyTheme: function() {
        document.documentElement.setAttribute('data-theme', this.state.theme);
        const btn = document.getElementById('theme-toggle');
        btn.textContent = this.state.theme === 'light' ? '🌙' : '☀️';
    },

    loadUserFromStorage: function() {
        // 迁移：早期版本把凭据写在 localStorage，这里顺手清掉残留，
        // 否则旧用户的 SESSDATA 会一直留在浏览器里。
        localStorage.removeItem('bili_cleaner_user');

        const stored = CREDENTIALS_STORAGE.getItem('bili_cleaner_user');
        if (stored) {
            try {
                this.state.user = JSON.parse(stored);
            } catch (e) {
                console.error('Failed to parse user data');
                CREDENTIALS_STORAGE.removeItem('bili_cleaner_user');
            }
        }
    },

    saveUserToStorage: function() {
        CREDENTIALS_STORAGE.setItem('bili_cleaner_user', JSON.stringify(this.state.user));
    },

    logout: function() {
        this.state.user = { mid: null, sessdata: null, bili_jct: null };
        CREDENTIALS_STORAGE.removeItem('bili_cleaner_user');
        localStorage.removeItem('bili_cleaner_user');
        this.stopPolling();
        this.switchView('login-view');
        this.initLogin();
        this.log('已退出登录（凭据已从本标签页清除）', 'info');
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

    authHeaders: function() {
        return {
            'SESSDATA': this.state.user.sessdata,
            'bili_jct': this.state.user.bili_jct
        };
    },

    requestJson: async function(endpoint, options = {}) {
        const res = await fetch(endpoint, options);
        const text = await res.text();
        let payload = {};
        if (text) {
            try {
                payload = JSON.parse(text);
            } catch (err) {
                payload = { error: text };
            }
        }
        if (!res.ok) {
            throw new Error(payload.error || payload.message || `HTTP ${res.status}`);
        }
        return payload;
    },

    delay: function(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    // 服务重启会丢失任务状态，网络也可能持续失败。没有上限的话页面会一直
    // 空转，按钮永远禁用，用户也拿不到任何结论。
    POLL_INTERVAL_MS: 3000,
    POLL_MAX_MS: 6 * 60 * 60 * 1000,   // 1.5 req/s 下清理超大账号的宽松上限
    POLL_MAX_CONSECUTIVE_ERRORS: 5,

    pollTask: async function(taskId) {
        let lastProgress = '';
        let consecutiveErrors = 0;
        const deadline = Date.now() + this.POLL_MAX_MS;

        while (true) {
            if (Date.now() > deadline) {
                throw new Error('任务轮询超时，请用 GET /api/v2/tasks 查询该任务的最终状态');
            }

            let task;
            try {
                task = await this.requestJson(`/api/v2/tasks/${encodeURIComponent(taskId)}`, {
                    headers: this.authHeaders()
                });
                consecutiveErrors = 0;
            } catch (err) {
                consecutiveErrors += 1;
                if (consecutiveErrors >= this.POLL_MAX_CONSECUTIVE_ERRORS) {
                    throw new Error(`无法获取任务状态（连续 ${consecutiveErrors} 次失败）：${err.message}`);
                }
                this.log(`查询任务状态失败，重试中 (${consecutiveErrors}/${this.POLL_MAX_CONSECUTIVE_ERRORS}): ${err.message}`, 'error');
                await this.delay(this.POLL_INTERVAL_MS);
                continue;
            }

            this.updateTaskProgress(task);

            const currentProgress = `${task.processed || 0}/${task.total || '?'}`;
            if (currentProgress !== lastProgress) {
                this.log(`任务进度: ${task.status} ${currentProgress}`, 'info');
                lastProgress = currentProgress;
            }

            if (!['pending', 'running'].includes(task.status)) {
                return task;
            }
            await this.delay(this.POLL_INTERVAL_MS);
        }
    },

    updateTaskProgress: function(task) {
        const fill = document.getElementById('progress-fill');
        fill.dataset.mode = 'determinate';
        const processed = Number(task.processed || 0);
        const total = Number(task.total || 0);
        if (total > 0) {
            fill.style.width = Math.min(100, Math.round((processed / total) * 100)) + '%';
        } else if (processed > 0) {
            fill.style.width = '90%';
        }
    },

    // 后端只保留前 N 条错误明细，真实总数在 error_count 里。用 errors.length
    // 会在大规模失败时严重少报。
    errorCount: function(task) {
        if (typeof task.error_count === 'number') return task.error_count;
        return Array.isArray(task.errors) ? task.errors.length : 0;
    },

    // stopped_reason 可能是字符串（单项清理），也可能是 {资源: 原因} 对象（clean-all）。
    describeStopped: function(reason) {
        if (typeof reason === 'string') return reason;
        return Object.entries(reason).map(([key, value]) => `${key}=${value}`).join(', ');
    },

    logTaskCompletion: function(type, task) {
        const result = task.result || {};
        if (task.status !== 'completed') {
            const count = this.errorCount(task);
            if (count) {
                this.log(`任务失败，错误数: ${count}`, 'error');
            }
            throw new Error(`任务状态: ${task.status}`);
        }

        if (type === 'all') {
            const followings = Number(result.followings || 0);
            const favorites = Number(result.favorites || 0);
            const dynamics = Number(result.dynamics || 0);
            const history = Number(result.history || 0);
            const total = followings + favorites + dynamics + history;
            this.log(`全部清理完成! 总计: ${total}`, 'success');
            this.log(`详情: 关注-${followings}, 收藏-${favorites}, 动态-${dynamics}, 历史-${history}`, 'success');
        } else {
            const ok = Number(result.ok || task.processed || 0);
            this.log(`清理完成! 成功处理数量: ${ok}`, 'success');
        }

        if (result.stopped_reason) {
            this.log(`任务提前停止（未清理干净）: ${this.describeStopped(result.stopped_reason)}`, 'error');
        }
        const errorCount = this.errorCount(task);
        if (errorCount) {
            this.log(`部分项目处理失败，错误数: ${errorCount}`, 'error');
        }
    },

    clean: async function(type) {
        if (this.state.isProcessing) return;
        
        const confirmMsg = {
            'followings': '确定要取消所有关注吗？此操作不可恢复。',
            'favorites': '确定要删除所有收藏夹内容吗？此操作不可恢复。',
            'dynamics': '确定要删除所有动态吗？此操作不可恢复。',
            'history': '确定要清空观看历史吗？',
            'all': '警告！这将清空关注、收藏、动态和历史记录！确定要继续吗？'
        };

        if (!confirm(confirmMsg[type])) return;

        this.setProcessing(true);
        this.log(`开始执行任务: ${type}...`, 'info');

        try {
            const mid = parseInt(this.state.user.mid, 10);
            if (!Number.isFinite(mid)) {
                throw new Error('当前用户 UID 无效，请重新登录');
            }

            if (type === 'history') {
                const result = await this.requestJson('/api/v2/history/clear', {
                    method: 'POST',
                    headers: this.authHeaders()
                });
                this.log(`清理完成! 成功处理数量: ${result.count || 1}`, 'success');
                return;
            }

            const endpoints = {
                followings: `/api/v2/followings/clear?mid=${encodeURIComponent(mid)}`,
                favorites: `/api/v2/favorites/clear?mid=${encodeURIComponent(mid)}`,
                dynamics: `/api/v2/dynamics/clear?mid=${encodeURIComponent(mid)}`,
                all: `/api/v2/tasks/clean-all?mid=${encodeURIComponent(mid)}`
            };
            const endpoint = endpoints[type];
            if (!endpoint) {
                throw new Error(`未知任务类型: ${type}`);
            }

            const ack = await this.requestJson(endpoint, {
                method: 'POST',
                headers: this.authHeaders()
            });
            if (!ack.task_id) {
                throw new Error('任务创建失败：响应缺少 task_id');
            }

            this.log(`任务已提交: ${ack.task_id}`, 'info');
            const task = await this.pollTask(ack.task_id);
            this.logTaskCompletion(type, task);

        } catch (err) {
            console.error(err);
            this.log(`请求发生错误: ${err.message}`, 'error');
        } finally {
            this.setProcessing(false);
        }
    },

    setProcessing: function(processing) {
        this.state.isProcessing = processing;
        const progressBar = document.getElementById('progress-bar');
        const progressFill = document.getElementById('progress-fill');

        document.querySelectorAll('button.btn-primary, button.btn-danger').forEach(btn => {
            btn.disabled = processing;
        });

        if (processing) {
            progressFill.dataset.mode = 'indeterminate';
            progressBar.classList.add('active');
            this.animateProgress();
        } else {
            progressFill.style.width = '100%';
            setTimeout(() => {
                progressBar.classList.remove('active');
                progressFill.style.width = '0%';
            }, 500);
        }
    },

    animateProgress: function() {
        const fill = document.getElementById('progress-fill');
        let width = 0;
        const animate = () => {
            if (!this.state.isProcessing) return;
            if (fill.dataset.mode === 'determinate') return;
            width = Math.min(width + Math.random() * 15, 90);
            fill.style.width = width + '%';
            setTimeout(animate, 300 + Math.random() * 500);
        };
        animate();
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
