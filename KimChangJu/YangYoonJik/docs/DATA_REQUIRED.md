# 데이터 및 비밀값 준비

운영 런타임은 정적 파일이 아니라 Supabase를 읽는다. 서울 열린데이터광장 API 호출과 분석·적재는 Python 또는 GitHub Actions에서만 실행한다.

## 필수 환경변수

로컬 개발은 저장소 루트의 `.env.local`을 사용한다. 이 파일과 실제 키는 커밋하지 않는다.

```text
VITE_VWORLD_API_KEY=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
SEOUL_OPEN_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
TARGET_DISTRICT=송파구
```

- 브라우저 공개 가능: `VITE_VWORLD_API_KEY`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- 서버 전용 비밀값: `SEOUL_OPEN_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_URL`은 Python 동기화 전용이며 보통 `VITE_SUPABASE_URL`과 같은 프로젝트 URL이다.
- Vercel에는 세 개의 `VITE_*` 값만 등록한다.
- GitHub Actions에는 `SEOUL_OPEN_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`를 Secrets로 등록한다.

## 초기 설정

1. Supabase Free 프로젝트를 만든다.
2. SQL Editor에서 `supabase/migrations/001_initial_schema.sql`을 실행한다.
3. 환경변수를 등록한다.
4. `python -m scripts.sync_seoul_data`를 실행한다.
5. 프론트엔드를 빌드하고 배포한다.

## 공식 API

- 추정매출-상권: `VwsmTrdarSelngQq`
- 점포-상권: `VwsmTrdarStorQq`
- 길단위인구-상권: `VwsmTrdarFlpopQq`
- 상권영역: `TbgisTrdarRelm`

동기화기는 서울 API의 최대 1,000건 페이지 제한, 전체 건수, 빈 응답, API 오류, HTTP 오류, timeout과 retry를 처리한다. 송파구 필터는 상권영역 결과를 기준으로 적용한다.

서울시 공식 Open API는 `http://openapi.seoul.go.kr:8088` 주소를 사용한다. API 키가 URL 경로로 전송되므로 신뢰할 수 있는 로컬 또는 GitHub Actions 환경에서만 실행하고 로그에 요청 URL을 남기지 않는다.

## 현재 blocker

- `.env.local`에 VWorld와 서울 API 키는 이동되어 있다.
- 서울시 API 네 서비스의 로컬 표본 호출은 성공했다.
- Supabase URL과 브라우저용 anon key는 설정되어 기존 데이터를 조회할 수 있다.
- 현재 `SUPABASE_SERVICE_ROLE_KEY`는 Supabase REST에서 401 Invalid API key로 거부된다. 같은 프로젝트의 올바른 service role/secret 키로 교체해야 서울 전체 학습 결과를 upsert할 수 있다.
- 이전 `.env.example`에 실제 키가 들어가 Git 기록에 포함됐을 가능성이 있으므로 VWorld와 서울 API 키를 재발급한 뒤 새 값을 `.env.local`과 배포 환경에 등록해야 한다.
- 가짜 데이터로 대체하지 않는다.
