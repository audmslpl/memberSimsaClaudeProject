#!/usr/bin/env python3
# =============================================================
# Claude Agent 프로젝트 보고서(기술팀용) PPT 생성 스크립트
# 사용법: .venv/bin/python scripts/build-report-ppt.py
# 동작: python-pptx로 16:9 다크 테마 슬라이드를 구성해
#       logs/Claude-Agent-Report.pptx 로 저장한다.
# 변경이력:
#   2026-06-09  최초 작성 — 기술팀 보고용 14슬라이드 구성
#   2026-06-09  스크린샷(텔레그램/대시보드) 슬라이드 추가
#   2026-06-09  아키텍처 2슬라이드로 보강(계층 구조 + 실행 모델)
#   2026-06-09  주식 대시보드 관련 슬라이드·언급 전체 제거
# =============================================================
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = "/Users/ghyu/Repositories/Claude/LMJAgent"
OUT = os.path.join(ROOT, "logs", "Claude-Agent-Report.pptx")
ARCH = os.path.join(ROOT, "logs", "architecture.png")
TG_STOCK   = os.path.join(ROOT, "logs", "tg-stock-morning.png")
TG_WEATHER = os.path.join(ROOT, "logs", "tg-weather-morning.png")
TG_FLIGHT  = os.path.join(ROOT, "logs", "tg-flight.png")
TG_ANALYZE = os.path.join(ROOT, "logs", "tg-stock-analyze.png")

try:
    from PIL import Image as _PILImage
    def _imgsize(p):
        with _PILImage.open(p) as im:
            return im.size
except Exception:
    _imgsize = None

# ── 테마 색상 (architecture.png 팔레트와 통일) ──
BG      = RGBColor(0x1A, 0x1A, 0x2E)
CARD    = RGBColor(0x16, 0x21, 0x3E)
BORDER  = RGBColor(0x0F, 0x34, 0x60)
ACCENT  = RGBColor(0xE9, 0x45, 0x60)   # red
CYAN    = RGBColor(0x53, 0xD8, 0xFB)
GOLD    = RGBColor(0xF5, 0xC5, 0x18)
GREEN   = RGBColor(0x00, 0xD2, 0x6A)
WHITE   = RGBColor(0xE8, 0xE8, 0xE8)
DIM     = RGBColor(0x88, 0x99, 0xAA)

FONT = "맑은 고딕"   # 회사(Windows) 환경 기준. Mac에서는 자동 대체됨.

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg.fill.solid(); bg.fill.fore_color.rgb = BG
    bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def textbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    return tf


def setp(p, text, size, color, bold=False, align=PP_ALIGN.LEFT, space=6, bullet=False):
    p.text = text
    p.alignment = align
    p.space_after = Pt(space)
    for r in p.runs:
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
    return p


def title_bar(s, label, title, color=CYAN):
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(0.45), Inches(0.12), Inches(0.75))
    bar.fill.solid(); bar.fill.fore_color.rgb = color; bar.line.fill.background()
    bar.shadow.inherit = False
    tf = textbox(s, 0.78, 0.38, 11.8, 1.0)
    p = tf.paragraphs[0]; setp(p, label, 12, color, bold=True, space=2)
    p2 = tf.add_paragraph(); setp(p2, title, 28, WHITE, bold=True)


def card(s, x, y, w, h, color=BORDER):
    c = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    c.fill.solid(); c.fill.fore_color.rgb = CARD
    c.line.color.rgb = color; c.line.width = Pt(1.5)
    c.shadow.inherit = False
    try:
        c.adjustments[0] = 0.06
    except Exception:
        pass
    return c


def card_text(s, x, y, w, h, head, lines, color=CYAN):
    card(s, x, y, w, h, color)
    tf = textbox(s, x + 0.25, y + 0.18, w - 0.5, h - 0.36)
    p = tf.paragraphs[0]; setp(p, head, 15, color, bold=True, space=6)
    for ln in lines:
        para = tf.add_paragraph()
        setp(para, ln, 11.5, WHITE, space=4)


def img_fit(s, path, bx, by, bw, bh, border=BORDER):
    """이미지를 (bx,by,bw,bh) 박스 안에 비율 유지하며 중앙 배치 + 테두리."""
    if not os.path.exists(path) or _imgsize is None:
        return
    iw, ih = _imgsize(path)
    scale = min(bw / iw, bh / ih)
    w, h = iw * scale, ih * scale
    x = bx + (bw - w) / 2
    y = by + (bh - h) / 2
    pic = s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    pic.line.color.rgb = border
    pic.line.width = Pt(1.5)
    return pic


