# OfficeFit 프로세스 & API 상세 문서

> OfficeFit은 서버가 없는 **오프라인 전용** 안드로이드 앱이라 REST API가 존재하지 않는다.
> 이 문서에서 말하는 "API"는 계층별(Compose UI → ViewModel → Repository → DAO/Room, 그리고 음성 인식 파이프라인)
> **클래스/함수 단위의 내부 API**를 뜻한다. 먼저 전체 프로세스 흐름을 소개하고, 그 다음 각 파일의
> 클래스·함수를 하나씩 상세히 설명한다.

---

## 1. 앱 개요

- **말로 시작하는 오프라인 업무일지 / 투두리스트**. 서버 없이 기기 안(Room DB)에서만 동작한다.
- 스택: Kotlin, Jetpack Compose(Material3, 다크 모드 기본), MVVM + Repository 패턴,
  Room(오프라인 우선), Coroutines/Flow, Android `SpeechRecognizer`(온디바이스 우선 음성 인식).
- `java.time` 대신 `java.util.Calendar`만 사용(= core library desugaring 설정을 추가하지 않기 위한 의도적 선택).

### 계층 구조

```
Compose UI (ui/dashboard/*, ui/voice/*)
    → MainViewModel (StateFlow로 화면 상태 관리, viewModelScope)
        → TodoRepository (DAO 호출을 감싸는 얇은 계층)
            → TodoDao / AppDatabase (Room, SQLite)

음성 텍스트 처리 파이프라인 (별도 트랙):
VoiceRecognitionManager → 원문 텍스트 → SmartTextParser → 마크다운 미리보기
    → (사용자 편집) → 저장 시 재파싱 → TodoItem 목록 → Repository.insertAll
```

### 화면 구성

내비게이션 라이브러리 없이 `MainActivity`가 `Boolean` 하나(`showDateList`)로 두 화면을 토글한다.

1. **`MainDashboardScreen`** — 항상 "오늘"만 보여주는 기본 화면.
2. **`DateTodoListScreen`** — `DatePickerDialog`로 임의 날짜를 골라 조회하는 화면.

---

## 2. 전체 프로세스 흐름

### 2-1. 앱 시작 프로세스

1. 시스템이 `OfficeFitApplication`을 생성 → `database`(`AppDatabase.getInstance`)와
   `repository`(`TodoRepository(database.todoDao())`)를 `by lazy`로 준비(최초 접근 시점에 생성).
2. 런처 Activity `MainActivity.onCreate()` 호출 → `application as OfficeFitApplication`으로
   전역 DB/Repository를 꺼냄 → `setContent { OfficeFitTheme { ... } }`로 Compose 화면 시작.
3. `viewModel<MainViewModel>(factory = MainViewModelFactory(app.repository, app))`로
   `MainViewModel` 인스턴스 획득(화면 회전 등 재구성에도 유지됨).
4. `showDateList = false`이므로 최초 화면은 `MainDashboardScreen`.

### 2-2. 오늘의 할 일 조회 프로세스 (대시보드)

1. `MainDashboardScreen`이 `viewModel.todayTodos`를 `collectAsState()`로 구독.
2. `MainViewModel.todayTodos`는 초기화 시 `DateUtils.todayRangeMillis()`(오늘 00:00~23:59:59.999 millis 범위)와
   `DateUtils.currentWeekDay()`(오늘 요일, 월=1~일=7)를 계산해
   `repository.getTodayTodos(dayOfWeek, dayStart, dayEnd)` → `TodoDao.getTodayTodos(...)` Flow를 구독한다.
3. SQL 조건: `dayOfWeek = :오늘요일 OR (dayOfWeek IS NULL AND createdAt BETWEEN 오늘범위)`
   → **매주 반복되는 항목**(요일 일치) + **오늘 새로 만든 일회성 항목**을 함께 가져온다.
4. `TodoListContent`가 결과를 `Category`(WORK/STUDY/ETC)별로 그룹핑해 `LazyColumn`으로 렌더링.
5. Room `Flow`는 테이블 변경을 자동 감지하므로, 이후 추가/수정/삭제/완료토글이 일어나면
   이 화면은 별도 새로고침 없이 자동으로 다시 그려진다.

### 2-3. 할 일 수동 등록 프로세스 ("+" 버튼)

