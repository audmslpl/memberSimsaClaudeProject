---
name: flight-check
description: 항공편 실시간 조회 (국내선 + 국제선). 날짜+방향을 받아 Playwright MCP로 네이버 항공권을 렌더링·파싱한 뒤 최저가 편을 정리해 텔레그램으로 전송. 김포↔제주, 인천↔도쿄, 인천↔후쿠오카 등 지원.
allowed-tools: [Bash, Read, mcp__playwright__browser_navigate, mcp__playwright__browser_wait_for, mcp__playwright__browser_evaluate, mcp__playwright__browser_close, mcp__playwright__browser_snapshot]
---

# 항공편 조회 (국내선 + 국제선)

Playwright MCP로 네이버 항공권을 실제 브라우저처럼 렌더링해서 항공편 리스트와 가격을 파싱합니다. 조회에 **10~15초** 걸리므로 요청 즉시 대기 안내를 보내고, 결과는 준비되는 대로 별도로 전송합니다.

## 0. 조회 시작 안내 (즉시 전송)

**가장 먼저** 요청자에게 대기 안내 전송 + **시작 시각 기록**:

```bash
# 시작 시각 기록 (elapsed 계산용)
START_TS=$(date +%s)
```

```
mcp__plugin_telegram_telegram__reply
  chat_id: [요청자의 chat_id — 인바운드 메시지의 <channel chat_id="..."> 속성에서 추출]
  text: "🔍 [출발]→[도착] · [M/D (요일)] 조회 중...
잠시만요, 약 30~40초 소요됩니다."
```

- chat_id는 인바운드 `<channel source="telegram" chat_id="...">` 태그에서 자동 추출
- 이 메시지는 요청자에게만 전송 (tg-send.sh 전체 발송 아님)
- **시간 안내는 정직하게** — 네이버 서버 응답 + LLM 추론 합쳐 실제 30~40초 소요
- 메시지 id 기억 필요 없음 (결과는 별도 메시지로 보냄)

이후 실제 조회 시작.

## 1. 입력 파싱

**날짜**: "5/4", "5월 4일", "2026-05-04", "다음 주 토요일" 등 → `YYYYMMDD`(8자리)
- 연도 없으면 가장 가까운 미래 날짜 (과거면 내년)

**방향**: 출발 → 도착 공항 코드

한국 (국내선):
- 서울/김포 = **GMP** · 인천 = **ICN** · 제주 = **CJU** · 부산 = **PUS**
- 대구 = TAE · 광주 = KWJ · 청주 = CJJ · 여수 = RSU · 양양 = YNY · 무안 = MWX

일본:
- 도쿄 나리타 = **NRT** · 도쿄 하네다 = **HND** · 오사카 = **KIX**
- 후쿠오카 = **FUK** · 삿포로 = **CTS** · 오키나와 = **OKA** · 나고야 = **NGO**

중국/홍콩:
- 베이징 = **PEK** · 상하이(푸동) = **PVG** · 홍콩 = **HKG** · 타이베이 = **TPE**

동남아:
- 방콕 = **BKK** · 싱가폴 = **SIN** · 쿠알라룸푸르 = **KUL**
- 하노이 = **HAN** · 호치민 = **SGN** · 세부 = **CEB** · 마닐라 = **MNL**

미주/유럽:
- LA = **LAX** · 뉴욕 = **JFK** · 샌프란시스코 = **SFO** · 시애틀 = **SEA**
- 런던 = **LHR** · 파리 = **CDG** · 프랑크푸르트 = **FRA**

**방향 생략 시**: 국내는 서울(GMP) → 목적지. 해외는 인천(ICN) → 목적지.
- "제주" → `GMP → CJU`
- "도쿄" → `ICN → NRT` (나리타 기본)
- "후쿠오카" → `ICN → FUK`

## 2. 국내/국제 판별 + URL 구성

한국 공항 코드 세트:
```
KOREAN = [GMP, ICN, CJU, PUS, TAE, KWJ, CJJ, RSU, YNY, MWX, USN, HIN, KUV]
```

