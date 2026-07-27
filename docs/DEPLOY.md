# 部署与运维 / Deploy and Operate

面向"要长期跑在一台自己的机器或 VPS 上"的场景。开发用法见 [README](../README.md)。

## 1. 部署前必须知道的三件事

1. **服务本身没有登录认证。** 凭据（`SESSDATA` / `bili_jct`）由调用方逐请求传入，服务不校验调用方身份。
   **任何能访问这个端口的人都能用它向 B 站发请求。** 因此默认只监听 `127.0.0.1`。
2. **必须单进程运行（`--workers 1`）。** 任务状态存在进程内存里。加到 2 个 worker 后，
   `POST .../clear` 可能落在 A 进程，而随后的 `GET /api/v2/tasks/{id}` 落到 B 进程，直接返回 404，
   而删除还在后台继续执行。`Dockerfile` 里已经写死 `--workers 1`，不要改。
3. **所有删除不可撤销。** B 站没有回收站。审计日志（见下）是唯一的事后追溯依据。

## 2. 启动

### Docker Compose（推荐）

```bash
docker compose up -d --build
```

默认行为：

- 监听 `127.0.0.1:8000`，不对外暴露。
- 以非 root 用户（uid 10001）运行。
- 审计日志写入宿主机 `./data/audit.jsonl`。
- 容器健康检查每 30s 探一次 `/healthz`，失败 3 次标记 unhealthy。
- 容器日志 json-file，单文件 10MB × 3。
- `stop_grace_period: 30s`，给正在跑的清理任务留出收尾时间。

### 直接用 uvicorn

```bash
pip install -r backend/requirements.txt -c constraints.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

## 3. 配置

全部通过环境变量，前缀 `BILI_`。无需配置文件，缺省值可直接上线。
非法值（比如 `BILI_API_QPS=abc`）会回退到默认值而不是崩溃。

| 变量 | 默认 | 说明 |
|------|------|------|
| `BILI_API_QPS` | `1.5` | 全进程共享的 B 站请求速率上限。**调高会显著提升触发风控概率。** |
| `BILI_HTTP_TIMEOUT` | `10.0` | 单次 B 站请求超时（秒）。 |
| `BILI_MAX_RETRIES` | `3` | 风控响应的重试次数（合计最多 4 次请求）。 |
| `BILI_RETRY_BASE_DELAY` | `1.0` | 指数退避基数（秒），上限 30s。 |
| `BILI_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR`。 |
| `BILI_LOG_REQUESTS` | `1` | 是否逐请求记录 method/path/status/耗时。 |
| `BILI_MAX_RUNNING_TASKS` | `4` | 并发任务上限，超出返回 429。 |
| `BILI_MAX_FINISHED_TASKS` | `200` | 保留的已完成任务条数。 |
| `BILI_MAX_TASK_ERRORS` | `200` | 单任务保留的错误明细条数（总数仍记在 `error_count`）。 |
| `BILI_SHUTDOWN_GRACE_SECONDS` | `5.0` | 关停时等待任务收尾的秒数。 |
| `BILI_AUDIT_LOG_ENABLED` | `1` | 是否记录删除审计。 |
| `BILI_AUDIT_LOG_PATH` | `data/audit.jsonl` | 审计日志路径。 |

CLI 另有 `BILI_SESSDATA` / `BILI_JCT` / `BILI_CREDENTIALS_PATH`，见 [API.md](API.md)。

复制 [.env.example](../.env.example) 为 `.env` 即可被 docker compose 自动加载。

## 4. 健康检查

| 端点 | 用途 | 语义 |
|------|------|------|
| `GET /healthz` | 存活探针 | 恒返回 200 + uptime。不通说明 event loop 卡死，应重启。 |
| `GET /readyz` | 就绪 / 容量探针 | 任务队列满时返回 **503**，否则 200。 |

两者都不需要认证，也**不会**调用 B 站接口——探针如果打 B 站，会占用限流额度并可能自己触发风控。

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
```

## 5. 日志

统一输出到 stdout，格式：

```
2026-07-28T00:18:20+0800 INFO     backend.main [4ee9b3f8f1f4] GET /api/v2/tasks -> 401 in 1ms
```

方括号里是 **request id**。每个响应都带 `X-Request-ID` 响应头；也可以由调用方通过
`X-Request-ID` 请求头传入，便于和上游网关串起来。

排障常用：

```bash
docker compose logs -f app
docker compose logs app | grep -E "WARNING|ERROR"
```

`/healthz` 与 `/readyz` 不记访问日志（探针会淹没日志）。

## 6. 审计日志与恢复

每次删除都会往 `data/audit.jsonl` 追加一行 JSON：

```json
{"ts": 1785000000.1, "action": "following.unfollow", "target": 12345, "ok": true}
```

`action` 取值：`following.unfollow`、`favorite.delete`、`dynamic.delete`、`history.delete`、`history.clear`。
文件按 5MB × 5 份自动轮转。

**这是唯一的"删了什么"的记录。** B 站不支持撤销，所以恢复只能是人工的：

```bash
# 取出一次误操作里被取关的所有 mid
jq -r 'select(.action=="following.unfollow" and .ok==true) | .target' data/audit.jsonl
```

拿到 mid 列表后，可以用 `POST /api/v2/followings/...` 相关接口或 CLI 重新关注。
收藏夹和动态**无法**用 mid/id 重建内容，审计日志只能证明删了什么，不能还原。

备份：审计日志是唯一有状态的数据，`data/` 目录纳入常规备份即可。服务本身无数据库、无状态。

## 7. 关停与回滚

### 正常关停

```bash
docker compose stop        # 发 SIGTERM，等待 stop_grace_period
```

收到 SIGTERM 后服务会取消所有在跑的任务，把状态标成 `cancelled` 并落日志，
而不是让任务永远停在 `running`。已经删掉的数据不会回滚——只是不再继续删。

### 回滚到上一版本

服务无状态、无数据库迁移，回滚就是换镜像：

```bash
git checkout <上一个 tag 或 commit>
docker compose up -d --build
curl -fsS http://127.0.0.1:8000/healthz
```

注意：**回滚会丢失内存中的任务状态**（本来重启就会丢）。回滚前先确认没有正在跑的清理：

```bash
curl -fsS http://127.0.0.1:8000/readyz   # running_tasks 应为 0
```

## 8. 暴露到公网（如果确实需要）

默认不建议。若必须：

1. 前面放反向代理（Caddy / Nginx），由代理提供 **TLS** 和 **认证**（Basic Auth 或 SSO）。
2. compose 端口保持 `127.0.0.1:8000:8000`，让代理走 loopback 连接。
3. 不要把 `/api/*` 直接开给公网——它可以代打 B 站请求。

## 9. 上线前检查清单

```bash
ruff check .                                        # lint
pytest tests/ -q                                    # 测试
pip install -r backend/requirements.txt -c constraints.txt   # 依赖按 pin 装得上
docker compose up -d --build
curl -fsS http://127.0.0.1:8000/healthz             # 200
curl -fsS http://127.0.0.1:8000/readyz              # 200
docker compose exec app id -u                       # 非 0
docker compose logs app | head -20                  # 启动参数是否符合预期
```
