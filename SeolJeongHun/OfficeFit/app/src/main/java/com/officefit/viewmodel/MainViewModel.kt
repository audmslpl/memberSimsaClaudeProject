package com.officefit.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.officefit.data.local.Category
import com.officefit.data.local.DateUtils
import com.officefit.data.local.TimeUtils
import com.officefit.data.local.TodoItem
import com.officefit.data.local.WeekDay
import com.officefit.data.repository.TodoRepository
import com.officefit.voice.SmartTextParser
import com.officefit.voice.VoiceRecognitionManager
import com.officefit.voice.VoiceRecognitionState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/** VoiceDumpDialog가 어느 단계를 보여줘야 하는지 나타내는 상태 */
enum class VoiceDumpStage {
    LISTENING,
    PREVIEW
}

/**
 * `ViewModel`은 안드로이드 Jetpack이 제공하는 "화면의 상태와 로직을 담당하는 계층"이다.
 * 화면(Compose UI)이 회전하거나 재구성돼도 ViewModel은 그대로 살아남기 때문에,
 * "이 화면이 지금 어떤 데이터를 보여줘야 하는지"를 여기서 관리하면 화면을 새로 그려도 데이터가 안 날아간다.
 * MVVM 아키텍처에서 View(Compose 화면)는 이 ViewModel이 들고 있는 StateFlow 값을 구독해서 그리기만 하고,
 * 실제 DB 접근이나 비즈니스 로직은 전부 이곳(그리고 그 아래 Repository/DAO)에서 처리한다.
 *
 * `StateFlow<T>`는 "현재 값을 항상 하나 들고 있고, 값이 바뀔 때마다 구독자에게 알려주는" 데이터 타입이다.
 * Compose에서는 `collectAsState()`로 구독하면 값이 바뀔 때 화면이 자동으로 다시 그려진다.
 * `viewModelScope`는 이 ViewModel이 살아있는 동안만 유효한 코루틴(비동기 작업) 범위로,
 * ViewModel이 파괴될 때 안에서 실행 중이던 코루틴도 자동으로 취소되어 메모리 누수를 막아준다.
 */
