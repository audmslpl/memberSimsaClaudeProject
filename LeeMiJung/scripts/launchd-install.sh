#!/bin/bash
# =============================================================
# cron → launchd 이전 설치 스크립트
#
# 용도:
#   날씨/주식 브리핑 6개 잡을 crontab에서 launchd LaunchAgent로 이전한다.
#   cron은 GUI 로그인 세션 밖(session 0)에서 실행되어 login keychain에
#   접근할 수 없다. 그래서 터미널에서 claude /login을 해도 cron 잡에서는
#   "키체인에 자격증명 없음"으로 계속 실패한다.
#   launchd의 gui/<uid> 도메인 잡은 사용자 Aqua 세션에서 실행되므로
#   login keychain 접근이 가능하다.
#
# 사용법:
#   ./scripts/launchd-install.sh            # 설치 + crontab 제거
#   ./scripts/launchd-install.sh --keep-cron  # 설치만, crontab 유지
#
# 동작 흐름:
#   1) 현재 crontab을 config/crontab.backup.<타임스탬프> 로 백업
#   2) 6개 plist를 gui/<uid> 도메인에 bootstrap (이미 있으면 bootout 후 재등록)
#   3) --keep-cron 이 아니면 crontab 비우기 (중복 실행 방지)
#   4) 등록된 잡 목록 출력
#
# 관련 파일:
#   ~/Library/LaunchAgents/com.ghyu.claude.{weather,stock}.{morning,lunch,evening}.plist
#
# 변경이력:
#   2026-08-04  최초 작성. cron이 키체인 접근 불가로 로그인 상태를 못 읽는
#               문제를 해결하기 위해 launchd LaunchAgent로 이전.
#   2026-08-04  crontab 제거를 `crontab -r` → `crontab /dev/null` 로 변경.
#               macOS의 crontab -r 은 삭제 확인(y/n)을 /dev/tty에서 읽어
#               비대화식 실행 시 무한 대기했음. /dev/null 설치는 동일 효과이면서
#               프롬프트가 없다.
#   2026-08-21  프로젝트 디렉토리 이름 변경(Claude/agent → Claude/LMJAgent)에 따른 경로 수정
# =============================================================

set -u

PROJECT_DIR=/Users/ghyu/Repositories/Claude/LMJAgent
LA_DIR="$HOME/Library/LaunchAgents"
UID_NUM=$(id -u)
DOMAIN="gui/$UID_NUM"
KEEP_CRON=0

[ "${1:-}" = "--keep-cron" ] && KEEP_CRON=1

LABELS=(
  com.ghyu.claude.weather.morning
  com.ghyu.claude.weather.lunch
  com.ghyu.claude.weather.evening
  com.ghyu.claude.stock.morning
  com.ghyu.claude.stock.lunch
  com.ghyu.claude.stock.evening
)

# --- 0) plist 존재 확인 ---
for L in "${LABELS[@]}"; do
  if [ ! -f "$LA_DIR/$L.plist" ]; then
    echo "❌ plist 없음: $LA_DIR/$L.plist"
    exit 1
  fi
done

# --- 1) crontab 백업 ---
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$PROJECT_DIR/config/crontab.backup.$STAMP"
if crontab -l > "$BACKUP" 2>/dev/null; then
  echo "✅ crontab 백업: $BACKUP"
else
  echo "ℹ️  기존 crontab 없음 (백업 생략)"
  rm -f "$BACKUP"
fi

# --- 2) LaunchAgent 등록 ---
for L in "${LABELS[@]}"; do
  launchctl bootout "$DOMAIN/$L" 2>/dev/null
  if launchctl bootstrap "$DOMAIN" "$LA_DIR/$L.plist" 2>&1; then
    echo "✅ 등록: $L"
  else
    echo "❌ 등록 실패: $L"
  fi
done

# --- 3) crontab 제거 (중복 실행 방지) ---
if [ "$KEEP_CRON" = "0" ]; then
  # crontab -r 은 tty에서 y/n 확인을 요구해 멈춘다. 빈 파일 설치로 대체.
  if crontab /dev/null 2>/dev/null; then
    echo "✅ crontab 비움 (복원: crontab $BACKUP)"
  else
    echo "❌ crontab 비우기 실패 — 수동 실행 필요: crontab /dev/null"
  fi
else
  echo "⚠️  --keep-cron: crontab 유지됨 → 잡이 중복 실행됩니다!"
fi

# --- 4) 결과 확인 ---
echo
echo "=== 등록된 잡 ==="
launchctl list | grep "com.ghyu.claude" || echo "(없음)"
echo
echo "다음 단계 — 키체인 접근이 실제로 되는지 확인:"
echo "  launchctl kickstart -k $DOMAIN/com.ghyu.claude.weather.lunch"
echo "  tail -20 $PROJECT_DIR/logs/weather-cron.log"
echo "  → '[check-login] OK' 가 보이면 성공"
