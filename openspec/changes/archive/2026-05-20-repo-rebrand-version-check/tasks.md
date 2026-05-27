## 1. 版本自检

- [x] 1.1 创建 `skill/scripts/version.sh`，定义 `CURRENT_VERSION="0.1.0"`
- [x] 1.2 创建 `skill/scripts/check-update.sh`，curl GitHub releases 检查最新版本并比较
- [x] 1.3 在 `status.sh` 中添加版本信息显示（source version.sh）

## 2. 仓库改名

- [x] 2.1 更新 `pyproject.toml` 中的 `name` 和 `description`
- [x] 2.2 更新 `docker-compose.yml` 中的容器名称（无显式容器名，无需修改）
- [x] 2.3 更新 `skill/SKILL.md` 中的仓库引用
- [x] 2.4 更新 `CLAUDE.md` 中的项目引用（无旧名称引用，无需修改）
- [x] 2.5 搜索并更新其他文件中的 "project-v" 引用（更新 INSTALL.md）

## 3. 双语 README

- [x] 3.1 创建 `README.md`（中文），包含项目介绍、功能列表、快速开始、截图说明
- [x] 3.2 创建 `README_EN.md`（英文），对应中文内容
