package com.carcue.app

import android.graphics.Bitmap
import android.os.Build
import android.os.SystemClock
import android.view.WindowManager
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.time.Instant
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Actual parked Pleos SDK + free local ASK; saved ANSWER translation never generates instructions. */
@RunWith(AndroidJUnit4::class)
class PleosCautionAnswersTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val args get() = InstrumentationRegistry.getArguments()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private lateinit var directory: File
    private val gets = mutableSetOf<String>()
    private val profileId = "ioniq5-ne1-2024-kr"
    private val guideId = "ioniq5-door-open-check"
    private val stepIds = listOf("check-pinch-area", "check-closure-display")
    private val sourceIds = listOf("hyundai-ne1-2024-kr-door-open-warning", "hyundai-ne1-2024-kr-door-pinch-caution")

    private data class Case(val locale: String, val question: String, val step: Int?, val target: String)
    private val cases = listOf(
        Case("ko-KR", "문을 닫기 전에 무엇을 확인해야 하나요?", 0, "en"),
        Case("en", "What should I check before closing the indicated door?", 1, "ja-JP"),
        Case("ja-JP", "表示されたドアを閉める前に何を確認しますか？", null, "ko-KR"),
    )
    private val prohibitions = mapOf(
        "ko-KR" to "몸의 일부가 문틈에 있으면 닫지 마세요.",
        "en" to "Do not close the door while any body part is in the opening.",
        "ja-JP" to "体の一部が開口部にある状態では、ドアを閉めないでください。",
    )
    private fun clickText(text: String) = rule.onNodeWithText(text).performScrollTo().performClick()
    private fun clickTag(tag: String) = rule.onNodeWithTag(tag).performScrollTo().performClick()
    private fun getCount(): Int {
        gets.addAll(vm.state.value.eventLog.filter { it.contains("PLEOS:GET_RECEIVED:RANGE_VERIFIED:value=0") })
        return gets.size
    }
    private fun actualReady() {
        rule.waitUntil(45000) { vm.state.value.ux.let { it.known && !it.restricted } }
        rule.waitUntil(60000) {
            vm.state.value.reading.expired(Instant.now(), BuildConfig.STATE_TTL_MS).let {
                it.source == Source.PLEOS && it.capability == Capability.SUPPORTED && it.status == ReadStatus.VALUE && it.value == "CLOSED"
            }
        }
    }
    private fun refreshActual() {
        val before = getCount()
        val received = vm.state.value.reading.receivedAt
        rule.runOnIdle { vm.refresh() } // Calls the production SDK GET adapter; no state/fixture injection.
        rule.waitUntil(60000) { getCount() > before && vm.state.value.reading.receivedAt != received }
        actualReady()
    }
    private fun selectLanguage(locale: String) {
        if (vm.state.value.locale != locale) {
            rule.runOnIdle { vm.language() }
            clickText(vm.content.languages.single { it.tag == locale }.native)
        }
        rule.waitUntil(45000) {
            vm.state.value.let { it.locale == locale && it.guides.any { g -> g.id == guideId && g.locale == locale && g.publicationVerified } }
        }
    }
    private fun rawGuide(locale: String): JSONObject {
        val all = CarCueApi().guides(profileId, locale)
        return (0 until all.length()).map { all.getJSONObject(it) }.single { it.getString("guide_id") == guideId }
    }
    private fun parts(guide: JSONObject): List<String> = buildList {
        add(guide.getString("body"))
        val steps = guide.getJSONArray("steps")
        assertEquals(2, steps.length())
        for (i in stepIds.indices) {
            val step = steps.getJSONObject(i)
            assertEquals(stepIds[i], step.getString("step_id"))
            add(step.getString("body"))
            val cautions = step.getJSONArray("official_cautions")
            assertTrue(cautions.length() > 0)
            for (j in 0 until cautions.length()) add(cautions.getString(j))
        }
    }
    private fun cautions(guide: JSONObject): List<String> = buildList {
        val steps = guide.getJSONArray("steps")
        for (i in 0 until steps.length()) {
            val items = steps.getJSONObject(i).getJSONArray("official_cautions")
            for (j in 0 until items.length()) add(items.getString(j))
        }
    }
    private fun assertComplete(text: String, guide: JSONObject) {
        val expected = parts(guide)
        assertEquals(expected.joinToString("\n"), text)
        assertTrue(cautions(guide).contains(prohibitions.getValue(guide.getString("locale"))))
        var end = 0
        for (part in expected) {
            val position = text.indexOf(part, end)
            assertTrue("Complete source passage/caution order must be retained", position >= end)
            end = position + part.length
        }
    }
    private fun assertTextVisible(text: String, guide: JSONObject) {
        rule.onNodeWithText(text).performScrollTo().assertIsDisplayed()
        for (caution in cautions(guide)) rule.onNodeWithText(caution, substring = true).assertIsDisplayed()
        // All caution text belongs to one complete Text node. Ensure its full bounds fit the viewport.
        val bounds = rule.onNodeWithText(text).getUnclippedBoundsInRoot()
        val root = rule.onRoot().getUnclippedBoundsInRoot()
        assertTrue("Complete answer must fit the captured viewport", bounds.top >= root.top && bounds.bottom <= root.bottom)
    }
    private fun image(name: String) {
        rule.waitUntil(15000) { rule.activity.hasWindowFocus() }
        rule.waitForIdle()
        File(directory, "$name.png").outputStream().use {
            rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it)
        }
        val physical = requireNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        File(directory, "$name-physical.png").outputStream().use {
            physical.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }
    private fun entry(case: Case) {
        rule.runOnIdle { vm.go(Page.STATUS) }
        actualReady(); refreshActual()
        if (case.step == null) {
            rule.runOnIdle { vm.go(Page.HOME) }
            assertEquals(Page.HOME, vm.state.value.page)
            // The actual sidebar entry from HOME supplies no guide context, even if a guide remains selected.
            rule.onAllNodesWithText(vm.content.copy(case.locale).get("ui_7a087ed8150b"))
                .onFirst().assertIsDisplayed().performClick()
        } else {
            rule.runOnIdle { vm.go(Page.GUIDES) }
            rule.waitUntil(45000) { !vm.state.value.guidesLoading }
            clickText(vm.state.value.guides.single { it.id == guideId }.title)
            if (case.step == 1) clickText(vm.content.copy(case.locale).get("ui_aef613c6612d"))
            assertEquals(case.step, vm.state.value.guideStep)
            assertEquals(guideId, vm.state.value.selectedGuide?.id)
            assertTrue(requireNotNull(vm.state.value.selectedGuide).publicationVerified)
            clickText(vm.content.copy(case.locale).get("ui_af7d9b9636de"))
        }
        assertEquals(Page.ASK, vm.state.value.page)
    }
    private fun send(translation: Boolean): Long {
        rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
        clickTag("ai_consent")
        val previous = vm.state.value.lastAiRequestId
        val started = SystemClock.elapsedRealtime()
        clickTag("ai_send")
        rule.waitUntil(150000) {
            vm.state.value.let { !it.busy && (it.error != null || it.lastAiRequestId != previous &&
                if (translation) it.translationOriginal.isNotEmpty() else it.answerStatus.isNotEmpty()) }
        }
        rule.runOnIdle {
            assertNull(vm.state.value.error)
            assertNotEquals(previous, vm.state.value.lastAiRequestId)
        }
        actualReady()
        return SystemClock.elapsedRealtime() - started
    }
    private fun record(phase: String, case: Case, guide: JSONObject, text: String, elapsed: Long, translation: Boolean) {
        val s = vm.state.value
        val citations = JSONArray()
        for (item in s.officialCitations) citations.put(JSONObject().put("source_id", item.sourceId)
            .put("guide_id", item.guideId).put("profile_id", item.profileId).put("manual_set_id", item.manualSetId)
            .put("source_version", item.sourceVersion).put("url", item.url))
        File(directory, "responses.jsonl").appendText(JSONObject().put("phase", phase).put("elapsed_ms", elapsed)
            .put("recorded_at", Instant.now().toString()).put("state_ttl_ms", BuildConfig.STATE_TTL_MS)
            .put("locale", s.locale).put("question", case.question).put("context_origin", if (case.step == null) "HOME" else "GUIDE")
            .put("context_guide_id", if (case.step == null) JSONObject.NULL else guideId)
            .put("context_step_id", case.step?.let { stepIds[it] } ?: JSONObject.NULL)
            .put("profile_id", s.profile?.id).put("profile_name", s.profile?.name).put("market", s.profile?.market)
            .put("request_id", s.lastAiRequestId).put("answer_request_id", s.answerRequestId)
            .put("status", if (translation) "TRANSLATED" else s.answerStatus)
            .put("mode", if (translation) s.translationMode else s.answerMode)
            .put("ai_provider", if (translation) s.translationProvider.name else s.answerProvider.name)
            .put("ai_model", (if (translation) s.translationModel else s.answerModel) ?: JSONObject.NULL)
            .put("content_kind", if (translation) s.translationKind else "ANSWER")
            .put("source_locale", if (translation) s.translationSourceLocale else s.answerLocale)
            .put("review_status", if (translation) s.translationReview else JSONObject.NULL)
            .put("text", text).put("required_cautions", JSONArray(cautions(guide))).put("citations", citations)
            .put("unit_suffix", ":closing-bundle:v1").put("vehicle_source", s.reading.source.name)
            .put("read_status", s.reading.status.name).put("capability", s.reading.capability.name).put("door", s.reading.value)
            .put("received_at", s.reading.receivedAt?.toString()).put("sdk_get_count", getCount())
            .put("ux_known", s.ux.known).put("ux_restricted", s.ux.restricted).put("ux_flags", s.ux.flags)
            .put("error", s.error ?: JSONObject.NULL).put("activity_window_focused", rule.activity.hasWindowFocus()).put("all_cautions_ui_visible", true).toString() + "\n")
    }

    @Test fun actualClosingCautionsAcrossContextsAndStoredTranslations() {
        assumeTrue(args.getString("validateCautionAnswers") == "true")
        assertFalse(BuildConfig.IS_MOCK)
        assertEquals(34, Build.VERSION.SDK_INT)
        assertEquals("http://10.0.2.2:8001", BuildConfig.SERVER_URL.trimEnd('/'))
        val runId = requireNotNull(args.getString("runId"))
        require(runId.matches(Regex("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")))
        directory = File(rule.activity.filesDir, "qa/$runId/caution-answers")
        check(!directory.exists() && directory.mkdirs())
        val originallyKeptAwake = rule.activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON != 0
        rule.runOnIdle { rule.activity.window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
        var completed = false
        try {
            actualReadyBeforeSession()
            clickTag("profile_$profileId")
            clickText("한국어")
            actualReady()
            val guides = cases.associate { it.locale to rawGuide(it.locale) }
            val expectedModel = args.getString("expectedLocalModel") ?: "qwen3:4b"
            for (case in cases) {
                selectLanguage(case.locale); entry(case)
                val guide = guides.getValue(case.locale)
                rule.onNodeWithText(requireNotNull(vm.state.value.profile).name).assertIsDisplayed()
                rule.onNodeWithTag("question_input").performScrollTo().performTextInput(case.question)
                val askMs = send(false)
                rule.runOnIdle {
                    val s = vm.state.value
                    assertEquals("ANSWERED", s.answerStatus); assertEquals("LIVE", s.answerMode)
                    assertEquals(AiProvider.OLLAMA_LOCAL, s.answerProvider); assertEquals(expectedModel, s.answerModel)
                    assertEquals(case.locale, s.answerLocale); assertEquals(s.lastAiRequestId, s.answerRequestId)
                    assertComplete(s.answer, guide)
                    assertEquals(sourceIds, s.officialCitations.map { it.sourceId })
                    val sources = guide.getJSONArray("sources")
                    assertEquals(2, sources.length())
                    for (i in sourceIds.indices) {
                        val citation = s.officialCitations[i]
                        assertEquals(sourceIds[i], sources.getJSONObject(i).getString("source_id"))
                        assertEquals(profileId, citation.profileId); assertEquals(guideId, citation.guideId)
                        assertEquals(guide.getString("manual_set_id"), citation.manualSetId)
                        assertEquals(guide.getString("source_version"), citation.sourceVersion)
                        assertEquals(sources.getJSONObject(i).getString("url"), citation.url)
                        assertTrue(citation.url.startsWith("https://ownersmanual.hyundai.com/"))
                    }
                }
                refreshActual()
                val answer = vm.state.value.answer
                assertTextVisible(answer, guide)
                image("ask-${case.locale}")
                record("ask-${case.locale}", case, guide, answer, askMs, false)
                clickText(vm.content.copy(case.locale).get("ui_translate_answer"))
                selectLanguage(case.target)
                val target = guides.getValue(case.target)
                val translatedMs = send(true)
                rule.runOnIdle {
                    val s = vm.state.value
                    assertEquals("ANSWER", s.translationKind); assertEquals("LIVE", s.translationMode)
                    assertEquals(AiProvider.STORED_GUIDE, s.translationProvider); assertNull(s.translationModel)
                    assertEquals(case.locale, s.translationSourceLocale); assertEquals(answer, s.translationOriginal)
                    assertComplete(s.translation, target)
                    assertEquals(target.getString("translation_review_status"), s.translationReview)
                    assertEquals(if (case.target == "ko-KR") "NOT_APPLICABLE" else "REVIEWED", s.translationReview)
                }
                refreshActual()
                rule.onNodeWithTag("translation_result_${vm.state.value.translationReview}").performScrollTo().assertIsDisplayed()
                assertTextVisible(vm.state.value.translation, target)
                image("stored-${case.locale}-to-${case.target}")
                record("stored-${case.locale}-to-${case.target}", case, target, vm.state.value.translation, translatedMs, true)
            }
            completed = true
        } catch (failure: Throwable) {
            val s = vm.state.value
            File(directory, "failure.json").writeText(JSONObject().put("error_type", failure.javaClass.simpleName)
                .put("page", s.page.name).put("locale", s.locale).put("ux_known", s.ux.known)
                .put("ux_restricted", s.ux.restricted).put("read_status", s.reading.status.name)
                .put("activity_lifecycle", rule.activity.lifecycle.currentState.name).toString(2))
            runCatching { image("failure") }
            throw failure
        } finally {
            try {
                rule.runOnIdle { vm.endSession() }
                rule.waitUntil(45000) { !vm.state.value.deletionPending }
                rule.runOnIdle {
                    assertEquals(Page.PROFILE, vm.state.value.page); assertFalse(vm.state.value.sessionStarted)
                    assertEquals("", vm.state.value.answer); assertEquals("", vm.state.value.translation)
                    assertEquals("", vm.state.value.lastAiRequestId)
                }
            } finally {
                if (!originallyKeptAwake) rule.runOnIdle { rule.activity.window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
            }
        }
        check(completed)
        File(directory, "result.json").writeText(JSONObject().put("passed", true).put("asks", 3)
            .put("stored_answer_translations", 3).put("question_translation_calls", 0)
            .put("session_end_asserted", true).put("deletion_pending", false).put("paid_provider_called", false)
            .put("physical_vehicle_tested", false).put("native_full_nine_cell_matrix", false)
            .put("screenshot_method", "Compose Window capture and focused-Activity UiAutomation physical default-display capture; independent visual review required")
            .put("test_only_keep_screen_on", true).put("sdk_get_count", getCount()).toString(2))
        File(directory, "done").writeText("pass\n")
    }
    private fun actualReadyBeforeSession() {
        rule.waitUntil(45000) { vm.state.value.ux.let { it.known && !it.restricted } }
    }
}
