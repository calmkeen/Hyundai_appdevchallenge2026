package com.carcue.app

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.ActivityNotFoundException
import android.content.ContextWrapper
import android.content.Intent
import android.graphics.Bitmap
import android.os.Build
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Opt-in actual Pleos UI/stock HTTPS handler test; no browser install, SDK SET or generated translation. */
@RunWith(AndroidJUnit4::class)
class PleosOfficialResourcesTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val arguments get() = InstrumentationRegistry.getArguments()
    private lateinit var model: CarCueViewModel
    private lateinit var activity: MainActivity
    private lateinit var directory: File
    private lateinit var expectedResult: ExternalOpenResult
    private val gets = mutableSetOf<String>()
    private val routes = mutableSetOf<String>()
    private val returnMethods = mutableSetOf<String>()
    private val profileId = "ioniq5-ne1-2024-kr"
    private val guideId = "ioniq5-door-open-check"
    private val supportId = "hyundai-kr-customer-support"
    private val supportUrl = "https://www.hyundai.com/kr/ko/e/customer/center"
    private val manualUrl = "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html"
    private val browserPackage = "org.chromium.webview_shell"
    private val stepIndex = 1

    private fun waitPlain(timeout: Long, description: String, condition: () -> Boolean) {
        val deadline = SystemClock.elapsedRealtime() + timeout
        while (!condition() && SystemClock.elapsedRealtime() < deadline) Thread.sleep(50)
        check(condition()) { description }
    }
    private fun getCount(): Int {
        gets.addAll(model.state.value.eventLog.filter { it.contains("PLEOS:GET_RECEIVED:RANGE_VERIFIED:value=0") })
        return gets.size
    }
    private fun ready() {
        rule.waitUntil(45000) { model.state.value.ux.let { it.known && !it.restricted } }
        rule.waitUntil(60000) { model.state.value.reading.let { it.source == Source.PLEOS && it.capability == Capability.SUPPORTED && it.status == ReadStatus.VALUE && it.value == "CLOSED" } }
        assertNotNull(model.state.value.reading.receivedAt)
    }
    private fun guideState(page: Page = Page.GUIDE) {
        val s = model.state.value
        assertEquals(page, s.page)
        assertEquals(profileId, s.profile?.id)
        assertEquals("KR", s.profile?.market)
        assertEquals(guideId, s.selectedGuide?.id)
        assertTrue(requireNotNull(s.selectedGuide).publicationVerified)
        assertEquals(stepIndex, s.guideStep)
        assertTrue(s.ux.known && !s.ux.restricted)
        assertEquals(Source.PLEOS, s.reading.source)
    }
    private fun clickText(text: String) = rule.onNodeWithText(text).performScrollTo().performClick()
    private fun appImage(name: String) {
        rule.waitForIdle()
        File(directory, "$name.png").outputStream().use { out ->
            rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, out)
        }
    }
    private fun physicalImage(name: String) {
        val bitmap = instrumentation.uiAutomation.takeScreenshot() ?: return
        File(directory, "$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
    private fun browserWindow(): Boolean {
        val windows = instrumentation.uiAutomation.windowsOnAllDisplays
        var found = false
        for (display in 0 until windows.size()) for (window in windows.valueAt(display)) {
            val root = window.root
            if (root?.packageName?.toString() == browserPackage) found = true
            root?.recycle(); window.recycle()
        }
        return found
    }
    private fun shell(command: String): String = ParcelFileDescriptor.AutoCloseInputStream(
        instrumentation.uiAutomation.executeShellCommand(command)).bufferedReader().use { it.readText().trim() }
    private fun back() { shell("input keyevent KEYCODE_BACK") }
    private fun returnFromBrowser() {
        back()
        val deadline = SystemClock.elapsedRealtime() + 1500
        while (SystemClock.elapsedRealtime() < deadline) {
            if (!browserWindow() && activity.lifecycle.currentState == Lifecycle.State.RESUMED) {
                returnMethods.add("BACK"); return
            }
            Thread.sleep(100)
        }
        // Browser2's test shell can consume BACK. Re-select the existing app task as a launcher would.
        // This is real platform navigation, not a direct vm.foreground() or a synthetic SDK reading.
        shell("am start --user 10 -W -f 0x10020000 -n com.carcue.app/.MainActivity")
        waitPlain(15000, "App task re-selection did not resume the same MainActivity") {
            !browserWindow() && activity.lifecycle.currentState == Lifecycle.State.RESUMED
        }
        returnMethods.add("APP_TASK_RESELECT")
    }
    private fun event(phase: String, extra: JSONObject = JSONObject()) {
        val s = model.state.value
        extra.put("phase", phase).put("locale", s.locale).put("page", s.page.name)
            .put("profile_id", s.profile?.id).put("market", s.profile?.market)
            .put("guide_id", s.selectedGuide?.id).put("guide_step", s.guideStep)
            .put("source", s.reading.source.name).put("read_status", s.reading.status.name)
            .put("door", s.reading.value ?: JSONObject.NULL).put("received_at", s.reading.receivedAt?.toString() ?: JSONObject.NULL)
            .put("ux_known", s.ux.known).put("ux_restricted", s.ux.restricted).put("ux_flags", s.ux.flags)
            .put("sdk_get_count", getCount()).put("activity_lifecycle", activity.lifecycle.currentState.name)
            .put("physical_vehicle_tested", false).put("page_loaded_asserted", false)
        File(directory, "events.jsonl").appendText(extra.toString() + "\n")
    }
    private fun open(phase: String, tag: String, id: String, url: String, page: Page = Page.GUIDE) {
        guideState(page)
        val beforeGet = getCount()
        val beforeReading = model.state.value.reading.receivedAt
        rule.onAllNodesWithTag(tag).onFirst().performScrollTo().performClick()
        waitPlain(15000, "No external dispatch outcome") { model.state.value.externalResource != null }
        val notice = requireNotNull(model.state.value.externalResource)
        assertEquals(expectedResult, notice.result)
        if (expectedResult == ExternalOpenResult.INTENT_DISPATCHED) {
            assertEquals(ExternalOpenRoute.PLEOS_AVD_STOCK, notice.route)
            routes.add(notice.route.name)
        }
        assertEquals(id, notice.resource.id)
        assertEquals(url, notice.resource.url)
        assertEquals("KR", notice.resource.market)
        assertEquals("ko-KR", notice.resource.sourceLocale)
        var observedBrowser = false
        if (expectedResult == ExternalOpenResult.INTENT_DISPATCHED) {
            waitPlain(15000, "Stock browser window was not observed") { browserWindow() }
            observedBrowser = true
            physicalImage("$phase-external-physical")
            event("${phase}_DISPATCHED", JSONObject().put("resource_id", id).put("url", url).put("source_locale", notice.resource.sourceLocale)
                .put("external_outcome", notice.result.name).put("external_route", notice.route.name).put("stock_browser_window_observed", true))
            returnFromBrowser()
            ready()
            // This must be a fresh GET after the actual external Activity roundtrip, not a reused reading.
            rule.waitUntil(60000) { getCount() > beforeGet && model.state.value.reading.receivedAt != beforeReading }
        } else {
            assertEquals(ExternalOpenResult.NO_HANDLER, notice.result)
            assertEquals(Lifecycle.State.RESUMED, activity.lifecycle.currentState)
        }
        rule.waitForIdle()
        guideState(page)
        rule.onNodeWithTag("external_result_$expectedResult").performScrollTo().assertIsDisplayed()
        rule.onNodeWithTag("external_resource_url").assertTextEquals(url)
        appImage("$phase-return")
        event("${phase}_RETURN", JSONObject().put("resource_id", id).put("url", url).put("source_locale", notice.resource.sourceLocale)
            .put("external_outcome", notice.result.name).put("external_route", notice.route.name).put("sdk_get_count_before", beforeGet)
            .put("stock_browser_roundtrip_exercised", observedBrowser))
    }
    private fun selectLanguage(locale: String) {
        if (model.state.value.locale != locale) {
            rule.runOnIdle { model.language() }
            clickText(model.content.languages.single { it.tag == locale }.native)
        }
        rule.waitUntil(45000) { model.state.value.let { !it.guidesLoading && it.locale == locale && it.guides.any { g -> g.id == guideId && g.locale == locale } } }
        ready()
    }
    private fun openGuide() {
        rule.runOnIdle { model.go(Page.GUIDES) }
        rule.waitUntil(45000) { model.state.value.page == Page.GUIDES && !model.state.value.guidesLoading }
        clickText(model.state.value.guides.single { it.id == guideId }.title)
        clickText(model.content.copy(model.state.value.locale).get("ui_aef613c6612d"))
        rule.runOnIdle { guideState() }
    }
    private fun adapterFailures() {
        val target = ExternalResource(supportId, "Registered official support", supportUrl, "KR", "ko-KR")
        val absent = object : ContextWrapper(instrumentation.targetContext) {
            override fun startActivity(intent: Intent) { throw ActivityNotFoundException() }
        }
        val denied = object : ContextWrapper(instrumentation.targetContext) {
            override fun startActivity(intent: Intent) { throw SecurityException() }
        }
        assertEquals(ExternalOpenResult.NO_HANDLER, OfficialResourceOpener(absent).open(target))
        assertEquals(ExternalOpenResult.REJECTED, OfficialResourceOpener(denied).open(target))
        File(directory, "adapter-failure-simulation.json").writeText(JSONObject()
            .put("scope", "CONTEXT_WRAPPER_DISPATCH_EXCEPTION_DOUBLE").put("actual_browser_absence_tested", false)
            .put("stock_browser_changed", false).put("no_handler_catch", true).put("security_rejection_catch", true).toString(2))
    }

    @Test fun registeredManualAndSupportDispatchReturnWithActualSdk() {
        assumeTrue(arguments.getString("validateOfficialResources") == "true")
        assertFalse(BuildConfig.IS_MOCK)
        assertEquals(34, Build.VERSION.SDK_INT)
        assertEquals("1", shell("getprop ro.kernel.qemu"))
        assertTrue(shell("getprop ro.boot.qemu.avd_name") in setOf("CarCue_Pleos21", "CarCue_Pleos21_LocalAI"))
        assertEquals("10", shell("am get-current-user"))
        assertEquals("http://10.0.2.2:8001", BuildConfig.SERVER_URL.trimEnd('/'))
        expectedResult = ExternalOpenResult.valueOf(requireNotNull(arguments.getString("expectedExternalResult")))
        require(expectedResult in listOf(ExternalOpenResult.INTENT_DISPATCHED, ExternalOpenResult.NO_HANDLER))
        val runId = requireNotNull(arguments.getString("runId"))
        require(runId.matches(Regex("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")))
        activity = rule.activity
        model = ViewModelProvider(activity)[CarCueViewModel::class.java]
        directory = File(activity.filesDir, "qa/$runId")
        check(!directory.exists() && directory.mkdirs()) { "Evidence directory must be new" }
        val originalFlags = instrumentation.uiAutomation.serviceInfo.flags
        instrumentation.uiAutomation.serviceInfo = instrumentation.uiAutomation.serviceInfo.apply {
            flags = flags or AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        }
        var actualAskCalls = 0
        try {
            adapterFailures()
            rule.waitUntil(45000) { model.state.value.ux.let { it.known && !it.restricted } }
            rule.onNodeWithTag("profile_$profileId").performScrollTo().performClick()
            clickText("한국어")
            for (locale in listOf("ko-KR", "en", "ja-JP")) {
                selectLanguage(locale); openGuide()
                val guide = requireNotNull(model.state.value.selectedGuide)
                val source = guide.officialSources.first()
                assertEquals(manualUrl, source.url)
                assertEquals("ko-KR", source.sourceLocale)
                assertEquals(supportUrl, model.state.value.profile?.supportContacts?.single { it.id == supportId }?.url)
                open("$locale-MANUAL", "manual_source_0", source.id, manualUrl)
                open("$locale-SUPPORT", "official_support", supportId, supportUrl)
            }
            selectLanguage("ko-KR"); openGuide()
            clickText(model.content.copy("ko-KR").get("ui_af7d9b9636de"))
            rule.onNodeWithTag("question_input").performScrollTo().performTextInput("문을 닫기 전에 무엇을 확인해야 하나요?")
            rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
            rule.onNodeWithTag("ai_consent").performScrollTo().performClick()
            rule.onNodeWithTag("ai_send").performScrollTo().performClick()
            rule.waitUntil(150000) { model.state.value.let { !it.busy && (it.answerStatus.isNotBlank() || it.error != null) } }
            // A real UX disconnect may gate the page after an already received answer.
            // Wait for a fresh allowed UX report; never replace it with a parked fixture.
            rule.waitUntil(45000) { model.state.value.ux.let { it.known && !it.restricted } }
            rule.runOnIdle {
                val s = model.state.value
                assertNull(s.error); assertEquals("ANSWERED", s.answerStatus)
                assertEquals("LIVE", s.answerMode); assertEquals(AiProvider.OLLAMA_LOCAL, s.answerProvider)
                assertEquals(arguments.getString("expectedLocalModel") ?: "qwen3:4b", s.answerModel)
                assertTrue(s.answerRequestId.isNotBlank()); assertEquals(s.answerRequestId, s.lastAiRequestId)
                assertTrue(s.officialCitations.isNotEmpty())
                for (citation in s.officialCitations) {
                    assertEquals(profileId, citation.profileId); assertEquals(guideId, citation.guideId)
                    assertEquals(s.profile?.manualSetId, citation.manualSetId); assertEquals(s.profile?.manualVersion, citation.sourceVersion)
                    assertEquals(s.selectedGuide?.officialSources?.single { it.id == citation.sourceId }?.url, citation.url)
                    assertTrue(("OPEN_MANUAL" to citation.sourceId) in s.actions)
                }
                assertTrue(("OPEN_SUPPORT" to supportId) in s.actions)
                guideState(Page.ASK)
            }
            actualAskCalls = 1
            appImage("ko-KR-ACTUAL_ANSWER")
            val citation = model.state.value.officialCitations.first()
            event("ACTUAL_LOCAL_ASK", JSONObject().put("request_id", model.state.value.answerRequestId)
                .put("ai_provider", model.state.value.answerProvider.name).put("ai_model", model.state.value.answerModel)
                .put("actions", JSONArray(model.state.value.actions.map { it.first })))
            open("ANSWER-MANUAL", "assistant_action_OPEN_MANUAL", citation.sourceId, citation.url, Page.ASK)
            open("ANSWER-SUPPORT", "assistant_action_OPEN_SUPPORT", supportId, supportUrl, Page.ASK)
            if (expectedResult == ExternalOpenResult.NO_HANDLER) {
                val before = getCount()
                rule.activityRule.scenario.moveToState(Lifecycle.State.CREATED)
                rule.activityRule.scenario.moveToState(Lifecycle.State.RESUMED)
                ready(); rule.waitUntil(60000) { getCount() > before }
                guideState(Page.ASK)
                event("SEPARATE_ACTIVITY_LIFECYCLE_RESTART", JSONObject().put("browser_roundtrip", false))
            }
        } catch (failure: Throwable) {
            runCatching { event("FAILED", JSONObject().put("error_type", failure.javaClass.simpleName)) }
            runCatching { physicalImage("failure-physical") }
            throw failure
        } finally {
            try {
                runCatching { if (expectedResult == ExternalOpenResult.INTENT_DISPATCHED && browserWindow()) returnFromBrowser() }
                instrumentation.runOnMainSync { model.endSession() }
                waitPlain(45000, "Remote session deletion still pending") { !model.state.value.deletionPending }
            } finally {
                instrumentation.uiAutomation.serviceInfo = instrumentation.uiAutomation.serviceInfo.apply { flags = originalFlags }
            }
        }
        assertFalse(model.state.value.sessionStarted)
        assertNull(model.state.value.profile)
        File(directory, "result.json").writeText(JSONObject().put("passed", true).put("source", "PLEOS")
            .put("expected_external_result", expectedResult.name).put("stock_browser_roundtrip_exercised", expectedResult == ExternalOpenResult.INTENT_DISPATCHED)
            .put("page_loaded_asserted", false).put("physical_vehicle_tested", false).put("app_sdk_set_called", false)
            .put("adapter_exception_test_scope", "CONTEXT_WRAPPER_DISPATCH_EXCEPTION_DOUBLE")
            .put("actual_browser_absence_tested", expectedResult == ExternalOpenResult.NO_HANDLER)
            .put("return_methods", JSONArray(returnMethods.toList())).put("external_routes", JSONArray(routes.toList())).put("actual_local_ask_calls", actualAskCalls).put("paid_ai_called", false).put("generated_question_translation_called", false).toString(2))
        File(directory, "done").writeText("pass\n")
    }
}
