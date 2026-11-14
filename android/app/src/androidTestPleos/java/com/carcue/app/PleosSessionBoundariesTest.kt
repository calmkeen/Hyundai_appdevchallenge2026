package com.carcue.app

import android.graphics.Bitmap
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.view.WindowManager
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.security.MessageDigest
import java.time.Instant
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Opt-in actual SDK/local-provider tests. Only the host changes isolated AVD fixtures. */
@RunWith(AndroidJUnit4::class)
class PleosSessionBoundariesTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val args get() = InstrumentationRegistry.getArguments()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private lateinit var directory: File
    private val gets = mutableSetOf<String>()
    private val profileId = "ioniq5-ne1-2024-kr"
    private val guideId = "ioniq5-door-open-check"
    private val sourceIds = listOf("hyundai-ne1-2024-kr-door-open-warning", "hyundai-ne1-2024-kr-door-pinch-caution")
    private val questions = linkedMapOf(
        "ko-KR" to "문을 닫기 전에 무엇을 확인해야 하나요?",
        "en" to "What should I check before closing the indicated door?",
        "ja-JP" to "表示されたドアを閉める前に何を確認しますか？",
    )
    private val expectedModel get() = args.getString("expectedLocalModel") ?: "qwen3:4b"
    private var originallyKeptAwake = false
    private fun file(name: String) = File(directory, name)
    private fun signal(name: String, value: JSONObject = JSONObject()) { file(name).writeText(value.toString()) }
    private fun waitSignal(name: String, timeout: Long = 45000) {
        val deadline = SystemClock.elapsedRealtime() + timeout
        while (!file(name).exists() && SystemClock.elapsedRealtime() < deadline) Thread.sleep(50)
        check(file(name).exists()) { "Host handshake timed out: $name" }
    }
    private fun clickText(text: String) {
        val node = rule.onNodeWithText(text)
        // Dialog buttons and the fixed navigation have no scroll parent.
        // Scroll only when a content target is not already visible.
        try { node.assertIsDisplayed() } catch (_: AssertionError) { node.performScrollTo() }
        node.assertIsDisplayed().performClick()
    }
    private fun clickTag(tag: String) = rule.onNodeWithTag(tag).performScrollTo().performClick()
    private fun copy(key: String) = vm.content.copy(vm.state.value.locale).get(key)
    private fun getCount(): Int {
        gets.addAll(vm.state.value.eventLog.filter { it.contains("PLEOS:GET_RECEIVED:RANGE_VERIFIED:") })
        return gets.size
    }
    private fun ux(allowed: Boolean = true) {
        rule.waitUntil(45000) { vm.state.value.ux.let { it.known && it.restricted != allowed } }
    }
    private fun reading(value: String = "CLOSED") {
        rule.waitUntil(60000) { vm.state.value.reading.expired(Instant.now(), BuildConfig.STATE_TTL_MS).let {
            it.source == Source.PLEOS && it.capability == Capability.SUPPORTED && it.status == ReadStatus.VALUE && it.value == value
        } }
    }
    private fun refresh() {
        reading(); val before = getCount(); val received = vm.state.value.reading.receivedAt
        rule.runOnIdle { vm.refresh() }
        rule.waitUntil(60000) { getCount() > before && vm.state.value.reading.receivedAt != received }
        reading(); ux()
    }
    private fun selectLanguage(tag: String) {
        if (vm.state.value.locale != tag) {
            rule.runOnIdle { vm.language() }
            clickText(vm.content.languages.single { it.tag == tag }.native)
        }
        rule.waitUntil(45000) { vm.state.value.let { it.locale == tag && it.guides.any { g -> g.id == guideId && g.locale == tag && g.publicationVerified } } }
    }
    private fun guide(step: Int) {
        rule.runOnIdle { vm.go(Page.GUIDES) }
        rule.waitUntil(45000) { !vm.state.value.guidesLoading }
        clickText(vm.state.value.guides.single { it.id == guideId }.title)
        if (step == 1) clickText(copy("ui_aef613c6612d"))
        assertEquals(step, vm.state.value.guideStep)
        assertTrue(requireNotNull(vm.state.value.selectedGuide).publicationVerified)
    }
    private fun enterAsk(step: Int?) {
        if (step == null) {
            rule.runOnIdle { vm.go(Page.HOME) }
            // This is the fixed visible sidebar, not a scrolling content row.
            rule.onAllNodesWithText(copy("ui_7a087ed8150b")).onFirst().assertIsDisplayed().performClick()
        } else { guide(step); clickText(copy("ui_af7d9b9636de")) }
        assertEquals(Page.ASK, vm.state.value.page)
    }
    private fun rawGuide(locale: String): JSONObject {
        val guides = CarCueApi().guides(profileId, locale)
        return (0 until guides.length()).map { guides.getJSONObject(it) }.single { it.getString("guide_id") == guideId }
    }
    private fun parts(guide: JSONObject): List<String> = buildList {
        add(guide.getString("body"))
        val steps = guide.getJSONArray("steps")
        assertEquals(2, steps.length())
        for (i in 0 until steps.length()) {
            val step = steps.getJSONObject(i)
            assertEquals(listOf("check-pinch-area", "check-closure-display")[i], step.getString("step_id"))
            add(step.getString("body"))
            val cautions = step.getJSONArray("official_cautions")
            assertTrue(cautions.length() > 0)
            for (j in 0 until cautions.length()) add(cautions.getString(j))
        }
    }
    private fun complete(text: String, guide: JSONObject) {
        assertEquals(parts(guide).joinToString("\n"), text)
    }
    private fun visibleComplete(text: String, guide: JSONObject) {
        complete(text, guide)
        rule.onNodeWithText(text).performScrollTo().assertIsDisplayed()
        for (part in parts(guide)) rule.onNodeWithText(part, substring = true).assertIsDisplayed()
        val bounds = rule.onNodeWithText(text).getUnclippedBoundsInRoot()
        val root = rule.onRoot().getUnclippedBoundsInRoot()
        assertTrue("Full caution bundle must fit the recorded viewport", bounds.top >= root.top && bounds.bottom <= root.bottom)
    }
    private fun image(name: String) {
        rule.waitUntil(15000) { rule.activity.hasWindowFocus() }
        rule.waitForIdle()
        file("$name.png").outputStream().use { rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it) }
        val physical = requireNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        file("$name-physical.png").outputStream().use { physical.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
    private fun state(): JSONObject {
        val s = vm.state.value
        val translated = s.page == Page.TRANSLATE
        return JSONObject().put("device_ms", SystemClock.elapsedRealtime()).put("recorded_at", Instant.now().toString())
            .put("app_pid", Process.myPid()).put("locale", s.locale).put("page", s.page.name)
            .put("profile_id", s.profile?.id ?: JSONObject.NULL).put("profile_name", s.profile?.name ?: JSONObject.NULL)
            .put("guide_id", s.selectedGuide?.id ?: JSONObject.NULL).put("guide_step", s.guideStep)
            .put("market", s.profile?.market ?: JSONObject.NULL).put("source", s.reading.source.name)
            .put("value", s.reading.value ?: JSONObject.NULL).put("read_status", s.reading.status.name)
            .put("received_at", s.reading.receivedAt?.toString() ?: JSONObject.NULL).put("state_ttl_ms", BuildConfig.STATE_TTL_MS)
            .put("capability", s.reading.capability.name).put("sdk_get_count", getCount())
            .put("ux_known", s.ux.known).put("ux_restricted", s.ux.restricted).put("ux_flags", s.ux.flags)
            .put("session_started", s.sessionStarted).put("deletion_pending", s.deletionPending).put("busy", s.busy)
            .put("request_id", s.lastAiRequestId).put("answer_request_id", s.answerRequestId)
            .put("status", if (translated) if (s.translation.isEmpty()) "EMPTY" else "TRANSLATED" else s.answerStatus)
            .put("ai_provider", if (translated) s.translationProvider.name else s.answerProvider.name)
            .put("ai_model", (if (translated) s.translationModel else s.answerModel) ?: JSONObject.NULL)
            .put("mode", if (translated) s.translationMode else s.answerMode)
            .put("content_kind", if (translated) s.translationKind else "ANSWER")
            .put("source_locale", if (translated) s.translationSourceLocale else s.answerLocale)
            .put("target_locale", if (translated) s.translationTargetLocale else s.answerLocale)
            .put("review_status", if (translated) s.translationReview else JSONObject.NULL)
            .put("error", s.error ?: JSONObject.NULL)
    }
    private fun event(phase: String) { file("events.jsonl").appendText(state().put("phase", phase).toString() + "\n") }
    private fun scene(id: String) {
        image(id)
        val item = state().put("scene_id", id).put("hold_seconds", 2)
            .put("compose_png", "$id.png").put("physical_png", "$id-physical.png")
        val until = SystemClock.elapsedRealtime() + 2000
        while (SystemClock.elapsedRealtime() < until) Thread.sleep(20)
        item.put("hold_end_device_ms", SystemClock.elapsedRealtime())
        file("scenes.jsonl").appendText(item.toString() + "\n")
    }
    private fun languageTransitionToEnglish() {
        val from = vm.state.value.locale
        assertNotEquals("en", from)
        rule.runOnIdle { vm.go(Page.HOME); vm.language() }
        rule.onNodeWithText("English").assertIsDisplayed()
        rule.waitForIdle()
        val started = SystemClock.elapsedRealtime()
        Thread.sleep(200)
        val clicked = SystemClock.elapsedRealtime()
        rule.onNodeWithText("English").performClick()
        rule.waitUntil(1500) { vm.state.value.locale == "en" && vm.state.value.page == Page.HOME }
        val completed = SystemClock.elapsedRealtime()
        assertTrue("Actual language selection must fit the two-second source interval", completed - started < 2000)
        while (SystemClock.elapsedRealtime() < started + 2000) Thread.sleep(10)
        val ended = SystemClock.elapsedRealtime()
        val item = state().put("scene_id", "language-en").put("scene_kind", "LANGUAGE_TRANSITION")
            .put("device_ms", started).put("hold_seconds", 2).put("hold_end_device_ms", ended)
            .put("from_locale", from).put("selected_locale", "en").put("selection_clicked_device_ms", clicked)
            .put("transition_completed_device_ms", completed).put("compose_png", "language-en.png")
            .put("physical_png", "language-en-physical.png")
        image("language-en")
        file("scenes.jsonl").appendText(item.toString() + "\n")
        selectLanguage("en") // Await the ordinary reviewed-guide HTTP load after the visible transition.
    }
    private fun startAsk(locale: String, checkEditedConsent: Boolean = false): String {
        rule.onNodeWithTag("question_input").performScrollTo().performTextInput(questions.getValue(locale))
        rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
        rule.onNodeWithTag("ai_consent").assertIsOff()
        clickTag("ai_consent")
        if (checkEditedConsent) {
            rule.onNodeWithTag("question_input").performScrollTo().performTextReplacement(questions.getValue(locale) + " ")
            rule.onNodeWithTag("ai_consent").assertIsOff()
            rule.onNodeWithTag("question_input").performTextReplacement(questions.getValue(locale))
            rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
            clickTag("ai_consent")
            event("EDITED_INPUT_RESET_CONSENT")
        }
        val previous = vm.state.value.lastAiRequestId
        clickTag("ai_send")
        rule.waitUntil(15000) { vm.state.value.lastAiRequestId != previous && vm.state.value.lastAiRequestId.isNotEmpty() }
        return vm.state.value.lastAiRequestId
    }
    private fun awaitAnswer(locale: String, raw: JSONObject) {
        rule.waitUntil(150000) { vm.state.value.let { !it.busy && (it.answerStatus.isNotEmpty() || it.error != null) } }
        ux(); reading()
        rule.runOnIdle {
            val s = vm.state.value
            assertNull(s.error); assertEquals("ANSWERED", s.answerStatus); assertEquals("LIVE", s.answerMode)
            assertEquals(AiProvider.OLLAMA_LOCAL, s.answerProvider); assertEquals(expectedModel, s.answerModel)
            assertEquals(locale, s.answerLocale); assertEquals(s.lastAiRequestId, s.answerRequestId)
            complete(s.answer, raw); assertEquals(sourceIds, s.officialCitations.map { it.sourceId })
            val sources = raw.getJSONArray("sources")
            for (i in sourceIds.indices) {
                val item = s.officialCitations[i]
                assertEquals(profileId, item.profileId); assertEquals(guideId, item.guideId)
                assertEquals(raw.getString("manual_set_id"), item.manualSetId)
                assertEquals(raw.getString("source_version"), item.sourceVersion)
                assertEquals(sources.getJSONObject(i).getString("url"), item.url)
            }
        }
        rule.onNodeWithTag("ask_source_locale").performScrollTo()
            .assertTextContains(vm.content.languages.single { it.tag == locale }.native, substring = true)
        refresh()
        visibleComplete(vm.state.value.answer, raw)
    }
    private fun response(phase: String, originalLocale: String, raw: JSONObject, translation: Boolean) {
        val s = vm.state.value
        val citations = JSONArray()
        for (item in s.officialCitations) citations.put(JSONObject().put("source_id", item.sourceId).put("guide_id", item.guideId)
            .put("profile_id", item.profileId).put("manual_set_id", item.manualSetId).put("source_version", item.sourceVersion).put("url", item.url))
        file("responses.jsonl").appendText(state().put("phase", phase).put("question", questions.getValue(originalLocale))
            .put("text", if (translation) s.translation else s.answer).put("citations", citations)
            .put("unit_suffix", ":closing-bundle:v1").put("all_cautions_ui_visible", true)
            .put("required_parts", JSONArray(parts(raw))).toString() + "\n")
    }
    private fun stored(source: String, target: String, raw: JSONObject, scene: Boolean = false) {
        val original = vm.state.value.answer
        clickText(copy("ui_translate_answer")); selectLanguage(target)
        rule.runOnIdle {
            assertEquals(original, vm.state.value.translationDraft)
            assertEquals(source, vm.state.value.translationSourceLocale)
            assertEquals("", vm.state.value.translation); assertEquals("", vm.state.value.translationTargetLocale)
        }
        rule.onNodeWithTag("translation_source_locale").performScrollTo()
            .assertTextContains(vm.content.languages.single { it.tag == source }.native, substring = true)
        rule.onNodeWithTag("translation_target_locale").performScrollTo()
            .assertTextContains(vm.content.languages.single { it.tag == target }.native, substring = true)
        rule.onNodeWithTag("ai_consent").assertIsOff()
        rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
        clickTag("ai_consent"); val before = vm.state.value.lastAiRequestId; clickTag("ai_send")
        rule.waitUntil(150000) { vm.state.value.let { !it.busy && (it.error != null || it.lastAiRequestId != before && it.translation.isNotEmpty()) } }
        rule.runOnIdle {
            val s = vm.state.value
            assertNull(s.error); assertEquals("LIVE", s.translationMode)
            assertEquals(AiProvider.STORED_GUIDE, s.translationProvider); assertNull(s.translationModel)
            assertEquals("ANSWER", s.translationKind); assertEquals(source, s.translationSourceLocale)
            assertEquals(target, s.translationTargetLocale); assertEquals(original, s.translationOriginal)
            assertEquals(raw.getString("translation_review_status"), s.translationReview)
            complete(s.translation, raw)
        }
        rule.onNodeWithTag("translation_result_target_locale").performScrollTo()
            .assertTextContains(vm.content.languages.single { it.tag == target }.native, substring = true)
        refresh()
        rule.onNodeWithTag("translation_result_${vm.state.value.translationReview}").performScrollTo().assertIsDisplayed()
        visibleComplete(vm.state.value.translation, raw)
        val phase = "stored-$source-to-$target"
        image(phase); response(phase, source, raw, true)
        if (scene) scene("translation-en")
    }
    private fun endViaUi() {
        rule.runOnIdle { vm.go(Page.SETTINGS) }
        clickText(copy("ui_48af33bc151c")); clickText(copy("ui_a827222cef89"))
        rule.waitUntil(45000) { !vm.state.value.deletionPending }
        clean()
    }
    private fun clean() {
        val s = vm.state.value
        assertEquals(Page.PROFILE, s.page); assertFalse(s.sessionStarted); assertNull(s.profile)
        assertEquals("ko-KR", s.locale); assertEquals("", s.answer); assertEquals("", s.answerRequestId)
        assertEquals("", s.translation); assertEquals("", s.translationDraft); assertEquals("", s.translationOriginal)
        assertEquals("", s.translationTargetLocale); assertEquals("", s.lastAiRequestId)
        assertTrue(s.citations.isEmpty()); assertTrue(s.officialCitations.isEmpty()); assertTrue(s.actions.isEmpty())
        assertNull(s.reading.value); assertFalse(s.busy)
    }
    private fun prepare(mode: String) {
        assertFalse(BuildConfig.IS_MOCK); assertEquals(34, Build.VERSION.SDK_INT)
        assertEquals("http://10.0.2.2:8001", BuildConfig.SERVER_URL.trimEnd('/'))
        val runId = requireNotNull(args.getString("runId"))
        require(runId.matches(Regex("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")))
        directory = File(rule.activity.filesDir, "qa/$runId/sdk-session")
        check(!directory.exists() && directory.mkdirs())
        originallyKeptAwake = rule.activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON != 0
        rule.runOnIdle { rule.activity.window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
        if (mode == "late") {
            // Let the host select this already-created instrumentation task before starting SDK/UX assertions.
            signal("activity-ready", state().put("window_focused", rule.activity.hasWindowFocus()))
            waitSignal("activity-go")
            rule.waitUntil(30000) { rule.activity.hasWindowFocus() }
            signal("activity-focus.json", state().put("window_focused", true))
        }
        ux(); event("PREPARED_$mode")
    }
    private fun finish(mode: String, passed: Boolean) {
        try {
            rule.runOnIdle { if (vm.state.value.sessionStarted) vm.endSession() }
            rule.waitUntil(45000) { !vm.state.value.deletionPending }
            clean()
            if (passed) {
                file("result.json").writeText(JSONObject().put("passed", true).put("mode", mode).put("app_pid", Process.myPid())
                    .put("asks", 3).put("stored_answer_translations", if (mode == "showcase") 3 else 0)
                    .put("question_translation_calls", 0).put("paid_provider_called", false).put("physical_vehicle_tested", false)
                    .put("seatbelt_status_connected", false).put("session_end_asserted", true).put("deletion_pending", false).toString(2))
                signal("done")
                waitSignal("stop")
            }
        } finally {
            if (!originallyKeptAwake) rule.runOnIdle { rule.activity.window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
        }
    }
    private fun failure(error: Throwable) {
        if (::directory.isInitialized) {
            file("failure.json").writeText(state().put("error_type", error.javaClass.simpleName).toString(2))
            runCatching { image("failure") }
        }
    }
    private fun carImage(name: String): Bitmap {
        rule.onNodeWithTag("pleos_vehicle_visual").performScrollTo()
        // The production pose uses 720ms of device time. Keep advancing real
        // Compose frames throughout that interval; sleeping alone can leave
        // this test's clock at the first frame even after the SDK callback.
        val until = SystemClock.elapsedRealtime() + 900
        while (SystemClock.elapsedRealtime() < until) {
            rule.mainClock.advanceTimeByFrame()
            Thread.sleep(16)
        }
        rule.waitForIdle()
        return rule.onNodeWithTag("pleos_vehicle_visual").captureToImage().asAndroidBitmap().also { bitmap ->
            file("$name.png").outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }
    private fun sha(name: String) = MessageDigest.getInstance("SHA-256").digest(file(name).readBytes())
        .joinToString("") { "%02x".format(it) }

    @Test fun connectedShowcaseFlow() {
        assumeTrue(args.getString("validateSdkSessionFlow") == "true" && args.getString("sessionFlowMode") == "showcase")
        var passed = false
        try {
            prepare("showcase")
            signal("ready"); waitSignal("go")
            scene("profile"); clickTag("profile_$profileId"); scene("language-ko")
            clickText("한국어"); ux(); reading(); refresh()
            val guides = questions.keys.associateWith { rawGuide(it) }
            rule.runOnIdle { vm.go(Page.STATUS) }
            val closed = carImage("car-initial-closed")
            scene("door-closed")
            signal("request-open"); rule.waitUntil(45000) { vm.state.value.reading.value == "OPEN" }; reading("OPEN")
            val opened = carImage("car-callback-open")
            assertFalse(closed.sameAs(opened)); scene("door-open")
            signal("request-close"); rule.waitUntil(45000) { vm.state.value.reading.value == "CLOSED" }; reading()
            val restored = carImage("car-restored-closed")
            assertTrue(closed.sameAs(restored)); scene("door-restored")
            file("car-pixels.json").writeText(JSONObject().put("closed", sha("car-initial-closed.png"))
                .put("open", sha("car-callback-open.png")).put("restored", sha("car-restored-closed.png")).toString())
            rule.onNodeWithTag("seatbelt_visual").performScrollTo().assertIsDisplayed(); scene("seatbelt")
            guide(1)
            rule.onNodeWithText(requireNotNull(vm.state.value.selectedGuide).steps[1].second).performScrollTo()
            scene("official-guide-step2")
            for ((index, source) in questions.keys.withIndex()) {
                if (source == "en") languageTransitionToEnglish() else selectLanguage(source)
                enterAsk(when (index) { 0 -> 0; 1 -> 1; else -> null })
                val retained = vm.state.value.answerLocale
                if (vm.state.value.answer.isNotEmpty() && retained != source) {
                    rule.onNodeWithTag("ask_source_locale").performScrollTo()
                        .assertTextContains(vm.content.languages.single { it.tag == retained }.native, substring = true)
                    event("RETAINED_ANSWER_LANGUAGE_EXPLICIT_$source")
                }
                startAsk(source, source == "ko-KR"); awaitAnswer(source, guides.getValue(source))
                response("ask-$source", source, guides.getValue(source), false)
                scene(when (source) { "ko-KR" -> "ask-ko"; "en" -> "ask-en"; else -> "ask-ja" })
                val target = listOf("en", "ja-JP", "ko-KR")[index]
                stored(source, target, guides.getValue(target), source == "ko-KR")
                if (source == "ko-KR") {
                    val original = vm.state.value.translationOriginal
                    selectLanguage("ja-JP")
                    rule.runOnIdle {
                        val s = vm.state.value
                        assertEquals("", s.translation); assertEquals("", s.translationTargetLocale)
                        assertEquals(original, s.translationOriginal); assertEquals(original, s.translationDraft)
                        assertEquals("ko-KR", s.translationSourceLocale)
                    }
                    rule.onNodeWithTag("translation_result_REVIEWED").assertDoesNotExist()
                    rule.onNodeWithTag("translation_result_target_locale").assertDoesNotExist()
                    rule.onNodeWithTag("ai_consent").assertIsOff()
                    event("LOCALE_CHANGE_CLEARED_OLD_TRANSLATION_AND_CONSENT")
                }
                if (source == "en") {
                    clickText(copy("ui_7812fd4be3f4"))
                    assertEquals(Page.ASK, vm.state.value.page)
                    assertEquals("en", vm.state.value.answerLocale)
                    clickText(copy("ui_7812fd4be3f4"))
                    rule.runOnIdle {
                        val s = vm.state.value
                        assertEquals(Page.GUIDE, s.page); assertEquals(guideId, s.selectedGuide?.id)
                        assertEquals(1, s.guideStep); assertEquals("en", s.selectedGuide?.locale)
                        assertEquals("ja-JP", s.locale)
                    }
                    rule.onNodeWithText(copy("ui_original_locale").replace("{locale}", "en"))
                        .performScrollTo().assertIsDisplayed()
                    image("translation-back-retained-guide-step2")
                    event("TWO_BACKS_RETAINED_ORIGINAL_GUIDE_STEP")
                }
            }
            signal("request-drive"); ux(false)
            rule.onNodeWithTag("question_input").assertDoesNotExist()
            rule.onNodeWithTag("assistant_answer").assertDoesNotExist()
            rule.onNodeWithTag("translation_result_NOT_APPLICABLE").assertDoesNotExist()
            scene("drive-restricted"); signal("request-park"); ux(); reading(); refresh()
            endViaUi(); scene("end-session"); passed = true
        } catch (error: Throwable) { failure(error); throw error }
        finally { if (::directory.isInitialized) finish("showcase", passed) }
    }

    private fun assertNoLateResult() {
        val s = vm.state.value
        assertFalse(s.busy); assertEquals("", s.answer); assertEquals("", s.answerRequestId); assertEquals("", s.answerStatus)
        assertEquals("", s.followUpQuestion); assertTrue(s.citations.isEmpty()); assertTrue(s.officialCitations.isEmpty()); assertTrue(s.actions.isEmpty())
        assertEquals("", s.translation); assertEquals("", s.translationTargetLocale)
        rule.onNodeWithTag("assistant_answer").assertDoesNotExist()
    }
    @Test fun lateResponseBoundaries() {
        assumeTrue(args.getString("validateSdkSessionFlow") == "true" && args.getString("sessionFlowMode") == "late")
        var passed = false
        try {
            prepare("late")
            clickTag("profile_$profileId"); clickText("한국어"); reading(); refresh()
            signal("ready"); waitSignal("go")
            for ((name, locale) in listOf("locale" to "ko-KR", "drive" to "en", "end" to "ja-JP")) {
                selectLanguage(locale); refresh(); enterAsk(0)
                val request = startAsk(locale)
                assertTrue("Actual request must still be pending", vm.state.value.busy)
                signal("pending-$name", state().put("request_id", request))
                waitSignal("boundary-go-$name")
                assertTrue("The boundary must precede the actual response", vm.state.value.busy)
                when (name) {
                    "locale" -> {
                        InstrumentationRegistry.getInstrumentation().runOnMainSync { vm.language() }
                        clickText(vm.content.languages.single { it.tag == "en" }.native)
                        // Record the actual UI boundary before unrelated asynchronous guide loading or semantic-idle checks.
                        val changed = vm.state.value
                        assertEquals("en", changed.locale); assertEquals(Page.ASK, changed.page); assertFalse(changed.busy)
                        signal("boundary-locale", state().put("cancelled_request_id", request)
                            .put("route", "PRODUCTION_NAVIGATION_HANDLER_ON_MAIN_THREAD_WHILE_INFLIGHT"))
                    }
                    "drive" -> { signal("request-drive"); ux(false); rule.onNodeWithTag("question_input").assertDoesNotExist() }
                    else -> {
                        // DELETE may still be pending while the model request completes. Do not wait for it before the boundary marker.
                        InstrumentationRegistry.getInstrumentation().runOnMainSync { vm.go(Page.SETTINGS) }
                        clickText(copy("ui_48af33bc151c")); clickText(copy("ui_a827222cef89"))
                        clean()
                    }
                }
                assertNoLateResult()
                if (name != "locale") signal("boundary-$name", state().put("cancelled_request_id", request).apply {
                    if (name == "end") put("route", "PRODUCTION_NAVIGATION_HANDLER_ON_MAIN_THREAD_WHILE_INFLIGHT")
                })
                waitSignal("model-finished-$name", 150000)
                val until = SystemClock.elapsedRealtime() + 2000
                while (SystemClock.elapsedRealtime() < until) { assertNoLateResult(); Thread.sleep(50) }
                image("late-$name"); event("LATE_${name.uppercase()}_SUPPRESSED")
                if (name == "drive") { signal("request-park"); ux(); reading(); refresh(); assertNoLateResult() }
                if (name == "end") {
                    rule.waitUntil(45000) { !vm.state.value.deletionPending }; clean()
                    clickTag("profile_$profileId"); clickText("English"); reading(); refresh()
                    assertEquals("en", vm.state.value.locale); assertNoLateResult(); event("NEW_USER_HAS_NO_OLD_RESPONSE")
                }
                signal("checked-$name", state().put("cancelled_request_id", request))
            }
            endViaUi(); passed = true
        } catch (error: Throwable) { failure(error); throw error }
        finally { if (::directory.isInitialized) finish("late", passed) }
    }
}
