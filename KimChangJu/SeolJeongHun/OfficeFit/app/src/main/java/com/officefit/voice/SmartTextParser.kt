package com.officefit.voice

/**
 * 음성으로 받아쓴 날 것의 텍스트(Raw Speech Text)를 분석해 마크다운 투두 리스트로
 * 구조화하는 유틸리티. 외부 API 없이 정규식/문자열 처리만으로 동작한다.
 *
 * 처리 순서: 접속사·연결어미 기준으로 문장을 태스크 단위로 분리 → 각 태스크에서
 * 시간 표현을 추출/포맷팅 → 키워드 매칭으로 카테고리 분류 → 카테고리별로 묶어
 * 마크다운 문자열로 렌더링.
 */
object SmartTextParser {

    /** 분리된 절을 표시하기 위한 내부 전용 구분자. 일반 텍스트에 등장하지 않는 제어 문자를 사용. */
    private const val SPLIT_MARKER = ""

    // 명시적 접속사/구분자. "그 다음에"가 "다음으로" 등에 부분적으로 먹히지 않도록
    // 긴 표현부터 매칭되도록 정렬해 둔다.
    private val explicitConnectors = listOf(
        "그리고 나서", "그런 다음에", "그런 다음", "그 다음에", "그다음에", "다음으로", "그리고"
    ).sortedByDescending { it.length }

    // "~하고" / "-고"로 끝나는 동사 연결형: 뒤에 다른 절이 이어질 때만(공백 뒤에
    // 내용이 더 있을 때만) 절 구분자로 취급한다. 문장 맨 끝의 "-고"는 분리하지 않는다.
    private val verbConnectorRegex = Regex("([가-힣]+?)(?:하고|고)\\s+(?=\\S)")

    // 시간 표현: "10시", "오후 2시", "저녁 7시 30분" 등. 시간 뒤에 붙는 조사 "에"도
    // 함께 매칭해 제거 대상에 포함시킨다.
    private val timeRegex =
        Regex("(오전|오후|아침|저녁|밤|새벽)?\\s*(\\d{1,2})시(?:\\s*(\\d{1,2})분)?에?")

    private val workKeywords = listOf("회의", "검토", "SQL", "업무", "배포", "코드", "프로젝트", "CM")
    private val studyKeywords = listOf("스터디", "공부", "학습", "문서", "강의", "운동")

    /**
     * UI의 "말하기 예시" 안내 카드에서 보여줄 키워드 목록. 안내 문구가 실제 매칭
     * 로직([workKeywords]/[studyKeywords])과 어긋나지 않도록 앞부분 일부를 그대로 노출한다.
     */
    val workKeywordExamples: List<String> get() = workKeywords.take(3)
    val studyKeywordExamples: List<String> get() = studyKeywords.take(3)

    // Category(data/local) 와는 별개의, 이 파서 전용 카테고리 enum이다.
    // MainViewModel.toDataCategory()에서 이 값을 최종적으로 data/local의 Category로 변환한다.
    enum class TaskCategory(val header: String) {
        WORK("### 🏢 사내 업무"),
        STUDY("### 📚 개인 스터디/성장"),
        GENERAL("### 📌 일반 할 일")
    }

    // 음성 인식 결과 한 문장(절)을 분석한 결과를 담는 데이터 덩어리.
    data class ParsedTask(
        val time: String?,
        val category: TaskCategory,
        val text: String,
        val isCompleted: Boolean = false
    ) {
        fun toMarkdownLine(): String {
            val checkbox = if (isCompleted) "- [x]" else "- [ ]"
            return if (time != null) "$checkbox [$time] $text" else "$checkbox $text"
        }
    }

    // 프리뷰 화면에서 사용자가 수정한 마크다운을 다시 읽어들일 때 쓰는 패턴들
    private val checkboxLineRegex = Regex("^-\\s*\\[( |x|X)\\]\\s*(.*)$")
    private val timePrefixRegex = Regex("^\\[(\\d{1,2}:\\d{2})\\]\\s*(.*)$")

    /** 날 것의 음성 텍스트를 바로 마크다운 투두 리스트 문자열로 변환 */
    fun parse(rawText: String): String = toMarkdown(parseToTasks(rawText))

    /** 마크다운으로 렌더링하기 전, 구조화된 태스크 목록만 필요할 때 사용 */
    fun parseToTasks(rawText: String): List<ParsedTask> =
        splitIntoClauses(rawText).mapNotNull(::clauseToTask)

