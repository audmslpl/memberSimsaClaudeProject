package com.officefit.data.local

/**
 * 할 일(TodoItem)이 어떤 종류인지 구분하는 분류표입니다.
 * Kotlin의 `enum class`는 "가능한 값이 정해진 목록"을 표현할 때 씁니다.
 * 여기서는 업무/스터디/기타, 이 3가지 값만 존재할 수 있고 그 외의 값은 만들 수 없습니다.
 *
 * `displayName`은 각 값에 딸려오는 부가 데이터입니다.
 * 예: `Category.WORK`라는 값 자체는 코드에서 쓰는 이름이고,
 * `Category.WORK.displayName`은 화면에 실제로 보여줄 한글 텍스트("업무")입니다.
 * 이렇게 나눠두면 코드 이름(WORK)은 안 바뀌면서 화면에 보이는 문구만 자유롭게 바꿀 수 있습니다.
 */
enum class Category(val displayName: String) {
    WORK("업무"),
    STUDY("스터디/학습"),
    ETC("기타")
}
