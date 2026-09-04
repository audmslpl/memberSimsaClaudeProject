# 상권나침반 — Codex 구현 명세

- 문서 버전: 2.0
- 기준일: 2026-09-04
- 목표: 1인 바이브 코딩으로 당일 동작 가능한 MVP
- 개발비 목표: 0원
- 운영비 목표: 0원
- 초기 지역: 서울특별시 송파구
- 핵심 사용자: 예비 창업자
- 사용자 핵심 문제: 앞으로 성장할 상권을 찾고 싶다

---

## 0. 절대 원칙

이 프로젝트는 아래 원칙을 다른 편의보다 우선한다.

1. **개발비·운영비 0원 목표**를 훼손하는 유료 API, 유료 지도, 유료 데이터, 유료 생성형 AI를 추가하지 않는다.
2. **서버와 DB를 운영하지 않는다.** 분석은 오프라인 Python으로 수행하고 웹은 정적 JSON/GeoJSON만 읽는다.
3. **가짜 사업 데이터를 만들지 않는다.** 실제 공공데이터가 없으면 사용자-facing 결과를 임의 숫자로 채우지 않는다.
4. **검증 전 모델 출력은 확률이라고 표현하지 않는다.** `1년 성장 가능성 87점`처럼 점수로 표시한다.
5. **모델 검증 실패 시 1년 성장 예측을 숨긴다.** 현재 성장 건강도와 위험도만 제공한다.
6. **브랜드·타이틀은 한글 단일 표기**를 사용한다. `상권ON`, `Commercial Map` 같은 한영 혼용 브랜드를 만들지 않는다.
7. **전체 UI는 밝은 라이트 테마**로 유지한다. 큰 면적의 검정/짙은 네이비 배경을 사용하지 않는다.
8. **AI 양산형 대시보드처럼 보이지 않게** 설계한다. 과도한 카드, 그라데이션, 글로우, Glassmorphism, 네온, 의미 없는 아이콘/이모지를 금지한다.
9. **애매한 줄바꿈과 UI 간섭을 허용하지 않는다.** 지도·필터·팝업·랭킹·헤더가 서로 겹치지 않아야 한다.
10. 사용자가 보는 숫자는 반드시 실제 원천 데이터 또는 그 데이터에서 계산된 값이어야 한다.

---

## 1. 서비스 정의

### 1.1 한 문장

**예비 창업자가 업종을 선택하면 송파구 상권의 1년 성장 가능성과 과열 위험을 비교하여 상대적으로 건강한 유망 상권을 찾도록 돕는 공공데이터 기반 웹서비스.**

### 1.2 핵심 기능

MVP의 핵심 기능은 정확히 3개다.

1. **1년 성장 가능성 분석**
2. **업종 맞춤 상권 추천**
3. **위험·과열 상권 경고**

### 1.3 MVP에서 하지 않는 것

- 실시간 카드 승인 데이터
- 카드사별 사용액 비교
- 창업 성공/매출 보장
- 로그인, 회원가입, 개인정보 저장
- 결제
- 생성형 AI API 호출
- 서버측 실시간 ML 추론
- 백엔드 API 서버
- 운영 DB
- SMS/카카오 알림
- 유료 지도 API
- 유료 도메인 필수화
- 사용자별 개인화 학습
- 임대료/권리금 분석

---

## 2. 사용자 흐름

```text
홈
→ 상위 업종 선택
→ 하위 업종 선택
→ 송파구 버블맵 갱신
→ 추천 상권 5곳 / 고성장·고위험 상권 확인
→ 버블 클릭
→ 해당 상권 Polygon 강조 + 요약 패널
→ 상세 분석
→ 성장 근거 / 위험 근거 / 최근 추이 확인
```

사용자가 첫 진입 후 **업종 선택 → 추천 상권 확인**까지 3번 이내의 주요 인터랙션으로 도달하게 한다.

---

## 3. 업종 분류

### 3.1 원칙

- 서울시 원본 `SVC_INDUTY_CD`는 수정하지 않는다.
- UI에서만 `상위 카테고리 → 하위 세부 업종`으로 재분류한다.
- 하위 세부 업종은 실제 서울시 코드와 1:1 연결한다.
- 상위 카테고리의 `전체` 분석은 하위 업종 점수 평균이 아니라 **원본 지표를 먼저 집계한 뒤 다시 계산**한다.

### 3.2 초기 카테고리 예시

