package com.officefit.voice

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * SmartTextParser의 동작을 검증하는 단위 테스트(Unit Test)다.
 * JUnit은 Kotlin/Java에서 가장 널리 쓰이는 테스트 프레임워크이며, `@Test`가 붙은 함수 하나하나가
 * "이 코드가 이렇게 동작해야 한다"는 개별 검증 항목이다. 함수 이름을 백틱(`` ` ``)으로 감싸면
 * 공백/한글이 포함된 자연어 문장을 그대로 테스트 이름으로 쓸 수 있다(일반 함수명 규칙 예외).
 * `assertEquals(기대값, 실제값)`은 "두 값이 같아야 한다"는 검증이며, 다르면 테스트가 실패로 표시된다.
 * 안드로이드 스튜디오에서 각 함수 옆 ▶ 아이콘을 눌러 테스트를 개별 실행할 수 있고,
 * 커맨드라인에서는 `./gradlew testDebugUnitTest`로 전체를 한 번에 실행할 수 있다.
 */
class SmartTextParserTest {

    @Test
    fun `요구사항 예시 문장을 그대로 마크다운으로 변환한다`() {
        val raw = "10시에 SQL 쿼리 최적화 검토하고 저녁 7시에 MSA 아키텍처 스터디 문서 읽기"

        val markdown = SmartTextParser.parse(raw)

        val expected = """
            ### 🏢 사내 업무
            - [ ] [10:00] SQL 쿼리 최적화 검토
            ### 📚 개인 스터디/성장
            - [ ] [19:00] MSA 아키텍처 스터디 문서 읽기
        """.trimIndent()
        assertEquals(expected, markdown)
    }

    @Test
    fun `그리고 접속사로 태스크를 분리한다`() {
        val tasks = SmartTextParser.parseToTasks("배포 준비하기 그리고 운동 다녀오기")

        assertEquals(2, tasks.size)
        assertEquals("배포 준비하기", tasks[0].text)
        assertEquals(SmartTextParser.TaskCategory.WORK, tasks[0].category)
        assertEquals("운동 다녀오기", tasks[1].text)
        assertEquals(SmartTextParser.TaskCategory.STUDY, tasks[1].category)
    }

    @Test
    fun `다음으로와 그 다음에 표현으로도 분리한다`() {
        val tasks = SmartTextParser.parseToTasks("코드 리뷰하기 다음으로 문서 정리하기 그 다음에 커피 마시기")

        assertEquals(3, tasks.size)
        assertEquals("코드 리뷰하기", tasks[0].text)
        assertEquals("문서 정리하기", tasks[1].text)
        assertEquals("커피 마시기", tasks[2].text)
    }

    @Test
    fun `연결어미 -고로 끝나는 절을 분리하고 어미를 제거한다`() {
        val tasks = SmartTextParser.parseToTasks("자료 정리하고 발표 준비하기")

        assertEquals(2, tasks.size)
        assertEquals("자료 정리", tasks[0].text)
        assertEquals("발표 준비하기", tasks[1].text)
    }

    @Test
    fun `문장 끝의 -고는 분리하지 않는다`() {
        val tasks = SmartTextParser.parseToTasks("책상 정리하고")

        assertEquals(1, tasks.size)
        assertEquals("책상 정리하고", tasks[0].text)
    }

    @Test
    fun `오전 오후 저녁 시간 표현을 24시간제로 변환한다`() {
        val tasks = SmartTextParser.parseToTasks(
            "오전 9시 스탠드업 미팅 그리고 오후 2시 클라이언트 회의 그리고 밤 11시 스트레칭"
        )

        assertEquals("09:00", tasks[0].time)
        assertEquals("14:00", tasks[1].time)
        assertEquals("23:00", tasks[2].time)
    }

    @Test
    fun `분 단위 시간 표현도 인식한다`() {
        val tasks = SmartTextParser.parseToTasks("오후 3시 30분 팀 회의하기")

        assertEquals("15:30", tasks[0].time)
        assertEquals("팀 회의하기", tasks[0].text)
    }

    @Test
    fun `시간 표현이 없으면 접두사 없이 출력한다`() {
        val tasks = SmartTextParser.parseToTasks("책상 정리하기")

        assertEquals(null, tasks[0].time)
        assertEquals("- [ ] 책상 정리하기", tasks[0].toMarkdownLine())
    }

    @Test
    fun `업무 스터디 키워드가 없으면 일반 할 일로 분류한다`() {
        val tasks = SmartTextParser.parseToTasks("친구랑 저녁 약속 가기")

        assertEquals(SmartTextParser.TaskCategory.GENERAL, tasks[0].category)
    }

    @Test
    fun `업무 키워드 회의 배포 프로젝트를 인식한다`() {
        val tasks = SmartTextParser.parseToTasks(
            "회의 참석하기 그리고 배포 진행하기 그리고 프로젝트 계획 세우기"
        )

        tasks.forEach { assertEquals(SmartTextParser.TaskCategory.WORK, it.category) }
    }

    @Test
    fun `스터디 키워드 공부 학습 강의를 인식한다`() {
        val tasks = SmartTextParser.parseToTasks(
            "영어 공부하기 그리고 온라인 강의 듣기 그리고 알고리즘 학습하기"
        )

        tasks.forEach { assertEquals(SmartTextParser.TaskCategory.STUDY, it.category) }
    }

    @Test
    fun `카테고리가 하나뿐이면 해당 헤더만 출력한다`() {
        val markdown = SmartTextParser.parse("친구랑 저녁 약속 가기")

        val expected = """
            ### 📌 일반 할 일
            - [ ] 친구랑 저녁 약속 가기
        """.trimIndent()
        assertEquals(expected, markdown)
    }

    @Test
    fun `parse 결과를 parseMarkdown으로 되돌리면 원래 태스크와 동일하다`() {
        val raw = "10시에 SQL 쿼리 최적화 검토하고 저녁 7시에 MSA 아키텍처 스터디 문서 읽기"

        val original = SmartTextParser.parseToTasks(raw)
        val roundTripped = SmartTextParser.parseMarkdown(SmartTextParser.parse(raw))

        assertEquals(original, roundTripped)
    }

    @Test
    fun `프리뷰에서 체크 표시된 항목은 완료 상태로 되돌린다`() {
        val edited = """
            ### 📌 일반 할 일
            - [x] 책상 정리하기
            - [ ] [09:00] 커피 내리기
        """.trimIndent()

        val tasks = SmartTextParser.parseMarkdown(edited)

        assertEquals(2, tasks.size)
        assertEquals(true, tasks[0].isCompleted)
        assertEquals("책상 정리하기", tasks[0].text)
        assertEquals(false, tasks[1].isCompleted)
        assertEquals("09:00", tasks[1].time)
    }

    @Test
    fun `사용자가 헤더 문구를 살짝 바꿔도 이모지로 카테고리를 인식한다`() {
        val edited = """
            ### 🏢 오늘의 업무 목록
            - [ ] 코드 리뷰
        """.trimIndent()

        val tasks = SmartTextParser.parseMarkdown(edited)

        assertEquals(SmartTextParser.TaskCategory.WORK, tasks[0].category)
    }

    @Test
    fun `헤더가 아예 없으면 기본 카테고리는 일반 할 일이다`() {
        val edited = "- [ ] 아무 헤더 없이 적은 할 일"

        val tasks = SmartTextParser.parseMarkdown(edited)

        assertEquals(SmartTextParser.TaskCategory.GENERAL, tasks[0].category)
    }
}
