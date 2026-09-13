#!/bin/bash
set -euo pipefail
# =============================================================
# Claude Code Telegram Agent — tmux Launcher
# LaunchAgent에서 호출되며, tmux 세션 안에서 Claude Code를 실행합니다.
# 세션 또는 프로세스 종료 시 자동 재시작합니다.
#
# 변경이력:
#   2026-08-20  Claude 실행 옵션에 --remote-control claude-agent 추가
#   2026-08-21  프로젝트 디렉토리 이름 변경(Claude/agent → Claude/LMJAgent)에 따른 경로 수정
# =============================================================

# --- 환경변수 (반드시 다른 변수 참조 전에 설정) ---
export HOME="/Users/ghyu"
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export BUN_INSTALL="$HOME/.bun"

# --- 설정 ---
SESSION_NAME="claude-agent"
PROJECT_DIR="$HOME/Repositories/Claude/LMJAgent"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/agent.log"
LOG_MAX_SIZE=$((10 * 1024 * 1024))  # 10MB

MAX_RESTARTS=10          # COOLDOWN_WINDOW 내 최대 재시작 횟수
RESTART_DELAY=30         # 재시작 전 대기 (초)
COOLDOWN_WINDOW=600      # 카운터 리셋 기간 (초)
STARTUP_GRACE=30         # Claude 기동 대기 시간 (초) — auth/credential 로드 여유
HEALTH_CHECK_INTERVAL=30 # 헬스체크 주기 (초) — heartbeat.sh가 5분 주기로 중복 감시 중
LOGIN_RETRY_DELAY=300    # 로그인 실패 시 재시도 간격 (초, 5분)
LOGIN_ALERT_COOLDOWN=1800 # 텔레그램 알림 쿨다운 (초, 30분)

CHECK_LOGIN_SCRIPT="$PROJECT_DIR/scripts/check-login.sh"
CLAUDE_CMD="claude --enable-auto-mode --allow-dangerously-skip-permissions --dangerously-skip-permissions --remote-control claude-agent --channels plugin:telegram@claude-plugins-official"

restart_count=0
window_start=$(date +%s)
last_login_alert=0

mkdir -p "$LOG_DIR"

# --- 함수 ---

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

rotate_log() {
    if [[ -f "$LOG_FILE" ]] && (( $(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0) > LOG_MAX_SIZE )); then
        mv "$LOG_FILE" "$LOG_FILE.1"
        log "INFO: 로그 로테이션 완료"
    fi
}

is_claude_running() {
    pgrep -f "claude --enable-auto-mode" > /dev/null 2>&1
}

kill_and_wait() {
    pkill -f "claude --enable-auto-mode" 2>/dev/null || true
    local waited=0
    while (( waited < 10 )) && is_claude_running; do
        sleep 1
        waited=$((waited + 1))
    done
}

cleanup() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log "WARNING: 기존 세션 '$SESSION_NAME' 발견. 종료합니다."
        tmux kill-session -t "$SESSION_NAME"
    fi
    kill_and_wait
}

# 로그인 상태 체크. 로그인 되어 있으면 0 반환, 아니면 1.
# check-login.sh는 실패 시 텔레그램 알림을 보내지만, 런처에서 반복 호출되므로
# 스팸 방지를 위해 last_login_alert 타임스탬프로 직접 제어한다.
check_login() {
    if [[ ! -x "$CHECK_LOGIN_SCRIPT" ]]; then
        log "WARNING: check-login.sh 실행 불가 ($CHECK_LOGIN_SCRIPT). 체크 건너뜀."
        return 0
    fi

    local now
    now=$(date +%s)

    # 알림 쿨다운 윈도우 안이면 check-login.sh의 알림을 억제하고 조용히 체크
    local output
    if (( now - last_login_alert < LOGIN_ALERT_COOLDOWN )); then
        output=$(NO_TELEGRAM_ALERT=1 "$CHECK_LOGIN_SCRIPT" 2>&1) && return 0 || true
    else
        output=$("$CHECK_LOGIN_SCRIPT" 2>&1) && return 0 || true
        last_login_alert=$now
        log "WARNING: 로그인 실패 감지. 텔레그램 알림 발송됨."
    fi

    # 실패 시 로그 기록
    log "ERROR: check-login.sh 실패: $(echo "$output" | tr '\n' ' ' | cut -c1-200)"
    return 1
}

# 로그인이 될 때까지 대기 (런처의 재시작 카운터는 증가시키지 않음)
wait_for_login() {
    log "INFO: 로그인 대기 모드 진입. ${LOGIN_RETRY_DELAY}초 간격으로 재시도."
    while ! check_login; do
        sleep "$LOGIN_RETRY_DELAY"
    done
    log "INFO: 로그인 확인됨. 정상 기동 재개."
}

start_claude() {
    log "INFO: Claude Code 에이전트 시작 (시도 #$((restart_count + 1)))"

    if ! tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR"; then
        log "ERROR: tmux 세션 생성 실패"
        return 1
    fi

    tmux send-keys -t "$SESSION_NAME" "$CLAUDE_CMD" Enter
    tmux pipe-pane -t "$SESSION_NAME" -o \
        "sed 's/\x1b\[[0-9;]*[a-zA-Z]//g; s/\x1b\][^\x07]*\x07//g' >> $LOG_FILE"

    log "INFO: tmux 세션 생성 완료. Claude 기동 대기 (${STARTUP_GRACE}초)..."
    local waited=0
    while (( waited < STARTUP_GRACE )); do
        sleep 3
        waited=$((waited + 3))
        if is_claude_running; then
            log "INFO: Claude 프로세스 확인됨 (${waited}초 경과)"
            return 0
        fi
    done

    log "ERROR: ${STARTUP_GRACE}초 내에 Claude 프로세스 시작 안 됨"
    return 1
}

main() {
    log "=========================================="
    log "INFO: 에이전트 런처 시작"
    log "=========================================="

    cleanup

    while true; do
        rotate_log

        # 쿨다운 윈도우 초과 시 카운터 리셋
        local now
        now=$(date +%s)
        if (( now - window_start > COOLDOWN_WINDOW )); then
            restart_count=0
            window_start=$now
        fi

        if (( restart_count >= MAX_RESTARTS )); then
            log "FATAL: ${COOLDOWN_WINDOW}초 안에 ${MAX_RESTARTS}회 재시작 초과. 수동 점검 필요."
            exit 1
        fi

        # Claude 시작 전 로그인 상태 체크. 실패 시 대기만 하고 재시작 카운터는 증가 X.
        if ! check_login; then
            wait_for_login
            continue
        fi

        if ! start_claude; then
            restart_count=$((restart_count + 1))
            log "ERROR: 시작 실패. ${RESTART_DELAY}초 후 재시도... (${restart_count}/${MAX_RESTARTS})"
            cleanup
            sleep "$RESTART_DELAY"
            continue
        fi

        # tmux 세션과 Claude 프로세스 둘 다 감시
        while tmux has-session -t "$SESSION_NAME" 2>/dev/null && is_claude_running; do
            sleep "$HEALTH_CHECK_INTERVAL"
        done

        restart_count=$((restart_count + 1))
        log "WARNING: 세션 또는 프로세스 종료 감지. ${RESTART_DELAY}초 후 재시작... (${restart_count}/${MAX_RESTARTS})"
        cleanup
        sleep "$RESTART_DELAY"
    done
}

main
