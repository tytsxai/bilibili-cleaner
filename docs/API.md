# Bilibili Cleaner API Reference / 哔哩哔哩账号清理 HTTP API 与 CLI

Bilibili Cleaner exposes a local FastAPI service and a Python CLI for
structured Bilibili account cleanup workflows: list first, enrich when
needed, filter locally, then run selective destructive actions. This
reference is the developer-facing companion to [`README.md`](../README.md),
[`llms.txt`](../llms.txt), and [`AGENTS.md`](../AGENTS.md).

All examples assume the server is running at `http://localhost:8000`
(`uvicorn backend.main:app`). The canonical machine-readable schema is
[`openapi.json`](../openapi.json).

中文定位：本文档用于开发者、脚本和 AI Agent 接入 Bilibili Cleaner，重点说明
`/api/v2/*` 接口、CLI 命令、鉴权方式、限流风控和安全清理工作流。

## Conventions

- All v2 endpoints are under `/api/v2/`. Earlier `/api/clean/*` paths are
  kept as v1 aliases (same behaviour).
- Write requests require headers `SESSDATA` and `bili_jct`. JSON bodies
  for endpoints that take one. The CLI does the same via local credential
  store.
- Response envelope on error:
  `{"error": "...", "code": <int|null>, "data": <any|null>}`.
- Rate limit: default 1.5 req/s shared by all `BiliApiClient` instances
  in the same server process / event loop. Auto-retry on risk-control
  codes (`-352`, `-799`, `-509`, HTTP 412/429) with exponential backoff
  and full jitter (3 retries, 4 attempts total, capped at 30s). Multiple
  OS processes have separate buckets, so extra workers trip risk control
  rather than adding throughput.
- For listings the response shape mirrors B 站's `data` field unless an
  explicit pydantic model documents otherwise — open `/docs` (Swagger)
  or [`openapi.json`](../openapi.json) for the exact shape.

## Auth flow

```bash
# 1. server side
curl http://localhost:8000/api/qrcode               # → {qrcode_key, image (base64 PNG)}
curl http://localhost:8000/api/qrcode/poll/$KEY     # poll until code==0 → SESSDATA / bili_jct in url

# 2. CLI side
bilibili-cleaner auth login                         # interactive QR; saves credentials
bilibili-cleaner me                                 # verify
```

Credentials persist at `~/.bilibili-cleaner/credentials.json` (override
with `$BILI_CREDENTIALS_PATH`) or via `$BILI_SESSDATA` + `$BILI_JCT` env
vars.

For curl examples, use a Bash/Zsh header array so both auth headers are
sent every time:

```bash
export BILI_SESSDATA="..."
export BILI_JCT="..."
AUTH=(-H "SESSDATA: $BILI_SESSDATA" -H "bili_jct: $BILI_JCT")
```

## Endpoint reference

> Authoritative schemas live in [`/openapi.json`](../openapi.json). Below
> are quick curl recipes.

### Identity

```bash
curl "${AUTH[@]}" http://localhost:8000/api/v2/me
# → {"isLogin": true, "mid": 12345, "uname": "tester", "raw": {…}}
```

### Users (any UP)

```bash
curl "${AUTH[@]}" http://localhost:8000/api/v2/users/12345
curl "${AUTH[@]}" http://localhost:8000/api/v2/users/12345/stat
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/users/12345/videos?page=1&page_size=1&order=pubdate'
```

`videos` returns `data.list.vlist[].pubdate` — use page_size=1 to cheaply
check "last upload time" for an activity filter.

### Followings

```bash
# list one page (basic)
curl "${AUTH[@]}" \
  'http://localhost:8000/api/v2/followings?mid=12345&page=1&page_size=50'

# list with enrichment (profile + stat + latest video)
curl "${AUTH[@]}" \
  'http://localhost:8000/api/v2/followings?mid=12345&with_detail=true&concurrency=3'

# inspect one UP
curl "${AUTH[@]}" http://localhost:8000/api/v2/followings/9999

# selective unfollow (sync; OK for small batches)
curl "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"mids":[101,102,103]}' \
  http://localhost:8000/api/v2/followings/unfollow

# selective unfollow (async; recommended >50 mids)
curl "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"mids":[…]}' \
  http://localhost:8000/api/v2/followings/unfollow-task
# → {"task_id": "abc…"}

# clear ALL (async)
curl -X POST "${AUTH[@]}" \
  'http://localhost:8000/api/v2/followings/clear?mid=12345'
```