class MainViewModel(
    private val repository: TodoRepository,
    appContext: Context
) : ViewModel() {

    private val voiceManager = VoiceRecognitionManager(appContext)

    // Repository가 주는 Flow(구독 스트림)를 StateFlow로 바꾼다.
    // stateIn(...)의 SharingStarted.WhileSubscribed(5000)은 "화면이 보고 있는 동안만 구독을 유지하고,
    // 화면이 사라진 뒤 5초 안에 다시 구독하지 않으면 스트림을 멈춘다"는 절전 정책이다.
    val allTodos: StateFlow<List<TodoItem>> = repository.allTodos
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** 대시보드 중앙에 렌더링되는, 오늘 요일 반복 항목 + 오늘 생성된 일회성 항목 */
    val todayTodos: StateFlow<List<TodoItem>> = run {
        val (dayStart, dayEnd) = DateUtils.todayRangeMillis()
        repository.getTodayTodos(DateUtils.currentWeekDay(), dayStart, dayEnd)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // "_밑줄로 시작하는 private 변수 + 밑줄 없는 public 변수" 쌍은 Kotlin/Android에서 흔한 관례다.
    // 내부에서는 값을 바꿀 수 있는 MutableStateFlow를 쓰고, 외부(화면)에는 읽기 전용(StateFlow)만 노출해서
    // 화면 쪽 코드가 실수로 ViewModel의 상태를 직접 바꾸지 못하게 막는다.
    private val _selectedCategory = MutableStateFlow<Category?>(null)
    val selectedCategory: StateFlow<Category?> = _selectedCategory.asStateFlow()

    // combine()은 여러 StateFlow/Flow를 합쳐서 "둘 중 하나라도 바뀌면 다시 계산"하는 새 Flow를 만든다.
    // 여기서는 "전체 할 일 목록"과 "선택된 카테고리 필터"를 합쳐서, 필터링된 목록을 만든다.
    val filteredTodos: StateFlow<List<TodoItem>> =
        combine(allTodos, _selectedCategory) { todos, category ->
            if (category == null) todos else todos.filter { it.category == category }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // 퇴근 후 화/목 개인 스터디 일정만 모아보는 전용 스트림
    val tuesdayThursdayStudySchedule: StateFlow<List<TodoItem>> =
        repository.getWeeklySchedule(
            category = Category.STUDY,
            days = listOf(WeekDay.TUESDAY, WeekDay.THURSDAY)
        ).stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // ---- 일자별 조회 화면 ----

    private val _selectedDate = MutableStateFlow(DateUtils.today())
    val selectedDate: StateFlow<DateUtils.DateKey> = _selectedDate.asStateFlow()

    // flatMapLatest는 "선택된 날짜가 바뀔 때마다, 그 날짜에 대한 새 Flow 구독으로 갈아탄다"는 뜻이다.
    // 이전 날짜를 구독하던 Flow는 자동으로 취소되므로, 날짜를 계속 바꿔도 옛 구독이 남아있지 않는다.
    // 아직 kotlinx.coroutines에서 실험적(Experimental) API로 표시되어 있어 @OptIn으로 사용 의사를 명시한다.
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val selectedDateTodos: StateFlow<List<TodoItem>> = _selectedDate
        .flatMapLatest { date ->
            val (dayStart, dayEnd) = DateUtils.rangeMillisOf(date)
            repository.getTodosForDate(DateUtils.weekDayOf(date), dayStart, dayEnd)
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun selectDate(date: DateUtils.DateKey) {
        _selectedDate.value = date
    }

    // ---- 모닝 보이스 덤프 ----

    val voiceState: StateFlow<VoiceRecognitionState> = voiceManager.state
    val partialVoiceText: StateFlow<String> = voiceManager.partialText
    val recognizedVoiceText: StateFlow<String> = voiceManager.recognizedText
    val voiceAmplitude: StateFlow<Float> = voiceManager.amplitude

    private val _showVoiceDumpDialog = MutableStateFlow(false)
    val showVoiceDumpDialog: StateFlow<Boolean> = _showVoiceDumpDialog.asStateFlow()

    private val _dumpStage = MutableStateFlow(VoiceDumpStage.LISTENING)
    val dumpStage: StateFlow<VoiceDumpStage> = _dumpStage.asStateFlow()

    private val _previewMarkdown = MutableStateFlow("")
    val previewMarkdown: StateFlow<String> = _previewMarkdown.asStateFlow()

    /** 마이크 FAB을 눌렀을 때 호출 (권한 확인은 Compose 쪽에서 먼저 처리) */
    fun openVoiceDump() {
        _dumpStage.value = VoiceDumpStage.LISTENING
        _previewMarkdown.value = ""
        _showVoiceDumpDialog.value = true
        voiceManager.startDump()
    }

    /** 듣는 중 다이얼로그를 취소(뒤로가기/바깥 터치 등) */
    fun cancelVoiceDump() {
        voiceManager.stopDump()
        _showVoiceDumpDialog.value = false
    }

    /** "완료 및 정리하기" 버튼: 듣기를 멈추고 SmartTextParser로 정리해 프리뷰 표시 */
    fun finishListeningAndPreview() {
        voiceManager.stopDump()
        _previewMarkdown.value = SmartTextParser.parse(voiceManager.recognizedText.value)
        _dumpStage.value = VoiceDumpStage.PREVIEW
    }

    /** 프리뷰 화면에서 사용자가 마크다운 텍스트를 직접 수정할 때 호출 */
    fun updatePreviewMarkdown(text: String) {
        _previewMarkdown.value = text
    }

    /** "일지 저장" 버튼: 프리뷰 마크다운을 다시 파싱해 개별 TodoItem으로 저장 */
    fun saveJournalEntry() {
        val tasks = SmartTextParser.parseMarkdown(_previewMarkdown.value)
        viewModelScope.launch {
            repository.insertAll(
                tasks.map { task ->
                    TodoItem(
                        title = task.text,
                        category = task.category.toDataCategory(),
                        targetTime = task.time?.let(TimeUtils::parse) ?: 0,
                        isCompleted = task.isCompleted,
                        dayOfWeek = null
                    )
                }
            )
            _showVoiceDumpDialog.value = false
            _previewMarkdown.value = ""
        }
    }

    private fun SmartTextParser.TaskCategory.toDataCategory(): Category = when (this) {
        SmartTextParser.TaskCategory.WORK -> Category.WORK
        SmartTextParser.TaskCategory.STUDY -> Category.STUDY
        SmartTextParser.TaskCategory.GENERAL -> Category.ETC
    }

    // ---- 공용 CRUD ----

    fun selectCategory(category: Category?) {
        _selectedCategory.value = category
    }

    fun addTodo(
        title: String,
        category: Category,
        startHour: Int,
        startMinute: Int = 0,
        dayOfWeek: Int? = null
    ) {
        // viewModelScope.launch { ... }는 "코루틴을 하나 새로 시작해서 중괄호 안 코드를 비동기로 실행하라"는 뜻이다.
        // DB 저장(repository.insert)은 시간이 걸릴 수 있는 작업이라 이렇게 감싸서 화면이 멈추지 않게 한다.
        viewModelScope.launch {
            repository.insert(
                TodoItem(
                    title = title,
                    category = category,
                    targetTime = TimeUtils.toMinutesOfDay(startHour, startMinute),
                    dayOfWeek = dayOfWeek
                )
            )
        }
    }

    /**
     * 일자별 조회 화면의 "+" 버튼용: [date]가 오늘이 아니어도 그 날짜에 바로 등록되게 한다.
     * 음성 덤프(saveJournalEntry)는 항상 "지금(now)"을 createdAt으로 찍어 오늘에만 귀속되는 것과 달리,
     * 여기서는 createdAt을 [date]의 자정 시각으로 직접 지정해 "일회성 할 일이 그 날짜에 생성됨"을 흉내낸다 —
     * TodoDao.getTodayTodos 쿼리가 "dayOfWeek IS NULL AND createdAt BETWEEN 그날 자정~다음날 자정" 조건으로
     * 일회성 항목을 찾기 때문에, 이렇게 해야 원하는 날짜의 목록에 나타난다.
     */
    fun addTodoForDate(
        date: DateUtils.DateKey,
        title: String,
        category: Category,
        startHour: Int,
        startMinute: Int = 0
    ) {
        viewModelScope.launch {
            val (dayStart, _) = DateUtils.rangeMillisOf(date)
            repository.insert(
                TodoItem(
                    title = title,
                    category = category,
                    targetTime = TimeUtils.toMinutesOfDay(startHour, startMinute),
                    createdAt = dayStart,
                    dayOfWeek = null
                )
            )
        }
    }

    fun updateTodo(todo: TodoItem) {
        viewModelScope.launch { repository.update(todo) }
    }

    fun deleteTodo(todo: TodoItem) {
        viewModelScope.launch { repository.delete(todo) }
    }

    fun toggleCompletion(id: Long, isCompleted: Boolean) {
        viewModelScope.launch { repository.toggleCompletion(id, isCompleted) }
    }

    override fun onCleared() {
        super.onCleared()
        voiceManager.release()
    }
}