- **대시보드에는 "+" 버튼이 없다** (오늘 할 일은 음성 덤프로만 추가하도록 설계됨).
- `DateTodoListScreen`의 "+" FAB → `AddTodoDialog` 오픈 → 제목/카테고리/시작 시각(HH:MM) 입력 →
  "등록" → `onSave(title, category, hour, minute)` → `viewModel.addTodoForDate(selectedDate, title, category, hour, minute)` 호출.
- `addTodoForDate`는 `createdAt`을 **선택된 날짜의 자정 millis**로 직접 지정해 `TodoItem`을 insert한다.
  (음성 덤프의 `saveJournalEntry`는 항상 "지금"을 `createdAt`으로 찍어 오늘에만 저장되는 것과 대비됨.)

### 2-4. 할 일 수정 프로세스

1. `TodoRow`(할 일 행) 탭 → `editingTodo = todo` → `EditTodoDialog` 오픈.
2. 제목/카테고리/시작 시각 수정 후 "저장" → `TimeUtils.parse(timeText)`로 문자열을 분 단위로 변환
   (파싱 실패 시 기존 값 유지, 앱이 죽지 않도록 `runCatching`으로 방어) →
   `onSave(todo.copy(...))` → `viewModel.updateTodo(updated)` → `repository.update` → `TodoDao.update`(Room `@Update`).
3. 다이얼로그 안의 "삭제" 버튼은 **바로 삭제하지 않고** `onDelete(todo)`로 호출부에 위임한다.

### 2-5. 할 일 삭제 프로세스

1. 행의 🗑 아이콘 탭 **또는** `EditTodoDialog`의 "삭제" → `pendingDeleteTodo = todo`.
2. `DeleteTodoConfirmDialog`("정말 삭제할까요?")로 한 번 더 확인.
3. "삭제" 확정 → `viewModel.deleteTodo(todo)` → `repository.delete` → `TodoDao.delete`(Room `@Delete`).
   → 실수로 지우는 것을 막기 위한 2단계 확인 구조.

### 2-6. 완료 체크 토글 프로세스

- 행의 `Checkbox` 클릭 → `onToggle(todo.id, checked)` → `viewModel.toggleCompletion(id, isCompleted)` →
  `repository.toggleCompletion` → `TodoDao.updateCompletion`(`UPDATE ... SET isCompleted = :isCompleted WHERE id = :id`).
- 전체 `TodoItem`을 다시 쓰지 않고 `isCompleted` 컬럼만 갱신하는 전용 쿼리.

### 2-7. 날짜별 조회 프로세스

1. 대시보드 상단 "📅 날짜별 보기" → `onOpenDateList()` → `MainActivity`의 `showDateList = true` → `DateTodoListScreen` 표시.
2. `viewModel.selectedDate`(기본값 오늘) 구독 → `viewModel.selectedDateTodos`는
   `flatMapLatest`로 선택 날짜가 바뀔 때마다 `repository.getTodosForDate(...)`(내부적으로 `getTodayTodos`와 동일 쿼리 재사용)로 새 Flow를 구독한다.
   (`flatMapLatest`이므로 이전 날짜 구독은 자동 취소됨.)
3. "📅 날짜 선택" → 네이티브 `DatePickerDialog` → 날짜 선택 시 `viewModel.selectDate(date)`.
4. 오늘이 아닐 때만 "← 오늘로" 버튼이 보이며, **화면 이탈 없이 날짜만 오늘로 되돌린다**.
5. 화면 이탈은 시스템 뒤로가기(`BackHandler`)가 전담하며, 나갈 때 선택 날짜를 오늘로 리셋한다
   (다음에 다시 들어오면 항상 오늘부터 시작).
6. 마이크 FAB은 **오늘을 보고 있을 때만** 노출(음성 덤프는 항상 "지금"을 `createdAt`으로 찍어 오늘에만 저장되므로 다른 날짜에서는 의미가 없음). "+" FAB은 날짜 무관 항상 노출.

### 2-8. 모닝 보이스 덤프 프로세스 (핵심 기능)

