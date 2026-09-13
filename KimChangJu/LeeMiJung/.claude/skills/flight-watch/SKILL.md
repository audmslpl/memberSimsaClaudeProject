---
name: flight-watch
description: 매진된 항공편(국내선/국제선)을 지속 모니터링하다가 좌석이 나타나는 순간 텔레그램으로 알림. flight-check와 달리 매번 결과를 보내지 않고 "매진→예약 가능" 전환 시에만 알림. /loop 또는 cron으로 반복 실행.
allowed-tools: [Bash, Read, Write, mcp__playwright__browser_navigate, mcp__playwright__browser_wait_for, mcp__playwright__browser_evaluate, mcp__playwright__browser_close, mcp__playwright__browser_snapshot]
---

# 항공편 매진 해제 알림 (flight-watch)

## 용도

매진 또는 원하는 조건에 미달되는 라우트를 등록해두고 반복 조회. **매진 → 예약 가능 전환 순간**에만 텔레그램 알림을 보냅니다. flight-check와 달리 상태 변화가 없으면 조용히 종료. 국내선·국제선 모두 지원.

## 1. 입력 파싱

flight-check와 동일한 규칙:
- **날짜**: "5/10", "5월 10일", "다음 주 토요일" 등 → `YYYYMMDD`
- **방향**: 공항 코드 매핑 (flight-check의 1번 섹션 참고 — 국내 + 일본/중국/동남아/미주/유럽 주요 공항 지원)
- **국내/국제 판별**: 출발+도착 모두 한국 공항이면 `/domestic/`, 아니면 `/international/`

**해제 요청 인식**: 사용자 메시지에 "감시 해제", "중단", "그만" 등이 있으면 상태 파일 삭제하고 알림 없이 종료.

## 2. 상태 파일 관리

```bash
STATE_DIR="$HOME/.cache/flight-watch"
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/${FROM}-${TO}-${YYYYMMDD}.json"
```

**해제 모드**인 경우:
```bash
if [ -f "$STATE_FILE" ]; then
  rm "$STATE_FILE"
  /Users/ghyu/Repositories/Claude/LMJAgent/scripts/tg-send.sh "🛑 감시 해제: ${FROM}→${TO} ${YYYYMMDD}"
fi
exit
```

## 3. 현재 상태 조회

### ⚡ 속도 최적화 원칙

**LLM 추론 시간이 주된 병목**이므로 툴 호출 횟수를 최소화한다.

**3턴 구조** (분리 호출 금지):
- **턴 1 (병렬)**: Bash(상태 파일 읽기) + browser_navigate — 한 응답에 함께
- **턴 2 (1개)**: browser_evaluate — 내부 폴링 + 파싱 + **알림 메시지 후보까지 JS가 생성**
- **턴 3 (1개)**: Bash — 상태 비교 + 알림 결정 + state 저장 + tg-send

`browser_wait_for`는 호출하지 않음 — JS 안에 폴링 로직이 있음.

```
MODE = (FROM과 TO 둘 다 한국 공항) ? "domestic" : "international"
URL = "https://flight.naver.com/flights/${MODE}/${FROM}-${TO}-${YYYYMMDD}"
```

### 턴 2 — JS 폴링 + 파싱 + 메시지 생성

`mcp__playwright__browser_evaluate`에 아래 async 함수 실행 (META 플레이스홀더 치환):

```javascript
async () => {
  const META = {
    fromName: '{FROM_NAME}', fromCode: '{FROM_CODE}',
    toName: '{TO_NAME}', toCode: '{TO_CODE}',
    dateLabel: '{DATE_LABEL}', // 예: '5/10(일)'
    url: '{URL}',
  };
  const airlines = ['대한항공','아시아나항공','아시아나','제주항공','진에어','티웨이항공','티웨이','에어부산','에어서울','에어프레미아','이스타항공','이스타','ANA','JAL','Peach','피치','Zipair','짚에어','Skymark','스카이마크','Jetstar','젯스타','중국남방항공','중국동방항공','중국국제항공','에어차이나','홍콩항공','캐세이','캐세이퍼시픽','VietJet','비엣젯','Vietnam Airlines','베트남항공','Thai','타이항공','Singapore Airlines','싱가포르항공','United','델타','Delta','American','에어프랑스','Lufthansa','루프트한자','KLM'];
  const normalize = (s) => s.replace('항공','').trim();
  const wonFmt = (n) => '₩' + n.toLocaleString('en-US');
  const circled = ['①','②','③','④','⑤','⑥','⑦'];
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const parseCards = () => {
    const cards = [];
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
      let seat = '일반석';
      if (t.includes('비즈니스')) seat = '비즈니스석';
      else if (t.includes('프리미엄')) seat = '프리미엄';
      cards.push({ airline: normalize(a), depart: tms[0], arrive: tms[1], price, seat });
    });
    return cards;
  };

  // 폴링: 카드 5장 이상 또는 차단 감지까지 최대 25초
  let cards = [];
  let blocked = false;
  for (let i = 0; i < 50; i++) {
    cards = parseCards();
    const txt = document.body.innerText || '';
    if (txt.includes('일시적으로 서비스') || txt.includes('로봇')) { blocked = true; break; }
    if (cards.length >= 5) break;
    await sleep(500);
  }

  if (blocked) return { ok: false, reason: 'blocked' };

  const seen = new Set(); const uniq = [];
  for (const c of cards) {
    const k = `${c.airline}-${c.depart}-${c.price}-${c.seat}`;
    if (seen.has(k)) continue;
    seen.add(k); uniq.push(c);
  }
  const economy = uniq.filter(c => c.seat === '일반석').sort((a, b) => a.price - b.price);
  const economyCount = economy.length;
  const economyMin = economy[0]?.price ?? null;

  // 알림 메시지 후보 3종을 미리 생성 (Bash가 상태 비교 후 골라 사용)
  const header = `${META.fromName} → ${META.toName} · ${META.dateLabel}`;
  const top5 = economy.slice(0, 5).map((c, i) =>
    `${circled[i]} ${c.airline}  ${c.depart} → ${c.arrive}  ${wonFmt(c.price)}`
  ).join('\n');

  const msgStart = economyCount > 0
    ? `🔔 flight-watch 시작\n${header}\n\n현재: 예약 가능 ${economyCount}편, 최저 ${wonFmt(economyMin)}\n\n좌석 변동 시 알림드립니다.`
    : `🔔 flight-watch 시작\n${header}\n\n현재: 매진 (0편)\n\n좌석 등장 시 알림드립니다.`;

  const msgSeatAvailable = `🚨 좌석 등장! ${header}\n\n예약 가능 ${economyCount}편 · 최저 ${wonFmt(economyMin || 0)}\n\n💰 상위 ${Math.min(5, economyCount)}편\n${top5}\n\n🔗 지금 바로 예약\n${META.url}`;

  const msgSoldOut = `ℹ️ 매진 전환 ${header}\n다시 좌석 등장 시 알림드립니다.`;

  return {
    ok: true,
    economyCount,
    economyMin,
    msgStart,
    msgSeatAvailable,
    msgSoldOut,
  };
}
```