```text
음식점
 ├─ 전체 음식점
 ├─ 한식
 ├─ 중식
 ├─ 일식
 ├─ 양식
 ├─ 패스트푸드
 ├─ 치킨
 └─ 분식

카페·베이커리
 ├─ 전체 카페·베이커리
 ├─ 커피·음료
 └─ 제과점

편의점·마트
 ├─ 전체 편의점·마트
 ├─ 편의점
 └─ 슈퍼마켓

주점
 └─ 호프·간이주점
```

그 외 상위 카테고리는 실제 원본 업종을 확인하여 아래 분류로 확장한다.

- 식품 판매
- 패션
- 뷰티
- 운동·스포츠
- 여가·오락
- 교육
- 반려동물
- 의료·건강
- 디지털·전자
- 자동차
- 생활·주거
- 숙박·여행
- 전문서비스
- 기타

### 3.3 확정된 외식 계열 코드

```csv
industryCode,industryName,topCategory,subCategory
CS100001,한식음식점,음식점,한식
CS100002,중식음식점,음식점,중식
CS100003,일식음식점,음식점,일식
CS100004,양식음식점,음식점,양식
CS100005,제과점,카페·베이커리,제과점
CS100006,패스트푸드점,음식점,패스트푸드
CS100007,치킨전문점,음식점,치킨
CS100008,분식전문점,음식점,분식
CS100009,호프·간이주점,주점,호프·간이주점
CS100010,커피·음료,카페·베이커리,커피·음료
```

### 3.4 미매핑 업종 처리

- 실제 원본 데이터에서 관측되는 코드가 `category_mapping.csv`에 없으면 임의로 추측해 매핑하지 않는다.
- `validate_raw.py`가 미매핑 코드를 출력한다.
- 공식 서울시 100대 생활밀접업종 자료로 확인 가능한 경우에만 매핑을 추가한다.
- 확인하지 못한 코드는 임시로 `기타`에 포함할 수 있으나 `mappingStatus: "unverified"`를 남기고 추천 랭킹에서 제외한다.

---

## 4. 공공데이터 원천

MVP 원천은 아래 4종으로 고정한다.

| 데이터 | 서비스 ID | 주요 목적 |
|---|---|---|
| 서울시 상권분석서비스(추정매출-상권) | OA-15572 | 매출, 매출건수, 업종 |
| 서울시 상권분석서비스(점포-상권) | OA-15577 | 점포수, 개업, 폐업, 프랜차이즈 |
| 서울시 상권분석서비스(길단위인구-상권) | OA-15568 | 유동인구 |
| 서울시 상권분석서비스(영역-상권) | OA-15560 | 송파구 필터, 중심좌표, Polygon |

분석 대상 기간은 현재 제공 기준에 맞춰 **2021~2025**를 기본으로 한다.

### 공식 참고 주소

- 추정매출: https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do
- 점포: https://data.seoul.go.kr/dataList/OA-15577/S/1/datasetView.do
- 길단위인구: https://data.seoul.go.kr/dataList/OA-15568/S/1/datasetView.do
- 영역-상권: https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do
- 100대 생활밀접업종: https://golmok.seoul.go.kr/images/100_v3.pdf
- VWorld API 샘플: https://github.com/V-world/V-world_API_sample

### 원본 데이터가 없을 때

Codex는 다음 순서로 행동한다.

1. 저장소의 `data/raw/`를 먼저 검사한다.
2. 원본이 없으면 공식 서울시 공개 페이지에서만 다운로드를 시도한다.
3. 로그인/결제/비공개 인증이 필요한 경로는 우회하지 않는다.
4. 다운로드가 불가능하면 ETL·UI 코드와 빈 상태까지 구현하되 **가짜 상권 결과를 생성하지 않는다.**
5. 누락 파일과 사용자가 해야 할 작업을 `DATA_REQUIRED.md`에 정확히 기록한다.
6. 테스트용 fixture는 `tests/fixtures/` 안에서만 사용하고 `public/data/`로 복사하지 않는다.

---

## 5. 원본 컬럼 매핑

### 5.1 추정매출-상권

