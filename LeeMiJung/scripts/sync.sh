#!/bin/bash
# =============================================================
# 공용 저장소 동기화 (LMJAgent → memberSimsaClaudeProject/LeeMiJung/LMJAgent)
#
# 로컬 프로젝트의 "git 추적 파일"만 골라 공용 저장소의 개인 서브디렉터리로
# 복사한 뒤 커밋·푸시합니다. 두 저장소는 히스토리가 분리되어 있으므로
# merge/pull이 아닌 "파일 미러링" 방식으로 동기화합니다.
#
# 사용법:
#   scripts/sync.sh                          # 동기화 후 푸시
#   scripts/sync.sh -n                       # dry-run (변경 목록만 출력)
#   scripts/sync.sh -m "대시보드 차트 추가"    # 커밋 메시지 지정
#   scripts/sync.sh --no-push                # 커밋까지만, 푸시는 수동
#
# 환경변수로 경로 변경 가능:
#   MIRROR_DIR=~/다른경로 scripts/sync.sh
#
# 동작 흐름:
#   1. 미러 저장소 준비 (없으면 clone, 있으면 pull로 최신화)
#   2. git ls-files로 추적 파일만 추출 → 임시 스테이징에 복사
#      (.venv, logs, config/env.sh 등 .gitignore 대상은 자동 제외)
#   3. 시크릿 마스킹 (API 키를 플레이스홀더로 치환)
#   4. 시크릿 스캔 — 잔여 시크릿 발견 시 푸시하지 않고 중단
#   5. rsync --delete로 미러 서브디렉터리에 반영 (로컬에서 지운 파일도 삭제)
#   6. 변경분이 있으면 커밋 + 푸시
#
# 반환: 정상 0 / 변경 없음 0 / 시크릿 검출·오류 1
#
# 변경이력:
#   2026-09-07  신규 작성
# =============================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- 설정 (환경변수로 덮어쓰기 가능) --------------------------------
MIRROR_DIR="${MIRROR_DIR:-$HOME/Repositories/Claude/memberSimsa}"
MIRROR_URL="${MIRROR_URL:-https://github.com/audmslpl/memberSimsaClaudeProject}"
SUBDIR="${SUBDIR:-LeeMiJung/LMJAgent}"
BRANCH="${BRANCH:-main}"

# --- 옵션 파싱 ------------------------------------------------------
DRY_RUN=0
DO_PUSH=1
COMMIT_MSG=""

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--dry-run) DRY_RUN=1; shift ;;
        --no-push)    DO_PUSH=0; shift ;;
        -m)           COMMIT_MSG="${2:-}"; shift 2 ;;
        -h|--help)    sed -n '2,32p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *)            echo "알 수 없는 옵션: $1 (사용법은 -h)" >&2; exit 1 ;;
    esac
done

