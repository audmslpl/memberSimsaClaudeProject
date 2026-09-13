# AGENTS.md — 상권나침반 개발 규칙

이 저장소에서 작업할 때 가장 먼저 `SPEC.md`를 읽고 그대로 따른다. 이 파일은 구현 행동 규칙이고, 제품/데이터 정의의 기준은 `SPEC.md`다.

## 1. 작업 방식

- 사용자의 목표는 **오늘 안에 동작하는 MVP**다. 과도한 추상화보다 작동하는 수직 슬라이스를 우선한다.
- 불필요한 확인 질문을 하지 않는다. 저장소와 데이터에서 확인 가능한 것은 직접 확인하고 진행한다.
- 자격증명이나 원본 데이터 접근처럼 정말로 사용자가 제공해야만 해결되는 경우만 blocker로 남긴다.
- 구현 중 기획을 임의로 확장하거나 핵심 산식을 바꾸지 않는다.
- 관련 없는 리팩터링을 하지 않는다.
- git commit/branch 생성은 요청받지 않는 한 하지 않는다.

## 2. 절대 금지

- 유료 API/서비스 추가 금지
- 백엔드 서버 추가 금지
- 운영 DB 추가 금지
- 생성형 AI API 호출 금지
- 사용자-facing 가짜 매출/점수/상권 데이터 생성 금지
- VWorld 키 하드코딩/커밋 금지
- 사용자-facing 화면에서 검증 전 점수를 `확률`로 표현 금지
- 모델 실패 시 currentHealthScore를 growthScore로 위장 금지
- OSM 등 외부 타일로 무단 fallback 금지
- 한영 혼용 브랜드/로고/페이지 타이틀 금지
- 다크 대시보드, 네온, 글로우, Glassmorphism, 무의미한 그라데이션 금지
- 모든 영역을 동일한 둥근 카드로 감싸는 AI 양산형 레이아웃 금지

## 3. 데이터 행동 규칙

- 먼저 `data/raw/`를 감사한다.
- 파일이 있으면 헤더/기간/행수/키 중복을 검증한 뒤 사용한다.
- 파일이 없으면 공식 서울시 공개 경로에서만 다운로드를 시도한다.
- 공식 다운로드가 막히면 가짜 데이터를 만들지 않고 `DATA_REQUIRED.md`에 blocker를 남긴다.
- 테스트 fixture는 `tests/fixtures/` 안에만 둔다.
- fixture를 `public/data/`로 내보내지 않는다.
- 원본 컬럼 차이는 mapping layer에서 해결하고 내부 schema는 유지한다.

## 4. 분석 규칙

- 점수 정규화는 SPEC의 `동일 quarter + 동일 analysisKey + 송파구` 비교집단, 5/95 winsorize, percentile rank 규칙을 그대로 사용한다.
- currentHealthScore, riskScore, growthScore, recommendationScore 공식을 임의 변경하지 않는다.
- 시간 누수 방지를 위해 random train/test split을 사용하지 않는다.
- 모델 검증 기준을 만족하지 못하면 `growthScore = null`로 유지한다.
- 분석이 불가능한 값을 0으로 대체하여 정상처럼 보이게 하지 않는다.

## 5. 프론트 규칙

- React + TypeScript + Vite + OpenLayers.
- 사용자-facing 텍스트는 한국어 중심.
- UI component library를 설치하지 않는다.
- CSS Modules 또는 CSS variables 기반 CSS를 사용한다.
- 전체는 밝은 라이트 테마.
- 지도 중심 레이아웃을 유지한다.
- 버블맵이 기본이고 클릭한 상권 Polygon을 강조한다.
- VWorld 키가 없어도 build와 앱 렌더는 성공해야 한다.
- key가 없으면 배경지도 안내만 보여주고 다른 외부 타일 서비스를 호출하지 않는다.
- 375px, 768px, 1440px에서 UI overlap을 확인한다.
- 긴 상권명 때문에 레이아웃이 밀리지 않게 한다.

## 6. 품질 기준

작업을 끝내기 전에 가능한 범위에서 반드시 실행한다.

```bash
npm run build
```

프로젝트에 script가 있다면 다음도 실행한다.

```bash
npm run typecheck
npm run lint
```

Python:

```bash
python -m pytest
```

테스트 또는 설치가 환경 문제로 실행되지 않으면 숨기지 말고 `IMPLEMENTATION_STATUS.md`에 명확히 기록한다.

## 7. 문서

- README에 로컬 실행법, 데이터 준비법, VWorld 키 설정법을 쓴다.
- 구현 완료 시 `IMPLEMENTATION_STATUS.md`를 생성한다.
- 사용자가 직접 해야 하는 blocker는 `DATA_REQUIRED.md`에 체크리스트 형태로 남긴다.

## 8. 완료 기준

- 코드를 만들기만 하고 끝내지 않는다.
- 가능한 경우 실제 데이터 파이프라인 → 정적 JSON/GeoJSON → UI까지 끝까지 연결한다.
- 실제 데이터가 없다면 ETL과 UI의 빈 상태, 테스트까지 완성하고 무엇이 부족한지 명확히 남긴다.
- 최종 답변에는 변경한 핵심 파일, 실행한 검증, 남은 blocker만 간결하게 요약한다.
