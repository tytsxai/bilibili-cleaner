# B站账号清理工具 - 开发计划

## 项目概述

一个帮助用户快速批量清理B站账号数据的工具，支持Web界面操作。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / httpx
- **前端**: HTML5 / CSS3 / Vanilla JS
- **认证**: 二维码扫码登录

## 功能清单

1. 二维码扫码登录
2. 批量取消关注
3. 批量删除收藏视频
4. 批量删除评论
5. 批量删除动态
6. 清理历史记录

## API 参考

基于 bilibili-API-collect 项目文档。

### 认证
- 生成二维码: `GET /x/passport-login/web/qrcode/generate`
- 轮询状态: `GET /x/passport-login/web/qrcode/poll`

### 关注管理
- 获取关注列表: `GET /x/relation/followings`
- 批量取关: `POST /x/relation/batch/modify` (最多50人/次)

### 收藏管理
- 获取收藏夹: `GET /x/v3/fav/folder/created/list-all`
- 获取收藏内容: `GET /x/v3/fav/resource/ids`
- 批量删除: `POST /x/v3/fav/resource/batch/del`

### 动态管理
- 获取动态: `GET /x/polymer/web-dynamic/v1/feed/space`
- 删除动态: `POST /dynamic_svr/v1/dynamic_svr/rm_dynamic`

### 评论管理
- 删除评论: `POST /x/v2/reply/del`

### 历史记录
- 清空历史: `POST /x/v2/history/clear`

---

## 任务分解

### T1: 核心API封装模块
- **type**: default
- **backend**: codex
- **dependencies**: none
- **scope**: `backend/api/*.py`
- **test**: `pytest tests/test_api.py -v --cov=backend/api --cov-report=term`

**文件清单**:
- `backend/api/__init__.py`
- `backend/api/client.py` - HTTP客户端基类
- `backend/api/auth.py` - 二维码登录
- `backend/api/relation.py` - 关注管理
- `backend/api/favorite.py` - 收藏管理
- `backend/api/dynamic.py` - 动态管理
- `backend/api/comment.py` - 评论管理
- `backend/api/history.py` - 历史记录

### T2: 清理服务层 + FastAPI后端
- **type**: default
- **backend**: codex
- **dependencies**: T1
- **scope**: `backend/services/*.py`, `backend/main.py`
- **test**: `pytest tests/test_services.py tests/test_main.py -v --cov=backend --cov-report=term`

**文件清单**:
- `backend/services/__init__.py`
- `backend/services/cleaner.py` - 批量清理逻辑
- `backend/main.py` - FastAPI应用入口
- `backend/requirements.txt`

### T3: Web UI界面
- **type**: ui
- **backend**: gemini
- **dependencies**: T2
- **scope**: `frontend/*`
- **test**: 手动测试

**文件清单**:
- `frontend/index.html`
- `frontend/style.css`
- `frontend/app.js`

### T4: 单元测试
- **type**: default
- **backend**: codex
- **dependencies**: T1, T2
- **scope**: `tests/*.py`
- **test**: `pytest tests/ -v --cov=backend --cov-report=term`

**文件清单**:
- `tests/__init__.py`
- `tests/conftest.py` - pytest fixtures
- `tests/test_api.py` - API模块测试
- `tests/test_services.py` - 服务层测试
- `tests/test_main.py` - FastAPI端点测试

---

## 目录结构

```
bilibili-cleaner/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── auth.py
│   │   ├── relation.py
│   │   ├── favorite.py
│   │   ├── dynamic.py
│   │   ├── comment.py
│   │   └── history.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── cleaner.py
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_services.py
│   └── test_main.py
└── README.md
```

## 覆盖率要求

所有后端代码测试覆盖率 ≥ 90%