| 원본 | 내부 | 용도 |
|---|---|---|
| `STDR_YYQU_CD` | `quarter` | 시계열/JOIN |
| `TRDAR_SE_CD` | `areaType` | 상권 분류 |
| `TRDAR_CD` | `areaId` | JOIN KEY |
| `TRDAR_CD_NM` | `areaName` | UI |
| `SVC_INDUTY_CD` | `industryCode` | JOIN KEY |
| `SVC_INDUTY_CD_NM` | `industryName` | UI |
| `THSMON_SELNG_AMT` | `sales` | 핵심 |
| `THSMON_SELNG_CO` | `salesCount` | 핵심/보조 |
| `MDWK_SELNG_AMT` | `weekdaySales` | 확장 |
| `WKEND_SELNG_AMT` | `weekendSales` | 확장 |

실제 CSV 헤더가 공개 API 문서와 다르면 `column_mapping.json` 또는 Python 설정에서만 매핑을 수정하고 분석 로직의 내부 컬럼명은 유지한다.

### 5.2 점포-상권

| 원본 | 내부 |
|---|---|
| `STDR_YYQU_CD` | `quarter` |
| `TRDAR_CD` | `areaId` |
| `SVC_INDUTY_CD` | `industryCode` |
| `SIMILR_INDUTY_STOR_CO` | `storeCount` |
| `STOR_CO` | `normalStoreCount` |
| `FRC_STOR_CO` | `franchiseCount` |
| `OPBIZ_RT` | `openRate` |
| `OPBIZ_STOR_CO` | `openCount` |
| `CLSBIZ_RT` | `closeRate` |
| `CLSBIZ_STOR_CO` | `closeCount` |

### 5.3 길단위인구-상권

| 원본 | 내부 |
|---|---|
| `STDR_YYQU_CD` | `quarter` |
| `TRDAR_CD` | `areaId` |
| `TOT_FLPOP_CO` | `floatingPopulation` |

유동인구에는 업종코드가 없으므로 동일한 `quarter + areaId`의 모든 업종에 공통 외부환경 변수로 결합한다.

### 5.4 영역-상권

| 원본 | 내부 |
|---|---|
| `TRDAR_CD` | `areaId` |
| `TRDAR_CD_NM` | `areaName` |
| `XCNTS_VALUE` | `x` |
| `YDNTS_VALUE` | `y` |
| `SIGNGU_CD` | `districtCode` |
| `SIGNGU_CD_NM` | `districtName` |
| `ADSTRD_CD` | `dongCode` |
| `ADSTRD_CD_NM` | `dongName` |
| `RELM_AR` | `areaSize` |

영역 데이터 좌표계는 원본 메타데이터를 검증한다. `EPSG:5181`로 확인되면 웹 출력용으로 `EPSG:4326`에 변환한다. SHP Polygon이 존재하면 GeoJSON으로 변환한다.

---

## 6. JOIN 및 집계 규칙

### 6.1 JOIN

매출 ↔ 점포:

```text
quarter + areaId + industryCode
```

매출/점포 ↔ 유동인구:

```text
quarter + areaId
```

영역:

```text
areaId
```

송파구 필터:

```text
districtName == "송파구"
```

### 6.2 상위 카테고리 집계

하위 업종의 점수를 평균하지 않는다. `quarter + areaId + topCategory` 단위로 원본을 집계한다.

- `sales`: 하위 업종 합계
- `salesCount`: 하위 업종 합계
- `storeCount`: 하위 업종 합계
- `normalStoreCount`: 합계
- `franchiseCount`: 합계
- `openCount`: 합계
- `closeCount`: 합계
- `floatingPopulation`: 상권/분기 값 1회 사용, 합산 금지
- `openRate`: 하위 업종 `storeCount` 가중평균. 분모가 없으면 결측
- `closeRate`: 하위 업종 `storeCount` 가중평균. 분모가 없으면 결측
- `franchiseRatio`: `sum(franchiseCount) / sum(storeCount)`
- `salesPerStore`: `sum(sales) / sum(storeCount)`

상위 카테고리를 내부적으로 하나의 분석 단위로 저장할 때 `analysisKey` 예시는 다음과 같다.

```text
IND:CS100001
CAT:음식점
CAT:카페·베이커리
```

---

## 7. 결측·이상치 규칙

1. `storeCount <= 0`이면 `salesPerStore`는 결측으로 처리한다.
2. 전년 동기 분모가 `<= 0`이면 해당 YoY는 결측으로 처리한다. 무한대를 만들지 않는다.
3. 성장률을 0으로 강제 대체하지 않는다.
4. 한 점수 계산에 필요한 핵심 구성요소가 하나라도 결측이면 해당 점수는 `null`로 둔다.
5. 원본 중복 키가 발견되면 조용히 합치지 말고 검증 리포트에 기록한다. 공식 구조상 합산이 맞다고 확인된 경우에만 명시적으로 aggregate한다.
6. 숫자형 파싱 실패와 음수 매출/음수 점포수 등 비정상값은 검증 오류로 기록한다.

