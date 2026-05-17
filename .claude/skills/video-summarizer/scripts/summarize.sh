#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${VIDEO_SUMMARIZER_URL:-http://localhost:8000}"
POLL_INTERVAL=3
TIMEOUT=300

usage() {
    echo "Usage: $0 <url> [--lang LANG] [--provider PROVIDER] [--detail DETAIL] [--mode MODE] [--no-poll]"
    echo ""
    echo "Options:"
    echo "  url              Video URL (Bilibili)"
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
PROVIDER="claude"
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
    echo "Error: 视频摘要服务未运行"
    echo ""
    echo "请先启动服务:"
    echo "  cd $(dirname "$0")/../../.. && uvicorn app.main:app --port 8000"
    exit 1
fi

# --- Submit task ---
echo "提交任务..."
RESP=$(curl -sf --connect-timeout 3 -X POST "$BASE_URL/api/summarize" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$URL\", \"language\": \"$LANG\", \"llm_provider\": \"$PROVIDER\", \"detail\": \"$DETAIL\", \"mode\": \"$MODE\"}" 2>/dev/null || echo "")

if [ -z "$RESP" ]; then
    echo "Error: 提交失败，无法连接服务"
    exit 1
fi

TASK_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || echo "")
if [ -z "$TASK_ID" ]; then
    ERROR=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail','未知错误'))" 2>/dev/null || echo "未知错误")
    echo "Error: $ERROR"
    exit 1
fi

echo "任务已创建: $TASK_ID"

if [ "$NO_POLL" = true ]; then
    echo "$TASK_ID"
    exit 0
fi

# --- Poll ---
ELAPSED=0
STATUS_LABELS='{"pending":"等待中","downloading":"下载中","transcribing":"转录中","extracting_frames":"提取关键帧中","summarizing":"总结中","done":"完成","failed":"失败"}'

while [ $ELAPSED -lt $TIMEOUT ]; do
    TASK_RESP=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks/$TASK_ID" 2>/dev/null || echo "{}")
    STATUS=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    LABEL=$(echo "$STATUS_LABELS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$STATUS','$STATUS'))" 2>/dev/null || echo "$STATUS")

    if [ "$STATUS" = "done" ]; then
        echo ""
        echo "=== 视频摘要完成 ==="
        echo ""
        echo "$TASK_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
meta = d.get('metadata') or {}
title = meta.get('title', '未知标题')
duration = meta.get('duration', 0)
platform = d.get('platform', 'unknown')
summary = d.get('summary', '')
transcript = d.get('transcript', '')
task_id = d.get('task_id', '')

m, s = divmod(duration, 60)
dur_str = f'{m}分{s}秒' if m > 0 else f'{s}秒'

print(f'标题: {title}')
print(f'时长: {dur_str} | 平台: {platform}')
print()
print('摘要:')
print(summary)

if transcript:
    preview = transcript[:500]
    if len(transcript) > 500:
        preview += '...'
    print()
    print('---')
    print(f'转录原文 (前 500 字):')
    print(preview)

print()
print(f'---')
print(f'任务ID: {task_id} | 完整详情: /api/tasks/{task_id}')
"
        exit 0

    elif [ "$STATUS" = "failed" ]; then
        ERROR=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','未知错误'))" 2>/dev/null || echo "未知错误")
        echo ""
        echo "Error: 任务失败 — $ERROR"
        exit 1
    fi

    printf "\r状态: %s (%ds)" "$LABEL" "$ELAPSED"
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo ""
echo "Error: 超时 (${TIMEOUT}s)，任务可能仍在运行"
echo "手动查询: curl $BASE_URL/api/tasks/$TASK_ID"
exit 1
