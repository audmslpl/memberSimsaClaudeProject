# 상권나침반 (🚀 서비스 바로가기 👉 [Commercial Compass 실행하기](https://mymapmk1.vercel.app))

예비 창업자가 송파구 상권의 성장 흐름과 과열 위험을 업종별로 비교하는 공공데이터 기반 웹서비스다.

## 프로젝트 개요

바이브코딩 툴을 활용하여 서비스 기획부터 개발 및 배포까지
전체 프로세스를 실습하기 위해 제작한 MVP 서비스입니다.

## 구조

```text
서울 열린데이터광장 Open API
  → Python 수집·검증·JOIN·점수·모델
  → Supabase PostgreSQL
  → React + OpenLayers + VWorld WMTS
```

별도 API 서버는 운영하지 않는다. 브라우저는 Supabase anon key로 읽기만 수행하며, 데이터 쓰기는 service role key를 가진 Python 동기화 작업만 수행한다.

# Commercial Compass

바이브코딩을 활용하여 제작한 상권 분석 MVP 서비스입니다. 

---

### 개발 환경

- 기획 : ChatGPT
- 바이브코딩 : Codex
- Repository : GitHub
- Database : Supabase
- Deployment : Vercel

## 로컬 실행

```powershell
npm install
npm run dev
```

실제 환경변수는 `.env.example`을 참고해 `.env.local`에 둔다.

```text
VITE_VWORLD_API_KEY=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
SEOUL_OPEN_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
TARGET_DISTRICT=송파구
```

VWorld 키가 없으면 배경지도를 비활성화하고 안내를 표시한다. Supabase 공개 설정이 없으면 앱은 중단되지 않고 `데이터베이스 연결 설정이 필요합니다.`를 표시한다.

## Supabase 초기화

Supabase SQL Editor에서 `supabase/migrations/001_initial_schema.sql`을 한 번 실행한다. RLS는 공개 읽기만 허용한다. service role key는 브라우저와 Vercel 프론트 환경변수에 넣지 않는다.

## 데이터 동기화

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m scripts.sync_seoul_data
```

연결만 확인하려면 `.\.venv\Scripts\python -m scripts.check_seoul_api`를 실행한다. 특정 분기만 호출할 때는 `.\.venv\Scripts\python -m scripts.sync_seoul_data --quarter 20254`를 실행한다. 동기화는 API 수집, 송파구 필터, 계약 키 JOIN, 파생지표, 점수 계산, RandomForest 시간순 검증, Supabase upsert를 한 번에 수행한다.

## 자동 동기화

`.github/workflows/sync-data.yml`은 수동 실행과 분기별 cron을 지원한다. 저장소 Secrets에 `SEOUL_OPEN_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`를 등록한다.

## Vercel

Vite preset, Root Directory `./`, 기본 build command를 사용한다. Vercel에는 `VITE_VWORLD_API_KEY`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`만 등록한다. `vercel.json`이 상세 페이지 새로고침을 SPA 진입점으로 연결한다.

## 검증

```powershell
.\.venv\Scripts\python -m pytest -q
npm run test:frontend
npm run typecheck
npm run lint
npm run build
```

기존 `data/raw`, `data/processed`, `public/data`는 개발·검증 자료로 남길 수 있으나 운영 프론트 런타임 데이터 소스로 사용하지 않는다.