---

## 8. 파생지표

```text
salesPerStore = sales / storeCount
salesYoY = sales(t) / sales(t-4) - 1
populationYoY = floatingPopulation(t) / floatingPopulation(t-4) - 1
storeYoY = storeCount(t) / storeCount(t-4) - 1
salesPerStoreYoY = salesPerStore(t) / salesPerStore(t-4) - 1
salesCountYoY = salesCount(t) / salesCount(t-4) - 1
franchiseRatio = franchiseCount / storeCount
```

추가 모델 feature:

```text
salesTrend4Q = t-3..t의 log1p(sales)에 대한 단순 선형회귀 slope
salesVolatility4Q = t-3..t 분기 매출의 연속 pct_change 표준편차
```

4개 분기 시계열이 완전하지 않으면 위 feature는 결측으로 둔다.

---

## 9. 점수 정규화 — 반드시 이 방식 사용

이 항목은 Codex가 임의로 Min-Max, Z-score 등으로 바꾸지 않는다.

### 9.1 비교집단

모든 현재 건강도·위험 구성점수는 다음 비교집단 안에서 상대평가한다.

```text
동일 quarter + 동일 analysisKey + 송파구 상권
```

즉 한식은 같은 분기의 송파구 한식 상권끼리, 카페·베이커리 전체는 같은 분기의 송파구 카페·베이커리 집계끼리 비교한다.

### 9.2 Winsorize + Percentile

각 지표마다:

1. 비교집단의 유효 관측치가 **8개 미만이면 점수 계산 불가**로 처리한다.
2. 유효 관측치를 5 percentile / 95 percentile에서 winsorize한다.
3. winsorize된 값을 percentile rank로 변환하여 `0~100` 점수로 만든다.
4. 동점은 평균 rank를 사용한다.
5. 최종 점수는 소수 첫째 자리까지 계산 후 UI에서 정수 반올림한다.

---

## 10. 현재 성장 건강도

성장 정의는 **매출 + 유동인구 + 점포당 매출이 함께 개선되는 것**이다.

구성점수:

- `salesGrowthScore = percentile(salesYoY)`
- `populationGrowthScore = percentile(populationYoY)`
- `salesPerStoreGrowthScore = percentile(salesPerStoreYoY)`

최종:

```text
currentHealthScore
= salesGrowthScore * 0.35
+ populationGrowthScore * 0.25
+ salesPerStoreGrowthScore * 0.40
```

이 값은 **현재 상태 설명용**이다. 모델이 실패했을 때 이를 `1년 성장 가능성`이라고 부르지 않는다.

---

## 11. 위험·과열 점수

### 11.1 구성요소

```text
storeRiskScore = percentile(storeYoY)

salesPerStoreRiskScore
= percentile(-salesPerStoreYoY)

closeRiskScore
= percentile(closeRate)

salesSlowdown
= salesYoY(t-4) - salesYoY(t)

slowdownRiskScore
= percentile(salesSlowdown)
```

`salesSlowdown`이 양수일수록 1년 전보다 성장률이 둔화된 것이다.

### 11.2 최종 위험점수

```text
riskScore
= storeRiskScore * 0.30
+ salesPerStoreRiskScore * 0.35
+ closeRiskScore * 0.25
+ slowdownRiskScore * 0.10
```

### 11.3 위험 상태

| 점수 | 내부 상태 | 사용자 표시 |
|---:|---|---|
| 0~24 | `safe` | 안전 |
| 25~49 | `caution` | 주의 |
| 50~74 | `overheat` | 과열 |
| 75~100 | `high_risk` | 고위험 |

핵심 구성점수가 결측이면 `riskScore = null`이고 사용자는 `분석 데이터 부족`을 본다.

---

## 12. 1년 성장 모델

### 12.1 Target

`t` 대비 정확히 `t+4` 분기에서 아래 3개가 모두 증가하면 성장이다.

```text
sales(t+4) > sales(t)
AND floatingPopulation(t+4) > floatingPopulation(t)
AND salesPerStore(t+4) > salesPerStore(t)
```

```text
futureGrowth = 1  # 모두 충족
futureGrowth = 0  # 그 외
```