    fun toMarkdown(tasks: List<ParsedTask>): String {
        val grouped = tasks.groupBy { it.category }
        return TaskCategory.entries
            .filter { grouped.containsKey(it) }
            .joinToString("\n") { category ->
                buildString {
                    append(category.header)
                    grouped.getValue(category).forEach { task ->
                        append('\n')
                        append(task.toMarkdownLine())
                    }
                }
            }
    }

    /**
     * [toMarkdown]으로 만든(혹은 사용자가 직접 수정한) 마크다운 텍스트를 다시
     * [ParsedTask] 목록으로 되돌린다. "일지 저장" 시 프리뷰에서 편집된 최종
     * 텍스트를 실제 TodoItem으로 변환하기 위해 사용한다.
     *
     * 헤더 줄은 이모지로만 느슨하게 매칭해, 사용자가 헤더 문구를 살짝 바꿔도
     * 카테고리를 잃지 않도록 한다. 알 수 없는 헤더/헤더가 없는 경우 직전
     * 카테고리(기본값 GENERAL)를 그대로 사용한다.
     */
    fun parseMarkdown(markdown: String): List<ParsedTask> {
        var currentCategory = TaskCategory.GENERAL
        val tasks = mutableListOf<ParsedTask>()

        markdown.lines().forEach { rawLine ->
            val line = rawLine.trim()
            when {
                line.isEmpty() -> Unit

                line.startsWith("#") -> {
                    currentCategory = when {
                        line.contains("🏢") -> TaskCategory.WORK
                        line.contains("📚") -> TaskCategory.STUDY
                        line.contains("📌") -> TaskCategory.GENERAL
                        else -> currentCategory
                    }
                }

                else -> {
                    val checkboxMatch = checkboxLineRegex.find(line) ?: return@forEach
                    val isCompleted = checkboxMatch.groupValues[1].equals("x", ignoreCase = true)
                    var rest = checkboxMatch.groupValues[2].trim()

                    var time: String? = null
                    timePrefixRegex.find(rest)?.let { timeMatch ->
                        time = timeMatch.groupValues[1]
                        rest = timeMatch.groupValues[2].trim()
                    }

                    if (rest.isNotEmpty()) {
                        tasks.add(ParsedTask(time, currentCategory, rest, isCompleted))
                    }
                }
            }
        }

        return tasks
    }

    private fun splitIntoClauses(rawText: String): List<String> {
        var normalized = rawText.trim().replace(Regex("\\s+"), " ")

        for (connector in explicitConnectors) {
            normalized = normalized.replace(connector, SPLIT_MARKER)
        }
        normalized = verbConnectorRegex.replace(normalized) { match ->
            match.groupValues[1] + SPLIT_MARKER
        }

        return normalized.split(SPLIT_MARKER)
            .map { it.trim() }
            .filter { it.isNotEmpty() }
    }

    private fun clauseToTask(clause: String): ParsedTask? {
        val match = timeRegex.find(clause)
        val time = match?.let { formatTime(it.groupValues[1], it.groupValues[2], it.groupValues[3]) }

        val withoutTime = if (match != null) {
            clause.substring(0, match.range.first) + clause.substring(match.range.last + 1)
        } else {
            clause
        }
        val text = withoutTime.replace(Regex("\\s+"), " ").trim().trim('-', ',', '.', ' ')

        if (text.isEmpty()) return null
        return ParsedTask(time, classify(clause), text)
    }

    private fun formatTime(modifier: String, hourStr: String, minuteStr: String): String {
        var hour = hourStr.toIntOrNull() ?: 0
        val minute = minuteStr.toIntOrNull() ?: 0

        hour = when (modifier) {
            "오후", "저녁", "밤" -> if (hour in 1..11) hour + 12 else hour
            "오전", "아침" -> if (hour == 12) 0 else hour
            "새벽" -> if (hour == 12) 0 else hour
            else -> hour
        }.coerceIn(0, 23)

        return "%02d:%02d".format(hour, minute)
    }

    private fun classify(clause: String): TaskCategory {
        val upper = clause.uppercase()
        if (workKeywords.any { upper.contains(it.uppercase()) }) return TaskCategory.WORK
        if (studyKeywords.any { clause.contains(it) }) return TaskCategory.STUDY
        return TaskCategory.GENERAL
    }
}
