package com.officefit.voice

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

/**
 * "모닝 보이스 덤프" 전용 연속 음성 인식 매니저.
 *
 * 안드로이드 [SpeechRecognizer]는 사용자가 잠시 말을 멈추면 onEndOfSpeech/onResults를
 * 호출하며 세션을 끝내버린다. 사용자가 여러 할 일을 끊어 말하는 시나리오에서는
 * 세션이 끝날 때마다 자동으로 재시작(startListening)하고, 그때까지 인식된 텍스트를
 * 계속 이어 붙이는 방식으로 "연속 인식"처럼 보이게 한다. [stopDump]가 호출되기
 * 전까지는 오류/무음 타임아웃이 발생해도 계속 재시작한다.
 *
 * SpeechRecognizer는 반드시 메인 스레드에서 생성/조작해야 하므로 내부적으로
 * 모든 호출을 메인 [Handler]를 통해 실행한다.
 */
class VoiceRecognitionManager(private val appContext: Context) {

    companion object {
        const val ERROR_CODE_NO_PERMISSION = -1
        const val ERROR_CODE_UNAVAILABLE = -2

        // 사용자가 말 사이에 잠깐 침묵해도 세션이 바로 끊기지 않도록 기본값보다
        // 여유 있게 잡은 무음 판단 기준(ms). 그래도 끊기면 restartListening()이
        // 이어서 세션을 새로 열어준다.
        private const val COMPLETE_SILENCE_MS = 2500L
        private const val POSSIBLY_COMPLETE_SILENCE_MS = 1500L
        private const val MIN_INPUT_LENGTH_MS = 15000L

        private const val RESTART_DELAY_MS = 150L
        private const val BUSY_RETRY_DELAY_MS = 400L
    }

    // Handler(Looper.getMainLooper())는 "이 안드로이드 앱의 메인(화면) 스레드에서 코드를 실행해라"는
    // 예약 도구다. 코루틴을 안 쓰고도 특정 시점에 메인 스레드에서 작업을 실행하거나(post),
    // 지연 실행(postDelayed)할 때 사용한다. SpeechRecognizer는 메인 스레드에서만 안전하게 다룰 수 있어서
    // 이 매니저의 모든 recognizer 호출은 반드시 mainHandler를 거친다.
    private val mainHandler = Handler(Looper.getMainLooper())
    private val textBuilder = StringBuilder()

    @Volatile
    private var isDumpActive = false

    private var speechRecognizer: SpeechRecognizer? = null

    private val _state = MutableStateFlow<VoiceRecognitionState>(VoiceRecognitionState.Idle)
    val state: StateFlow<VoiceRecognitionState> = _state.asStateFlow()

    /** 세션들을 이어붙인, 지금까지 확정된 전체 인식 텍스트 */
    private val _recognizedText = MutableStateFlow("")
    val recognizedText: StateFlow<String> = _recognizedText.asStateFlow()

    /** 현재 세션에서 말하는 중인 실시간 중간 인식 결과 (UI 피드백용) */
    private val _partialText = MutableStateFlow("")
    val partialText: StateFlow<String> = _partialText.asStateFlow()

    /** 마이크 입력 음량(dB, 대략 0~10 범위). 파동/펄스 애니메이션 구동용 */
    private val _amplitude = MutableStateFlow(0f)
    val amplitude: StateFlow<Float> = _amplitude.asStateFlow()

