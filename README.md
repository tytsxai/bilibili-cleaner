# Bilibili Cleaner - B站账号快速清理工具

[![CI](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/tytsxai/bilibili-cleaner/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen.svg)](tests/)

一个帮助用户快速批量清理B站账号数据的工具，支持 Web 界面操作。

## 功能特性

- 🔐 **二维码扫码登录** - 使用B站App安全扫码登录
- 👥 **批量取消关注** - 一键取消所有关注的UP主
- ⭐ **批量删除收藏** - 清空所有收藏夹内容
- 📝 **批量删除动态** - 删除发布的所有动态
- 🕐 **清空历史记录** - 清除观看历史
- 🚀 **一键全部清理** - 同时执行以上所有操作

## 截图预览

启动后访问 `http://localhost:8000` 即可看到 Web 界面。

## 快速开始

### 环境要求

- Python 3.10+

### 安装

```bash
# 克隆项目
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner

# 安装依赖
pip install -r backend/requirements.txt

# 启动服务
uvicorn backend.main:app --reload
```

### 使用方法

1. 启动服务后，浏览器访问 `http://localhost:8000`
2. 使用哔哩哔哩App扫描二维码登录
3. 选择需要清理的内容，点击执行

## 项目结构

```
bilibili-cleaner/
├── backend/
│   ├── api/              # B站API封装
│   │   ├── auth.py       # 二维码登录
│   │   ├── relation.py   # 关注管理
│   │   ├── favorite.py   # 收藏管理
│   │   ├── dynamic.py    # 动态管理
│   │   ├── comment.py    # 评论管理
│   │   └── history.py    # 历史记录
│   ├── services/
│   │   └── cleaner.py    # 批量清理服务
│   ├── main.py           # FastAPI入口
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── tests/                # 单元测试 (覆盖率96%)
```

## API 文档

启动服务后访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

### 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/qrcode` | GET | 获取登录二维码 |
| `/api/qrcode/poll/{key}` | GET | 轮询登录状态 |
| `/api/clean/followings` | POST | 清理关注列表 |
| `/api/clean/favorites` | POST | 清理收藏 |
| `/api/clean/dynamics` | POST | 清理动态 |
| `/api/clean/history` | POST | 清理历史 |
| `/api/clean/all` | POST | 一键清理全部 |

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v --cov=backend

# 代码覆盖率
pytest tests/ --cov=backend --cov-report=html
```

## 致谢

- [bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect) - B站API文档参考

## 免责声明

- 本工具仅供学习交流使用
- 请谨慎操作，清理后的数据无法恢复
- 使用本工具产生的任何后果由用户自行承担

## License

MIT License
