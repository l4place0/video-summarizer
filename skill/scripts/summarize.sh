#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${VIDEO_SUMMARIZER_URL:-http://localhost:8000}"
POLL_INTERVAL=3
TIMEOUT=300

usage() {
    echo "Usage: $0 <url> [--lang LANG] [--provider PROVIDER] [--detail DETAIL] [--mode MODE] [--no-poll]"
    echo ""
    echo "Options:"
    echo "  url              Video URL (Bilibili / YouTube)"
    echo "  --lang LANG      Language: zh (default), en, ja"
    echo "  --provider LLM   Provider: claude (default), openai"
    echo "  --detail LEVEL   Detail: brief, normal (default), detailed"
    echo "  --mode MODE      Mode: audio (default), multimodal"
    echo "  --no-poll        Submit only, print task_id and exit"
    exit 1
}

# --- Parse args ---
if [ $# -lt 1 ]; then
    usage
fi

URL=""
LANG="zh"
PROVIDER="openai"
DETAIL="normal"
MODE="audio"
NO_POLL=false

while [ $# -gt 0 ]; do
    case "$1" in
        --lang)     LANG="$2"; shift 2 ;;
        --provider) PROVIDER="$2"; shift 2 ;;
        --detail)   DETAIL="$2"; shift 2 ;;
        --mode)     MODE="$2"; shift 2 ;;
        --no-poll)  NO_POLL=true; shift ;;
        -*)         echo "Unknown option: $1"; usage ;;
        *)
            if [ -z "$URL" ]; then
                URL="$1"; shift
            else
                echo "Unexpected argument: $1"; usage
            fi
            ;;
    esac
done

if [ -z "$URL" ]; then
    echo "Error: URL is required"
    usage
fi

# --- Health check ---
HEALTH=$(curl -sf --connect-timeout 3 "$BASE_URL/health" 2>/dev/null || echo "")
if ! echo "$HEALTH" | grep -q '"ok"'; then
    echo "Error: Video summarizer service is not running"
    echo ""
    echo "Start the service first:"
    echo "  cd $(dirname "$0")/../../.. && uvicorn core.main:app --port 8000"
    exit 1
fi

# --- Submit task ---
echo "Submitting task..."
RESP=$(curl -sf --connect-timeout 3 -X POST "$BASE_URL/api/summarize" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$URL\", \"language\": \"$LANG\", \"llm_provider\": \"$PROVIDER\", \"detail\": \"$DETAIL\", \"mode\": \"$MODE\"}" 2>/dev/null || echo "")

if [ -z "$RESP" ]; then
    echo "Error: Submission failed, cannot connect to service"
    exit 1
fi

TASK_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || echo "")
if [ -z "$TASK_ID" ]; then
    ERROR=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail','Unknown error'))" 2>/dev/null || echo "Unknown error")
    echo "Error: $ERROR"
    exit 1
fi

echo "Task created: $TASK_ID"

if [ "$NO_POLL" = true ]; then
    echo "$TASK_ID"
    exit 0
fi

# --- Poll ---
ELAPSED=0
STATUS_LABELS='{"pending":"Pending","downloading":"Downloading","transcribing":"Transcribing","classifying":"Classifying","extracting_frames":"Extracting frames","summarizing":"Summarizing","done":"Done","failed":"Failed"}'

while [ $ELAPSED -lt $TIMEOUT ]; do
    TASK_RESP=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks/$TASK_ID" 2>/dev/null || echo "{}")
    STATUS=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    LABEL=$(echo "$STATUS_LABELS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$STATUS','$STATUS'))" 2>/dev/null || echo "$STATUS")

    if [ "$STATUS" = "done" ]; then
        echo ""
        echo "=== Video Summary Complete ==="
        echo ""
        echo "$TASK_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
meta = d.get('metadata') or {}
title = meta.get('title', 'Unknown')
duration = meta.get('duration', 0)
platform = d.get('platform', 'unknown')
summary = d.get('summary', '')
transcript = d.get('transcript', '')
task_id = d.get('task_id', '')

m, s = divmod(duration, 60)
dur_str = f'{m}m {s}s' if m > 0 else f'{s}s'

print(f'Title: {title}')
print(f'Duration: {dur_str} | Platform: {platform}')
print()
print('Summary:')
print(summary)

if transcript:
    preview = transcript[:500]
    if len(transcript) > 500:
        preview += '...'
    print()
    print('---')
    print('Transcript (first 500 chars):')
    print(preview)

print()
print('---')
print(f'Task ID: {task_id} | Full details: /api/tasks/{task_id}')
"
        exit 0

    elif [ "$STATUS" = "failed" ]; then
        ERROR=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','Unknown error'))" 2>/dev/null || echo "Unknown error")
        echo ""
        echo "Error: Task failed — $ERROR"
        exit 1
    fi

    printf "\rStatus: %s (%ds)" "$LABEL" "$ELAPSED"
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo ""
echo "Error: Timeout (${TIMEOUT}s), task may still be running"
echo "Check manually: curl $BASE_URL/api/tasks/$TASK_ID"
exit 1
