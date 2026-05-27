## Context

Bilibili App 和网页分享按钮生成的格式为：
```
【【中文字幕】C 中的递归宏】 https://www.bilibili.com/video/BV1fWdPBmEMc/?share_source=copy_web&vd_source=b235e9c478ba07e2678b1ac01bb439c6
```

用户粘贴到 textarea 时可能带上前缀标题文本。当前 `isValidVideoUrl` 直接对整行做正则匹配，无法识别这种格式。

## Goals / Non-Goals

**Goals:**
- 自动从 `【标题】 URL` 格式中提取 URL
- 支持纯 URL（向后兼容）
- 支持批量模式每行带标题

**Non-Goals:**
- 不解析标题内容（仅丢弃）
- 不支持其他非标准分享格式

## Decisions

### 1. 纯前端解析

在 `app.js` 中添加 `extractUrl(text)` 函数，提交前对每行调用。

**替代方案：** 后端解析（不必要，增加复杂度）

### 2. 提取策略

使用正则 `/https?:\/\/[^\s]+/` 从文本中提取第一个 URL。

**理由：** 简单可靠，覆盖所有 HTTP/HTTPS URL，不受标题内容影响。

### 3. 调用点

在 `handleSubmit` 的 `lines.map` 流程中，先 `extractUrl` 再 `isValidVideoUrl`。

## Risks / Trade-offs

- [误提取] 文本中包含多个 URL → 仅提取第一个，符合分享链接语义
- [非标准格式] 标题不含方括号 → 不处理，用户需手动清理
