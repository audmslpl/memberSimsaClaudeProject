#!/bin/bash
# =============================================================
# Claude Code 로그인 상태 체크 공통 스크립트
#
# 3단계로 로그인 상태를 확인하고, 모두 실패 시 텔레그램으로 알림 후 exit 1.
#   1) claude auth status — CLI가 보고하는 로그인 상태
#   2) macOS 키체인 — 토큰 존재 여부 및 만료 시각
#   3) ~/.claude/.credentials.json — 키체인 접근 불가 시 fallback
#
# 주의: auth status가 OK여도 서버 측에서 토큰이 revoke된 경우
#       실제 API 호출 시 401이 발생할 수 있음.
#       이 케이스는 각 cron 스크립트에서 실행 결과를 검사하여 처리.
#
# 사용법: check-login.sh && <다음 명령>
#
# 변경이력:
#   2026-04-17  auth status OK인데 토큰이 서버 측 무효인 케이스 대응 주석 추가.
#               실제 API 검증은 cron 스크립트 쪽에서 후처리로 분리.
#   2026-07-28  expiresAt=0 을 '만료 없음(정상)'으로 오판하던 버그 수정.
#               0(파싱 실패/필드 없음/죽은 토큰)을 무효로 처리하여
#               죽은 토큰이 조용히 OK로 넘어가지 않고 로그인 알림이 발동하도록 함.
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/env.sh"

# 알림은 마스터(첫 번째 chat_id)에게만 전송
read -r -a _CHAT_IDS <<< "$TG_CHAT_IDS_STR"
TG_ALERT_CHAT="${_CHAT_IDS[0]}"

# 텔레그램 알림 전송 (NO_TELEGRAM_ALERT=1 이면 억제)
notify() {
  if [ "${NO_TELEGRAM_ALERT:-0}" = "1" ]; then
    return 0
  fi
  local msg="$1"
  curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TG_ALERT_CHAT}" \
    --data-urlencode "text=${msg}" > /dev/null
}

CLAUDE_BIN=/Users/ghyu/.local/bin/claude
CRED_FILE="$HOME/.claude/.credentials.json"

# 키체인 데이터를 credentials.json에 백업 (키체인 접근 가능할 때)
sync_keychain_to_file() {
  local kc_data
  kc_data=$(security find-generic-password -s "Claude Code-credentials" -a "$USER" -w 2>/dev/null)
  if [ -n "$kc_data" ]; then
    echo "$kc_data" > "$CRED_FILE" 2>/dev/null
    echo "[check-login] synced keychain → credentials.json"
  fi
}

# 모든 단계 실패 시 텔레그램 알림 + exit 1
prompt_login() {
  local reason="$1"
  echo "[check-login] $reason" >&2
  notify "⚠️ 마스터님, Claude Code 로그인이 필요해요!

사유: ${reason}

터미널에서 다시 로그인해주세요:

  claude /login

로그인 후 다음 스케줄부터 정상 동작합니다. 🌟"
  exit 1
}

NOW_MS=$(($(date +%s) * 1000))

# JSON에서 expiresAt 추출 (없거나 파싱 실패 시 0 반환)
extract_exp() {
  /usr/bin/python3 -c "import sys,json
try:
    d=json.loads(sys.stdin.read())
    o=d.get('claudeAiOauth') or d
    print(int(o.get('expiresAt',0)))
except: print(0)" 2>/dev/null
}

REASONS=()

# --- 1단계: claude auth status ---
STATUS_JSON=$("$CLAUDE_BIN" auth status 2>/dev/null)
LOGGED_IN=$(echo "$STATUS_JSON" | /usr/bin/python3 -c "import sys,json
try: print(json.load(sys.stdin).get('loggedIn',False))
except: print(False)" 2>/dev/null)
if [ "$LOGGED_IN" = "True" ]; then
  sync_keychain_to_file
  echo "[check-login] OK (auth status)"
  exit 0
fi
REASONS+=("auth status: 로그인 안 됨")

# --- 2단계: macOS 키체인 ---
KC_CRED=$(security find-generic-password -s "Claude Code-credentials" -a "$USER" -w 2>/dev/null)
if [ -n "$KC_CRED" ]; then
  KC_EXP=$(echo "$KC_CRED" | extract_exp)
  # expiresAt=0 은 파싱 실패/필드 없음/죽은 토큰을 의미하므로 무효로 처리한다.
  if [ "$KC_EXP" != "0" ] && [ "$KC_EXP" -gt "$NOW_MS" ]; then
    echo "$KC_CRED" > "$CRED_FILE" 2>/dev/null
    echo "[check-login] OK (keychain)"
    exit 0
  fi
  if [ "$KC_EXP" = "0" ]; then
    REASONS+=("키체인 토큰 무효(expiresAt=0)")
  else
    REASONS+=("키체인 토큰 만료")
  fi
else
  REASONS+=("키체인에 자격증명 없음")
fi

# --- 3단계: ~/.claude/.credentials.json fallback ---
if [ -f "$CRED_FILE" ]; then
  FILE_EXP=$(cat "$CRED_FILE" | extract_exp)
  # expiresAt=0 은 죽은 토큰. 정상으로 오판하면 실패가 조용히 묻히므로 무효 처리.
  if [ "$FILE_EXP" != "0" ] && [ "$FILE_EXP" -gt "$NOW_MS" ]; then
    echo "[check-login] OK (credentials.json)"
    exit 0
  fi
  if [ "$FILE_EXP" = "0" ]; then
    REASONS+=(".credentials.json 토큰 무효(expiresAt=0)")
  else
    REASONS+=(".credentials.json 토큰 만료")
  fi
else
  REASONS+=(".credentials.json 없음")
fi

# 모든 단계 실패 → 텔레그램 알림
prompt_login "$(IFS=' / '; echo "${REASONS[*]}")"
