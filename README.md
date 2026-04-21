# Bilibili Cleaner · B站账号一键清理工具

> **关键词**：B站清理工具 / 哔哩哔哩批量取关 / 清空B站收藏 / 删除B站动态 / 清空观看历史 / bilibili cleaner / B站注销前数据清理 / B站小号清理 / 一键清空B站

[![CI](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](tests/)

**Bilibili Cleaner** 是一个开源的 B 站（哔哩哔哩）账号快速清理工具，提供简洁的网页界面，帮你**一键批量取消关注、清空收藏夹、删除所有动态、清空观看历史**。适合账号注销前清理数据、小号整理、隐私数据清除等场景。

---

## 📑 目录

- [功能特性](#-功能特性)
- [效果预览](#-效果预览)
- [快速开始](#-快速开始)
  - [方式一：Docker 一键启动（推荐小白）](#方式一docker-一键启动推荐小白)
  - [方式二：Python 本地运行](#方式二python-本地运行)
- [使用教程（图文步骤）](#-使用教程图文步骤)
- [常见问题 FAQ](#-常见问题-faq)
- [安全说明](#-安全说明)
- [功能范围与已知限制](#-功能范围与已知限制)
- [项目结构](#-项目结构)
- [API 接口说明](#-api-接口说明)
- [开发与贡献](#-开发与贡献)
- [致谢](#-致谢)
- [免责声明](#-免责声明)
- [License](#-license)

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔐 **扫码登录** | 使用哔哩哔哩 App 扫描二维码安全登录，无需输入账号密码 |
| 👥 **批量取消关注** | 自动拉取全部关注列表并逐一取关 |
| ⭐ **批量清空收藏** | 遍历所有收藏夹并批量删除视频 |
| 📝 **批量删除动态** | 支持删除文字、转发、图文（opus）、视频等各类动态 |
| 🕐 **清空观看历史** | 一键清除全部观看记录 |
| 🚀 **一键全部清理** | 同时执行以上所有操作 |
| 🌓 **深色 / 浅色主题** | 跟随系统或手动切换 |
| 📋 **实时执行日志** | 前端实时显示每一步结果 |

---

## 🖼️ 效果预览

启动后访问 `http://localhost:8000` 即可看到 Web 界面：

**① 扫码登录页** — 手机 App 扫码，无需输密码

**② 清理控制台**

```
┌──────────────────────────────────────────┐
│  当前 UID: 12345678         [退出登录]   │
├──────────────────────────────────────────┤
│  清理关注    批量取消所有关注   [执行]   │
│  清理收藏    批量删除收藏内容   [执行]   │
│  清理动态    批量删除发布动态   [执行]   │
│  清理历史    清空观看历史       [执行]   │
│  一键清理所有                  [全部清理]│
├──────────────────────────────────────────┤
│  执行日志                    [清空日志]  │
│  [15:23:12] 开始执行: all...             │
│  [15:23:45] 全部清理完成! 总计: 342      │
└──────────────────────────────────────────┘
```

支持浅色 / 深色主题切换，实时显示进度与结果。

---

## 🚀 快速开始

### 环境要求

- **Docker**（推荐，[点此下载安装 Docker Desktop](https://www.docker.com/products/docker-desktop/)）或 **Python 3.10+**
- 浏览器（Chrome / Edge / Safari / Firefox 均可）
- 哔哩哔哩手机 App（用于扫码登录）

### 方式一：Docker 一键启动（推荐小白）

```bash
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner
docker compose up -d
```

然后浏览器打开 http://localhost:8000 即可。

停止服务：

```bash
docker compose down
```

> 💡 **8000 端口被占？** 编辑 `docker-compose.yml`，把 `"8000:8000"` 左边改成空闲端口，如 `"8080:8000"`，浏览器访问对应端口即可。

### 方式二：Python 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner

# 2. 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 3. 安装依赖
pip install -r backend/requirements.txt

# 4. 启动服务（端口被占用可改 --port 8080）
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

浏览器访问 http://localhost:8000。

---

## 📘 使用教程（图文步骤）

### 第一步：启动服务

按上面两种方式之一启动，确保浏览器能打开 `http://localhost:8000`。

### 第二步：扫码登录

1. 打开页面后会自动显示二维码
2. 打开**哔哩哔哩 App** → 右上角扫一扫 → 扫描屏幕上的二维码
3. 在手机上点击"确认登录"
4. 浏览器自动跳转到控制台，显示当前 UID

> ⚠️ 二维码有效期约 3 分钟，过期后点击二维码刷新即可。

### 第三步：选择要清理的内容

控制台每项功能都有独立的**执行**按钮：

- **清理关注** → 取消所有关注的 UP 主
- **清理收藏** → 删除所有收藏夹内的视频
- **清理动态** → 删除发布过的所有动态
- **清理历史** → 清空观看历史
- **一键清理所有** → 以上所有功能一次性执行

点击按钮后会弹窗二次确认，确认后开始执行。右侧日志区实时显示进度。

### 第四步：查看结果

执行完成后，日志会显示清理总数。例如：

```
[15:23:12] 开始执行任务: all...
[15:23:45] 全部清理完成! 总计: 342
[15:23:45] 详情: 关注-58, 收藏-213, 动态-42, 历史-1
```

### 第五步：退出登录

右上角"退出登录"清除本地保存的登录凭证。

---

## ❓ 常见问题 FAQ

### Q1. 会不会泄露我的账号？
- 登录凭证（SESSDATA、bili_jct）**仅保存在你本地浏览器** localStorage
- 所有 API 调用都是**你本机** → B 站，不经过任何第三方服务器
- 代码全部开源可审计
- 用完记得点"退出登录"清除凭证

### Q2. 清理会不会很慢？
- 取关/删动态/清收藏 是**逐条请求** B 站接口，速度取决于数据量
- 大致速度：每秒 1–3 条（B 站限流，跑快会被风控）
- 几百条数据通常几分钟内完成

### Q3. 清理过程中可以关闭浏览器吗？
不可以。清理请求由前端发起，浏览器/标签页关闭会中断任务。建议全程保持页面打开。

### Q4. 清理后数据能恢复吗？
**不能**。所有操作都是永久删除，B 站无回收站。请务必确认后再执行。

### Q5. 遇到"请求发生错误"怎么办？
可能原因：
- **登录凭证过期** → 点击退出登录并重新扫码
- **B 站风控** → 稍等 10–30 分钟再试
- **网络问题** → 检查网络连接

### Q6. 为什么有些动态删不掉？
绝大多数动态（文字、转发、图文 opus、视频）都能删除。如出现个别删不掉的动态，通常是：
- 已被 B 站官方删除（幽灵动态）
- 动态属于特殊业务类型（如专栏转发）

可打开 B 站 Web 端手动确认。

### Q7. 支持 Windows 吗？
支持。推荐用 Docker Desktop，或者安装 Python 3.10+ 后按本地运行方式启动。

### Q8. 可以用于他人账号吗？
**不行**。本工具只清理当前扫码登录的账号数据，无法也不支持操作他人账号。

### Q9. 会不会导致账号被封？
本工具调用的都是 B 站官方 Web API，行为与手动操作一致，理论上不会。但若短时间内清理数据量过大，可能触发风控（暂时限流，不是封号）。

### Q10. 如何只清理某一项而不是全部？
在控制台选择具体清理项（关注/收藏/动态/历史），点击对应的"执行"按钮。

---

## 🔒 安全说明

- **本地部署**：整个工具运行在你自己的电脑上，**不向任何第三方服务器发送数据**
- **凭证保存**：登录后 `SESSDATA` / `bili_jct` 保存在浏览器 localStorage；请勿在公共电脑使用
- **XSS 防护**：日志输出使用 `textContent` 写入，已防范 XSS
- **CSRF 同步**：所有写操作自动带上 `bili_jct` 作为 csrf 参数
- **源码透明**：所有代码均开源，欢迎审计

---

## 🎯 功能范围与已知限制

### 可以做到
- ✅ 取消全部关注（使用 `/x/relation/modify`）
- ✅ 删除全部收藏夹视频（使用 `/x/v3/fav/resource/batch-del`）
- ✅ 删除各类动态，含新版图文 opus（带 WBI 签名拉取列表，`rm_dynamic` 删除）
- ✅ 清空观看历史（`/x/v2/history/clear`）

### 暂不支持
- ❌ 删除用户发布过的评论（B 站未开放"列出我发的评论"的接口，无法批量定位）
- ❌ 清理私信 / 粉丝 / 追番 / 稍后再看（暂未实现，欢迎 PR）
- ❌ 多账号同时清理（每次只能处理当前扫码登录的账号）

### 依赖外部因素
- B 站风控：短时间内大量请求可能触发，表现为接口返回空或报错，等待一段时间即可
- API 变动：B 站偶尔调整接口，如失效请提 Issue

---

## 📂 项目结构

```
bilibili-cleaner/
├── backend/                  # Python 后端（FastAPI）
│   ├── api/                  # B 站 API 封装
│   │   ├── auth.py           # 二维码登录
│   │   ├── relation.py       # 关注管理
│   │   ├── favorite.py       # 收藏管理
│   │   ├── dynamic.py        # 动态管理
│   │   ├── history.py        # 历史记录
│   │   ├── wbi.py            # WBI 签名算法
│   │   └── client.py         # HTTP 客户端
│   ├── services/
│   │   └── cleaner.py        # 批量清理服务
│   └── main.py               # FastAPI 入口
├── frontend/                 # 原生 HTML/CSS/JS 前端
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/                    # 单元测试（95% 覆盖）
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🔌 API 接口说明

启动服务后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/qrcode` | GET | 获取登录二维码 |
| `/api/qrcode/poll/{key}` | GET | 轮询扫码状态 |
| `/api/clean/followings` | POST | 清理关注列表 |
| `/api/clean/favorites` | POST | 清理全部收藏 |
| `/api/clean/dynamics` | POST | 清理全部动态 |
| `/api/clean/history` | POST | 清空观看历史 |
| `/api/clean/all` | POST | 一键清理全部 |

写操作请求头需带上：

```
SESSDATA: <你的 SESSDATA>
bili_jct: <你的 bili_jct>
Content-Type: application/json
```

Body 示例（除 `/api/clean/history` 外均需要）：

```json
{ "mid": 12345678 }
```

---

## 👨‍💻 开发与贡献

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v --cov=backend

# 生成 HTML 覆盖率报告
pytest tests/ --cov=backend --cov-report=html
```

欢迎提交 Issue 和 PR，详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

版本更新记录见 [CHANGELOG.md](CHANGELOG.md)。

---

## 🙏 致谢

- [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect) — B 站 API 文档参考
- [nemo2011/bilibili-api](https://github.com/nemo2011/bilibili-api) — 动态 / WBI 签名参考
- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架

---

## ⚠️ 免责声明

- 本工具**仅供学习交流**，旨在帮助用户合法清理个人账号数据
- 清理操作**不可撤销**，请务必谨慎操作并提前备份重要数据
- 使用本工具所产生的任何后果由用户自行承担
- 请遵守哔哩哔哩用户协议，不得用于违反法律法规或侵害他人权益的行为
- 本项目与哔哩哔哩官方无任何关联

---

## 📄 License

[MIT License](LICENSE) © 2024–2026

如果本项目对你有帮助，欢迎点一个 ⭐ Star 支持！
