# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [1.4.0] - 2026-07-28

Web UI 从"一排清空按钮"升级为本地账号清理控制台。后端接口无变化，CLI 与
`/api/v2/*` 的调用方不受影响。

### 新增

- **Web UI 控制台**：按关注审计 / 收藏夹 / 动态 / 观看历史分工作区，支持分页加载、
  按昵称・签名・粉丝数・最近投稿筛选、跨页选择后批量处理。
- **关注复核流程**：可先把候选 UP 加入 `to-review` 分组，在 B 站 App 或网页人工复核后再取关。
- **任务面板**：常驻显示后台任务的状态与进度，替代此前的阻塞式轮询。
- **脱敏演示模式**：用示例数据浏览完整界面，不需要登录，便于截图与试用。
- README 增加 Web UI 截图（使用脱敏演示数据，不含真实账号信息）。

### 修复

- **任务面板错误数显示为 0**：`GET /api/v2/tasks` 返回的是摘要，`errors` 已被截断，
  面板却在读 `errors.length`——一个失败 37 项的任务会显示成"0 个错误"。改用 `error_count`。
- **提前中止的清理在任务列表中不可见**：任务摘要此前整个丢弃 `result`，导致"提前放弃"
  和"正常完成"长得一模一样。摘要现在保留 `stopped_reason` 这一个字段（短字符串或小 dict），
  其余 `result` 内容照旧丢弃。
- **Web UI 凭据回退到 `localStorage`**：Web UI 重写基于 v1.3.0 之前的代码，覆盖了
  v1.3.0 的凭据处理。已重新应用——凭据存 `sessionStorage`（关标签页即清除），
  并在加载时清理旧版遗留在 `localStorage` 的凭据。
- 校正 README / README.en / FAQ 中与代码不符的 `localStorage` 说法；FAQ 中"需要长期
  可追溯记录请自行落库"改为指向 v1.3.0 起提供的删除审计日志。

## [1.3.0] - 2026-07-28

本版本包含两部分：此前开发但从未打过 tag 的 1.2.0（`/api/v2` 资源接口、Typer CLI、
异步任务队列），以及一轮面向生产环境的补强。**没有破坏性接口改动**，`/api/clean/*`
与 `/api/v2/*` 的既有调用方均不受影响。

由于 1.2.0 从未发布，其内容一并计入本版本。

### 新增：HTTP API v2、CLI 与任务队列（原 1.2.0）

- **`/api/v2/*` 资源接口**：按 `me` / `users` / `followings` / `favorites` / `dynamics` /
  `history` / `relation-tags` / `tasks` 分组，带 Pydantic schema 与 OpenAPI tag，
  支持"列出 → 筛选 → 选择性删除"而不只是一键清空。
- **`bilibili-cleaner` CLI**：基于 Typer，与 HTTP API 共用同一 service 层，默认输出 JSON。
  凭据支持环境变量或 `~/.bilibili-cleaner/credentials.json`。
- **异步任务队列**：长时间清理返回 `task_id`，通过 `GET /api/v2/tasks/{id}` 轮询进度；
  Web UI 也改为轮询任务而不是等待同步响应。
- **全局限流与风控重试**：进程内共享令牌桶（默认 1.5 req/s），对 `-352`、`-799`、`-509`、
  HTTP `412/429` 指数退避重试。
- **WBI 签名助手**：动态与用户接口统一走签名逻辑，失败时自动刷新密钥重试一次。
- **`openapi.json` 快照与 `AGENTS.md`**：供 AI Agent / 脚本编排使用。

### 生产就绪 / Production readiness

面向"上线并长期稳定运行"的一轮补强。

#### 修复
- **误报成功**：`clear_all` 在触发页数安全上限时会直接返回，看起来和"清理干净了"一模一样。
  现在返回 `stopped_reason: "page_limit"`，动态清理也补上了此前缺失的 `no_progress` 判定。
- **v1 `/api/clean/*` 恒返回 `success: true`**：即使逐项失败或提前中止也报成功。
  现在 `success` 反映实际是否清理完成，并新增 `errors` / `stopped_reason` 字段（增量字段，旧调用方不受影响）。
- **WBI 密钥每请求重取**：HTTP 层每个请求新建一个 client，导致每次签名调用都额外打一次 `/nav`，
  白白消耗限流额度并抬高风控概率。改为进程级缓存（TTL 1 小时）。
- **应用日志全部丢失**：root logger 没有 handler，`INFO` 被静默丢弃，`WARNING` 以上退化为
  无时间戳的 lastResort 输出。现在统一配置日志。

#### 新增
- `GET /healthz`（存活）与 `GET /readyz`（就绪 / 容量，任务队列满时返回 503）。两者都不调用 B 站接口。
- 请求日志中间件：记录 method / path / 状态码 / 耗时，并为每个请求生成 request id，
  通过 `X-Request-ID` 响应头返回，也接受调用方传入。
- **删除审计日志**：每次删除追加一行 JSON 到 `data/audit.jsonl`（可配置、可关闭、自动轮转）。
  B 站没有回收站，这是唯一的事后追溯依据。
- **优雅关停**：收到 SIGTERM 时取消在跑的任务并标记为 `cancelled`，不再让任务永远停在 `running`。
- **任务并发上限**（默认 4，超出返回 429）与**任务错误条数上限**（默认 200，总数记在新的 `error_count` 字段）。
- `GET /api/v2/tasks` 改为只返回摘要，不再携带全部 `errors` / `result`，避免大规模清理时响应体膨胀。
- `backend/settings.py`：所有可调项走 `BILI_` 前缀环境变量，非法值回退默认值。新增 `.env.example`。
- `constraints.txt`：部署用的固定依赖版本，使 `docker build` 可复现；`requirements.txt` / `pyproject.toml` 补上版本上界。
- 新增 `docs/DEPLOY.md`（部署、配置、健康检查、日志、审计恢复、关停回滚）与 `SECURITY.md`（威胁模型、凭据处理）。

