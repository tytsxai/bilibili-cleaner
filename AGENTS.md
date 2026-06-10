# AGENTS.md — Bilibili Cleaner AI orchestration manual

This is the entry point for AI agents (Claude, Cursor, etc.) calling this
project. It is intentionally short — read this first, then drill into
[`docs/API.md`](docs/API.md) for the full reference and into
[`openapi.json`](openapi.json) for machine-readable schemas.

The project's design assumption is: **AI does the high-level reasoning
(filter rules, prioritisation, dry runs); this tool exposes the building
blocks reliably and cheaply.** Don't ask the project for "filter by
quality" — ask it for "list everything with detail" and apply the filter
yourself, then call the selective delete endpoint.

## What this project gives you

- A FastAPI HTTP service (`uvicorn backend.main:app`, default
  `localhost:8000`) and a Python CLI (`bilibili-cleaner …`) that share the
  same service layer.
- Authenticated reads/writes against the user's own Bilibili account.
- Global rate-limiting (1.5 r/s default) + automatic retry on `-352` /
  HTTP 412 risk-control responses.
- Async task queue for long-running batch operations (`POST …/clear` →
  `task_id`, then `GET /api/v2/tasks/{id}` to poll).

## Core mental model

```
listing endpoints  →  enrichment endpoints  →  selective action endpoints
GET …/followings        GET /users/{mid}…         POST …/unfollow {mids}
GET …/favorites/items   GET /users/{mid}/videos   POST …/folders/{id}/delete
GET …/dynamics                                    POST …/dynamics/delete
GET …/history
```

For 100s+ items, wrap actions in **async tasks** instead of synchronous
batch endpoints. Pattern:

```
POST /api/v2/followings/unfollow-task  body {"mids": [...]}   → {task_id}
GET  /api/v2/tasks/{task_id}                                  → {status, processed, total, errors, result}
```

Poll roughly every 5–10 seconds. Worst case for 1600 unfollows: ~18 min.

## Critical limits (don't ignore)

- **No batch unfollow on B 站's side.** `/x/relation/modify` only takes
  one `fid` at a time. The "batch" endpoints in this project loop with
  rate-limiting underneath.
- **Default rate is 1.5 req/s.** It is shared by all `BiliApiClient`
  instances inside the same server process / event loop. Multiple OS
  processes still have separate buckets, so don't scale workers to
  circumvent it — you'll trip risk control.
- **B 站 has no "list my comments" API.** Don't propose deleting the
  user's comments; it's not possible.
- **Watch history `clear` is a single call.** Other `/clear` endpoints
  are async tasks; `/api/v2/history/clear` returns immediately.
- **Credentials live in the request.** Send `SESSDATA` and `bili_jct` as
  HTTP headers (NOT cookies). 401 if missing.
- **Tasks are in-memory.** Process restart loses task state and progress.
  Finished task history is bounded to avoid long-running process growth.
  Acceptable for tasks under ~30 min.
- **All deletes are permanent.** B 站 has no undo. Always offer a dry-run
  list to the user before calling write endpoints with 100+ items.

## Recommended workflows

### A. Quality-based selective unfollow (the project's headline use case)

```
1. GET  /api/v2/me                                            → {mid}
2. GET  /api/v2/followings?mid={mid}&page=1&page_size=50      ← loop pages
3. For candidates of interest:
   GET /api/v2/followings/{target_mid}                        → {info, stat, latest_video, video_count}
4. Locally apply filters
   (e.g. follower < N, pubdate older than 180 days, sign contains keyword)
5. (Optional) Safety net:
   POST /api/v2/relation/tags/members {mids, tag_name: "review"}
6. POST /api/v2/followings/unfollow-task {mids: [...]}        → {task_id}
7. GET  /api/v2/tasks/{task_id}                               ← poll until status=completed
```

### B. Favorites audit

```
1. GET  /api/v2/favorites/folders?mid={mid}
2. For each folder:
   GET /api/v2/favorites/folders/{media_id}/items?page=1&page_size=20
3. Filter by upper.mid blacklist / duration / title keyword
4. POST /api/v2/favorites/folders/{media_id}/delete {resources: [{id, type}]}
```

### C. Safety-first unfollow with manual review

```
1. List + filter as in (A) but stop before deleting.
2. POST /api/v2/relation/tags     {name: "to-review"}         → {tagid}
3. POST /api/v2/relation/tags/members {mids, tagid}
4. Hand control back to the user: "I tagged 73 UPs in '关注分组 → to-review'.
   Open b23.tv in the app, audit them, then run /api/v2/followings/unfollow-task
   with the final list."
```

## Endpoint quick reference

| Concern | Listing | Detail | Mutation |
|---|---|---|---|
| Self | `GET /me` | — | — |
| Users | — | `GET /users/{mid}`, `/stat`, `/videos` | — |
| Followings | `GET /followings?mid` (+`with_detail`) | `GET /followings/{mid}` | `POST /followings/unfollow`, `/unfollow-task`, `/clear` |
| Favorites | `GET /favorites/folders`, `/folders/{id}/items` | — | `POST /folders/{id}/delete`, `/clear` |
| Dynamics | `GET /dynamics?mid&offset` | — | `POST /dynamics/delete`, `/clear` |
| History | `GET /history?max_id` | — | `POST /history/delete`, `/clear` |
| Tags | `GET /relation/tags`, `/tags/{id}/users` | — | `POST /relation/tags`, `/tags/members`, `DELETE /tags/{id}`, `PUT /tags/{id}` |
| Tasks | `GET /tasks` | `GET /tasks/{id}` | `DELETE /tasks/{id}`, `POST /tasks/clean-all` |

All v2 endpoints are under `/api/v2/`. v1 `/api/clean/*` endpoints are
preserved aliases.

## CLI mirror

Every HTTP endpoint has a CLI equivalent. CLI loads credentials from
`~/.bilibili-cleaner/credentials.json` (saved by `bilibili-cleaner auth login`)
or from `BILI_SESSDATA` / `BILI_JCT` env vars. Default output is JSON.

```
bilibili-cleaner me
bilibili-cleaner followings list --with-detail --page-size 50 | jq '...'
bilibili-cleaner followings detail 12345
bilibili-cleaner followings unfollow 11 22 33
bilibili-cleaner tag add-users 11 22 --tag-name to-review
```

## Error model

All errors come back as
```json
{"error": "message", "code": <bili_code_or_null>, "data": <raw_payload_or_null>}
```

HTTP status codes:
- `401` — missing `SESSDATA` / `bili_jct`
- `404` — task or resource not found
- `412` / `429` — risk control (the client auto-retries before surfacing)
- `502` — propagated B 站 API error
- `500` — unexpected

When you see `code == -101`, the session is invalid — instruct the user
to re-login. `code == -352` or `-799` means risk control; back off the
caller's pace (the client already retries with backoff).

## Code-level entry points (for direct embedding)

If you're embedding this in another Python project rather than calling
HTTP:

- `backend.api.client.BiliApiClient(sessdata=..., bili_jct=..., qps=1.5)`
- `backend.services.{FollowingService, FavoriteService, DynamicService, HistoryService, TagService}`
- `backend.services.tasks.task_registry`
- `backend.cli.main.app` — typer App if you want to embed the CLI itself

All service methods take an `on_item`/`on_batch` progress callback so you
can stream live updates instead of polling the task registry.
