# Video Summarizer

LLM-powered video summarization tool. Downloads video from Bilibili, transcribes audio with Whisper, then uses Claude or OpenAI-compatible LLMs to generate structured summaries.

## Features

- **Two-stage prompt system** — Classifies video content type first, then routes to specialized prompts for structured output
- **Multimodal support** — Extracts key frames and combines with transcript for visual-aware summaries
- **Video cache** — Same video ID skips download and transcription on repeat requests
- **Web UI** — Browser-based interface with task history and real-time status
- **Skill integration** — Claude Code skill scripts for CLI usage
- **Multi-language** — Chinese, English, Japanese output
- **Multi-provider** — Claude and OpenAI-compatible endpoints (tested with MIMO)

## Quick Start

See [INSTALL.md](INSTALL.md) for detailed setup.

```bash
# Install
uv sync
cp .env.example .env  # edit with your API keys

# Start
uv run uvicorn app.main:app --port 8000

# Use
bash .claude/skills/video-summarizer/scripts/summarize.sh "https://bilibili.com/video/BVxxxxx"
```

## Architecture

```
URL → Download (yt-dlp) → Audio Extract (ffmpeg) → Transcribe (Whisper)
                                                          ↓
                               Classify (LLM Stage 1) ← transcript
                                    ↓
                          Route to specialized prompt
                                    ↓
                          Summarize (LLM Stage 2) → structured output
```

### Content Type Routing

The system first classifies videos into one of 7 types, then applies a tailored prompt:

| Type | Description | Output Structure |
|------|-------------|-----------------|
| tutorial | How-to guides | Steps, prerequisites, pitfalls |
| tech_talk | Tech speeches | Core argument, evidence, outlook |
| demo | Product demos | Workflow, input/output, strengths |
| review | Comparisons | Subjects, criteria, recommendations |
| news | Current events | Facts, context, perspectives |
| vlog | Daily content | Scenes, notable points |
| general | Fallback | Core content, key points, analysis |

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/summarize` | POST | Submit video for summarization |
| `/api/tasks` | GET | List all tasks |
| `/api/tasks/{id}` | GET | Get task detail |
| `/api/storage` | GET | Storage usage info |
| `/api/storage` | DELETE | Clear all data |

### Submit Request

```json
{
  "url": "https://bilibili.com/video/BVxxxxx",
  "language": "zh",
  "llm_provider": "openai",
  "detail": "normal",
  "mode": "audio"
}
```

- `mode`: `audio` (text-only) or `multimodal` (frames + transcript)

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | | OpenAI/MIMO API key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API endpoint |
| `OPENAI_MODEL` | `gpt-4o` | Text model |
| `OPENAI_VISION_MODEL` | | Vision model for multimodal (e.g. `mimo-v2-omni`) |
| `ANTHROPIC_API_KEY` | | Claude API key |
| `WHISPER_MODEL` | `base` | Whisper model size |
| `MAX_FRAMES` | `10` | Max frames for multimodal |

## Tech Stack

- Python 3.10+, FastAPI, uv
- Whisper (ASR), yt-dlp (download), ffmpeg (audio/video processing)
- Claude / OpenAI-compatible LLMs

## License

MIT
