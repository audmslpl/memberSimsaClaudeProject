package com.officefit

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.officefit.ui.dashboard.DateTodoListScreen
import com.officefit.ui.dashboard.MainDashboardScreen
import com.officefit.ui.theme.OfficeFitTheme
import com.officefit.viewmodel.MainViewModel
import com.officefit.viewmodel.MainViewModelFactory

/**
 * 이 앱의 유일한 화면 진입점(Activity)이다. 안드로이드에서 "Activity"는 사용자가 실제로 보고
 * 조작하는 화면 하나의 단위이며, 앱이 실행되면 `AndroidManifest.xml`에서 launcher로 지정된
 * Activity(바로 이 MainActivity)의 `onCreate()`가 시스템에 의해 자동으로 호출된다.
 * `ComponentActivity`는 Compose를 쓰기 위한 최소한의 기반 Activity 클래스다.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // application은 이 Activity가 속한 전역 Application 객체(OfficeFitApplication.kt 참고)를 가리킨다.
        // 그 안에 미리 만들어둔 DB/Repository를 그대로 재사용하기 위해 형변환(as)해서 꺼낸다.
        val app = application as OfficeFitApplication

        // setContent { ... }는 "이 Activity의 화면을 Compose로 그리겠다"는 선언이다.
        // 전통적인 XML 레이아웃(setContentView) 대신 Compose 함수 호출만으로 화면 전체가 구성된다.
        setContent {
            OfficeFitTheme {
                // viewModel<MainViewModel>(factory = ...): Compose에서 ViewModel 인스턴스를 얻는 표준 방법.
                // 화면이 다시 그려져도(recomposition) 같은 ViewModel 인스턴스가 재사용된다.
                val viewModel = viewModel<MainViewModel>(
                    factory = MainViewModelFactory(app.repository, app)
                )
                // 아직 별도 내비게이션 라이브러리를 쓰지 않으므로, "지금 어느 화면을 보여줄지"를
                // 이 Boolean 하나로 직접 관리한다 (대시보드 ↔ 일자별 조회 화면, 두 화면뿐이라 충분하다).
                var showDateList by remember { mutableStateOf(false) }
                if (showDateList) {
                    DateTodoListScreen(viewModel = viewModel, onBack = { showDateList = false })
                } else {
                    MainDashboardScreen(viewModel = viewModel, onOpenDateList = { showDateList = true })
                }
            }
        }
    }
}
