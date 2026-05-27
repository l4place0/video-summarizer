## Why

用户需要将视频总结笔记导出到 Obsidian 进行知识管理。当前 WebUI 只能在线查看总结内容，无法一键导出为带完整元数据的 Markdown 文件。手动复制会丢失视频元信息（标题、作者、标签等），不利于 Obsidian 中的检索和组织。

## What Changes

- WebUI 结果区域新增"导出 Markdown"按钮
- 点击后生成带 YAML frontmatter 的 Markdown，复制到剪贴板
- Frontmatter 包含：视频元信息（title/author/url/platform/tags/duration）、简介、分类结果
- Markdown 正文为 LLM 总结内容
- 支持导出成功/失败的 toast 提示

## Capabilities

### New Capabilities
- `markdown-export`: 生成带 YAML frontmatter 的 Obsidian 兼容 Markdown，包含视频元信息和总结内容，复制到剪贴板

### Modified Capabilities

（无）

## Impact

- `core/web/app.js` — 新增导出逻辑和剪贴板 API 调用
- `core/web/index.html` — 新增导出按钮
- `core/web/style.css` — 导出按钮样式
- 无后端改动，纯前端功能
