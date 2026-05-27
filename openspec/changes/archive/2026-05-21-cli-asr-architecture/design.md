## Context

当前项目有两条使用路径：
1. WebUI — 用户通过浏览器提交 URL，pipeline 在服务器进程内运行（包含 Whisper 推理）
2. API — Skill 通过 HTTP 调用，但需要预先启动服务器

用户希望有第三条路径：CLI 直接调用，不需要启动服务器，且 CLI 包体尽可能小。

核心约束：Whisper 转录需要 torch (~2.5GB)，是唯一让 CLI 变重的依赖。

## Goals / Non-goals

**Goals:**
- CLI 包体 < 200MB（不含 torch）
- CLI 可以一键完成：`video-sum run <url>` → JSON 结果
- ASR 后端可插拔：自建 HTTP 服务或云端 API
- 与现有 WebUI 共存，互不影响

**Non-goals:**
- 不替换现有 WebUI
- 不做 CLI 的交互式界面
- 不做 ASR 服务的自动发现/负载均衡

## Decisions

### 1. ASR 抽象层设计

与 `BaseLLM` 对称的抽象：

```python
# core/asr/base.py
class BaseASR(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language: str) -> str:
        """转录音频，返回带时间戳的文本 [MM:SS] ..."""
        ...
```

实现：
- `LocalASR(endpoint)` — POST 音频到自建服务
- `OpenAIWhisperAPI(api_key)` — 调 OpenAI Whisper API
- `InProcessASR()` — 包装现有 whisper.py（WebUI 用）

选择逻辑：
```python
def get_asr() -> BaseASR:
    provider = settings.asr_provider  # "local" | "openai" | "inprocess"
    if provider == "local":
        return LocalASR(settings.asr_endpoint)
    elif provider == "openai":
        return OpenAIWhisperAPI(settings.asr_api_key)
    else:
        return InProcessASR()  # 现有 whisper.py
```

### 2. CLI 架构

```
cli/
  __init__.py      # entry point: video-sum
  commands.py      # click 子命令
  output.py        # JSON 输出
  client.py        # 编排逻辑
```

CLI 有两种运行模式：

**模式 A: 直接调 pipeline（本地模式）**
```python
# client.py
def run_local(url, language, provider, asr_provider):
    asr = get_asr(asr_provider)
    # 下载
    audio_path, metadata = download(url)
    # 转录（通过 ASR 服务）
    transcript = asr.transcribe(audio_path, language)
    # 分类 + 总结（通过 LLM API）
    llm = get_llm(provider)
    content_type = llm.classify(transcript, lang=language)
    summary = llm.summarize(transcript, lang=language, content_type=content_type)
    return {"summary": summary, "transcript": transcript, "metadata": metadata}
```

**模式 B: 调远程 API（客户端模式）**
```python
# client.py
def run_remote(url, language, provider, server_url):
    resp = httpx.post(f"{server_url}/api/summarize", json={...})
    task_id = resp.json()["task_id"]
    while True:
        status = httpx.get(f"{server_url}/api/tasks/{task_id}/status")
        if status.json()["status"] == "done":
            return httpx.get(f"{server_url}/api/tasks/{task_id}").json()
        time.sleep(2)
```

子命令：
```bash
video-sum run <url>                    # 一键模式（本地）
video-sum run <url> --remote <server>  # 一键模式（远程）
video-sum submit <url>                 # 只提交，返回 task_id
video-sum status <task_id>             # 查询状态
video-sum result <task_id>             # 获取结果
```

### 3. Pipeline 适配

现有 `run_pipeline` 是一个大函数，CLI 需要更细粒度的控制。拆分方式：

不改 `run_pipeline`（WebUI 继续用），CLI 新建一个编排函数：

```python
# cli/client.py
def orchestrate(url, language, llm_provider, asr_provider, detail, mode):
    """CLI 专用编排，逐步执行，每步输出 JSON 事件"""
    emit("downloading")
    audio_path, metadata, video_path = download(url)
    
    emit("transcribing")
    asr = get_asr(asr_provider)
    transcript = asr.transcribe(audio_path, language)
    
    emit("classifying")
    llm = get_llm(llm_provider)
    content_type = llm.classify(transcript, lang=language)
    
    emit("summarizing")
    summary = llm.summarize(transcript, ...)
    
    emit("done", summary=summary, transcript=transcript)
```

### 4. 自建 ASR 后端

```python
# whisper-server/server.py
app = FastAPI()
model = None

@app.on_event("startup")
def load_model():
    global model
    from faster_whisper import WhisperModel
    model = WhisperModel("medium", device="cuda", compute_type="float32")

@app.post("/transcribe")
async def transcribe(audio: UploadFile, language: str = "zh"):
    segments, info = model.transcribe(audio.file, language=language)
    lines = [f"[{int(s.start//60):02d}:{int(s.start%60):02d}] {s.text.strip()}" for s in segments]
    return {"transcript": "\n".join(lines), "language": info.language}
```

Dockerfile：
```dockerfile
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04
RUN pip install faster-whisper uvicorn fastapi python-multipart
COPY server.py /app/
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 5. 配置扩展

```python
# core/config.py 新增
asr_provider: str = "inprocess"       # inprocess | local | openai
asr_endpoint: str = ""                 # http://gpu-server:8001
asr_api_key: str = ""                  # OpenAI API key for Whisper
asr_model: str = "whisper-1"           # 云端模型名
```

## Risks / Trade-offs

- **[ASR 服务延迟]** 自建后端有网络开销 → 可接受，转录本身耗时 >> 网络延迟
- **[音频格式兼容]** yt-dlp 输出的格式需要 ASR 后端支持 → 统一转为 WAV/MP3
- **[CLI 模式 A 仍需 torch]** 如果用 `--asr=inprocess` 模式 → 仅 `local`/`openai` 模式不需要 torch
- **[错误处理]** ASR 服务不可用时 CLI 应该有清晰的错误信息 → 超时 + 重试 + 错误码
