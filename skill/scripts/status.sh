#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${VIDEO_SUMMARIZER_URL:-http://localhost:8000}"

# --- Parse args ---
MODE="status"
TASK_ID=""

while [ $# -gt 0 ]; do
    case "$1" in
        --task)    MODE="task"; TASK_ID="$2"; shift 2 ;;
        --cleanup) MODE="cleanup"; shift ;;
        -*)        echo "Unknown option: $1"; exit 1 ;;
        *)         echo "Unexpected argument: $1"; exit 1 ;;
    esac
done

# --- Health check ---
HEALTH=$(curl -sf --connect-timeout 3 "$BASE_URL/health" 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q '"ok"'; then
    VERSION=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
    SERVICE_UP=true
else
    SERVICE_UP=false
fi

# --- Task detail mode ---
if [ "$MODE" = "task" ]; then
    if [ "$SERVICE_UP" != true ]; then
        echo "Error: Service is not running"
        exit 1
    fi
    RESP=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks/$TASK_ID" 2>/dev/null || echo "")
    if [ -z "$RESP" ] || echo "$RESP" | grep -q '"detail"'; then
        echo "Error: Task not found ($TASK_ID)"
        exit 1
    fi
    echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
meta = d.get('metadata') or {}
title = meta.get('title', 'Unknown')
duration = meta.get('duration', 0)
platform = d.get('platform', 'unknown')
status = d.get('status', 'unknown')
summary = d.get('summary', '')
transcript = d.get('transcript', '')
error = d.get('error', '')
created = d.get('created_at', '')
completed = d.get('completed_at', '')

m, s = divmod(duration, 60)
dur_str = f'{m}m {s}s' if m > 0 else f'{s}s'

print(f'Task ID: {d.get(\"task_id\", \"\")}')
print(f'Status:  {status}')
print(f'Title:   {title}')
print(f'Duration: {dur_str} | Platform: {platform}')
print(f'Created: {created}')
if completed:
    print(f'Completed: {completed}')
print()

if summary:
    print('Summary:')
    print(summary)
    print()

if transcript:
    print('Transcript:')
    print(transcript)
    print()

if error:
    print(f'Error: {error}')
"
    exit 0
fi

# --- Cleanup mode ---
if [ "$MODE" = "cleanup" ]; then
    if [ "$SERVICE_UP" != true ]; then
        echo "Error: Service is not running"
        exit 1
    fi
    echo "Cleaning up all storage data..."
    RESP=$(curl -sf --connect-timeout 3 -X DELETE "$BASE_URL/api/storage" 2>/dev/null || echo "")
    if [ -z "$RESP" ]; then
        echo "Error: Cleanup failed"
        exit 1
    fi
    echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Deleted {d.get(\"deleted_tasks\", 0)} tasks')
print(f'Deleted {d.get(\"deleted_files\", 0)} files')
freed = d.get('freed_bytes', 0)
if freed > 1024*1024:
    print(f'Freed: {freed/1024/1024:.1f} MB')
elif freed > 1024:
    print(f'Freed: {freed/1024:.1f} KB')
else:
    print(f'Freed: {freed} B')
"
    exit 0
fi

# --- Status mode (default) ---
echo "=== Video Summarizer Status ==="

if [ "$SERVICE_UP" = true ]; then
    echo "Service: Running (v$VERSION)"
else
    echo "Service: Not running"
    echo ""
    echo "Start command:"
    echo "  cd $(dirname "$0")/../../.. && uvicorn core.main:app --port 8000"
    exit 1
fi

# Storage info
STORAGE=$(curl -sf --connect-timeout 3 "$BASE_URL/api/storage" 2>/dev/null || echo "")
if [ -n "$STORAGE" ]; then
    echo "$STORAGE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
count = d.get('task_count', 0)
total = d.get('db_size_bytes', 0) + d.get('cache_size_bytes', 0)
if total > 1024*1024:
    size_str = f'{total/1024/1024:.1f} MB'
elif total > 1024:
    size_str = f'{total/1024:.1f} KB'
else:
    size_str = f'{total} B'
print(f'Storage: {count} tasks | {size_str}')
"
fi

# Recent tasks
TASKS=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks" 2>/dev/null || echo "")
if [ -n "$TASKS" ]; then
    echo ""
    echo "Recent tasks:"
    echo "$TASKS" | python3 -c "
import sys, json
from datetime import datetime
tasks = json.load(sys.stdin).get('tasks', [])
tasks.sort(key=lambda t: t.get('created_at', ''), reverse=True)
for t in tasks[:5]:
    status = t.get('status', 'unknown')
    created = t.get('created_at', '')
    try:
        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        time_str = dt.strftime('%m-%d %H:%M')
    except:
        time_str = created[:16]
    meta = t.get('metadata') or {}
    title = meta.get('title', '')
    if not title:
        url = t.get('url', '')
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            title = p.hostname + p.path[:20]
        except:
            title = url[:30]
    print(f'  [{status:<10}] {time_str}  {title}')
"
fi
