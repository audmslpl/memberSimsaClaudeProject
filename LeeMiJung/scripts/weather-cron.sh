#!/bin/bash
# =============================================================
# 날씨 브리핑 cron 스크립트
#
# 사용법: weather-cron.sh [morning|lunch|evening]
#
# 스케줄러: launchd LaunchAgent (2026-08-04 cron에서 이전)
#   ~/Library/LaunchAgents/com.ghyu.claude.weather.{morning,lunch,evening}.plist
#   morning 08:00 / lunch 12:00 / evening 18:00 (매일)
#   수동 실행: launchctl kickstart -k gui/$(id -u)/com.ghyu.claude.weather.lunch
#
# 동작 흐름:
#   1) check-login.sh로 사전 로그인 체크 (명백한 로그아웃 감지)
#   2) claude -p로 스킬 실행
#   3) 실행 결과에서 인증 에러 감지 시 텔레그램 알림
#      (auth status OK인데 서버 측 토큰 무효인 경우 대응)
#
# 변경이력:
#   2026-04-17  실행 결과 기반 인증 에러 감지 + 텔레그램 알림 추가.
#               check-login.sh만으로 잡지 못하는 서버 측 토큰 무효 대응.
#   2026-08-04  crontab → launchd LaunchAgent로 스케줄러 이전.
#               cron은 GUI 세션 밖이라 login keychain 접근이 불가해
#               매 실행이 "키체인에 자격증명 없음"으로 실패했음.
#   2026-08-21  프로젝트 디렉토리 이름 변경(Claude/agent → Claude/LMJAgent)에 따른 경로 수정
# =============================================================

MODE=${1:-morning}
PROJECT_DIR=/Users/ghyu/Repositories/Claude/LMJAgent
LOG_FILE="$PROJECT_DIR/logs/weather-cron.log"
CLAUDE_BIN=/Users/ghyu/.local/bin/claude

cd "$PROJECT_DIR"

# --- 1) 사전 로그인 체크 (비용 없음) ---
if ! "$PROJECT_DIR/scripts/check-login.sh" >> "$LOG_FILE" 2>&1; then
  echo "=== $(date) | login check failed, abort $MODE ===" >> "$LOG_FILE"
  exit 1
fi

# --- 2) 모드별 스킬 실행 ---
case "$MODE" in
  evening) COMMAND="weather-evening 스킬을 실행해줘" ;;
  lunch)   COMMAND="weather-lunch 스킬을 실행해줘" ;;
  *)       COMMAND="weather-morning 스킬을 실행해줘" ;;
esac

echo "=== $(date) | $MODE briefing ===" >> "$LOG_FILE"
OUTPUT=$(cd "$PROJECT_DIR" && "$CLAUDE_BIN" -p "$COMMAND" --dangerously-skip-permissions 2>&1)
echo "$OUTPUT" >> "$LOG_FILE"

# --- 3) 실행 결과에서 인증 에러 감지 → 마스터에게 텔레그램 알림 ---
if echo "$OUTPUT" | grep -q "authentication_error\|401\|Invalid authentication"; then
  source "$PROJECT_DIR/config/env.sh"
  read -r -a _CHAT_IDS <<< "$TG_CHAT_IDS_STR"
  "$PROJECT_DIR/scripts/tg-send.sh" -c "${_CHAT_IDS[0]}" \
    "⚠️ 마스터님, 날씨 브리핑($MODE) 실행 중 인증 오류가 발생했어요!

Claude Code 토큰이 만료된 것 같습니다.
터미널에서 다시 로그인해주세요:

  claude /login"
  exit 1
fi