### 12.2 모델

기본 모델:

```text
RandomForestClassifier
```

입력 feature 후보:

- `salesYoY`
- `populationYoY`
- `salesPerStoreYoY`
- `storeYoY`
- `closeRate`
- `openRate`
- `franchiseRatio`
- `salesCountYoY`
- `salesTrend4Q`
- `salesVolatility4Q`

### 12.3 학습 단위

- leaf 업종과 상위 집계 카테고리 각각 `analysisKey` 단위로 모델을 시도한다.
- 단, 표본이 부족한 경우 억지로 별도 모델을 만들지 않는다.
- 하나의 `analysisKey`에 대한 학습 labeled row가 80개 미만이면 모델 사용 불가.
- train의 각 class가 20개 미만이면 모델 사용 불가.
- validation의 각 class가 10개 미만이면 검증 불가.

### 12.4 시간 누수 방지

랜덤 셔플 분할 금지.

기본 예시:

```text
학습 current quarter: 2022Q1 ~ 2023Q4
검증 current quarter: 2024Q1 ~ 2024Q4
검증 target: 2025Q1 ~ 2025Q4
```

실제 사용 가능한 분기 범위가 다르면 마지막 4개 current quarter를 검증 구간으로 두고 그 이전 labeled data를 학습에 사용한다.

### 12.5 검증 기준

validation에 두 class가 모두 존재할 때 다음을 계산한다.

- ROC-AUC
- balanced accuracy
- F1

모델 사용 가능 조건:

```text
ROC-AUC >= 0.60
AND balanced_accuracy >= 0.55
```

조건을 충족하지 못하면 해당 `analysisKey`는 모델 점수를 사용자에게 노출하지 않는다.

### 12.6 성장 가능성 점수

검증을 통과한 모델에 한해 최신 행에 대해 `predict_proba(...)[1] * 100`을 계산한다.

사용자-facing 이름은 **`1년 성장 가능성 점수`**이며 `확률`이라고 부르지 않는다.

내부 필드:

```text
growthScore
scoreSource = "model"
```

모델을 사용할 수 없으면:

```text
growthScore = null
scoreSource = "unavailable"
```

현재 건강도를 대신 `growthScore`에 넣지 않는다.

---

## 13. 업종 맞춤 추천

### 13.1 모델이 사용 가능한 경우

```text
safetyScore = 100 - riskScore

recommendationScore
= growthScore * 0.70
+ safetyScore * 0.30
```

`riskScore >= 75`인 상권은 일반 추천 5곳에서 제외하고 `고성장·고위험` 목록으로 분리한다.

### 13.2 모델이 사용 불가능한 경우

미래 예측처럼 보이게 하지 않는다.

```text
fallbackRecommendationScore
= currentHealthScore * 0.70
+ safetyScore * 0.30
```

사용자-facing 라벨:

```text
현재 성장 건강도 기반 추천
```

`1년 성장 가능성` 영역은 `분석 데이터가 충분하지 않습니다` 상태를 표시한다.

### 13.3 정렬

- 동일 선택 업종/카테고리 안에서만 정렬한다.
- 점수 `null`인 상권은 추천 랭킹에서 제외한다.
- 동점은 `riskScore` 낮은 순 → `salesPerStoreYoY` 높은 순으로 정렬한다.

---

## 14. 규칙 기반 설명문

생성형 AI를 사용하지 않는다.

예:

```text
IF salesYoY > 0
AND populationYoY > 0
AND salesPerStoreYoY > 0
→ "매출과 유동인구가 함께 증가하고 있고 점포당 매출도 개선되고 있습니다."

IF salesYoY > 0
AND storeYoY > salesYoY
AND salesPerStoreYoY < 0
→ "전체 매출은 증가하지만 점포 증가 속도가 더 빨라 경쟁 과열 신호가 나타납니다."

IF closeRate가 비교집단 상위 25%
→ "동일 업종의 다른 송파구 상권보다 폐업 수준이 높은 편입니다."
```

설명문은 실제 조건과 일치할 때만 노출한다. 데이터가 없으면 추측하지 않는다.

---

## 15. 지도

### 15.1 기술

- React
- TypeScript
- Vite
- OpenLayers
- VWorld WMTS 배경지도
- 서울시 상권 GeoJSON
- 정적 분석 JSON

### 15.2 VWorld 키

환경변수:

