package com.officefit.ui.dashboard

import android.app.DatePickerDialog
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.LargeFloatingActionButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.officefit.data.local.DateUtils
import com.officefit.data.local.TodoItem
import com.officefit.ui.voice.rememberMicrophonePermissionState
import com.officefit.viewmodel.MainViewModel
import java.util.Calendar

/**
 * 원하는 날짜를 골라 그 날의 할 일을 확인하는 화면. 오늘을 보고 있을 때는 음성 덤프(🎤)로,
 * 다른 날짜를 보고 있을 때는 "+" 수동 등록으로 그 날짜에 할 일을 추가할 수 있다.
 * 목록/수정/삭제 UI는 대시보드와 같은 [TodoListContent]/[EditTodoDialog]/[DeleteTodoConfirmDialog]를
 * 그대로 재사용한다.
 */
@Composable
fun DateTodoListScreen(viewModel: MainViewModel, onBack: () -> Unit, modifier: Modifier = Modifier) {
    val selectedDate by viewModel.selectedDate.collectAsState()
    val todos by viewModel.selectedDateTodos.collectAsState()
    val context = LocalContext.current
    val isToday = selectedDate == DateUtils.today()

    var editingTodo by remember { mutableStateOf<TodoItem?>(null) }
    var pendingDeleteTodo by remember { mutableStateOf<TodoItem?>(null) }
    var showAddDialog by remember { mutableStateOf(false) }

    // 시스템 뒤로가기(버튼/제스처)로 이 화면을 나갈 때는 다음에 다시 들어와도 항상 오늘부터
    // 시작하도록 선택 날짜를 리셋한다. 화면 안의 "오늘로" 버튼은 이 동작과 분리되어 있어서
    // (아래 참고) 화면을 나가지 않고 날짜만 오늘로 돌아올 수 있다.
    BackHandler {
        viewModel.selectDate(DateUtils.today())
        onBack()
    }

    val showDumpDialog by viewModel.showVoiceDumpDialog.collectAsState()
    var isDumpDialogMounted by remember { mutableStateOf(false) }
    LaunchedEffect(showDumpDialog) {
        if (showDumpDialog) isDumpDialogMounted = true
    }
    val micPermission = rememberMicrophonePermissionState(
        onResult = { granted -> if (granted) viewModel.openVoiceDump() }
    )

    Scaffold(
        modifier = modifier,
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
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
                    // 이미 오늘을 보고 있으면 "오늘로 돌아가기"는 의미가 없으므로 숨긴다.
                    // 이 버튼은 화면을 나가지 않고 날짜만 오늘로 바꾼다 (화면 나가기는 시스템 뒤로가기 담당).
                    if (isToday) {
                        // 자리만 차지하는 빈 컴포저블. Row의 두 자식(왼쪽/오른쪽) 배치를 유지해
                        // "📅 날짜 선택" 버튼이 계속 오른쪽 끝에 붙어 있게 한다.
                        Spacer(modifier = Modifier)
                    } else {
                        TextButton(onClick = { viewModel.selectDate(DateUtils.today()) }) {
                            Text("← 오늘로")
                        }
                    }
                    TextButton(onClick = {
                        showDatePicker(context, selectedDate) { picked -> viewModel.selectDate(picked) }
                    }) {
                        Text("📅 날짜 선택")
                    }
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    text = DateUtils.labelOf(selectedDate),
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )
            }
        },
        floatingActionButton = {
            Column(horizontalAlignment = Alignment.End) {
                FloatingActionButton(onClick = { showAddDialog = true }) {
                    Text(text = "➕", fontSize = 22.sp)
                }
                // 음성 덤프는 항상 "오늘"에 저장되므로, 오늘을 보고 있을 때만 마이크 버튼을 보여준다.
                if (isToday) {
                    Spacer(Modifier.height(12.dp))
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
            }
        }
    ) { paddingValues ->
        TodoListContent(
            todos = todos,
            onToggle = viewModel::toggleCompletion,
            onEdit = { editingTodo = it },
            onDelete = { pendingDeleteTodo = it },
            emptyTitle = if (isToday) "아직 오늘 할 일이 없어요" else "이 날은 할 일이 없어요",
            emptySubtitle = if (isToday) "🎤 또는 ➕ 버튼으로 할 일을 추가해보세요" else "➕ 버튼으로 이 날짜에 할 일을 등록해보세요",
            modifier = Modifier.padding(paddingValues)
        )
    }

    if (isDumpDialogMounted) {
        VoiceDumpDialog(
            viewModel = viewModel,
            onFullyDismissed = { isDumpDialogMounted = false }
        )
    }

    if (showAddDialog) {
        AddTodoDialog(
            onDismiss = { showAddDialog = false },
            onSave = { title, category, hour, minute ->
                viewModel.addTodoForDate(selectedDate, title, category, hour, minute)
                showAddDialog = false
            }
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

private fun showDatePicker(
    context: android.content.Context,
    current: DateUtils.DateKey,
    onPicked: (DateUtils.DateKey) -> Unit
) {
    val calendar = Calendar.getInstance().apply {
        set(Calendar.YEAR, current.year)
        set(Calendar.MONTH, current.month - 1)
        set(Calendar.DAY_OF_MONTH, current.dayOfMonth)
    }
    DatePickerDialog(
        context,
        { _, year, month, dayOfMonth -> onPicked(DateUtils.DateKey(year, month + 1, dayOfMonth)) },
        calendar.get(Calendar.YEAR),
        calendar.get(Calendar.MONTH),
        calendar.get(Calendar.DAY_OF_MONTH)
    ).show()
}
