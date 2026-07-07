package com.officefit.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

/**
 * DAO = Data Access Object. Room에서 "DB에 어떤 SQL 질의(쿼리)를 실행할지"를 정의하는 곳이다.
 * `interface`로 선언하고 함수 시그니처와 SQL 문자열만 적어두면, Room이 컴파일 시점에
 * 실제로 동작하는 구현체를 자동 생성해준다 (직접 SQLite 코드를 짤 필요가 없다).
 * `@Dao` 어노테이션이 Room에게 "이 인터페이스는 DAO다"라고 알려준다.
 *
 * 반환 타입이 `Flow<List<TodoItem>>`인 함수들은 "구독"용이다. `Flow`는 Kotlin Coroutines가 제공하는
 * 비동기 데이터 스트림으로, DB의 해당 데이터가 바뀔 때마다 자동으로 새 목록을 흘려보내준다.
 * 즉 화면 쪽에서 한 번 구독해두면, 할 일을 추가/삭제/수정할 때마다 화면이 알아서 갱신된다.
 * 반면 `suspend fun`으로 선언된 함수들은 "한 번만 실행하고 끝나는" 단발성 작업(삽입/수정/삭제 등)이며,
 * `suspend`는 이 함수가 코루틴(비동기 작업 단위) 안에서만 호출 가능하다는 뜻이다 —
 * DB 작업은 시간이 걸릴 수 있어서 메인(화면) 스레드를 막지 않기 위해 항상 비동기로 실행한다.
 */
@Dao
interface TodoDao {

    // @Query 안의 문자열은 실제 SQL문이다. ":category" 처럼 콜론이 붙은 이름은 함수 파라미터 값이 그대로 대입된다.
    @Query("SELECT * FROM todo_items ORDER BY createdAt DESC")
    fun getAllTodos(): Flow<List<TodoItem>>

    @Query("SELECT * FROM todo_items ORDER BY dayOfWeek ASC, targetTime ASC")
    fun getAllTodosSortedByTime(): Flow<List<TodoItem>>

    @Query("SELECT * FROM todo_items WHERE category = :category ORDER BY createdAt DESC")
    fun getTodosByCategory(category: Category): Flow<List<TodoItem>>

    // 퇴근 후 화/목 스터디처럼 특정 요일에 반복되는 카테고리별 일정 조회
    @Query(
        """
        SELECT * FROM todo_items
        WHERE category = :category AND dayOfWeek IN (:days)
        ORDER BY dayOfWeek ASC, targetTime ASC
        """
    )
    fun getWeeklySchedule(category: Category, days: List<Int>): Flow<List<TodoItem>>

    // 오늘의 대시보드용: 오늘 요일에 반복되는 항목 + 오늘 생성된 일회성 항목
    @Query(
        """
        SELECT * FROM todo_items
        WHERE dayOfWeek = :dayOfWeek
           OR (dayOfWeek IS NULL AND createdAt BETWEEN :dayStartMillis AND :dayEndMillis)
        ORDER BY targetTime ASC
        """
    )
    fun getTodayTodos(dayOfWeek: Int, dayStartMillis: Long, dayEndMillis: Long): Flow<List<TodoItem>>

    @Query("SELECT * FROM todo_items WHERE id = :id")
    suspend fun getTodoById(id: Long): TodoItem?

    // @Insert/@Update/@Delete는 SQL문 없이도 Room이 파라미터로 받은 TodoItem을 보고 알아서
    // INSERT/UPDATE/DELETE 문을 만들어 실행해준다. onConflict = REPLACE는 같은 id가 이미 있으면
    // 새로 덮어쓰라는 충돌 처리 전략이다.
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(todo: TodoItem): Long

    @Update
    suspend fun update(todo: TodoItem)

    @Delete
    suspend fun delete(todo: TodoItem)

    @Query("UPDATE todo_items SET isCompleted = :isCompleted WHERE id = :id")
    suspend fun updateCompletion(id: Long, isCompleted: Boolean)
}
