# Codex 전달 방법

1. 새 프로젝트 폴더 또는 작업할 저장소 루트에 아래 파일을 복사합니다.
   - `AGENTS.md`
   - `SPEC.md`
   - `CODEX_PROMPT.md`
   - `DATA_REQUIRED.md`
   - `.env.example`
2. 가능하면 서울시 원본 파일을 `data/raw/` 하위에 넣습니다.
3. VWorld 키가 있으면 `.env.local`에 `VITE_VWORLD_API_KEY=...`로 설정합니다.
4. Codex를 저장소 루트에서 실행합니다.
5. `CODEX_PROMPT.md`의 본문을 첫 요청으로 그대로 보냅니다.

Codex는 현재 프로젝트의 `AGENTS.md` 지침을 자동으로 활용할 수 있습니다. 원본 데이터나 VWorld 키가 없어도 코드 scaffold와 빈 상태는 구현하도록 명세되어 있으며, 가짜 사용자-facing 데이터는 만들지 않도록 금지되어 있습니다.
