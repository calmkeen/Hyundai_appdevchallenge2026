package com.carcue.app

import android.graphics.Bitmap
import android.os.SystemClock
import android.util.Base64
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/** Opt-in official AVD test. Only the host changes the external console fixtures; no app SET/scenario calls. */
@RunWith(AndroidJUnit4::class)
class PleosOfficialGuideTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val arguments get() = InstrumentationRegistry.getArguments()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private lateinit var directory: File
    private val profileId = "ioniq5-ne1-2024-kr"
    private val guideId = "ioniq5-door-open-check"
    private val manualSetId = "hyundai-ioniq5-ne1-2024-kr"
    private val manualVersion get() = arguments.getString("expectedSourceVersion")
        ?: "NE1-2024-KR-ko_KR-D202406100040-20240722"
    private val sourceUrls = setOf(
        "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html",
        "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html",
    )

    private fun file(name: String) = File(directory, name)
    private fun signal(name: String) { file(name).writeText("ready\n") }
    private fun waitSignal(name: String) {
        val until = SystemClock.elapsedRealtime() + 45000
        while (!file(name).exists() && SystemClock.elapsedRealtime() < until) Thread.sleep(100)
        check(file(name).exists()) { "Host handshake timed out: $name" }
    }
    private fun event(phase: String) {
        val state = vm.state.value
        // Deliberately records only the tested door and UI state, never VIN/raw vehicle payloads.
        file("events.jsonl").appendText(JSONObject().put("phase", phase)
            .put("device_ms", SystemClock.elapsedRealtime()).put("source", state.reading.source.name)
            .put("door_status", state.reading.status.name).put("door_value", state.reading.value ?: JSONObject.NULL)
            .put("ux_known", state.ux.known).put("ux_restricted", state.ux.restricted)
            .put("page", state.page.name).toString() + "\n")
    }
    private fun settle() {
        val until = SystemClock.elapsedRealtime() + 1000
        while (SystemClock.elapsedRealtime() < until) { rule.mainClock.advanceTimeByFrame(); Thread.sleep(16) }
        rule.waitForIdle()
    }
    private fun save(bitmap: Bitmap, name: String): String {
        file("$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        return MessageDigest.getInstance("SHA-256").digest(file("$name.png").readBytes())
            .joinToString("") { "%02x".format(it) }
    }
    private fun screenshot(name: String) { rule.waitForIdle(); save(rule.onRoot().captureToImage().asAndroidBitmap(), name) }
    private fun clickText(text: String) {
        val node = rule.onNodeWithText(text)
        try { node.assertIsDisplayed() } catch (_: AssertionError) { node.performScrollTo() }
        node.performClick(); rule.waitForIdle()
    }
    private fun reading(value: String) {
        rule.waitUntil(60000) { vm.state.value.reading.let { it.status == ReadStatus.VALUE && it.value == value } }
        rule.runOnIdle {
            val reading = vm.state.value.reading
            assertEquals(Source.PLEOS, reading.source)
            assertEquals(Capability.SUPPORTED, reading.capability)
            assertEquals("door.position", reading.propertyId)
            assertEquals("ROW_1_LEFT", reading.areaId)
            assertNotNull(reading.receivedAt)
        }
    }
    private fun assertOfficialGuide(captureSources: Boolean = false) {
        rule.runOnIdle {
            val state = vm.state.value
            val profile = requireNotNull(state.profile)
            val guide = requireNotNull(state.selectedGuide)
            assertTrue(profile.verified)
            assertEquals(profileId, profile.id)
            assertEquals(manualSetId, profile.manualSetId)
            assertEquals(manualVersion, profile.manualVersion)
            assertEquals(guideId, guide.id)
            assertTrue(guide.publicationVerified)
            assertEquals(manualSetId, guide.manualSetId)
            assertEquals(manualVersion, guide.sourceVersion)
            assertTrue(profileId in guide.profileIds)
            assertEquals(sourceUrls, guide.sources.map { it.second }.toSet())
            assertFalse(guide.id.startsWith("__"))
            assertEquals(Page.GUIDE, state.page)
        }
        rule.onNodeWithTag("guide_manual_sources").assertExists()
        rule.onNodeWithText(manualVersion, substring = true).performScrollTo().assertIsDisplayed()
        if (captureSources) screenshot("official-guide-manual-version")
        sourceUrls.forEachIndexed { index, url ->
            rule.onNodeWithText(url, substring = true).performScrollTo().assertIsDisplayed()
            if (captureSources) screenshot("official-guide-source-${index + 1}")
        }
    }

    @Test fun sdkDoorCallbacksOpenPublishedOfficialGuideAndRespectDrivingRestriction() {
        assumeTrue(arguments.getString("validateOfficialGuide") == "true")
        assertFalse(BuildConfig.IS_MOCK)
        assertEquals("http://10.0.2.2:8001", BuildConfig.SERVER_URL.trimEnd('/'))
        val runId = requireNotNull(arguments.getString("runId"))
        require(runId.matches(Regex("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")))
        directory = File(rule.activity.filesDir, "qa/$runId")
        check(!directory.exists() && directory.mkdirs()) { "Evidence directory must be new" }
        android.util.Log.i("CarCueOfficialGuide", "OFFICIAL_GUIDE:$runId:BEGIN")
        val encodedUrls = requireNotNull(arguments.getString("expectedSourceUrlsBase64"))
        val suppliedUrls = JSONArray(String(Base64.decode(encodedUrls, Base64.URL_SAFE or Base64.NO_WRAP), Charsets.UTF_8))
        assertEquals(sourceUrls, (0 until suppliedUrls.length()).map { suppliedUrls.getString(it) }.toSet())

        try {
            rule.waitUntil(45000) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
            rule.onNodeWithTag("profile_$profileId").performScrollTo().performClick()
            clickText("한국어")
            reading("CLOSED")
            rule.waitUntil(45000) { vm.state.value.serverConnection == "CONNECTED" && vm.state.value.guides.any { it.id == guideId } }
            clickText(vm.content.copy("ko-KR").get("ui_516e0278f12b"))
            rule.onNodeWithTag("related_door_guide").assertDoesNotExist()
            rule.onNodeWithTag("guide_image_card").assertDoesNotExist()
            settle()
            val initial = rule.onNodeWithTag("pleos_vehicle_visual").performScrollTo().captureToImage().asAndroidBitmap()
            val closedHash = save(initial, "car-initial-closed")
            screenshot("initial-get-closed"); event("INITIAL_GET_CLOSED"); signal("request-open")

            reading("OPEN")
            rule.waitUntil(15000) { vm.state.value.eventLog.any { it.contains("CALLBACK_RECEIVED:RANGE_VERIFIED:value=1") } }
            settle()
            val open = rule.onNodeWithTag("pleos_vehicle_visual").performScrollTo().captureToImage().asAndroidBitmap()
            val openHash = save(open, "car-callback-open")
            assertFalse("Actual SDK callback must change the vehicle visualization", initial.sameAs(open))
            screenshot("callback-open")
            rule.onNodeWithTag("related_door_guide").performScrollTo().assertIsEnabled().performClick()
            assertOfficialGuide(captureSources = true); screenshot("official-guide-sources")
            rule.onNodeWithTag("guide_live_door_status").performScrollTo()
                .assertTextContains(vm.content.copy("ko-KR").get("ui_86b92bfd7c71"), substring = true)
            val openReceived = vm.state.value.reading.receivedAt
            screenshot("official-guide-open"); event("OFFICIAL_GUIDE_OPEN"); signal("request-close")
            reading("CLOSED")
            rule.waitUntil(15000) { vm.state.value.reading.receivedAt != openReceived }
            rule.onNodeWithTag("related_door_guide").assertDoesNotExist()
            rule.onNodeWithTag("guide_live_door_status").performScrollTo()
                .assertTextContains(vm.content.copy("ko-KR").get("ui_f70cce500477"), substring = true)
            screenshot("guide-callback-closed"); event("CALLBACK_CLOSED")
            val getCount = vm.state.value.eventLog.count { it.contains("GET_RECEIVED:RANGE_VERIFIED:value=0") }
            rule.onNodeWithTag("refresh_door_status").performScrollTo().performClick()
            rule.waitUntil(30000) { vm.state.value.eventLog.count { it.contains("GET_RECEIVED:RANGE_VERIFIED:value=0") } > getCount }
            reading("CLOSED"); assertOfficialGuide()
            rule.onNodeWithTag("guide_live_door_status").performScrollTo(); screenshot("guide-refresh-get-closed")
            event("EXPLICIT_REFRESH_GET_CLOSED"); signal("request-drive")

            rule.waitUntil(45000) { vm.state.value.ux.known && vm.state.value.ux.restricted }
            rule.onNodeWithTag("guide_live_door_status").assertDoesNotExist()
            rule.onNodeWithTag("guide_manual_sources").assertDoesNotExist()
            screenshot("driving-guide-blocked"); event("DRIVING_GUIDE_BLOCKED")
            clickText(vm.content.copy("ko-KR").get("ui_6b02921768d6"))
            rule.onNodeWithTag("related_door_guide").assertDoesNotExist()
            rule.runOnIdle { vm.openRelatedDoorGuide(guideId) }
            rule.runOnIdle { assertEquals(Page.STATUS, vm.state.value.page) }
            event("RESTRICTED_NAVIGATION_REJECTED"); signal("request-park")

            rule.waitUntil(45000) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
            reading("CLOSED"); settle()
            val restored = rule.onNodeWithTag("pleos_vehicle_visual").performScrollTo().captureToImage().asAndroidBitmap()
            val restoredHash = save(restored, "car-restored-closed")
            assertTrue("Closing callback must restore the original vehicle image", initial.sameAs(restored))
            assertEquals(closedHash, restoredHash)
            screenshot("parked-return"); event("PARKED_RETURN")
            rule.runOnIdle { vm.endSession() }
            rule.runOnIdle {
                assertFalse(vm.state.value.sessionStarted)
                assertNull(vm.state.value.profile)
                assertNull(vm.state.value.reading.value)
            }
            screenshot("session-ended"); event("SESSION_ENDED")
            file("result.json").writeText(JSONObject().put("source", "PLEOS").put("physical_vehicle_tested", false)
                .put("profile_id", profileId).put("profile_selected_by_user", true).put("sdk_identified_vehicle_model", false)
                .put("manual_set_id", manualSetId).put("source_version", manualVersion).put("guide_id", guideId)
                .put("source_urls", JSONArray(sourceUrls.toList())).put("initial_closed_sha256", closedHash)
                .put("callback_open_sha256", openHash).put("restored_closed_sha256", restoredHash)
                .put("driving_guide_blocked", true).put("restricted_navigation_rejected", true)
                .put("explicit_refresh_get_closed", true).put("app_sdk_set_called", false)
                .put("external_ai_called", false).put("seatbelt_status_connected", false).toString(2))
            android.util.Log.i("CarCueOfficialGuide", "OFFICIAL_GUIDE:$runId:DONE")
            signal("done"); waitSignal("host-finished")
        } finally {
            // A failed assertion must not leave a vehicle listener/session running.
            rule.runOnIdle { if (vm.state.value.sessionStarted) vm.endSession() }
        }
    }
}
