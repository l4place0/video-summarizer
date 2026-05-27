## Context

项目存在三个层面的问题：
1. **安全**：frame 端点允许路径穿越（`../../etc/passwd.jpg`），update_task 无列名白名单
2. **质量**：错误处理丢失 traceback、性能瓶颈（全表扫描）、硬编码配置
3. **测试**：CUDA OOM fallback、LLM 降级链等关键路径无测试

## Goals / Non-Goals

**Goals:**
- 消除已知安全漏洞（路径穿越、列注入）
- 错误日志保留完整上下文
- 缓存查询从 O(n) 优化到 O(1)
- 关键路径有测试覆盖

**Non-Goals:**
- 不改变 API 接口设计
- 不重构整体架构
- 不新增功能

## Decisions

### 1. 路径穿越防护方案

**选择**：在 `get_task_frame` 中使用 `Path(filename).name` 提取纯文件名，然后在 task 的 output_dir 内 resolve 并检查是否在目录内。

**替代方案**：
- 使用 `send_from_directory`（需要引入新依赖）
- 白名单文件扩展名（不够全面）

### 2. update_task 列名白名单

**选择**：定义 `ALLOWED_COLUMNS` 常量集合，在 `update_task` 中校验 key 是否在白名单内。

**替代方案**：
- 使用 Pydantic model 约束（需要改动调用方）
- 使用 enum（过于严格）

### 3. find_cached_task 查询优化

**选择**：为 `video_id` 添加独立列 + 索引，查询时用 SQL WHERE 而非 Python 过滤。需要 DB migration。

**替代方案**：
- 使用 SQLite JSON1 扩展 `json_extract(metadata, '$.video_id')`（依赖 SQLite 编译选项）
- 添加索引列（当前方案）

### 4. 批量提交策略

**选择**：新增 `update_task_batch` 方法接受多条更新，在 pipeline 结束时统一 commit。

**替代方案**：
- 使用 WAL 模式减少锁竞争（已实施，但 commit 开销仍在）
- 上下文管理器（改动较大）

### 5. 测试策略

**选择**：使用 pytest + mock，为每个关键路径写独立测试。mock 外部依赖（yt-dlp、whisper model、LLM API）。

## Risks / Trade-offs

- **[DB migration]** 添加 `video_id` 列需要 migration → 使用已有的 `_migrate` 模式，向后兼容
- **[测试 mock 复杂度]** CUDA OOM fallback 需要 mock RuntimeError → 可控，使用 `side_effect`
- **[列名白名单维护]** 新增字段需更新白名单 → 在代码中注释提示，CI 可检测遗漏
