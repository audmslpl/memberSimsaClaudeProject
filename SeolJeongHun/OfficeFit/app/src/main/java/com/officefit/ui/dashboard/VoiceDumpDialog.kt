package com.officefit.ui.dashboard

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.BottomSheetDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.officefit.viewmodel.MainViewModel
import com.officefit.viewmodel.VoiceDumpStage
import com.officefit.voice.SmartTextParser
import com.officefit.voice.VoiceRecognitionState

/**
 * 마이크 FAB을 누르면 뜨는 바텀 시트. LISTENING 단계에서는 실시간 인식 텍스트와
 * 파동 애니메이션을, PREVIEW 단계에서는 SmartTextParser가 정리한 마크다운을
 * 직접 수정 가능한 형태로 보여준다.
 */
// ModalBottomSheet 등 일부 Material3 API는 아직 "실험적(Experimental)" 딱지가 붙어 있어서,
// 이를 사용하려면 "이 API가 나중에 바뀔 수 있음을 인지했다"는 표시로 @OptIn을 명시해야 한다.
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoiceDumpDialog(viewModel: MainViewModel, onFullyDismissed: () -> Unit) {
    val stage by viewModel.dumpStage.collectAsState()
    val showDialog by viewModel.showVoiceDumpDialog.collectAsState()
    // 바텀 시트(화면 아래에서 올라오는 패널)의 열림/닫힘 애니메이션 상태를 관리하는 객체.
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    // ViewModel의 showDialog 플래그는 즉시 false가 되지만, 시트가 닫히는 애니메이션은 시간이 걸린다.
    // 그래서 sheetState.hide()로 애니메이션이 끝나길 기다린 뒤에야 onFullyDismissed()를 불러
    // 부모(MainDashboardScreen)에게 "이제 이 다이얼로그를 화면에서 완전히 빼도 된다"고 알려준다.
    LaunchedEffect(showDialog) {
        if (!showDialog) {
            sheetState.hide()
            onFullyDismissed()
        }
    }

    ModalBottomSheet(
        onDismissRequest = { viewModel.cancelVoiceDump() },
        sheetState = sheetState,
        containerColor = MaterialTheme.colorScheme.surface,
        dragHandle = { BottomSheetDefaults.DragHandle() }
    ) {
        Box(modifier = Modifier.defaultMinSize(minHeight = 320.dp)) {
            when (stage) {
                VoiceDumpStage.LISTENING -> ListeningStageContent(viewModel)
                VoiceDumpStage.PREVIEW -> PreviewStageContent(viewModel)
            }
        }
    }
}

@Composable
private fun ListeningStageContent(viewModel: MainViewModel) {
    val voiceState by viewModel.voiceState.collectAsState()
    val partialText by viewModel.partialVoiceText.collectAsState()
    val recognizedText by viewModel.recognizedVoiceText.collectAsState()
    val amplitude by viewModel.voiceAmplitude.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "오늘 할 일을 편하게 말해보세요",
            style = MaterialTheme.typography.titleMedium
        )

        Spacer(Modifier.height(8.dp))

        SpeakingTemplateHint()

        Spacer(Modifier.height(16.dp))

        PulsingMicIndicator(
            amplitude = amplitude,
            isListening = voiceState is VoiceRecognitionState.Listening
        )

        Spacer(Modifier.height(24.dp))

        val displayText = when {
            recognizedText.isNotBlank() && partialText.isNotBlank() -> "$recognizedText $partialText"
            recognizedText.isNotBlank() -> recognizedText
            partialText.isNotBlank() -> partialText
            else -> "듣고 있어요..."
        }
        Text(
            text = displayText,
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = if (recognizedText.isBlank() && partialText.isBlank()) {
                MaterialTheme.colorScheme.onSurfaceVariant
            } else {
                MaterialTheme.colorScheme.onSurface
            },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 72.dp)
        )

        (voiceState as? VoiceRecognitionState.Error)?.let { error ->
            Spacer(Modifier.height(8.dp))
            Text(
                text = error.message,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall
            )
        }

        Spacer(Modifier.height(24.dp))

        Button(
            onClick = { viewModel.finishListeningAndPreview() },
            modifier = Modifier.fillMaxWidth(),
            enabled = recognizedText.isNotBlank() || partialText.isNotBlank()
        ) {
            Text("완료 및 정리하기")
        }
        Spacer(Modifier.height(4.dp))
        TextButton(
            onClick = { viewModel.cancelVoiceDump() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("취소")
        }
        Spacer(Modifier.height(12.dp))
    }
}