JS가 3가지 시나리오의 메시지를 **미리 만들어 반환**하므로 Bash는 상태 비교 후 적절한 것을 골라 발송하면 끝.

**ok=false (blocked)**: 상태 파일 업데이트 없이 즉시 종료 (false alert 방지).

## 4. 상태 비교 + 알림 결정

```bash
NOW_ISO=$(date -u '+%Y-%m-%dT%H:%M:%S+09:00')
CUR_COUNT=[evaluate 결과의 economyCount]
CUR_MIN=[evaluate 결과의 economyMin 또는 null]

if [ -f "$STATE_FILE" ]; then
  PREV_COUNT=$(jq -r '.economyCount' "$STATE_FILE")
  PREV_ALERTED=$(jq -r '.alerted' "$STATE_FILE")
  FIRST_CHECK=$(jq -r '.firstCheck' "$STATE_FILE")
else
  PREV_COUNT=""
  PREV_ALERTED="false"
  FIRST_CHECK="$NOW_ISO"
fi
```

### 분기 로직

| 이전 상태 | 현재 상태 | 알림 타입 |
|---|---|---|
| 없음 (첫 등록) | 매진 (0편) | 🔔 모니터링 시작 알림 |
| 없음 (첫 등록) | 예약 가능 (N편) | 🔔 모니터링 시작 + 현재 상황 |
| 매진 (0편) | 매진 (0편) | **조용히** (lastCheck만 업데이트) |
| 매진 (0편) | 예약 가능 (N편) | 🚨 **좌석 등장 알림** (alerted=true) |
| 예약 가능 | 여전히 예약 가능 | **조용히** |
| 예약 가능 | 매진 (0편) | ℹ️ 매진 전환 알림 + alerted 리셋 |

## 5. 알림 메시지

JS가 이미 3종(`msgStart`, `msgSeatAvailable`, `msgSoldOut`)을 만들어 반환함. LLM은 텍스트를 새로 짜지 않음. 상태 비교 결과에 따라 그중 하나를 그대로 발송.

## 6. 상태 파일 저장

```bash
cat > "$STATE_FILE" <<EOF
{
  "from": "${FROM}",
  "to": "${TO}",
  "date": "${YYYYMMDD}",
  "firstCheck": "${FIRST_CHECK}",
  "lastCheck": "${NOW_ISO}",
  "economyCount": ${CUR_COUNT},
  "economyMin": ${CUR_MIN:-null},
  "alerted": ${SHOULD_ALERT}
}
EOF
```

`alerted`는 좌석 등장 알림 직후 true, 매진 복귀 시 false로 리셋.

## 7. 텔레그램 전송

알림이 필요한 경우만:
```bash
/Users/ghyu/Repositories/Claude/LMJAgent/scripts/tg-send.sh "$MSG"
```

상태 변화 없음: `echo "no change"` 정도로 stdout 로그만.

## 8. 사용 흐름 예시

### 등록
텔레그램에 `"5/10 부산 매진 알림 시작"` → 첫 실행 → 🔔 모니터링 시작 메시지
→ `~/.cache/flight-watch/GMP-PUS-20260510.json` 생성

### 반복 조회 (선택)
- 세션 내: `/loop 30m 5/10 부산 매진 감시해줘`
- 영구: cron에 `flight-watch-cron.sh` 등록 (추후 필요 시 작성)

### 해제
텔레그램에 `"5/10 부산 감시 해제"` → state 파일 삭제 + 🛑 확인 알림

## 9. flight-check와의 관계

- **flight-check**: 정보 조회, 항상 결과 전송
- **flight-watch**: 모니터링, 상태 변화 시에만 알림
- 내부 파싱 로직은 동일 (같은 evaluate 함수 재사용)
