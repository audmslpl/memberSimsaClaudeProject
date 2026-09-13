package com.officefit.ui.dashboard

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LargeFloatingActionButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.officefit.data.local.Category
import com.officefit.data.local.DateUtils
import com.officefit.data.local.TimeUtils
import com.officefit.data.local.TodoItem
import com.officefit.ui.voice.rememberMicrophonePermissionState
import com.officefit.viewmodel.MainViewModel

/**
 * 앱 첫 화면. 상단에 오늘 날짜, 중앙에 오늘의 할 일(카테고리별 그룹), 우측 하단에
 * 모닝 보이스 덤프를 시작하는 마이크 FAB을 배치한다.
 *
 * Jetpack Compose는 XML 레이아웃 대신 "함수 하나 = 화면 요소 하나"로 UI를 그리는 방식이다.
 * `@Composable` 함수 안에서 다른 `@Composable` 함수(Scaffold, Column, Text 등)를 호출하면
 * 그 요소가 화면에 나타난다. 상태(값)가 바뀌면 관련된 부분만 자동으로 다시 그려진다(recomposition).
 */
@Composable
fun MainDashboardScreen(
    viewModel: MainViewModel,
    onOpenDateList: () -> Unit,
    modifier: Modifier = Modifier
) {
    // collectAsState()는 ViewModel의 StateFlow를 Compose가 읽을 수 있는 State로 변환해 구독한다.
    // `by`를 쓰면 todayTodos.value 대신 todayTodos처럼 값 자체를 바로 쓸 수 있다(Kotlin의 위임 프로퍼티).
    val todayTodos by viewModel.todayTodos.collectAsState()
    val showDumpDialog by viewModel.showVoiceDumpDialog.collectAsState()

    // ModalBottomSheet의 닫힘 애니메이션이 끝날 때까지는 컴포지션에 남겨둔다.
    // remember { mutableStateOf(...) }: 이 화면이 다시 그려져도 값이 초기화되지 않도록 기억해두는 로컬 상태.
    var isDumpDialogMounted by remember { mutableStateOf(false) }
    // LaunchedEffect(key)는 key(여기선 showDumpDialog) 값이 바뀔 때마다 중괄호 안 코드를 한 번 실행하는
    // Compose의 부수효과(side-effect) 처리 도구다. "화면을 그리는 도중"이 아니라 "그려진 후 반응"이 필요할 때 쓴다.
    LaunchedEffect(showDumpDialog) {
        if (showDumpDialog) isDumpDialogMounted = true
    }

    val micPermission = rememberMicrophonePermissionState(
        onResult = { granted -> if (granted) viewModel.openVoiceDump() }
    )

    // 수정/삭제 다이얼로그 상태. null이 아니면 해당 다이얼로그가 화면 위에 뜬다.
    var editingTodo by remember { mutableStateOf<TodoItem?>(null) }
    var pendingDeleteTodo by remember { mutableStateOf<TodoItem?>(null) }

    // Scaffold는 Material Design의 "화면 기본 골격"(상단바/본문/플로팅 버튼 위치 등)을
    // 알아서 배치해주는 컨테이너 Composable이다. Modifier는 크기/패딩/색 등 "이 요소를 어떻게
    // 그릴지"에 대한 설정을 체이닝(.fillMaxSize().padding(...) 식으로 이어붙임) 방식으로 적용하는 객체다.
    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = { DashboardHeader(onOpenDateList = onOpenDateList) },
        floatingActionButton = {
            LargeFloatingActionButton(
                onClick = {
                    if (micPermission.hasPermission) viewModel.openVoiceDump()
                    else micPermission.requestPermission()
                },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                shape = CircleShape
            ) {
                Text(text = "🎤", fontSize = 30.sp)
            }
        }
    ) { paddingValues ->
        TodoListContent(
            todos = todayTodos,
            onToggle = viewModel::toggleCompletion,
            onEdit = { editingTodo = it },
            onDelete = { pendingDeleteTodo = it },
            emptyTitle = "아직 오늘 할 일이 없어요",
            emptySubtitle = "마이크 버튼을 눌러 오늘 할 일을 말해보세요",
            modifier = Modifier.padding(paddingValues)
        )
    }

    if (isDumpDialogMounted) {
        VoiceDumpDialog(
            viewModel = viewModel,
            onFullyDismissed = { isDumpDialogMounted = false }
        )
    }

    editingTodo?.let { todo ->
        EditTodoDialog(
            todo = todo,
            onDismiss = { editingTodo = null },
            onSave = { updated ->
                viewModel.updateTodo(updated)
                editingTodo = null
            },
            onDelete = {
                pendingDeleteTodo = it
                editingTodo = null
            }
        )
    }

    pendingDeleteTodo?.let { todo ->
        DeleteTodoConfirmDialog(
            todo = todo,
            onConfirm = {
                viewModel.deleteTodo(todo)
                pendingDeleteTodo = null
            },
            onDismiss = { pendingDeleteTodo = null }
        )
    }
}