```bash
if [ "$FROM" in KOREAN ] && [ "$TO" in KOREAN ]; then
  MODE="domestic"
else
  MODE="international"
fi
URL="https://flight.naver.com/flights/${MODE}/${FROM}-${TO}-${YYYYMMDD}"
```

## 3. 접속 + 대기

```
mcp__playwright__browser_navigate → url: $URL
mcp__playwright__browser_wait_for → text: "편도"
```

**Smart wait**: 고정 시간 대신 "편도" 텍스트가 등장하면 즉시 통과 (첫 항공편 카드 렌더링 완료 시점).
일반적으로 1~3초에 통과. 데이터 로드가 느리면 최대 30초까지 기다림.

만약 "편도"가 나타나지 않으면 (차단된 경우): 타임아웃 에러 → 섹션 7 폴백으로.

## 4. 파싱

`mcp__playwright__browser_evaluate`로 아래 함수 실행:

```javascript
() => {
  const airlines = [
    // 한국
    '대한항공','아시아나항공','아시아나','제주항공','진에어','티웨이항공','티웨이',
    '에어부산','에어서울','에어프레미아','이스타항공','이스타',
    // 일본
    'ANA','JAL','Peach','피치','Zipair','짚에어','Skymark','스카이마크','Jetstar','젯스타',
    // 아시아
    '중국남방항공','중국동방항공','중국국제항공','에어차이나','홍콩항공','캐세이','캐세이퍼시픽',
    'VietJet','비엣젯','Vietnam Airlines','베트남항공','Thai','타이항공','Singapore Airlines','싱가포르항공',
    // 기타
    'United','델타','Delta','American','에어프랑스','Lufthansa','루프트한자','KLM',
  ];
  const normalize = (s) => s.replace('항공','').trim();

  const cards = [];
  // 넓은 셀렉터 — 국제선 DOM이 국내선과 다름
  document.querySelectorAll('*').forEach((el) => {
    if (el.children.length > 15) return;
    const t = (el.innerText || '').trim();
    if (t.length < 30 || t.length > 700) return;
    const a = airlines.find((x) => t.includes(x));
    if (!a) return;
    const tms = t.match(/\d{1,2}:\d{2}/g);
    if (!tms || tms.length < 2) return;
    const pm = t.match(/편도\s*([\d,]+)원/) || t.match(/([\d,]+)원~?/);
    if (!pm) return;
    const price = parseInt(pm[1].replace(/,/g, ''), 10);
    if (isNaN(price) || price < 10000 || price > 10000000) return;

    // 소요 시간
    const dur = t.match(/(\d{1,2})시간\s*(\d{1,2})분/);
    const duration = dur ? `${parseInt(dur[1])}h ${parseInt(dur[2])}m` : null;
    // 직항/경유
    const transit = t.includes('경유') ? '경유' : '직항';
    // 좌석
    let seat = '일반석';
    if (t.includes('비즈니스')) seat = '비즈니스석';
    else if (t.includes('프리미엄')) seat = '프리미엄';

    cards.push({ airline: normalize(a), depart: tms[0], arrive: tms[1], price, duration, transit, seat });
  });

  // 중복 제거
  const seen = new Set();
  const uniq = [];
  for (const c of cards) {
    const k = `${c.airline}-${c.depart}-${c.price}-${c.seat}`;
    if (seen.has(k)) continue;
    seen.add(k);
    uniq.push(c);
  }

  const economy = uniq.filter(c => c.seat === '일반석').sort((a, b) => a.price - b.price);
  const business = uniq.filter(c => c.seat !== '일반석').sort((a, b) => a.price - b.price);
  const directOnly = economy.filter(c => c.transit === '직항');

  return {
    economy: economy.slice(0, 10),
    economyCount: economy.length,
    economyMin: economy[0]?.price,
    economyMax: economy[economy.length - 1]?.price,
    directCount: directOnly.length,
    business: business.slice(0, 5),
    businessCount: business.length,
    businessMin: business[0]?.price,
  };
}
```

**파싱 결과 비어있으면** (`economyCount === 0`):
- `browser_snapshot`으로 페이지 상태 확인 (차단/에러인지)
- 차단 시 섹션 7 폴백으로

