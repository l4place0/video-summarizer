---
name: video-summarizer
description: >-
  Summarize videos from Bilibili using ASR (Whisper) + LLM. Triggers when user
  shares a Bilibili video URL, asks to summarize/transcribe a video, or types
  /summarize. Supports Chinese/English/Japanese, Claude/OpenAI providers.
  Use for: video summarization, video transcription, bilibili summary.
---

# Video Summarizer

Summarize Bilibili videos via ASR + LLM pipeline.

## How to Use

When the user provides a video URL or asks to summarize a video:

1. Extract the URL from the user's message
2. Run the summarize script:

```bash
bash .claude/skills/video-summarizer/scripts/summarize.sh "<URL>"
```

### Options

```bash
bash .claude/skills/video-summarizer/scripts/summarize.sh "<URL>" \
  --lang zh          # Language: zh (default), en, ja
  --provider claude  # LLM: claude (default), openai
  --detail normal    # Detail: brief, normal (default), detailed
  --mode audio       # Mode: audio (default), multimodal
```

### Multimodal Mode

When the user asks for a more visual/complete summary, use `--mode multimodal`:

```bash
bash .claude/skills/video-summarizer/scripts/summarize.sh "<URL>" --mode multimodal
```

This extracts key frames from the video and sends them along with the audio transcript to the LLM for a richer summary that includes visual content analysis.

## Output Format

The script outputs a structured summary. Present it to the user as-is — it is already formatted.

## Service Not Running

If the script reports the service is not running, tell the user:

> 视频摘要服务未运行。请先启动：
> ```bash
> cd /home/l4p/project-v && uvicorn app.main:app --port 8000
> ```

## Other Commands

### Check status

```bash
bash .claude/skills/video-summarizer/scripts/status.sh
```

### Query specific task

```bash
bash .claude/skills/video-summarizer/scripts/status.sh --task <task_id>
```

### Cleanup storage

```bash
bash .claude/skills/video-summarizer/scripts/status.sh --cleanup
```
