## 1. ASR 抽象层

- [x] 1.1 在 `core/asr/base.py` 中定义 `BaseASR` 抽象基类，包含 `transcribe(audio_path, language) -> str` 方法
- [x] 1.2 在 `core/asr/local.py` 中实现 `LocalASR`：POST 音频文件到 `ASR_ENDPOINT`，返回转写文本
- [x] 1.3 在 `core/asr/cloud.py` 中实现 `OpenAIWhisperAPI`：调用 OpenAI Whisper API，返回转写文本
- [x] 1.4 在 `core/asr/whisper.py` 中新增 `InProcessASR` 类，包装现有 `_transcribe_once` 逻辑
- [x] 1.5 实现 `get_asr(provider: str) -> BaseASR` 工厂函数
- [x] 1.6 在 `core/config.py` 中新增配置项：`asr_provider`, `asr_endpoint`, `asr_api_key`, `asr_model`
- [x] 1.7 为 `LocalASR` 和 `OpenAIWhisperAPI` 编写单元测试（mock HTTP 响应）

## 2. CLI 入口

- [x] 2.1 在 `pyproject.toml` 中添加 `click` 依赖和 `[project.scripts]` entry point：`video-sum = "cli:main"`
- [x] 2.2 在 `cli/__init__.py` 中创建 click group 入口
- [x] 2.3 在 `cli/output.py` 中实现 JSON 输出工具函数：`emit(event, **data)` 输出 JSON 行到 stdout
- [x] 2.4 在 `cli/commands.py` 中实现 `run` 子命令：一键模式（下载→转录→分类→总结→输出）
- [x] 2.5 在 `cli/commands.py` 中实现 `submit` 子命令：提交任务返回 task_id
- [x] 2.6 在 `cli/commands.py` 中实现 `status` 子命令：查询任务状态
- [x] 2.7 在 `cli/commands.py` 中实现 `result` 子命令：获取任务结果

## 3. CLI 编排逻辑

- [x] 3.1 在 `cli/client.py` 中实现 `orchestrate()` 函数：逐步执行 pipeline，每步 emit JSON 事件
- [x] 3.2 实现本地模式：直接调用 `get_asr()` + `get_llm()` + 下载/帧提取
- [x] 3.3 实现远程模式：POST 到服务器 API + 轮询 status + 获取结果
- [x] 3.4 `run` 子命令支持 `--remote <server_url>` 参数切换本地/远程模式
- [x] 3.5 CLI 日志输出到 stderr，JSON 结果输出到 stdout
- [x] 3.6 退出码约定：0=成功，1=失败，2=部分完成

## 4. 自建 ASR 后端

- [x] 4.1 在 `whisper-server/server.py` 中实现 FastAPI 服务：`POST /transcribe` 端点
- [x] 4.2 实现模型预加载（startup event）和健康检查 `GET /health`
- [x] 4.3 在 `whisper-server/Dockerfile` 中配置 CUDA + faster-whisper 环境
- [x] 4.4 在 `whisper-server/docker-compose.yml` 中配置 GPU 透传和端口映射

## 5. 集成验证

- [x] 5.1 CLI 本地模式测试：`video-sum run <url> --asr-provider openai`，验证 JSON 输出
- [x] 5.2 CLI 远程模式测试：启动服务器，`video-sum run <url> --remote http://localhost:8000`
- [ ] 5.3 ASR 后端测试：启动 whisper-server，验证 `POST /transcribe` 返回正确格式
- [x] 5.4 验证现有 WebUI 不受影响：`uvicorn core.main:app` 正常启动和使用
