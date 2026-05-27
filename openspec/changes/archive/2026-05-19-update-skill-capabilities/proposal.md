## Why

项目后端已新增多项能力（批量提交、任务重试、进度细分、历史搜索、Markdown 导出），但 `skill/SKILL.md` 中的能力描述仍停留在初始版本，只涵盖单个 URL 提交和基本查询。Skill 是 Claude Code 与用户交互的主要入口，描述不匹配会导致 Claude 无法正确引导用户使用新功能。

## What Changes

- 更新 `skill/SKILL.md` 的 description 和正文，反映新增能力
- 新增批量提交的使用说明
- 新增任务重试的使用说明
- 新增 Markdown 导出的使用说明
- 新增历史搜索的使用说明
- 更新进度显示的描述

## Capabilities

### New Capabilities
- `skill-description-sync`: Skill 描述与后端 API 能力保持同步

### Modified Capabilities

（无）

## Impact

- `skill/SKILL.md` — 更新能力描述
- `skill/scripts/summarize.sh` — 可能需要添加批量参数支持
