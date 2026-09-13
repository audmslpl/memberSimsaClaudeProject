#!/usr/bin/env python3
# =============================================================
# LMJ Agent 프로젝트 보고서(기술팀용) PPT 생성 스크립트 — v2 (모던 리디자인)
#
# 사용법:
#   node scripts/gen-report-icons.js          # 아이콘 PNG 선행 생성
#   .venv/bin/python scripts/build-report-ppt-v2.py
#
# 동작:
#   python-pptx로 16:9 다크 슬라이드 16장을 구성해
#   logs/LMJ-Agent-Report-v2.pptx 로 저장한다.
#   (검토용 PDF: PowerPoint에서 "다른 이름으로 저장 → PDF" 로 내보낸
#    logs/LMJ-Agent-Report-v2.pdf 를 함께 둔다.)
#
# v1(build-report-ppt.py) 대비 변경점:
#   - 스케줄러를 launchd 기준으로 기술 (전용 슬라이드 추가, cron 관련 서술 전부 제거)
#   - Lucide 아이콘(PNG) 도입, 다크 + 앰버 단일 강조 팔레트로 재디자인
#   - 폰트: 한글 맑은 고딕 / 영문 Segoe UI / 코드 Consolas (Windows 기본 탑재)
#   - 스킬 개수 표기 정정: 주식 5 → 4 (실제 .claude/skills 기준 총 9종)
#
# 변경이력:
#   2026-08-20  최초 작성. v1을 기반으로 launchd 기준 재작성 + 모던 리디자인.
#   2026-08-20  cron → launchd 이전(migration) 서사 슬라이드 제거.
#               최신 구성만 기술하도록 요약/이력 슬라이드 문구 정리. 17 → 16장.
#   2026-08-21  제품 표기명을 "Claude Agent" → "LMJ Agent"로 변경(표지·헤더·푸터,
#               출력 파일명 LMJ-Agent-Report-v2.pptx). 런타임 식별자
#               (launchd 라벨 com.claude.agent, tmux 세션명, 경로)와
#               외부 제품명 "Claude Code"는 실제 값이므로 그대로 둔다.
# =============================================================
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = "/Users/ghyu/Repositories/Claude/LMJAgent"
OUT = os.path.join(ROOT, "logs", "LMJ-Agent-Report-v2.pptx")
ICONS = os.path.join(ROOT, "logs", "report-icons")
TG_STOCK = os.path.join(ROOT, "logs", "tg-stock-morning.png")
TG_WEATHER = os.path.join(ROOT, "logs", "tg-weather-morning.png")
TG_FLIGHT = os.path.join(ROOT, "logs", "tg-flight.png")
TG_ANALYZE = os.path.join(ROOT, "logs", "tg-stock-analyze.png")

from PIL import Image as _PILImage


def _imgsize(p):
    with _PILImage.open(p) as im:
        return im.size


# ── 팔레트 (gen-report-icons.js 의 COLORS 와 1:1 대응) ──────────
HEX = {
    "ink": "0A0E1A",     # 배경 (지배색)
    "card": "141A2B",    # 카드 표면
    "line": "232B42",    # 헤어라인
    "amber": "FFB020",   # 주 강조
    "teal": "4ECDC4",
    "rose": "FF6B6B",
    "green": "3DDC84",
    "violet": "9B8CFF",
    "white": "F2F4F8",
    "muted": "8B93A8",
    "faint": "5A6377",
}


def C(key):
    return RGBColor.from_string(HEX[key])


def blend(fg_key, bg_key, alpha):
    """fg를 bg 위에 alpha 비율로 올린 불투명 색 (PPT는 도형 알파를 쓰지 않기 위함)."""
    f = HEX[fg_key]
    b = HEX[bg_key]
    out = []
    for i in (0, 2, 4):
        fv = int(f[i:i + 2], 16)
        bv = int(b[i:i + 2], 16)
        out.append(int(round(fv * alpha + bv * (1 - alpha))))
    return RGBColor(*out)


FONT_KR = "맑은 고딕"     # 한글 (Windows 기본)
FONT_EN = "Segoe UI"      # 영문/숫자 디스플레이 (Windows 기본)
FONT_MONO = "Consolas"    # 코드/식별자 (Windows 기본)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]

M = 0.7                 # 좌우 여백
CW = 13.333 - M * 2     # 콘텐츠 폭 = 11.933


# ───────────────────────── 저수준 헬퍼 ─────────────────────────
def set_font(run, size, color, bold=False, latin=FONT_KR, ea=FONT_KR, spacing=None):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = latin
    rPr = f._rPr
    for tag, face in (("a:ea", ea), ("a:cs", latin)):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", face)
    if spacing is not None:
        rPr.set("spc", str(int(spacing * 100)))


def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C("ink")
    bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def tbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def put(tf, text, size, color, bold=False, latin=FONT_KR, ea=FONT_KR,
        align=PP_ALIGN.LEFT, space=6, spacing=None, line=1.2, first=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space)
    p.line_spacing = line
    r = p.add_run()
    r.text = text
    set_font(r, size, color, bold, latin, ea, spacing)
    return p


