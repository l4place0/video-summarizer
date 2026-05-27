## Why

多线程并发场景存在数据安全和状态竞争问题：Whisper 全局变量被并发转录覆盖、运行中任务可被删除导致文件竞态、clean_cache 无保护可能清除活跃任务文件、轮询效率低、输入无校验。

## What Changes

- **Whisper 并发安全**：加锁保护全局模型状态，防止并发 OOM fallback 竞争
- **删除安全**：delete_task 检查任务状态，拒绝删除运行中任务
- **clean_cache 保护**：排除 favorited 和正在处理的任务文件
- **轮询优化**：批量模式合并为单次轮询遍历所有 task
- **输入校验**：language/mode/detail 添加 enum 约束，url 添加长度限制
- **硬编码修复**：main.py auto_cleanup 和 retry_task 读取正确参数

## Capabilities

### New Capabilities

- `whisper-thread-safety`: Whisper 全局状态加锁保护
- `task-lifecycle-safety`: 任务删除前状态检查、clean_cache 保护
- `batch-poll-optimization`: 批量轮询合并
- `input-validation`: Pydantic enum 约束和长度限制

### Modified Capabilities

（无）

## Impact

- `core/asr/whisper.py` — threading.Lock 保护全局状态
- `core/api/routes.py` — delete_task 状态检查、retry 读取原参数、轮询优化
- `core/storage/files.py` — clean_cache 排除活跃任务
- `core/models.py` — enum 约束
- `core/main.py` — auto_cleanup 读 settings
- `core/web/app.js` — 批量轮询合并
