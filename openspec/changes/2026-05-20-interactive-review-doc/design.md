## Context

当前 pipeline 产出三份独立素材：总结稿（Markdown）、转写稿（带时间戳纯文本）、关键帧（jpg 文件）。用户需要在 WebUI 中分别查看，无法离线携带，也没有主动复习机制。

目标是将这三份素材打包为一个自包含的单 HTML 文件，内嵌 CSS/JS/图片（base64），作为一个独立运行的交互式复习应用。

## Goals / Non-goals

**Goals:**
- 单 HTML 文件完全自包含，双击即可在浏览器中打开使用
- 知识卡片从总结中自动提取（方案 C：prompt 顺带生成）
- SM-2 间隔复习算法，复习状态持久化到 localStorage
- 时间线视图：关键帧与转写文本联动
- 任意段落可添加笔记，全文可搜索高亮
- WebUI 按钮触发生成 + API 端点可被 Skill 调用

**Non-goals:**
- 不做多用户协作
- 不做云端同步
- 不嵌入视频播放器
- 不修改已有总结输出格式（卡片是追加 section）

## Decisions

### 1. 卡片数据格式

LLM 在总结末尾输出 `## 复习卡片` section，格式为：

```markdown
## 复习卡片

**Q1:** 什么是 SM-2 算法的核心思想？
**A1:** 通过 ease factor 和间隔天数动态调整复习频率，遗忘曲线驱动。

**Q2:** ...
**A2:** ...
```

解析逻辑：正则匹配 `**Q\d+:**` 和 `**A\d+:**` 提取问答对。容错：如果 LLM 没有输出此 section（旧任务或自定义 prompt），降级为无卡片模式，文档仍然正常生成。

### 2. HTML 模板渲染方式

使用 Jinja2 渲染 HTML 模板。模板含循环（帧列表、卡片列表、转写段落）和条件（有无卡片、有无帧），纯字符串拼接不可维护。

结构：
```
templates/review_doc.html (Jinja2 模板)
├── <style> ... </style>          ← 内联 CSS
├── <div id="app"> ... </div>     ← 骨架 HTML（Jinja2 循环渲染帧/卡片/段落）
├── <script>
│   window.REVIEW_DATA = {...}    ← JSON 注入（summary/transcript/frames/metadata/cards）
│   ... 内联 JS（SRS引擎/笔记/搜索/时间线） ...
└── </script>
```

静态数据（帧 base64、卡片、转写段落）通过 Jinja2 直接渲染到 HTML 中。动态交互数据注入到 `window.REVIEW_DATA`，JS 运行时读取并驱动 UI。

### 3. 帧图片 base64 编码

在服务端完成：
```python
import base64
for frame_path in frame_files:
    b64 = base64.b64encode(frame_path.read_bytes()).decode()
    data_uri = f"data:image/jpeg;base64,{b64}"
```

注入到 `REVIEW_DATA.frames[].data_uri`。HTML 文件大小预估：20 帧 x 200KB ≈ 4MB base64 + 文本 ≈ 4-5MB 总计。

### 4. SRS 引擎（SM-2 算法）

在 HTML 内联 JS 中实现简化版 SM-2：

```js
// 每张卡片的状态
{ ease: 2.5, interval: 0, due: today, reviews: 0 }

// 评分：0=忘记, 1=模糊, 2=熟悉, 3=掌握
function sm2(card, quality) {
  if (quality < 2) { card.interval = 0; card.reviews = 0; }
  else {
    if (card.reviews === 0) card.interval = 1;
    else if (card.reviews === 1) card.interval = 6;
    else card.interval = Math.round(card.interval * card.ease);
    card.reviews++;
  }
  card.ease = Math.max(1.3, card.ease + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02)));
  card.due = today + card.interval;
}
```

持久化到 `localStorage["review_{taskId}"]`。

### 5. 转写文本分段策略

转写文本按 Whisper 的段落（`\n\n` 分隔）切分。每段包裹为：
```html
<div class="transcript-seg" data-idx="0">
  <span class="seg-time">[00:00]</span>
  <span class="seg-text">...</span>
  <button class="note-btn" data-idx="0">📝</button>
</div>
```

时间戳 `[MM:SS]` 从转写文本中正则提取，用于时间线定位。

### 6. 时间线联动

关键帧按提取顺序排列（对应视频时间均匀分布）。点击帧时：
1. 计算帧对应的大致转写段落索引（`frame_index / total_frames * total_segments`）
2. 滚动到该段落并高亮
3. 高亮持续 3 秒后淡出

### 7. API 端点设计

```
GET /api/tasks/{task_id}/review-doc
```

- 返回 `Content-Type: text/html; charset=utf-8`
- `Content-Disposition: attachment; filename="review_{taskId[:8]}.html"`
- 如果任务状态不是 `done`，返回 400
- 如果没有总结内容，返回 404

### 8. 新增依赖

需要 `jinja2` 用于模板渲染（HTML 模板含循环和条件，纯字符串拼接不可维护）。

## Risks / Trade-offs

- **[文件大小]** base64 内嵌帧图片使文件达 4-5MB → 可接受，现代浏览器无压力
- **[LLM 输出格式]** `## 复习卡片` 的格式可能不一致 → 正则容错 + 降级无卡片模式
- **[localStorage 容量]** 每个任务的复习数据约 1-2KB → 远低于 5MB 限制
- **[模板维护]** 内联 JS/CSS 较长 → 单文件模板，集中维护，不拆分
