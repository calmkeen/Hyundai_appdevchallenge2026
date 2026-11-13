package com.carcue.app

import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class CarCueFlowTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private fun image(name: String) {
        rule.waitForIdle()
        val dir = File(rule.activity.filesDir, "qa").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
    private fun begin() {
        rule.onNodeWithText("IONIQ 5 · 2024").performScrollTo().performClick()
        rule.onNodeWithText("한국어").performScrollTo().performClick()
        rule.onNodeWithText("무엇을 확인할까요?").assertIsDisplayed()
    }
    @Test fun navigationStatusFailureUxAndSessionClear() {
        image("01-profile")
        begin()
        image("02-home")
        rule.onNodeWithText("현재 차량 상태 보기 →").performScrollTo().performClick()
        rule.onNodeWithText("앞좌석 왼쪽 문이 열려 있어요").assertIsDisplayed()
        image("03-mock-door-open")
        rule.onNodeWithText("앞좌석 왼쪽 문이 열려 있어요").performClick()
        image("04-door-detail")
        rule.runOnIdle { vm.scenario("UNAVAILABLE"); vm.go(Page.STATUS) }
        rule.onNodeWithText("아직 차량 정보를 읽지 못했어요").assertIsDisplayed()
        image("05-no-value")
        rule.runOnIdle { vm.scenario("CHECK_FAILED") }
        rule.onNodeWithText("지원 여부를 확인하지 못했어요").assertIsDisplayed()
        rule.runOnIdle { vm.scenario("UNSUPPORTED") }
        rule.onNodeWithText("이 차량에서 제공하지 않는 항목이에요").assertIsDisplayed()
        rule.runOnIdle { vm.scenario("STALE") }
        rule.onNodeWithText("이전에 받은 정보예요 · 현재값은 확인하지 못했어요").assertIsDisplayed()
        rule.runOnIdle { vm.openAssistant(); vm.scenario("RESTRICTED") }
        rule.onNodeWithTag("question_input").assertDoesNotExist()
        rule.onNodeWithText("주차한 뒤 이용해 주세요").assertIsDisplayed()
        image("06-mock-ux-restricted")
        rule.runOnIdle { vm.scenario("PARKED"); vm.go(Page.SETTINGS) }
        rule.onNodeWithText("이용 마치기").performScrollTo().performClick()
        rule.onNodeWithText("지우고 마치기").performClick()
        rule.onNodeWithText("어떤 차량을 이용하시나요?").assertIsDisplayed()
        rule.runOnIdle {
            assertEquals("ko-KR", vm.state.value.locale)
            assertEquals(ReadStatus.NOT_REQUESTED, vm.state.value.reading.status)
            assertNull(vm.state.value.profile)
            assertEquals("", vm.state.value.answer)
        }
        image("07-session-ended")
    }
    @Test fun guideStepReturnAndPlannedRtlKeepMarket() {
        begin()
        rule.runOnIdle { vm.go(Page.GUIDES) }
        rule.onNodeWithText("MOCK · 단계별 화면 시연").performScrollTo().performClick()
        rule.onNodeWithText("다음").performScrollTo().performClick()
        rule.onNodeWithText("2 / 3").assertIsDisplayed()
        rule.onNodeWithText("이 단계에 관해 질문").performScrollTo().performClick()
        rule.onNodeWithText("이전 안내로 돌아가기").performScrollTo().performClick()
        rule.onNodeWithText("2 / 3").assertIsDisplayed()
        image("08-guide-step")
        rule.runOnIdle { vm.language(); vm.chooseLanguage("ar") }
        rule.runOnIdle { assertEquals("KR", vm.state.value.profile?.market) }
        rule.onNodeWithText("This language is planned. UI is shown in English; vehicle specification is unchanged.").assertIsDisplayed()
        image("09-rtl-fallback")
    }
    @Test fun serverMockRoundTripAndUnknownQr() {
        begin()
        rule.runOnIdle { vm.openAssistant(); vm.send("door position", consent = true) }
        rule.waitUntil(45000) { vm.state.value.answerMode == "MOCK" || vm.state.value.error != null }
        rule.runOnIdle {
            assertEquals("MOCK", vm.state.value.answerMode)
            assertTrue(vm.state.value.answer.contains("검수된 자료"))
            assertEquals(Source.MOCK, vm.state.value.reading.source)
        }
        image("10-server-mock-response")
        rule.runOnIdle { vm.endSession(); vm.deepLink(android.net.Uri.parse("carcue://guide?profile_id=does-not-exist")) }
        rule.onNodeWithText("이 차량의 안내 정보를 찾지 못했어요. 차량을 다시 선택해 주세요.").assertIsDisplayed()
        rule.runOnIdle { assertNull(vm.state.value.profile) }
        image("11-invalid-qr")
    }
}
