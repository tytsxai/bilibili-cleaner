# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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

[1.1.0]: https://github.com/tytsxai/bilibili-cleaner/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/tytsxai/bilibili-cleaner/releases/tag/v1.0.0
