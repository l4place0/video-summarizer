## 1. HTML

- [x] 1.1 在 `#result-actions` 区域添加"导出 Markdown"按钮（id="export-markdown"，class="ghost-btn hidden"）

## 2. CSS

- [x] 2.1 添加 toast 提示样式（`.toast`，固定定位，2 秒自动消失动画）

## 3. JavaScript

- [x] 3.1 实现 `formatDurationHMS(seconds)` 工具函数，将秒数转为 HH:MM:SS 或 MM:SS 格式
- [x] 3.2 实现 `generateObsidianMarkdown(task)` 函数，根据 task 对象生成带 YAML frontmatter 的 Markdown
- [x] 3.3 实现 `copyToClipboard(text)` 函数，使用 Clipboard API + execCommand fallback
- [x] 3.4 实现 `showToast(message, type)` 函数，显示成功/失败 toast
- [x] 3.5 实现 `handleExportMarkdown()` 函数，串联生成和复制逻辑
- [x] 3.6 绑定按钮点击事件，在 `showResult()` 中根据任务状态控制按钮显示/隐藏

## 4. 测试

- [x] 4.1 手动测试：提交视频 → 等待完成 → 点击导出 → 验证剪贴板内容格式
