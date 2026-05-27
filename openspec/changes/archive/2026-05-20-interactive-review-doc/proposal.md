## Why

当前系统产出的总结稿、转写稿、关键帧是散落的独立数据，用户需要在 WebUI 中来回切换查看。对于学习型视频（教程、技术分享），用户需要**主动回忆和自测**来巩固知识，而不是被动阅读。现有 WebUI 缺少复习、笔记、间隔复习等学习辅助功能，也无法离线携带。

需要一个自包含的单 HTML 文件，将所有素材整合为**交互式复习文档**，支持知识卡片翻转测试、SRS 间隔复习、时间线联动浏览、全文笔记标注，可离线使用和分享。

## What Changes

### 总结 Prompt 增强（方案 C）
- 所有 content_type 的总结 prompt 末尾追加 `## 复习卡片` section
- LLM 在总结时顺带生成 5-10 组 Q&A 知识卡片
- 零额外 LLM 调用，卡片与总结一体输出
- max_tokens 适配：detailed 模式下从 8192 提升到 10240 以容纳卡片

### 新增 API 端点
- `GET /api/tasks/{id}/review-doc` — 生成并返回单 HTML 文件
- 服务端组装：读取 summary/transcript/metadata + frames 转 base64 + 渲染 Jinja2 模板
- 返回 `Content-Type: application/octet-stream` + `Content-Disposition: attachment`

### WebUI 增强
- 结果区域新增"生成复习文档"按钮（仅 `done` 状态显示）
- 点击后调用 API，触发浏览器下载

### 单 HTML 文件内置功能
- **知识卡片**：从总结中提取 Q&A，翻转动画，掌握度标记
- **SRS 引擎**：SM-2 算法，localStorage 持久化复习状态
- **时间线视图**：关键帧按时间戳排列，点击跳转到对应转写段落
- **转写稿浏览**：按段落折叠/展开，支持搜索高亮
- **笔记系统**：任意段落添加笔记，localStorage 持久化
- **全文搜索**：跨总结+转写搜索，关键词高亮和结果跳转
- **帧图片灯箱**：base64 内嵌，点击放大，左右键切换

## Capabilities

### New Capabilities
- `interactive-review-doc`: 生成自包含单 HTML 交互式复习文档，内嵌总结稿、转写稿、关键帧（base64），支持知识卡片、SRS 间隔复习、时间线联动、笔记标注、全文搜索
- `review-cards-generation`: 总结 prompt 自动产出 Q&A 知识卡片，无需额外 LLM 调用

### Modified Capabilities
- `markdown-export`: 无改动，两者独立共存

## Impact

### 后端
- `core/llm/prompts.py` — 所有 content_type 的 prompt 追加 `## 复习卡片` section
- `core/api/routes.py` — 新增 `GET /api/tasks/{id}/review-doc` 端点
- `core/review_doc.py` (新文件) — HTML 模板渲染逻辑，帧图片 base64 编排，卡片数据解析

### 前端
- `core/web/index.html` — 结果区域新增"生成复习文档"按钮
- `core/web/app.js` — 按钮点击事件，调用 API 触发下载
- `core/web/style.css` — 按钮样式

### HTML 模板
- `core/templates/review_doc.html` (新文件) — Jinja2 模板，内联 CSS/JS，自包含单文件

## Non-goals

- 不做多用户协作笔记（单机本地场景）
- 不做云端同步复习状态（localStorage 足够）
- 不做视频播放器嵌入（单 HTML 离线场景不适用）
- 不修改现有总结的输出格式（卡片是追加 section，不破坏已有结构）
