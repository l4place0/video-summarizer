## Why

1. **版本自检缺失** — 用户无法知道当前安装的 skill 是否过时，可能使用旧版本遇到已修复的 bug
2. **仓库名称不准确** — "project-v" 不能反映项目功能，需要更直观的名称
3. **缺少英文文档** — 国际用户无法快速了解项目

## What Changes

- **版本自检脚本** — 添加 `check-update.sh`，curl GitHub releases 检查最新版本
- **仓库改名** — 改为 `bilibili-learning-helper`
- **双语 README** — 添加中英文 README.md
- **版本号管理** — 在配置中维护当前版本号

## Capabilities

### New Capabilities

- `version-check`: Skill 自检版本更新脚本

### Modified Capabilities

（无）

## Impact

- `skill/scripts/check-update.sh` — 新增版本检查脚本
- `README.md` — 新增中英文双语文档
- `README_EN.md` — 新增英文文档
- `skill/SKILL.md` — 更新仓库名称引用
- `pyproject.toml` — 更新项目名称和描述
- `docker-compose.yml` — 更新容器名称