def rrect(s, x, y, w, h, fill, line_color=None, radius=0.055, line_w=1.0):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line_color is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line_color
        sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    try:
        sh.adjustments[0] = radius
    except Exception:
        pass
    sh.text_frame.word_wrap = True
    return sh


def icon(s, name, color_key, x, y, size):
    path = os.path.join(ICONS, f"{name}-{color_key}.png")
    if not os.path.exists(path):
        return None
    return s.shapes.add_picture(path, Inches(x), Inches(y), Inches(size), Inches(size))


def icon_tile(s, name, color_key, x, y, tile=0.64):
    """강조색으로 옅게 채운 라운드 타일 + 그 위 아이콘 — 전 슬라이드 공통 모티프."""
    rrect(s, x, y, tile, tile, blend(color_key, "ink", 0.15), blend(color_key, "ink", 0.34),
          radius=0.28, line_w=1.0)
    pad = tile * 0.24
    icon(s, name, color_key, x + pad, y + pad, tile - pad * 2)


def header(s, kicker, title, icon_name, color_key="amber"):
    icon_tile(s, icon_name, color_key, M, 0.52, 0.66)
    tf = tbox(s, M + 0.9, 0.46, CW - 0.9, 0.85)
    put(tf, kicker, 10.5, C(color_key), bold=True, latin=FONT_EN, ea=FONT_KR,
        space=3, spacing=1.4, line=1.0, first=True)
    put(tf, title, 27, C("white"), bold=True, latin=FONT_EN, space=0, line=1.0)


def footer(s, page):
    tf = tbox(s, M, 7.02, 6.0, 0.3)
    put(tf, "LMJ Agent  ·  개발 결과 보고 (기술팀)", 9, C("faint"),
        latin=FONT_EN, space=0, first=True)
    tf2 = tbox(s, 13.333 - M - 1.2, 7.02, 1.2, 0.3)
    put(tf2, f"{page:02d}", 9, C("faint"), bold=True, latin=FONT_EN,
        align=PP_ALIGN.RIGHT, space=0, first=True)


def card(s, x, y, w, h, accent="amber"):
    return rrect(s, x, y, w, h, C("card"), C("line"), radius=0.05, line_w=1.0)


def list_card(s, x, y, w, h, icon_name, head, lines, accent="amber",
              head_size=14.5, body=11.5, sub=None):
    """아이콘 타일 + 제목 + 대시 리스트로 구성된 표준 카드."""
    card(s, x, y, w, h, accent)
    icon_tile(s, icon_name, accent, x + 0.26, y + 0.26, 0.56)
    tf = tbox(s, x + 0.26, y + 0.98, w - 0.52, 0.4)
    put(tf, head, head_size, C("white"), bold=True, space=2, first=True)
    top = y + 1.42
    if sub:
        tf2 = tbox(s, x + 0.26, y + 1.4, w - 0.52, 0.3)
        put(tf2, sub, 10, C(accent), bold=True, latin=FONT_EN, space=0, first=True)
        top = y + 1.78
    body_tf = tbox(s, x + 0.26, top, w - 0.52, h - (top - y) - 0.26)
    for i, ln in enumerate(lines):
        p = body_tf.paragraphs[0] if i == 0 else body_tf.add_paragraph()
        p.space_after = Pt(7)
        p.line_spacing = 1.25
        r1 = p.add_run()
        r1.text = "–  "
        set_font(r1, body, C(accent), True, FONT_EN, FONT_KR)
        r2 = p.add_run()
        r2.text = ln
        set_font(r2, body, C("white"), False, FONT_KR, FONT_KR)
    return body_tf


def img_fit(s, path, bx, by, bw, bh):
    """비율 유지 + 가로 중앙 / 세로 상단 정렬 + 카드형 프레임 (좌우 상단선을 맞추기 위함)."""
    if not os.path.exists(path):
        return
    iw, ih = _imgsize(path)
    scale = min(bw / iw, bh / ih)
    w, h = iw * scale, ih * scale
    x = bx + (bw - w) / 2
    y = by
    rrect(s, x - 0.13, y - 0.13, w + 0.26, h + 0.26, C("card"), C("line"), radius=0.03)
    s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))


def note_band(s, y, icon_name, title, text, accent="amber", h=1.12):
    """콘텐츠 카드 아래에 붙는 전폭 요약 밴드 — 슬라이드 하단 여백을 정리하는 공통 요소."""
    card(s, M, y, CW, h, accent)
    icon_tile(s, icon_name, accent, M + 0.28, y + 0.27, 0.56)
    tf = tbox(s, M + 1.0, y + 0.24, CW - 1.3, 0.34)
    put(tf, title, 12.5, C(accent), bold=True, space=0, first=True)
    tf = tbox(s, M + 1.0, y + 0.63, CW - 1.3, 0.34)
    put(tf, text, 11.5, C("white"), space=0, line=1.2, first=True)


def caption(s, x, y, w, text, color="muted", size=11, align=PP_ALIGN.CENTER):
    tf = tbox(s, x, y, w, 0.32)
    put(tf, text, size, C(color), align=align, space=0, first=True)


# ═══════════════════════ 01. 표지 ═══════════════════════
s = slide()
rrect(s, 9.55, 2.05, 2.9, 2.9, blend("amber", "ink", 0.13), blend("amber", "ink", 0.3),
      radius=0.16, line_w=1.25)
