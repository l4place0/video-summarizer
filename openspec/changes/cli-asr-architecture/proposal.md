## Why

当前项目是纯 WebUI 架构（FastAPI + 浏览器），Skill 调用只能通过 HTTP API，需要预先启动服务器。用户希望有一个轻量 CLI 作为编排层，让 Skill 可以直接 `video-sum run <url>` 一行调用。

核心问题：Whisper 转录是唯一重计算环节（需要 torch ~2.5GB + CUDA），如果 CLI 自包含所有依赖，包体会很大。解决方案是将 ASR 抽象为可插拔服务层 — CLI 做编排，ASR 推理可以是自建后端或云端 API。

## What Changes

### ASR 服务抽象层
- 新增 `BaseASR` 抽象基类（与 `BaseLLM` 对称）
- 实现 `LocalASR`（调自建 HTTP 后端）、`OpenAIWhisperAPI`（调 OpenAI Whisper API）
- 通过配置切换：`ASR_PROVIDER=local|openai`

### 轻量 CLI 入口
- 新增 `cli/` 模块，使用 `click` 构建子命令
- 子命令：`submit`（提交）、`status`（查询）、`result`（获取结果）、`run`（一键模式）
- 输出为 JSON（stdout），日志去 stderr，适合 Skill 解析
- CLI 只依赖 yt-dlp + httpx + click，不含 torch

### 自建 ASR 后端
- 新增 `whisper-server/` 目录，独立 FastAPI 服务
- Dockerfile 使用 nvidia/cuda base + faster-whisper
- 暴露 `POST /transcribe` 端点

### 现有 WebUI 保留
- WebUI 继续使用进程内 Whisper（不经过 ASR 服务）
- CLI 和 WebUI 共享 pipeline 核心逻辑，但 ASR 调用路径不同

## Capabilities

### New Capabilities
- `cli-orchestration`: 轻量 CLI 入口，JSON 结构化 I/O，适合 Skill 和脚本调用
- `asr-service-abstraction`: ASR 可插拔后端（自建/云端），通过配置切换
- `whisper-server`: 自建 Whisper HTTP 推理服务，Docker 部署

### Modified Capabilities
- 无（WebUI 和现有 API 不受影响）

## Impact

### 新增文件
- `core/asr/base.py` — `BaseASR` 抽象基类
- `core/asr/local.py` — `LocalASR`（调 HTTP 后端）
- `core/asr/cloud.py` — `OpenAIWhisperAPI`（调云端 API）
- `cli/__init__.py` — CLI 入口
- `cli/commands.py` — 子命令实现
- `cli/output.py` — JSON 输出格式化
- `cli/client.py` — API 客户端（调本地 pipeline 或远程服务器）
- `whisper-server/server.py` — ASR HTTP 服务
- `whisper-server/Dockerfile` — CUDA + faster-whisper 容器
- `whisper-server/docker-compose.yml` — 部署配置

### 修改文件
- `core/asr/whisper.py` — 保留进程内转录，但重构为使用 `BaseASR` 接口
- `core/pipeline.py` — ASR 调用改为通过抽象层
- `pyproject.toml` — 添加 click 依赖，添加 CLI entry point

## Non-goals

- 不改现有 WebUI 的使用方式
- 不移除进程内 Whisper（WebUI 仍然直接用）
- 不做多用户/认证
- 不做 CLI 的交互式 TUI
