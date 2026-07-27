// 凭据存放在 sessionStorage 而不是 localStorage：
// sessionStorage 仅限当前标签页，关闭即清除；localStorage 会把 SESSDATA 长期
// 留在浏览器 profile 里，任何一次 XSS 或共用电脑都能取走。
// 后端刻意不落盘任何凭据，所以浏览器侧的留存时间就是真实暴露窗口。
// 主题偏好不敏感，仍用 localStorage 以便跨标签页保持。
const CREDENTIALS_STORAGE = window.sessionStorage;
const CREDENTIALS_KEY = "bili_cleaner_user";

const app = {
    state: {
        qrcodeKey: null,
        pollInterval: null,
        taskPollInterval: null,
        theme: "light",
        activePanel: "overview-panel",
        demo: false,
        user: {
            mid: null,
            uname: null,
            sessdata: null,
            bili_jct: null
        },
        followings: {
            page: 1,
            pageSize: 50,
            total: null,
            items: [],
            selected: new Set()
        },
        favorites: {
            folders: [],
            activeFolder: null,
            page: 1,
            items: [],
            selected: new Map()
        },
        dynamics: {
            items: [],
            offset: "",
            hasMore: false,
            selected: new Set()
        },
        history: {
            items: [],
            cursor: { max: 0, view_at: 0 },
            selected: new Set()
        },
        tasks: new Map()
    },

    demoData: {
        followings: [
            {
                mid: 100101,
                uname: "AI 工程实践",
                sign: "大模型应用、Agent 编排、工程落地",
                face: "",
                detail: {
                    stat: { follower: 284000 },
                    video_count: 168,
                    latest_video: { title: "从 OpenAPI 到可执行 Agent 工作流", pubdate: 1779120000 }
                }
            },
            {
                mid: 100102,
                uname: "旧账号杂谈",
                sign: "停更很久，偶尔转发抽奖",
                face: "",
                detail: {
                    stat: { follower: 820 },
                    video_count: 12,
                    latest_video: { title: "两年前的生活记录", pubdate: 1704067200 }
                }
            },
            {
                mid: 100103,
                uname: "Python 自动化实验室",
                sign: "FastAPI、Typer、爬虫与本地工具",
                face: "",
                detail: {
                    stat: { follower: 76200 },
                    video_count: 94,
                    latest_video: { title: "用 CLI 管理个人数据清理任务", pubdate: 1777824000 }
                }
            },
            {
                mid: 100104,
                uname: "低质搬运号",
                sign: "每日热门合集，商务合作私信",
                face: "",
                detail: {
                    stat: { follower: 3100 },
                    video_count: 402,
                    latest_video: { title: "无来源混剪合集", pubdate: 1751328000 }
                }
            },
            {
                mid: 100105,
                uname: "科普观察站",
                sign: "计算机、物理、工程科普",
                face: "",
                detail: {
                    stat: { follower: 191000 },
                    video_count: 221,
                    latest_video: { title: "为什么本地优先工具更适合隐私数据", pubdate: 1778428800 }
                }
            }
        ],
        folders: [
            { id: 201, media_id: 201, title: "技术学习", media_count: 36 },
            { id: 202, media_id: 202, title: "待清理合集", media_count: 118 },
            { id: 203, media_id: 203, title: "生活收藏", media_count: 19 }
        ],
        favorites: [
            { id: 9001, type: 2, title: "FastAPI 完整项目结构", bvid: "BV1demo001", upper: { name: "后端工程笔记", mid: 301 } },
            { id: 9002, type: 2, title: "三年前的热点搬运", bvid: "BV1demo002", upper: { name: "旧内容搬运", mid: 302 } },
            { id: 9003, type: 2, title: "本地 CLI 工具设计", bvid: "BV1demo003", upper: { name: "自动化实践", mid: 303 } }
        ],
        dynamics: [
            { id: "8001", id_str: "8001", type: "DYNAMIC_TYPE_WORD", modules: { module_dynamic: { desc: { text: "发布一个本地清理工具的开发记录，强调先预览再删除。" } } } },
            { id: "8002", id_str: "8002", type: "DYNAMIC_TYPE_DRAW", modules: { module_dynamic: { desc: { text: "旧抽奖转发，适合作为清理候选。" } } } }
        ],
        history: [
            { title: "OpenAPI 与 AI Agent 接入实践", author_name: "AI 工程实践", kid: "archive_7001", history: { business: "archive", oid: 7001 }, view_at: 1779292800 },
            { title: "低质量合集视频", author_name: "旧内容搬运", kid: "archive_7002", history: { business: "archive", oid: 7002 }, view_at: 1779206400 },
            { title: "FastAPI 后端任务队列讲解", author_name: "后端工程笔记", kid: "archive_7003", history: { business: "archive", oid: 7003 }, view_at: 1779120000 }
        ]
    },

    init() {
        this.initTheme();
        this.loadUserFromStorage();
        this.bindEvents();

        if (new URLSearchParams(window.location.search).get("demo") === "1") {
            this.enterDemoMode();
            return;
        }

        if (this.state.user.sessdata && this.state.user.mid) {
            this.showDashboard();
            this.refreshTasks();
        } else {
            this.initLogin();
        }
    },

    bindEvents() {
        document.getElementById("theme-toggle").addEventListener("click", () => this.toggleTheme());
        document.getElementById("logout-btn").addEventListener("click", () => this.logout());
        document.getElementById("demo-toggle").addEventListener("click", () => this.enterDemoMode());
        document.getElementById("demo-login-btn").addEventListener("click", () => this.enterDemoMode());
        document.getElementById("qrcode-expired").addEventListener("click", () => this.initLogin());
        document.getElementById("clear-log-btn").addEventListener("click", () => this.clearLog());

        document.querySelectorAll("[data-panel]").forEach((button) => {
            button.addEventListener("click", () => this.switchPanel(button.dataset.panel));
        });

        document.getElementById("load-followings-btn").addEventListener("click", () => this.loadFollowings(1));
        document.getElementById("followings-prev").addEventListener("click", () => this.loadFollowings(Math.max(1, this.state.followings.page - 1)));
        document.getElementById("followings-next").addEventListener("click", () => this.loadFollowings(this.state.followings.page + 1));
        document.getElementById("following-search").addEventListener("input", () => this.renderFollowings());
        document.getElementById("following-fans-max").addEventListener("input", () => this.renderFollowings());
        document.getElementById("following-stale-days").addEventListener("input", () => this.renderFollowings());
        document.getElementById("followings-select-page").addEventListener("change", (event) => this.toggleFollowingsPage(event.target.checked));
        document.getElementById("tag-followings-btn").addEventListener("click", () => this.tagSelectedFollowings());
        document.getElementById("unfollow-selected-btn").addEventListener("click", () => this.unfollowSelected());

        document.getElementById("load-folders-btn").addEventListener("click", () => this.loadFolders());
        document.getElementById("search-favorites-btn").addEventListener("click", () => this.loadFavoriteItems(1));
        document.getElementById("favorite-keyword").addEventListener("keydown", (event) => {
            if (event.key === "Enter") this.loadFavoriteItems(1);
        });
        document.getElementById("favorites-prev").addEventListener("click", () => this.loadFavoriteItems(Math.max(1, this.state.favorites.page - 1)));
        document.getElementById("favorites-next").addEventListener("click", () => this.loadFavoriteItems(this.state.favorites.page + 1));
        document.getElementById("delete-favorites-btn").addEventListener("click", () => this.deleteSelectedFavorites());

        document.getElementById("load-dynamics-btn").addEventListener("click", () => this.loadDynamics(true));
        document.getElementById("dynamics-more").addEventListener("click", () => this.loadDynamics(false));
        document.getElementById("delete-dynamics-btn").addEventListener("click", () => this.deleteSelectedDynamics());

        document.getElementById("load-history-btn").addEventListener("click", () => this.loadHistory(true));
        document.getElementById("history-more").addEventListener("click", () => this.loadHistory(false));
        document.getElementById("clear-history-btn").addEventListener("click", () => this.clearHistory());
    },

    initTheme() {
        const saved = localStorage.getItem("bili_cleaner_theme");
        if (saved) {
            this.state.theme = saved;
        } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
            this.state.theme = "dark";
        }
        this.applyTheme();
    },

    toggleTheme() {
        this.state.theme = this.state.theme === "light" ? "dark" : "light";
        localStorage.setItem("bili_cleaner_theme", this.state.theme);
        this.applyTheme();
    },

    applyTheme() {
        document.documentElement.setAttribute("data-theme", this.state.theme);
        document.getElementById("theme-toggle").textContent = this.state.theme === "light" ? "◐" : "◑";
    },

    loadUserFromStorage() {
        // 迁移：早期版本把凭据写在 localStorage，这里顺手清掉残留，
        // 否则旧用户的 SESSDATA 会一直留在浏览器 profile 里。
        localStorage.removeItem(CREDENTIALS_KEY);

        const stored = CREDENTIALS_STORAGE.getItem(CREDENTIALS_KEY);
        if (!stored) return;
        try {
            this.state.user = JSON.parse(stored);
        } catch {
            CREDENTIALS_STORAGE.removeItem(CREDENTIALS_KEY);
        }
    },

    saveUserToStorage() {
        if (this.state.demo) return;
        CREDENTIALS_STORAGE.setItem(CREDENTIALS_KEY, JSON.stringify(this.state.user));
    },

    enterDemoMode() {
        this.stopPolling();
        this.state.demo = true;
        this.state.user = {
            mid: 22334455,
            uname: "demo_user",
            sessdata: "demo",
            bili_jct: "demo"
        };
        this.showDashboard();
        const requestedPanel = new URLSearchParams(window.location.search).get("panel");
        this.switchPanel(requestedPanel || "followings-panel");
        this.loadFollowings(1);
        this.loadFolders();
        this.loadDynamics(true);
        this.loadHistory(true);
        this.log("已进入脱敏演示模式，所有数据均为示例。", "info");
    },

    logout() {
        this.state.user = { mid: null, uname: null, sessdata: null, bili_jct: null };
        this.state.demo = false;
        CREDENTIALS_STORAGE.removeItem(CREDENTIALS_KEY);
        localStorage.removeItem(CREDENTIALS_KEY);
        this.stopPolling();
        this.stopTaskPolling();
        document.getElementById("dashboard-view").classList.add("hidden");
        document.getElementById("login-view").classList.remove("hidden");
        document.getElementById("logout-btn").classList.add("hidden");
        this.clearSelections();
        this.initLogin();
        this.log("已退出登录，浏览器本地凭证已清除。", "info");
    },

    showDashboard() {
        document.getElementById("login-view").classList.add("hidden");
        document.getElementById("dashboard-view").classList.remove("hidden");
        document.getElementById("logout-btn").classList.remove("hidden");
        document.getElementById("user-label").textContent = this.state.user.uname || `UID ${this.state.user.mid}`;
        document.getElementById("session-label").textContent = this.state.demo ? "脱敏演示数据" : `UID ${this.state.user.mid}`;
        this.startTaskPolling();
        this.updateSelectionState();
    },

    initLogin: async function() {
        if (this.state.demo) return;
        this.stopPolling();
        const img = document.getElementById("qrcode-img");
        const loading = document.getElementById("qrcode-loading");
        const expired = document.getElementById("qrcode-expired");
        const status = document.getElementById("login-status");

        img.classList.add("hidden");
        expired.classList.add("hidden");
        loading.classList.remove("hidden");
        loading.textContent = "获取二维码中...";
        status.textContent = "正在获取二维码...";

        try {
            const response = await fetch("/api/qrcode");
            const data = await response.json();
            if (!data.qrcode_key || !data.image) throw new Error("二维码响应无效");
            this.state.qrcodeKey = data.qrcode_key;
            img.src = `data:image/png;base64,${data.image}`;
            img.classList.remove("hidden");
            loading.classList.add("hidden");
            status.textContent = "请使用哔哩哔哩 App 扫码";
            this.startPolling();
        } catch (error) {
            loading.textContent = "获取失败";
            status.textContent = "获取二维码失败，可刷新页面或使用演示模式预览。";
            this.log(`二维码获取失败：${error.message}`, "error");
        }
    },

    startPolling() {
        this.state.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/qrcode/poll/${this.state.qrcodeKey}`);
                const json = await response.json();
                const data = json.data;
                if (!data) return;

                if (data.code === 0) {
                    this.stopPolling();
                    document.getElementById("login-status").textContent = "登录成功，正在进入控制台...";
                    await this.handleLoginSuccess(data.url);
                } else if (data.code === 86090) {
                    document.getElementById("login-status").textContent = "已扫码，请在手机上确认";
                } else if (data.code === 86038) {
                    this.stopPolling();
                    document.getElementById("qrcode-expired").classList.remove("hidden");
                    document.getElementById("login-status").textContent = "二维码已过期";
                }
            } catch (error) {
                this.log(`登录轮询失败：${error.message}`, "warning");
            }
        }, 3000);
    },

    stopPolling() {
        if (this.state.pollInterval) {
            clearInterval(this.state.pollInterval);
            this.state.pollInterval = null;
        }
    },

    async handleLoginSuccess(url) {
        try {
            const parsed = new URL(url);
            const params = new URLSearchParams(parsed.search);
            const mid = params.get("DedeUserID");
            const sessdata = params.get("SESSDATA");
            const biliJct = params.get("bili_jct");
            if (!mid || !sessdata || !biliJct) throw new Error("登录回调缺少凭证");
            this.state.user = { mid, sessdata, bili_jct: biliJct, uname: null };
            const me = await this.apiFetch("/api/v2/me");
            this.state.user.uname = me.uname || null;
            this.saveUserToStorage();
            this.showDashboard();
            this.log(`登录成功：${this.state.user.uname || `UID ${mid}`}`, "success");
        } catch (error) {
            this.log(`登录解析失败：${error.message}`, "error");
            this.initLogin();
        }
    },

    async apiFetch(path, options = {}) {
        if (this.state.demo) return this.mockFetch(path, options);
        const headers = {
            "Content-Type": "application/json",
            "SESSDATA": this.state.user.sessdata,
            "bili_jct": this.state.user.bili_jct,
            ...(options.headers || {})
        };
        const response = await fetch(path, { ...options, headers });
        const text = await response.text();
        const data = text ? JSON.parse(text) : {};
        if (!response.ok || data.error) {
            throw new Error(this.formatApiError(response.status, data));
        }
        return data;
    },

    formatApiError(status, data) {
        const code = data && data.code;
        if (status === 401 || code === -101) return "登录态已失效，请重新扫码登录。";
        if (status === 412 || status === 429 || code === -352 || code === -799) {
            return "触发 B 站风控或限流，请暂停批量操作，等待一段时间后再继续。";
        }
        return (data && (data.error || data.message)) || `请求失败：HTTP ${status}`;
    },

    async mockFetch(path, options = {}) {
        await new Promise((resolve) => setTimeout(resolve, 120));
        if (path.startsWith("/api/v2/me")) {
            return { isLogin: true, mid: this.state.user.mid, uname: this.state.user.uname };
        }
        if (path.startsWith("/api/v2/followings?")) {
            return { page: this.state.followings.page, page_size: 50, total: this.demoData.followings.length, items: this.demoData.followings };
        }
        if (path.startsWith("/api/v2/relation/tags/members")) {
            return { ok: true, tag_name: "to-review" };
        }
        if (path.startsWith("/api/v2/followings/unfollow-task")) {
            return this.createDemoTask("followings.unfollow", JSON.parse(options.body || "{}").mids.length);
        }
        if (path.startsWith("/api/v2/favorites/folders/") && path.includes("/items")) {
            return { info: this.state.favorites.activeFolder, medias: this.demoData.favorites };
        }
        if (path.startsWith("/api/v2/favorites/folders/") && path.endsWith("/delete")) {
            return { ok: JSON.parse(options.body || "{}").resources.length, total: JSON.parse(options.body || "{}").resources.length, errors: [] };
        }
        if (path.startsWith("/api/v2/favorites/folders")) {
            return this.demoData.folders;
        }
        if (path.startsWith("/api/v2/dynamics/delete")) {
            return { ok: JSON.parse(options.body || "{}").ids.length, total: JSON.parse(options.body || "{}").ids.length, errors: [] };
        }
        if (path.startsWith("/api/v2/dynamics")) {
            return { items: this.demoData.dynamics, has_more: false, offset: "" };
        }
        if (path.startsWith("/api/v2/history/delete")) {
            return { ok: true };
        }
        if (path.startsWith("/api/v2/history/clear")) {
            return { success: true, count: 1 };
        }
        if (path.startsWith("/api/v2/history")) {
            return { cursor: { max: 0, view_at: 0 }, list: this.demoData.history };
        }
        if (path.startsWith("/api/v2/tasks")) {
            return Array.from(this.state.tasks.values());
        }
        return {};
    },

    createDemoTask(kind, total) {
        const taskId = `demo-${Date.now()}`;
        const task = {
            task_id: taskId,
            kind,
            status: "running",
            processed: 0,
            total,
            errors: [],
            result: null,
            started_at: Date.now() / 1000,
            finished_at: null
        };
        this.state.tasks.set(taskId, task);
        const timer = setInterval(() => {
            task.processed = Math.min(task.total, task.processed + Math.max(1, Math.ceil(task.total / 4)));
            if (task.processed >= task.total) {
                task.status = "completed";
                task.finished_at = Date.now() / 1000;
                task.result = { ok: task.total, total: task.total };
                clearInterval(timer);
            }
            this.renderTasks(Array.from(this.state.tasks.values()));
        }, 700);
        return { task_id: taskId, status: "pending" };
    },

    switchPanel(panelId) {
        this.state.activePanel = panelId;
        document.querySelectorAll(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === panelId));
        document.querySelectorAll(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.panel === panelId));
        const active = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
        document.getElementById("page-title").textContent = active ? active.textContent : "本地账号清理控制台";
    },

    async loadFollowings(page) {
        this.state.followings.page = page;
        const withDetail = document.getElementById("following-with-detail").checked;
        this.log(`加载关注列表：第 ${page} 页${withDetail ? "，包含详情" : ""}。`, "info");
        try {
            const params = new URLSearchParams({
                mid: this.state.user.mid,
                page: String(page),
                page_size: String(this.state.followings.pageSize),
                with_detail: String(withDetail)
            });
            const data = await this.apiFetch(`/api/v2/followings?${params.toString()}`);
            this.state.followings.items = data.items || [];
            this.state.followings.total = data.total || null;
            this.renderFollowings();
            this.log(`已加载 ${this.state.followings.items.length} 个关注。`, "success");
        } catch (error) {
            this.log(error.message, "error");
            this.renderEmpty("followings-body", "关注列表加载失败");
        }
    },

    renderFollowings() {
        const body = document.getElementById("followings-body");
        body.replaceChildren();
        const items = this.filteredFollowings();
        if (!items.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 6;
            cell.appendChild(this.emptyNode("暂无匹配关注，请调整筛选或加载列表。"));
            row.appendChild(cell);
            body.appendChild(row);
        }

        items.forEach((item) => {
            const row = document.createElement("tr");
            const mid = Number(item.mid);
            const detail = item.detail || {};
            const latest = detail.latest_video || {};
            const fans = this.readFans(item);
            const checkbox = this.el("input");
            checkbox.type = "checkbox";
            checkbox.checked = this.state.followings.selected.has(mid);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) this.state.followings.selected.add(mid);
                else this.state.followings.selected.delete(mid);
                this.updateSelectionState();
            });

            row.appendChild(this.td(checkbox));
            row.appendChild(this.td(this.avatarLine(item.face, item.uname || `UID ${mid}`, `UID ${mid}`)));
            row.appendChild(this.td(this.formatNumber(fans)));
            row.appendChild(this.td(String(detail.video_count ?? "-")));
            row.appendChild(this.td(this.videoSummary(latest)));
            row.appendChild(this.td(item.sign || "-"));
            body.appendChild(row);
        });

        document.getElementById("followings-page-label").textContent = `第 ${this.state.followings.page} 页${this.state.followings.total ? ` / 共 ${this.state.followings.total}` : ""}`;
        document.getElementById("followings-select-page").checked = items.length > 0 && items.every((item) => this.state.followings.selected.has(Number(item.mid)));
        this.updateSelectionState();
    },

    filteredFollowings() {
        const keyword = document.getElementById("following-search").value.trim().toLowerCase();
        const fansMax = Number(document.getElementById("following-fans-max").value || 0);
        const staleDays = Number(document.getElementById("following-stale-days").value || 0);
        const staleBefore = staleDays ? Date.now() / 1000 - staleDays * 86400 : 0;
        return this.state.followings.items.filter((item) => {
            const text = `${item.mid} ${item.uname || ""} ${item.sign || ""}`.toLowerCase();
            const latest = item.detail && item.detail.latest_video;
            if (keyword && !text.includes(keyword)) return false;
            if (fansMax && this.readFans(item) > fansMax) return false;
            if (staleBefore && latest && latest.pubdate && latest.pubdate > staleBefore) return false;
            return true;
        });
    },

    toggleFollowingsPage(checked) {
        this.filteredFollowings().forEach((item) => {
            const mid = Number(item.mid);
            if (checked) this.state.followings.selected.add(mid);
            else this.state.followings.selected.delete(mid);
        });
        this.renderFollowings();
    },

    async tagSelectedFollowings() {
        const mids = Array.from(this.state.followings.selected);
        if (!mids.length) return;
        const ok = await this.confirmDanger({
            title: "加入复核分组",
            message: `将 ${mids.length} 个关注加入 B 站分组 to-review。这个操作不会删除数据，适合先人工复核。`,
            danger: false
        });
        if (!ok) return;
        try {
            await this.apiFetch("/api/v2/relation/tags/members", {
                method: "POST",
                body: JSON.stringify({ mids, tag_name: "to-review" })
            });
            this.log(`已加入 to-review 分组：${mids.length} 个关注。`, "success");
        } catch (error) {
            this.log(error.message, "error");
        }
    },

    async unfollowSelected() {
        const mids = Array.from(this.state.followings.selected);
        if (!mids.length) return;
        const ok = await this.confirmDanger({
            title: "异步取关所选关注",
            message: `即将取关 ${mids.length} 个 UP 主。B 站没有批量取关接口，任务会按限流逐个执行，删除不可恢复。`,
            requireText: mids.length > 100 ? "确认取关" : ""
        });
        if (!ok) return;
        try {
            const ack = await this.apiFetch("/api/v2/followings/unfollow-task", {
                method: "POST",
                body: JSON.stringify({ mids })
            });
            this.log(`已创建取关任务：${ack.task_id}`, "success");
            this.state.followings.selected.clear();
            this.renderFollowings();
            this.refreshTasks();
        } catch (error) {
            this.log(error.message, "error");
        }
    },

    async loadFolders() {
        this.log("加载收藏夹列表。", "info");
        try {
            const data = await this.apiFetch(`/api/v2/favorites/folders?mid=${encodeURIComponent(this.state.user.mid)}`);
            this.state.favorites.folders = Array.isArray(data) ? data : [];
            this.renderFolders();
            if (!this.state.favorites.activeFolder && this.state.favorites.folders.length) {
                this.selectFolder(this.state.favorites.folders[0]);
            }
            this.log(`已加载 ${this.state.favorites.folders.length} 个收藏夹。`, "success");
        } catch (error) {
            this.log(error.message, "error");
            document.getElementById("folders-list").replaceChildren(this.emptyNode("收藏夹加载失败"));
        }
    },

    renderFolders() {
        const list = document.getElementById("folders-list");
        list.replaceChildren();
        if (!this.state.favorites.folders.length) {
            list.appendChild(this.emptyNode("暂无收藏夹"));
            return;
        }
        this.state.favorites.folders.forEach((folder) => {
            const item = this.el("button", "folder-item");
            item.type = "button";
            item.classList.toggle("active", this.folderId(folder) === this.folderId(this.state.favorites.activeFolder));
            item.appendChild(this.el("strong", "", folder.title || folder.name || `收藏夹 ${this.folderId(folder)}`));
            item.appendChild(this.el("small", "resource-meta", `${folder.media_count ?? folder.count ?? "-"} 个资源`));
            item.addEventListener("click", () => this.selectFolder(folder));
            list.appendChild(item);
        });
    },

    selectFolder(folder) {
        this.state.favorites.activeFolder = folder;
        this.state.favorites.page = 1;
        this.state.favorites.selected.clear();
        this.renderFolders();
        this.loadFavoriteItems(1);
    },

    async loadFavoriteItems(page) {
        const folder = this.state.favorites.activeFolder;
        if (!folder) {
            document.getElementById("favorite-items").replaceChildren(this.emptyNode("请先选择收藏夹"));
            return;
        }
        this.state.favorites.page = page;
        const keyword = document.getElementById("favorite-keyword").value.trim();
        const params = new URLSearchParams({ page: String(page), page_size: "20", keyword, order: "mtime" });
        try {
            const data = await this.apiFetch(`/api/v2/favorites/folders/${this.folderId(folder)}/items?${params.toString()}`);
            this.state.favorites.items = data.medias || data.items || [];
            this.renderFavoriteItems();
            this.log(`已加载收藏资源：${this.state.favorites.items.length} 条。`, "success");
        } catch (error) {
            this.log(error.message, "error");
            document.getElementById("favorite-items").replaceChildren(this.emptyNode("收藏资源加载失败"));
        }
    },

    renderFavoriteItems() {
        const list = document.getElementById("favorite-items");
        list.replaceChildren();
        if (!this.state.favorites.items.length) {
            list.appendChild(this.emptyNode("当前收藏夹暂无匹配资源"));
        }
        this.state.favorites.items.forEach((item) => {
            const key = this.favoriteKey(item);
            const checkbox = this.el("input");
            checkbox.type = "checkbox";
            checkbox.checked = this.state.favorites.selected.has(key);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) this.state.favorites.selected.set(key, item);
                else this.state.favorites.selected.delete(key);
                this.updateSelectionState();
            });
            list.appendChild(this.resourceCard({
                checkbox,
                title: item.title || `资源 ${item.id}`,
                meta: `${item.bvid || "no-bvid"} · ${item.upper && (item.upper.name || item.upper.uname) ? (item.upper.name || item.upper.uname) : "未知 UP"}`,
                desc: `id=${item.id} type=${item.type || 2}`
            }));
        });
        document.getElementById("favorites-page-label").textContent = `第 ${this.state.favorites.page} 页`;
        this.updateSelectionState();
    },

    async deleteSelectedFavorites() {
        const folder = this.state.favorites.activeFolder;
        const resources = Array.from(this.state.favorites.selected.values()).map((item) => ({ id: Number(item.id), type: Number(item.type || 2) }));
        if (!folder || !resources.length) return;
        const ok = await this.confirmDanger({
            title: "删除所选收藏资源",
            message: `将从收藏夹「${folder.title || this.folderId(folder)}」删除 ${resources.length} 个资源。此操作不可恢复。`,
            requireText: resources.length > 100 ? "确认删除" : ""
        });
        if (!ok) return;
        try {
            await this.apiFetch(`/api/v2/favorites/folders/${this.folderId(folder)}/delete`, {
                method: "POST",
                body: JSON.stringify({ resources })
            });
            this.log(`已删除收藏资源：${resources.length} 个。`, "success");
            this.state.favorites.selected.clear();
            await this.loadFavoriteItems(this.state.favorites.page);
        } catch (error) {
            this.log(error.message, "error");
        }
    },

    async loadDynamics(reset) {
        if (reset) {
            this.state.dynamics.offset = "";
            this.state.dynamics.items = [];
            this.state.dynamics.selected.clear();
        }
        const params = new URLSearchParams({ mid: this.state.user.mid, offset: this.state.dynamics.offset || "" });
        try {
            const data = await this.apiFetch(`/api/v2/dynamics?${params.toString()}`);
            this.state.dynamics.items = this.state.dynamics.items.concat(data.items || []);
            this.state.dynamics.offset = data.offset || "";
            this.state.dynamics.hasMore = Boolean(data.has_more);
            this.renderDynamics();
            this.log(`已加载动态：${data.items ? data.items.length : 0} 条。`, "success");
        } catch (error) {
            this.log(error.message, "error");
            document.getElementById("dynamics-list").replaceChildren(this.emptyNode("动态加载失败"));
        }
    },

    renderDynamics() {
        const list = document.getElementById("dynamics-list");
        list.replaceChildren();
        if (!this.state.dynamics.items.length) list.appendChild(this.emptyNode("暂无动态"));
        this.state.dynamics.items.forEach((item) => {
            const id = String(item.id_str || item.id || item.dynamic_id);
            const checkbox = this.el("input");
            checkbox.type = "checkbox";
            checkbox.checked = this.state.dynamics.selected.has(id);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) this.state.dynamics.selected.add(id);
                else this.state.dynamics.selected.delete(id);
                this.updateSelectionState();
            });
            const deleteButton = this.el("button", "btn btn-ghost", "删除单条");
            deleteButton.type = "button";
            deleteButton.addEventListener("click", () => this.deleteDynamics([id]));
            list.appendChild(this.resourceCard({
                checkbox,
                title: this.dynamicTitle(item),
                meta: `dynamic_id=${id}`,
                desc: this.dynamicText(item),
                actions: [deleteButton]
            }));
        });
        document.getElementById("dynamics-more").disabled = !this.state.dynamics.hasMore;
        this.updateSelectionState();
    },

    async deleteSelectedDynamics() {
        const ids = Array.from(this.state.dynamics.selected);
        await this.deleteDynamics(ids);
    },

    async deleteDynamics(ids) {
        if (!ids.length) return;
        const ok = await this.confirmDanger({
            title: "删除动态",
            message: `将删除 ${ids.length} 条动态。此操作不可恢复。`,
            requireText: ids.length > 100 ? "确认删除" : ""
        });
        if (!ok) return;
        try {
            await this.apiFetch("/api/v2/dynamics/delete", {
                method: "POST",
                body: JSON.stringify({ ids })
            });
            this.log(`已删除动态：${ids.length} 条。`, "success");
            ids.forEach((id) => this.state.dynamics.selected.delete(String(id)));
            this.state.dynamics.items = this.state.dynamics.items.filter((item) => !ids.includes(String(item.id_str || item.id || item.dynamic_id)));
            this.renderDynamics();
        } catch (error) {
            this.log(error.message, "error");
        }
    },

    async loadHistory(reset) {
        if (reset) {
            this.state.history.cursor = { max: 0, view_at: 0 };
            this.state.history.items = [];
        }
        const cursor = this.state.history.cursor;
        const params = new URLSearchParams({
            max_id: String(cursor.max || 0),
            view_at: String(cursor.view_at || 0),
            page_size: "20",
            type: "all"
        });
        try {
            const data = await this.apiFetch(`/api/v2/history?${params.toString()}`);
            const items = data.list || [];
            this.state.history.items = this.state.history.items.concat(items);
            this.state.history.cursor = data.cursor || cursor;
            this.renderHistory();
            this.log(`已加载观看历史：${items.length} 条。`, "success");
        } catch (error) {
            this.log(error.message, "error");
            document.getElementById("history-list").replaceChildren(this.emptyNode("观看历史加载失败"));
        }
    },

    renderHistory() {
        const list = document.getElementById("history-list");
        list.replaceChildren();
        if (!this.state.history.items.length) list.appendChild(this.emptyNode("暂无观看历史"));
        this.state.history.items.forEach((item) => {
            const kid = this.historyKid(item);
            const deleteButton = this.el("button", "btn btn-ghost", "删除单条");
            deleteButton.type = "button";
            deleteButton.addEventListener("click", () => this.deleteHistory(kid));
            list.appendChild(this.resourceCard({
                title: item.title || item.show_title || "未命名记录",
                meta: `${item.author_name || item.author || "未知 UP"} · ${this.formatTime(item.view_at)}`,
                desc: kid,
                actions: [deleteButton]
            }));
        });
    },

    async deleteHistory(kid) {
        const ok = await this.confirmDanger({
            title: "删除单条观看历史",
            message: `将删除观看历史记录 ${kid}。此操作不可恢复。`
        });
        if (!ok) return;
        try {
            await this.apiFetch(`/api/v2/history/delete?kid=${encodeURIComponent(kid)}`, { method: "POST" });
            this.state.history.items = this.state.history.items.filter((item) => this.historyKid(item) !== kid);
            this.renderHistory();
            this.log(`已删除观看历史：${kid}`, "success");
        } catch (error) {
            this.log(error.message, "error");
        }
    },

    async clearHistory() {
        const ok = await this.confirmDanger({
            title: "清空全部观看历史",
            message: "这会调用 B 站清空观看历史接口，影响当前账号全部观看历史，且不可恢复。请输入「清空历史」确认。",
            requireText: "清空历史"
        });
        if (!ok) return;
        try {
            await this.apiFetch("/api/v2/history/clear", { method: "POST" });
            this.state.history.items = [];
            this.renderHistory();
            this.log("已清空观看历史。", "success");
        } catch (error) {
            this.log(error.message, "error");
        }
    },

    startTaskPolling() {
        if (this.state.taskPollInterval) return;
        this.state.taskPollInterval = setInterval(() => this.refreshTasks(), 5000);
    },

    stopTaskPolling() {
        if (this.state.taskPollInterval) {
            clearInterval(this.state.taskPollInterval);
            this.state.taskPollInterval = null;
        }
    },

    async refreshTasks() {
        if (!this.state.user.mid) return;
        try {
            const tasks = await this.apiFetch("/api/v2/tasks");
            this.renderTasks(Array.isArray(tasks) ? tasks : []);
        } catch (error) {
            this.log(`任务状态刷新失败：${error.message}`, "warning");
        }
    },

    // GET /api/v2/tasks 只返回摘要：errors 被截断为空数组，result 为 null。
    // 用 errors.length 会把大规模失败显示成 0 个错误。error_count 才是真实总数。
    taskErrorCount(task) {
        if (typeof task.error_count === "number") return task.error_count;
        return Array.isArray(task.errors) ? task.errors.length : 0;
    },

    // stopped_reason 可能是字符串（单项清理），也可能是 {资源: 原因} 对象（clean-all）。
    describeStopped(reason) {
        if (typeof reason === "string") return reason;
        return Object.entries(reason).map(([key, value]) => `${key}=${value}`).join("、");
    },

    renderTasks(tasks) {
        const list = document.getElementById("task-list");
        list.replaceChildren();
        const active = tasks.filter((task) => ["pending", "running"].includes(task.status));
        document.getElementById("task-count").textContent = String(tasks.length);
        document.getElementById("task-summary").textContent = active.length ? `${active.length} 个任务运行中` : "暂无运行任务";
        if (!tasks.length) {
            list.appendChild(this.el("p", "empty-state", "暂无任务"));
            return;
        }
        tasks.slice().reverse().forEach((task) => {
            const total = task.total || task.processed || 0;
            const percent = total ? Math.min(100, Math.round((task.processed / total) * 100)) : (task.status === "completed" ? 100 : 8);
            const item = this.el("div", "task-item");
            const top = this.el("div", "task-top");
            top.appendChild(this.el("strong", "", task.kind || "task"));
            top.appendChild(this.el("span", "", task.status));
            const meta = this.el("small", "resource-meta", `${task.processed || 0}${total ? ` / ${total}` : ""} · ${task.task_id}`);
            const track = this.el("div", "progress-track");
            const fill = this.el("div", "progress-fill");
            fill.style.width = `${percent}%`;
            track.appendChild(fill);
            item.appendChild(top);
            item.appendChild(meta);
            item.appendChild(track);
            const errorCount = this.taskErrorCount(task);
            if (errorCount) {
                item.appendChild(
                    this.el("small", "log-error", `${errorCount} 个错误，见 GET /api/v2/tasks/${task.task_id}`)
                );
            }
            const stopped = task.result && task.result.stopped_reason;
            if (stopped) {
                item.appendChild(
                    this.el("small", "log-error", `提前停止（未清理干净）：${this.describeStopped(stopped)}`)
                );
            }
            list.appendChild(item);
        });
    },

    updateSelectionState() {
        const count = this.state.followings.selected.size + this.state.favorites.selected.size + this.state.dynamics.selected.size;
        document.getElementById("selected-count").textContent = String(count);
        document.getElementById("tag-followings-btn").disabled = this.state.followings.selected.size === 0;
        document.getElementById("unfollow-selected-btn").disabled = this.state.followings.selected.size === 0;
        document.getElementById("delete-favorites-btn").disabled = this.state.favorites.selected.size === 0;
        document.getElementById("delete-dynamics-btn").disabled = this.state.dynamics.selected.size === 0;
    },

    clearSelections() {
        this.state.followings.selected.clear();
        this.state.favorites.selected.clear();
        this.state.dynamics.selected.clear();
        this.updateSelectionState();
    },

    confirmDanger({ title, message, requireText = "", danger = true }) {
        return new Promise((resolve) => {
            const backdrop = document.getElementById("confirm-modal");
            const titleNode = document.getElementById("confirm-title");
            const messageNode = document.getElementById("confirm-message");
            const input = document.getElementById("confirm-input");
            const ok = document.getElementById("confirm-ok");
            const cancel = document.getElementById("confirm-cancel");

            titleNode.textContent = title;
            messageNode.textContent = message;
            ok.className = danger ? "btn btn-danger" : "btn btn-primary";
            input.value = "";
            input.placeholder = requireText ? `请输入：${requireText}` : "";
            input.classList.toggle("hidden", !requireText);
            backdrop.classList.remove("hidden");
            if (requireText) input.focus();

            const cleanup = (value) => {
                backdrop.classList.add("hidden");
                ok.removeEventListener("click", onOk);
                cancel.removeEventListener("click", onCancel);
                resolve(value);
            };
            const onOk = () => {
                if (requireText && input.value.trim() !== requireText) {
                    this.log(`确认文本不匹配，需要输入：${requireText}`, "warning");
                    return;
                }
                cleanup(true);
            };
            const onCancel = () => cleanup(false);
            ok.addEventListener("click", onOk);
            cancel.addEventListener("click", onCancel);
        });
    },

    log(message, type = "normal") {
        const container = document.getElementById("log-container");
        const placeholder = container.querySelector(".log-placeholder");
        if (placeholder) placeholder.remove();
        const entry = this.el("div", "log-entry");
        entry.appendChild(this.el("span", "log-time", new Date().toLocaleTimeString()));
        entry.appendChild(this.el("span", this.logClass(type), message));
        container.appendChild(entry);
        container.scrollTop = container.scrollHeight;
    },

    clearLog() {
        const container = document.getElementById("log-container");
        container.replaceChildren(this.el("div", "log-placeholder", "准备就绪，等待指令..."));
    },

    logClass(type) {
        if (type === "success") return "log-success";
        if (type === "error") return "log-error";
        if (type === "info") return "log-info";
        if (type === "warning") return "log-warning";
        return "";
    },

    readFans(item) {
        return Number(item.follower || item.fans || (item.detail && item.detail.stat && item.detail.stat.follower) || 0);
    },

    videoSummary(video) {
        if (!video || !video.title) return "-";
        const wrap = this.el("div", "name-cell");
        wrap.appendChild(this.el("strong", "", video.title));
        wrap.appendChild(this.el("small", "", this.formatTime(video.pubdate)));
        return wrap;
    },

    dynamicTitle(item) {
        return item.type || item.card_type || "动态";
    },

    dynamicText(item) {
        return (item.modules && item.modules.module_dynamic && item.modules.module_dynamic.desc && item.modules.module_dynamic.desc.text)
            || item.text
            || item.content
            || "当前动态没有可展示摘要，请打开 B 站复核后再删除。";
    },

    historyKid(item) {
        if (item.kid) return String(item.kid);
        const history = item.history || {};
        const business = history.business || item.business || "archive";
        const oid = history.oid || item.oid || item.id;
        return `${business}_${oid}`;
    },

    favoriteKey(item) {
        return `${item.id}:${item.type || 2}`;
    },

    folderId(folder) {
        if (!folder) return null;
        return folder.media_id || folder.id;
    },

    formatNumber(value) {
        const number = Number(value || 0);
        if (!number) return "-";
        if (number >= 10000) return `${(number / 10000).toFixed(1)} 万`;
        return String(number);
    },

    formatTime(seconds) {
        if (!seconds) return "-";
        return new Date(Number(seconds) * 1000).toLocaleDateString();
    },

    avatarLine(src, title, subtitle) {
        const wrap = this.el("div", "avatar-line");
        const img = this.el("img", "avatar");
        img.alt = "";
        img.src = src || this.inlineAvatar(title);
        const text = this.el("div", "name-cell");
        text.appendChild(this.el("strong", "", title));
        text.appendChild(this.el("small", "", subtitle));
        wrap.appendChild(img);
        wrap.appendChild(text);
        return wrap;
    },

    inlineAvatar(seed) {
        const label = encodeURIComponent(String(seed || "BC").slice(0, 2).toUpperCase());
        return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='76' height='76'%3E%3Crect width='76' height='76' rx='38' fill='%2300a8d8'/%3E%3Ctext x='38' y='45' text-anchor='middle' font-family='Arial' font-size='22' font-weight='700' fill='white'%3E${label}%3C/text%3E%3C/svg%3E`;
    },

    resourceCard({ checkbox = null, title, meta, desc, actions = [] }) {
        const item = this.el("article", "resource-item");
        item.appendChild(checkbox || this.el("span"));
        const body = this.el("div");
        body.appendChild(this.el("span", "resource-title", title));
        body.appendChild(this.el("span", "resource-meta", meta || ""));
        body.appendChild(this.el("span", "resource-desc", desc || ""));
        const actionWrap = this.el("div", "resource-actions");
        actions.forEach((action) => actionWrap.appendChild(action));
        item.appendChild(body);
        item.appendChild(actionWrap);
        return item;
    },

    td(content) {
        const cell = document.createElement("td");
        if (content instanceof Node) cell.appendChild(content);
        else cell.textContent = String(content);
        return cell;
    },

    el(tag, className = "", text = "") {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== "") node.textContent = text;
        return node;
    },

    emptyNode(message) {
        return this.el("p", "empty-state", message);
    },

    renderEmpty(id, message) {
        const node = document.getElementById(id);
        node.replaceChildren();
        if (node.tagName === "TBODY") {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 6;
            cell.appendChild(this.emptyNode(message));
            row.appendChild(cell);
            node.appendChild(row);
        } else {
            node.appendChild(this.emptyNode(message));
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    app.init();
});
