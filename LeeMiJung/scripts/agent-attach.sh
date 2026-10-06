#!/bin/bash
# tmux 세션에 읽기 전용으로 연결 (리사이즈 방지)
# 종료: Ctrl+b d (detach)
SESSION_NAME="claude-agent"

if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "세션 '$SESSION_NAME'이 없습니다."
    exit 1
fi

exec tmux attach -t "$SESSION_NAME"
