# Bilibili Cleaner FAQ / 常见问题

本文补充 [README.md](../README.md) 和 [API.md](API.md)，面向第一次使用 Bilibili Cleaner 的用户、开发者和 AI Agent。

## 基础定位

### Bilibili Cleaner 是什么？

Bilibili Cleaner 是一个开源、自托管、本地运行的哔哩哔哩账号清理工具。它提供 Web UI、FastAPI HTTP API 和 Python CLI，可用于清理当前登录账号的关注、收藏夹、动态和观看历史。

English: Bilibili Cleaner is an open-source self-hosted Bilibili account cleanup toolkit with a local Web UI, FastAPI API, CLI, and OpenAPI schema.

### 它适合谁？

- 想在账号注销或停用前清理个人 B 站数据的用户。
- 想整理小号、测试号或旧账号的用户。
- 需要通过 API 或 CLI 自动化 Bilibili account cleanup 的开发者。
- 需要稳定、结构化工具接口的 AI Agent。

### 它是不是官方工具？

不是。本项目与哔哩哔哩官方没有关联。它调用的是 B 站 Web API，使用者需要自行承担操作后果并遵守平台规则。

## 安全与隐私

### 会不会把账号凭证上传到第三方服务器？

项目本身不提供托管服务。默认运行方式下，Web UI、后端和 CLI 都在你的本机或自托管环境中运行，请求从你的机器直接访问 bilibili.com。

Web UI 会把 `SESSDATA` 和 `bili_jct` 保存在浏览器 localStorage；CLI 会把凭证保存在 `~/.bilibili-cleaner/credentials.json`，除非你改用 `BILI_SESSDATA` 和 `BILI_JCT` 环境变量。

### 可以在公共电脑上使用吗？

不建议。凭证保存在本地浏览器或用户目录中。公共设备使用后必须退出登录、清理浏览器数据，并确认本地凭证文件已删除。

### 会导致封号吗？

项目按较低频率调用 B 站接口，并对常见风控响应做重试。正常使用通常更可能遇到临时限流，而不是封号。但任何自动化批量操作都存在平台风控风险，数据量大时应分批执行。

## 功能范围

### 支持清理哪些内容？

- 关注列表：全部取关、指定 `mid` 取关、异步任务取关。
- 收藏夹内容：列出收藏夹和资源，按资源删除或清空。
- 动态：列出并删除动态，包含新版图文 `opus` 动态。
- 观看历史：列出、删除单条、清空全部。
- 关注分组：创建、删除、添加成员、列出成员，适合安全复核。

### 为什么不能删除我发过的评论？

B 站没有可靠公开的“列出我发过的所有评论”的 API。没有完整列表就无法安全批量定位和删除评论，因此项目不提供“删除我的评论”功能。

### 是否支持私信、粉丝、追番、稍后再看？

当前不支持。README 中列出的功能范围才是项目当前能力。

### 能否清理别人账号？

不能。项目只能操作当前扫码登录或凭证对应的账号。不要尝试操作他人账号。

## 使用与排障

### 推荐用 Web UI、CLI 还是 API？

- 想在浏览器里预览、筛选、复核并选择性删除：使用 Web UI。
- 想批处理、导出 JSON、写脚本或长期自动化：使用 CLI。
- 想让脚本或 AI Agent 编排：使用 `/api/v2/*`、`openapi.json` 和 `llms.txt`。

Web UI、CLI 和 API 不是互斥关系。它们共享同一套后端服务层：Web UI 适合人工可视化确认，CLI/API 适合高级自动化和 Agent 编排。

### Web UI 的登录凭证保存在哪里？

扫码登录成功后，Web UI 会把 `SESSDATA` 和 `bili_jct` 保存在当前浏览器的 localStorage 中，用于后续向本地 FastAPI 服务发送请求头。点击“退出登录”会删除这份浏览器本地凭证。

不要在公共电脑或共享浏览器配置中使用 Web UI。如果必须使用，操作后请退出登录并清理浏览器数据。

### 为什么 Web UI 推荐先预览再删除？

B 站删除、取关、清空历史等操作没有项目侧的回滚能力。Web UI 默认把列表预览、筛选、勾选、二次确认和任务进度放在删除之前，是为了避免“一键误删”。

关注清理尤其建议先把候选账号加入 `to-review` 分组，在 B 站 App 或网页里人工复核后，再执行最终取关。

### 为什么批量取关比较慢？

B 站没有真正的批量取关接口，底层只能逐个 `fid` 调用。项目默认限流约 `1.5 req/s`，这是为了降低触发风控的概率。

### 看到 `-101` 怎么办？

`-101` 通常表示登录态失效。重新扫码登录，或更新 CLI / 环境变量中的 `SESSDATA` 和 `bili_jct`。

### 看到 `-352`、`-799`、HTTP `412` 或 `429` 怎么办？

这些通常是风控或限流。项目会自动重试几次；如果仍失败，停止批量操作，等待 10-30 分钟或更久后再继续。不要通过开多个客户端来绕过限流。

### 清理过程中可以关闭浏览器吗？

关注的大批量取关会通过 `/api/v2/followings/unfollow-task` 创建后端异步任务，关闭浏览器不会立刻取消任务，但你会失去当前页面上的实时进度视图。重新打开页面后可通过任务面板或 `/api/v2/tasks` 查看仍保存在内存中的任务。

收藏、动态和单条历史删除是即时请求。请求发出后请等待页面返回结果，不要在进行中关闭标签页。

### 服务重启后任务还在吗？

不在。`/api/v2/tasks/*` 使用进程内存保存任务状态，服务重启会丢失任务进度。

## 开发者与 AI Agent

### 最适合 AI Agent 的入口是什么？

先读 [AGENTS.md](../AGENTS.md)、[llms.txt](../llms.txt) 和 [docs/API.md](API.md)。机器可读 schema 是 [openapi.json](../openapi.json)。

### 推荐的安全删除流程是什么？

1. 先调用列表接口拿到完整数据。
2. 在本地做筛选和排序。
3. 对 100+ 项的写操作，先把候选对象加入 `to-review` 分组或输出 dry-run 列表。
4. 用户确认后再调用选择性删除接口。
5. 大批量操作使用异步任务并轮询状态。

### 修改 API 后需要更新什么？

如果接口、请求体或响应结构变化，应更新：

- `docs/API.md`
- `openapi.json`，通过 `python3 scripts/dump_openapi.py` 生成
- `README.md` 中的 API 概览
- 必要时更新 `llms.txt`

## 相关搜索词

B 站清理工具、哔哩哔哩账号清理、Bilibili Cleaner、Bilibili account cleanup、Bilibili bulk unfollow、哔哩哔哩批量取关、清空 B 站收藏夹、删除 B 站动态、清空观看历史、self-hosted Bilibili API、FastAPI Bilibili CLI。
