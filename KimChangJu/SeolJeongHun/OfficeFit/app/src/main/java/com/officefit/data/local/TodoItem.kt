package com.officefit.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room은 안드로이드에서 기기 내부 DB(SQLite)를 쉽게 다루게 해주는 라이브러리다.
 * `@Entity`가 붙은 이 클래스는 "DB에 저장될 테이블 하나"를 의미한다 — Room이 이 클래스를 보고
 * 자동으로 `todo_items`라는 이름의 SQLite 테이블을 만들어준다. 클래스의 각 프로퍼티(val)는
 * 테이블의 컬럼(열) 하나에 대응한다.
 * `data class`는 Kotlin에서 "데이터를 담기 위한 클래스"에 붙이는 표시로, 값 비교(equals)나
 * 출력(toString) 같은 기능을 자동으로 만들어준다.
 */
@Entity(tableName = "todo_items")
data class TodoItem(
    // @PrimaryKey는 이 컬럼이 각 행(row)을 구분하는 고유 번호임을 뜻한다.
    // autoGenerate = true 이므로 새 항목을 넣을 때 id를 직접 정하지 않아도 Room이 1,2,3...으로 자동 채번한다.
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    val title: String,

    val category: Category,

    // 목표 시작 시각 - 자정(00:00) 기준 분 단위(0~1439). 예: 21시 = 1260, 09시30분 = 570
    // "몇 분 동안 할지(기간)"가 아니라 "몇 시에 시작할지(시각)"를 의미한다.
    val targetTime: Int = 0,

    val isCompleted: Boolean = false,

    // epoch millis (1970년 1월 1일 0시부터 흐른 밀리초) - 이 항목이 생성된 시각
    val createdAt: Long = System.currentTimeMillis(),

    // 매주 반복되는 요일(WeekDay 상수, 1~7). 일회성 할 일이면 null.
    // 예: 매주 화/목 저녁 스터디처럼 "요일마다 반복되는 할 일"을 표현할 때만 값이 들어간다.
    val dayOfWeek: Int? = null
)
