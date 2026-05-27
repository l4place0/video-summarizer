## Context

WebUI 当前在结果区域展示视频总结，但没有导出功能。用户使用 Obsidian 管理知识笔记，需要将总结内容连同视频元信息一起导出为 Markdown。当前数据流中，task 对象已包含完整的 metadata（title/uploader/tags/description 等）和 classification 结果，前端可直接使用。

## Goals / Non-Goals

**Goals:**
- 一键复制带 YAML frontmatter 的 Markdown 到剪贴板
- Frontmatter 包含视频元信息、简介、分类结果
- 正文为 LLM 总结内容
- 兼容 Obsidian 的 YAML frontmatter 解析

**Non-Goals:**
- 不做文件下载（仅剪贴板）
- 不做批量导出
- 不做后端改动（纯前端功能）
- 不做 Markdown 模板自定义（v1 固定格式）

## Decisions

### 1. Markdown 格式设计

```markdown
---
title: "视频标题"
author: "UP主名"
url: "https://..."
platform: bilibili
tags: [标签1, 标签2]
date: 2026-05-19
duration: "01:23:45"
upload_date: "2026-05-09"
content_type: tutorial
language: zh
description: |
  视频简介内容...
---

# 视频标题

## 总结

（LLM 总结内容）
```

**理由：**
- YAML frontmatter 是 Obsidian 的标准 meta 格式
- `title`/`author`/`url` 为必选 meta，Obsidian 可检索
- `tags` 用 YAML 数组格式，Obsidian 原生识别为标签
- `date` 用 ISO 日期格式，便于 Obsidian 日历插件
- `duration` 转为人类可读格式（HH:MM:SS）
- `description` 用 YAML 多行语法 `|`，保留换行
- `content_type`/`language` 记录分类结果
- 正文前加 `# 标题` 和 `## 总结`，结构清晰

### 2. 剪贴板 API

使用 `navigator.clipboard.writeText()`，现代浏览器均支持。失败时 fallback 到 `document.execCommand('copy')`。

### 3. 交互反馈

复制成功后显示 toast 提示（2 秒自动消失），失败显示错误 toast。

## Risks / Trade-offs

- [剪贴板权限] 部分浏览器可能拒绝剪贴板访问 → 使用 fallback 方案
- [长简介] description 可能很长 → YAML `|` 语法天然支持多行，不做截断
- [特殊字符] 标题/简介中可能有 YAML 特殊字符 → 使用引号包裹字符串字段
