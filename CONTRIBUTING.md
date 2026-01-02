# 贡献指南

感谢你对 Bilibili Cleaner 项目的关注！欢迎提交 Issue 和 Pull Request。

## 开发环境设置

```bash
# 克隆项目
git clone https://github.com/tytsxai/bilibili-cleaner.git
cd bilibili-cleaner

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
```

## 运行测试

```bash
pytest tests/ -v --cov=backend
```

## 提交规范

提交信息请遵循以下格式：

- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `test:` 测试相关
- `refactor:` 代码重构

## Pull Request 流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改
4. 确保测试通过
5. 提交 Pull Request

## 问题反馈

如有问题，请提交 Issue 并附上：
- 问题描述
- 复现步骤
- 环境信息
