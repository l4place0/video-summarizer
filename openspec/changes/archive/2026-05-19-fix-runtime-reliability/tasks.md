## 1. Claude 帧提取修复

- [x] 1.1 在 `claude.py` 中导入 `openai_proto._extract_frames`，替换旧的 `_extract_frames` 函数
- [x] 1.2 更新 `ClaudeLLM.summarize_multimodal()` 调用新导入的帧提取函数

## 2. CUDA 回退逻辑

- [x] 2.1 在 `whisper.py` 的 `transcribe()` 中添加 CUDA OOM 捕获逻辑
- [x] 2.2 OOM 时设置 `_device = "cpu"`、清空 `_model = None`，重新加载模型并重试

## 3. 分类结果存储

- [x] 3.1 在 `pipeline.py` classify 阶段后将 content_type 和 language 写入 metadata dict
- [x] 3.2 调用 `db.update_task()` 持久化更新后的 metadata

## 4. 导出功能适配

- [x] 4.1 修改 `app.js` 的 `generateObsidianMarkdown()` 从 metadata 读取 content_type 和 language

## 5. 测试

- [x] 5.1 验证 Claude 帧提取对长视频不再挂起
- [x] 5.2 验证分类结果正确存入数据库
- [x] 5.3 验证导出 Markdown 的 frontmatter 包含 content_type 和 language