// 음성 인식이 정확하지 않다는 피드백에 따라 추가한 안내 카드. 기본은 접혀 있고,
// 눌러서 펼치면 SmartTextParser가 실제로 인식하는 규칙(절 구분자/시간 표현/카테고리
// 키워드)을 그대로 반영한 예시 문장과 팁을 보여준다. 안내 문구가 파서 로직과
// 어긋나지 않도록 키워드는 SmartTextParser.workKeywordExamples/studyKeywordExamples를
// 그대로 가져다 쓴다.
@Composable
private fun SpeakingTemplateHint() {
    var expanded by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxWidth()) {
        TextButton(onClick = { expanded = !expanded }) {
            Text(if (expanded) "💡 말하기 예시 접기 ▲" else "💡 이렇게 말하면 더 정확해요 ▼")
        }

        AnimatedVisibility(visible = expanded) {
            Surface(
                shape = MaterialTheme.shapes.medium,
                color = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "\"오전 10시에 팀 회의 하고, SQL 코드 검토하고, 오후 3시에 스터디 문서 읽기\"",
                        style = MaterialTheme.typography.bodyMedium,
                        fontStyle = FontStyle.Italic
                    )
                    Spacer(Modifier.height(12.dp))
                    HintLine("\"그리고\" 또는 \"~하고\"로 할 일을 하나씩 끊어서 말해주세요")
                    HintLine("시간은 \"오후 2시\", \"저녁 7시 30분\"처럼 숫자 + \"시\"로 말해주세요")
                    HintLine(
                        "업무(${SmartTextParser.workKeywordExamples.joinToString(", ")} 등) / " +
                            "스터디(${SmartTextParser.studyKeywordExamples.joinToString(", ")} 등) " +
                            "단어가 들어가면 자동으로 분류돼요"
                    )
                }
            }
        }
    }
}

@Composable
private fun HintLine(text: String) {
    Text(
        text = "• $text",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(top = 4.dp)
    )
}

// 마이크 버튼 주변에 퍼지는 "파동" 애니메이션. rememberInfiniteTransition + animateFloat 조합은
// Compose에서 "값이 A↔B 사이를 계속 반복해서 왔다갔다 하게" 만드는 표준 패턴이다.
@Composable
private fun PulsingMicIndicator(amplitude: Float, isListening: Boolean) {
    val infiniteTransition = rememberInfiniteTransition(label = "mic-pulse")
    val basePulse by infiniteTransition.animateFloat(
        initialValue = 0.9f,
        targetValue = 1.15f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "base-pulse"
    )

    // SpeechRecognizer의 rmsdB는 대략 0~10 범위로 들어온다. 0~1로 정규화해 파동 크기에 반영.
    val amplitudeScale by animateFloatAsState(
        targetValue = 1f + (amplitude / 10f).coerceIn(0f, 1f) * 0.6f,
        animationSpec = tween(120),
        label = "amplitude-scale"
    )

    val ringColor = MaterialTheme.colorScheme.primary

    Box(modifier = Modifier.size(140.dp), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(140.dp)) {
            if (isListening) {
                val radius = size.minDimension / 2f
                drawCircle(
                    color = ringColor.copy(alpha = 0.15f),
                    radius = radius * basePulse * amplitudeScale,
                    center = center
                )
                drawCircle(
                    color = ringColor.copy(alpha = 0.25f),
                    radius = radius * 0.7f * amplitudeScale,
                    center = center
                )
            }
        }
        Surface(
            shape = CircleShape,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(72.dp)
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
                Text(text = "🎤", fontSize = 30.sp)
            }
        }
    }
}

@Composable
private fun PreviewStageContent(viewModel: MainViewModel) {
    val previewMarkdown by viewModel.previewMarkdown.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 8.dp)
    ) {
        Text(
            text = "정리된 오늘의 할 일",
            style = MaterialTheme.typography.titleMedium
        )
        Text(
            text = "내용을 눌러 직접 수정할 수 있어요",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(16.dp))

        OutlinedTextField(
            value = previewMarkdown,
            onValueChange = { viewModel.updatePreviewMarkdown(it) },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 200.dp, max = 360.dp)
                .verticalScroll(rememberScrollState()),
            textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace),
            placeholder = { Text("인식된 할 일이 여기에 표시됩니다") }
        )

        Spacer(Modifier.height(20.dp))

        Button(
            onClick = { viewModel.saveJournalEntry() },
            modifier = Modifier.fillMaxWidth(),
            enabled = previewMarkdown.isNotBlank()
        ) {
            Text("일지 저장")
        }
        Spacer(Modifier.height(4.dp))
        TextButton(
            onClick = { viewModel.cancelVoiceDump() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("취소")
        }
        Spacer(Modifier.height(12.dp))
    }
}
