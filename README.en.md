# Bilibili Cleaner · Self-hosted Bilibili Account Cleaner

**Bilibili Cleaner** is an open-source, self-hosted toolkit for inspecting and cleaning a Bilibili account. It provides a local Web UI, FastAPI HTTP API, Python CLI, OpenAPI schema, rate limiting, retry handling, and async tasks for long-running cleanup operations.

中文主文档: [README.md](README.md) · API reference: [docs/API.md](docs/API.md) · FAQ: [docs/FAQ.md](docs/FAQ.md) · LLM summary: [llms.txt](llms.txt)

## What It Solves

Cleaning a Bilibili account manually is slow: followings, favorites, dynamics, and watch history may require hundreds or thousands of clicks. Closed third-party tools also require trust. This project runs on your own machine and calls Bilibili Web APIs directly from your local environment.

## Who It Is For

- Users preparing to delete or retire a Bilibili account.
- Users cleaning a side account, test account, or old account.
- Developers who need a local API or CLI for Bilibili account cleanup workflows.
- AI agents that need structured listing, enrichment, selective action, and task polling endpoints.

## Core Features

- QR-code login with the Bilibili mobile app.
- List followings, enrich them with UP profile/stat/latest-video data, and unfollow selected `mid`s.
- Empty favorite folders or delete selected favorite resources.
- List and delete dynamics, including newer `opus` image-text dynamics via WBI-signed fetches.
- List, delete, or clear watch history.
- Manage Bilibili following groups for safe "tag first, review later, then unfollow" workflows.
- Async task queue for long-running batch operations.
- CLI command `bilibili-cleaner` and canonical `/api/v2/*` HTTP API.
- OpenAPI schema for tool integration and AI-agent consumption.

## Limitations

- Deleted data cannot be recovered.
- Bilibili has no reliable public API for "list comments I posted", so this project does not delete posted comments.
- Private messages, fans, bangumi follows, and watch-later are outside the current scope.
- Bilibili has no real batch-unfollow endpoint; this project unfollows one account at a time with a shared in-process rate limit.
- Task state is in memory. Restarting the service loses task progress, and finished task history is bounded.
- The tool only operates on the account that logged in.

## Quick Start

### Docker Compose

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner
docker compose up -d
```

Open:

```text
http://localhost:8000
```

Stop:

```bash
docker compose down
```

### Python

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner

python3 -m venv .venv
source .venv/bin/activate

pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Then open:

- Web UI: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

The Web UI submits async tasks for followings, favorites, dynamics, and
"clean all", then polls real task progress. Watch history clear is a single
synchronous Bilibili call.

## CLI

```bash
pip install -e .
bilibili-cleaner auth login
bilibili-cleaner me

bilibili-cleaner followings list --with-detail
bilibili-cleaner followings all
bilibili-cleaner followings unfollow 111 222 333

bilibili-cleaner favorites folders
bilibili-cleaner dynamics list
bilibili-cleaner history list
```

Credentials are stored at `~/.bilibili-cleaner/credentials.json` or can be provided through `BILI_SESSDATA` and `BILI_JCT`.

## API

Recommended endpoints are under `/api/v2/*`.

| Area | Endpoints |
|---|---|
| Identity | `GET /api/v2/me` |
| Users | `GET /api/v2/users/{mid}`, `/stat`, `/videos` |
| Followings | `GET /api/v2/followings`, `POST /api/v2/followings/unfollow`, `POST /api/v2/followings/unfollow-task` |
| Favorites | `GET /api/v2/favorites/folders`, `GET /api/v2/favorites/folders/{id}/items`, `POST /api/v2/favorites/folders/{id}/delete` |
| Dynamics | `GET /api/v2/dynamics`, `POST /api/v2/dynamics/delete` |
| History | `GET /api/v2/history`, `POST /api/v2/history/delete`, `POST /api/v2/history/clear` |
| Relation tags | `GET /api/v2/relation/tags`, `POST /api/v2/relation/tags`, `POST /api/v2/relation/tags/members` |
| Tasks | `GET /api/v2/tasks`, `GET /api/v2/tasks/{id}`, `DELETE /api/v2/tasks/{id}` |

Write requests require:

```text
SESSDATA: <your SESSDATA>
bili_jct: <your bili_jct>
Content-Type: application/json
```

See [docs/API.md](docs/API.md) for curl recipes and cookbook workflows.

## Privacy and Safety

This project is a local tool, not a hosted service. Web credentials are stored in browser localStorage, and CLI credentials are stored locally. API calls go from your machine to bilibili.com. Use it only for accounts you own, and review carefully before running destructive operations.

## Keywords

Bilibili account cleanup, Bilibili cleaner, Bilibili bulk unfollow, clear Bilibili favorites, delete Bilibili dynamics, clear Bilibili watch history, self-hosted privacy tool, FastAPI Bilibili API, Bilibili CLI, AI agent OpenAPI integration.

## Star History

If this project is useful to you, a star helps others discover it. Star History is only an open-source visibility signal and does not imply any affiliation with Bilibili.

<p align="center">
  <a href="https://star-history.com/#tytsxai/bilibili-cleaner&Date">
    <img src="https://api.star-history.com/svg?repos=tytsxai/bilibili-cleaner&type=Date" alt="Star History" width="760" />
  </a>
</p>

## License

MIT © 2024-2026. This project is not affiliated with Bilibili.
