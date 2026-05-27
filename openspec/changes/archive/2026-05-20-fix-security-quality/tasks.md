## 1. 安全修复

- [x] 1.1 在 `routes.py` 的 `get_task_frame` 中添加路径穿越防护（`Path(filename).name` + resolve 检查）
- [x] 1.2 在 `db.py` 中定义 `ALLOWED_COLUMNS` 白名单并在 `update_task` 中校验
- [x] 1.3 创建 `FavoriteRequest` Pydantic model 并在 `set_task_favorite` 端点使用

## 2. 错误处理改进

- [x] 2.1 在 `pipeline.py:163` 改用 `logger.exception` 保留完整 traceback
- [x] 2.2 在 `openai_proto.py:27` 的 `_get_video_duration` 中添加 warning 日志
- [x] 2.3 在 `base.py` 的分类重试中区分 JSON 解析错误和网络错误

## 3. 性能优化

- [x] 3.1 在 `db.py` 中添加 `video_id` 列和索引（migration）
- [x] 3.2 修改 `find_cached_task` 使用 SQL WHERE 查询 video_id
- [x] 3.3 验证 `update_task` 的批量更新行为已正确实现

## 4. 代码质量

- [x] 4.1 清理 `base.py` 中未使用的 import（CLASSIFY_PROMPT, CLASSIFY_PROMPT_MULTIMODAL, SUMMARY_PROMPTS）
- [x] 4.2 修改 `routes.py:234` 的 `retry_task` 从原任务读取参数
- [x] 4.3 将 `AUTO_CLEANUP_DAYS` 移入 Settings 配置

## 5. 测试补全

- [x] 5.1 为 CUDA OOM fallback 编写单元测试（mock RuntimeError）
- [x] 5.2 为 LLM 三级降级链编写单元测试（mock API 错误）
- [x] 5.3 为路径穿越防护编写测试用例
