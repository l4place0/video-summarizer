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
        echo "Error: 服务未运行"
        exit 1
    fi
    RESP=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks/$TASK_ID" 2>/dev/null || echo "")
    if [ -z "$RESP" ] || echo "$RESP" | grep -q '"detail"'; then
        echo "Error: 任务不存在 ($TASK_ID)"
        exit 1
    fi
    echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
meta = d.get('metadata') or {}
title = meta.get('title', '未知标题')
duration = meta.get('duration', 0)
platform = d.get('platform', 'unknown')
status = d.get('status', 'unknown')
summary = d.get('summary', '')
transcript = d.get('transcript', '')
error = d.get('error', '')
created = d.get('created_at', '')
completed = d.get('completed_at', '')

m, s = divmod(duration, 60)
dur_str = f'{m}分{s}秒' if m > 0 else f'{s}秒'

print(f'任务ID: {d.get(\"task_id\", \"\")}')
print(f'状态:   {status}')
print(f'标题:   {title}')
print(f'时长:   {dur_str} | 平台: {platform}')
print(f'创建:   {created}')
if completed:
    print(f'完成:   {completed}')
print()

if summary:
    print('摘要:')
    print(summary)
    print()

if transcript:
    print('转录:')
    print(transcript)
    print()

if error:
    print(f'错误: {error}')
"
    exit 0
fi

# --- Cleanup mode ---
if [ "$MODE" = "cleanup" ]; then
    if [ "$SERVICE_UP" != true ]; then
        echo "Error: 服务未运行"
        exit 1
    fi
    echo "清理所有存储数据..."
    RESP=$(curl -sf --connect-timeout 3 -X DELETE "$BASE_URL/api/storage" 2>/dev/null || echo "")
    if [ -z "$RESP" ]; then
        echo "Error: 清理失败"
        exit 1
    fi
    echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'已删除 {d.get(\"deleted_tasks\", 0)} 个任务')
print(f'已删除 {d.get(\"deleted_files\", 0)} 个文件')
freed = d.get('freed_bytes', 0)
if freed > 1024*1024:
    print(f'释放空间: {freed/1024/1024:.1f} MB')
elif freed > 1024:
    print(f'释放空间: {freed/1024:.1f} KB')
else:
    print(f'释放空间: {freed} B')
"
    exit 0
fi

# --- Status mode (default) ---
echo "=== Video Summarizer Status ==="

if [ "$SERVICE_UP" = true ]; then
    echo "服务: 运行中 (v$VERSION)"
else
    echo "服务: 未运行"
    echo ""
    echo "启动命令:"
    echo "  cd $(dirname "$0")/../../.. && uvicorn app.main:app --port 8000"
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
print(f'存储: {count} 个任务 | {size_str}')
"
fi

# Recent tasks
TASKS=$(curl -sf --connect-timeout 3 "$BASE_URL/api/tasks" 2>/dev/null || echo "")
if [ -n "$TASKS" ]; then
    echo ""
    echo "最近任务:"
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
