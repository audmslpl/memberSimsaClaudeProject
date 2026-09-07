#!/bin/bash
# Claude Agent 중지 (LaunchAgent + Heartbeat + tmux)

echo "=== LaunchAgent 언로드 ==="
launchctl unload ~/Library/LaunchAgents/com.claude.agent.heartbeat.plist 2>&1
launchctl unload ~/Library/LaunchAgents/com.claude.agent.plist 2>&1

echo ""
echo "=== tmux 세션 종료 ==="
tmux kill-session -t claude-agent 2>&1 || echo "(세션 없음)"

echo ""
echo "=== 상태 확인 ==="
launchctl list | grep claude || echo "(등록된 에이전트 없음)"
