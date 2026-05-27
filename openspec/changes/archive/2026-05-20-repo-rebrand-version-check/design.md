## Context

当前仓库名为 "project-v"，没有版本自检机制，没有正式的 README 文档。用户需要手动检查更新，仓库名称也不能直观反映功能。

## Goals / Non-Goals

**Goals:**
- 用户运行 `bash skill/scripts/check-update.sh` 可检查是否有新版本
- 仓库名改为 `bilibili-learning-helper`，更直观
- 中英文 README 让不同语言用户快速了解项目

**Non-Goals:**
- 不做自动更新（仅提示）
- 不改代码逻辑
- 不迁移 git 历史

## Decisions

### 1. 版本检查方案

使用 `curl` 请求 GitHub API `/repos/{owner}/{repo}/releases/latest`，比较 tag 与本地版本。

**替代方案：** 请求 raw 文件（不需要 API 但不够规范）

### 2. 本地版本来源

在 `skill/scripts/version.sh` 中定义 `CURRENT_VERSION` 变量，其他脚本 `source` 它。

**替代方案：** 从 pyproject.toml 读取（需要 python 解析）

### 3. 仓库改名范围

更新：README、SKILL.md、pyproject.toml、docker-compose.yml、CLAUDE.md 中的引用。

不改：目录结构、核心代码、数据库。

## Risks / Trade-offs

- [GitHub API 限流] 未认证请求 60 次/小时 → 用户场景足够
- [改名遗漏] 部分引用未更新 → 搜索所有文件中的旧名称
