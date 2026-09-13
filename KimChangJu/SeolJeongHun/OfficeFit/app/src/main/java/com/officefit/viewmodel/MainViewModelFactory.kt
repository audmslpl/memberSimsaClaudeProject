package com.officefit.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.officefit.data.repository.TodoRepository

/**
 * 안드로이드의 ViewModel은 파라미터가 없는 기본 생성자만 있으면 시스템이 알아서 만들어주지만,
 * 이 프로젝트의 MainViewModel처럼 생성자에 Repository/Context 같은 값을 넘겨줘야 하는 경우엔
 * "이렇게 만들어달라"고 알려주는 Factory(공장) 클래스가 필요하다.
 * Hilt 같은 의존성 주입 라이브러리를 쓰면 이 클래스가 자동 생성되지만, 이 프로젝트는 아직 수동으로 작성한다.
 * 실제 사용 예: `viewModel<MainViewModel>(factory = MainViewModelFactory(repository, context))`
 */
class MainViewModelFactory(
    private val repository: TodoRepository,
    private val appContext: Context
) : ViewModelProvider.Factory {
    // 시스템이 "이 타입의 ViewModel을 만들어달라"고 요청하면 호출되는 함수.
    // 여기서는 MainViewModel 하나만 처리하고, 모르는 타입이 들어오면 예외를 던진다.
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(MainViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST") // 제네릭 타입 캐스팅 경고를 의도적으로 무시(우리가 타입을 이미 확인했으므로 안전함)
            return MainViewModel(repository, appContext.applicationContext) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
