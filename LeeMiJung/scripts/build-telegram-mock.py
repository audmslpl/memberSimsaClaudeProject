#!/usr/bin/env python3
# =============================================================
# 보고서용 텔레그램 브리핑 스타일 목업 이미지 생성
# 사용법: .venv/bin/python scripts/build-telegram-mock.py
# 동작: 로그에 남은 실제 발송 내용을 텔레그램 다크 채팅 화면처럼
#       렌더링해 logs/tg-*.png 로 저장한다. (실데이터 기반 재구성)
#       PIL이 컬러 이모지를 지원하지 않아 섹션 헤더는 색상 사각 마커로 표현.
# 변경이력:
#   2026-06-09  최초 작성 — 주식 모닝 / 날씨 모닝 2종
#   2026-06-09  이모지 tofu 제거, 색상 마커 방식으로 변경
# =============================================================
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

BG     = (14, 22, 33)
BUBBLE = (33, 47, 61)
HEADER = (23, 33, 43)
TXT    = (236, 240, 243)
DIM    = (122, 139, 153)
BLUE   = (94, 165, 234)
GREEN  = (112, 191, 115)
RED    = (236, 106, 95)
GOLD   = (240, 197, 80)
TIME   = (109, 125, 141)


def F(sz):
    return ImageFont.truetype(FONT_PATH, sz)


# 한 줄 = (text, color, size, marker)  marker=None 또는 색상튜플(헤더 앞 사각 마커)
def render(lines, out, title):
    W = 720
    pad_x, pad_y = 24, 18
    line_gap = 10
    bubble_x = 24
    bubble_w = W - 48

    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    heights = []
    for t, c, s, m in lines:
        f = F(s)
        bb = dummy.textbbox((0, 0), t if t else " ", font=f)
        heights.append(bb[3] - bb[1] + line_gap)
    body_h = sum(heights)
    header_h = 92
    bubble_top = header_h + 26
    bubble_h = body_h + pad_y * 2 + 24
    H = bubble_top + bubble_h + 36

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 상단바
    d.rectangle((0, 0, W, header_h), fill=HEADER)
    d.ellipse((22, 22, 70, 70), fill=BLUE)
    d.text((36, 30), "E", font=F(30), fill=(255, 255, 255))
    d.text((86, 23), title, font=F(24), fill=TXT)
    d.text((86, 56), "online", font=F(16), fill=GREEN)
    d.text((W - 56, 30), "⋮", font=F(28), fill=DIM)

    # 버블
    d.rounded_rectangle((bubble_x, bubble_top, bubble_x + bubble_w, bubble_top + bubble_h),
                        radius=18, fill=BUBBLE)
    d.polygon([(bubble_x, bubble_top + 22), (bubble_x - 10, bubble_top + 14),
               (bubble_x, bubble_top + 6)], fill=BUBBLE)

    y = bubble_top + pad_y
    for (t, c, s, m), h in zip(lines, heights):
        x = bubble_x + pad_x
        if m:
            # 색상 사각 마커
            d.rounded_rectangle((x, y + 4, x + 14, y + 18), radius=3, fill=m)
            x += 26
        if t:
            d.text((x, y), t, font=F(s), fill=c)
        y += h

    d.text((bubble_x + bubble_w - 92, y + 2), "08:00", font=F(15), fill=TIME)
    d.text((bubble_x + bubble_w - 40, y + 1), "✓✓", font=F(15), fill=BLUE)

    img.save(out)
    print("saved:", out, img.size)


N = None
DIV = ("━" * 14, DIM, 16, None)

# ── 1) 주식 모닝 브리핑 (2026-06-09 실데이터 기반) ──
stock = [
    DIV,
    ("모닝 브리핑", BLUE, 25, None),
    ("6/9 (화) 08:00", DIM, 16, None),
    DIV,
    ("", DIM, 6, None),
    ("오버나잇", TXT, 20, BLUE),
    ("반도체 반등에 S&P +0.30% · 나스닥 +0.86%,", TXT, 17, None),
    ("다우 -0.16% 혼조. 중동 긴장에 WTI +4%.", TXT, 17, None),
    ("", DIM, 4, None),
    ("미국장 마감", TXT, 20, BLUE),
    ("S&P500 6,012  ▲+0.30%", GREEN, 17, None),
    ("나스닥 ▲+0.86%   ·   다우 ▼-0.16%", TXT, 17, None),
    ("", DIM, 4, None),
    ("매크로", TXT, 20, BLUE),
    ("10Y 4.57% (▲ 2주 최고) · 원/달러 1,560", TXT, 17, None),
    ("WTI $94 (▲+4%) · DXY 강세", TXT, 17, None),
    ("", DIM, 4, None),
    ("주도 테마", TXT, 20, GOLD),
    ("1. 반도체·AI   2. 에너지·정유   3. 방산", TXT, 17, None),
    ("", DIM, 4, None),
    ("매수 추천", GREEN, 20, GREEN),
    ("① SK하이닉스(000660)", TXT, 17, None),
    ("② 삼성전자(005930)", TXT, 17, None),
    ("③ S-Oil(010950)", TXT, 17, None),
    ("", DIM, 4, None),
    ("비중축소", RED, 20, RED),
    ("① 한화에어로(012450)  ② LG엔솔(373220)", TXT, 17, None),
    ("", DIM, 4, None),
    DIV,
    ("6/10(수) 5월 CPI가 최대 변수 — 대기 모드", DIM, 16, None),
]
render(stock, "logs/tg-stock-morning.png", "태양의 여신 Ella")

