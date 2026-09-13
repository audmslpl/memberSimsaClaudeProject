package com.officefit.data.local

/**
 * 요일을 숫자로 표현하기 위한 상수 모음입니다. ISO-8601 기준(월요일=1 ~ 일요일=7)을 따릅니다.
 * Kotlin의 `object`는 인스턴스를 하나만 만드는 "싱글톤"입니다. `WeekDay()`처럼 새로 만들 필요 없이
 * 어디서든 `WeekDay.MONDAY`처럼 바로 꺼내 쓸 수 있습니다.
 * 요일을 굳이 java.time의 `DayOfWeek` 같은 정식 타입 대신 단순 `Int`(정수)로 저장하는 이유는,
 * java.time을 쓰려면 Android에서 별도의 "core library desugaring" 설정이 추가로 필요해서
 * 프로젝트를 더 단순하게 유지하기 위함입니다.
 */
object WeekDay {
    const val MONDAY = 1
    const val TUESDAY = 2
    const val WEDNESDAY = 3
    const val THURSDAY = 4
    const val FRIDAY = 5
    const val SATURDAY = 6
    const val SUNDAY = 7
}
