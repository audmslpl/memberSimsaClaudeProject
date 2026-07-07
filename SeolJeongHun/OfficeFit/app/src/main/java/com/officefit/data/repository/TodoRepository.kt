package com.officefit.data.repository

import com.officefit.data.local.Category
import com.officefit.data.local.TodoDao
import com.officefit.data.local.TodoItem
import kotlinx.coroutines.flow.Flow

/**
 * Repository(저장소) 패턴: ViewModel(화면 로직)이 DAO(DB 접근 상세)를 직접 알 필요 없이,
 * 이 클래스를 거쳐서 데이터를 주고받게 하는 중간 계층이다.
 * 지금은 단순히 DAO 함수를 그대로 호출만 하지만, 나중에 "서버와도 동기화한다"거나
 * "캐시를 쓴다" 같은 로직이 추가되어도 ViewModel 코드는 건드릴 필요가 없다는 장점이 있다.
 * 이런 계층 구조를 MVVM(Model-View-ViewModel) 아키텍처라고 부른다.
 */
class TodoRepository(private val dao: TodoDao) {

    val allTodos: Flow<List<TodoItem>> = dao.getAllTodos()

    fun getByCategory(category: Category): Flow<List<TodoItem>> =
        dao.getTodosByCategory(category)

    fun getWeeklySchedule(category: Category, days: List<Int>): Flow<List<TodoItem>> =
        dao.getWeeklySchedule(category, days)

    fun getTodayTodos(dayOfWeek: Int, dayStartMillis: Long, dayEndMillis: Long): Flow<List<TodoItem>> =
        dao.getTodayTodos(dayOfWeek, dayStartMillis, dayEndMillis)

    // getTodayTodos와 같은 쿼리지만, "오늘"이 아니라 임의의 날짜를 조회한다는 의도를 이름으로 드러낸다.
    fun getTodosForDate(dayOfWeek: Int, dayStartMillis: Long, dayEndMillis: Long): Flow<List<TodoItem>> =
        dao.getTodayTodos(dayOfWeek, dayStartMillis, dayEndMillis)

    suspend fun insertAll(todos: List<TodoItem>) = todos.forEach { dao.insert(it) }

    suspend fun getById(id: Long): TodoItem? = dao.getTodoById(id)

    suspend fun insert(todo: TodoItem): Long = dao.insert(todo)

    suspend fun update(todo: TodoItem) = dao.update(todo)

    suspend fun delete(todo: TodoItem) = dao.delete(todo)

    suspend fun toggleCompletion(id: Long, isCompleted: Boolean) =
        dao.updateCompletion(id, isCompleted)
}
