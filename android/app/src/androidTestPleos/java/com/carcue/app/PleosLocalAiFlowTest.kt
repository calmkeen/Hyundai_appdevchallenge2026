package com.carcue.app

import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Opt-in, actual local-model HTTP calls. Requires a prewarmed local LIVE backend and parked Pleos AVD.
 * No API keys, SDK SET calls, app scenarios, package-data clears or external paid-provider calls.
 */
@RunWith(AndroidJUnit4::class)
class PleosLocalAiFlowTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val arguments get() = InstrumentationRegistry.getArguments()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private val profileId = "ioniq5-ne1-2024-kr"
    private val guideId = "ioniq5-door-open-check"
    private lateinit var directory: File

    private fun clickText(text: String) = rule.onNodeWithText(text).performScrollTo().performClick()
    private fun clickTag(tag: String) = rule.onNodeWithTag(tag).performScrollTo().performClick()
    private fun locale(tag: String) {
        if (vm.state.value.locale != tag) {
            rule.runOnIdle { vm.language() }
            clickText(vm.content.languages.single { it.tag == tag }.native)
        }
        rule.waitUntil(45000) { vm.state.value.let { it.locale == tag && it.guides.any { g -> g.id == guideId && g.locale == tag } } }
    }
    private fun guide() {
        rule.runOnIdle { vm.go(Page.GUIDES) }
        val title = vm.state.value.guides.single { it.id == guideId }.title
        clickText(title)
        rule.runOnIdle {
            assertTrue(requireNotNull(vm.state.value.selectedGuide).publicationVerified)
            assertEquals(guideId, vm.state.value.selectedGuide?.id)
        }
    }
    private fun rawGuide(locale: String): JSONObject {
        val guides = CarCueApi().guides(profileId, locale)
        return (0 until guides.length()).map { guides.getJSONObject(it) }
            .single { it.getString("guide_id") == guideId }
    }
    private fun answerUnits(guide: JSONObject): Map<String, String> = buildMap {
        put("body", guide.getString("body"))
        val steps = guide.getJSONArray("steps")
        for (i in 0 until steps.length()) {
            val step = steps.getJSONObject(i)
            val cautions = step.getJSONArray("official_cautions")
            val text = listOf(step.getString("body")) + (0 until cautions.length()).map { cautions.getString(it) }
            put("step:${step.getString("step_id")}", text.joinToString("\n"))
        }
    }
    private fun capture(phase: String, elapsed: Long) {
        val s = vm.state.value
        // Fixed test prompts only; no tokens, session IDs, raw SDK payloads or personal vehicle identifiers.
        File(directory, "responses.jsonl").appendText(JSONObject()
            .put("phase", phase).put("elapsed_ms", elapsed).put("locale", s.locale).put("profile_id", s.profile?.id)
            .put("request_id", s.lastAiRequestId).put("vehicle_source", s.reading.source.name)
            .put("status", if (s.page == Page.ASK) s.answerStatus else if (s.translation.isNotBlank()) "TRANSLATED" else "UNAVAILABLE")
            .put("translation_status", if (s.page == Page.ASK) JSONObject.NULL else if (s.translation.isNotBlank()) "TRANSLATED"
                else if (s.error == "TRANSLATION_UNAVAILABLE") "TEMPORARILY_UNAVAILABLE" else "UNKNOWN")
            .put("translation_empty", s.translation.isEmpty()).put("retry_new_request", s.assistantRetry == AssistantRetry.NEW_REQUEST)
            .put("mode", if (s.page == Page.ASK) s.answerMode else s.translationMode)
            .put("ai_provider", if (s.page == Page.ASK) s.answerProvider.name else s.translationProvider.name)
            .put("ai_model", (if (s.page == Page.ASK) s.answerModel else s.translationModel) ?: JSONObject.NULL)
            .put("translation_source_locale", s.translationSourceLocale).put("content_kind", s.translationKind)
            .put("citations", s.citations.size).put("review_status", s.translationReview)
            .put("error", s.error ?: JSONObject.NULL).toString() + "\n")
        rule.onNodeWithTag("ai_processing").performScrollTo()
        rule.waitForIdle()
        File(directory, "$phase.png").outputStream().use { out ->
            rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, out)
        }
    }
    private fun send(translation: Boolean, allowUnavailableQuestion: Boolean = false): Long {
        if (allowUnavailableQuestion) {
            assertTrue(translation)
            assertEquals("QUESTION", vm.state.value.translationKind)
        }
        rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
        clickTag("ai_consent")
        val previous = vm.state.value.lastAiRequestId
        val start = SystemClock.elapsedRealtime()
        clickTag("ai_send")
        rule.waitUntil(150000) {
            vm.state.value.let { !it.busy && (it.error != null || it.lastAiRequestId != previous &&
                if (translation) it.translationOriginal.isNotBlank() else it.answerStatus.isNotBlank()) }
        }
        rule.runOnIdle {
            if (allowUnavailableQuestion && vm.state.value.error == "TRANSLATION_UNAVAILABLE") {
                assertEquals("QUESTION", vm.state.value.translationKind)
            } else assertNull("Actual local AI request failed", vm.state.value.error)
            assertNotEquals(previous, vm.state.value.lastAiRequestId)
            assertEquals(Source.PLEOS, vm.state.value.reading.source)
        }
        return SystemClock.elapsedRealtime() - start
    }
    private fun initialUxFailure() {
        val state = vm.state.value
        val data = JSONObject().put("ux_known", state.ux.known).put("ux_restricted", state.ux.restricted)
            .put("ux_flags", state.ux.flags).put("page", state.page.name)
            .put("activity_lifecycle", rule.activity.lifecycle.currentState.name)
            .put("window_focused", rule.activity.hasWindowFocus())
            .put("screenshot_method", "UiAutomation.takeScreenshot; physical default display; rendering unchanged")
        runCatching {
            val bitmap = InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
            if (bitmap == null) data.put("screenshot_available", false) else {
                File(directory, "initial-ux-physical.png").outputStream().use { out -> bitmap.compress(Bitmap.CompressFormat.PNG, 100, out) }
                data.put("screenshot_available", true)
            }
        }.onFailure { data.put("screenshot_error_type", it.javaClass.simpleName) }
        File(directory, "initial-ux-failure.json").writeText(data.toString(2) + "\n")
    }

    @Test fun actualLocalAskAndQuestionTranslationInThreeLanguages() {
        assumeTrue(arguments.getString("validateLocalAi") == "true")
        runFlow(allowUnavailableQuestion = false)
    }

    /** Separate coverage of safe rejection; this does not establish generated-translation quality. */
    @Test fun actualLocalAskAndGuardedQuestionTranslationInThreeLanguages() {
        assumeTrue(arguments.getString("validateGuardedLocalAi") == "true")
        runFlow(allowUnavailableQuestion = true)
    }

    private fun runFlow(allowUnavailableQuestion: Boolean) {
        assertFalse(BuildConfig.IS_MOCK)
        assertEquals("http://10.0.2.2:8001", BuildConfig.SERVER_URL.trimEnd('/'))
        val runId = requireNotNull(arguments.getString("runId"))
        require(runId.matches(Regex("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")))
        directory = File(rule.activity.filesDir, "qa/$runId/local-ai")
        check(!directory.exists() && directory.mkdirs()) { "Evidence directory must be new" }
        val expectedModel = arguments.getString("expectedLocalModel") ?: "qwen3:4b"
        try {
            try {
                rule.waitUntil(45000) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
            } catch (failure: Exception) {
                runCatching { initialUxFailure() } // Diagnostic collection must never replace the strict failure.
                throw failure
            }
            clickTag("profile_$profileId")
            clickText("한국어")
            rule.waitUntil(60000) { vm.state.value.reading.let { it.source == Source.PLEOS && it.status == ReadStatus.VALUE && it.capability == Capability.SUPPORTED } }
            val questions = listOf(
                Triple("ko-KR", "문을 닫기 전에 무엇을 확인해야 하나요?", "en"),
                Triple("en", "What should I check before closing the indicated door?", "ja-JP"),
                Triple("ja-JP", "表示されたドアを閉める前に何を確認しますか？", "ko-KR"),
            )
            for ((source, question, target) in questions) {
                locale(source)
                guide()
                clickText(vm.content.copy(source).get("ui_af7d9b9636de"))
                rule.onNodeWithTag("question_input").performScrollTo().performTextInput(question)
                val askMs = send(false)
                rule.runOnIdle {
                    val s = vm.state.value
                    assertEquals("LIVE", s.answerMode)
                    assertEquals("ANSWERED", s.answerStatus)
                    assertEquals(source, s.answerLocale)
                    assertEquals(AiProvider.OLLAMA_LOCAL, s.answerProvider)
                    assertEquals(expectedModel, s.answerModel)
                    assertTrue(s.answer.isNotBlank())
                    assertTrue(s.citations.isNotEmpty())
                    assertTrue(s.citations.all { it.second.startsWith("https://ownersmanual.hyundai.com/") })
                }
                capture("ask-$source", askMs)
                clickTag("translate_question")
                locale(target)
                val translateMs = send(true, allowUnavailableQuestion)
                val unavailable = vm.state.value.error == "TRANSLATION_UNAVAILABLE"
                rule.runOnIdle {
                    val s = vm.state.value
                    assertEquals("LIVE", s.translationMode)
                    assertEquals(AiProvider.OLLAMA_LOCAL, s.translationProvider)
                    assertEquals(expectedModel, s.translationModel)
                    assertEquals("QUESTION", s.translationKind)
                    assertEquals(question, s.translationOriginal)
                    assertEquals("UNREVIEWED", s.translationReview)
                    if (unavailable) {
                        assertTrue("Strict scenario still requires TRANSLATED", allowUnavailableQuestion)
                        assertEquals("", s.translation)
                        assertEquals("auto", s.translationSourceLocale)
                        assertEquals(AssistantRetry.NEW_REQUEST, s.assistantRetry)
                    } else {
                        assertNull(s.error)
                        assertEquals(source, s.translationSourceLocale)
                        assertTrue(s.translation.isNotBlank())
                    }
                }
                if (unavailable) {
                    rule.onNodeWithTag("translation_result_UNREVIEWED").assertDoesNotExist()
                    rule.onNodeWithText(vm.content.copy(target).get("ui_241983579b6f")).performScrollTo().assertIsDisplayed()
                    rule.onNodeWithTag("ai_retry").performScrollTo().assertIsDisplayed().assertIsEnabled()
                } else {
                    rule.onNodeWithTag("translation_result_UNREVIEWED").performScrollTo().assertIsDisplayed()
                    rule.onNodeWithText(vm.content.copy(target).get("ui_372ae2e0ffb4")).assertIsDisplayed()
                }
                capture("question-translation-$source-to-$target", translateMs)
            }

            // Safety instructions use canonical reviewed units, never model-generated translations.
            // The last actual answer is Japanese; map exactly the same unit from the public KR guide.
            val originalAnswer = vm.state.value.answer
            val sourceGuide = rawGuide("ja-JP")
            val targetGuide = rawGuide("ko-KR")
            for (key in listOf("guide_id", "manual_set_id", "source_version")) assertEquals(sourceGuide.getString(key), targetGuide.getString(key))
            val unitKey = answerUnits(sourceGuide).entries.single { it.value == originalAnswer }.key
            val expectedAnswer = answerUnits(targetGuide).getValue(unitKey)
            rule.runOnIdle { vm.back() }
            clickText(vm.content.copy("ko-KR").get("ui_translate_answer"))
            val storedAnswerMs = send(true)
            rule.runOnIdle {
                val s = vm.state.value
                assertEquals("ANSWER", s.translationKind)
                assertEquals(AiProvider.STORED_GUIDE, s.translationProvider)
                assertNull(s.translationModel)
                assertEquals("ja-JP", s.translationSourceLocale)
                assertEquals(originalAnswer, s.translationOriginal)
                assertEquals(expectedAnswer, s.translation)
                assertEquals(targetGuide.getString("translation_review_status"), s.translationReview)
                assertEquals("NOT_APPLICABLE", s.translationReview)
            }
            rule.onNodeWithTag("translation_result_NOT_APPLICABLE").performScrollTo().assertIsDisplayed()
            rule.onNodeWithText(vm.content.copy("ko-KR").get("ui_translation_original")).assertIsDisplayed()
            capture("stored-answer-ja-to-ko", storedAnswerMs)

            // A reviewed guide translation must remain distinct from a new model generation.
            locale("ko-KR")
            guide()
            val originalGuide = vm.state.value.selectedGuide!!.body
            val targetEnglishGuide = rawGuide("en")
            clickText(vm.content.copy("ko-KR").get("ui_translate_guide"))
            locale("en")
            val storedMs = send(true)
            rule.runOnIdle {
                assertEquals(AiProvider.STORED_GUIDE, vm.state.value.translationProvider)
                assertNull(vm.state.value.translationModel)
                assertEquals(originalGuide, vm.state.value.translationOriginal)
                assertEquals(targetEnglishGuide.getString("body"), vm.state.value.translation)
                assertEquals("REVIEWED", vm.state.value.translationReview)
            }
            rule.onNodeWithTag("translation_result_REVIEWED").performScrollTo().assertIsDisplayed()
            rule.onNodeWithText(vm.content.copy("en").get("ui_translation_reviewed")).assertIsDisplayed()
            capture("stored-guide-ko-to-en", storedMs)
        } finally {
            rule.runOnIdle { vm.endSession() }
            rule.waitUntil(45000) { !vm.state.value.deletionPending }
        }
        rule.runOnIdle {
            assertEquals(Page.PROFILE, vm.state.value.page)
            assertFalse(vm.state.value.sessionStarted)
            assertEquals("", vm.state.value.lastAiRequestId)
            assertEquals("", vm.state.value.answer)
            assertEquals("", vm.state.value.translation)
        }
        File(directory, "done").writeText("pass\n")
    }
}
