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

/**
 * "+" 버튼으로 여는, 새 할 일을 직접 입력해 등록하는 다이얼로그. 음성 덤프는 항상 "오늘"에만
 * 저장되지만, 이 다이얼로그는 일자별 조회 화면에서 지금 보고 있는 날짜가 오늘이 아니어도
 * 그 날짜에 바로 등록할 수 있게 해준다 (실제 날짜 지정은 호출한 쪽의 onSave에서 처리).
 */
@Composable
fun AddTodoDialog(
    onDismiss: () -> Unit,
    onSave: (title: String, category: Category, hour: Int, minute: Int) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var category by remember { mutableStateOf(Category.WORK) }
    var timeText by remember { mutableStateOf("09:00") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("할 일 등록") },
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
            TextButton(
                onClick = {
                    val parts = timeText.split(":")
                    val hour = parts.getOrNull(0)?.toIntOrNull() ?: 9
                    val minute = parts.getOrNull(1)?.toIntOrNull() ?: 0
                    onSave(title.trim(), category, hour, minute)
                },
                enabled = title.isNotBlank()
            ) {
                Text("등록")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("취소") }
        }
    )
}
