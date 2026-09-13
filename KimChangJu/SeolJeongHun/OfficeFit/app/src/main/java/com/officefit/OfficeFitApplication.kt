package com.officefit

import android.app.Application
import com.officefit.data.local.AppDatabase
import com.officefit.data.repository.TodoRepository

/**
 * 안드로이드 앱이 실행될 때 (어떤 화면보다도 먼저) 딱 한 번 생성되는 전역 객체다.
 * `AndroidManifest.xml`의 `<application>` 태그가 이 클래스를 가리키도록 등록되어 있어야
 * 시스템이 앱 시작 시 자동으로 이 클래스의 인스턴스를 만든다.
 * 이 프로젝트는 Hilt 같은 의존성 주입(DI) 라이브러리를 아직 쓰지 않기 때문에,
 * "DB와 Repository를 이 앱 안에서 하나씩만 만들어서 필요한 곳에 전달한다"는 역할을
 * 이 클래스가 수동으로 담당한다 (이를 "수동 DI"라고 부른다).
 * `by lazy { ... }`는 이 프로퍼티에 처음 접근하는 순간에만 값을 계산하고, 그 이후로는
 * 캐시된 값을 재사용하는 Kotlin 문법이다 — 앱 시작과 동시에 DB를 여는 대신, 실제로
 * 필요해지는 시점까지 늦춘다.
 */
class OfficeFitApplication : Application() {
    val database: AppDatabase by lazy { AppDatabase.getInstance(this) }
    val repository: TodoRepository by lazy { TodoRepository(database.todoDao()) }
}
