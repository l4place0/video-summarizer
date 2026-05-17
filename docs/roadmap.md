# Project Roadmap

## Phase 01 — Backend Core (done)
完整的后端服务，可通过 curl 测试。
- FastAPI 项目骨架 + Docker
- 平台抽象层 (Bilibili via yt-dlp)
- ASR (Whisper)
- LLM 抽象层 (Claude / OpenAI 协议，支持自定义端点)
- Pipeline 编排
- SQLite 存储 + 清理 API
- REST API 端点

## Phase 02 — Web UI (current)
最小可用的 Web 界面。
- 纯静态前端 (HTML + CSS + JS)，无框架
- 输入 URL，展示摘要结果
- 任务历史列表
- 存储清理入口

## Phase 03 — Skill Package
打包为 Claude Code Skill。
- SKILL.md + wrapper script
- 服务健康检测
- 参数解析与输出格式化

---

## 迭代闭环流程（每个 Phase 必须遵守）

每个阶段实现完成后，必须通过以下自检才能提交验收：

### 1. 单元测试
- 各模块独立测试，mock 外部依赖
- `python -m pytest tests/ -v` 全部通过

### 2. 集成测试（业务流自测）
- Mock 外部依赖（ffmpeg、Whisper、LLM API、网络）
- 通过真实 HTTP 请求跑完整业务流程
- 覆盖：
  - 成功路径（happy path）
  - 错误路径（无效输入、外部服务失败）
  - 状态流转（pending → ... → done / failed）
  - 数据持久化（存储、查询、清理）

### 3. 环境检查
- 记录但不阻塞：缺少 ffmpeg、API key 未配置等环境问题
- 最后阶段统一报告给用户

### 4. 验收交付物
- pytest 报告（全绿）
- 集成测试覆盖的场景清单
- 已知环境问题清单
- 手动验证命令（curl / self_check.sh）