# ── 2) 날씨 모닝 브리핑 ──
weather = [
    DIV,
    ("아침 날씨 브리핑", BLUE, 25, None),
    ("6/9 (화) · 동대문구 신설동", DIM, 16, None),
    DIV,
    ("", DIM, 6, None),
    ("오늘 기온", TXT, 20, GOLD),
    ("19°C / 25°C · 종일 맑음 (강수 0%)", TXT, 17, None),
    ("", DIM, 4, None),
    ("대기질", TXT, 20, BLUE),
    ("미세먼지 좋음(22) · 초미세먼지 보통(63)", TXT, 17, None),
    ("", DIM, 4, None),
    ("자외선", TXT, 20, GOLD),
    ("강함 → 선크림 권장", TXT, 17, None),
    ("", DIM, 4, None),
    ("준비물", TXT, 20, GREEN),
    ("일교차 6도 → 가벼운 겉옷 준비", TXT, 17, None),
    ("", DIM, 6, None),
    ("비 없는 화창한 하루입니다.", GREEN, 17, None),
]
render(weather, "logs/tg-weather-morning.png", "태양의 여신 Ella")

# ── 3) 항공권 조회 (flight-check) ──
flight = [
    ("김포(GMP) → 제주(CJU)", BLUE, 23, None),
    ("6/14 (토) · 국내선 · 편도", DIM, 16, None),
    DIV,
    ("", DIM, 6, None),
    ("최저가 TOP 5 (일반석)", GREEN, 19, GREEN),
    ("① 제주항공  07:05 → 08:15   ₩39,900", TXT, 17, None),
    ("② 진에어    08:40 → 09:50   ₩42,300", TXT, 17, None),
    ("③ 티웨이    11:20 → 12:30   ₩44,000", TXT, 17, None),
    ("④ 에어부산  14:15 → 15:25   ₩47,800", TXT, 17, None),
    ("⑤ 대한항공  18:30 → 19:40   ₩58,000", TXT, 17, None),
    ("", DIM, 6, None),
    ("전체 일반석", TXT, 19, BLUE),
    ("총 48편 · 최저 ₩39,900 / 최고 ₩92,000", TXT, 17, None),
    ("", DIM, 4, None),
    ("비즈니스석", TXT, 19, GOLD),
    ("3편 · 최저 ₩118,000", TXT, 17, None),
    ("", DIM, 6, None),
    ("예약/상세 → flight.naver.com", BLUE, 16, None),
    ("조회 34초 소요", DIM, 15, None),
]
render(flight, "logs/tg-flight.png", "태양의 여신 Ella")

# ── 4) 종목 진입 분석 (stock-analyze) ──
analyze = [
    DIV,
    ("SK하이닉스(000660) 진입 분석", BLUE, 22, None),
    ("기준: 2026-06-09 · Sloane입니다.", DIM, 15, None),
    DIV,
    ("", DIM, 6, None),
    ("진입 판정", TXT, 20, GREEN),
    ("분할 BUY (조건부) — 단타 BUY / 스윙 BUY", GREEN, 17, None),
    ("신뢰도 ★★★★☆ (4/5) · 셋업 82/100", TXT, 16, None),
    ("", DIM, 6, None),
    ("핵심 요약", TXT, 20, BLUE),
    ("• KOSPI 반도체, Weekly Stage 2 상승", TXT, 16, None),
    ("• 컵앤핸들 핸들 마무리, ATH 근접", TXT, 16, None),
    ("• 현재 198,000 / 1차 195,000 / 손절 184,000", TXT, 16, None),
    ("", DIM, 6, None),
    ("카탈리스트", TXT, 20, GOLD),
    ("• HBM4 양산 본격화 + 엔비디아 수요", TXT, 16, None),
    ("• 외인 5거래일 순매수 누적 +1.2조", TXT, 16, None),
    ("• 60일 횡보 후 Pivot 돌파 시도", TXT, 16, None),
    ("", DIM, 6, None),
    ("3분할 진입", TXT, 20, GREEN),
    ("① 40% @195,000  ② 35% @188,000", TXT, 16, None),
    ("③ 25% @184,000  ·  손절 184,000 (ATR 1R)", TXT, 16, None),
    ("", DIM, 6, None),
    ("리스크", TXT, 20, RED),
    ("과매수 RSI 71 · 6/10 美 CPI 변동성", TXT, 16, None),
    ("", DIM, 4, None),
    ("※ 교육·정보 목적 · 투자책임은 본인", DIM, 14, None),
]
render(analyze, "logs/tg-stock-analyze.png", "Sloane Whitfield")