say()  { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# --- 1. 미러 저장소 준비 --------------------------------------------
say "미러 저장소 준비"
if [ ! -d "$MIRROR_DIR/.git" ]; then
    echo "  미러가 없어 새로 클론합니다: $MIRROR_DIR"
    git clone "$MIRROR_URL" "$MIRROR_DIR" || fail "클론 실패"
else
    git -C "$MIRROR_DIR" rev-parse --git-dir >/dev/null 2>&1 || fail "미러 경로가 git 저장소가 아닙니다: $MIRROR_DIR"
    # 미러에 손으로 만든 변경이 남아있으면 pull이 깨지므로 먼저 확인
    if [ -n "$(git -C "$MIRROR_DIR" status --porcelain)" ]; then
        fail "미러에 커밋되지 않은 변경이 있습니다. 정리 후 다시 실행하세요: $MIRROR_DIR"
    fi
    git -C "$MIRROR_DIR" checkout -q "$BRANCH" || fail "$BRANCH 브랜치 체크아웃 실패"
    git -C "$MIRROR_DIR" pull --ff-only origin "$BRANCH" || fail "pull 실패 (원격이 앞서 있거나 네트워크 오류)"
fi
echo "  미러 HEAD: $(git -C "$MIRROR_DIR" log --oneline -1)"

# --- 2. 추적 파일을 스테이징으로 복사 --------------------------------
say "추적 파일 수집"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

COUNT=0
while IFS= read -r -d '' f; do
    mkdir -p "$STAGE/$(dirname "$f")"
    cp -p "$SRC_DIR/$f" "$STAGE/$f"   # -p: mtime 보존 → 미변경 파일이 diff로 잡히지 않게
    COUNT=$((COUNT + 1))
done < <(git -C "$SRC_DIR" ls-files -z)
[ "$COUNT" -gt 0 ] || fail "추적 파일이 없습니다"
echo "  ${COUNT}개 파일 ($(du -sh "$STAGE" | cut -f1))"

# --- 3. 시크릿 마스킹 ------------------------------------------------
say "시크릿 마스킹"
SETTINGS="$STAGE/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    # settings.json의 env 블록에 들어있는 실제 키 값을 플레이스홀더로 치환
    for KEY in GEMINI_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY TG_BOT_TOKEN; do
        if grep -q "\"$KEY\"" "$SETTINGS"; then
            sed -i '' "s#\"$KEY\": \".*\"#\"$KEY\": \"REPLACE_WITH_YOUR_${KEY}\"#" "$SETTINGS"
            echo "  마스킹: .claude/settings.json → $KEY"
        fi
    done
fi

# --- 4. 시크릿 스캔 (발견 시 중단) -----------------------------------
say "시크릿 스캔"
PATTERN='AIzaSy[0-9A-Za-z_-]{30,}|bot[0-9]{8,}:[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY'
HITS="$(grep -rnIE "$PATTERN" "$STAGE" 2>/dev/null | sed "s#^$STAGE/##")"
if [ -n "$HITS" ]; then
    echo "$HITS" | sed 's/^/  /' >&2
    fail "시크릿으로 보이는 값이 남아있어 중단합니다. 위 파일을 정리한 뒤 다시 실행하세요."
fi
echo "  깨끗함"

# --- 5. 미러에 반영 (삭제분 포함) ------------------------------------
say "미러에 반영: $SUBDIR"
DEST="$MIRROR_DIR/$SUBDIR"
mkdir -p "$DEST"

# --checksum: 타임스탬프가 아닌 "내용"으로 비교.
#   git checkout/clone은 내용이 같아도 mtime을 바꾸므로 시각 기준이면 전부 변경으로 오탐됨.
#   소유자·그룹(-o/-g)도 제외 — 미러 환경 차이로 인한 오탐 방지.
RSYNC_OPTS=(-rlpt --checksum --delete --itemize-changes)
[ "$DRY_RUN" -eq 1 ] && RSYNC_OPTS+=(--dry-run)
# 실제 변경만 추출: 전송(>f) / 신규 생성(cf, cL) / 삭제(*deleting).
#   앞이 '.'인 줄은 내용 동일 + 속성만 갱신 → 무시. 'cd'(디렉터리 생성)도 제외.
CHANGES="$(rsync "${RSYNC_OPTS[@]}" "$STAGE/" "$DEST/" | grep -E '^(\*|[<>c][fL])' || true)"

if [ -z "$CHANGES" ]; then
    echo "  변경 없음 — 동기화할 내용이 없습니다."
    exit 0
fi
echo "$CHANGES" | sed 's/^/  /'

if [ "$DRY_RUN" -eq 1 ]; then
    say "dry-run 종료 (실제 변경 없음)"
    exit 0
fi

# --- 6. 커밋 + 푸시 --------------------------------------------------
say "커밋"
git -C "$MIRROR_DIR" add -A "$SUBDIR"
if git -C "$MIRROR_DIR" diff --cached --quiet; then
    echo "  스테이징된 변경이 없습니다 (.gitignore에 걸렸을 수 있음)."
    exit 0
fi
git -C "$MIRROR_DIR" diff --cached --stat | tail -1 | sed 's/^/  /'

[ -n "$COMMIT_MSG" ] || COMMIT_MSG="sync: LMJAgent $(date '+%Y-%m-%d %H:%M')"
git -C "$MIRROR_DIR" commit -q -m "$COMMIT_MSG" || fail "커밋 실패"
echo "  $(git -C "$MIRROR_DIR" log --oneline -1)"

if [ "$DO_PUSH" -eq 0 ]; then
    say "완료 (--no-push: 푸시는 수동으로)"
    echo "  git -C \"$MIRROR_DIR\" push origin $BRANCH"
    exit 0
fi

say "푸시"
if git -C "$MIRROR_DIR" push origin "$BRANCH"; then
    say "동기화 완료"
    echo "  https://github.com/audmslpl/memberSimsaClaudeProject/tree/$BRANCH/$SUBDIR"
else
    fail "푸시 실패 — 권한(collaborator) 또는 인증(classic PAT)을 확인하세요. 커밋은 로컬에 남아있습니다."
fi
