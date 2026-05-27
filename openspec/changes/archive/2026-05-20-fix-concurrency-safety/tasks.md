## 1. Whisper 并发安全

- [x] 1.1 在 `whisper.py` 中添加 `threading.Lock` 保护 `_get_model` 和 OOM fallback

## 2. 任务生命周期安全

- [x] 2.1 在 `routes.py` 的 `delete_task` 中检查任务状态，拒绝删除活跃任务（返回 409）
- [x] 2.2 在 `files.py` 的 `clean_cache` 中查询活跃和收藏任务 ID，排除其文件

## 3. 硬编码修复

- [x] 3.1 修改 `main.py:26` 的 `auto_cleanup` 使用 `settings.auto_cleanup_days`
- [x] 3.2 修改 `routes.py` 的 `retry_task` 从 metadata 读取 `llm_provider` 和 `detail`

## 4. 批量轮询优化

- [x] 4.1 重写 `app.js` 的 `startBatchPolling` 使用单个 setInterval 遍历所有 task

## 5. 输入校验

- [x] 5.1 在 `models.py` 中添加 `LanguageEnum`、`ModeEnum`、`DetailEnum` 并用于请求模型
- [x] 5.2 在 `SummarizeRequest` 中为 `url` 添加 `max_length=2000` 约束