```text
VITE_VWORLD_API_KEY=
```

- 키를 저장소에 커밋하지 않는다.
- `.env.example`만 커밋한다.
- 키가 없어도 `npm run build`가 성공해야 한다.
- 키가 없으면 OpenLayers 벡터 레이어/상권 데이터는 렌더링하고 배경지도 영역에는 `지도 인증키를 설정하면 배경지도가 표시됩니다`라는 비차단 안내를 표시한다.
- OSM 등 다른 외부 타일로 몰래 fallback하지 않는다.

### 15.3 버블맵

- 기본 시각화는 버블맵.
- 위치: 상권 중심 좌표.
- 크기: `growthScore`가 있으면 growthScore, 없으면 `currentHealthScore`를 사용하되 범례/라벨을 현재 건강도 기반으로 바꾼다.
- 반경(px): `10 + 14 * score / 100`, 최소 10, 최대 24.
- 버블 내부에는 점수만 표시.
- 긴 상권명은 버블 안에 넣지 않는다.
- 클릭 시 Polygon 강조.

상태색은 `riskScore`를 표현한다.

- 안전: green
- 주의: amber
- 과열: orange
- 고위험: red
- 데이터 부족: neutral gray

색만으로 정보를 전달하지 말고 범례/텍스트 상태를 함께 제공한다.

### 15.4 UI 충돌 방지

- Header, filter bar, OpenLayers controls, tooltip, ranking panel의 z-index 계층을 토큰으로 정의한다.
- popup은 viewport 경계에서 자동 위치 보정한다.
- 버블 간 겹침이 심하면 줌 레벨에 따라 반경을 줄인다.
- 선택된 버블은 맨 위에서 렌더링한다.
- PC: 지도 + 오른쪽 분석/랭킹 패널.
- 모바일: 지도 + bottom sheet.
- 터치 대상 최소 44px.

---

## 16. 디자인 시스템

### 16.1 방향

**밝고 전문적이며, 데이터가 많아도 답답하지 않은 국내 상용 데이터 서비스.**

공공기관 사이트처럼 딱딱하지 않고, 흔한 AI 생성 대시보드처럼 과장되지 않아야 한다.

### 16.2 금지

- 다크 테마
- 큰 검정/짙은 네이비 면적
- 무의미한 그라데이션
- 글로우/네온
- Glassmorphism 남발
- 모든 섹션을 동일한 둥근 카드에 넣기
- 카드 안에 카드 중첩
- 불필요한 이모지
- 장식 목적 3D
- 의미 없는 숫자 KPI 대량 나열
- 과도하게 큰 Hero 영역
- 영문을 장식처럼 섞은 타이틀

### 16.3 브랜드/언어

- 임시 브랜드명: `상권나침반`
- 로고: 간단한 심볼 + `상권나침반`
- 로고에 영문 부제 금지
- 브랜드와 페이지 타이틀에서 한글/영문 혼용 금지
- 사용자-facing UI 라벨은 한국어 우선
- `TOP 5` 대신 `추천 상권 5곳`
- `Overview` 대신 `요약`
- 개발 코드, 파일명, 변수명은 영어 사용 가능

### 16.4 줄바꿈

- 브랜드명: `white-space: nowrap`
- 짧은 제목/CTA는 한 줄 우선
- 제목이 의미 중간에서 끊기지 않도록 container와 typography 조정
- 긴 상권명은 ellipsis + 접근 가능한 전체 텍스트 제공

### 16.5 기본 토큰

```text
background      #F7F8FA
surface         #FFFFFF
text-primary    #20242A
text-secondary  #667085
border          #E5E7EB
primary         #2563EB
safe            #16803C
caution         #A16207
overheat        #C2410C
high-risk       #B42318
neutral         #667085
```

색은 의미 전달에만 사용하고 대면적 장식 배경으로 사용하지 않는다.

### 16.6 CSS/컴포넌트

- UI component framework를 추가하지 않는다.
- CSS Modules 또는 명확히 구조화된 CSS + CSS variables를 사용한다.
- 디자인 토큰을 한 곳에서 관리한다.
- 기본 radius는 작거나 중간 수준으로 절제한다.
- shadow는 필요한 overlay/popup에만 얕게 사용한다.

---

## 17. 화면 요구사항

### 17.1 홈 / 미래지도

필수 순서:

