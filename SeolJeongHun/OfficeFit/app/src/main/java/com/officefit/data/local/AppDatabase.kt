package com.officefit.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

/**
 * 앱 전체에서 쓰는 Room 데이터베이스의 "설계도" 겸 "접근 창구"다.
 * `entities = [TodoItem::class]`는 이 DB 안에 어떤 테이블들이 있는지 Room에게 알려주는 목록이고,
 * `version`은 테이블 구조가 바뀔 때마다 올려야 하는 스키마 버전 번호다(마이그레이션에 사용).
 * `@TypeConverters(Converters::class)`는 앞서 만든 Converters(Category ↔ String 변환기)를
 * 이 DB 전체에 적용하겠다는 등록이다.
 * `abstract class` + `RoomDatabase()`를 상속하면, Room이 컴파일 시점에 실제 구현 클래스를
 * 자동으로 만들어준다 — 우리는 `todoDao()`처럼 "이 DAO를 쓸 것이다"라는 선언만 하면 된다.
 */
@Database(entities = [TodoItem::class], version = 1, exportSchema = false)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {

    abstract fun todoDao(): TodoDao

    // DB 연결은 비용이 크기 때문에 앱 전체에서 딱 하나의 인스턴스만 만들어 재사용한다 (싱글톤 패턴).
    companion object {
        // @Volatile: 여러 스레드가 동시에 이 변수를 볼 때, 항상 최신 값을 보게 강제하는 표시.
        @Volatile private var INSTANCE: AppDatabase? = null

        // 이미 만들어둔 인스턴스가 있으면 그걸 재사용하고, 없으면 새로 만든다.
        // synchronized(this)는 여러 스레드가 동시에 호출해도 인스턴스가 2개 이상 생기지 않도록 잠그는 구간이다.
        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "officefit.db" // 기기 내부에 저장될 실제 DB 파일 이름
                ).build().also { INSTANCE = it }
            }
        }
    }
}
