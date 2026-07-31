# Bilibili Cleaner · 哔哩哔哩账号清理工具 / Self-hosted Bilibili Account Cleaner

**Bilibili Cleaner** 是一个开源、自托管的 B 站账号清理工具。它提供 Web UI、FastAPI HTTP API 和 Python CLI，帮助用户在自己的电脑上检查并清理个人哔哩哔哩账号数据，包括批量取关、清理收藏夹、删除动态、清空观看历史，以及基于 API/CLI 的选择性清理工作流。

**Bilibili Cleaner is an open-source, self-hosted toolkit for inspecting and cleaning a Bilibili account.** It runs locally with a FastAPI backend, plain HTML/CSS/JS frontend, Typer CLI, OpenAPI schema, rate limiting, retry handling, and async tasks for long-running cleanup jobs.

[![CI](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/tytsxai/bilibili-cleaner)](https://github.com/tytsxai/bilibili-cleaner/releases)

[English README](README.en.md) · [文档总览](docs/README.md) · [API 文档](docs/API.md) · [FAQ](docs/FAQ.md) · [llms.txt](llms.txt) · [Changelog](CHANGELOG.md) · [Issues](https://github.com/tytsxai/bilibili-cleaner/issues)

## 一句话定位 / TL;DR

**Bilibili Cleaner = 本地运行的 B 站账号清理工作台。** 它把“列出账号数据 → 本地筛选 → 人工复核 → 选择性删除”的流程做成 Web UI、HTTP API 和 CLI，适合清理自己的关注、收藏夹、动态和观看历史，也适合开发者或 AI Agent 通过 OpenAPI 编排安全的批量清理任务。

English: **Bilibili Cleaner is a local-first, self-hosted Bilibili account cleanup toolkit** for users, developers, scripts, and AI agents that need structured listing, enrichment, review, selective deletion, and async task polling.

## 目录 / Contents

- [项目定位 / What It Is](#项目定位--what-it-is)
- [核心功能 / Core Features](#核心功能--core-features)
- [适用场景 / Use Cases](#适用场景--use-cases)
- [重要限制 / Limitations](#重要限制--limitations)
- [快速开始 / Quick Start](#快速开始--quick-start)
- [Web UI 使用流程](#web-ui-使用流程)
- [CLI 用法 / Command Line](#cli-用法--command-line)
- [HTTP API / AI Agent 接入](#http-api--ai-agent-接入)
- [推荐工作流 / Recommended Workflow](#推荐工作流--recommended-workflow)
- [安全与隐私 / Security and Privacy](#安全与隐私--security-and-privacy)
- [部署与运维 / Deploy and Operate](#部署与运维--deploy-and-operate)
- [常见问题 / FAQ](#常见问题--faq)

## 项目定位 / What It Is

| 项目属性 | 说明 |
|---|---|
| 项目类型 / Type | 开源 Bilibili 账号清理工具、个人数据清理 API、CLI 自动化工具 |
| 解决问题 / Problem | B 站关注、收藏、动态、观看历史长期堆积，手动清理成本高，第三方闭源工具不透明 |
| 适合用户 / Audience | 想清理个人 B 站账号的用户、账号注销前整理数据的用户、需要 API/CLI 自动化的开发者和 AI Agent |
| 技术栈 / Stack | Python 3.10+、FastAPI、httpx、Typer、Pydantic、原生 HTML/CSS/JavaScript、Docker Compose |
| 运行方式 / Runtime | 本地 Python、Docker、自托管服务；默认端口 `8000` |
| 数据流向 / Data Flow | 登录凭证保存在本地，API 请求从你的机器直接访问 bilibili.com，不经过第三方服务器 |

## 文档阅读路径 / Reading Path

| 你想做什么 | 优先阅读 |
|---|---|
| 先判断项目是否适合自己 | 本 README 的“项目定位”“核心功能”“重要限制” |
| 快速启动 Web UI | [快速开始](#快速开始--quick-start) |
| 用脚本或 Agent 接入 | [docs/API.md](docs/API.md)、[openapi.json](openapi.json)、[llms.txt](llms.txt) |
| 排查登录、限流、风控、任务状态 | [docs/FAQ.md](docs/FAQ.md) |
| 了解文档体系和维护入口 | [docs/README.md](docs/README.md) |

## 核心功能 / Core Features

- **扫码登录 / QR-code login**：使用哔哩哔哩 App 扫码登录，不需要输入账号密码。
- **关注清理 / Bulk unfollow**：列出关注列表，支持全部取关、指定 `mid` 取关、异步取关任务。
- **关注质量筛选 / Following audit**：可拉取 UP 主资料、粉丝数、投稿列表和最新视频，用于本地规则筛选。
- **收藏夹清理 / Favorites cleanup**：列出收藏夹和收藏内容，支持按资源选择删除或清空收藏夹内容。
- **动态清理 / Dynamic deletion**：支持列出并删除动态，包含新版图文 `opus` 动态的 WBI 签名拉取。
- **观看历史清理 / Watch history cleanup**：支持分页查看观看历史、删除单条历史、清空全部历史。
- **关注分组安全复核 / Review tag workflow**：可先把候选 UP 加入 B 站关注分组，人工确认后再取关。
- **异步任务 / Async tasks**：长时间批量操作返回 `task_id`，通过 `/api/v2/tasks/{id}` 查询进度和错误。
- **CLI 与 OpenAPI / CLI and OpenAPI**：`bilibili-cleaner` 命令行与 HTTP API 共享同一服务层，适合脚本、Agent 和自动化流程。

## 适用场景 / Use Cases

- B 站账号注销或停用前，清理个人关注、收藏、动态和观看历史。
- 小号、测试号或多年未整理账号的批量清理。
- 不想把 Cookie 或账号凭证交给第三方工具，希望本地自部署、可审计。
- 先导出列表并按规则筛选，例如“半年未更新且粉丝数较低的关注账号”。
- 给 AI Agent、脚本或内部工具提供稳定的 Bilibili 账号清理 API。

## 与其他清理方式对比 / Comparison

| 方案 | 适合场景 | 主要风险或限制 |
|---|---|---|
| 手动在 B 站网页/App 删除 | 少量内容、偶尔整理 | 点击成本高，难以按规则筛选和复核 |
| 浏览器脚本或临时脚本 | 单一页面、一次性操作 | 可维护性和风控处理通常较弱，接口变化后容易失效 |
| 闭源第三方清理工具 | 追求开箱即用 | 凭证流向不透明，难以审计实际操作 |
| **Bilibili Cleaner** | 本地自托管、可审计、需要 API/CLI/Agent 工作流 | 需要自己启动服务；删除不可恢复；仍受 B 站接口和风控限制 |

## 重要限制 / Limitations

- **所有删除不可恢复**：B 站没有回收站，批量删除前请先用列表接口或 Web UI 确认。
- **不支持删除自己发过的评论**：B 站没有可靠的“列出我发过的评论”公开接口。
- **不清理私信、粉丝、追番、稍后再看**：当前功能范围不包含这些数据。
- **B 站没有批量取关接口**：项目会逐个调用取关接口，并默认在同一服务进程（同一 event loop）内共享约 `1.5 req/s` 限流。因此取关 1600 个账号大约需要 18 分钟。
- **大量操作可能触发风控**：遇到 `-352`、`-799`、`-509`、HTTP `412/429` 时会自动指数退避重试（3 次重试，合计最多 4 次请求）；仍失败时应暂停一段时间再继续。
- **任务状态保存在内存中**：服务进程重启会丢失 `/api/v2/tasks/*` 的任务进度；已完成任务默认只保留最近 200 条用于排障。
- **必须单进程运行**：任务状态在进程内存里，多 worker 会让 `GET /api/v2/tasks/{id}` 随机返回 404，而后台删除仍在继续。Docker 镜像已写死 `--workers 1`。
- **服务本身没有认证**：`SESSDATA` / `bili_jct` 是逐请求传入的 B 站凭据，不是本服务的登录凭据；能访问端口的人就能通过它请求 B 站。默认只监听 `127.0.0.1`，详见 [SECURITY.md](SECURITY.md)。
- **只操作当前登录账号**：不能也不应该用于他人账号。

## 快速开始 / Quick Start

### 方式一：Docker Compose

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner
docker compose up -d
```

浏览器打开：

```text
http://localhost:8000
```

停止服务：

```bash
docker compose down
```

如果 `8000` 端口被占用，修改 [docker-compose.yml](docker-compose.yml) 中的端口映射，例如把 `"127.0.0.1:8000:8000"` 改成 `"127.0.0.1:8080:8000"`。

默认只绑定 `127.0.0.1`：服务本身没有认证，能访问端口的人就能通过它向 B 站发请求。
需要远程访问时请在前面加带认证的反向代理，见 [docs/DEPLOY.md](docs/DEPLOY.md)。

删除操作会记录到宿主机 `./data/audit.jsonl`。B 站没有回收站，这是唯一的事后追溯依据。

### 方式二：Python 本地运行

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner

python3 -m venv .venv
source .venv/bin/activate

# -c constraints.txt 使用与镜像一致的固定版本；省略则按上下界解析最新可用版本
pip install -r backend/requirements.txt -c constraints.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

启动后访问：

- Web UI: `http://localhost:8000`
- Swagger / OpenAPI UI: `http://localhost:8000/docs`
- 存活探针 / Liveness: `http://localhost:8000/healthz`
- 就绪探针 / Readiness: `http://localhost:8000/readyz`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Web UI 截图 / Screenshots

Web UI 现在是一个可独立使用的本地清理控制台，不再只是“一键清空”入口。它适合普通用户在浏览器里完成扫码登录、列表预览、筛选候选、选择性删除、关注分组复核和异步任务进度查看；CLI、HTTP API 和 AI Agent 仍然共享同一套后端服务层，适合更高级的自动化流程。

界面默认深色，可在右上角切换浅色主题；侧边栏可折叠，工作区、指标卡和任务日志面板在窄屏下会自动重排。

> 截图使用脱敏演示数据，不包含真实账号 UID、昵称、Cookie 或清理记录。可用 `http://localhost:8000/?demo=1` 直接进入同样的演示模式。登录页截图中的二维码是指向本仓库的占位图，不是可用的登录二维码。

扫码登录页：

![Bilibili Cleaner login](docs/assets/web-login.png)

总览：

![Bilibili Cleaner Web dashboard](docs/assets/web-dashboard.png)

关注审计：

![Bilibili Cleaner following audit](docs/assets/web-followings-audit.png)

## Web UI 使用流程

1. 启动服务并打开 `http://localhost:8000`。
2. 使用哔哩哔哩 App 扫描页面二维码。
3. 手机端确认登录后，页面会显示当前 UID。
4. 在“关注审计、收藏夹、动态、观看历史”工作区加载列表并筛选候选项。
5. 对关注账号可先加入 `to-review` 分组，在 B 站 App 或网页中人工复核后再取关。
6. 对收藏、动态、观看历史执行选择性删除；大批量关注取关会创建异步任务并在右侧任务面板显示进度。
7. 完成后点击“退出登录”，清除本标签页的登录凭证。凭证存放在 `sessionStorage`，关闭标签页也会自动清除。

Web UI 适合可视化审计和人工确认；CLI 适合批处理脚本；`/api/v2/*` API 和 `openapi.json` 适合 AI Agent 或内部系统编排。三者互不冲突。

## CLI 用法 / Command Line

安装为本地可编辑包：

```bash
pip install -e .
bilibili-cleaner --help
```

扫码登录并保存凭证：

```bash
bilibili-cleaner auth login
bilibili-cleaner me
```

常用命令：

```bash
bilibili-cleaner followings list --with-detail
bilibili-cleaner followings all
bilibili-cleaner followings detail 12345
bilibili-cleaner followings unfollow 111 222 333

bilibili-cleaner tag create to-review
bilibili-cleaner tag add-users 111 222 --tag-name to-review

bilibili-cleaner favorites folders
bilibili-cleaner favorites items 9876
bilibili-cleaner dynamics list
bilibili-cleaner history list
```

CLI 默认输出 JSON，可用 `--pretty` 切换为更适合人工阅读的输出。凭证会保存到 `~/.bilibili-cleaner/credentials.json`，也可以通过环境变量提供：

```bash
export BILI_SESSDATA="..."
export BILI_JCT="..."
```

## HTTP API / AI Agent 接入

所有推荐接口都在 `/api/v2/*` 下。写操作需要请求头：

```text
SESSDATA: <your SESSDATA>
bili_jct: <your bili_jct>
Content-Type: application/json
```

常用接口：

| 资源 | 接口 |
|---|---|
| 当前账号 | `GET /api/v2/me` |
| UP 主资料 | `GET /api/v2/users/{mid}`、`GET /api/v2/users/{mid}/stat`、`GET /api/v2/users/{mid}/videos` |
| 关注 | `GET /api/v2/followings?mid=...&with_detail=true`、`POST /api/v2/followings/unfollow`、`POST /api/v2/followings/unfollow-task` |
| 收藏 | `GET /api/v2/favorites/folders`、`GET /api/v2/favorites/folders/{id}/items`、`POST /api/v2/favorites/folders/{id}/delete` |
| 动态 | `GET /api/v2/dynamics?mid=...`、`POST /api/v2/dynamics/delete` |
| 历史 | `GET /api/v2/history`、`POST /api/v2/history/delete`、`POST /api/v2/history/clear` |
| 关注分组 | `GET /api/v2/relation/tags`、`POST /api/v2/relation/tags`、`POST /api/v2/relation/tags/members` |
| 异步任务 | `GET /api/v2/tasks`、`GET /api/v2/tasks/{id}`、`DELETE /api/v2/tasks/{id}` |

完整示例见 [docs/API.md](docs/API.md)，机器可读版本见 [openapi.json](openapi.json)，AI 搜索和 Agent 摘要见 [llms.txt](llms.txt)。

## 推荐工作流 / Recommended Workflow

### 安全取关：先筛选，再分组复核，最后删除

1. `GET /api/v2/me` 获取自己的 `mid`。
2. 分页调用 `GET /api/v2/followings?mid=<mid>&with_detail=true` 获取关注列表和详情。
3. 在本地按粉丝数、最近投稿时间、签名、名称等规则筛选候选账号。
4. 调用 `POST /api/v2/relation/tags/members` 把候选账号加入 `to-review` 分组。
5. 在 B 站 App 或网页中人工复核该分组。
6. 调用 `POST /api/v2/followings/unfollow-task` 执行最终取关，并轮询 `/api/v2/tasks/{task_id}`。

这个流程比“一键全部取关”更适合长期使用的主账号。

## 安全与隐私 / Security and Privacy

- 本项目是本地运行工具，不提供托管服务。
- **服务本身没有认证**：`SESSDATA` / `bili_jct` 是逐请求传入的 B 站凭据。默认只绑定 `127.0.0.1`；要远程访问必须自己加带认证的反向代理。
- Web UI 将 `SESSDATA` 和 `bili_jct` 存在浏览器 `sessionStorage`（仅限当前标签页，关闭即清除）；旧版本遗留在 `localStorage` 的凭据会在加载时自动清理。
- CLI 凭证默认保存在 `~/.bilibili-cleaner/credentials.json`（保存时 `chmod 600`）。
- 服务端不落盘任何凭据，也不把凭据写进日志。
- 异步任务按创建者归属（凭据摘要），其他会话看不到也取消不了你的任务。
- 后端对 B 站写操作带 `bili_jct` 作为 CSRF 参数。
- 日志输出使用 `textContent` 写入，降低前端日志 XSS 风险。
- 容器以非 root 用户（uid 10001）运行。
- 代码开源，建议在执行大规模删除前先阅读代码和 API 文档。

完整威胁模型与凭据存放说明见 [SECURITY.md](SECURITY.md)。

## 部署与运维 / Deploy and Operate

上线、配置、健康检查、日志、审计与回滚的完整说明见 **[docs/DEPLOY.md](docs/DEPLOY.md)**。要点：

- 全部配置走 `BILI_` 前缀环境变量，可复制 [.env.example](.env.example) 为 `.env`。
- `GET /healthz` 存活探针，`GET /readyz` 就绪 / 容量探针（任务队列满时返回 503）。
- 每次删除写入 `data/audit.jsonl`，用于事后核对被删了什么。
- 收到 SIGTERM 会取消在跑的任务并标记状态，不会让任务永远停在 `running`。
- 服务无数据库、无迁移，回滚就是换镜像重启。

## 项目结构 / Repository Layout

```text
bilibili-cleaner/
├── AGENTS.md                 # AI Agent 编排入口
├── README.md                 # 中文主文档
├── README.en.md              # English README
├── llms.txt                  # AI search / LLM-friendly project summary
├── docs/
│   ├── README.md             # 文档总览与阅读路径
│   ├── API.md                # HTTP API + CLI reference
│   ├── DEPLOY.md             # 部署、配置、健康检查、审计、回滚
│   └── FAQ.md                # FAQ and troubleshooting
├── SECURITY.md               # 威胁模型与凭据处理
├── .env.example              # 可复制为 .env 的运行配置
├── constraints.txt           # 部署用的固定依赖版本
├── openapi.json              # OpenAPI snapshot
├── backend/
│   ├── api/                  # Bilibili API wrappers, WBI, rate limit, retry
│   ├── services/             # Shared business layer for API and CLI
│   ├── routers/              # FastAPI v2 routers
│   ├── cli/                  # Typer CLI
│   └── main.py               # FastAPI app and legacy v1 endpoints
├── frontend/                 # Plain HTML/CSS/JS Web UI
├── tests/                    # pytest test suite
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## 开发 / Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .

pytest tests/ -v
python3 scripts/dump_openapi.py
```

提交 PR 前建议至少运行测试，并在接口变化后更新 `openapi.json` 和相关文档。

## 常见问题 / FAQ

**Bilibili Cleaner 是官方工具吗？**
不是。本项目与哔哩哔哩官方没有任何关联，调用的是 B 站公开 Web API，使用者需自行遵守平台规则。

**会不会把我的账号凭证上传到第三方服务器？**
不会。项目不提供托管服务。Web UI、后端和 CLI 都在你自己的机器上运行，请求从你的机器直接发往 bilibili.com。凭证保存在浏览器 `sessionStorage`（关闭标签页即清除）或 `~/.bilibili-cleaner/credentials.json`。

**会导致封号吗？**
项目默认以约 `1.5 req/s` 的低频调用接口并自动处理风控重试，正常使用更常见的是临时限流而不是封号。但任何批量自动化操作都存在平台风控风险，数据量大时建议分批执行。

**能删除我发过的评论吗？**
不能。B 站没有可靠的“列出我发过的所有评论”公开接口，无法安全定位并批量删除，因此项目不提供该功能。

**支持清理私信、粉丝、追番、稍后再看吗？**
当前不支持。项目范围是关注、收藏夹、动态和观看历史四类数据。

**能清理别人的账号吗？**
不能。只能操作当前扫码登录或凭证对应的账号。

**删除后还能恢复吗？**
不能。B 站没有回收站，所有删除不可恢复。建议先用列表接口导出并复核，再执行删除。

**为什么批量取关这么慢？**
B 站没有真正的批量取关接口，底层只能逐个 `fid` 调用，加上默认限流，取关 1600 个账号约需 18 分钟。

**该用 Web UI、CLI 还是 API？**
只想快速清空用 Web UI；想先筛选、复核、分批操作用 CLI；要让脚本或 AI Agent 编排用 `/api/v2/*` 配合 [openapi.json](openapi.json)。

更多排障内容（`-101` 登录失效、`-352` 风控、任务状态丢失等）见 [docs/FAQ.md](docs/FAQ.md)。

## Star History

如果这个项目对你有帮助，欢迎 star。Star History 用于观察开源关注度变化，不代表项目与哔哩哔哩官方存在任何关联。

<p align="center">
  <a href="https://star-history.com/#tytsxai/bilibili-cleaner&Date">
    <img src="https://api.star-history.com/svg?repos=tytsxai/bilibili-cleaner&type=Date" alt="Star History" width="760" />
  </a>
</p>

## 致谢 / Acknowledgments

- [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect) — B 站 API 参考。
- [nemo2011/bilibili-api](https://github.com/nemo2011/bilibili-api) — 动态和 WBI 签名参考。
- [FastAPI](https://fastapi.tiangolo.com/) — Web API 框架。

## 免责声明 / Disclaimer

本项目仅用于用户清理自己的哔哩哔哩账号数据。所有删除操作不可恢复，使用前请确认数据和账号归属，并遵守相关平台规则和法律法规。本项目与哔哩哔哩官方无关联。

## License

[MIT License](LICENSE) © 2024-2026
