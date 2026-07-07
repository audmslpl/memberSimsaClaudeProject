package com.officefit.voice

/**
 * VoiceRecognitionManager가 방출하는 인식 진행 상태.
 * `sealed interface`는 "이 타입이 될 수 있는 경우의 수를 여기 적힌 것들로 제한"하는 Kotlin 기능이다.
 * 일반 enum과 달리 각 경우가 서로 다른 데이터(Error는 message/code)를 가질 수 있다는 게 장점이고,
 * `when (state) { ... }`로 분기 처리할 때 컴파일러가 "모든 경우를 다 처리했는지" 검사해준다.
 * `data object`는 데이터를 안 갖는 단일 인스턴스(Idle, Listening, Processing)에 쓰는 표기법이고,
 * `data class`는 값을 갖는 경우(Error)에 쓴다.
 */
sealed interface VoiceRecognitionState {
    data object Idle : VoiceRecognitionState        // 아무 것도 안 하고 있는 초기 상태
    data object Listening : VoiceRecognitionState    // 마이크로 음성을 듣고 있는 중
    data object Processing : VoiceRecognitionState   // 들은 음성을 텍스트로 변환 처리 중
    data class Error(val message: String, val code: Int) : VoiceRecognitionState // 인식 실패
}
