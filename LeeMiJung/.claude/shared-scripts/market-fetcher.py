#!/usr/bin/env python3
"""
market-fetcher.py — 시장 데이터 병렬 수집기

모든 금융/날씨/대기질 데이터를 동시에 가져와서 JSON으로 출력.
Stooq(미국) + Naver(국내) + Finviz(섹터) + aqicn/weatheri 병렬 수집.
Yahoo 의존성 제거 — crumb 429 이슈에서 자유.

Usage:
    python3 market-fetcher.py              # 전체 데이터
    python3 market-fetcher.py --market     # 시장 데이터만
    python3 market-fetcher.py --weather    # 날씨+대기질만
    python3 market-fetcher.py --stocks 010950,000660,012450  # 한국 종목 추가

동작 흐름:
    1) 미국 지수/매크로/선물/환율 → Stooq 단일쿼트 CSV (무인증)
    2) KOSPI/KOSDAQ/국내종목 → Naver 실시간 폴링 API
    3) 섹터: Finviz(미국 11개) + Naver(한국 주요 18개)
    4) 날씨/대기질: weatheri + aqicn
    5) 결과를 그룹(us_indices/korean_indices/us_futures/macro/fx)으로 매핑해 JSON 출력

변경이력:
    2026-04-19  Yahoo crumb 디스크 캐시(1h TTL) + 지수 백오프/지터 +
                Retry-After 헤더 존중 + 스테일 캐시 폴백 추가 (429 완화).
    2026-04-19  Yahoo 전면 실패 시 Stooq(미국지수/매크로/선물/환율) +
                Naver(KOSPI/KOSDAQ/국내종목) 폴백 경로 추가.
    2026-04-19  성능 튜닝: 국내(KOSPI/KOSDAQ/종목)는 Naver가 primary로 항상 호출.
                Yahoo는 미국지수/매크로/선물/환율만 담당. crumb 429는 즉시 실패
                (재시도 없이 Stooq로 폴백). 장애 시 수집 시간 30s+ → ~2s.
    2026-04-19  Yahoo 의존성 제거. Stooq + Naver primary 구조로 단순화.
                crumb/쿠키 캐시 파일, 재시도 로직, fetch_yahoo_batch 삭제.
                DXY는 Stooq dx.f (ICE USD Index futures)로 공급.
                Russell 2000 / VIX / US 10Y 는 무인증 소스 부재로 제외.
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

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

# ─── 심볼 정의 ──────────────────────────────────────────────
# history.py가 YAHOO_SYMBOLS를 import해서 chart 엔드포인트용 심볼로 쓰므로
# 이 매핑은 "Yahoo chart API(무인증) 참조용"으로 유지.

YAHOO_SYMBOLS = {
    # 미국 지수
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "russell2000": "^RUT",
    # 한국 지수
    "kospi": "^KS11",
    "kosdaq": "^KQ11",
    # 미국 선물
    "sp500_fut": "ES=F",
    "nasdaq_fut": "NQ=F",
    "dow_fut": "YM=F",
    # 매크로
    "us10y": "^TNX",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "wti": "CL=F",
    "gold": "GC=F",
    # 환율
    "usdkrw": "USDKRW=X",
}

# Stooq 무료 단일쿼트 엔드포인트(/q/l/, apikey 불필요)로 가져올 심볼.
# 매핑 없는 키(russell2000, vix, us10y)는 무인증 소스 부재로 제외.
STOOQ_SYMBOLS = {
    "sp500": "^spx",
    "nasdaq": "^ndq",
    "dow": "^dji",
    "sp500_fut": "es.f",
    "nasdaq_fut": "nq.f",
    "dow_fut": "ym.f",
    "wti": "cl.f",
    "gold": "gc.f",
    "dxy": "dx.f",  # ICE U.S. Dollar Index Futures
    "usdkrw": "usdkrw",
}

# 출력 구조 매핑
GROUP_MAP = {
    "sp500": "us_indices", "nasdaq": "us_indices",
    "dow": "us_indices", "russell2000": "us_indices",
    "kospi": "korean_indices", "kosdaq": "korean_indices",
    "sp500_fut": "us_futures", "nasdaq_fut": "us_futures",
    "dow_fut": "us_futures",
    "us10y": "macro", "vix": "macro", "dxy": "macro",
    "wti": "macro", "gold": "macro",
    "usdkrw": "fx",
}


# ─── Stooq (미국 지수/매크로/선물/환율) ──────────────────────

async def fetch_stooq_quotes(
    client: httpx.AsyncClient, keys: List[str]
) -> Dict[str, dict]:
    """Stooq /q/l/ 단일 쿼트 CSV (apikey 불필요). 키별 병렬 호출.

    fetch_yahoo_batch와 동일한 dict shape 반환:
      {key: {price, prev_close, change, change_pct}}
    """
    mapped = [(k, STOOQ_SYMBOLS[k]) for k in keys if k in STOOQ_SYMBOLS]
    if not mapped:
        return {}

    async def _one(key: str, sym: str):
        url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcp&h&e=csv"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return key, None
            lines = resp.text.strip().splitlines()
            if len(lines) < 2:
                return key, None
            parts = lines[1].split(",")
            if len(parts) < 8 or "N/D" in parts:
                return key, None
            close = float(parts[6])
            prev = float(parts[7])
            change = close - prev
            change_pct = (change / prev * 100) if prev else 0
            return key, {
                "price": round(close, 2),
                "prev_close": round(prev, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
            }
        except Exception:
            return key, None

    results = await asyncio.gather(*(_one(k, s) for k, s in mapped))
    return {k: v for k, v in results if v is not None}


# ─── Naver 폴백 (국내 지수/종목) ─────────────────────────────

_NAVER_HEADERS = {"Referer": "https://finance.naver.com/"}


async def _naver_polling_parse(
    client: httpx.AsyncClient, url: str
) -> Optional[dict]:
    try:
        resp = await client.get(url, headers=_NAVER_HEADERS)
        if resp.status_code != 200:
            return None
        datas = resp.json().get("datas") or []
        if not datas:
            return None
        d = datas[0]
        close = float(d["closePriceRaw"])
        change = float(d["compareToPreviousClosePriceRaw"])
        change_pct = float(d["fluctuationsRatioRaw"])
        prev = close - change
        out = {
            "price": round(close, 2),
            "prev_close": round(prev, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
        if "stockName" in d:
            out["name"] = d["stockName"]
        return out
    except Exception:
        return None


async def fetch_naver_korean_indices(
    client: httpx.AsyncClient,
) -> Dict[str, dict]:
    """KOSPI/KOSDAQ을 Naver 실시간 폴링 API로 조회."""
    base = "https://polling.finance.naver.com/api/realtime/domestic/index/"
    kospi, kosdaq = await asyncio.gather(
        _naver_polling_parse(client, base + "KOSPI"),
        _naver_polling_parse(client, base + "KOSDAQ"),
    )
    out: Dict[str, dict] = {}
    if kospi:
        out["kospi"] = kospi
    if kosdaq:
        out["kosdaq"] = kosdaq
    return out


async def fetch_naver_korean_stocks(
    client: httpx.AsyncClient, codes: List[str]
) -> Dict[str, dict]:
    """한국 종목 코드들을 Naver 실시간 폴링 API로 조회."""
    base = "https://polling.finance.naver.com/api/realtime/domestic/stock/"
    results = await asyncio.gather(
        *(_naver_polling_parse(client, base + c) for c in codes)
    )
    return {c: v for c, v in zip(codes, results) if v is not None}


async def _fetch_naver_index_intraday_one(
    client: httpx.AsyncClient, code: str, points: int = 30
) -> List[float]:
    """Naver 지수 분봉 API에서 당일 minute 종가 시퀀스 (다운샘플)."""
    url = f"https://api.stock.naver.com/chart/domestic/index/{code}/minute"
    try:
        resp = await client.get(url, headers=_NAVER_HEADERS)
        if resp.status_code != 200:
            return []
        rows = resp.json() or []
        prices = [
            float(r["currentPrice"]) for r in rows
            if r.get("currentPrice") is not None
        ]
        if not prices or len(prices) <= points:
            return prices
        step = len(prices) / points
        return [prices[int(i * step)] for i in range(points)] + [prices[-1]]
    except Exception:
        return []


async def fetch_naver_index_intraday(
    client: httpx.AsyncClient,
) -> Dict[str, List[float]]:
    """KOSPI/KOSDAQ 지수의 분봉 시세를 스파크라인용 ~30 포인트로 요약."""
    kospi, kosdaq = await asyncio.gather(
        _fetch_naver_index_intraday_one(client, "KOSPI"),
        _fetch_naver_index_intraday_one(client, "KOSDAQ"),
    )
    out: Dict[str, List[float]] = {}
    if kospi:
        out["kospi"] = kospi
    if kosdaq:
        out["kosdaq"] = kosdaq
    return out


async def _fetch_naver_stock_intraday_one(
    client: httpx.AsyncClient, code: str, points: int = 30
) -> List[float]:
    """Naver 분봉 API에서 당일 minute close price 시퀀스 가져오기 (다운샘플)."""
    url = f"https://api.stock.naver.com/chart/domestic/item/{code}/minute"
    try:
        resp = await client.get(url, headers=_NAVER_HEADERS)
        if resp.status_code != 200:
            return []
        rows = resp.json() or []
        prices = [
            float(r["currentPrice"]) for r in rows
            if r.get("currentPrice") is not None
        ]
        if not prices or len(prices) <= points:
            return prices
        step = len(prices) / points
        return [prices[int(i * step)] for i in range(points)] + [prices[-1]]
    except Exception:
        return []


async def fetch_naver_korean_stocks_intraday(
    client: httpx.AsyncClient, codes: List[str]
) -> Dict[str, List[float]]:
    """국내 종목들의 분봉 시세를 스파크라인용 ~30 포인트로 요약해 반환."""
    results = await asyncio.gather(
        *(_fetch_naver_stock_intraday_one(client, c) for c in codes)
    )
    return {c: v for c, v in zip(codes, results) if v}


# ─── Naver 섹터 (한국 업종) ──────────────────────────────────

# 대시보드 히트맵용 핵심 KR 섹터 화이트리스트 (12개 — 6×2 그리드).
# Naver 업종 이름 기준. 대표성 낮거나 종목 수 적은 업종 제외.
_KR_IMPORTANT_SECTORS = {
    "반도체와반도체장비",
    "자동차부품",
    "디스플레이장비및부품",
    "전자장비와기기",
    "화학",
    "철강",
    "조선",
    "건설",
    "제약",
    "소프트웨어",
    "은행",
    "게임엔터테인먼트",
}


async def fetch_naver_sectors(client: httpx.AsyncClient) -> Optional[dict]:
    """Naver 모바일 API로 한국 업종(섹터)별 등락률 수집.

    _KR_IMPORTANT_SECTORS 화이트리스트로 필터링해 주요 섹터만 반환.
    반환 shape은 fetch_finviz_sectors와 동일: {top, bottom, all}
    """
    url = "https://m.stock.naver.com/api/stocks/industry?pageSize=100"
    try:
        resp = await client.get(url, headers=_NAVER_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        groups = data.get("groups") or []
        all_sectors = []
        for g in groups:
            name = g.get("name")
            rate = g.get("changeRate")
            if not name or rate is None:
                continue
            try:
                pct = float(rate)
            except (TypeError, ValueError):
                continue
            all_sectors.append({
                "name": name,
                "change_pct": pct,
                "count": g.get("totalCount"),
            })
        if not all_sectors:
            return {"error": "no sectors"}
        all_sectors.sort(key=lambda x: x["change_pct"], reverse=True)

        # 화이트리스트 우선. 음수 섹터가 MIN_NEG 미만이면 비화이트리스트에서
        # 가장 하락률 큰 섹터로 채워 히트맵이 "상승만" 보이지 않게 보장.
        TARGET_TOTAL = 12
        MIN_NEG = 3
        whitelisted = [
            s for s in all_sectors if s["name"] in _KR_IMPORTANT_SECTORS
        ]
        neg_in_wl = sum(1 for s in whitelisted if s["change_pct"] < 0)
        if neg_in_wl >= MIN_NEG or len(whitelisted) < TARGET_TOTAL:
            result = whitelisted[:TARGET_TOTAL]
        else:
            needed = MIN_NEG - neg_in_wl
            non_wl_neg = sorted(
                (s for s in all_sectors
                 if s["name"] not in _KR_IMPORTANT_SECTORS
                 and s["change_pct"] < 0),
                key=lambda x: x["change_pct"],
            )[:needed]
            # 화이트리스트 하단(양수 중 제일 약한 것)을 needed 만큼 제거해 자리 확보
            pos_wl = [s for s in whitelisted if s["change_pct"] >= 0]
            neg_wl = [s for s in whitelisted if s["change_pct"] < 0]
            drop = len(non_wl_neg)
            pos_kept = pos_wl[:-drop] if drop else pos_wl
            result = pos_kept + neg_wl + non_wl_neg
            result.sort(key=lambda x: x["change_pct"], reverse=True)

        return {
            "top": result[:2],
            "bottom": result[-2:] if len(result) >= 2 else result,
            "all": result,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Finviz 섹터 ─────────────────────────────────────────────

async def fetch_finviz_sectors(client: httpx.AsyncClient) -> Optional[dict]:
    """Finviz에서 섹터별 일간 등락률 가져오기."""
    url = "https://finviz.com/groups.ashx?g=sector&v=110&o=name"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text
        sectors = []

        if HAS_BS4:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select('a[href*="f=sec_"]'):
                name = link.get_text(strip=True)
                if not name:
                    continue
                row = link.find_parent("tr")
                if not row:
                    continue
                for td in reversed(row.find_all("td")):
                    text = td.get_text(strip=True)
                    m = re.search(r'([-+]?\d+\.\d+)%', text)
                    if m:
                        sectors.append({
                            "name": name,
                            "change_pct": float(m.group(1)),
                        })
                        break
        else:
            for m in re.finditer(
                r'f=sec_[^"]*">([^<]+)</a>.*?([-+]?\d+\.\d+)%',
                html, re.DOTALL,
            ):
                sectors.append({
                    "name": m.group(1).strip(),
                    "change_pct": float(m.group(2)),
                })

        # 중복 제거
        seen = set()
        unique = []
        for s in sectors:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique.append(s)

        sorted_s = sorted(unique, key=lambda x: x["change_pct"], reverse=True)
        return {
            "top": sorted_s[:2],
            "bottom": sorted_s[-2:] if len(sorted_s) >= 2 else sorted_s,
            "all": sorted_s,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── 대기질 (aqicn) ──────────────────────────────────────────

async def fetch_air_quality(client: httpx.AsyncClient) -> Optional[dict]:
    """WAQI API로 서울 대기질 데이터 가져오기."""
    url = "https://api.waqi.info/feed/seoul/?token=demo"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            return {"error": "API status: " + str(data.get("status"))}

        feed = data["data"]
        result = {
            "overall_aqi": feed.get("aqi"),
        }

        iaqi = feed.get("iaqi", {})
        for key in ["pm25", "pm10"]:
            if key in iaqi:
                v = iaqi[key].get("v", 0)
                result[key] = {"aqi": int(v), "level": _aqi_level(int(v))}

        return result
    except Exception as e:
        return {"error": str(e)}


def _aqi_level(aqi: int) -> str:
    if aqi <= 50:
        return "좋음"
    elif aqi <= 100:
        return "보통"
    elif aqi <= 150:
        return "나쁨"
    return "매우나쁨"


# ─── 날씨 (weatheri) ─────────────────────────────────────────

async def fetch_weather(client: httpx.AsyncClient) -> Optional[dict]:
    """weatheri.co.kr에서 서울 날씨 + WAQI API에서 보조 데이터."""
    url = "https://www.weatheri.co.kr/forecast/forecast01.php"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text
        result = {}

        # "N시 현재" + 기온 패턴
        m = re.search(
            r'(\d+)시\s*현재.*?([-\d.]+)\s*℃',
            html, re.DOTALL,
        )
        if m:
            result["current_temp"] = float(m.group(2))
            result["obs_hour"] = int(m.group(1))

        # 모든 기온값 수집 → 최저/최고 추정
        temps = []
        for m in re.finditer(r'([-\d.]+)\s*℃', html):
            v = float(m.group(1))
            if -40 < v < 50:
                temps.append(v)
        if temps:
            result["min_temp"] = min(temps)
            result["max_temp"] = max(temps)

        # 강수확률
        rain_m = re.search(r'강수확률[^\d]*(\d+)', html)
        if rain_m:
            result["precipitation_pct"] = int(rain_m.group(1))

        # 강수량
        precip_m = re.search(r'강수량[^\d]*([\d.]+)\s*mm', html)
        if precip_m:
            result["precipitation_mm"] = float(precip_m.group(1))

        return result if result else {"error": "no data parsed"}
    except Exception as e:
        return {"error": str(e)}


# ─── 메인 오케스트레이터 ─────────────────────────────────────

async def collect(
    fetch_market: bool = True,
    fetch_weather_data: bool = False,
    extra_stocks: Optional[List[str]] = None,
) -> Dict:
    """시장/날씨 데이터를 병렬 수집해 dict로 반환.

    CLI(main)와 dashboard 양쪽에서 공유하는 진입점.
    기존 main() JSON 출력 구조와 완전히 동일한 dict를 반환.
    """
    if extra_stocks is None:
        extra_stocks = []

    output = {
        "timestamp": datetime.now(KST).isoformat(),
        "errors": [],
        "sources": {},
    }  # type: Dict

    async with httpx.AsyncClient(
        headers={"User-Agent": UA},
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as client:

        tasks = {}

        if fetch_market:
            # 미국 지수/매크로/선물/환율 → Stooq 단일쿼트
            us_keys = [
                k for k in YAHOO_SYMBOLS.keys()
                if k not in ("kospi", "kosdaq")
            ]
            tasks["quotes"] = fetch_stooq_quotes(client, us_keys)
            # 국내 지수 → Naver 실시간 폴링
            tasks["kr_indices"] = fetch_naver_korean_indices(client)
            # 국내 지수 분봉(스파크라인용)
            tasks["kr_indices_intraday"] = fetch_naver_index_intraday(client)
            # 섹터
            tasks["sectors"] = fetch_finviz_sectors(client)
            tasks["kr_sectors"] = fetch_naver_sectors(client)

        if extra_stocks:
            tasks["stocks"] = fetch_naver_korean_stocks(
                client, extra_stocks
            )
            tasks["stocks_intraday"] = fetch_naver_korean_stocks_intraday(
                client, extra_stocks
            )

        if fetch_weather_data:
            tasks["air_quality"] = fetch_air_quality(client)
            tasks["weather"] = fetch_weather(client)

        task_names = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                output["errors"].append("{}: {}".format(name, result))
                output["sources"][name] = "error"
                continue

            if isinstance(result, dict) and "_error" in result:
                output["errors"].append(
                    "{}: {}".format(name, result["_error"])
                )
                output["sources"][name] = "error"
                continue

            if isinstance(result, dict) and "error" in result and len(result) == 1:
                output["errors"].append(
                    "{}: {}".format(name, result["error"])
                )
                output["sources"][name] = "error"
                continue

            output["sources"][name] = "ok"

            if name == "quotes":
                grouped = {}  # type: Dict[str, dict]
                for key, val in result.items():
                    group = GROUP_MAP.get(key, "other")
                    if group not in grouped:
                        grouped[group] = {}
                    clean_key = key.replace("_fut", "")
                    grouped[group][clean_key] = val
                for g, v in grouped.items():
                    # kr_indices 태스크가 korean_indices를 채우므로 덮어쓰지 않게
                    if g == "korean_indices":
                        continue
                    output[g] = v
            elif name == "kr_indices":
                output["korean_indices"] = result
            else:
                output[name] = result

    if not output["errors"]:
        del output["errors"]

    return output


async def main():
    args = sys.argv[1:]

    fetch_market = "--weather" not in args
    fetch_weather_data = "--market" not in args
    extra_stocks = []  # type: List[str]

    for i, arg in enumerate(args):
        if arg == "--stocks" and i + 1 < len(args):
            extra_stocks = [
                s.strip() for s in args[i + 1].split(",") if s.strip()
            ]

    output = await collect(
        fetch_market=fetch_market,
        fetch_weather_data=fetch_weather_data,
        extra_stocks=extra_stocks,
    )

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
