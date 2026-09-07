#!/bin/bash
# =============================================================
# Claude Agent Heartbeat — 상태 확인 & 자동 복구
# LaunchAgent에서 5분마다 호출됩니다.
#
# 점검 항목:
#   Claude Hang 감지 (살아있지만 응답 없음) — 프로세스 죽음/launcher 죽음은
#   agent-launcher.sh / LaunchAgent가 각각 담당하므로 여기서는 관여하지 않음.
#   로그인/토큰 체크는 check-login.sh(크론 프리플라이트)가 전담.
# =============================================================

export HOME="/Users/ghyu"
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# config 로드 (PROJECT_DIR)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/env.sh"

SESSION_NAME="claude-agent"
LOG_FILE="$PROJECT_DIR/logs/heartbeat.log"
HANG_MARKER="$PROJECT_DIR/logs/.hang_count"

CLAUDE_PATTERN="claude --enable-auto-mode"
LAUNCHER_PATTERN="agent-launcher\.sh"
HANG_THRESHOLD=2  # 연속 hang 감지 횟수 → 이 횟수 도달 시 재시작 (5분 × 2 = 10분)

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

reset_hang_count() {
    rm -f "$HANG_MARKER"
}

get_hang_count() {
    cat "$HANG_MARKER" 2>/dev/null || echo 0
}

increment_hang_count() {
    local count
    count=$(get_hang_count)
    echo $((count + 1)) > "$HANG_MARKER"
    echo $((count + 1))
}

is_claude_responsive() {
    local pid
    pid=$(pgrep -f "$CLAUDE_PATTERN" | head -1)
    [[ -z "$pid" ]] && return 1

    # CPU 시간이 변하고 있는지 확인 (완전히 멈춘 프로세스 감지)
    # /proc 대신 macOS의 ps 사용
    local state
    state=$(ps -o state= -p "$pid" 2>/dev/null)

    # T = stopped, Z = zombie → 비정상
    if [[ "$state" == *T* ]] || [[ "$state" == *Z* ]]; then
        return 1
    fi

    # fd 수 체크 — hang 상태면 보통 fd가 닫혀있거나 비정상
    # tmux pane에 최근 출력이 있는지 확인
    local pane_output
    pane_output=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | tail -5)
    if [[ -z "$pane_output" ]]; then
        return 1
    fi

    return 0
}

# --- 1. 프로세스 없으면 heartbeat는 관여 안 함 ---
# launcher 내부 루프(30초 주기)가 감지하고 재시작함.
# launcher 자체가 죽었으면 LaunchAgent(KeepAlive=true)가 재시작함.
if ! pgrep -f "$CLAUDE_PATTERN" > /dev/null 2>&1; then
    reset_hang_count
    log "INFO: Claude 프로세스 없음. launcher/LaunchAgent가 처리 중."
    exit 0
fi

# --- 2. Hang 감지 (살아있지만 응답 없음) ---
if ! is_claude_responsive; then
    count=$(increment_hang_count)
    log "WARNING: Claude 응답 없음 (연속 ${count}/${HANG_THRESHOLD}회)"

    if (( count >= HANG_THRESHOLD )); then
        log "ERROR: ${HANG_THRESHOLD}회 연속 무응답. 강제 재시작합니다."
        reset_hang_count
        pkill -9 -f "$CLAUDE_PATTERN" 2>/dev/null || true
        tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    fi
    exit 0
fi

# --- 3. 정상 ---
reset_hang_count
log "OK: PID=$(pgrep -f "$CLAUDE_PATTERN" | head -1)"
