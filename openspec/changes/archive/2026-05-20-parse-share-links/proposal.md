## Why

Bilibili 的分享链接格式为 `【标题】 https://www.bilibili.com/video/BVxxxxx/?...`，用户从 App 或网页复制时会带上前缀标题。当前系统只接受纯 URL，用户必须手动删除标题部分才能提交，体验不佳。

## What Changes

- 前端提交时自动从文本中提取 URL（支持 `【标题】 URL` 格式和其他混合文本）
- 支持批量模式下每行带标题前缀的分享链接
- 不改变后端逻辑，纯前端解析

## Capabilities

### New Capabilities

- `share-link-parsing`: 从分享文本中自动提取视频 URL

### Modified Capabilities

（无）

## Impact

- `core/web/app.js` — 添加 URL 提取函数，修改提交逻辑
