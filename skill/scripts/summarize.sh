#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${VIDEO_SUMMARIZER_URL:-http://localhost:8000}"
POLL_INTERVAL=3
TIMEOUT=300

usage() {
    echo "Usage: $0 <url> [url2 ...] [--lang LANG] [--provider PROVIDER] [--detail DETAIL] [--mode MODE] [--no-poll]"
    echo ""
    echo "Options:"
    echo "  url              Video URL(s) (Bilibili / YouTube). Multiple URLs for batch submit."
    echo "  --lang LANG      Language: zh (default), en, ja"
    echo "  --provider LLM   Provider: openai (default), claude"
    echo "  --detail LEVEL   Detail: brief, normal (default), detailed"
    echo "  --mode MODE      Mode: audio (default), multimodal"
    echo "  --no-poll        Submit only, print task_id(s) and exit"
    exit 1
}

# --- Parse args ---
if [ $# -lt 1 ]; then
    usage
fi

URLS=()
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
            URLS+=("$1"); shift
            ;;
    esac
done

if [ ${#URLS[@]} -eq 0 ]; then
    echo "Error: At least one URL is required"
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

# --- Single URL: use existing single endpoint ---
if [ ${#URLS[@]} -eq 1 ]; then
    URL="${URLS[0]}"
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

    # Poll single task
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
fi

# --- Multiple URLs: use batch endpoint ---
echo "Submitting ${#URLS[@]} URLs..."
URLS_JSON=$(printf '%s\n' "${URLS[@]}" | python3 -c "
import sys, json
urls = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps(urls))
")

RESP=$(curl -sf --connect-timeout 3 -X POST "$BASE_URL/api/summarize/batch" \
    -H "Content-Type: application/json" \
    -d "{\"urls\": $URLS_JSON, \"language\": \"$LANG\", \"llm_provider\": \"$PROVIDER\", \"detail\": \"$DETAIL\", \"mode\": \"$MODE\"}" 2>/dev/null || echo "")

if [ -z "$RESP" ]; then
    echo "Error: Batch submission failed, cannot connect to service"
    exit 1
fi

TASKS=$(echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tasks = d.get('tasks', [])
skipped = d.get('skipped', [])
for t in tasks:
    print(f'{t[\"task_id\"]} {t[\"url\"]}')
if skipped:
    print(f'SKIPPED: {len(skipped)} invalid URL(s)')
" 2>/dev/null || echo "")

if [ -z "$TASKS" ]; then
    echo "Error: No valid URLs submitted"
    exit 1
fi

echo "$TASKS"
TASK_IDS=$(echo "$TASKS" | grep -v "^SKIPPED" | awk '{print $1}')

if [ "$NO_POLL" = true ]; then
    exit 0
fi

# Poll all tasks
echo ""
echo "Polling ${#URLS[@]} tasks..."
ELAPSED=0
TOTAL=$(echo "$TASK_IDS" | wc -l)
COMPLETED=0
FAILED=0

declare -A TASK_STATUS
for TID in $TASK_IDS; do
    TASK_STATUS[$TID]="pending"
done

while [ $ELAPSED -lt $TIMEOUT ]; do
    COMPLETED=0
    FAILED=0
    for TID in $TASK_IDS; do
        STATUS="${TASK_STATUS[$TID]}"
        if [ "$STATUS" = "done" ] || [ "$STATUS" = "failed" ]; then
            if [ "$STATUS" = "done" ]; then COMPLETED=$((COMPLETED+1)); else FAILED=$((FAILED+1)); fi
            continue
        fi
        TASK_RESP=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks/$TID" 2>/dev/null || echo "{}")
        NEW_STATUS=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
        TASK_STATUS[$TID]="$NEW_STATUS"
        if [ "$NEW_STATUS" = "done" ]; then COMPLETED=$((COMPLETED+1)); elif [ "$NEW_STATUS" = "failed" ]; then FAILED=$((FAILED+1)); fi
    done

    DONE=$((COMPLETED + FAILED))
    printf "\rBatch progress: %d/%d done, %d failed (%ds)" "$DONE" "$TOTAL" "$FAILED" "$ELAPSED"

    if [ "$DONE" -eq "$TOTAL" ]; then
        echo ""
        echo ""
        echo "=== Batch Complete ==="
        echo "Completed: $COMPLETED | Failed: $FAILED"
        for TID in $TASK_IDS; do
            STATUS="${TASK_STATUS[$TID]}"
            echo "  [$STATUS] $TID"
        done
        exit 0
    fi

    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo ""
echo "Error: Timeout (${TIMEOUT}s), some tasks may still be running"
for TID in $TASK_IDS; do
    STATUS="${TASK_STATUS[$TID]}"
    if [ "$STATUS" != "done" ] && [ "$STATUS" != "failed" ]; then
        echo "  [pending] $TID"
    fi
done
exit 1