    fun hasMicrophonePermission(): Boolean =
        ContextCompat.checkSelfPermission(
            appContext,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

    /** API 31+ 기기 내 온디바이스 인식기가 실제로 사용 가능한지 여부 */
    fun isOnDeviceRecognitionAvailable(): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            SpeechRecognizer.isOnDeviceRecognitionAvailable(appContext)

    /** 마이크 버튼을 눌러 "오늘 할 일 말하기"를 시작 */
    fun startDump() {
        if (isDumpActive) return

        if (!hasMicrophonePermission()) {
            _state.value = VoiceRecognitionState.Error("마이크 권한이 없습니다.", ERROR_CODE_NO_PERMISSION)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(appContext)) {
            _state.value = VoiceRecognitionState.Error(
                "이 기기에서는 음성 인식을 사용할 수 없습니다.",
                ERROR_CODE_UNAVAILABLE
            )
            return
        }

        isDumpActive = true
        textBuilder.clear()
        _recognizedText.value = ""
        _partialText.value = ""

        mainHandler.post { startNewSession() }
    }

    /** 사용자가 마이크 버튼을 다시 눌러 덤프를 종료 */
    fun stopDump() {
        if (!isDumpActive) return
        isDumpActive = false

        mainHandler.post {
            mainHandler.removeCallbacksAndMessages(null)
            speechRecognizer?.stopListening()
            releaseRecognizer()
            _partialText.value = ""
            _amplitude.value = 0f
            _state.value = VoiceRecognitionState.Idle
        }
    }

    /** 화면/뷰모델이 사라질 때 반드시 호출해 SpeechRecognizer 리소스를 해제 */
    fun release() {
        isDumpActive = false
        mainHandler.removeCallbacksAndMessages(null)
        mainHandler.post { releaseRecognizer() }
    }

    private fun startNewSession() {
        releaseRecognizer()

        val recognizer = if (isOnDeviceRecognitionAvailable()) {
            SpeechRecognizer.createOnDeviceSpeechRecognizer(appContext)
        } else {
            SpeechRecognizer.createSpeechRecognizer(appContext)
        }
        recognizer.setRecognitionListener(recognitionListener)
        speechRecognizer = recognizer

        recognizer.startListening(buildRecognizerIntent())
    }

    private fun restartSession(delayMs: Long = RESTART_DELAY_MS) {
        mainHandler.postDelayed({
            if (!isDumpActive) return@postDelayed
            _partialText.value = ""
            _amplitude.value = 0f
            val recognizer = speechRecognizer
            if (recognizer != null) {
                recognizer.startListening(buildRecognizerIntent())
            } else {
                startNewSession()
            }
        }, delayMs)
    }

    private fun buildRecognizerIntent() =
        android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, appContext.packageName)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            // 인터넷 연결이 있어도 기기 내 오프라인 엔진을 우선 사용하도록 요청
            // (createOnDeviceSpeechRecognizer를 못 쓰는 API 30 이하 대비)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS,
                COMPLETE_SILENCE_MS
            )
            putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS,
                POSSIBLY_COMPLETE_SILENCE_MS
            )
            putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS,
                MIN_INPUT_LENGTH_MS
            )
        }

    private fun appendRecognizedSegment(segment: String) {
        val trimmed = segment.trim()
        if (trimmed.isEmpty()) return
        if (textBuilder.isNotEmpty()) textBuilder.append(' ')
        textBuilder.append(trimmed)
        _recognizedText.value = textBuilder.toString()
    }

    private fun releaseRecognizer() {
        speechRecognizer?.apply {
            setRecognitionListener(null)
            destroy()
        }
        speechRecognizer = null
    }

    private fun errorMessage(code: Int): String = when (code) {
        SpeechRecognizer.ERROR_AUDIO -> "오디오 녹음 중 오류가 발생했습니다."
        SpeechRecognizer.ERROR_CLIENT -> "음성 인식 클라이언트 오류가 발생했습니다."
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "마이크 권한이 필요합니다."
        SpeechRecognizer.ERROR_NETWORK -> "네트워크 오류가 발생했습니다."
        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "네트워크 응답 시간이 초과되었습니다."
        SpeechRecognizer.ERROR_NO_MATCH -> "인식된 음성이 없습니다."
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "음성 인식기가 사용 중입니다."
        SpeechRecognizer.ERROR_SERVER -> "서버 오류가 발생했습니다."
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "말이 감지되지 않았습니다."
        else -> "알 수 없는 오류가 발생했습니다. (코드 $code)"
    }

    // RecognitionListener는 안드로이드 SpeechRecognizer가 진행 상황을 알려주는 콜백 인터페이스다.
    // "object : RecognitionListener { ... }"는 이 인터페이스를 구현하는 이름 없는(익명) 객체를 즉석에서
    // 만드는 Kotlin 문법이다. 아래 각 override 함수는 SpeechRecognizer가 특정 이벤트가 생길 때마다
    // 자동으로 호출해주는 콜백이며, Bundle은 안드로이드에서 여러 종류의 데이터를 하나로 묶어 전달하는 상자다.
    private val recognitionListener = object : RecognitionListener {
        // 마이크가 듣기 시작할 준비가 됐을 때 호출
        override fun onReadyForSpeech(params: Bundle?) {
            _state.value = VoiceRecognitionState.Listening
        }

        override fun onBeginningOfSpeech() {
            _state.value = VoiceRecognitionState.Listening
        }

        override fun onRmsChanged(rmsdB: Float) {
            _amplitude.value = rmsdB.coerceAtLeast(0f)
        }

        override fun onBufferReceived(buffer: ByteArray?) = Unit

        override fun onEndOfSpeech() {
            _amplitude.value = 0f
            _state.value = VoiceRecognitionState.Processing
        }

        override fun onError(error: Int) {
            when (error) {
                // 침묵 타임아웃/무매칭은 "덤프 종료"가 아니라 "다음 문장을 기다림"을
                // 의미하므로, 활성 상태라면 조용히 새 세션을 열어 계속 듣는다.
                SpeechRecognizer.ERROR_NO_MATCH,
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> {
                    if (isDumpActive) {
                        restartSession()
                    } else {
                        _state.value = VoiceRecognitionState.Idle
                    }
                }

                // 이전 세션 종료 직후 재시작 타이밍이 겹쳐 발생하는 일시적 오류이므로
                // 약간의 지연 후 재시도한다.
                SpeechRecognizer.ERROR_CLIENT,
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> {
                    if (isDumpActive) restartSession(BUSY_RETRY_DELAY_MS)
                }

                else -> {
                    isDumpActive = false
                    releaseRecognizer()
                    _state.value = VoiceRecognitionState.Error(errorMessage(error), error)
                }
            }
        }

        override fun onResults(results: Bundle?) {
            val text = results
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                .orEmpty()
            appendRecognizedSegment(text)

            if (isDumpActive) {
                restartSession()
            } else {
                _state.value = VoiceRecognitionState.Idle
            }
        }

        override fun onPartialResults(partialResults: Bundle?) {
            _partialText.value = partialResults
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                .orEmpty()
        }

        override fun onEvent(eventType: Int, params: Bundle?) = Unit
    }
}
