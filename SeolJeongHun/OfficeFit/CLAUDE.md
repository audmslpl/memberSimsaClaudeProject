# OfficeFit

말로 시작하는 오프라인 전용 업무일지 / 투두리스트 안드로이드 앱. 서버 없이 기기 안(Room DB)에서만 동작한다.

## 스택

- Kotlin, Jetpack Compose (Material 3, 다크 모드 기본)
- MVVM + Repository 패턴
- Room (오프라인 우선, 유일한 데이터 소스) + Coroutines/Flow
- Android `SpeechRecognizer` (온디바이스 우선 음성 인식)
- `java.time` 대신 `java.util.Calendar`만 사용 — core library desugaring 설정을 추가하지 않기 위한 의도적 선택

## 빌드/실행

```bash
export JAVA_HOME="/c/Program Files/Java/jdk-17.0.5"   # AGP 8.5.2는 JDK 17 필요. 시스템 기본 JDK(21/25)로는 실패함
./gradlew compileDebugKotlin testDebugUnitTest         # 컴파일 + 유닛테스트(SmartTextParserTest, 16개)
./gradlew assembleDebug                                # APK 빌드
```

실기기 설치/실행 (adb):
```bash
ADB="/c/Users/seol/AppData/Local/Android/Sdk/platform-tools/adb.exe"
"$ADB" install -r app/build/outputs/apk/debug/app-debug.apk
"$ADB" shell am start -n com.officefit/.MainActivity
```
- Git-bash에서 `adb shell screencap -p /sdcard/x.png`나 `adb pull /sdcard/x.png` 같은 원격 경로는 **`//sdcard/x.png`처럼 슬래시 두 개**로 써야 한다. 안 그러면 MSYS가 경로를 Windows 스타일로 잘못 변환해버린다.
- 에뮬레이터: `Pixel_5_API_27` (부팅 확인됨). 실기기: 삼성 Galaxy Z Fold5(`SM_F946N`) — USB 드라이버 설치 + "파일 전송" 모드 + 디버깅 허용 팝업 승인 순서로 `adb devices`에 잡힌다.

### 환경 특이사항: 한글 리터럴이 컴파일 시 깨지는 문제
이 머신(한글 Windows)에서는 Kotlin 컴파일 데몬이 소스 파일을 플랫폼 기본 인코딩(CP949)으로 읽어, `.kt` 안의 한글 문자열/정규식 리터럴이 깨진다 (`gradle.properties`의 `org.gradle.jvmargs=-Dfile.encoding=UTF-8`만으로는 부족 — 그건 Gradle 데몬에만 적용됨). 반드시 `gradle.properties`에 다음이 있어야 한다:
```
kotlin.daemon.jvmargs=-Dfile.encoding=UTF-8
```
없어졌거나 한글 키워드/정규식 매칭이 이유 없이 안 되면 이걸 먼저 의심할 것 (`./gradlew --stop` 후 clean 빌드로 재확인).

## 아키텍처

```
Compose UI (ui/dashboard/*, ui/voice/*)
    → MainViewModel (StateFlow로 화면 상태 관리, viewModelScope)
        → TodoRepository (DAO 호출을 감싸는 얇은 계층)
            → TodoDao / AppDatabase (Room, SQLite)
```

음성 텍스트 처리는 별도 파이프라인: `VoiceRecognitionManager` → 원문 텍스트 → `SmartTextParser` → 마크다운 미리보기 → 저장 시 다시 파싱해 `TodoItem` 목록으로 변환.

### 데이터 모델 핵심 결정 (`data/local/`)
- `TodoItem.targetTime`: **기간이 아니라 "시작 시각"**. 자정 기준 분(0~1439)으로 저장 (`TimeUtils.toMinutesOfDay/format/parse`). "몇 시부터 시작"이라는 개념을 사용자가 명시적으로 요청했음.
- `TodoItem.dayOfWeek`: nullable, `WeekDay` 상수(월=1~일=7, ISO-8601). null이면 일회성 항목, 값이 있으면 매주 반복(예: 화/목 저녁 스터디).
- `TodoItem.createdAt`: 일회성 항목이 "어느 날짜에 속하는지" 판단하는 기준. `TodoDao.getTodayTodos(dayOfWeek, dayStartMillis, dayEndMillis)` 쿼리가 `dayOfWeek 일치 OR (dayOfWeek IS NULL AND createdAt이 그 날 범위 안)`으로 조회한다. 이름은 "Today"지만 실제로는 임의의 날짜 범위를 받는 범용 쿼리 — `TodoRepository.getTodosForDate(...)`가 같은 쿼리를 재사용한다.
- `DateUtils.DateKey(year, month, dayOfMonth)`: 연/월/일로 특정 하루를 가리키는 값 타입(month는 1~12). 일자별 조회 화면에서 임의의 날짜를 다룰 때 사용.

## 화면 구성 (내비게이션 라이브러리 없이 상태 전환)

`MainActivity`가 `var showDateList by remember { mutableStateOf(false) }` 하나로 두 화면을 토글한다:

1. **`MainDashboardScreen`** — 항상 "오늘"만 보여주는 기본 화면. 마이크 FAB(모닝 보이스 덤프) + "📅 날짜별 보기" 버튼.
2. **`DateTodoListScreen`** — 네이티브 `android.app.DatePickerDialog`로 임의 날짜를 골라 조회.
   - 오늘을 보고 있을 때만 마이크 FAB 노출(음성 덤프는 항상 "지금"을 `createdAt`으로 찍어 오늘에만 저장되므로, 다른 날짜에서는 의미가 없음).
   - "+" FAB은 날짜 무관 항상 노출 — `MainViewModel.addTodoForDate(date, ...)`가 `createdAt`을 그 날짜 자정으로 직접 지정해 등록한다.
   - 오늘이 아닐 때만 "← 오늘로" 텍스트버튼이 보이며, **화면을 나가지 않고 날짜만 오늘로 되돌린다** (화면 이탈과는 분리된 동작).
   - 화면 이탈은 시스템 뒤로가기(`BackHandler`)로 처리하며, 나갈 때 선택 날짜를 오늘로 리셋한다.