1. 상단 브랜드/내비게이션
2. `1년 뒤 성장할 상권을 찾아보세요`
3. 상위 업종 선택
4. 하위 업종 선택
5. 송파구 버블맵
6. 추천 상권 5곳
7. 고성장·고위험 목록
8. 데이터 출처/주의 문구

### 17.2 상권 요약 패널

버블 클릭 시:

- 상권명
- 선택 업종
- `1년 성장 가능성 점수` 또는 `분석 데이터 부족`
- 현재 성장 건강도
- 과열 위험 점수/상태
- 매출 YoY
- 유동인구 YoY
- 점포당 매출 YoY
- `상세 분석` CTA

### 17.3 상세 페이지

- 상권명 / 업종
- 성장 가능성 점수
- 현재 성장 건강도
- 위험점수
- 추천 상태
- 매출 YoY
- 유동인구 YoY
- 점포당 매출 YoY
- 점포 증가율
- 폐업률
- 최근 분기 추이
- 규칙 기반 설명문
- 데이터 기준 분기
- `공공 추정 데이터이며 창업 성공을 보장하지 않습니다` 안내

최근 분기 추이는 라이브러리를 추가하지 않아도 되는 단순 SVG line chart로 구현해도 된다.

---

## 18. 정적 데이터 계약