## 5. 브라우저 유지 (닫기 생략)

**`browser_close` 호출하지 않음** — MCP가 세션을 재사용하므로 다음 조회 시 자동으로 새 페이지로 이동. 시간 절약(~0.5초).

단, 스킬이 끝난 후 일정 시간 사용 없으면 MCP가 알아서 브라우저를 정리함.

## 6. 메시지 작성 + 전송

**국내선 template (duration 생략, 직항만 있음)**:
```
✈️ [출발]([FROM]) → [도착]([TO]) · [M/D (요일)]

💰 최저가 TOP 7 (일반석, 편도)
① [항공사]  [HH:MM] → [HH:MM]  ₩[가격]
② ...

📊 전체 일반석 [N]편
• 최저 ₩[min] / 최고 ₩[max]

🛋 비즈니스석 [N]편 · 최저 ₩[price]
(비즈니스 0편이면 줄 생략)

🔗 예약 / 상세
https://flight.naver.com/flights/domestic/{FROM}-{TO}-{YYYYMMDD}

⏱ [ELAPSED]초 소요
```

**국제선 template (duration 추가, 직항/경유 표시)**:
```
✈️ [출발]([FROM]) → [도착]([TO]) · [M/D (요일)] [국제선]

💰 최저가 TOP 7 (일반석, 편도, 직항 우선)
① [항공사]  [HH:MM] → [HH:MM] ([duration]) [직항|경유]  ₩[가격]
② ...

📊 전체 [N]편 · 직항 [N]편
• 최저 ₩[min] / 최고 ₩[max]

🛋 비즈니스/프리미엄 [N]편 · 최저 ₩[price]
(비즈니스 0편이면 줄 생략)

🔗 예약 / 상세
https://flight.naver.com/flights/international/{FROM}-{TO}-{YYYYMMDD}

💡 네이버는 한국 항공사 위주 표시. 현지 항공사(ANA/JAL 등)는 별도 사이트 확인 권장.

⏱ [ELAPSED]초 소요
```

**포맷 가이드**:
- 번호: `①②③④⑤⑥⑦` 원문자
- 항공사명 정규화: "아시아나항공" → "아시아나"
- 가격 쉼표 포맷 (`₩114,900`)
- 공백 정렬 X (비례폰트). 1~2칸으로 구조만
- TOP 5~7편 (8편 이상이면 길어짐)
- 국제선은 **경유 포함 전체 중 TOP 7** 또는 **직항만 TOP 7** (데이터 양에 따라 판단)

Bash로 tg-send (elapsed 시간 계산 포함):
```bash
ELAPSED=$(( $(date +%s) - START_TS ))
MSG="[작성한 본문]

⏱ ${ELAPSED}초 소요"
/Users/ghyu/Repositories/Claude/LMJAgent/scripts/tg-send.sh "$MSG"
```

`START_TS`는 섹션 0에서 기록한 값. elapsed 표시로 사용자에게 투명성 제공.

## 7. 폴백 (차단·타임아웃 시)

파싱 실패 시 browser_close 후 딥링크만 전송:

```
✈️ [출발]→[도착] · [M/D (요일)]

⚠️ 자동 조회 실패 (봇 차단 또는 로딩 지연). 아래 링크로 직접 확인.

🔍 비교 검색
• 네이버: [해당 URL]
• 스카이스캐너: https://www.skyscanner.co.kr/transport/flights/{from}/{to}/{YYMMDD}/
• 카카오 항공: https://flight.kakao.com/
```

## 주의사항

- 왕복 조회는 URL 포맷이 달라 별도 구현 필요. 현재는 편도만 지원.
- 국제선은 **한국 항공사 위주**로 표시됨 (네이버 기본). ANA/JAL/피치 등 현지 항공사는 일부만 등장. 전체 비교 필요하면 스카이스캐너/구글 플라이트 권장 안내.
- 국제선 DOM이 국내선과 다름 → `querySelectorAll('*')` 넓은 스캔 사용 (초기 로딩 조금 느림).
- 경유편은 "경유" 라벨로 구분. 직항 우선 정렬해서 보여주면 사용자 편의.
