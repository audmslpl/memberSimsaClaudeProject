#!/bin/bash
# Claude Agent 시작 (LaunchAgent + Heartbeat)

echo "=== plist 문법 검증 ==="
plutil -lint ~/Library/LaunchAgents/com.claude.agent.plist
plutil -lint ~/Library/LaunchAgents/com.claude.agent.heartbeat.plist

echo ""
echo "=== LaunchAgent 로드 ==="
launchctl load ~/Library/LaunchAgents/com.claude.agent.plist 2>&1
launchctl load ~/Library/LaunchAgents/com.claude.agent.heartbeat.plist 2>&1

echo ""
echo "=== 상태 확인 ==="
launchctl list | grep claude