icon(s, "LuBot", "amber", 10.33, 2.83, 1.34)

tf = tbox(s, 0.95, 1.62, 8.3, 0.4)
put(tf, "LMJ AGENT  ·  TECHNICAL REPORT", 12, C("amber"), bold=True,
    latin=FONT_EN, space=0, spacing=2.2, first=True)

tf = tbox(s, 0.95, 2.12, 8.4, 2.4)
put(tf, "LMJ Agent", 58, C("white"), bold=True, latin=FONT_EN, space=6,
    line=1.0, first=True)
put(tf, "Telegram 기반 상시 AI 비서 · 자동화 시스템", 21, C("teal"), bold=True,
    space=10, line=1.1)
put(tf, "개발 결과 보고 (기술팀)  —  구성 · 운영 · 신뢰성",
    13.5, C("muted"), space=0, line=1.2)

chips = [("상시 가동 24/7", "amber"), ("운영 스킬 9종", "teal"),
         ("일 6회 자동 브리핑", "violet"), ("launchd 잡 8종", "green")]
cx = 0.95
for label, col in chips:
    w = 0.30 + len(label) * 0.115
    rrect(s, cx, 4.72, w, 0.44, blend(col, "ink", 0.13), blend(col, "ink", 0.32),
          radius=0.4, line_w=1.0)
    ctf = tbox(s, cx, 4.72, w, 0.44, MSO_ANCHOR.MIDDLE)
    put(ctf, label, 11, C(col), bold=True, align=PP_ALIGN.CENTER, space=0, first=True)
    cx += w + 0.2

tf = tbox(s, 0.95, 6.42, 11.4, 0.5)
put(tf, "2026-08-20   ·   macOS · Python · Bash · Claude Code",
    12.5, C("faint"), latin=FONT_EN, space=0, first=True)

# ═══════════════════════ 02. 요약 ═══════════════════════
s = slide()
header(s, "SUMMARY", "한눈에 보기", "LuGauge", "amber")

stats = [
    ("24/7", "상시 가동 에이전트", "KeepAlive + 5분 헬스체크", "LuActivity", "teal"),
    ("9", "운영 스킬", "주식 4 · 날씨 3 · 항공 2", "LuPuzzle", "amber"),
    ("6", "일일 자동 브리핑", "주식 3회(평일) · 날씨 3회", "LuCalendarClock", "violet"),
    ("8", "launchd 잡", "상시 2 + 정시 6", "LuServer", "green"),
]
xs = [M, M + 3.02, M + 6.04, M + 9.06]
for (big, label, sub, ic, col), x in zip(stats, xs):
    card(s, x, 1.72, 2.87, 2.05, col)
    icon_tile(s, ic, col, x + 0.26, 1.96, 0.54)
    tf = tbox(s, x + 1.0, 1.9, 1.7, 0.7, MSO_ANCHOR.MIDDLE)
    put(tf, big, 34, C(col), bold=True, latin=FONT_EN, space=0, line=1.0, first=True)
    tf = tbox(s, x + 0.26, 2.78, 2.35, 0.8)
    put(tf, label, 13.5, C("white"), bold=True, space=4, first=True)
    put(tf, sub, 10.5, C("muted"), space=0, line=1.2)