@Composable
private fun DashboardHeader(onOpenDateList: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 20.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "OFFICEFIT",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            TextButton(onClick = onOpenDateList) {
                Text("📅 날짜별 보기")
            }
        }
        Spacer(Modifier.height(4.dp))
        Text(
            text = DateUtils.todayLabel(),
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )
        Text(
            text = "오늘도 가볍게 정리해볼까요?",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

/**
 * 카테고리별로 묶어 보여주는 할 일 목록. 대시보드(오늘)와 일자별 조회 화면이
 * 함께 사용하는 공용 컴포저블이라 이 파일 안에서 private으로 감싸지 않는다.
 */
@Composable
fun TodoListContent(
    todos: List<TodoItem>,
    onToggle: (Long, Boolean) -> Unit,
    onEdit: (TodoItem) -> Unit,
    onDelete: (TodoItem) -> Unit,
    emptyTitle: String,
    emptySubtitle: String,
    modifier: Modifier = Modifier
) {
    if (todos.isEmpty()) {
        EmptyTodoState(title = emptyTitle, subtitle = emptySubtitle, modifier = modifier.fillMaxSize())
        return
    }

    val grouped = todos.groupBy { it.category }

    // LazyColumn은 스크롤 가능한 목록으로, 안드로이드 예전 방식의 RecyclerView에 해당한다.
    // "Lazy"라는 이름처럼 화면에 실제로 보이는 항목만 그려서 목록이 길어도 성능이 유지된다.
    // item{}은 항목 하나(여기서는 카테고리 제목), items(list){}은 리스트 전체를 하나씩 그려주는 블록이다.
    // key = { it.id }를 주면 Compose가 "어느 데이터가 어느 화면 요소인지" 정확히 추적해서
    // 목록이 바뀔 때 불필요한 재구성을 줄여준다.
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Category.entries.filter { grouped.containsKey(it) }.forEach { category ->
            item(key = "header_${category.name}") {
                Text(
                    text = category.sectionTitle(),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onBackground,
                    modifier = Modifier.padding(top = 8.dp, bottom = 2.dp)
                )
            }
            items(grouped.getValue(category), key = { it.id }) { todo ->
                TodoRow(todo = todo, onToggle = onToggle, onEdit = onEdit, onDelete = onDelete)
            }
        }
    }
}

@Composable
private fun TodoRow(
    todo: TodoItem,
    onToggle: (Long, Boolean) -> Unit,
    onEdit: (TodoItem) -> Unit,
    onDelete: (TodoItem) -> Unit
) {
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
        // 행 전체를 탭하면 수정 다이얼로그가 뜬다. 체크박스/삭제 버튼은 각자 자기 클릭을
        // 먼저 처리하므로(Compose의 중첩 clickable 우선순위), 이 클릭과 겹치지 않는다.
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onEdit(todo) }
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 8.dp)
        ) {
            Checkbox(
                checked = todo.isCompleted,
                onCheckedChange = { checked -> onToggle(todo.id, checked) }
            )
            Spacer(Modifier.width(2.dp))
            if (todo.targetTime > 0) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Text(
                        text = TimeUtils.format(todo.targetTime),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
                Spacer(Modifier.width(8.dp))
            }
            Text(
                text = todo.title,
                style = MaterialTheme.typography.bodyLarge,
                textDecoration = if (todo.isCompleted) TextDecoration.LineThrough else TextDecoration.None,
                color = if (todo.isCompleted) {
                    MaterialTheme.colorScheme.onSurfaceVariant
                } else {
                    MaterialTheme.colorScheme.onSurface
                },
                modifier = Modifier.weight(1f)
            )
            Spacer(Modifier.width(4.dp))
            Text(
                text = "🗑",
                fontSize = 18.sp,
                modifier = Modifier
                    .clickable { onDelete(todo) }
                    .padding(6.dp)
            )
        }
    }
}

@Composable
private fun EmptyTodoState(title: String, subtitle: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "📭", fontSize = 40.sp)
        Spacer(Modifier.height(8.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onBackground
        )
        Text(
            text = subtitle,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

private fun Category.sectionTitle(): String = when (this) {
    Category.WORK -> "🏢 사내 업무"
    Category.STUDY -> "📚 개인 스터디/성장"
    Category.ETC -> "📌 일반 할 일"
}
