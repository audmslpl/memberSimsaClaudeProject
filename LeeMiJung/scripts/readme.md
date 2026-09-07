# plist 문법 검증
plutil -lint ~/Library/LaunchAgents/com.claude.agent.plist

# LaunchAgent 로드 (즉시 실행됨)
launchctl load ~/Library/LaunchAgents/com.claude.agent.plist

# 상태 확인
launchctl list | grep claude

launchctl start com.claude.agent

---

# 세션 목록
tmux ls

# 세션에 접속 (Claude Code 인터랙티브 화면 확인)
tmux attach -t claude-agent

# 세션에서 나가기 (Claude는 계속 실행됨)
# Ctrl+B 누른 후 D

# 로그 확인
tail -f ~/Repositories/Claude/LMJAgent/logs/agent.log

---

# --- 에이전트 중지 ---
launchctl unload ~/Library/LaunchAgents/com.claude.agent.plist
tmux kill-session -t claude-agent


launchctl stop com.claude.agent