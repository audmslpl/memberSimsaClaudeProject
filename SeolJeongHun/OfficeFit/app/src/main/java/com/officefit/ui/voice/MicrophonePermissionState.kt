package com.officefit.ui.voice

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat

/**
 * RECORD_AUDIO 런타임 권한 상태와 요청 동작을 함께 들고 있는 홀더.
 * 마이크 권한처럼 "위험 권한(dangerous permission)"은 앱 설치 시 자동으로 주어지지 않고,
 * 앱이 실행 중일 때 사용자에게 직접 물어봐야 한다 (이를 "런타임 권한 요청"이라 한다).
 */
class MicrophonePermissionState internal constructor(
    granted: Boolean,
    permanentlyDenied: Boolean,
    private val launchRequest: () -> Unit
) {
    // `by mutableStateOf(...)`는 Jetpack Compose의 핵심 기법이다: 이 값이 바뀌면
    // 이 값을 읽고 있던 Composable 함수(화면)가 자동으로 다시 그려진다(recomposition).
    // `internal set`은 이 값을 이 모듈 내부에서만 변경할 수 있게 제한한다(외부에서는 읽기만 가능).
    var hasPermission by mutableStateOf(granted)
        internal set

    /** 사용자가 "다시 묻지 않음"과 함께 거부해 시스템 다이얼로그가 더 안 뜨는 상태 */
    var isPermanentlyDenied by mutableStateOf(permanentlyDenied)
        internal set

    fun requestPermission() = launchRequest()
}

/**
 * RECORD_AUDIO 권한 확인 + 요청 로직을 Compose 화면에서 쓰기 좋게 감싼 훅.
 *
 * 사용 예:
 * ```
 * val micPermission = rememberMicrophonePermissionState()
 * Button(onClick = {
 *     if (micPermission.hasPermission) manager.startDump()
 *     else micPermission.requestPermission()
 * }) { Text("오늘 할 일 말하기") }
 * ```
 */
// @Composable은 "이 함수가 Compose 화면(UI)의 일부를 그리거나, 화면에서 쓰는 상태를 관리하는
// 특수한 함수"임을 표시한다. 이런 함수를 관례상 "훅(hook)"이라 부르기도 한다.
@Composable
fun rememberMicrophonePermissionState(
    onResult: (granted: Boolean) -> Unit = {}
): MicrophonePermissionState {
    // LocalContext.current: 지금 이 화면이 속한 안드로이드 Context(시스템 서비스 접근 통로)를 가져온다.
    val context = LocalContext.current

    // remember{}는 Composable이 다시 그려져도(recomposition) 값을 기억해 매번 새로 계산하지 않게 해준다.
    // rememberSaveable{}은 한 걸음 더 나아가, 화면 회전처럼 Activity가 재생성돼도 값을 유지한다.
    var hasPermission by rememberSaveable {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED
        )
    }
    var isPermanentlyDenied by rememberSaveable { mutableStateOf(false) }

    // rememberLauncherForActivityResult: 안드로이드 시스템 권한 요청 팝업을 띄우고,
    // 사용자가 허용/거부를 선택한 뒤 그 결과를 콜백(중괄호 안)으로 받는 Compose 표준 방법이다.
    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasPermission = granted
        if (!granted) {
            // 두 번째 이후 거부 시 시스템이 더 이상 rationale을 보여주지 않는 것으로
            // "다시 묻지 않음"을 유추한다. 이 값이 true면 설정 화면 유도 UI로 전환.
            isPermanentlyDenied = context is android.app.Activity &&
                !context.shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO)
        }
        onResult(granted)
    }

    return remember(hasPermission, isPermanentlyDenied) {
        MicrophonePermissionState(
            granted = hasPermission,
            permanentlyDenied = isPermanentlyDenied,
            launchRequest = { launcher.launch(Manifest.permission.RECORD_AUDIO) }
        )
    }
}