### Favorites

```bash
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/favorites/folders?mid=12345'
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/favorites/folders/9876/items?page=1'
curl "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"resources":[{"id":111,"type":2},{"id":222,"type":2}]}' \
  http://localhost:8000/api/v2/favorites/folders/9876/delete
curl -X POST "${AUTH[@]}" 'http://localhost:8000/api/v2/favorites/clear?mid=12345'
```

### Dynamics

```bash
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/dynamics?mid=12345'
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/dynamics?mid=12345&offset=<from-prev>'
curl "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"ids":["100","101"]}' \
  http://localhost:8000/api/v2/dynamics/delete
curl -X POST "${AUTH[@]}" 'http://localhost:8000/api/v2/dynamics/clear?mid=12345'
```

### History

```bash
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/history?max_id=0&page_size=20'
curl -X POST "${AUTH[@]}" \
  'http://localhost:8000/api/v2/history/delete?kid=archive_12345'
curl -X POST "${AUTH[@]}" http://localhost:8000/api/v2/history/clear
```

### Relation tags (following groups)

```bash
curl "${AUTH[@]}" http://localhost:8000/api/v2/relation/tags
curl "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"name":"to-review"}' \
  http://localhost:8000/api/v2/relation/tags
curl "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"mids":[1,2,3],"tag_name":"to-review"}' \
  http://localhost:8000/api/v2/relation/tags/members
curl "${AUTH[@]}" 'http://localhost:8000/api/v2/relation/tags/5/users?page=1'
curl -X DELETE "${AUTH[@]}" http://localhost:8000/api/v2/relation/tags/5
```

### Tasks

```bash
curl "${AUTH[@]}" http://localhost:8000/api/v2/tasks
curl "${AUTH[@]}" http://localhost:8000/api/v2/tasks/<task_id>
curl -X DELETE "${AUTH[@]}" http://localhost:8000/api/v2/tasks/<task_id>
curl -X POST "${AUTH[@]}" \
  'http://localhost:8000/api/v2/tasks/clean-all?mid=12345'
```

Task state shape:
```json
{
  "task_id": "abc…",
  "kind": "followings.unfollow",
  "status": "running",
  "processed": 73,
  "total": 1600,
  "errors": [{"mid": 999, "type": "BiliApiError", "message": "…"}],
  "result": null,
  "started_at": 1715000000.0,
  "finished_at": null
}
```

Task state is in-memory and process-local. A restart loses running task
progress; only the most recent 200 finished tasks are retained so a
long-running service does not grow unboundedly. Treat `/api/v2/tasks/*`
as live progress reporting, not as a durable audit log — if you need a
permanent record of what was deleted, persist it on the caller side.

## Cookbooks

### Cookbook 1 — Unfollow UPs inactive for 6+ months with under 1000 followers

```bash
# 1. get my mid
MID=$(curl -s "${AUTH[@]}" http://localhost:8000/api/v2/me | jq -r '.mid')

# 2. dump all followings to a local JSON array.
# The CLI uses the same service layer; for pure HTTP, loop GET /followings pages until items < page_size.
bilibili-cleaner followings all --mid "$MID" --json > all-followings.json

# 3. for each mid: cheap "last upload" + follower count
for m in $(jq -r '.[].mid' all-followings.json); do
  STAT=$(curl -s "${AUTH[@]}" "http://localhost:8000/api/v2/users/$m/stat")
  VID=$(curl -s "${AUTH[@]}" "http://localhost:8000/api/v2/users/$m/videos?page=1&page_size=1")
  echo "$m $(jq -r '.follower' <<<"$STAT") $(jq -r '.list.vlist[0].pubdate // 0' <<<"$VID")"
done > scored.txt

# 4. filter locally (here: <1000 followers and last upload older than about 6 months)
CUTOFF=$(python3 - <<'PY'
import datetime
print(int((datetime.datetime.now() - datetime.timedelta(days=183)).timestamp()))
PY
)
awk -v cutoff="$CUTOFF" '$2 < 1000 && $3 < cutoff {print $1}' scored.txt > to-unfollow.txt

# 5. start async unfollow task
MIDS=$(jq -R . to-unfollow.txt | jq -sc 'map(tonumber)')
TASK=$(curl -s "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d "{\"mids\": $MIDS}" \
  http://localhost:8000/api/v2/followings/unfollow-task | jq -r .task_id)

# 6. poll
while :; do
  S=$(curl -s "${AUTH[@]}" "http://localhost:8000/api/v2/tasks/$TASK")
  jq -r '"\(.status) \(.processed)/\(.total)"' <<<"$S"
  [ "$(jq -r .status <<<"$S")" = "running" ] || break
  sleep 5
done
```

