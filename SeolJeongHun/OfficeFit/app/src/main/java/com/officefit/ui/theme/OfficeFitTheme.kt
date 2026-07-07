package com.officefit.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * Material 3(구글의 디자인 시스템)의 색상 팔레트를 이 앱 전용으로 정의하는 파일이다.
 * `Color(0xFF6C63FF)`처럼 0xAARRGGBB(투명도-빨강-초록-파랑) 16진수로 색을 표현한다.
 * `darkColorScheme`/`lightColorScheme`은 Material3가 제공하는 "이 앱의 버튼/배경/글자 등에
 * 어떤 색을 쓸지"를 한 번에 정의하는 함수이고, 아래 `OfficeFitTheme`이 이 팔레트를 화면 전체에 적용한다.
 */
private val Indigo = Color(0xFF6C63FF)
private val Amber = Color(0xFFFFB74D)

private val OfficeFitDarkColors = darkColorScheme(
    primary = Indigo,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF3A3564),
    onPrimaryContainer = Color(0xFFD8D4FF),
    secondary = Amber,
    onSecondary = Color(0xFF1C1C24),
    background = Color(0xFF121218),
    onBackground = Color(0xFFEDEDF2),
    surface = Color(0xFF1C1C24),
    onSurface = Color(0xFFEDEDF2),
    surfaceVariant = Color(0xFF2A2A34),
    onSurfaceVariant = Color(0xFFB8B8C4),
    error = Color(0xFFFF6B6B)
)

private val OfficeFitLightColors = lightColorScheme(
    primary = Indigo,
    onPrimary = Color.White,
    secondary = Amber,
    background = Color(0xFFF7F7FA),
    surface = Color.White
)

/**
 * 프로젝트 기본값은 다크모드. 오피스 생산성 툴 느낌의 인디고/앰버 액센트 팔레트.
 * 사용법: `MainActivity`에서 `setContent { OfficeFitTheme { 실제_화면_내용() } }`처럼
 * 모든 화면을 이 함수로 한 번 감싸주면, 그 안의 모든 Composable이 이 색상 테마를 물려받는다.
 * `content: @Composable () -> Unit` 파라미터는 "다른 Composable 내용을 통째로 받아서
 * 그 자리에 그대로 그려주는" 슬롯이라고 생각하면 된다.
 */
@Composable
fun OfficeFitTheme(
    darkTheme: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) OfficeFitDarkColors else OfficeFitLightColors
    MaterialTheme(colorScheme = colorScheme, content = content)
}