```
[마이크 FAB]
   │ 권한 있음? ──No──▶ MicrophonePermissionState.requestPermission() ──허용──▶ openVoiceDump()
   │ Yes
   ▼
MainViewModel.openVoiceDump()
   - dumpStage = LISTENING, previewMarkdown = "", showVoiceDumpDialog = true
   - voiceManager.startDump()
   ▼
VoiceRecognitionManager.startDump()
   - 권한/기기 지원 재확인 → textBuilder 초기화 → startNewSession()
   - SpeechRecognizer 세션 시작 (API31+ 온디바이스 인식기 우선, 아니면 PREFER_OFFLINE 힌트)
   ▼
[사용자가 "오전 10시에 회의 하고, 코드 검토하고, ..." 라고 연속으로 말함]
   - onRmsChanged → amplitude 갱신(파동 애니메이션 구동)
   - onPartialResults → partialText 갱신(실시간 프리뷰)
   - 말이 잠깐 끊기면 onResults 또는 onError(NO_MATCH/SPEECH_TIMEOUT) 발생
     → appendRecognizedSegment(text)로 recognizedText에 이어붙이고
     → isDumpActive == true면 restartSession()으로 세션 자동 재시작 (연속 인식처럼 보이게 함)
   ▼
["완료 및 정리하기" 버튼 탭]
MainViewModel.finishListeningAndPreview()
   - voiceManager.stopDump() (재시작 루프 종료, recognizer 해제)
   - SmartTextParser.parse(recognizedText) → previewMarkdown
   - dumpStage = PREVIEW
   ▼
[PREVIEW 단계: OutlinedTextField로 마크다운 직접 수정 가능]
   - updatePreviewMarkdown(text)로 편집 내용 반영
   ▼
["일지 저장" 버튼 탭]
MainViewModel.saveJournalEntry()
   - SmartTextParser.parseMarkdown(previewMarkdown) → List<ParsedTask>
   - 각 task를 TodoItem(dayOfWeek=null, createdAt=지금)으로 변환해 repository.insertAll(...)
   - showVoiceDumpDialog = false, previewMarkdown = ""
   ▼
[대시보드 목록에 즉시 반영] (Room Flow 자동 갱신)
```

- 취소 경로: LISTENING/PREVIEW 어느 단계에서든 "취소" 또는 바깥 터치/뒤로가기 →
  `cancelVoiceDump()` → `voiceManager.stopDump()` + `showVoiceDumpDialog = false`.
- `VoiceDumpDialog`는 `showVoiceDumpDialog`가 `false`가 된 뒤에도 `ModalBottomSheet`가 닫히는
  애니메이션이 끝날 때까지 `isDumpDialogMounted`로 컴포지션에 남아 있다가, `sheetState.hide()` 완료 후
  `onFullyDismissed()`로 완전히 제거된다.

#### 2-8-1. SmartTextParser 내부 처리 순서 (텍스트 → 마크다운)

1. **절 분리** (`splitIntoClauses`): 명시적 접속사(`그리고`, `다음으로`, `그 다음에` 등, 긴 표현부터 매칭)로 치환 →
   `"~하고"/"-고"` 연결어미 정규식(문장 끝이 아니라 뒤에 내용이 더 있을 때만 분리)으로 추가 분리 →
   내부 제어문자(U+0001) 구분자로 split.
2. **시간 추출** (`clauseToTask` → `formatTime`): `(오전|오후|아침|저녁|밤|새벽)? (\d{1,2})시(\s*(\d{1,2})분)?에?` 매칭 →
   24시간제 `HH:MM` 문자열로 변환(오후/저녁/밤+1~11시→+12, 오전/아침/새벽+12시→0시).
3. **카테고리 분류** (`classify`): `workKeywords`(회의/검토/SQL/업무/배포/코드/프로젝트/CM) /
   `studyKeywords`(스터디/공부/학습/문서/강의/운동) 포함 여부로 WORK/STUDY/GENERAL 분류
   (`SmartTextParser.TaskCategory` — `data/local/Category`와는 별개 enum).
4. **마크다운 렌더링** (`toMarkdown`): 카테고리별로 그룹핑해 `### 🏢 사내 업무` 등 헤더 + `- [ ] [HH:MM] 내용` 라인 생성.
5. **역파싱** (`parseMarkdown`): 저장 시 사용자가 편집한 마크다운을 다시 읽어 `ParsedTask` 목록으로 복원.
   헤더는 이모지(🏢/📚/📌)로 느슨하게 매칭해 헤더 문구를 바꿔도 카테고리를 잃지 않음.

---

## 3. 계층별 상세 API 레퍼런스

