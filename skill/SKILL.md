---
name: bilibili-learning-helper
description: >-
  Summarize videos from Bilibili and YouTube using ASR (Whisper) + LLM.
  Supports single and batch URL submission, Chinese/English/Japanese,
  Claude/OpenAI providers, multimodal mode with frame analysis.
  Features: task retry, progress tracking, Markdown export to Obsidian,
  history search/filter, version update check.
  Triggers when user shares a video URL, asks to summarize/transcribe a video,
  or types /summarize.
---

# Bilibili Learning Helper

Summarize videos from Bilibili and YouTube via ASR + LLM pipeline.

## How to Use

### Single URL

When the user provides a video URL or asks to summarize a video:

```bash
bash skill/scripts/summarize.sh "<URL>"
```

### Batch Submit

When the user provides multiple URLs or asks to summarize several videos:

```bash
bash skill/scripts/summarize.sh "<URL1>" "<URL2>" "<URL3>"
```

Each URL is submitted as an independent task. Invalid URLs are skipped and reported.

### Options

```bash
bash skill/scripts/summarize.sh "<URL>" \
  --lang zh          # Language: zh (default), en, ja
  --provider openai  # LLM: openai (default), claude
  --detail normal    # Detail: brief, normal (default), detailed
  --mode multimodal  # Mode: audio (default), multimodal
  --no-poll          # Submit only, print task_id and exit
```

### Multimodal Mode

For a richer summary with visual content analysis:

```bash
bash skill/scripts/summarize.sh "<URL>" --mode multimodal
```

This extracts key frames from the video and sends them along with the transcript to the LLM.

## Task Retry

If a task fails, retry it via the WebUI (click "Retry" button on the failed task) or via API:

```bash
curl -X POST http://localhost:8000/api/tasks/<task_id>/retry
```

## Progress Tracking

Tasks show real-time progress within each stage:
- Downloading: 10-25%
- Transcribing: 25-50%
- Extracting frames: 50-70%
- Classifying: 75%
- Summarizing: 90%
- Done: 100%

## Markdown Export

After a task completes, click "Export Markdown" in the WebUI to copy an Obsidian-compatible
Markdown with YAML frontmatter (title, author, tags, duration, etc.) to clipboard.

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

## Service Not Running

If the script reports the service is not running, tell the user:

> Video summarizer service is not running. Start it first:
> ```bash
> cd /home/l4p/project-v && uvicorn core.main:app --port 8000
> ```
