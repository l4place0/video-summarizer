## Context

`skill/SKILL.md` 是 Claude Code 的 skill 定义文件，描述了视频总结工具的能力和使用方式。当前描述只覆盖：
- 单个 URL 提交
- 基本选项（lang/provider/detail/mode）
- 状态查询
- 存储清理

后端已新增的能力：
- 批量 URL 提交（batch-submit）
- 失败任务重试（task-retry）
- 阶段内进度百分比（progress-granularity）
- 历史搜索过滤（history-search-filter）
- Markdown 导出到 Obsidian（export-markdown-obsidian）
- SQLite WAL 模式（sqlite-wal）
- 下载重试（download-retry）

## Goals / Non-Goals

**Goals:**
- SKILL.md 描述与后端实际能力完全一致
- Claude 能根据 SKILL.md 正确引导用户使用所有功能
- 保持 SKILL.md 简洁，不过度详细

**Non-Goals:**
- 不修改后端 API
- 不创建新的 skill 脚本（除非批量功能需要）

## Decisions

### 1. 更新 SKILL.md 而非创建新 skill

所有功能仍属于同一个 video-summarizer skill，只是扩展描述。

**理由：** 功能都在同一个服务中，不需要拆分 skill。

### 2. 批量提交通过脚本参数支持

在 `summarize.sh` 中添加 `--batch` 参数，接受多个 URL。

**理由：** 保持脚本接口简洁，一个脚本覆盖单个和批量场景。

### 3. 导出功能通过 WebUI 操作

Markdown 导出是纯前端功能，不需要脚本支持。在 SKILL.md 中说明"在 WebUI 结果页面点击 Export Markdown"。

**理由：** 导出依赖浏览器剪贴板 API，无法通过 CLI 脚本实现。

## Risks / Trade-offs

- [SKILL.md 长度] 添加过多描述可能让 SKILL.md 变得冗长 → 保持简洁，只列功能和用法
