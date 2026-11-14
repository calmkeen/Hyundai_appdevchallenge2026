package com.carcue.app

import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/** One APK/process, real SDK values throughout onboarding, guides and all three languages. */
@RunWith(AndroidJUnit4::class)
class PleosShowcaseTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private val dir get() = File(rule.activity.filesDir, "pleos-showcase").apply { mkdirs() }
    private fun file(name: String) = File(dir, name)
    private fun waitSignal(name: String) {
        val until = SystemClock.elapsedRealtime() + 45000
        while (!file(name).exists() && SystemClock.elapsedRealtime() < until) Thread.sleep(100)
        check(file(name).exists()) { "Host handshake timed out: $name" }
    }
    private fun show(name: String) {
        rule.waitForIdle()
        val state = vm.state.value
        assertEquals(Source.PLEOS, state.reading.source)
        file("events.jsonl").appendText(JSONObject().put("scene", name).put("device_ms", SystemClock.elapsedRealtime())
            .put("source", state.reading.source.name).put("value", state.reading.value ?: JSONObject.NULL)
            .put("locale", state.locale).put("page", state.page.name).toString()+"\n")
        val until = SystemClock.elapsedRealtime() + 2000
        while (SystemClock.elapsedRealtime() < until) {
            rule.mainClock.advanceTimeByFrame(); Thread.sleep(16)
        }
        rule.waitForIdle()
    }
    private fun click(text: String) {
        val node = rule.onNodeWithText(text)
        try { node.assertIsDisplayed() } catch (_: AssertionError) { node.performScrollTo() }
        node.performClick(); rule.waitForIdle()
    }
    private fun reading(value: String) {
        rule.waitUntil(45000) { vm.state.value.reading.value == value && vm.state.value.reading.status == ReadStatus.VALUE }
        rule.runOnIdle {
            assertEquals(Source.PLEOS, vm.state.value.reading.source)
            assertEquals(Capability.SUPPORTED, vm.state.value.reading.capability)
            assertNotNull(vm.state.value.reading.receivedAt)
        }
    }
    private fun car(name: String): Bitmap {
        val bitmap = rule.onNodeWithTag("pleos_vehicle_visual").captureToImage().asAndroidBitmap()
        file("$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG,100,it) }
        return bitmap
    }
    private fun screenshot(name: String) {
        file("$name.png").outputStream().use { rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG,100,it) }
    }
    private fun sha(name: String) = MessageDigest.getInstance("SHA-256").digest(file(name).readBytes()).joinToString("") { "%02x".format(it) }

    @Test fun recordConnectedAppInThreeLanguages() {
        assumeTrue(!BuildConfig.IS_MOCK && InstrumentationRegistry.getArguments().getString("recordShowcase") == "true")
        dir.listFiles()?.forEach { it.delete() }
        rule.waitUntil(30000) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
        rule.onNodeWithText("어떤 차량을 이용하시나요?").assertIsDisplayed()
        file("ready").writeText("ready"); waitSignal("go")
        try {
            show("차량 선택")
            click("IONIQ 5 · 2024"); show("세 언어 선택")
            click("한국어"); reading("CLOSED"); show("한국어 · SDK 홈")
            click("현재 차량 상태 보기 →"); show("SDK 최초 닫힘 수신")
            rule.onNodeWithText("MOCK · 열림 시연").assertDoesNotExist()
            val closed = car("car-initial-closed"); screenshot("ko-closed")
            file("request-open").writeText("1"); reading("OPEN"); show("SDK 열림 콜백")
            val opened = car("car-open"); screenshot("ko-open")
            assertFalse("SDK open callback must change the car image", closed.sameAs(opened))
            file("request-close").writeText("0"); reading("CLOSED"); show("SDK 닫힘 콜백")
            val restored = car("car-restored-closed"); screenshot("ko-restored")
            assertTrue("SDK close callback must restore car pixels", closed.sameAs(restored))
            rule.onNodeWithTag("seatbelt_visual").assertIsDisplayed(); show("SDK 앱의 안전벨트 안내")
            click("앞좌석 왼쪽 문이 닫혀 있어요"); show("SDK 문 상세")
            click("사용 가이드"); rule.onNodeWithTag("guide_image_card").performScrollTo(); show("가이드 목록 · 앱 내 사진")
            click("예시 · 단계별 안내 보기"); show("가이드 1단계 · SDK 차량")
            click("다음"); rule.onNodeWithTag("guide_preview_image").assertExists(); show("가이드 2단계 · 앱 내 사진")
            click("이 단계에 관해 질문"); show("AI 질문 화면")
            click("이전 안내로 돌아가기"); rule.onNodeWithText("2 / 3").assertIsDisplayed()
            click("홈"); click("한국어"); show("언어 변경 · 영어 선택")
            click("English"); reading("CLOSED"); show("English · Home"); screenshot("en-home")
            click("View vehicle status →")
            file("request-open-en").writeText("1"); reading("OPEN"); show("English · Vehicle status"); screenshot("en-status")
            click("Home"); click("English"); show("언어 변경 · 일본어 선택")
            click("日本語"); reading("OPEN"); show("日本語 · ホーム"); screenshot("ja-home")
            click("現在の車両状態を見る →")
            file("request-close-ja").writeText("0"); reading("CLOSED"); show("日本語 · 車両の状態"); screenshot("ja-status")
            rule.runOnIdle { assertEquals("KR", vm.state.value.profile?.market) }
            click("利用設定・利用終了"); click("利用を終了"); show("이용 종료 확인")
            click("削除して終了"); rule.onNodeWithText("어떤 차량을 이용하시나요?").assertIsDisplayed()
            rule.runOnIdle { assertNull(vm.state.value.profile); assertNull(vm.state.value.reading.value); assertFalse(vm.state.value.sessionStarted) }
            show("이용 종료 · 초기화")
            file("result.json").writeText(JSONObject().put("source", "PLEOS").put("single_apk", true)
                .put("languages", "ko-KR,en,ja-JP").put("initial_closed_sha256", sha("car-initial-closed.png"))
                .put("open_sha256", sha("car-open.png")).put("restored_closed_sha256", sha("car-restored-closed.png"))
                .put("guide_content", "DEBUG_LAYOUT_PREVIEW").put("external_ai_called", false)
                .put("seatbelt_status_connected", false).toString(2))
            file("done").writeText("done"); waitSignal("stop")
        } finally { file("ready").delete() }
    }
}