def caption(s, x, y, w, text, color=DIM, size=12, align=PP_ALIGN.CENTER):
    tf = textbox(s, x, y, w, 0.4)
    setp(tf.paragraphs[0], text, size, color, align=align)


def layer_band(s, x, y, w, h, cat, desc, color):
    """좌측 카테고리 칩 + 우측 설명으로 구성된 계층 밴드."""
    card(s, x, y, w, h, color)
    bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.12), Inches(y + 0.12),
                             Inches(1.95), Inches(h - 0.24))
    bar.fill.solid(); bar.fill.fore_color.rgb = color; bar.line.fill.background()
    bar.shadow.inherit = False
    cf = bar.text_frame; cf.word_wrap = True; cf.vertical_anchor = MSO_ANCHOR.MIDDLE
    setp(cf.paragraphs[0], cat, 13, BG, bold=True, align=PP_ALIGN.CENTER, space=0)
    tf = textbox(s, x + 2.25, y, w - 2.45, h, MSO_ANCHOR.MIDDLE)
    setp(tf.paragraphs[0], desc, 12, WHITE, space=0)


def flow_band(s, x, y, w, steps, color=CYAN):
    """가로 데이터 흐름 밴드: step1 → step2 → ..."""
    card(s, x, y, w, 0.7, color)
    tf = textbox(s, x + 0.2, y, w - 0.4, 0.7, MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    for i, st in enumerate(steps):
        r = p.add_run(); r.text = st
        r.font.name = FONT; r.font.size = Pt(12.5); r.font.bold = True; r.font.color.rgb = WHITE
        if i < len(steps) - 1:
            a = p.add_run(); a.text = "   →   "
            a.font.name = FONT; a.font.size = Pt(12.5); a.font.color.rgb = color


# ───────────────────────── 1. 표지 ─────────────────────────
s = slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(2.55), SW, Inches(0.06))
bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background(); bar.shadow.inherit = False
tf = textbox(s, 1.0, 2.7, 11.3, 2.2)
setp(tf.paragraphs[0], "Claude Agent", 54, WHITE, bold=True)
setp(tf.add_paragraph(), "Telegram 기반 상시 AI 비서 · 자동화 시스템", 24, CYAN, bold=True, space=4)
setp(tf.add_paragraph(), "개발 결과 보고 (기술팀)", 16, DIM)
tf2 = textbox(s, 1.0, 6.4, 11.3, 0.6)
setp(tf2.paragraphs[0], "2026-06-09  ·  macOS / Python / Claude Code", 13, DIM)

# ───────────────────────── 2. 배경 & 목적 ─────────────────────────
s = slide(); title_bar(s, "01  OVERVIEW", "추진 배경 및 목적")
card_text(s, 0.6, 1.7, 3.95, 4.9, "배경 (문제 정의)", [
    "• 시황·날씨·항공권 정보를 매번 직접 검색",
    "• 정해진 시간대 반복 작업의 수작업 부담",
    "• 모바일에서 즉시 받아볼 채널 부재",
    "• 24시간 상시 응답하는 비서가 필요"], ACCENT)
card_text(s, 4.7, 1.7, 3.95, 4.9, "목표", [
    "• Telegram으로 대화·지시 가능한 에이전트",
    "• 정기 브리핑 완전 자동화 (아침/점심/저녁)",
    "• 스킬 단위로 기능 확장 가능한 구조",
    "• 장애 시 자동 복구되는 상시 운영"], GOLD)
card_text(s, 8.8, 1.7, 3.95, 4.9, "핵심 성과", [
    "• 상시 백그라운드 에이전트 구축",
    "• 스킬 9종 운영 (주식·날씨·항공권)",
    "• 일 다회 정기 브리핑 자동 발송",
    "• 채널 기반 실시간 대화·요청 처리",
    "• 자동 재시작·헬스체크 운영체계"], GREEN)

