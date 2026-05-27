## Why

代码审查发现多个安全隐患和质量问题：路径穿越漏洞、SQL 列注入风险、错误处理丢失上下文、性能瓶颈（全表扫描）、硬编码配置值。这些问题影响生产环境的安全性和可维护性。

## What Changes

- **安全修复**：frame 端点路径穿越防护、update_task 列名白名单、favorite 端点 Pydantic 校验
- **错误处理改进**：pipeline 使用 logger.exception 保留 traceback、ffprobe 失败记录日志、分类重试区分错误类型
- **性能优化**：find_cached_task 改用 SQL 查询替代全表扫描、update_task 支持批量提交
- **代码质量**：清理未使用 import、retry_task 从原任务读取参数、统一配置项
- **测试补全**：为关键路径（CUDA OOM fallback、LLM 降级链）添加单元测试

## Capabilities

### New Capabilities

- `security-hardening`: 路径遍历防护、SQL 注入防护、输入校验
- `error-context-preservation`: 结构化错误日志、traceback 保留、错误类型区分
- `db-query-optimization`: 缓存查询优化、批量提交支持

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

- `core/api/routes.py` — 路径验证、输入模型、参数读取
- `core/storage/db.py` — 查询优化、批量提交、列名白名单
- `core/pipeline.py` — 错误日志改进
- `core/llm/openai_proto.py` — ffprobe 错误日志
- `core/llm/base.py` — 分类错误区分、import 清理
- 新增测试文件 `tests/` — 覆盖关键路径