### 18.1 `public/data/areas.geojson`

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "areaId": "...",
        "areaName": "...",
        "dongName": "..."
      },
      "geometry": {}
    }
  ]
}
```

### 18.2 `public/data/categories.json`

상위/하위 카테고리와 `analysisKey`를 제공한다.

```json
{
  "categories": [
    {
      "name": "음식점",
      "analysisKey": "CAT:음식점",
      "children": [
        {"name": "한식", "analysisKey": "IND:CS100001", "industryCode": "CS100001"}
      ]
    }
  ]
}
```

### 18.3 `public/data/commercial.json`

```json
{
  "quarter": "20254",
  "generatedAt": "ISO-8601",
  "records": [
    {
      "areaId": "...",
      "areaName": "...",
      "dongName": "...",
      "analysisKey": "IND:CS100001",
      "topCategory": "음식점",
      "subCategory": "한식",
      "industryCode": "CS100001",
      "lng": 127.0,
      "lat": 37.5,
      "growthScore": 87,
      "scoreSource": "model",
      "currentHealthScore": 82,
      "riskScore": 21,
      "riskStatus": "safe",
      "recommendationScore": 85,
      "recommendationMode": "future",
      "salesYoY": 0.12,
      "populationYoY": 0.08,
      "salesPerStoreYoY": 0.06,
      "storeYoY": 0.03,
      "closeRate": 0.04,
      "sales": 123456789,
      "storeCount": 42,
      "modelMetrics": {
        "rocAuc": 0.68,
        "balancedAccuracy": 0.61,
        "f1": 0.63
      }
    }
  ]
}
```

모델 미사용 행:

```json
{
  "growthScore": null,
  "scoreSource": "unavailable",
  "currentHealthScore": 76,
  "recommendationMode": "current_health"
}
```

### 18.4 사용자-facing 데이터에 fixture 금지

`public/data/*.json`은 실제 공공데이터 ETL 결과 또는 빈 구조만 허용한다. 테스트용 임의 숫자는 금지한다.

---

## 19. 프로젝트 구조

```text
commercial-compass/
├─ AGENTS.md
├─ SPEC.md
├─ CODEX_PROMPT.md
├─ DATA_REQUIRED.md
├─ .env.example
├─ data/
│  ├─ raw/
│  │  ├─ sales/
│  │  ├─ stores/
│  │  ├─ population/
│  │  └─ area/
│  ├─ config/
│  │  ├─ category_mapping.csv
│  │  └─ column_mapping.json
│  └─ processed/
├─ analysis/
│  ├─ collect_population.py
│  ├─ validate_raw.py
│  ├─ build_dataset.py
│  ├─ train_growth_model.py
│  └─ export_web_data.py
├─ tests/
│  ├─ fixtures/
│  └─ test_analysis.py
├─ public/
│  └─ data/
│     ├─ areas.geojson
│     ├─ categories.json
│     └─ commercial.json
├─ src/
│  ├─ pages/
│  ├─ components/
│  │  ├─ map/
│  │  ├─ ranking/
│  │  ├─ category/
│  │  └─ analysis/
│  ├─ lib/
│  ├─ styles/
│  ├─ types/
│  └─ App.tsx
├─ .env.example
├─ package.json
└─ README.md
```

---

## 20. 기술/실행 원칙

### 20.1 런타임

- Node.js: 20 이상 LTS 계열
- Python: 3.11 이상
- prerelease 패키지 사용 금지
- 신규 프로젝트라면 실행 환경에서 사용 가능한 안정 버전을 사용한다.

### 20.2 프론트

- React + TypeScript + Vite
- OpenLayers
- React Router 사용 가능
- UI component library는 추가하지 않는다.
- CSS Modules 또는 CSS variables 기반 CSS
- 서버 fetch는 `public/data/*.json` 같은 정적 파일만 대상

### 20.3 Python

필요 패키지 예시:

- pandas
- numpy
- geopandas
- shapely
- pyproj
- scikit-learn
- joblib
- pytest

인터넷 연결이 없으면 설치 실패를 숨기지 말고 필요한 패키지를 문서화한다.

---

## 21. QA 및 테스트

최소 자동 검증:

### Python

- 파생지표 분모 0 처리
- t-4 YoY 정렬
- 상위 카테고리 집계가 점수 평균이 아님을 테스트
- percentile/winsorization 테스트
- 위험점수 가중치 테스트
- Target 생성 테스트
- 시간순 train/validation 분리 테스트
- 모델 실패 fallback 테스트

### Frontend

- TypeScript typecheck
- production build
- 데이터 파일이 비어도 crash하지 않음
- VWorld 키가 없어도 build/페이지 렌더 성공
- 선택 업종 변경 시 표시 데이터 변경
- growthScore null 시 1년 성장 숫자 표시 금지
- riskScore null 시 허위 안전 상태 표시 금지

### 접근성/레이아웃

- keyboard focus 가능
- color 외 텍스트 상태 제공
- viewport 375px / 768px / 1440px에서 주요 UI overlap 없음
- 브랜드/주요 버튼 의미 중간 줄바꿈 없음

---

## 22. 완료 조건

실제 원천 데이터가 존재하는 경우 아래 흐름이 실제 데이터로 동작하면 MVP 완료다.

```text
서비스 접속
→ 음식점
→ 한식
→ 송파구 버블맵 변경
→ 추천 상권 5곳 표시
→ 버블 클릭
→ 상권 Polygon 강조
→ 성장 가능성 점수 또는 분석 불가 상태 확인
→ 과열 위험 확인
→ 매출/유동인구/점포당 매출 근거 확인
→ 상세 페이지 이동
```

추가 완료 조건:

- `npm run build` 성공
- Python test 성공
- 사용자-facing mock 데이터 없음
- 서울시 API를 웹 runtime에서 호출하지 않음
- VWorld 키 저장소 커밋 없음
- 서버/DB 없음
- 유료 서비스 없음
- 한영 혼용 브랜드 없음
- 다크 UI 없음
- UI 겹침 없음
- 데이터 부족/모델 실패 상태가 정직하게 표현됨

원본 공공데이터가 없는 경우에는 다음까지 완료하면 된다.

- 전체 프로젝트 scaffold
- ETL/검증/모델 코드
- 실제 데이터 계약
- UI 및 지도 빈 상태
- 테스트 fixture 기반 자동 테스트
- `DATA_REQUIRED.md`에 정확한 누락 데이터 안내
- public 사용자-facing 파일에 fixture를 넣지 않음

---

## 23. 최종 구현 우선순위

1. 프로젝트/실행 환경 구성
2. 원본 데이터 감사(audit)
3. `validate_raw.py`
4. 카테고리/컬럼 매핑
5. JOIN/파생지표
6. 현재 건강도/위험점수
7. 1년 Target/모델/검증
8. 정적 JSON/GeoJSON export
9. 밝은 지도 중심 UI
10. 버블맵/랭킹
11. 상세 페이지
12. 빈 상태/오류 상태
13. 테스트/빌드
14. README 및 `IMPLEMENTATION_STATUS.md`

---

## 24. 구현 완료 후 Codex가 남길 보고서

루트에 `IMPLEMENTATION_STATUS.md`를 생성한다.

반드시 포함:

- 구현 완료 기능
- 실제 사용한 데이터 파일
- 원본 데이터가 없어서 막힌 항목
- 모델별 sample 수와 validation metric
- 모델이 숨겨진 업종/카테고리와 이유
- 실행 명령
- 테스트/빌드 결과
- VWorld 키 설정 방법
- 향후 수동으로 해야 할 작업

