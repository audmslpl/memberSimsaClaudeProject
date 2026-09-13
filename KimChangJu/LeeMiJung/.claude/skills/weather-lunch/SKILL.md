---
name: weather-lunch
description: 점심 날씨 브리핑을 텔레그램으로 전송합니다. 오후 날씨 중심.
allowed-tools: [WebFetch, WebSearch, Bash, Read]
---

# 점심 날씨 브리핑 전송

아래 단계를 수행하세요:

## 1. 날씨 정보 수집

Bash로 스크립트를 실행하세요:
```bash
/Users/ghyu/Repositories/Claude/LMJAgent/.venv/bin/python3 /Users/ghyu/Repositories/Claude/LMJAgent/.claude/shared-scripts/market-fetcher.py --weather
```

JSON 결과에서 `weather`(기온, 강수)와 `air_quality`(PM2.5, PM10) 데이터를 사용하세요.
스크립트 실패 시 WebFetch로 https://www.weatheri.co.kr/forecast/forecast01.php 와 https://aqicn.org/city/seoul/kr/ 를 폴백으로 사용하세요.

## 2. 메시지 작성

아래 형식으로 작성하세요:

```
🌤 마스터님 좋은 오후!

📍 동대문구 신설동
🌡 현재 기온: [현재]°C / 최고 [최고]°C
🌂 오후 강수확률: [수치]%
🌧 오후 날씨: [시간대별 요약 - 12시~18시 중심]
💨 미세먼지: [상태] (AQI [수치])
😷 초미세먼지: [상태] (AQI [수치])

[한줄 코멘트 - 오후 외출/우산/자외선 등 조언]
남은 오후도 기분 좋게 보내세요! 🌟
```

## 3. 텔레그램 전송

Bash로 헬퍼 스크립트를 실행하세요 (등록된 모든 수신자에게 자동 전송):

```bash
MSG="[작성한 메시지]"
/Users/ghyu/Repositories/Claude/LMJAgent/scripts/tg-send.sh "$MSG"
```

모든 수신자에 대해 ok:True가 출력되는지 확인하세요.
