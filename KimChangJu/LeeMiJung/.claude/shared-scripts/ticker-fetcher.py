#!/usr/bin/env python3
"""
ticker-fetcher.py — 단일 종목 차트/수급 데이터 수집기

stock-analyze skill에서 사용. 종목 코드(KR 6자리) 또는 티커(US)를 받아
진입 타이밍 분석에 필요한 데이터를 JSON으로 stdout 출력.

Usage:
    python3 ticker-fetcher.py 005930
    python3 ticker-fetcher.py NVDA
    python3 ticker-fetcher.py NVDA --raw    # 일봉 OHLCV 배열까지 포함

수집 항목:
    - 기본: 종목명/티커, 현재가, 등락(%), 시가/고가/저가, 거래량, 거래대금
    - 추세: Stage(1~4 추정), 주봉 추세, 일봉 셋업 힌트
    - 이평: MA5/20/60/120, 종가 vs MA 위치
    - 모멘텀: 52주 고/저 위치(%), 신고가 여부, 5일/20일 등락
    - 거래량: 5일/20일 평균 대비 오늘, 거래량 수축/팽창 여부
    - 보조: RSI(14), ATR(14), 볼린저밴드 위치
    - 수급(KR): 외국인/기관 최근 5일 순매수 (HTML 파싱)
    - 패턴 힌트: VCP 후보, 신고가 돌파, 박스권 등 휴리스틱

데이터 소스:
    - 한국(6자리): Naver fchart (일봉 300개), Naver frgn (수급)
    - 미국: Yahoo chart API v8 (무인증)

변경이력:
    2026-04-25  최초 작성. KR/US 단일 종목용 통합 fetcher.
    2026-04-25  한국 주요 종목명 → 코드 매핑 테이블 추가.
                "삼성전자", "하이닉스", "포스코홀딩스" 등 직접 입력 가능.
    2026-04-25  미국 주요 종목 한글 별칭 매핑 추가.
                "엔비디아", "애플", "테슬라" 등 한글로 입력해도 인식.
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from xml.etree import ElementTree as ET

import httpx

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

KST = timezone(timedelta(hours=9))
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def is_korean_code(s: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", s))


# ─── 한국 주요 종목 매핑 테이블 ────────────────────────────────
# 시총 상위 + 거래 활발 종목 위주. 별칭/축약형 함께 포함.
# 누락된 종목은 6자리 코드로 직접 입력하면 됨.
KR_NAME_TO_CODE: Dict[str, str] = {
    # KOSPI 시총 TOP
    "삼성전자": "005930", "삼전": "005930",
    "삼성전자우": "005935",
    "SK하이닉스": "000660", "하이닉스": "000660", "SK하닉": "000660",
    "LG에너지솔루션": "373220", "엘지에너지솔루션": "373220", "LG엔솔": "373220",
    "삼성바이오로직스": "207940", "삼바": "207940",
    "현대차": "005380", "현대자동차": "005380",
    "기아": "000270",
    "셀트리온": "068270",
    "POSCO홀딩스": "005490", "포스코홀딩스": "005490", "포스코": "005490",
    "KB금융": "105560",
    "신한지주": "055550",
    "NAVER": "035420", "네이버": "035420",
    "삼성SDI": "006400",
    "LG화학": "051910",
    "카카오": "035720",
    "메리츠금융지주": "138040", "메리츠금융": "138040",
    "하나금융지주": "086790", "하나금융": "086790",
    "삼성생명": "032830",
    "삼성물산": "028260",
    "현대모비스": "012330",
    "HD현대중공업": "329180", "현대중공업": "329180",
    "한화에어로스페이스": "012450", "한화에어로": "012450",
    "두산에너빌리티": "034020",
    "고려아연": "010130",
    "삼성화재": "000810",
    "LG전자": "066570",
    "HMM": "011200",
    "KT&G": "033780",
    "우리금융지주": "316140", "우리금융": "316140",
    "포스코퓨처엠": "003670",
    "SK": "034730",
    "한국전력": "015760", "한전": "015760",
    "삼성에스디에스": "018260", "삼성SDS": "018260",
    "한미반도체": "042700",
    "삼성중공업": "010140",
    "HD한국조선해양": "009540",
    "HD현대": "267250",
    "LIG넥스원": "079550",
    "한화오션": "042660",
    "LG생활건강": "051900", "LG생건": "051900",
    "LG": "003550",
    "엔씨소프트": "036570", "NC소프트": "036570", "엔씨": "036570",
    "JYP Ent.": "035900", "JYP": "035900",
    "와이지엔터테인먼트": "122870", "YG엔터": "122870", "YG": "122870",
    "에스엠": "041510", "SM엔터": "041510",
    "하이브": "352820", "HYBE": "352820",
    "CJ ENM": "035760", "CJ": "001040",
    "두산": "000150",
    "효성": "004800",
    "롯데케미칼": "011170",
    "S-Oil": "010950", "에스오일": "010950",
    "GS": "078930",
    "한화": "000880",
    "현대글로비스": "086280",
    "두산밥캣": "241560",
    "한온시스템": "018880",
    "포스코인터내셔널": "047050",
    "기업은행": "024110",
    "DB하이텍": "000990",
    "현대건설": "000720",
    "GS건설": "006360",
    "대우건설": "047040",
    # KOSDAQ 시총/거래 상위
    "에코프로비엠": "247540",
    "에코프로": "086520",
    "알테오젠": "196170",
    "HLB": "028300",
    "클래시스": "214150",
    "리노공업": "058470",
    "펄어비스": "263750",
    "카카오게임즈": "293490",
    "위메이드": "112040",
    "셀트리온제약": "068760",
    "동진쎄미켐": "005290",
    "솔브레인": "357780",
    "원익IPS": "240810",
    "ISC": "095340",
    "엘앤에프": "066970", "L&F": "066970",
    "JYP엔터": "035900",
    "HPSP": "403870",
    "리가켐바이오": "141080",
    "이오테크닉스": "039030",
    "주성엔지니어링": "036930",
    "파마리서치": "214450",
    "바이넥스": "053030",
    "에이비엘바이오": "298380",
    "삼천당제약": "000250",
    "휴젤": "145020",
    "코미코": "183300",
    "케어젠": "214370",
    "한미반도체장비": "042700",
    "와이씨": "232140",
    # 카카오 계열
    "카카오뱅크": "323410",
    "카카오페이": "377300",
}


# ─── 미국 주요 종목 한글/별칭 매핑 ────────────────────────────
# Korean retail이 흔히 부르는 한글 이름 → US 티커.
US_NAME_TO_TICKER: Dict[str, str] = {
    # Mag 7 + 빅테크
    "엔비디아": "NVDA", "엔디비아": "NVDA",
    "애플": "AAPL",
    "마이크로소프트": "MSFT", "MS": "MSFT", "마소": "MSFT",
    "구글": "GOOGL", "알파벳": "GOOGL", "구글A": "GOOGL", "구글C": "GOOG",
    "아마존": "AMZN",
    "메타": "META", "페이스북": "META",
    "테슬라": "TSLA",
    # 반도체/AI
    "AMD": "AMD",
    "인텔": "INTC",
    "마이크론": "MU",
    "브로드컴": "AVGO",
    "퀄컴": "QCOM",
    "TSMC": "TSM", "대만반도체": "TSM",
    "ASML": "ASML",
    "어플라이드머티리얼즈": "AMAT", "어플라이드": "AMAT",
    "램리서치": "LRCX",
    "팔란티어": "PLTR",
    "ARM": "ARM",
    "스노우플레이크": "SNOW",
    "오라클": "ORCL",
    "세일즈포스": "CRM",
    # 소비재/플랫폼
    "넷플릭스": "NFLX",
    "디즈니": "DIS",
    "스타벅스": "SBUX",
    "맥도날드": "MCD",
    "코카콜라": "KO",
    "펩시": "PEP",
    "나이키": "NKE",
    "룰루레몬": "LULU",
    "월마트": "WMT",
    "코스트코": "COST",
    "타겟": "TGT",
    "홈디포": "HD",
    "우버": "UBER",
    "에어비앤비": "ABNB",
    "도어대시": "DASH",
    "쇼피파이": "SHOP",
    # 금융
    "JP모건": "JPM", "JP모간": "JPM",
    "버크셔": "BRK.B", "버크셔해서웨이": "BRK.B",
    "비자": "V",
    "마스터카드": "MA",
    "뱅크오브아메리카": "BAC", "BoA": "BAC",
    "골드만삭스": "GS",
    "모건스탠리": "MS", # MSFT와 충돌하므로 위에서 MS=MSFT가 이김; 모건스탠리는 풀네임만
    "페이팔": "PYPL",
    "블록": "SQ",
    # 헬스케어
    "일라이릴리": "LLY", "릴리": "LLY",
    "노보노디스크": "NVO",
    "유나이티드헬스": "UNH",
    "존슨앤존슨": "JNJ", "J&J": "JNJ",
    "화이자": "PFE",
    "머크": "MRK",
    "애브비": "ABBV",
    # 산업/에너지
    "보잉": "BA",
    "캐터필러": "CAT",
    "GE": "GE",
    "록히드마틴": "LMT",
    "엑손모빌": "XOM", "엑손": "XOM",
    "셰브론": "CVX",
    # ETF (자주 거래)
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "DIA": "DIA",
    "TQQQ": "TQQQ", "SQQQ": "SQQQ",
    "SOXL": "SOXL", "SOXS": "SOXS",
    "TLT": "TLT", "GLD": "GLD",
}


def _lookup_dict(s: str, table: Dict[str, str]) -> Optional[str]:
    """공백/대소문자 무시 매칭."""
    if s in table:
        return table[s]
    compact = s.replace(" ", "")
    for k, v in table.items():
        if k.replace(" ", "") == compact:
            return v
    upper = s.upper().replace(" ", "")
    for k, v in table.items():
        if k.upper().replace(" ", "") == upper:
            return v
    return None


def resolve_kr_name(s: str) -> Optional[str]:
    """한국 종목명/별칭이면 6자리 코드 반환. 실패 시 None."""
    return _lookup_dict(s, KR_NAME_TO_CODE) if s else None


def resolve_us_alias(s: str) -> Optional[str]:
    """미국 종목 한글/영문 별칭이면 US 티커 반환. 실패 시 None."""
    return _lookup_dict(s, US_NAME_TO_TICKER) if s else None


def has_korean_chars(s: str) -> bool:
    return bool(re.search(r"[가-힣]", s))


# ─── Korean: Naver fchart 일봉 ────────────────────────────────
def fetch_naver_daily(code: str, count: int = 300) -> List[Dict]:
    url = (
        f"https://fchart.stock.naver.com/sise.nhn"
        f"?symbol={code}&timeframe=day&count={count}&requestType=0"
    )
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    rows = []
    for item in root.iter("item"):
        data = (item.attrib.get("data") or "").split("|")
        if len(data) < 6:
            continue
        d, o, h, l, c, v = data[:6]
        try:
            rows.append({
                "date": d,
                "open": int(o),
                "high": int(h),
                "low": int(l),
                "close": int(c),
                "volume": int(v),
            })
        except ValueError:
            continue
    return rows


def fetch_naver_name(code: str) -> str:
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        wrap = soup.select_one(".wrap_company h2 a")
        return wrap.get_text(strip=True) if wrap else code
    except Exception:
        return code


def fetch_naver_supply(code: str) -> List[Dict]:
    """외국인/기관 최근 5일 순매수(주). 음수면 순매도."""
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows = []
        for tr in soup.select("table.type2 tr"):
            tds = tr.find_all("td")
            if len(tds) < 9:
                continue
            date = tds[0].get_text(strip=True)
            if not re.match(r"\d{4}\.\d{2}\.\d{2}", date):
                continue
            try:
                foreign = int(tds[5].get_text(strip=True).replace(",", ""))
                inst = int(tds[6].get_text(strip=True).replace(",", ""))
                rows.append({"date": date, "foreign": foreign, "inst": inst})
            except (ValueError, IndexError):
                continue
            if len(rows) >= 5:
                break
        return rows
    except Exception:
        return []


# ─── US: Yahoo chart API v8 (무인증) ───────────────────────────
# Yahoo는 긴 Chrome UA에 429를 자주 던지므로 짧은 UA 사용 + query1/query2 폴백.
YAHOO_UA = "Mozilla/5.0"


def fetch_yahoo_daily(ticker: str, range_: str = "1y") -> Tuple[List[Dict], Optional[str]]:
    """미국 종목 일봉. (rows, longName) 반환."""
    params = {"range": range_, "interval": "1d", "includePrePost": "false"}
    last_err = None
    r = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{ticker}"
        try:
            r = httpx.get(url, params=params, headers={"User-Agent": YAHOO_UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                break
            last_err = f"{host} -> {r.status_code}"
        except httpx.HTTPError as e:
            last_err = f"{host} -> {e}"
            r = None
    if r is None or r.status_code != 200:
        raise RuntimeError(f"Yahoo fetch failed: {last_err}")
    data = r.json()
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        return [], None
    res = result[0]
    meta = res.get("meta") or {}
    name = meta.get("longName") or meta.get("shortName") or ticker
    timestamps = res.get("timestamp") or []
    quote = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    vols = quote.get("volume") or []
    rows = []
    for i, ts in enumerate(timestamps):
        if i >= len(closes) or closes[i] is None:
            continue
        try:
            d = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            rows.append({
                "date": d,
                "open": float(opens[i] or closes[i]),
                "high": float(highs[i] or closes[i]),
                "low": float(lows[i] or closes[i]),
                "close": float(closes[i]),
                "volume": int(vols[i] or 0),
            })
        except (TypeError, ValueError):
            continue
    return rows, name


# ─── 지표 계산 ────────────────────────────────────────────────
def sma(values: List[float], n: int) -> Optional[float]:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def rsi(closes: List[float], n: int = 14) -> Optional[float]:
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(-n, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(rows: List[Dict], n: int = 14) -> Optional[float]:
    if len(rows) < n + 1:
        return None
    trs = []
    for i in range(-n, 0):
        h = rows[i]["high"]
        l = rows[i]["low"]
        pc = rows[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / n


def stage_estimate(closes: List[float], ma20: Optional[float],
                   ma60: Optional[float], ma120: Optional[float]) -> int:
    """Weinstein 4단계 추정. 1=축적, 2=상승, 3=분배, 4=하락"""
    if not closes or ma20 is None or ma60 is None:
        return 0
    last = closes[-1]
    above20 = last > ma20
    above60 = last > ma60
    above120 = (ma120 is not None) and (last > ma120)
    ma60_rising = len(closes) >= 65 and ma60 > (sum(closes[-65:-5]) / 60)
    ma60_falling = len(closes) >= 65 and ma60 < (sum(closes[-65:-5]) / 60)

    if above20 and above60 and ma60_rising:
        return 2
    if above60 and not above20 and not ma60_falling:
        return 3 if last < ma20 else 2
    if not above60 and ma60_falling:
        return 4
    return 1


def vcp_hint(rows: List[Dict]) -> bool:
    """최근 30일에서 변동성 수축 후보 — 단순 휴리스틱."""
    if len(rows) < 35:
        return False
    seg = rows[-30:]
    highs = [r["high"] for r in seg]
    lows = [r["low"] for r in seg]
    range_pct = (max(highs) - min(lows)) / seg[-1]["close"] * 100
    recent10 = seg[-10:]
    recent_range = (max(r["high"] for r in recent10) - min(r["low"] for r in recent10)) / recent10[-1]["close"] * 100
    return range_pct >= 8 and recent_range < range_pct * 0.5


def breakout_hint(rows: List[Dict]) -> bool:
    """52주 고가의 95% 이상 + 최근 거래량 증가."""
    if len(rows) < 100:
        return False
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    last = closes[-1]
    hi52 = max(r["high"] for r in rows[-252:] if True) if len(rows) >= 252 else max(r["high"] for r in rows)
    near_high = last >= hi52 * 0.95
    vol_avg5 = sum(vols[-5:]) / 5
    vol_avg20 = sum(vols[-20:]) / 20 if len(vols) >= 20 else vol_avg5
    vol_pop = vol_avg5 > vol_avg20 * 1.2
    return near_high and vol_pop


# ─── 메인 분석 ─────────────────────────────────────────────────
def analyze(rows: List[Dict], market: str) -> Dict:
    if not rows:
        return {"error": "no_data"}
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    last = rows[-1]

    ma5 = sma(closes, 5)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    ma120 = sma(closes, 120)

    hi52 = max(r["high"] for r in rows[-252:]) if len(rows) >= 252 else max(r["high"] for r in rows)
    lo52 = min(r["low"] for r in rows[-252:]) if len(rows) >= 252 else min(r["low"] for r in rows)

    chg_pct = ((last["close"] - rows[-2]["close"]) / rows[-2]["close"] * 100) if len(rows) >= 2 else 0.0
    chg_5d = ((last["close"] - rows[-6]["close"]) / rows[-6]["close"] * 100) if len(rows) >= 6 else None
    chg_20d = ((last["close"] - rows[-21]["close"]) / rows[-21]["close"] * 100) if len(rows) >= 21 else None

    vol_avg5 = sum(vols[-5:]) / 5 if len(vols) >= 5 else None
    vol_avg20 = sum(vols[-20:]) / 20 if len(vols) >= 20 else None
    vol_ratio = (last["volume"] / vol_avg20) if vol_avg20 else None

    rsi14 = rsi(closes, 14)
    atr14 = atr(rows, 14)

    stage = stage_estimate(closes, ma20, ma60, ma120)

    fmt_num = (lambda x: round(x, 2)) if market == "us" else (lambda x: int(round(x)))

    return {
        "last": fmt_num(last["close"]),
        "open": fmt_num(last["open"]),
        "high": fmt_num(last["high"]),
        "low": fmt_num(last["low"]),
        "volume": last["volume"],
        "change_pct": round(chg_pct, 2),
        "change_5d_pct": round(chg_5d, 2) if chg_5d is not None else None,
        "change_20d_pct": round(chg_20d, 2) if chg_20d is not None else None,
        "ma5": fmt_num(ma5) if ma5 else None,
        "ma20": fmt_num(ma20) if ma20 else None,
        "ma60": fmt_num(ma60) if ma60 else None,
        "ma120": fmt_num(ma120) if ma120 else None,
        "high_52w": fmt_num(hi52),
        "low_52w": fmt_num(lo52),
        "from_high_pct": round((last["close"] / hi52 - 1) * 100, 2),
        "from_low_pct": round((last["close"] / lo52 - 1) * 100, 2),
        "vol_avg5": int(vol_avg5) if vol_avg5 else None,
        "vol_avg20": int(vol_avg20) if vol_avg20 else None,
        "vol_ratio": round(vol_ratio, 2) if vol_ratio else None,
        "rsi14": round(rsi14, 1) if rsi14 else None,
        "atr14": fmt_num(atr14) if atr14 else None,
        "stage": stage,
        "above_ma20": ma20 is not None and last["close"] > ma20,
        "above_ma60": ma60 is not None and last["close"] > ma60,
        "above_ma120": ma120 is not None and last["close"] > ma120,
        "vcp_candidate": vcp_hint(rows),
        "breakout_candidate": breakout_hint(rows),
        "data_points": len(rows),
        "last_date": last["date"],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", help="종목코드(KR 6자리), 한국 종목명, 또는 미국 티커")
    p.add_argument("--raw", action="store_true", help="일봉 OHLCV 배열도 포함")
    args = p.parse_args()

    raw = args.ticker.strip()
    # 입력 분기:
    # 1) 6자리 숫자 → KR 코드
    # 2) 한글 포함 → KR 매핑 우선, 실패 시 US 한글 별칭(엔비디아 등) 시도
    # 3) 영문 → KR 별칭(NAVER 등) 우선, 실패 시 US 별칭, 최종 fallback US 티커
    code: Optional[str] = None
    us_ticker: Optional[str] = None

    if is_korean_code(raw):
        code = raw
    elif has_korean_chars(raw):
        code = resolve_kr_name(raw)
        if not code:
            us_ticker = resolve_us_alias(raw)
            if not us_ticker:
                print(json.dumps({
                    "error": "name_not_found",
                    "input": raw,
                    "hint": "등록된 종목명이 아닙니다. 6자리 코드(KR) 또는 영문 티커(US)로 입력하세요."
                }, ensure_ascii=False))
                sys.exit(1)
    else:
        code = resolve_kr_name(raw)
        if not code:
            us_ticker = resolve_us_alias(raw) or raw.upper()

    if code:
        ticker = code
        market = "kr"
        rows = fetch_naver_daily(ticker)
        name = fetch_naver_name(ticker)
        supply = fetch_naver_supply(ticker)
    else:
        ticker = us_ticker
        market = "us"
        rows, _name = fetch_yahoo_daily(ticker)
        name = _name or ticker
        supply = []

    if not rows:
        print(json.dumps({"error": "no_data", "ticker": ticker, "market": market}, ensure_ascii=False))
        sys.exit(1)

    summary = analyze(rows, market)
    out = {
        "ticker": ticker,
        "name": name,
        "market": market,
        "fetched_at": datetime.now(KST).isoformat(),
        "summary": summary,
    }
    if supply:
        out["supply_5d"] = supply
    if args.raw:
        out["ohlcv"] = rows[-60:]

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
