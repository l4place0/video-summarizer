# Phase 04 — 多模态视频总结

## 目标
支持视频关键帧采样 + 音频转录联合总结，利用 LLM 视觉能力理解视频画面内容。

## 设计思路

当前 pipeline：`下载 → 提取音频 → Whisper转录 → LLM文本总结`

新增 pipeline：`下载 → 提取音频 → Whisper转录 → 提取关键帧 → LLM多模态总结(文本+图片)`

两种模式共存，通过请求参数 `mode` 切换：
- `audio`（默认）：纯音频模式，兼容现有行为
- `multimodal`：关键帧 + 音频联合总结

## 模块清单

### 1. 关键帧提取模块 (`app/vision/frames.py`)

#### 功能
从视频文件中提取关键帧图片。

#### 接口
```python
def extract_frames(
    video_path: Path,
    output_dir: Path,
    max_frames: int = 10,
    mode: str = "interval",  # "interval" | "scene"
    interval: int = 30,       # 秒，interval 模式用
    scene_threshold: float = 0.3,  # scene 模式用
) -> list[Path]:
    """提取关键帧，返回帧图片路径列表。"""
```

#### 实现策略
- **interval 模式**：每隔 N 秒截取一帧，用 ffmpeg `-vf fps=1/N`
- **scene 模式**：ffmpeg scene detection (`select='gt(scene,T)'`)
- 输出格式：JPEG，分辨率缩放到 720p 以控制大小
- 帧数上限：默认 10 帧（控制 LLM token 消耗）

#### ffmpeg 命令
```bash
# interval 模式：每 30 秒一帧
ffmpeg -i video.mp4 -vf "fps=1/30,scale=1280:-2" -q:v 3 frame_%03d.jpg

# scene 模式：场景变化检测
ffmpeg -i video.mp4 -vf "select='gt(scene,0.3)',scale=1280:-2" -vsync vfr -q:v 3 frame_%03d.jpg
```

### 2. LLM 多模态支持

#### BaseLLM 新增方法
```python
class BaseLLM(ABC):
    @abstractmethod
    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal") -> str:
        """纯文本总结（现有）"""
        ...

    def summarize_multimodal(
        self, transcript: str, frames: list[Path], lang: str = "zh", detail: str = "normal"
    ) -> str:
        """多模态总结：文本 + 关键帧。默认回退到纯文本。"""
        return self.summarize(transcript, lang, detail)
```

#### Claude 实现 (`app/llm/claude.py`)
```python
def summarize_multimodal(self, transcript, frames, lang="zh", detail="normal"):
    content = []
    # 添加图片
    for frame_path in frames:
        b64 = base64.b64encode(frame_path.read_bytes()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })
    # 添加文本提示
    content.append({"type": "text", "text": prompt})
    # 调用 API
    message = self.client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
```

#### OpenAI 实现 (`app/llm/openai_proto.py`)
```python
def summarize_multimodal(self, transcript, frames, lang="zh", detail="normal"):
    content = []
    for frame_path in frames:
        b64 = base64.b64encode(frame_path.read_bytes()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    content.append({"type": "text", "text": prompt})
    response = self.client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": content}],
        max_tokens=4096,
    )
```

#### 多模态提示词
```
请根据以下视频关键帧截图和音频转录文本，对视频内容进行全面总结。
关键帧展示了视频中的重要画面，请结合画面内容和转录文本进行分析。

[转录文本]
{transcript}
```

### 3. Pipeline 改动 (`app/core/pipeline.py`)

```python
# 新增步骤：提取关键帧（仅 multimodal 模式）
if mode == "multimodal":
    db.update_task(task_id, status="extracting_frames")
    frames = extract_frames(video_path, frame_dir, ...)
    summary = llm.summarize_multimodal(transcript, frames, ...)
else:
    summary = llm.summarize(transcript, ...)
```

#### 状态流转
- `audio` 模式：pending → downloading → transcribing → summarizing → done
- `multimodal` 模式：pending → downloading → transcribing → extracting_frames → summarizing → done

