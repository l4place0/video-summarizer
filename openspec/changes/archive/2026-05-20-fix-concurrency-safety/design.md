## Context

系统使用 threading 模式运行 pipeline，多个任务并发时存在：
1. Whisper 全局变量（_model, _device）被并发修改
2. delete_task 与 pipeline 线程文件操作竞态
3. clean_cache 可能删除正在写入的文件
4. 批量轮询 N 个 task 创建 N 个 setInterval

## Goals / Non-Goals

**Goals:**
- 并发转录安全
- 任务生命周期安全（删除/清理不破坏运行中任务）
- 批量轮询效率
- 输入校验

**Non-Goals:**
- 不改 SQLite 为其他 DB
- 不引入 asyncio（保持 threading 模式）
- 不添加任务取消功能（仅阻止删除）

## Decisions

### 1. Whisper 锁保护

使用 `threading.Lock` 保护 `_get_model` 和 OOM fallback 逻辑。锁粒度：模型加载 + 转录尝试。

**替代方案：** 每个线程独立模型实例（内存开销过大）

### 2. delete_task 状态检查

拒绝删除 `status in ("pending", "downloading", "transcribing", "extracting_frames", "classifying", "summarizing")` 的任务。

**替代方案：** 添加 cancel 标志位（复杂度高，超出范围）

### 3. clean_cache 保护

查询 DB 获取 active task IDs 和 favorited task IDs，排除这些任务的文件。

### 4. 批量轮询合并

`startBatchPolling` 使用单个 `setInterval`，每次遍历所有未完成 task。

### 5. 输入校验

添加 `LanguageEnum`、`ModeEnum`、`DetailEnum`，url 限制 2000 字符。

## Risks / Trade-offs

- [锁粒度] 全局锁可能成为瓶颈 → 当前并发量（<10 线程）可接受
- [状态检查] 运行中任务不能删除 → 用户需等待完成或使用 cleanup