두 화면 모두 `TodoListContent`/`TodoRow`(카테고리별 그룹 리스트, 체크박스, 🗑 삭제, 행 탭=수정)와 `EditTodoDialog`/`DeleteTodoConfirmDialog`/`AddTodoDialog`를 그대로 재사용한다 (`ui/dashboard/MainDashboardScreen.kt`에 공용 컴포저블이 있고 `private`이 아님).

### 할 일 수정/삭제
- 행을 탭하면 `EditTodoDialog`(내용/카테고리/시작 시각 수정). 다이얼로그 안의 "삭제"는 바로 지우지 않고 호출부에 위임 → 삭제는 항상 `DeleteTodoConfirmDialog`로 한 번 더 확인한 뒤 실행된다 (실수 방지).

## 모닝 보이스 덤프 (`voice/`, `ui/voice/`, `ui/dashboard/VoiceDumpDialog.kt`)

- **연속 인식은 자동 재시작으로 구현**: `SpeechRecognizer`는 한 번 말이 끊기면 세션이 끝나버리므로, `VoiceRecognitionManager`가 `onResults`/`onError(NO_MATCH, SPEECH_TIMEOUT)`에서 `isDumpActive`가 true인 동안 계속 `startListening()`을 다시 호출하고, 각 세션 텍스트를 하나의 `StringBuilder`(`recognizedText` StateFlow)에 누적한다. `stopDump()`만이 이 루프를 끝낸다.
- **오프라인 우선**: API 31+에서 `createOnDeviceSpeechRecognizer()`, 아니면 `createSpeechRecognizer()` + `EXTRA_PREFER_OFFLINE=true` 힌트로 폴백.
- `SpeechRecognizer`는 반드시 메인 스레드에서 호출해야 해서, 매니저 내부에서 `Handler(Looper.getMainLooper())`로 모든 호출을 감싼다.
- `VoiceDumpDialog`는 `ModalBottomSheet`(Material3 실험적 API, `@OptIn` 처리됨)로, `LISTENING`(실시간 텍스트 + 진폭 연동 파동 애니메이션)과 `PREVIEW`(마크다운 직접 수정) 두 단계.
- **"말하기 예시" 힌트**: 인식 정확도 피드백에 따라 LISTENING 단계에 접이식 힌트 카드(`SpeakingTemplateHint`) 추가. 안내 문구가 실제 파서 로직과 어긋나지 않도록, `SmartTextParser.workKeywordExamples`/`studyKeywordExamples`(실제 매칭 키워드 앞부분을 그대로 노출)를 가져다 쓴다.

## SmartTextParser (`voice/SmartTextParser.kt`)

외부 API 없이 정규식/문자열 처리만으로 "음성 원문 → 카테고리별 마크다운 체크리스트"를 만든다.

1. **절 분리**: 명시적 접속사(`그리고`, `다음으로`, `그 다음에` 등, 긴 표현부터 매칭) + `"-고"/"하고"` 연결어미 정규식(`([가-힣]+?)(?:하고|고)\s+(?=\S)`, 문장 끝의 "-고"는 뒤에 공백+내용이 없으므로 분리 안 됨).
2. **시간 추출**: `(오전|오후|아침|저녁|밤|새벽)?\s*(\d{1,2})시(?:\s*(\d{1,2})분)?에?` → 24시간제 HH:MM. 모디파이어 없이 숫자+"시"만 있어도 매칭되지만, 모디파이어 단어 단독(예: "저녁 약속"의 "저녁")은 매칭되지 않음.
3. **카테고리 분류**: `workKeywords`(회의/검토/SQL/업무/배포/코드/프로젝트/**CM**), `studyKeywords`(스터디/공부/학습/문서/강의/운동) 포함 여부로 WORK/STUDY/GENERAL 분류. `TaskCategory`는 `data/local/Category`와 별개 enum이며 `MainViewModel`의 `toDataCategory()`에서 최종 변환.
4. `toMarkdown`/`parseMarkdown`으로 양방향 변환 가능 — 프리뷰에서 사용자가 마크다운을 직접 수정해도 저장 시 다시 태스크 목록으로 되돌릴 수 있다. 헤더는 이모지(🏢/📚/📌)로 느슨하게 매칭해 사용자가 헤더 문구를 바꿔도 카테고리를 잃지 않음.
5. `SPLIT_MARKER`는 리터럴 U+0001 제어문자 상수 — 일부러 그런 것이며, 다시 `` 이스케이프로 "고쳐" 쓰지 말 것 (이 환경의 파일 쓰기 파이프라인이 이스케이프를 실제 바이트로 바꿔버려서 어차피 같은 결과가 됨).

## 테스트

`app/src/test/java/com/officefit/voice/SmartTextParserTest.kt` — JUnit4, 16개, `./gradlew testDebugUnitTest`로 실행. 한글 관련 코드를 고치고 나서 이 테스트가 원인 불명으로 실패하면 위의 CP949 인코딩 문제부터 의심할 것.

## 아직 안 된 것 / 다음 단계

- 음성 인식 정확도의 실사용 기반 개선 (오탐 케이스 수집)
- 화/목 스터디 같은 주간 반복 일정 전용 UI (현재는 `TodoDao.getWeeklySchedule`로 조회만 가능, 등록 UI 없음)
- 카테고리 필터/완료 항목 통계·회고 뷰
