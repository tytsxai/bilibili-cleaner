# Bilibili Cleaner · One-Click Bilibili Account Cleanup Tool

> **Keywords**: bilibili cleaner, bulk unfollow bilibili, clear bilibili favorites, delete bilibili dynamics, wipe bilibili watch history, bilibili account wipe, delete bilibili account data, bilibili pre-deletion cleanup, B站清理工具, 哔哩哔哩批量清理

[![CI](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](tests/)

[简体中文](README.md) · [llms.txt](llms.txt) · [Changelog](CHANGELOG.md)

**Bilibili Cleaner** is an open-source, self-hosted web tool that wipes a Bilibili (B 站) account in a single click: bulk-unfollow everyone, empty every favorite folder, delete every dynamic (post), and clear the watch history. It runs entirely on your own machine — login by scanning a QR code with the Bilibili mobile app, and every API call goes directly from your computer to bilibili.com.

## Why use it

- You're about to delete a Bilibili account and want a clean slate first
- You're consolidating a side / "小号" account
- You're handing the account to someone else and need to wipe history first
- You want to scrub years of clutter without sitting through 5,000 manual clicks

## Features

| Feature | Description |
|---|---|
| 🔐 QR-code login | Scan with the Bilibili mobile app — no password required |
| 👥 Bulk unfollow | Pulls your entire following list and unfollows one by one |
| ⭐ Empty favorites | Walks every favorite folder and batch-deletes videos |
| 📝 Delete every dynamic | Text, repost, opus (image+text), video — all supported |
| 🕐 Wipe watch history | Clears the full watch history in one call |
| 🚀 One-click "Clean Everything" | Runs all four operations sequentially |
| 🌓 Light / dark theme | Follows the system or toggle manually |
| 📋 Live execution log | Real-time progress + results in the browser |

## Quick Start

### Option A — Docker (recommended)

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner
docker compose up -d
```

Open `http://localhost:8000` in your browser. To stop:

```bash
docker compose down
```

> Port 8000 in use? Edit `docker-compose.yml` and change `"8000:8000"` to e.g. `"8080:8000"`.

### Option B — Python locally

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## How to use

1. Start the service and open `http://localhost:8000`.
2. Open the Bilibili mobile app → tap the scan icon → scan the QR code on the page.
3. Confirm "登录" on your phone. The page jumps to the control console showing your UID.
4. Click the **执行** button next to any cleanup category, or **一键清理所有** for everything.
5. Watch the live log on the right for progress and totals.
6. Click **退出登录** when done to wipe credentials from your browser.

## FAQ

**Q: Is my account at risk?**
Credentials (`SESSDATA`, `bili_jct`) live only in your browser's localStorage. Every API call is direct from your machine to bilibili.com. Code is open-source and auditable. Click "退出登录" when finished.

**Q: How fast is the cleanup?**
Operations are throttled at ~1–3 requests/sec to avoid 风控 (rate-limit). A few hundred items usually finish in a few minutes.

**Q: Can I close the browser tab while it's running?**
No. Requests are issued by the frontend; closing the tab cancels them. Keep the tab open.

**Q: Can I recover what I deleted?**
No. All operations are permanent. Bilibili has no recycle bin. Double-check before clicking.

**Q: Will my account be banned?**
This calls the same Web APIs that the official site uses, so a ban is unlikely. Heavy rapid use may trigger temporary rate-limiting (not a ban) — wait 10–30 minutes and retry.

**Q: Why isn't there a "delete my comments" feature?**
Bilibili does not expose a public API to list comments you posted (only "comments on your stuff"). The previous v1.0 attempt was misleading and was removed in v1.1.0.

**Q: Does it work on Windows / macOS / Linux?**
All three. Docker Desktop is the simplest path; Python 3.10+ works directly.

**Q: Can I use this on someone else's account?**
No. Only the account that scanned the QR code is touched.

## What this tool does NOT do

- Delete comments you posted (no Bilibili API for that)
- Touch private messages, fans list, 追番 (bangumi follows), or 稍后再看 (watch-later)
- Operate multiple accounts simultaneously
- Send your data to any third-party server

## API surface

A FastAPI Swagger spec is available at `http://localhost:8000/docs` after starting. Endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/qrcode` | GET | Issue a login QR code |
| `/api/qrcode/poll/{key}` | GET | Poll QR scan status |
| `/api/clean/followings` | POST | Unfollow everyone |
| `/api/clean/favorites` | POST | Empty all favorites |
| `/api/clean/dynamics` | POST | Delete all dynamics |
| `/api/clean/history` | POST | Wipe watch history |
| `/api/clean/all` | POST | Run all four |

## Acknowledgments

- [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect) — Bilibili API reference
- [nemo2011/bilibili-api](https://github.com/nemo2011/bilibili-api) — Dynamic / WBI signature reference
- [FastAPI](https://fastapi.tiangolo.com/)

## Disclaimer

For personal account data cleanup only. All operations are irreversible. Use at your own risk and comply with Bilibili's terms of service. This project is not affiliated with Bilibili.

## License

MIT © 2024–2026 — see [LICENSE](LICENSE).
