package com.carcue.app

import android.graphics.Bitmap
import android.os.SystemClock
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
import org.json.JSONObject
import java.security.MessageDigest

/** Official Pleos AVD only; the external test driver changes the simulator's front-left door. */
@RunWith(AndroidJUnit4::class)
class PleosSdkTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private val directory get() = File(rule.activity.filesDir, "qa").apply { mkdirs() }
    private fun settleVisual() {
        val until = SystemClock.elapsedRealtime() + 1000
        while (SystemClock.elapsedRealtime() < until) {
            rule.mainClock.advanceTimeByFrame()
            Thread.sleep(16)
        }
        rule.waitForIdle()
    }
    private fun save(bitmap: Bitmap, name: String): String {
        val file = File(directory, "$name.png")
        file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        return MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
    }
    private fun screenshot(name: String) {
        save(rule.onRoot().captureToImage().asAndroidBitmap(), name)
    }
    private fun car(): Bitmap = rule.onNodeWithTag("pleos_vehicle_visual").captureToImage().asAndroidBitmap()
    private fun assertRealReading(value: String) {
        rule.runOnIdle {
            val reading = vm.state.value.reading
            assertEquals(Source.PLEOS, reading.source)
            assertEquals(Capability.SUPPORTED, reading.capability)
            assertEquals(ReadStatus.VALUE, reading.status)
            assertEquals(value, reading.value)
            assertNotNull(reading.receivedAt)
        }
    }
    @Test fun getChangeCallbackAndRelease() {
        assertFalse(BuildConfig.IS_MOCK)
        rule.runOnIdle { vm.openReadOnlyStatus() }
        rule.waitUntil(60000) { vm.state.value.reading.status == ReadStatus.VALUE }
        assertRealReading("CLOSED")
        settleVisual()
        rule.onNodeWithTag("pleos_vehicle_visual").assertContentDescriptionEquals("앞좌석 왼쪽 문 · 닫힘")
        rule.onNodeWithTag("seatbelt_visual").assertExists()
        rule.onNodeWithText("안내 이미지 예시 · 착용 상태 미연결").assertIsDisplayed()
        rule.onNodeWithText("MOCK · 열림 시연").assertDoesNotExist()
        val initial = car()
        val initialHash = save(initial, "sdk-car-initial-closed")
        screenshot("pleos-initial-get")
        android.util.Log.i("CarCueVehicle", "SDK_TEST:UX_STATE:known=${vm.state.value.ux.known}:restricted=${vm.state.value.ux.restricted}:flags=${vm.state.value.ux.flags}")
        android.util.Log.i("CarCueVehicle", "SDK_TEST:INITIAL_CAPTURED:value=CLOSED:device_ms=${SystemClock.elapsedRealtime()}")
        rule.waitUntil(60000) { vm.state.value.reading.value == "OPEN" &&
            vm.state.value.reading.status == ReadStatus.VALUE && vm.state.value.eventLog.any { it.contains("CALLBACK_RECEIVED") } }
        assertRealReading("OPEN")
        val openReceivedAt = vm.state.value.reading.receivedAt
        settleVisual()
        rule.onNodeWithTag("pleos_vehicle_visual").assertContentDescriptionEquals("앞좌석 왼쪽 문 · 열림")
        val opened = car()
        assertEquals(initial.width, opened.width)
        assertEquals(initial.height, opened.height)
        val a = IntArray(initial.width * initial.height)
        val b = IntArray(a.size)
        initial.getPixels(a, 0, initial.width, 0, 0, initial.width, initial.height)
        opened.getPixels(b, 0, opened.width, 0, 0, opened.width, opened.height)
        val changedPixels = a.indices.count { a[it] != b[it] }
        assertTrue("SDK callback must change actual car pixels", changedPixels > maxOf(100, a.size / 1000))
        val openHash = save(opened, "sdk-car-open")
        screenshot("pleos-changed-callback")
        android.util.Log.i("CarCueVehicle", "SDK_TEST:OPEN_CAPTURED:changed_pixels=$changedPixels:device_ms=${SystemClock.elapsedRealtime()}")
        rule.waitUntil(60000) { vm.state.value.reading.value == "CLOSED" &&
            vm.state.value.reading.status == ReadStatus.VALUE && vm.state.value.reading.receivedAt != openReceivedAt }
        assertRealReading("CLOSED")
        settleVisual()
        rule.onNodeWithTag("pleos_vehicle_visual").assertContentDescriptionEquals("앞좌석 왼쪽 문 · 닫힘")
        val restored = car()
        assertTrue("SDK close callback must restore original car pixels", initial.sameAs(restored))
        val restoredHash = save(restored, "sdk-car-restored-closed")
        assertEquals(initialHash, restoredHash)
        screenshot("pleos-restored-callback")
        File(directory, "sdk-visual-result.json").writeText(JSONObject()
            .put("source", "PLEOS").put("sequence", "CLOSED→OPEN→CLOSED")
            .put("changed_pixels", changedPixels).put("total_pixels", a.size)
            .put("initial_closed_sha256", initialHash).put("open_sha256", openHash)
            .put("restored_closed_sha256", restoredHash).put("seatbelt_status_connected", false)
            .put("external_ai_called", false).toString(2))
        android.util.Log.i("CarCueVehicle", "SDK_TEST:RESTORED_CAPTURED:exact_pixels_restored=true:device_ms=${SystemClock.elapsedRealtime()}")
        val finish = File(rule.activity.filesDir, "sdk-validation-finish")
        finish.delete()
        val deadline = SystemClock.elapsedRealtime() + 30000
        while (!finish.exists() && SystemClock.elapsedRealtime() < deadline) Thread.sleep(100)
        check(finish.exists()) { "Host did not finish evidence capture" }
        rule.runOnIdle { vm.endSession() }
        rule.runOnIdle {
            assertNull(vm.state.value.reading.value)
            assertFalse(vm.state.value.sessionStarted)
        }
        screenshot("pleos-session-ended")
    }
}
