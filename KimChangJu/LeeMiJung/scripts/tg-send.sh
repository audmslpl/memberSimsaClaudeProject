#!/bin/bash
# =============================================================
# Telegram 메시지 전송 헬퍼
# config/env.sh의 TG_BOT_TOKEN, TG_CHAT_IDS_STR을 사용해
# 등록된 모든 chat_id에 동일 메시지를 전송합니다.
#
# 사용법:
#   scripts/tg-send.sh "메시지 본문"
#   scripts/tg-send.sh -c 123456789 "특정 사용자에게만"   # 단일 수신자
#   echo "메시지" | scripts/tg-send.sh                       # stdin
#
# 출력: 각 chat_id 전송 결과(ok:true/false) 한 줄씩
# 반환: 전부 성공 시 0, 하나라도 실패 시 1
#
# 변경이력:
#   2026-09-03  사용법 주석의 실제 chat_id 예시를 더미 값으로 교체
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/env.sh"

SINGLE_CHAT=""
if [ "${1:-}" = "-c" ]; then
    SINGLE_CHAT="$2"
    shift 2
fi

# 메시지: 인자 우선, 없으면 stdin
if [ $# -gt 0 ]; then
    MSG="$*"
else
    MSG=$(cat)
fi

if [ -z "$MSG" ]; then
    echo "Error: 메시지가 비어있습니다." >&2
    exit 2
fi

# 대상 chat_id 결정
if [ -n "$SINGLE_CHAT" ]; then
    CHAT_IDS=("$SINGLE_CHAT")
else
    read -r -a CHAT_IDS <<< "$TG_CHAT_IDS_STR"
fi

fail=0
for cid in "${CHAT_IDS[@]}"; do
    resp=$(curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${cid}" \
        --data-urlencode "text=${MSG}")
    ok=$(echo "$resp" | /usr/bin/python3 -c "import sys,json
try: print(json.load(sys.stdin).get('ok',False))
except: print(False)" 2>/dev/null)
    if [ "$ok" != "True" ]; then
        echo "chat_id=${cid}: ok=${ok} — retrying in 5s..."
        sleep 5
        resp=$(curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
            --data-urlencode "chat_id=${cid}" \
            --data-urlencode "text=${MSG}")
        ok=$(echo "$resp" | /usr/bin/python3 -c "import sys,json
try: print(json.load(sys.stdin).get('ok',False))
except: print(False)" 2>/dev/null)
    fi
    echo "chat_id=${cid}: ok=${ok}"
    [ "$ok" = "True" ] || fail=1
done

exit $fail