### 3-1. `data/local/TodoItem.kt` — Room 엔티티

`@Entity(tableName = "todo_items")` `data class TodoItem`

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | `Long` | `@PrimaryKey(autoGenerate = true)`. 신규 삽입 시 직접 지정하지 않음(기본값 0) |
| `title` | `String` | 할 일 내용 |
| `category` | `Category` | WORK/STUDY/ETC (`Converters`로 String 변환되어 저장) |
| `targetTime` | `Int` | **기간이 아니라 "시작 시각"**. 자정 기준 분(0~1439). 예: 21시=1260 |
| `isCompleted` | `Boolean` | 완료 여부, 기본 `false` |
| `createdAt` | `Long` | epoch millis, 기본값 `System.currentTimeMillis()`. 일회성 항목이 "어느 날짜에 속하는지" 판단하는 기준 |
| `dayOfWeek` | `Int?` | `WeekDay` 상수(1~7), null이면 일회성, 값이 있으면 매주 반복 |

### 3-2. `data/local/Category.kt` / `WeekDay.kt`

- `Category(val displayName: String)` — `WORK("업무")`, `STUDY("스터디/학습")`, `ETC("기타")`.
- `WeekDay` — `object`(싱글톤) 상수 모음. ISO-8601 기준 `MONDAY=1` ~ `SUNDAY=7`.

### 3-3. `data/local/TimeUtils.kt`

| 함수 | 시그니처 | 동작 |
|---|---|---|
| `toMinutesOfDay` | `(hour: Int, minute: Int = 0): Int` | 시/분 → 자정 기준 분(`hour*60+minute`) |
| `hourOf` | `(minutesOfDay: Int): Int` | 분 값에서 "시" 부분 추출(`/60`) |
| `minuteOf` | `(minutesOfDay: Int): Int` | 분 값에서 "분" 부분 추출(`%60`) |
| `format` | `(minutesOfDay: Int): String` | `"HH:MM"` 문자열로 변환(항상 2자리, `%02d:%02d`) |
| `parse` | `(formatted: String): Int` | `"HH:MM"` → 자정 기준 분. `":"` split 후 파싱 실패 시 0 취급 |

### 3-4. `data/local/DateUtils.kt`

- `DateKey(year, month, dayOfMonth)` — 특정 하루를 가리키는 값 타입(`month`는 1~12).
- `today(): DateKey` — 오늘 날짜.
- `weekDayOf(date): Int` — ISO-8601 요일(월=1~일=7). `Calendar.DAY_OF_WEEK`(일=1~토=7)와 순서가 달라
  일요일만 예외 처리하고 나머지는 `-1` 보정.
- `currentWeekDay(): Int` — 오늘 요일.
- `rangeMillisOf(date): Pair<Long, Long>` — 해당 날짜 00:00:00.000 ~ 다음날 00:00:00.000 직전(-1ms) millis 범위.
- `todayRangeMillis(): Pair<Long, Long>` — 오늘의 범위.
- `labelOf(date): String` — `"7월 4일 (금)"` 형식.
- `todayLabel(): String` — 오늘자 라벨(대시보드 상단 표시용).

### 3-5. `data/local/Converters.kt`

- `fromCategory(category): String` — `Category.name`으로 저장(예: `Category.WORK` → `"WORK"`).
- `toCategory(value): Category` — `Category.valueOf(value)`로 복원. `AppDatabase`에 `@TypeConverters`로 등록되어야 동작.

### 3-6. `data/local/AppDatabase.kt`

- `abstract class AppDatabase : RoomDatabase()`, `entities = [TodoItem::class]`, `version = 1`.
- `abstract fun todoDao(): TodoDao`.
- `companion object.getInstance(context)` — 앱 전체에서 DB 인스턴스를 하나만 유지하는 싱글톤.
  `@Volatile` + `synchronized`로 멀티스레드 환경에서도 인스턴스가 중복 생성되지 않도록 보장.
  실제 파일명은 `officefit.db`.

### 3-7. `data/local/TodoDao.kt` — Room DAO (실제 SQL 쿼리 정의부)