CLI equivalent (no jq required):

```bash
bilibili-cleaner followings all --json > all.json
bilibili-cleaner users stat 12345 # … etc, score externally
bilibili-cleaner followings unfollow $(cat to-unfollow.txt | tr '\n' ' ')
```

### Cookbook 2 — Audit one favorites folder and delete videos shorter than 60s

```bash
# 1. find the folder id
curl -s "${AUTH[@]}" "http://localhost:8000/api/v2/favorites/folders?mid=$MID" \
  | jq '.[] | {id, title}'

# 2. page through items collecting short ones
PAGE=1
> short.txt
while :; do
  DATA=$(curl -s "${AUTH[@]}" \
    "http://localhost:8000/api/v2/favorites/folders/9876/items?page=$PAGE&page_size=20")
  echo "$DATA" | jq -r '.medias[] | select(.duration < 60) | "\(.id) \(.type)"' >> short.txt
  COUNT=$(echo "$DATA" | jq '.medias | length')
  [ "$COUNT" -lt 20 ] && break
  PAGE=$((PAGE+1))
done

# 3. batch delete
RES=$(awk '{print "{\"id\":"$1",\"type\":"$2"}"}' short.txt | jq -sc .)
curl -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d "{\"resources\": $RES}" \
  http://localhost:8000/api/v2/favorites/folders/9876/delete
```

### Cookbook 3 — Two-phase safe unfollow with a "review" tag

```bash
# Phase 1: tag candidates
curl -s "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"mids":[1,2,3,4,5],"tag_name":"to-review"}' \
  http://localhost:8000/api/v2/relation/tags/members
# user audits via the B 站 app: 关注 → 分组 → to-review

# Phase 2: after manual confirmation, unfollow
TAG_ID=$(curl -s "${AUTH[@]}" http://localhost:8000/api/v2/relation/tags \
  | jq -r '.[] | select(.name=="to-review") | .tagid')
MIDS=$(curl -s "${AUTH[@]}" \
  "http://localhost:8000/api/v2/relation/tags/$TAG_ID/users?page=1&page_size=50" \
  | jq -c '[.[].mid]')
curl -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d "{\"mids\": $MIDS}" \
  http://localhost:8000/api/v2/followings/unfollow-task
```

## CLI reference (one-liners)

```bash
bilibili-cleaner auth login                         # QR code → save credentials
bilibili-cleaner auth logout                        # forget credentials
bilibili-cleaner me                                 # GET /api/v2/me

bilibili-cleaner users info <mid>
bilibili-cleaner users stat <mid>
bilibili-cleaner users videos <mid> --page-size 1

bilibili-cleaner followings list [--with-detail]
bilibili-cleaner followings all                     # stream all pages → JSON array
bilibili-cleaner followings detail <mid>
bilibili-cleaner followings unfollow <mid> ...
bilibili-cleaner followings clear --yes

bilibili-cleaner favorites folders
bilibili-cleaner favorites items <media_id>
bilibili-cleaner favorites delete <media_id> <aid> <aid> ...
bilibili-cleaner favorites clear --yes

bilibili-cleaner dynamics list
bilibili-cleaner dynamics delete <id> <id> ...
bilibili-cleaner dynamics clear --yes

bilibili-cleaner history list
bilibili-cleaner history delete <kid>
bilibili-cleaner history clear --yes

bilibili-cleaner tag list
bilibili-cleaner tag create <name>
bilibili-cleaner tag add-users <mid> ... --tag-name to-review
bilibili-cleaner tag list-users <tagid>
bilibili-cleaner tag delete <tagid>
```

All commands accept `--json` (default) or `--pretty`.

## OpenAPI / Swagger

Live, interactive docs at `http://localhost:8000/docs`. A committed
snapshot lives at [`openapi.json`](../openapi.json); regenerate with:

```bash
python3 scripts/dump_openapi.py
```
