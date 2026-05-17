#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0
SKIP=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "pass" ]; then
        echo "  [PASS] $name"
        ((PASS++))
    elif [ "$result" = "skip" ]; then
        echo "  [SKIP] $name"
        ((SKIP++))
    else
        echo "  [FAIL] $name"
        ((FAIL++))
    fi
}

echo "=== Video Summarizer Self-Check ==="
echo ""

# 1. Health check
echo "1. Health Check"
HEALTH=$(curl -sf "$BASE_URL/health" 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"ok"'; then
    check "GET /health" "pass"
else
    check "GET /health" "fail"
    echo ""
    echo "Service not running. Start with: docker compose up -d"
    exit 1
fi

# 2. Invalid URL handling
echo ""
echo "2. Error Handling"
INVALID_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/api/summarize" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://youtube.com/watch?v=abc"}' 2>/dev/null || echo "000")
if [ "$INVALID_STATUS" = "400" ]; then
    check "Invalid URL returns 400" "pass"
else
    check "Invalid URL returns 400" "fail"
fi

# 3. Storage endpoints
echo ""
echo "3. Storage"
STORAGE=$(curl -sf "$BASE_URL/api/storage" 2>/dev/null || echo "FAIL")
if echo "$STORAGE" | grep -q 'db_size_bytes'; then
    check "GET /api/storage" "pass"
else
    check "GET /api/storage" "fail"
fi

# 4. Task list
echo ""
echo "4. Tasks"
TASKS=$(curl -sf "$BASE_URL/api/tasks" 2>/dev/null || echo "FAIL")
if echo "$TASKS" | grep -q 'tasks'; then
    check "GET /api/tasks" "pass"
else
    check "GET /api/tasks" "fail"
fi

# 5. Full pipeline (requires API keys)
echo ""
echo "5. Full Pipeline"
if [ -f .env ] && grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
    echo "  Submitting test video..."
    RESP=$(curl -sf -X POST "$BASE_URL/api/summarize" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://www.bilibili.com/video/BV1GJ411x7h7", "language": "zh"}' 2>/dev/null || echo "FAIL")
    if echo "$RESP" | grep -q 'task_id'; then
        TASK_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null || echo "")
        if [ -n "$TASK_ID" ]; then
            check "Submit task" "pass"
            echo "  Polling task $TASK_ID ..."
            for i in $(seq 1 60); do
                STATUS_RESP=$(curl -sf "$BASE_URL/api/tasks/$TASK_ID" 2>/dev/null || echo "{}")
                STATUS=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
                if [ "$STATUS" = "done" ]; then
                    check "Pipeline completed" "pass"
                    SUMMARY=$(echo "$STATUS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('summary','')[:100])" 2>/dev/null || echo "")
                    echo "  Summary preview: ${SUMMARY:0:100}..."
                    break
                elif [ "$STATUS" = "failed" ]; then
                    check "Pipeline completed" "fail"
                    echo "  Error: $(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null)"
                    break
                fi
                sleep 5
            done
            if [ "$STATUS" != "done" ] && [ "$STATUS" != "failed" ]; then
                check "Pipeline completed" "fail"
                echo "  Timeout after 5 minutes"
            fi
        else
            check "Submit task" "fail"
        fi
    else
        check "Submit task" "fail"
    fi
else
    check "Full pipeline (no API key configured)" "skip"
fi

# 6. Storage cleanup
echo ""
echo "6. Cleanup"
CLEANUP=$(curl -sf -X DELETE "$BASE_URL/api/storage" 2>/dev/null || echo "FAIL")
if echo "$CLEANUP" | grep -q 'deleted_files'; then
    check "DELETE /api/storage" "pass"
else
    check "DELETE /api/storage" "fail"
fi

# Summary
echo ""
echo "=== Results ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "Some checks failed."
    exit 1
else
    echo "All checks passed."
    exit 0
fi
