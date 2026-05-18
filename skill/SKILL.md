---
name: video-summarizer
description: >-
  Summarize videos from Bilibili and YouTube using ASR (Whisper) + LLM. Triggers when user
  shares a video URL, asks to summarize/transcribe a video, or types /summarize.
  Supports Chinese/English/Japanese, Claude/OpenAI providers.
  Use for: video summarization, video transcription, bilibili summary, youtube summary.
---

# Video Summarizer

Summarize videos from Bilibili and YouTube via ASR + LLM pipeline.

## How to Use

When the user provides a video URL or asks to summarize a video:

1. Extract the URL from the user's message
2. Run the summarize script:

```bash
bash skill/scripts/summarize.sh "<URL>"
```

### Options

```bash
bash skill/scripts/summarize.sh "<URL>" \
  --lang zh          # Language: zh (default), en, ja
  --provider claude  # LLM: claude (default), openai
  --detail normal    # Detail: brief, normal (default), detailed
  --mode audio       # Mode: audio (default), multimodal
```

### Multimodal Mode

When the user asks for a more visual/complete summary, use `--mode multimodal`:

```bash
bash skill/scripts/summarize.sh "<URL>" --mode multimodal
```

This extracts key frames from the video and sends them along with the audio transcript to the LLM for a richer summary that includes visual content analysis.

## Output Format

The script outputs a structured summary. Present it to the user as-is — it is already formatted.

## Service Not Running

If the script reports the service is not running, tell the user:

> Video summarizer service is not running. Start it first:
> ```bash
> cd /home/l4p/project-v && uvicorn core.main:app --port 8000
> ```

## Other Commands

### Check status

```bash
bash skill/scripts/status.sh
```

### Query specific task

```bash
bash skill/scripts/status.sh --task <task_id>
```

### Cleanup storage

```bash
bash skill/scripts/status.sh --cleanup
```
