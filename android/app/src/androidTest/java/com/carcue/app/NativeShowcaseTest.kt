package com.carcue.app

import android.os.SystemClock
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** One uninterrupted run of the real demo APK. The host starts/stops Android screenrecord.
 * The handshakes keep the test runner and launcher out of the actual recording.
 */
@RunWith(AndroidJUnit4::class)
class NativeShowcaseTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private val dir get() = File(rule.activity.filesDir, "native-recording").apply { mkdirs() }
    private fun signal(name: String) = File(dir, name)
    private fun waitSignal(name: String) {
        val until = SystemClock.elapsedRealtime() + 45000
        while (!signal(name).exists() && SystemClock.elapsedRealtime() < until) Thread.sleep(100)
        check(signal(name).exists()) { "Host handshake timed out: $name" }
    }
    private fun show(name: String) {
        rule.waitForIdle()
        signal("events.jsonl").appendText(JSONObject().put("scene", name).put("device_ms", SystemClock.elapsedRealtime()).toString() + "\n")
        Thread.sleep(2000)
    }
    private fun click(text: String) {
        val node = rule.onNodeWithText(text)
        try { node.assertIsDisplayed() } catch (_: AssertionError) { node.performScrollTo() }
        node.performClick()
        rule.waitForIdle()
    }
    @Test fun recordNativeScreens() {
        assumeTrue(BuildConfig.IS_MOCK && InstrumentationRegistry.getArguments().getString("recordShowcase") == "true")
        listOf("go", "stop", "done", "events.jsonl").forEach { signal(it).delete() }
        rule.onNodeWithText("어떤 차량을 이용하시나요?").assertIsDisplayed()
        signal("ready").writeText("ready")
        waitSignal("go")
        try {
            show("차량 선택")
            click("IONIQ 5 · 2024")
            show("세 언어 선택")
            click("한국어")
            show("홈 · 앱 내 3D 차량")
            click("현재 차량 상태 보기 →")
            rule.onNodeWithTag("vehicle_3d").assertContentDescriptionEquals("앞좌석 왼쪽 문 · 열림")
            show("차량 상태 · 문 열림")
            click("MOCK · 닫힘 시연")
            rule.onNodeWithTag("vehicle_3d").assertContentDescriptionEquals("앞좌석 왼쪽 문 · 닫힘")
            show("차량 상태 · 문 닫힘")
            rule.onNodeWithTag("vehicle_3d").performTouchInput { swipeLeft(durationMillis = 500) }
            show("앱 내 3D 모형 회전")
            click("MOCK · 열림 시연")
            click("앞좌석 왼쪽 문이 열려 있어요")
            show("문 상세 · 3D 위치")
            click("사용 가이드")
            rule.onNodeWithTag("guide_image_card").performScrollTo()
            show("가이드 목록 · 앱 내 사진")
            click("MOCK · 단계별 화면 시연")
            show("가이드 1단계 · 차량 그림")
            click("다음")
            rule.onNodeWithTag("guide_preview_image").assertExists()
            show("가이드 2단계 · 앱 내 사진")
            click("이 단계에 관해 질문")
            show("AI 질문 화면")
            click("이전 안내로 돌아가기")
            rule.onNodeWithText("2 / 3").assertIsDisplayed()
            click("홈")
            click("한국어")
            show("언어 변경 · 영어 선택")
            click("English")
            rule.onNodeWithText("What would you like to check?").assertIsDisplayed()
            show("English · Home")
            click("View vehicle status →")
            show("English · Vehicle status")
            click("Home")
            click("English")
            show("언어 변경 · 일본어 선택")
            click("日本語")
            rule.onNodeWithText("何を確認しますか？").assertIsDisplayed()
            show("日本語 · ホーム")
            click("現在の車両状態を見る →")
            show("日本語 · 車両の状態")
            click("利用設定・利用終了")
            click("利用を終了")
            show("이용 종료 확인")
            click("削除して終了")
            rule.onNodeWithText("어떤 차량을 이용하시나요?").assertIsDisplayed()
            rule.runOnIdle { check(vm.state.value.profile == null) }
            show("이용 종료 · 초기화")
            // Force a final native frame after the dialog fade and the two-second
            // hold; Android screenrecord can omit a fully static trailing frame.
            click("CarCue")
            Thread.sleep(300)
            signal("done").writeText("done")
            waitSignal("stop")
        } finally {
            signal("ready").delete()
        }
    }
}
