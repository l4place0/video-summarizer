## 1. Prompt 增强

- [x] 1.1 在 `core/llm/prompts.py` 中定义 `REVIEW_CARDS_SUFFIX_ZH` 和 `REVIEW_CARDS_SUFFIX_EN` 常量，包含 `## 复习卡片` section 的指令模板
- [x] 1.2 修改 `get_summary_prompt()` 在返回 prompt 末尾追加复习卡片 suffix（根据 lang 选择中英文）
- [x] 1.3 在 `DETAIL_MAX_TOKENS` 中将 `detailed` 从 8192 调整为 10240，为卡片输出留出空间
- [x] 1.4 在 prompt store 中支持自定义复习卡片 suffix（可选，不阻塞主流程）

## 2. 卡片数据解析

- [x] 2.1 在 `core/review_doc.py` (新文件) 中实现 `parse_review_cards(summary: str) -> list[dict]`，用正则从 `## 复习卡片` section 中提取 `**Q\d+:**` / `**A\d+:**` 问答对
- [x] 2.2 容错处理：无 `## 复习卡片` section 时返回空列表；Q/A 数量不匹配时截取到最短长度
- [x] 2.3 为 `parse_review_cards` 编写单元测试（正常格式、无 section、格式异常三种 case）

## 3. 帧图片 base64 编码

- [x] 3.1 在 `core/review_doc.py` 中实现 `encode_frames(task_id: str) -> list[dict]`，读取帧文件并返回 `[{index, data_uri, timestamp}]` 列表
- [x] 3.2 帧文件查找逻辑复用 API 端点的路径逻辑（先查 `cache_dir/frames/{id}`，再查 `audio_dir/{id}`）
- [x] 3.3 帧时间戳估算：根据帧索引和总数等分视频时长（从 metadata.duration 获取）

## 4. HTML 模板

- [x] 4.1 在 `core/templates/review_doc.html` (新文件) 创建 Jinja2 模板骨架：顶部导航栏、侧栏、主内容区
- [x] 4.2 实现知识卡片区域：翻转动画 CSS（`transform: rotateY(180deg)`），掌握度按钮（忘记/模糊/熟悉/掌握）
- [x] 4.3 实现时间线视图：帧图片纵向排列，每帧标注估算时间戳，点击帧触发转写段落滚动高亮
- [x] 4.4 实现转写稿区域：按段落渲染，每段带时间戳标签和笔记按钮，支持折叠/展开
- [x] 4.5 实现笔记系统：点击笔记按钮弹出输入框，笔记数据存入 localStorage
- [x] 4.6 实现全文搜索：搜索框实时过滤，关键词高亮（`<mark>` 标签），结果计数和上下跳转
- [x] 4.7 实现帧灯箱：点击帧图片放大显示，左右键/按钮切换，ESC 关闭
- [x] 4.8 实现 SRS 复习模式：独立视图，逐张展示待复习卡片，评分后自动下一张，复习完成显示统计
- [x] 4.9 内联 CSS：暗色主题、响应式布局、卡片/时间线/转写各区域样式
- [x] 4.10 测试模板在 Chrome/Firefox 中的渲染效果

## 5. 后端生成逻辑

- [x] 5.1 在 `core/review_doc.py` 中实现 `generate_review_doc(task: dict, frames: list[dict], cards: list[dict]) -> str`，Jinja2 渲染完整 HTML
- [x] 5.2 在 `core/api/routes.py` 中新增 `GET /api/tasks/{task_id}/review-doc` 端点
- [x] 5.3 端点逻辑：校验任务状态 → 读取 summary/transcript/metadata → 编码帧图片 → 解析卡片 → 渲染模板 → 返回 HTML 文件下载
- [x] 5.4 添加 `jinja2` 到 `pyproject.toml` dependencies

## 6. WebUI 集成

- [x] 6.1 在 `core/web/index.html` 的 `#result-actions` 区域添加"生成复习文档"按钮（id="export-review-doc"，class="ghost-btn hidden"）
- [x] 6.2 在 `core/web/app.js` 中实现 `handleExportReviewDoc()` 函数，fetch API 端点并触发浏览器下载
- [x] 6.3 在 `showResult()` 中根据任务状态 `done` 控制按钮显示/隐藏
- [x] 6.4 在 `core/web/style.css` 中添加按钮样式

## 7. 集成测试

- [x] 7.1 端到端测试：提交视频 → 等待完成 → 点击生成复习文档 → 验证下载的 HTML 文件可正常打开
- [x] 7.2 验证 HTML 文件中：帧图片正确显示、卡片可翻转、笔记可保存、搜索可高亮、SRS 复习流程正常
- [x] 7.3 验证旧任务（无复习卡片 section）降级为无卡片模式正常工作