card(s, M, 4.02, 7.6, 2.6, "amber")
icon_tile(s, "LuBot", "amber", M + 0.3, 4.3, 0.58)
tf = tbox(s, M + 1.02, 4.36, 6.3, 0.45)
put(tf, "시스템 요약", 15, C("white"), bold=True, space=0, first=True)
tf = tbox(s, M + 0.3, 5.08, 7.0, 1.35)
for i, txt in enumerate([
    "Telegram 채널로 24시간 대화·지시를 받는 상시 백그라운드 에이전트",
    "주식·날씨 브리핑은 macOS launchd LaunchAgent가 정시에 헤드리스로 실행",
    "기능은 스킬 9종으로 모듈화되어 단위별 추가·수정이 가능",
    "launchd · 런처 · heartbeat 3중 감시로 종료·행(hang) 시 자동 복구",
]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(5)
    p.line_spacing = 1.25
    r1 = p.add_run()
    r1.text = "–  "
    set_font(r1, 11.5, C("amber"), True, FONT_EN, FONT_KR)
    r2 = p.add_run()
    r2.text = txt
    set_font(r2, 11.5, C("white"))

card(s, M + 7.93, 4.02, 4.0, 2.6, "teal")
icon_tile(s, "LuServer", "teal", M + 8.23, 4.3, 0.58)
tf = tbox(s, M + 8.95, 4.36, 2.8, 0.45)
put(tf, "운영 환경", 15, C("white"), bold=True, space=0, first=True)
tf = tbox(s, M + 8.23, 5.08, 3.4, 1.35)
put(tf, "실행 기반", 11, C("muted"), bold=True, latin=FONT_EN, space=3, first=True)
put(tf, "macOS launchd + tmux 세션", 11, C("white"), space=10)
put(tf, "채널", 11, C("muted"), bold=True, latin=FONT_EN, space=3)
put(tf, "Telegram (MCP 플러그인)", 11, C("white"), space=0)
footer(s, 2)

# ═══════════════════════ 03. 배경 & 목적 ═══════════════════════
s = slide()
header(s, "01  OVERVIEW", "추진 배경 및 목적", "LuFlag", "amber")
list_card(s, M, 1.72, 3.87, 3.62, "LuTriangleAlert", "배경 (문제 정의)", [
    "시황·날씨·항공권 정보를 매번 직접 검색",
    "정해진 시간대 반복 작업의 수작업 부담",
    "모바일에서 즉시 받아볼 채널 부재",
    "24시간 상시 응답하는 비서가 필요",
], "rose")
list_card(s, M + 4.02, 1.72, 3.87, 3.62, "LuTarget", "목표", [
    "Telegram으로 대화·지시 가능한 에이전트",
    "정기 브리핑 완전 자동화 (아침/점심/저녁)",
    "스킬 단위로 기능 확장 가능한 구조",
    "장애 시 자동 복구되는 상시 운영",
], "amber")
list_card(s, M + 8.04, 1.72, 3.87, 3.62, "LuCircleCheck", "핵심 성과", [
    "상시 백그라운드 에이전트 구축",
    "스킬 9종 운영 (주식·날씨·항공권)",
    "일 6회 정기 브리핑 자동 발송",
    "채널 기반 실시간 대화·요청 처리",
    "자동 재시작·헬스체크 운영체계 확립",
], "green")
note_band(s, 5.58, "LuGitBranch", "적용 현황",
          "2026-06 구축 이후 단일 macOS 워크스테이션에서 상시 운영 중  ·  정기 브리핑은 launchd LaunchAgent가 평일/매일 스케줄로 자동 발송",
          "teal")
footer(s, 3)

# ═══════════════════════ 04. 아키텍처 — 계층 ═══════════════════════
s = slide()
header(s, "02  ARCHITECTURE", "시스템 아키텍처 — 계층 구조", "LuLayers", "teal")
LAYERS = [
    ("LuMonitorSmartphone", "teal", "사용자 채널",
     "Telegram · Discord — MCP 플러그인 채널 (인바운드 메시지 / 아웃바운드 발송)"),
    ("LuBot", "amber", "에이전트 코어",
     "Claude Code (auto-mode) · 스킬 라우팅 · 권한 allowlist · 메모리/파일 접근"),
    ("LuPuzzle", "violet", "스킬 & 도구",
     "Skills 9종 · shared-scripts (market-fetcher · ticker-fetcher) · Playwright MCP · Web"),
    ("LuDatabase", "rose", "데이터 · 출력",
     "시장 / 날씨 / 항공 소스  →  Telegram Bot API (실시간 · 정기 발송)"),
    ("LuServer", "green", "OS 기반",
     "macOS launchd LaunchAgent 8종 (상시 2 + 정시 6) · tmux 상시 세션"),
]
by = 1.72
for ic, col, cat, desc in LAYERS:
    card(s, M, by, CW, 0.86, col)
    icon_tile(s, ic, col, M + 0.22, by + 0.15, 0.56)
    tf = tbox(s, M + 0.96, by, 2.35, 0.86, MSO_ANCHOR.MIDDLE)
    put(tf, cat, 14, C(col), bold=True, space=0, first=True)
    tf = tbox(s, M + 3.36, by, CW - 3.6, 0.86, MSO_ANCHOR.MIDDLE)
    put(tf, desc, 11.5, C("white"), space=0, line=1.2, first=True)
    by += 0.98
caption(s, M, 6.6, CW,
        "계층 간 호출은 단방향(위 → 아래)이며, 결과 발송만 채널 계층으로 되돌아온다.",
        "muted", 10.5, PP_ALIGN.LEFT)
footer(s, 4)

# ═══════════════════════ 05. 실행 모델 & 데이터 흐름 ═══════════════════════
s = slide()
header(s, "02-1  EXECUTION MODEL", "실행 모델 & 데이터 흐름", "LuWorkflow", "teal")
list_card(s, M, 1.72, 5.8, 3.55, "LuMessageCircle", "① 상시 대화형 에이전트", [
    "launchd com.claude.agent — RunAtLoad + KeepAlive",
    "→ agent-launcher.sh → tmux 세션(claude-agent)",
    "→ claude --enable-auto-mode (Telegram 채널 연결)",
    "Telegram / Discord 메시지에 실시간 응답",
    "종료·행(hang) 감지 시 자동 재시작",
], "teal")
list_card(s, M + 6.13, 1.72, 5.8, 3.55, "LuCalendarClock", "② 헤드리스 스케줄 실행", [
    "launchd LaunchAgent 6종 — StartCalendarInterval",
    "→ check-login.sh 프리플라이트 (로그인 점검)",
    "→ claude -p [스킬] (1회성 헤드리스 실행)",
    "→ tg-send.sh → Telegram Bot API 발송",
    "인증 에러 감지 시 텔레그램 알림",
], "amber")

steps = ["트리거", "스킬 실행", "데이터 수집", "LLM 가공", "tg-send.sh", "Bot API", "사용자"]
fy = 5.42
card(s, M, fy, CW, 0.78, "violet")
sw = (CW - 0.44) / len(steps)
for i, st in enumerate(steps):
    stf = tbox(s, M + 0.22 + sw * i, fy, sw, 0.78, MSO_ANCHOR.MIDDLE)
    put(stf, st, 12, C("white"), bold=True, align=PP_ALIGN.CENTER, space=0, first=True)
    if i < len(steps) - 1:
        atf = tbox(s, M + 0.22 + sw * (i + 0.5), fy, sw, 0.78, MSO_ANCHOR.MIDDLE)
        put(atf, "→", 13, C("violet"), bold=True, align=PP_ALIGN.CENTER, space=0,
            latin=FONT_EN, first=True)

tf = tbox(s, M, 6.36, CW, 0.55)
put(tf, "수집 경로: market-fetcher.py(시장) · Playwright MCP(항공권 렌더링) · WebFetch/Search(폴백·뉴스)",
    11, C("white"), space=4, first=True)
put(tf, "프로세스: launchd 8종 + tmux   |   설정: env.sh · settings.json · .mcp.json · *.yaml",
    11, C("muted"), space=0)
footer(s, 5)

# ═══════════════════════ 06. launchd 잡 구성 ═══════════════════════
s = slide()
header(s, "03  SCHEDULER", "launchd 잡 구성 (8종)", "LuTimer", "green")

ROWS = [
    ("com.claude.agent", "RunAtLoad + KeepAlive", "상시", "agent-launcher.sh → tmux → claude", "teal"),
    ("com.claude.agent.heartbeat", "StartInterval 300", "5분", "heartbeat.sh (hang 감지·복구)", "teal"),
    ("com.ghyu.claude.stock.morning", "StartCalendarInterval", "평일 07:30", "stock-cron.sh morning", "amber"),
    ("com.ghyu.claude.stock.lunch", "StartCalendarInterval", "평일 12:30", "stock-cron.sh lunch", "amber"),
    ("com.ghyu.claude.stock.evening", "StartCalendarInterval", "평일 17:30", "stock-cron.sh evening", "amber"),
    ("com.ghyu.claude.weather.morning", "StartCalendarInterval", "매일 08:00", "weather-cron.sh morning", "violet"),
    ("com.ghyu.claude.weather.lunch", "StartCalendarInterval", "매일 12:00", "weather-cron.sh lunch", "violet"),
    ("com.ghyu.claude.weather.evening", "StartCalendarInterval", "매일 18:00", "weather-cron.sh evening", "violet"),
]
COLW = [4.05, 2.75, 1.55, 3.58]
ty, rh, hh = 1.72, 0.50, 0.46

hx = M
for j, (w, label) in enumerate(zip(COLW, ["LABEL", "트리거 키", "주기", "실행 대상"])):
    htf = tbox(s, hx + (0.34 if j == 0 else 0.16), ty, w - 0.2, hh, MSO_ANCHOR.MIDDLE)
    put(htf, label, 10, C("muted"), bold=True, latin=FONT_EN, space=0, spacing=1.2, first=True)
    hx += w

ry = ty + hh
for i, (label, trig, cycle, target, col) in enumerate(ROWS):
    if i % 2 == 0:
        rrect(s, M, ry, CW, rh - 0.06, C("card"), None, radius=0.06)
    rrect(s, M + 0.04, ry + (rh - 0.06) / 2 - 0.055, 0.11, 0.11, C(col), None, radius=0.5)
    cx = M
    vals = [(label, FONT_MONO, "white", 10.5, True),
            (trig, FONT_MONO, "muted", 10, False),
            (cycle, FONT_EN, col, 10.5, True),
            (target, FONT_MONO, "white", 10, False)]
    for j, (w, (txt, fnt, colr, sz, bd)) in enumerate(zip(COLW, vals)):
        pad = 0.34 if j == 0 else 0.16          # 첫 칸은 상태 점(dot)만큼 더 들여쓴다
        ctf = tbox(s, cx + pad, ry, w - pad - 0.04, rh - 0.06, MSO_ANCHOR.MIDDLE)
        put(ctf, txt, sz, C(colr), bold=bd, latin=fnt, ea=FONT_KR, space=0, first=True)
        cx += w
    ry += rh

tf = tbox(s, M, 6.34, CW, 0.62)
put(tf, "수동 즉시 실행:   launchctl kickstart -k gui/$(id -u)/com.ghyu.claude.stock.lunch",
    10.5, C("teal"), latin=FONT_MONO, space=5, first=True)
put(tf, "* 브리핑 스크립트 파일명은 *-cron.sh 이지만, 실행을 트리거하는 주체는 모두 launchd이다.",
    10, C("faint"), space=0)
footer(s, 6)

# ═══════════════════════ 08. 기술 스택 ═══════════════════════
s = slide()
header(s, "04  TECH STACK", "기술 스택", "LuBoxes", "violet")
stacks = [
    ("LuBot", "amber", "런타임 / 에이전트",
     ["Claude Code (auto-mode)", "Telegram · Discord MCP 채널", "Playwright MCP"]),
    ("LuFileCode", "teal", "언어 / 실행환경",
     ["Python 3.14 (venv)", "Bash 스크립트", "Node / npx (MCP)"]),
    ("LuServer", "green", "프로세스 관리",
     ["launchd LaunchAgent 8종", "tmux 상시 세션", "heartbeat 헬스체크 (5분)"]),
    ("LuNetwork", "violet", "데이터 수집",
     ["WebFetch / WebSearch", "Playwright (항공권)", "Yahoo Finance · Finviz"]),
]
xs = [M, M + 3.02, M + 6.04, M + 9.06]
for (ic, col, head, lines), x in zip(stacks, xs):
    list_card(s, x, 1.72, 2.87, 2.95, ic, head, lines, col, head_size=13.5, body=11)
note_band(s, 4.95, "LuCpu", "실행 환경",
          "단일 macOS 워크스테이션에서 상시 가동  ·  Python 3.14 (venv)  ·  Node 24  ·  tmux 세션  ·  launchd LaunchAgent 8종으로 모든 실행을 관리",
          "green", h=1.3)
footer(s, 7)

# ═══════════════════════ 09. 런타임 & 신뢰성 ═══════════════════════
s = slide()
header(s, "05  RELIABILITY", "에이전트 런타임 & 신뢰성", "LuHeartPulse", "rose")

tf = tbox(s, M, 1.74, 5.8, 0.35)
put(tf, "3중 감시 구조", 14.5, C("white"), bold=True, space=0, first=True)
TIERS = [
    ("LuServer", "green", "1단계  launchd", "com.claude.agent — KeepAlive:true / ThrottleInterval 10\n프로세스가 죽으면 launchd가 즉시 재기동"),
    ("LuRefreshCw", "amber", "2단계  agent-launcher.sh", "30초 주기 헬스체크 · 세션/프로세스 종료 시 재시작\n600초 윈도우 내 최대 10회 (재시작 폭주 방지)"),
    ("LuHeartPulse", "rose", "3단계  heartbeat.sh", "launchd가 5분마다 호출 — 살아있으나 응답 없는 hang 감지\n2회 연속(10분) 감지 시 강제 종료 후 재시작"),
]
ty = 2.2
for ic, col, head, desc in TIERS:
    card(s, M, ty, 5.8, 1.42, col)
    icon_tile(s, ic, col, M + 0.26, ty + 0.22, 0.52)
    tf = tbox(s, M + 0.94, ty + 0.24, 4.6, 0.32)
    put(tf, head, 12.5, C(col), bold=True, space=0, first=True)
    tf = tbox(s, M + 0.94, ty + 0.66, 4.66, 0.62)
    for j, ln in enumerate(desc.split("\n")):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.space_after = Pt(2)
        p.line_spacing = 1.2
        r = p.add_run()
        r.text = ln
        set_font(r, 10.5, C("white") if j == 0 else C("muted"))
    ty += 1.52

list_card(s, M + 6.13, 1.74, 5.8, 4.9, "LuListChecks", "장애 대응 / 운영", [
    "로그 10MB 자동 로테이션 (agent.log)",
    "로그인 실패 시 5분 주기 재시도 + 텔레그램 알림 (쿨다운 30분)",
    "STARTUP_GRACE 30초 — 인증·크리덴셜 로드 대기 후 헬스체크 시작",
    "스케줄 잡은 check-login.sh 프리플라이트로 사전 차단 (비용 절감)",
    "실행 결과에서 인증 에러 문자열 감지 → 서버측 토큰 무효까지 포착",
    "logs/.hang_count 마커로 연속 hang 횟수를 추적·리셋",
    "잡별 로그 분리 — agent · heartbeat · stock · weather",
    "운영 스크립트: agent-start.sh / agent-stop.sh / agent-attach.sh",
], "teal", head_size=14.5, body=11.5)
footer(s, 8)

# ═══════════════════════ 10. 스킬 시스템 ═══════════════════════
s = slide()
header(s, "06  SKILLS", "스킬 시스템 (9종)", "LuPuzzle", "amber")
skills = [
    ("LuChartCandlestick", "amber", "주식  (4)", "STOCK", [
        "stock-morning / lunch / evening",
        "→ 장 시간대별 시황 정기 브리핑",
        "stock-analyze → 단타·스윙 진입 분석",
        "market-fetcher · ticker-fetcher 공통 사용",
    ]),
    ("LuCloudSun", "teal", "날씨  (3)", "WEATHER", [
        "weather-morning / lunch / evening",
        "→ 시간대별 날씨 브리핑",
        "저녁 브리핑에 내일 날씨 포함",
    ]),
    ("LuPlane", "rose", "항공권  (2)", "FLIGHT", [
        "flight-check → 최저가 실시간 조회",
        "flight-watch → 매진편 좌석 감시·알림",
        "Playwright MCP로 네이버 항공권 렌더링",
    ]),
]
xs = [M, M + 4.02, M + 8.04]
for (ic, col, head, sub, lines), x in zip(skills, xs):
    list_card(s, x, 1.72, 3.87, 3.62, ic, head, lines, col, sub=sub)
note_band(s, 5.58, "LuPuzzle", "공통 구조",
          "SKILL.md(실행 지침) + shared-scripts(수집 로직) 조합. 스킬 단위로 독립 추가·수정이 가능해 기능 확장 비용이 낮다.",
          "violet")
footer(s, 9)

# ═══════════════════════ 11. 브리핑 파이프라인 ═══════════════════════
s = slide()
header(s, "07  PIPELINE", "주식 브리핑 파이프라인", "LuZap", "amber")
tf = tbox(s, M, 1.72, CW, 0.4)
put(tf, "launchd 정시 트리거  →  스킬 실행  →  데이터 수집  →  메시지 작성  →  Telegram 전송",
    14, C("white"), bold=True, space=0, first=True)
pipe = [
    ("1", "트리거", "amber", ["launchd LaunchAgent", "평일 07:30 / 12:30 / 17:30",
                            "check-login.sh 프리플라이트", "stock-cron.sh 호출"]),
    ("2", "수집", "teal", ["market-fetcher.py", "지수 · 선물 · 환율 · 섹터",
                          "배치 API로 일괄 수집", "실패 시 Web 폴백"]),
    ("3", "가공", "violet", ["주도 테마 TOP3", "매수 / 매도 종목 선정",
                            "실명 + 종목코드 표기", "다음 세션 관전 포인트"]),
    ("4", "전송", "green", ["모바일 가독성 포맷", "표 대신 인라인 구성",
                           "2,000자 이내로 압축", "tg-send.sh → Bot API"]),
]
xs = [M, M + 3.02, M + 6.04, M + 9.06]
for (num, head, col, lines), x in zip(pipe, xs):
    card(s, x, 2.42, 2.87, 2.95, col)
    rrect(s, x + 0.26, 2.68, 0.5, 0.5, blend(col, "ink", 0.16), blend(col, "ink", 0.36),
          radius=0.5, line_w=1.0)
    ntf = tbox(s, x + 0.26, 2.68, 0.5, 0.5, MSO_ANCHOR.MIDDLE)
    put(ntf, num, 15, C(col), bold=True, latin=FONT_EN, align=PP_ALIGN.CENTER,
        space=0, first=True)
    tf = tbox(s, x + 0.9, 2.72, 1.85, 0.42, MSO_ANCHOR.MIDDLE)
    put(tf, head, 14.5, C("white"), bold=True, space=0, first=True)
    btf = tbox(s, x + 0.26, 3.4, 2.35, 1.9)
    for i, ln in enumerate(lines):
        p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
        p.space_after = Pt(7)
        p.line_spacing = 1.25
        r1 = p.add_run()
        r1.text = "–  "
        set_font(r1, 11, C(col), True, FONT_EN, FONT_KR)
        r2 = p.add_run()
        r2.text = ln
        set_font(r2, 11, C("white"))
note_band(s, 5.6, "LuCloudSun", "날씨 파이프라인",
          "동일한 4단계 구조를 그대로 사용하며, 트리거만 weather LaunchAgent 3종(매일 08:00 / 12:00 / 18:00)으로 바뀐다.",
          "teal")
footer(s, 10)

# ═══════════════════════ 12. 스크린샷 1 ═══════════════════════
s = slide()
header(s, "07-1  SCREENSHOT", "Telegram 브리핑 — 주식 · 날씨", "LuSend", "teal")
img_fit(s, TG_STOCK, 1.5, 1.68, 4.4, 4.42)
img_fit(s, TG_WEATHER, 7.4, 1.68, 4.4, 4.42)
caption(s, 1.5, 6.24, 4.4, "▲  주식 모닝 브리핑 (평일 07:30)")
caption(s, 7.4, 6.24, 4.4, "▲  날씨 모닝 브리핑 (매일 08:00)")
caption(s, M, 6.62, CW, "* 실제 발송 데이터를 기반으로 재구성한 화면", "faint", 10, PP_ALIGN.LEFT)
footer(s, 11)

# ═══════════════════════ 13. 스크린샷 2 ═══════════════════════
s = slide()
header(s, "07-2  SCREENSHOT", "Telegram — 항공권 · 종목 분석", "LuSend", "rose")
img_fit(s, TG_FLIGHT, 1.5, 1.68, 4.4, 4.42)
img_fit(s, TG_ANALYZE, 7.4, 1.68, 4.4, 4.42)
caption(s, 1.5, 6.24, 4.4, "▲  항공권 최저가 조회 (flight-check)")
caption(s, 7.4, 6.24, 4.4, "▲  종목 진입 분석 (stock-analyze)")
caption(s, M, 6.62, CW, "* 실제 발송 포맷을 기반으로 재구성한 화면", "faint", 10, PP_ALIGN.LEFT)
footer(s, 12)

# ═══════════════════════ 14. 자동화 & 구성 관리 ═══════════════════════
s = slide()
header(s, "08  AUTOMATION", "자동화 & 구성 관리", "LuCalendarCheck", "violet")
list_card(s, M, 1.72, 3.87, 3.62, "LuClock", "스케줄 작업", [
    "주식 브리핑 — 평일 07:30 / 12:30 / 17:30",
    "날씨 브리핑 — 매일 08:00 / 12:00 / 18:00",
    "heartbeat 헬스체크 — 5분 주기",
    "에이전트 상시 구동 · 자동 복구",
], "amber")
list_card(s, M + 4.02, 1.72, 3.87, 3.62, "LuServer", "실행 메커니즘", [
    "launchd — 상시 데몬 + 정시 트리거",
    "check-login.sh — 실행 전 인증 점검",
    "tg-send.sh — 공통 Telegram 전송 유틸",
    "/loop — 감시형 작업 반복 실행",
], "green")
list_card(s, M + 8.04, 1.72, 3.87, 3.62, "LuSettings", "구성 관리", [
    ".claude/settings.json — 권한 allowlist",
    "config/env.sh — 공통 환경변수",
    ".mcp.json — Playwright MCP 등록",
    "스킬별 SKILL.md — 실행 지침",
    "LaunchAgents/*.plist — 잡 정의",
], "teal")
note_band(s, 5.58, "LuServer", "단일 운영 체계",
          "정시 실행 · 상시 구동 · 헬스체크가 모두 launchd 한 체계에서 관리되며, 잡 정의는 plist 파일로 버전 관리·재현이 가능하다.",
          "amber")
footer(s, 13)

# ═══════════════════════ 15. 보안 · 운영 고려사항 ═══════════════════════
s = slide()
header(s, "09  SECURITY", "보안 · 운영 고려사항", "LuShieldAlert", "rose")
list_card(s, M, 1.72, 5.8, 3.62, "LuLock", "현재 적용", [
    "채널 접근제어 — access 스킬 기반 페어링 승인",
    "도구 권한 allowlist (.claude/settings.json)",
    "파일 접근 범위를 프로젝트 디렉토리로 제한",
    "파괴적 작업(rm · 덮어쓰기) 전 확인 정책",
    "launchd plist에서 환경변수·작업디렉토리 고정",
], "teal")
list_card(s, M + 6.13, 1.72, 5.8, 3.62, "LuScanEye", "개선 과제", [
    "API 키 평문 저장 → 환경변수 / 시크릿 분리 필요",
    "auto-mode · skip-permissions 적용 범위 재점검",
    "로그 내 민감정보 마스킹 규칙 부재",
    "외부 전송 데이터 검토 프로세스 미비",
    "단일 계정 keychain 의존 — 만료 시 전체 스케줄 중단",
], "rose")
note_band(s, 5.58, "LuBellRing", "조치 우선순위",
          "①  시크릿(.env / keychain) 분리   ②  도구 권한 범위 축소   ③  로그 마스킹 규칙 수립   —  keychain 만료 알림이 최우선",
          "amber")
footer(s, 14)

# ═══════════════════════ 16. 성과 · 한계 · 향후 ═══════════════════════
s = slide()
header(s, "10  RESULT", "성과 · 한계 · 향후 계획", "LuSparkles", "green")
list_card(s, M, 1.72, 3.87, 3.62, "LuCircleCheck", "성과", [
    "정기 브리핑 수작업 → 완전 자동화",
    "모바일에서 즉시 정보 수신",
    "9개 스킬로 기능 모듈화",
    "3중 감시로 자동복구 상시 운영 달성",
    "launchd 단일 체계로 스케줄 운영",
], "green")
list_card(s, M + 4.02, 1.72, 3.87, 3.62, "LuTriangleAlert", "한계", [
    "단일 macOS 머신 의존 (SPOF)",
    "외부 사이트 구조 변경에 취약",
    "보안 강화 필요 (09장 참조)",
    "테스트 · 모니터링 자동화 부족",
], "amber")
list_card(s, M + 8.04, 1.72, 3.87, 3.62, "LuRocket", "향후 계획", [
    "시크릿 관리 체계화",
    "스킬 추가 (캘린더 · 메일 등)",
    "장애 알림 · 운영 지표 모니터링",
    "배포 / 이중화 검토",
], "violet")
note_band(s, 5.58, "LuFlag", "다음 마일스톤",
          "시크릿 분리와 운영 지표 모니터링을 우선 적용하고, 안정화가 확인되면 이중화(보조 실행 환경)를 검토한다.",
          "green")
footer(s, 15)

# ═══════════════════════ 17. 마무리 ═══════════════════════
s = slide()
rrect(s, 9.55, 2.35, 2.9, 2.9, blend("teal", "ink", 0.13), blend("teal", "ink", 0.3),
      radius=0.16, line_w=1.25)
icon(s, "LuMessageCircle", "teal", 10.33, 3.13, 1.34)
tf = tbox(s, 0.95, 2.7, 8.3, 0.4)
put(tf, "THANK YOU", 12, C("teal"), bold=True, latin=FONT_EN, space=0, spacing=2.2, first=True)
tf = tbox(s, 0.95, 3.2, 8.4, 2.0)
put(tf, "감사합니다", 46, C("white"), bold=True, space=10, line=1.0, first=True)
put(tf, "Q & A  ·  실 서비스 데모 시연 가능", 17, C("muted"), space=0)
tf = tbox(s, 0.95, 6.42, 11.4, 0.5)
put(tf, "~/Repositories/Claude/LMJAgent   ·   2026-08-20", 12, C("faint"),
    latin=FONT_MONO, space=0, first=True)

prs.save(OUT)
print("saved:", OUT, "| slides:", len(prs.slides._sldIdLst))