# ───────────────────────── 3. 시스템 아키텍처 — 계층 구조 ─────────────────────────
s = slide(); title_bar(s, "02  ARCHITECTURE", "시스템 아키텍처 — 계층 구조")
LAYERS = [
    ("사용자 채널", "Telegram · Discord  —  MCP 플러그인 채널 (인바운드 메시지 / 아웃바운드 발송)", CYAN),
    ("에이전트 코어", "Claude Code (auto-mode)  ·  스킬 라우팅  ·  권한 allowlist  ·  파일/메모리 접근", GOLD),
    ("스킬 & 도구", "Skills 9종  ·  shared-scripts (market·ticker-fetcher)  ·  Playwright MCP  ·  Web", GREEN),
    ("데이터 · 출력", "시장 / 날씨 / 항공 소스  →  Telegram Bot API (실시간·정기 발송)", ACCENT),
    ("OS 기반", "launchd (상시 구동·헬스체크)  ·  tmux 세션  ·  cron (정시 트리거)", CYAN),
]
by = 1.65
for cat, desc, col in LAYERS:
    layer_band(s, 0.6, by, 6.45, 0.92, cat, desc, col)
    by += 1.04
if os.path.exists(ARCH):
    s.shapes.add_picture(ARCH, Inches(7.45), Inches(1.55), height=Inches(5.55))
caption(s, 7.45, 7.12, 4.2, "▲ 전체 아키텍처 다이어그램", DIM, 11)

# ───────────────────────── 3-2. 아키텍처 — 실행 모델 & 데이터 흐름 ─────────────────────────
s = slide(); title_bar(s, "02-1  ARCHITECTURE", "실행 모델 & 데이터 흐름")
card_text(s, 0.6, 1.6, 5.95, 3.55, "① 상시 대화형 에이전트", [
    "• launchd(com.claude.agent) · RunAtLoad + KeepAlive",
    "• → agent-launcher.sh → tmux 세션(claude-agent)",
    "• → claude --enable-auto-mode (Telegram 채널 연결)",
    "• Telegram/Discord 메시지에 실시간 응답",
    "• 종료·행(hang) 감지 시 자동 재시작 (heartbeat 5분)"], CYAN)
card_text(s, 6.8, 1.6, 5.95, 3.55, "② 헤드리스 스케줄 실행", [
    "• crontab → stock / weather-cron.sh (정시 트리거)",
    "• → check-login.sh 프리플라이트 (로그인 점검)",
    "• → claude -p [스킬] (1회성 헤드리스 실행)",
    "• → tg-send.sh → Telegram Bot API 발송",
    "• 인증 에러 감지 시 텔레그램 알림"], GOLD)
flow_band(s, 0.6, 5.45, 12.15,
          ["트리거", "스킬 실행", "데이터 수집", "LLM 가공", "tg-send.sh", "Bot API", "사용자"], GREEN)
tf = textbox(s, 0.6, 6.35, 12.15, 0.9)
setp(tf.paragraphs[0],
     "수집 경로: market-fetcher.py(시장) · Playwright MCP(항공권 렌더링) · WebFetch/Search(폴백·뉴스)", 12.5, WHITE, space=4)
setp(tf.add_paragraph(),
     "프로세스: launchd 2종(agent · heartbeat) + tmux   |   설정: env.sh · settings.json · .mcp.json · *.yaml", 12.5, DIM)

# ───────────────────────── 4. 기술 스택 ─────────────────────────
s = slide(); title_bar(s, "03  TECH STACK", "기술 스택")
stacks = [
    ("런타임 / 에이전트", ["Claude Code (auto-mode)", "Telegram·Discord MCP 채널", "Playwright MCP"], CYAN),
    ("언어 / 실행환경", ["Python 3.14 (venv)", "Bash 스크립트", "Node / npx (MCP)"], GOLD),
    ("프로세스 관리", ["macOS launchd (LaunchAgent)", "tmux 상시 세션", "heartbeat 헬스체크"], GREEN),
    ("데이터 수집", ["WebFetch / WebSearch", "Playwright (항공권 렌더링)", "yfinance·finviz 등 소스"], ACCENT),
]
xs = [0.6, 3.65, 6.7, 9.75]
for (head, lines, col), x in zip(stacks, xs):
    card_text(s, x, 1.8, 2.95, 4.4, head, ["• " + l for l in lines], col)

