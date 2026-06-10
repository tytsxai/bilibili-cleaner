# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 文档
- 优化 README 首屏定位、阅读路径、使用场景和方案对比，提升传统搜索引擎与 AI 搜索引擎理解度。
- 新增 `docs/README.md` 文档总览，串联 README、API、FAQ、OpenAPI、llms 和 Agent 使用边界。
- 修正 `docs/API.md` 中 curl 鉴权示例和 cookbook 的可执行性，统一使用双请求头数组。
- 补充 `llms.txt` 的权威引用入口和机器可读摘要，并扩充 `pyproject.toml` 项目关键词。

## [1.1.1] - 2026-05-19

### 文档
- **新增英文 README** (`README.en.md`)：面向 GitHub 国际用户的完整英文版，含 Quick Start / FAQ / API 接口说明
- **新增 `llms.txt`**：为 ChatGPT / Claude / Perplexity / Gemini 等 AI 搜索引擎提供精炼项目索引
- **新增「适合谁用 / 使用场景」章节**：覆盖账号注销前清理、小号整理、账号转手、隐私清洁等场景
- **新增「与其它清理方案对比」表**：对比油猴脚本 / 第三方清理小程序 / 手动删除四种方案
- **README 顶部新增 Release / 英文 / llms.txt / Changelog 导航链接**

无代码改动，API 与运行行为与 1.1.0 完全一致。

## [1.1.0] - 2026-04-21

### 新增
- **WBI 签名支持**：动态列表接口 `/x/polymer/web-dynamic/v1/feed/space` 加入 WBI 签名，登录后也能稳定拉取全部动态，兼容新版 opus 图文动态
- **完整使用文档**：README 大幅扩充，新增 10 条 FAQ、图文使用教程、Docker / Python 双部署方式、安全说明、功能边界说明
- **CHANGELOG.md**：建立版本更新记录

### 修复
- **取消关注接口错误**：`/x/relation/batch/modify` 的 `act=2` 不被官方支持，改用单用户接口 `/x/relation/modify`
- **收藏批量删除 URL**：`/x/v3/fav/resource/batch/del` → `/x/v3/fav/resource/batch-del`（连字符）
- **动态列表稳定性**：补齐 `features`、`timezone_offset`、`platform`、`Referer` 等参数，避免返回空结果

### 移除
- **删除"清理评论"功能**：`/x/msgfeed/reply` 实际返回的是"回复我的"，并非用户自己发布的评论；B 站未开放"列出我发的评论"的公开接口，无法可靠实现，移除避免误导

### 致谢
- API 对齐参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)
- WBI 签名实现参考 [nemo2011/bilibili-api](https://github.com/nemo2011/bilibili-api)

## [1.0.0] - 2026-01-02

### 新增
- 首个正式版本
- 二维码扫码登录
- 批量取消关注 / 清空收藏 / 删除动态 / 清空历史
- 一键全部清理
- FastAPI 后端 + 原生 HTML/CSS/JS 前端
- Docker Compose 一键部署
- 单元测试（95%+ 覆盖率）

[1.1.1]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/tytsxai/bilibili-cleaner/releases/tag/v1.0.0
