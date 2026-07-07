package com.officefit.data.local

import java.util.Calendar

/**
 * "오늘" 관련 계산 전용 유틸. TimeUtils와 마찬가지로 core library desugaring이
 * 필요한 java.time 대신 java.util.Calendar만 사용한다.
 */
object DateUtils {

    private val koreanWeekdayNames = arrayOf("월", "화", "수", "목", "금", "토", "일")

    /**
     * 연/월/일만으로 특정 하루를 가리키는 값. 일자별 TODO 조회 화면에서 "오늘이 아닌 다른 날"을
     * 고를 때 쓴다. month는 사람이 쓰는 표기대로 1~12 (java.util.Calendar.MONTH처럼 0-based가 아님).
     */
    data class DateKey(val year: Int, val month: Int, val dayOfMonth: Int)

    private fun calendarFor(date: DateKey): Calendar = Calendar.getInstance().apply {
        set(Calendar.YEAR, date.year)
        set(Calendar.MONTH, date.month - 1)
        set(Calendar.DAY_OF_MONTH, date.dayOfMonth)
    }

    /** 오늘 날짜를 [DateKey]로 */
    fun today(): DateKey {
        val calendar = Calendar.getInstance()
        return DateKey(
            year = calendar.get(Calendar.YEAR),
            month = calendar.get(Calendar.MONTH) + 1,
            dayOfMonth = calendar.get(Calendar.DAY_OF_MONTH)
        )
    }

    /**
     * ISO-8601 기준 요일 (WeekDay 상수: 월=1 ~ 일=7)
     * 주의: 안드로이드의 `Calendar.DAY_OF_WEEK`는 일요일=1, 월요일=2, ... 토요일=7 순서를 쓴다
     * (우리가 원하는 월=1~일=7 순서와 다름). 그래서 일요일만 예외 처리하고, 나머지는 1을 빼서 맞춘다.
     */
    fun weekDayOf(date: DateKey): Int {
        val calendarDay = calendarFor(date).get(Calendar.DAY_OF_WEEK)
        return if (calendarDay == Calendar.SUNDAY) WeekDay.SUNDAY else calendarDay - 1
    }

    /** ISO-8601 기준 오늘 요일 (WeekDay 상수: 월=1 ~ 일=7) */
    fun currentWeekDay(): Int = weekDayOf(today())

    /**
     * 해당 날짜 자정(00:00:00.000)부터 다음날 자정 직전까지의 epoch millis 범위.
     * "epoch millis"란 1970년 1월 1일 0시부터 지금까지 흐른 밀리초(1/1000초) 숫자로,
     * 안드로이드/자바에서 날짜와 시간을 표현하는 가장 기본적인 방식이다.
     * Room DB에 저장된 할 일의 "생성 시각"이 그 날 안에 있는지 비교할 때 이 범위를 사용한다.
     * `Pair<Long, Long>`은 값 2개(시작, 끝)를 하나로 묶어 반환하는 Kotlin의 간단한 튜플 타입이다.
     */
    fun rangeMillisOf(date: DateKey): Pair<Long, Long> {
        val start = calendarFor(date).apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis
        val end = start + 24L * 60 * 60 * 1000 - 1
        return start to end
    }

    /** 오늘 자정부터 다음날 자정 직전까지의 epoch millis 범위 */
    fun todayRangeMillis(): Pair<Long, Long> = rangeMillisOf(today())

    /** "7월 4일 (금)" 형식 라벨 */
    fun labelOf(date: DateKey): String {
        val weekdayName = koreanWeekdayNames[weekDayOf(date) - 1]
        return "%d월 %d일 (%s)".format(date.month, date.dayOfMonth, weekdayName)
    }

    /** 대시보드 상단에 쓰는 오늘자 라벨 */
    fun todayLabel(): String = labelOf(today())
}