# ───────────────────────── 5. 에이전트 런타임 ─────────────────────────
s = slide(); title_bar(s, "04  RUNTIME", "에이전트 런타임 & 신뢰성")
card_text(s, 0.6, 1.7, 5.9, 4.9, "상시 실행 구조", [
    "• LaunchAgent → agent-launcher.sh 기동",
    "• tmux 세션(claude-agent) 안에서 Claude 실행",
    "• 세션/프로세스 종료 시 자동 재시작",
    "• STARTUP_GRACE로 인증·크리덴셜 로드 대기",
    "• 로그인 실패 시 5분 주기 재시도 + 알림"], CYAN)
card_text(s, 6.8, 1.7, 5.9, 4.9, "장애 대응 / 운영", [
    "• MAX_RESTARTS=10 / 600초 윈도우 폭주 방지",
    "• heartbeat.sh 5분 주기 중복 헬스체크",
    "• 로그 10MB 자동 로테이션 (agent.log)",
    "• 로그인 끊김 → Telegram 알림(쿨다운 30분)",
    "• start/stop/attach 운영 스크립트 제공"], GREEN)

# ───────────────────────── 6. 스킬 시스템 ─────────────────────────
s = slide(); title_bar(s, "05  SKILLS", "스킬 시스템 (9종)")
skills = [
    ("주식 (5)", ["stock-morning / lunch / evening", "→ 시황 정기 브리핑", "stock-analyze → 단타·스윙 진입분석", "공통 market-fetcher.py 사용"], GOLD),
    ("날씨 (3)", ["weather-morning / lunch / evening", "→ 시간대별 날씨 브리핑", "오늘·내일 날씨 포함"], CYAN),
    ("항공권 (2)", ["flight-check → 최저가 실시간 조회", "flight-watch → 매진편 좌석감시", "Playwright로 네이버항공 렌더링"], ACCENT),
]
xs = [0.6, 4.85, 9.1]
for (head, lines, col), x in zip(skills, xs):
    card_text(s, x, 1.8, 3.6, 4.5, head, ["• " + l for l in lines], col)
tf = textbox(s, 0.6, 6.45, 12.1, 0.8)
setp(tf.paragraphs[0], "공통 구조: SKILL.md(지침) + shared-scripts(수집 로직). 스킬 단위로 독립 추가/수정 가능 → 확장 용이.", 12.5, DIM)

# ───────────────────────── 7. 주식 브리핑 파이프라인 ─────────────────────────
s = slide(); title_bar(s, "06  PIPELINE", "주식 브리핑 파이프라인", GOLD)
tf = textbox(s, 0.6, 1.65, 12.2, 1.0)
setp(tf.paragraphs[0], "cron/launchd 트리거 → 스킬 실행 → 데이터 수집 → 메시지 작성 → Telegram 전송", 15, WHITE, bold=True)
steps = [
    ("1. 트리거", ["stock-cron.sh", "장 시간대별 호출", "(아침/점심/저녁)"], CYAN),
    ("2. 수집", ["market-fetcher.py", "지수·선물·환율·섹터", "실패 시 Web 폴백"], GOLD),
    ("3. 가공", ["주도테마 TOP3", "매수/매도 종목 선정", "실명+종목코드"], ACCENT),
    ("4. 전송", ["모바일 가독성 포맷", "표 대신 인라인", "Telegram 발송"], GREEN),
]
xs = [0.6, 3.65, 6.7, 9.75]
for (head, lines, col), x in zip(steps, xs):
    card_text(s, x, 2.9, 2.95, 3.3, head, ["• " + l for l in lines], col)

# ───────────────────────── 7-1. Telegram 브리핑 예시 (스크린샷) ─────────────────────────
s = slide(); title_bar(s, "06-1  SCREENSHOT", "Telegram 브리핑 예시", GOLD)
img_fit(s, TG_STOCK,   1.3, 1.55, 4.6, 5.2)
img_fit(s, TG_WEATHER, 7.4, 1.55, 4.6, 5.2)
caption(s, 1.3, 6.75, 4.6, "▲ 주식 모닝 브리핑 (장 시작 전)")
caption(s, 7.4, 6.75, 4.6, "▲ 날씨 모닝 브리핑")
caption(s, 0.6, 7.05, 12.1, "* 실제 발송 데이터 기반 재구성 화면", DIM, 10)

