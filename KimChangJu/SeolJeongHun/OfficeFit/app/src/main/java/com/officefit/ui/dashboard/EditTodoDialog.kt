package com.officefit.ui.dashboard

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.officefit.data.local.Category
import com.officefit.data.local.TimeUtils
import com.officefit.data.local.TodoItem

/**
 * 할 일 행을 탭하면 뜨는 수정 다이얼로그. 제목/카테고리/시작 시각을 바꿀 수 있고,
 * "삭제" 버튼을 누르면 (여기서 바로 지우지 않고) [onDelete]로 알려서 호출한 쪽이
 * 삭제 확인 다이얼로그([DeleteTodoConfirmDialog])를 띄우도록 위임한다.
 */
@Composable
fun EditTodoDialog(
    todo: TodoItem,
    onDismiss: () -> Unit,
    onSave: (TodoItem) -> Unit,
    onDelete: (TodoItem) -> Unit
) {
    // remember(todo.id): todo.id가 바뀌면(=다른 항목을 열면) 입력값을 새로 초기화한다.
    var title by remember(todo.id) { mutableStateOf(todo.title) }
    var category by remember(todo.id) { mutableStateOf(todo.category) }
    var timeText by remember(todo.id) { mutableStateOf(TimeUtils.format(todo.targetTime)) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("할 일 수정") },
        text = {
            Column {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("내용") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(12.dp))
                Row {
                    Category.entries.forEach { c ->
                        FilterChip(
                            selected = category == c,
                            onClick = { category = c },
                            label = { Text(c.shortLabel()) },
                            modifier = Modifier.padding(end = 6.dp)
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = timeText,
                    onValueChange = { timeText = it },
                    label = { Text("시작 시각 (HH:MM)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(onClick = {
                // 사용자가 시각을 엉뚱한 형식으로 고쳐도 앱이 죽지 않도록, 파싱 실패 시 기존 값을 그대로 둔다.
                val parsedTime = runCatching { TimeUtils.parse(timeText) }.getOrDefault(todo.targetTime)
                onSave(todo.copy(title = title.trim(), category = category, targetTime = parsedTime))
            }) {
                Text("저장")
            }
        },
        dismissButton = {
            Row {
                TextButton(onClick = { onDelete(todo) }) { Text("삭제") }
                TextButton(onClick = onDismiss) { Text("취소") }
            }
        }
    )
}

/** "정말 삭제할까요?" 확인 다이얼로그. 실수로 지우는 것을 막기 위한 한 단계다. */
@Composable
fun DeleteTodoConfirmDialog(todo: TodoItem, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("정말 삭제할까요?") },
        text = { Text(todo.title) },
        confirmButton = { TextButton(onClick = onConfirm) { Text("삭제") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("취소") } }
    )
}

internal fun Category.shortLabel(): String = when (this) {
    Category.WORK -> "🏢 업무"
    Category.STUDY -> "📚 스터디"
    Category.ETC -> "📌 일반"
}