| 함수 | SQL / 동작 | 반환 | 용도 |
|---|---|---|---|
| `getAllTodos()` | `SELECT * FROM todo_items ORDER BY createdAt DESC` | `Flow<List<TodoItem>>` | 전체 목록 구독(`Repository.allTodos`) |
| `getAllTodosSortedByTime()` | `... ORDER BY dayOfWeek ASC, targetTime ASC` | `Flow<List<TodoItem>>` | (현재 미사용) 요일·시각순 정렬 |
| `getTodosByCategory(category)` | `WHERE category = :category ORDER BY createdAt DESC` | `Flow<List<TodoItem>>` | 카테고리 필터(`Repository.getByCategory`) |
| `getWeeklySchedule(category, days)` | `WHERE category = :category AND dayOfWeek IN (:days) ORDER BY dayOfWeek, targetTime` | `Flow<List<TodoItem>>` | 화/목 스터디처럼 특정 요일 반복 일정 조회 |
| `getTodayTodos(dayOfWeek, dayStartMillis, dayEndMillis)` | `WHERE dayOfWeek = :dayOfWeek OR (dayOfWeek IS NULL AND createdAt BETWEEN :dayStartMillis AND :dayEndMillis) ORDER BY targetTime` | `Flow<List<TodoItem>>` | **이름은 "Today"지만 실제로는 임의 날짜 범위를 받는 범용 쿼리.** 대시보드(오늘)와 날짜별 조회 화면 둘 다 이 쿼리를 재사용 |
| `getTodoById(id)` | `WHERE id = :id` | `TodoItem?` (`suspend`) | 단건 조회(현재 ViewModel에서 직접 호출하는 곳은 없음, Repository만 래핑) |
| `insert(todo)` | `@Insert(onConflict = REPLACE)` | `Long`(신규 id) (`suspend`) | 신규 등록(같은 id 있으면 덮어씀) |
| `update(todo)` | `@Update` | `Unit` (`suspend`) | 전체 필드 갱신 |
| `delete(todo)` | `@Delete` | `Unit` (`suspend`) | 삭제 |
| `updateCompletion(id, isCompleted)` | `UPDATE todo_items SET isCompleted = :isCompleted WHERE id = :id` | `Unit` (`suspend`) | 완료 체크 토글 전용(부분 업데이트) |

> `Flow<List<TodoItem>>` 반환 함수는 "구독"형(DB 변경 시 자동으로 새 목록 emit), `suspend fun`은 "단발성" 작업.

### 3-8. `data/repository/TodoRepository.kt`

DAO 호출을 그대로 감싸는 얇은 계층(MVVM의 Repository). ViewModel이 DAO를 직접 알 필요 없게 분리.

| 함수 | 내부 위임 | 비고 |
|---|---|---|
| `allTodos` (property) | `dao.getAllTodos()` | |
| `getByCategory(category)` | `dao.getTodosByCategory` | |
| `getWeeklySchedule(category, days)` | `dao.getWeeklySchedule` | |
| `getTodayTodos(dayOfWeek, dayStartMillis, dayEndMillis)` | `dao.getTodayTodos` | |
| `getTodosForDate(dayOfWeek, dayStartMillis, dayEndMillis)` | `dao.getTodayTodos`(동일 쿼리) | 이름만 다름 — "오늘"이 아닌 임의 날짜 조회라는 **의도**를 드러내기 위한 별칭 |
| `insertAll(todos)` | `todos.forEach { dao.insert(it) }` | 음성 덤프 저장 시 여러 건 한 번에 삽입 |
| `getById(id)` | `dao.getTodoById` | |
| `insert(todo)` | `dao.insert` | |
| `update(todo)` | `dao.update` | |
| `delete(todo)` | `dao.delete` | |
| `toggleCompletion(id, isCompleted)` | `dao.updateCompletion` | |

### 3-9. `viewmodel/MainViewModel.kt`

생성자: `MainViewModel(private val repository: TodoRepository, appContext: Context)`.
내부에서 `VoiceRecognitionManager(appContext)`를 직접 소유(1:1).

**상태(StateFlow) 목록**