# ───────────────────────── 7-2. 항공권 · 종목분석 예시 (스크린샷) ─────────────────────────
s = slide(); title_bar(s, "06-2  SCREENSHOT", "Telegram — 항공권 · 종목분석", ACCENT)
img_fit(s, TG_FLIGHT,  1.3, 1.55, 4.6, 5.2)
img_fit(s, TG_ANALYZE, 7.4, 1.55, 4.6, 5.2)
caption(s, 1.3, 6.75, 4.6, "▲ 항공권 최저가 조회 (flight-check)")
caption(s, 7.4, 6.75, 4.6, "▲ 종목 진입 분석 (stock-analyze)")
caption(s, 0.6, 7.05, 12.1, "* 실제 발송 포맷 기반 재구성 화면", DIM, 10)

# ───────────────────────── 9. 자동화 & 스케줄 ─────────────────────────
s = slide(); title_bar(s, "08  AUTOMATION", "자동화 & 스케줄링")
card_text(s, 0.6, 1.7, 3.95, 4.9, "스케줄 작업", [
    "• 주식 브리핑 (아침/점심/저녁)",
    "• 날씨 브리핑 (아침/점심/저녁)",
    "• heartbeat 헬스체크 (5분)",
    "• 에이전트 상시 구동·자동복구"], GOLD)
card_text(s, 4.7, 1.7, 3.95, 4.9, "실행 메커니즘", [
    "• launchd: 부팅 시 상시 데몬",
    "• cron: 시간대별 브리핑 트리거",
    "• tg-send.sh: 공통 전송 유틸",
    "• /loop: 모니터링 반복 실행"], CYAN)
card_text(s, 8.8, 1.7, 3.95, 4.9, "구성 관리", [
    "• .claude/settings.json 권한",
    "• config/env.sh 환경변수",
    "• .mcp.json (Playwright MCP)",
    "• 스킬별 SKILL.md 지침"], GREEN)

# ───────────────────────── 10. 보안 고려사항 ─────────────────────────
s = slide(); title_bar(s, "09  SECURITY", "보안 · 운영 고려사항", ACCENT)
card_text(s, 0.6, 1.7, 5.9, 4.9, "현재 적용", [
    "• 채널 접근제어(access 스킬, 페어링 승인)",
    "• 도구 권한 allowlist (settings.json)",
    "• 파일 접근 범위 제한 (프로젝트 디렉토리)",
    "• 파괴적 작업 전 확인 정책"], CYAN)
card_text(s, 6.8, 1.7, 5.9, 4.9, "개선 과제", [
    "• API 키 평문 저장 → 환경변수/시크릿 분리",
    "• auto-mode/skip-permissions 범위 재점검",
    "• 로그 내 민감정보 마스킹",
    "• 외부 전송 데이터 검토 프로세스"], ACCENT)

# ───────────────────────── 11. 성과 / 한계 / 향후 ─────────────────────────
s = slide(); title_bar(s, "10  RESULT", "성과 · 한계 · 향후 계획", GREEN)
card_text(s, 0.6, 1.7, 3.95, 4.9, "성과", [
    "• 정기 브리핑 수작업 → 완전 자동화",
    "• 모바일에서 즉시 정보 수신",
    "• 9개 스킬로 기능 모듈화",
    "• 자동복구 상시 운영 달성"], GREEN)
card_text(s, 4.7, 1.7, 3.95, 4.9, "한계", [
    "• 단일 머신(macOS) 의존",
    "• 외부 사이트 구조 변경에 취약",
    "• 보안 강화 필요 (좌측 9장)",
    "• 테스트/모니터링 자동화 부족"], GOLD)
card_text(s, 8.8, 1.7, 3.95, 4.9, "향후 계획", [
    "• 시크릿 관리 체계화",
    "• 스킬 추가 (캘린더·메일 등)",
    "• 장애 알림·운영 지표 모니터링",
    "• 배포/이중화 검토"], CYAN)

# ───────────────────────── 12. 마무리 ─────────────────────────
s = slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(3.0), SW, Inches(0.06))
bar.fill.solid(); bar.fill.fore_color.rgb = CYAN; bar.line.fill.background(); bar.shadow.inherit = False
tf = textbox(s, 1.0, 3.2, 11.3, 1.6)
setp(tf.paragraphs[0], "감사합니다", 40, WHITE, bold=True)
setp(tf.add_paragraph(), "Q & A  ·  데모 시연 가능", 18, CYAN)

prs.save(OUT)
print("saved:", OUT, "slides:", len(prs.slides._sldIdLst))