#### 变更
- `/api/v2/tasks/*` 从"完全不校验"改为**按创建者归属**：任务记录 `SESSDATA` 的 SHA-256 摘要，
  查询 / 列表 / 取消只对同一凭据可见，其他凭据一律 404（返回 403 等于确认任务存在）。
  注册表内不保存可用凭据。
- **收藏夹清理补上"整页零进展"保护**，与关注 / 动态一致：某个收藏夹一条都删不掉时停下并返回
  `stopped_reason`，而不是继续遍历剩余收藏夹后报告清理成功。
- **`clean-all` 任务结果透出 `stopped_reason`**：任一资源提前中止都会记录在 `result.stopped_reason` 里，
  不再让任务以 `completed` 收尾却少删了东西。
- **统一出站客户端构造**（`_deps.build_client`）：此前 11 处内联构造 `BiliApiClient` 绕过了配置的
  timeout / 重试策略——恰好包括最需要它们的后台长任务。
- **Web UI 凭据改存 `sessionStorage`**（关标签页即清除），并在加载时清掉旧版遗留在 `localStorage` 的凭据。
- **Web UI 任务轮询加上上限**：总时长上限、连续失败上限，服务重启或网络中断时不再无限空转；
  错误数改用 `error_count`（`errors` 已被截断，用它会严重少报）。
- 进度回调从 `"object | None"` 改为真实的 `Callable` 类型（`backend/services/_progress.py`）。
- ruff 启用 `UP` 规则并完成 `typing.Mapping` → `collections.abc` 的现代化。
- Docker 镜像以非 root 用户（uid 10001）运行，内置 `HEALTHCHECK`，并写死 `--workers 1`
  ——任务状态在进程内存中，多 worker 会让任务查询随机 404。
- `docker-compose.yml` 默认绑定 `127.0.0.1:8000`（服务本身没有认证），
  增加 healthcheck、日志轮转、`stop_grace_period` 和 `./data` 卷。
- CI 增加 ruff lint、固定版本安装验证、Docker 构建 + 健康检查 + 非 root 校验。

### 文档
- 优化 README 首屏定位、阅读路径、使用场景和方案对比，提升传统搜索引擎与 AI 搜索引擎理解度。
- 新增 `docs/README.md` 文档总览，串联 README、API、FAQ、OpenAPI、llms 和 Agent 使用边界。
- 修正 `docs/API.md` 中 curl 鉴权示例和 cookbook 的可执行性，统一使用双请求头数组。
- 补充 `llms.txt` 的权威引用入口和机器可读摘要，并扩充 `pyproject.toml` 项目关键词。

## [1.1.1] - 2026-05-19

### 文档
- **新增英文 README** (`README.en.md`)：面向 GitHub 国际用户的完整英文版，含 Quick Start / FAQ / API 接口说明
- **新增 `llms.txt`**：为 ChatGPT / Claude / Perplexity / Gemini 等 AI 搜索引擎提供精炼项目索引
- **新增「适合谁用 / 使用场景」章节**：覆盖账号注销前清理、小号整理、账号转手、隐私清洁等场景
- **新增「与其它清理方案对比」表**：对比油猴脚本 / 第三方清理小程序 / 手动删除四种方案
- **README 顶部新增 Release / 英文 / llms.txt / Changelog 导航链接**

无代码改动，API 与运行行为与 1.1.0 完全一致。

## [1.1.0] - 2026-04-21

### 新增
- **WBI 签名支持**：动态列表接口 `/x/polymer/web-dynamic/v1/feed/space` 加入 WBI 签名，登录后也能稳定拉取全部动态，兼容新版 opus 图文动态
- **完整使用文档**：README 大幅扩充，新增 10 条 FAQ、图文使用教程、Docker / Python 双部署方式、安全说明、功能边界说明
- **CHANGELOG.md**：建立版本更新记录

### 修复
- **取消关注接口错误**：`/x/relation/batch/modify` 的 `act=2` 不被官方支持，改用单用户接口 `/x/relation/modify`
- **收藏批量删除 URL**：`/x/v3/fav/resource/batch/del` → `/x/v3/fav/resource/batch-del`（连字符）
- **动态列表稳定性**：补齐 `features`、`timezone_offset`、`platform`、`Referer` 等参数，避免返回空结果

### 移除
- **删除"清理评论"功能**：`/x/msgfeed/reply` 实际返回的是"回复我的"，并非用户自己发布的评论；B 站未开放"列出我发的评论"的公开接口，无法可靠实现，移除避免误导

### 致谢
- API 对齐参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)
- WBI 签名实现参考 [nemo2011/bilibili-api](https://github.com/nemo2011/bilibili-api)

## [1.0.0] - 2026-01-02

### 新增
- 首个正式版本
- 二维码扫码登录
- 批量取消关注 / 清空收藏 / 删除动态 / 清空历史
- 一键全部清理
- FastAPI 后端 + 原生 HTML/CSS/JS 前端
- Docker Compose 一键部署
- 单元测试（95%+ 覆盖率）

[1.4.0]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.1.1...v1.3.0
[1.1.1]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/tytsxai/bilibili-cleaner/releases/tag/v1.0.0