#### 关键改动：保留视频文件
当前 pipeline 在提取音频后删除视频文件。multimodal 模式需要保留视频直到帧提取完成。

### 4. 模型改动 (`app/core/models.py`)

#### TaskStatus 新增
```python
EXTRACTING_FRAMES = "extracting_frames"
```

#### SummarizeRequest 新增
```python
mode: str = "audio"  # "audio" | "multimodal"
```

### 5. 配置改动 (`app/core/config.py`)

```python
# 视觉
frame_mode: str = "interval"        # "interval" | "scene"
max_frames: int = 10                 # 最大帧数
frame_interval: int = 30             # 秒，interval 模式
scene_threshold: float = 0.3         # scene 模式阈值
```

### 6. Web UI 改动

#### 输入区
新增模式选择：`[音频模式▾]` → 下拉：音频模式 / 多模态模式

#### 结果区
状态新增 `extracting_frames` → 显示 "提取关键帧中..."

#### JS 改动
- 提交时传入 `mode` 参数
- 状态标签新增 `extracting_frames: "提取关键帧中"`

### 7. Skill 改动

#### summarize.sh
新增 `--mode` 参数：
```bash
bash scripts/summarize.sh <url> --mode multimodal
```

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/vision/__init__.py` | 新建 | 模块初始化 |
| `app/vision/frames.py` | 新建 | 关键帧提取 |
| `app/llm/base.py` | 修改 | 新增 `summarize_multimodal` 方法 |
| `app/llm/claude.py` | 修改 | 实现多模态总结 |
| `app/llm/openai_proto.py` | 修改 | 实现多模态总结 |
| `app/core/pipeline.py` | 修改 | 新增帧提取步骤，保留视频文件 |
| `app/core/models.py` | 修改 | 新增 `EXTRACTING_FRAMES` 状态和 `mode` 字段 |
| `app/core/config.py` | 修改 | 新增视觉配置 |
| `app/web/app.js` | 修改 | 支持模式选择和新状态 |
| `app/web/index.html` | 修改 | 新增模式下拉框 |
| `.claude/skills/video-summarizer/scripts/summarize.sh` | 修改 | 新增 `--mode` 参数 |
| `.claude/skills/video-summarizer/SKILL.md` | 修改 | 文档更新 |
| `tests/test_vision.py` | 新建 | 帧提取单元测试 |
| `tests/test_integration.py` | 修改 | 新增多模态集成测试 |

## 验收标准

### 功能验收

| # | 场景 | 预期结果 |
|---|------|---------|
| 1 | `mode=audio` | 行为与现有完全一致 |
| 2 | `mode=multimodal` + Bilibili URL | 下载→转录→提取帧→多模态总结 |
| 3 | 多模态总结输出 | 摘要包含画面描述，比纯文本更丰富 |
| 4 | 帧提取失败 | 回退到纯文本模式，不阻塞 |
| 5 | Web UI 模式选择 | 下拉切换，提交时传入 mode |
| 6 | Skill `--mode multimodal` | 完整流程跑通 |
| 7 | 帧数量控制 | 不超过 max_frames 配置 |
| 8 | 大视频处理 | 10 分钟视频，帧提取 < 30 秒 |

### 非功能验收

| 维度 | 要求 |
|------|------|
| 向后兼容 | `mode=audio` 行为不变，测试不回归 |
| 帧大小 | 单帧 < 200KB，总帧 < 2MB |
| token 控制 | 10 帧 + 转录不超过模型上下文限制 |
| 错误处理 | 帧提取失败回退，LLM 图片错误回退 |

### 验收命令

```bash
# 纯文本模式（回归）
bash .claude/skills/video-summarizer/scripts/summarize.sh <url>

# 多模态模式
bash .claude/skills/video-summarizer/scripts/summarize.sh <url> --mode multimodal

# Web UI
# 选择"多模态模式"下拉，提交视频 URL
```
