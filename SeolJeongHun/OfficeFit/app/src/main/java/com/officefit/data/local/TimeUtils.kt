package com.officefit.data.local

/**
 * "시각"을 다루는 계산 도구 모음입니다.
 * 이 앱은 시간을 "오전 9시 30분" 같은 형태로 저장하지 않고, 자정(00:00)부터 몇 분이 지났는지를
 * 나타내는 정수(0~1439) 하나로 저장합니다. 예: 09:30 → 9*60+30 = 570.
 * 이렇게 하면 DB에는 Int 하나만 저장하면 되고, 화면에 보여줄 때만 이 유틸로 "HH:MM" 문자열로 바꿉니다.
 */
object TimeUtils {
    // 시(hour)와 분(minute)을 받아서 "자정부터 몇 분째인지"로 합칩니다.
    fun toMinutesOfDay(hour: Int, minute: Int = 0): Int = hour * 60 + minute

    // 반대로, 분(minutesOfDay) 값에서 "시" 부분만 뽑아냅니다.
    fun hourOf(minutesOfDay: Int): Int = minutesOfDay / 60

    // "분" 부분만 뽑아냅니다.
    fun minuteOf(minutesOfDay: Int): Int = minutesOfDay % 60

    // 화면 표시용으로 "09:30"처럼 항상 두 자리(%02d)로 맞춘 문자열을 만듭니다.
    fun format(minutesOfDay: Int): String =
        "%02d:%02d".format(hourOf(minutesOfDay), minuteOf(minutesOfDay))

    /** "HH:MM" 형식 문자열을 자정 기준 분(minutes-of-day)으로 되돌린다. */
    fun parse(formatted: String): Int {
        val parts = formatted.split(":")
        val hour = parts.getOrNull(0)?.toIntOrNull() ?: 0
        val minute = parts.getOrNull(1)?.toIntOrNull() ?: 0
        return toMinutesOfDay(hour, minute)
    }
}