| 이름 | 타입 | 설명 |
|---|---|---|
| `allTodos` | `StateFlow<List<TodoItem>>` | 전체 목록(현재 화면에서 직접 쓰이진 않고 `filteredTodos`의 원본) |
| `todayTodos` | `StateFlow<List<TodoItem>>` | 대시보드 렌더링용(§2-2) |
| `selectedCategory` | `StateFlow<Category?>` | 카테고리 필터 상태 |
| `filteredTodos` | `StateFlow<List<TodoItem>>` | `allTodos` × `selectedCategory`를 `combine`한 결과 |
| `tuesdayThursdayStudySchedule` | `StateFlow<List<TodoItem>>` | 화/목 스터디 전용 스트림(`getWeeklySchedule` 고정 파라미터) |
| `selectedDate` | `StateFlow<DateUtils.DateKey>` | 날짜별 조회 화면에서 선택된 날짜(기본값 오늘) |
| `selectedDateTodos` | `StateFlow<List<TodoItem>>` | `selectedDate`가 바뀔 때마다 `flatMapLatest`로 재구독되는 해당 날짜 목록 |
| `voiceState` / `partialVoiceText` / `recognizedVoiceText` / `voiceAmplitude` | - | `VoiceRecognitionManager`의 상태를 그대로 노출 |
| `showVoiceDumpDialog` | `StateFlow<Boolean>` | 바텀시트 표시 여부 |
| `dumpStage` | `StateFlow<VoiceDumpStage>` | `LISTENING` / `PREVIEW` |
| `previewMarkdown` | `StateFlow<String>` | PREVIEW 단계에서 편집 중인 마크다운 |

**함수 목록**

| 함수 | 동작 |
|---|---|
| `selectDate(date)` | `_selectedDate` 갱신 |
| `openVoiceDump()` | 마이크 FAB 클릭 시. LISTENING 단계로 초기화 + `voiceManager.startDump()` |
| `cancelVoiceDump()` | 듣기 중단 + 다이얼로그 닫기 |
| `finishListeningAndPreview()` | 듣기 중단 → `SmartTextParser.parse`로 마크다운 생성 → PREVIEW 전환 |
| `updatePreviewMarkdown(text)` | 프리뷰 텍스트 편집 반영 |
| `saveJournalEntry()` | 마크다운 재파싱(`SmartTextParser.parseMarkdown`) → `TodoItem` 리스트로 변환(`toDataCategory()`로 카테고리 매핑, `TimeUtils.parse`로 시각 변환) → `repository.insertAll` → 다이얼로그 닫기 |
| `selectCategory(category)` | 카테고리 필터 변경 |
| `addTodo(title, category, startHour, startMinute, dayOfWeek)` | 오늘 기준(`createdAt` 기본값) 신규 등록. `dayOfWeek` 지정 시 매주 반복 항목 |
| `addTodoForDate(date, title, category, startHour, startMinute)` | `createdAt`을 `date`의 자정으로 지정해 임의 날짜에 일회성 항목 등록(§2-3) |
| `updateTodo(todo)` | `repository.update` |
| `deleteTodo(todo)` | `repository.delete` |
| `toggleCompletion(id, isCompleted)` | `repository.toggleCompletion` |
| `onCleared()` | ViewModel 파괴 시 `voiceManager.release()`로 리소스 해제 |

> DB 접근이 필요한 함수는 전부 `viewModelScope.launch { ... }`로 감싸 비동기 실행(메인 스레드 블로킹 방지).
> `StateFlow`들은 `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ...)`로 변환되어,
> 화면이 사라진 뒤 5초 안에 재구독이 없으면 구독이 자동 정지된다(절전 정책).

### 3-10. `viewmodel/MainViewModelFactory.kt`

- `ViewModelProvider.Factory` 구현체. `MainViewModel`이 기본 생성자가 아니라 `(repository, appContext)`를
  받기 때문에 필요(Hilt 등 DI 라이브러리 미사용, 수동 DI).
- `create(modelClass)` — 요청 타입이 `MainViewModel`이면 인스턴스 생성, 아니면 `IllegalArgumentException`.

### 3-11. `OfficeFitApplication.kt`

- `Application()` 서브클래스, 앱 시작 시 시스템이 자동 생성.
- `database`, `repository` 프로퍼티를 `by lazy`로 보유(최초 접근 시점까지 DB 오픈을 늦춤) — 앱 전역 싱글톤 소스.

### 3-12. `MainActivity.kt`

- 유일한 화면 진입점(Activity). `onCreate()`에서 `OfficeFitApplication`의 `repository`를 꺼내
  `MainViewModelFactory`로 `MainViewModel`을 생성.
- `var showDateList by remember { mutableStateOf(false) }` 하나로 `MainDashboardScreen` ↔ `DateTodoListScreen` 전환
  (별도 내비게이션 라이브러리 없음).

