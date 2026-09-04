# 구현 상태

## 구현 완료

- 서울 열린데이터광장 공통 페이지네이션·timeout·retry·오류 처리 클라이언트
- 매출, 점포, 유동인구, 상권영역 API 수집 모듈
- 송파구 영역 기준 필터, 계약 키 JOIN, 중복·필수값 검증
- 기존 산식의 5~95 percentile 정규화, 성장 건강도·위험·추천 계산
- RandomForestClassifier와 시간순 검증, 실패 시 성장점수 비노출
- 서울 전체 상권 학습 + 송파구 전용 시간순 검증·점수 정규화 파이프라인
- 장시간 수집 전 Supabase 자격증명 사전검증
- Supabase migration, RLS 공개 읽기 정책, service role 전용 upsert
- React가 Supabase에서 업종·최신 분석·상권·시계열을 조회
- OpenLayers 버블과 선택 Polygon, VWorld WMTS
- 추천·위험 목록 클릭 시 지도 앵커 이동과 선택 Polygon 범위 자동 확대
- 요약 패널의 상세 분석을 페이지 전환 없는 접근성 모달로 제공
- 로딩·빈 데이터·Supabase 미설정·조회 오류·지도 키 없음 상태
- 추천과 고성장·고위험 분리 정렬
- GitHub Actions 수동/분기 자동 동기화와 Vercel SPA 설정

## 데이터

- 원천: 서울 열린데이터광장 Open API
- 서비스: OA-15572 추정매출, OA-15577 점포, OA-15568 길단위인구, OA-15560 상권영역
- 현재 운영 DB에는 전체 기간 송파구 데이터가 적재되어 있음(최신 분기 2026년 2분기)
- 서울 전체 학습 파이프라인 결과는 Supabase 서비스 키 401로 아직 운영 DB에 반영되지 않음
- Supabase 적재: 상권 70건, 분기 통계 12,075건, 분석 결과 12,075건, 모델 실행 13건
- 사용자에게 노출되는 가짜 데이터 없음

## ETL

```powershell
.\.venv\Scripts\python -m scripts.sync_seoul_data
.\.venv\Scripts\python -m scripts.sync_seoul_data --quarter 20254
```

생성 대상은 Supabase의 `commercial_areas`, `industry_categories`, `quarterly_stats`, `area_analysis`, `model_runs` 테이블이다. upsert 기준은 각 테이블의 기본키 또는 고유키다.

## 모델

- 사용 모델: RandomForestClassifier
- 현재 운영 DB 모델 학습 기간: 2022년 1분기~2024년 2분기
- 현재 운영 DB 모델 검증 기간: 2024년 3분기~2025년 2분기
- 신규 파이프라인: 서울 전체 상권으로 학습하고 마지막 4개 분기는 송파구 상권만 검증
- metric: balanced accuracy, F1, ROC AUC
- 검증 결과: 13개 분석 단위 중 1개 통과
- 통과 모델: `CS100004`(balanced accuracy 0.57, F1 0.31, ROC AUC 0.65)
- 최신 분기 20개 상권에만 검증된 성장점수를 노출
- 검증 전 또는 실패 결과의 `growth_score`는 null 처리

## UI

- Supabase 업종 계층 필터
- 최신 분기 버블맵, 선택 상권 요약, 추천 및 위험 랭킹
- 상권 상세 시계열 조회 및 화면 전환 없는 모달 표시
- 매출 추이 차트의 분기·매출액 축, 격자, 데이터 포인트 제공
- 설정 필요·빈 상태·오류 상태

## 지도

- OpenLayers + VWorld WMTS
- VWorld 키는 `VITE_VWORLD_API_KEY`에서만 읽음
- 상권 중심좌표와 Polygon은 `commercial_areas`에서 조회
- 다른 지도 타일 fallback 없음

## 테스트

- `.venv\Scripts\python -m pytest`: 성공, 18 passed
- `pnpm run test:frontend`: 성공, 2 passed
- `pnpm run typecheck`: 성공
- `pnpm run lint`: 성공
- `pnpm run build`: 성공, Vite 500 kB 초과 청크 경고 1건
- 서울 Open API 네 서비스 연결 성공
- 신규 서울 전체 학습 동기화는 데이터 수집·계산 후 Supabase 401로 적재 실패; 이후 자격증명 사전검증을 추가해 재시도 시 즉시 실패 확인
- 최신 분석 조회: 529건, 현재 건강도 528건, 위험점수 526건, 검증된 성장점수 20건

## 미완료

- `.env.local`의 `SUPABASE_SERVICE_ROLE_KEY`가 현재 프로젝트에서 401 Invalid API key로 거부됨. 올바른 프로젝트 service role/secret 키로 교체 후 전체 동기화 재실행 필요
- 과거 `.env.example`에 노출된 VWorld·서울 API 키 재발급 필요
- 모델 검증을 통과하지 못한 12개 분석 단위는 미래 성장점수 비노출
- 프론트 번들 코드 분할 최적화 미적용

## 실행 방법

```powershell
pnpm install
pnpm run dev
```

초기화 또는 재동기화 절차는 `docs/DATA_REQUIRED.md`를 따른다.
