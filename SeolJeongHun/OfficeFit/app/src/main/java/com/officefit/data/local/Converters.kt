package com.officefit.data.local

import androidx.room.TypeConverter

/**
 * SQLite(Room이 쓰는 기기 내부 DB)는 기본적으로 텍스트/숫자 같은 단순한 타입만 저장할 수 있고,
 * `Category` 같은 enum 타입은 그대로 저장하지 못한다. `@TypeConverter`가 붙은 함수는
 * "이런 타입을 저장할 땐 이렇게 변환해서 넣고, 꺼낼 땐 이렇게 되돌려라"를 Room에게 알려주는 역할이다.
 * 이 클래스는 AppDatabase에 등록되어야 Room이 실제로 사용한다.
 */
class Converters {
    // DB에 저장할 때: Category enum → 그 이름의 문자열(예: Category.WORK → "WORK")
    @TypeConverter
    fun fromCategory(category: Category): String = category.name

    // DB에서 꺼낼 때: 문자열 → 다시 Category enum으로 복원
    @TypeConverter
    fun toCategory(value: String): Category = Category.valueOf(value)
}