### 3-13. `voice/VoiceRecognitionState.kt`

`sealed interface` — `Idle`(대기) / `Listening`(듣는 중) / `Processing`(처리 중) / `Error(message, code)`(실패).

### 3-14. `voice/VoiceRecognitionManager.kt`

**공개 상태(StateFlow)**: `state`, `recognizedText`(세션 누적 전체 텍스트), `partialText`(현재 세션 실시간 중간결과), `amplitude`(마이크 음량, 파동 애니메이션용).

**공개 함수**

| 함수 | 동작 |
|---|---|
| `hasMicrophonePermission()` | `RECORD_AUDIO` 권한 보유 여부 |
| `isOnDeviceRecognitionAvailable()` | API 31+ & 기기 내 온디바이스 인식기 사용 가능 여부 |
| `startDump()` | 권한/기기 지원 확인 → 상태 초기화 → `mainHandler.post { startNewSession() }` |
| `stopDump()` | `isDumpActive = false` → 재시작 루프 종료, recognizer 해제, 상태 초기화 |
| `release()` | 화면/뷰모델 파괴 시 호출, recognizer 리소스 완전 해제 |

**내부 동작 핵심**

- **연속 인식은 자동 재시작으로 구현**: `SpeechRecognizer`는 말이 끊기면 세션이 끝나버리므로,
  `onResults`/`onError(NO_MATCH, SPEECH_TIMEOUT)`에서 `isDumpActive`가 true인 동안 `restartSession()`으로
  계속 새 세션을 열고, 각 세션 텍스트를 `textBuilder`(`StringBuilder`)에 계속 이어붙인다. `stopDump()`만이 이 루프를 끝낸다.
- **오프라인 우선**: API 31+에서 `createOnDeviceSpeechRecognizer()`, 아니면 `createSpeechRecognizer()` +
  `EXTRA_PREFER_OFFLINE=true` 힌트로 폴백.
- 무음 판단 기준을 기본값보다 넉넉히 잡음(`COMPLETE_SILENCE_MS=2500`, `POSSIBLY_COMPLETE_SILENCE_MS=1500`,
  `MIN_INPUT_LENGTH_MS=15000`) — 그래도 끊기면 자동 재시작이 안전망 역할.
- `SpeechRecognizer`는 메인 스레드에서만 안전하므로 모든 recognizer 호출을 `Handler(Looper.getMainLooper())` 경유.
- `RecognitionListener` 콜백별 처리:
  - `onReadyForSpeech`/`onBeginningOfSpeech` → `state = Listening`
  - `onRmsChanged` → `amplitude` 갱신
  - `onEndOfSpeech` → `state = Processing`, `amplitude = 0`
  - `onError(NO_MATCH/SPEECH_TIMEOUT)` → 활성 상태면 조용히 재시작(다음 문장 대기 의미)
  - `onError(CLIENT/RECOGNIZER_BUSY)` → 지연 후 재시도(`BUSY_RETRY_DELAY_MS`, 세션 겹침으로 인한 일시 오류)
  - `onError(그 외)` → 덤프 완전 종료 + `state = Error(message, code)`
  - `onResults` → 텍스트 확정 후 이어붙이고, 활성 상태면 재시작
  - `onPartialResults` → `partialText` 실시간 갱신

### 3-15. `voice/SmartTextParser.kt`

외부 API 없이 정규식/문자열 처리만으로 "음성 원문 → 카테고리별 마크다운 체크리스트"를 만드는 순수 로직(§2-8-1 참고).

| 함수/프로퍼티 | 시그니처 | 설명 |
|---|---|---|
| `parse(rawText)` | `(String): String` | 원문 → 마크다운 문자열(`toMarkdown(parseToTasks(rawText))`) |
| `parseToTasks(rawText)` | `(String): List<ParsedTask>` | 마크다운 렌더링 전 구조화된 태스크 목록만 필요할 때 |
| `toMarkdown(tasks)` | `(List<ParsedTask>): String` | 태스크 목록 → 카테고리별 헤더 + 체크박스 라인 마크다운 |
| `parseMarkdown(markdown)` | `(String): List<ParsedTask>` | 마크다운(사용자 편집 포함) → 태스크 목록 역파싱 |
| `workKeywordExamples` / `studyKeywordExamples` | `List<String>` | UI 힌트 카드용, 실제 매칭 키워드 앞 3개를 그대로 노출(문구 불일치 방지) |
| `splitIntoClauses` (private) | `(String): List<String>` | 접속사/연결어미 기준 절 분리 |
| `clauseToTask` (private) | `(String): ParsedTask?` | 절 하나 → 시간 추출 + 카테고리 분류 |
| `formatTime` (private) | `(modifier, hourStr, minuteStr): String` | 오전/오후 등 → 24시간제 HH:MM |
| `classify` (private) | `(String): TaskCategory` | 키워드 매칭으로 WORK/STUDY/GENERAL 분류 |

