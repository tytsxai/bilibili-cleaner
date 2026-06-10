# Bilibili Cleaner · 哔哩哔哩账号清理工具 / Self-hosted Bilibili Account Cleaner

**Bilibili Cleaner** 是一个开源、自托管的 B 站账号清理工具。它提供 Web UI、FastAPI HTTP API 和 Python CLI，帮助用户在自己的电脑上检查并清理个人哔哩哔哩账号数据，包括批量取关、清理收藏夹、删除动态、清空观看历史，以及基于 API/CLI 的选择性清理工作流。

**Bilibili Cleaner is an open-source, self-hosted toolkit for inspecting and cleaning a Bilibili account.** It runs locally with a FastAPI backend, plain HTML/CSS/JS frontend, Typer CLI, OpenAPI schema, rate limiting, retry handling, and async tasks for long-running cleanup jobs.

[![CI](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/tytsxai/bilibili-cleaner)](https://github.com/tytsxai/bilibili-cleaner/releases)

[English README](README.en.md) · [API 文档](docs/API.md) · [FAQ](docs/FAQ.md) · [llms.txt](llms.txt) · [Changelog](CHANGELOG.md) · [Issues](https://github.com/tytsxai/bilibili-cleaner/issues)

## 项目定位 / What It Is

| 项目属性 | 说明 |
|---|---|
| 项目类型 / Type | 开源 Bilibili 账号清理工具、个人数据清理 API、CLI 自动化工具 |
| 解决问题 / Problem | B 站关注、收藏、动态、观看历史长期堆积，手动清理成本高，第三方闭源工具不透明 |
| 适合用户 / Audience | 想清理个人 B 站账号的用户、账号注销前整理数据的用户、需要 API/CLI 自动化的开发者和 AI Agent |
| 技术栈 / Stack | Python 3.10+、FastAPI、httpx、Typer、Pydantic、原生 HTML/CSS/JavaScript、Docker Compose |
| 运行方式 / Runtime | 本地 Python、Docker、自托管服务；默认端口 `8000` |
| 数据流向 / Data Flow | 登录凭证保存在本地，API 请求从你的机器直接访问 bilibili.com，不经过第三方服务器 |

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

## 重要限制 / Limitations

- **所有删除不可恢复**：B 站没有回收站，批量删除前请先用列表接口或 Web UI 确认。
- **不支持删除自己发过的评论**：B 站没有可靠的“列出我发过的评论”公开接口。
- **不清理私信、粉丝、追番、稍后再看**：当前功能范围不包含这些数据。
- **B 站没有批量取关接口**：项目会逐个调用取关接口，并默认在同一服务进程内共享约 `1.5 req/s` 限流。
- **大量操作可能触发风控**：遇到 `-352`、`-799`、HTTP `412/429` 时会自动重试；仍失败时应暂停一段时间。
- **任务状态保存在内存中**：服务进程重启会丢失 `/api/v2/tasks/*` 的任务进度，已完成任务只保留最近一批用于排障。
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

如果 `8000` 端口被占用，修改 [docker-compose.yml](docker-compose.yml) 中的端口映射，例如把 `"8000:8000"` 改成 `"8080:8000"`。

### 方式二：Python 本地运行

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner

python3 -m venv .venv
source .venv/bin/activate

pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

启动后访问：

- Web UI: `http://localhost:8000`
- Swagger / OpenAPI UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Web UI 使用流程

1. 启动服务并打开 `http://localhost:8000`。
2. 使用哔哩哔哩 App 扫描页面二维码。
3. 手机端确认登录后，页面会显示当前 UID。
4. 选择清理关注、收藏、动态、历史，或执行“一键清理所有”。
5. 操作前会二次确认；关注、收藏、动态和一键清理会提交后台任务并轮询真实进度，历史清理是单次同步调用。
6. 完成后点击“退出登录”，清除浏览器 localStorage 中的登录凭证。

Web UI 适合快速清空；如果要先筛选、复核、分批删除，优先使用 CLI 或 `/api/v2/*` API。

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
- Web UI 将 `SESSDATA` 和 `bili_jct` 存在浏览器 localStorage；不要在公共电脑上使用。
- CLI 凭证默认保存在 `~/.bilibili-cleaner/credentials.json`。
- 后端对 B 站写操作带 `bili_jct` 作为 CSRF 参数。
- 日志输出使用 `textContent` 写入，降低前端日志 XSS 风险。
- 代码开源，建议在执行大规模删除前先阅读代码和 API 文档。

## 项目结构 / Repository Layout

```text
bilibili-cleaner/
├── AGENTS.md                 # AI Agent 编排入口
├── README.md                 # 中文主文档
├── README.en.md              # English README
├── llms.txt                  # AI search / LLM-friendly project summary
├── docs/
│   ├── API.md                # HTTP API + CLI reference
│   └── FAQ.md                # FAQ and troubleshooting
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

## GitHub Topics 建议

如果你维护此仓库，建议在 GitHub Topics 中添加：

```text
bilibili, bilibili-cleaner, b站, 哔哩哔哩, account-cleanup, privacy-tool,
fastapi, typer, cli-tool, self-hosted, openapi, ai-agent, data-cleanup
```

## SEO / GEO 关键词说明

本项目相关的自然搜索词包括：B 站清理工具、哔哩哔哩批量取关、Bilibili bulk unfollow、清空 B 站收藏夹、删除 B 站动态、清空 Bilibili watch history、B 站账号注销前数据清理、Bilibili account cleanup、self-hosted Bilibili cleaner、Bilibili API CLI。

这些关键词描述的是项目真实能力，不代表官方背书或与哔哩哔哩存在关联。

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