`ParsedTask(time, category, text, isCompleted)` — `toMarkdownLine()`로 `- [ ] [HH:MM] 내용` 형태 라인 생성.
`TaskCategory(WORK/STUDY/GENERAL)`는 `data/local/Category`와 별개 enum — `MainViewModel.toDataCategory()`에서 최종 변환.

### 3-16. `ui/voice/MicrophonePermissionState.kt`

- `rememberMicrophonePermissionState(onResult): MicrophonePermissionState` — Compose 훅.
  `RECORD_AUDIO` 런타임 권한의 현재 상태(`hasPermission`)와 "다시 묻지 않음" 여부(`isPermanentlyDenied`)를 추적.
- `MicrophonePermissionState.requestPermission()` — 시스템 권한 팝업 실행.
- 두 번째 이후 거부 시 `shouldShowRequestPermissionRationale`이 false가 되는 것으로 "영구 거부"를 판별.

### 3-17. `ui/dashboard/*.kt` — Composable 화면 요소

| 파일/함수 | 역할 |
|---|---|
| `MainDashboardScreen` | 대시보드 루트. 헤더 + 오늘 목록 + 마이크 FAB, 각종 다이얼로그 상태 소유 |
| `DashboardHeader` (private) | 상단 로고/날짜/"📅 날짜별 보기" 버튼 |
| `TodoListContent` | 카테고리별 그룹 리스트 렌더링(대시보드·날짜별 화면 공용, `private` 아님) |
| `TodoRow` (private) | 할 일 한 줄: 체크박스, 시각 뱃지, 제목(완료 시 취소선), 🗑 삭제, 행 탭=수정 |
| `EmptyTodoState` (private) | 목록이 비어있을 때 안내 문구 |
| `DateTodoListScreen` | 날짜별 조회 화면 루트(§2-7) |
| `showDatePicker` (private) | 네이티브 `DatePickerDialog` 래퍼 |
| `VoiceDumpDialog` | 음성 덤프 바텀시트. `dumpStage`에 따라 `ListeningStageContent`/`PreviewStageContent` 전환 |
| `ListeningStageContent` (private) | 실시간 인식 텍스트 + 파동 애니메이션 + "완료 및 정리하기"/"취소" |
| `SpeakingTemplateHint` (private) | 접이식 "말하기 예시" 안내 카드 |
| `PulsingMicIndicator` (private) | 마이크 주변 파동 애니메이션(기본 펄스 + 음량 연동 스케일) |
| `PreviewStageContent` (private) | 마크다운 편집 필드 + "일지 저장"/"취소" |
| `AddTodoDialog` | "+"로 여는 신규 등록 다이얼로그(제목/카테고리/HH:MM 입력) |
| `EditTodoDialog` | 행 탭으로 여는 수정 다이얼로그(삭제는 위임) |
| `DeleteTodoConfirmDialog` | 삭제 최종 확인 다이얼로그 |
| `Category.shortLabel()` / `Category.sectionTitle()` | 카테고리 → UI 표시용 이모지+텍스트 매핑(각각 다이얼로그용 짧은 표기, 목록 섹션용 긴 표기) |

---

## 4. 참고 — 아직 구현되지 않은 부분

- 음성 인식 정확도의 실사용 기반 개선(오탐 케이스 수집).
- 화/목 스터디 같은 주간 반복 일정 **등록** UI(현재는 `TodoDao.getWeeklySchedule`로 조회만 가능).
- 카테고리 필터/완료 항목 통계·회고 뷰(`filteredTodos`/`selectedCategory` 상태는 이미 있으나 이를 사용하는 화면 UI는 아직 없음).
