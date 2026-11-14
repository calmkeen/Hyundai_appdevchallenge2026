package com.carcue.app

import android.graphics.Bitmap
import android.os.SystemClock
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

/** Actual SDK/network flow in a separately installed QA package. No scenario/Reading injection,
 * package-data clearing, SDK SET, key loading or paid-provider calls. Only the host changes the
 * dedicated AVD Console and starts/stops its own local backend. Run the two methods in distinct
 * instrumentation processes, preserving this package's files and the backend SQLite database.
 */
@RunWith(AndroidJUnit4::class)
class PleosOfflineGuidesTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val arguments get() = InstrumentationRegistry.getArguments()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private val profileId = "ioniq5-ne1-2024-kr"
    private val guideId = "ioniq5-door-open-check"
    private val manualSetId = "hyundai-ioniq5-ne1-2024-kr"
    private val manualVersion = "NE1-2024-KR-ko_KR-D202406100040-20240722"
    private val locales = listOf("ko-KR", "en", "ja-JP")
    private val officialUrls = setOf(
        "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/idff13cd5359c.html",
        "https://ownersmanual.hyundai.com/full_webhelp/NE1/2024/ko_KR/id0d6d99a8d21.html",
    )
    private lateinit var directory: File
    private var currentPhase = "PREPARE"

    private fun file(name: String) = File(directory, name)
    private fun signal(name: String) { check(!file(name).exists()); file(name).writeText("ready\n") }
    private fun waitSignal(name: String) {
        val deadline = SystemClock.elapsedRealtime() + 60000
        while (!file(name).exists() && SystemClock.elapsedRealtime() < deadline) Thread.sleep(100)
        check(file(name).exists()) { "Host handshake timed out: $name" }
    }
    private fun prepare(firstProcess: Boolean, requireEmptyCache: Boolean = true) {
        assertFalse(BuildConfig.IS_MOCK)
        assertTrue(BuildConfig.APPLICATION_ID in setOf("com.carcue.app.offlineqa", "com.carcue.app.offlineqa2", "com.carcue.app.offlineqa3"))
        assertEquals("http://10.0.2.2:8001", BuildConfig.SERVER_URL.trimEnd('/'))
        val runId = requireNotNull(arguments.getString("runId"))
        require(runId.matches(Regex("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")))
        directory = File(rule.activity.filesDir, "qa/$runId/offline-guides")
        if (firstProcess) {
            check(!directory.exists() && directory.mkdirs()) { "Evidence directory must be new" }
            @Suppress("DEPRECATION")
            val installation = rule.activity.packageManager.getPackageInfo(BuildConfig.APPLICATION_ID, 0)
            val initiallyEmpty = cacheFiles().isEmpty()
            file("installation.json").writeText(JSONObject()
                .put("applicationId", BuildConfig.APPLICATION_ID)
                .put("firstInstallTime", installation.firstInstallTime)
                .put("lastUpdateTime", installation.lastUpdateTime)
                .put("cacheInitiallyEmpty", initiallyEmpty).toString(2) + "\n")
            assertTrue("QA package must have a valid initial-install timestamp", installation.firstInstallTime > 0)
            assertEquals("Bundled cold-start proof requires a new installation, not an update",
                installation.firstInstallTime, installation.lastUpdateTime)
            if (requireEmptyCache) assertTrue("Fresh QA package must have no downloaded public-guide files", initiallyEmpty)
        } else {
            check(directory.isDirectory && file("phase1-done").readText() == "pass\n")
            check(!file("phase2-events.jsonl").exists() && !file("done").exists())
        }
    }
    private fun clickText(text: String) = rule.onNodeWithText(text).performScrollTo().performClick()
    private fun clickTag(tag: String) = rule.onNodeWithTag(tag).performScrollTo().performClick()
    private fun digest(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }
    private fun cacheFiles(): Map<String, String> = File(rule.activity.filesDir, "public_guides")
        .listFiles().orEmpty().filter { it.isFile }.associate { it.name to digest(it.readBytes()) }

    private fun failureState() {
        if (!::directory.isInitialized || !directory.isDirectory) return
        // This allowlist deliberately excludes answers, request bodies, session/token IDs and raw SDK data.
        runCatching {
            val state = vm.state.value
            file("failure-state.json").writeText(JSONObject().put("phase", currentPhase)
                .put("page", state.page.name).put("locale", state.locale)
                .put("profile_id", state.profile?.id ?: JSONObject.NULL)
                .put("guide_count", state.guides.size).put("guide_titles", JSONArray(state.guides.map { it.title }))
                .put("ux_known", state.ux.known).put("ux_restricted", state.ux.restricted)
                .put("reading_source", state.reading.source.name).put("reading_status", state.reading.status.name)
                .put("error", state.error ?: JSONObject.NULL).toString(2) + "\n")
        }
        runCatching {
            file("failure-state.png").outputStream().use { out ->
                rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, out)
            }
        }
    }
    private inline fun withFailureCapture(block: () -> Unit) {
        var original: Throwable? = null
        try {
            block()
        } catch (failure: Throwable) {
            original = failure
            failureState() // Best effort before endSession clears the failing state.
            throw failure
        } finally {
            try {
                rule.runOnIdle { if (vm.state.value.sessionStarted) vm.endSession() }
            } catch (cleanupFailure: Throwable) {
                // A failed diagnostic or cleanup must never hide the original assertion/timeout.
                if (original == null) throw cleanupFailure else original.addSuppressed(cleanupFailure)
            }
        }
    }

    private fun capture(phase: String, secondProcess: Boolean = false, extra: JSONObject? = null) {
        currentPhase = phase
        rule.waitForIdle()
        val state = vm.state.value
        val event = JSONObject().put("phase", phase).put("device_ms", SystemClock.elapsedRealtime())
            .put("page", state.page.name).put("locale", state.locale)
            .put("profile_id", state.profile?.id ?: JSONObject.NULL)
            .put("guide_id", state.selectedGuide?.id ?: JSONObject.NULL)
            .put("guide_origin", state.selectedGuide?.origin?.name
                ?: state.guides.firstOrNull()?.origin?.name ?: GuideOrigin.NONE.name)
            .put("guide_connection", state.guideConnection).put("guides_loading", state.guidesLoading)
            .put("guide_count", state.guides.size).put("vehicle_source", state.reading.source.name)
            .put("door_status", state.reading.status.name).put("door_value", state.reading.value ?: JSONObject.NULL)
            .put("ux_known", state.ux.known).put("ux_restricted", state.ux.restricted)
            .put("answer_status", state.answerStatus).put("answer_empty", state.answer.isEmpty())
            .put("ai_provider", state.answerProvider.name).put("ai_model", state.answerModel ?: JSONObject.NULL)
            .put("citations", state.citations.size).put("error", state.error ?: JSONObject.NULL)
            .put("deletion_pending", state.deletionPending)
            // Request hash permits exact audit correlation without recording session/token/vehicle payloads.
            .put("request_id_hash", state.lastAiRequestId.takeIf { it.isNotEmpty() }
                ?.let { digest(it.toByteArray(Charsets.UTF_8)) } ?: JSONObject.NULL)
        extra?.let { fields -> fields.keys().forEach { key -> event.put(key, fields.get(key)) } }
        file(if (secondProcess) "phase2-events.jsonl" else "events.jsonl").appendText(event.toString() + "\n")
        file((if (secondProcess) "phase2-" else "") + "$phase.png").outputStream().use { out ->
            rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, out)
        }
    }

    private fun rawGuide(locale: String): JSONObject {
        val assets = rule.activity.assets
        val records = assets.list("guides").orEmpty().filter { it.endsWith(".json") }.map { name ->
            JSONObject(assets.open("guides/$name").bufferedReader().use { it.readText() })
        }
        return records.single { it.getString("guide_id") == guideId && it.getString("locale") == locale
            && it.getString("lifecycle") == "PUBLISHED" }.also {
            assertEquals(manualSetId, it.getString("manual_set_id"))
            assertEquals(manualVersion, it.getString("source_version"))
        }
    }
    private fun strings(array: JSONArray): List<String> = (0 until array.length()).map { array.getString(it) }
    private fun answerUnits(guide: JSONObject): Map<String, String> = buildMap {
        put("body", guide.getString("body"))
        val steps = guide.getJSONArray("steps")
        for (index in 0 until steps.length()) {
            val step = steps.getJSONObject(index)
            put("step:${step.getString("step_id")}", (listOf(step.getString("body"))
                + strings(step.getJSONArray("official_cautions"))).joinToString("\n"))
        }
    }
    private fun assertGuide(guide: Guide, locale: String, origin: GuideOrigin) {
        val raw = rawGuide(locale)
        assertEquals(guideId, guide.id)
        assertEquals(locale, guide.locale)
        assertEquals(origin, guide.origin)
        assertTrue(guide.publicationVerified)
        assertEquals(manualSetId, guide.manualSetId)
        assertEquals(manualVersion, guide.sourceVersion)
        assertEquals(listOf(profileId), guide.profileIds)
        assertEquals(raw.getString("title"), guide.title)
        assertEquals(raw.getString("body"), guide.body)
        val steps = raw.getJSONArray("steps")
        assertEquals((0 until steps.length()).map { steps.getJSONObject(it).getString("step_id") }, guide.stepIds)
        assertEquals((0 until steps.length()).map { steps.getJSONObject(it).let { step ->
            step.getString("title") to step.getString("body") } }, guide.steps)
        assertEquals((0 until steps.length()).map { strings(steps.getJSONObject(it).getJSONArray("official_cautions")) }, guide.cautions)
        val sources = raw.getJSONArray("sources")
        val pairs = (0 until sources.length()).map { sources.getJSONObject(it).let { source ->
            "${source.getString("title")} · ${source.getString("section")}" to source.getString("url") } }
        assertEquals(pairs, guide.sources)
        assertEquals(officialUrls, guide.sources.map { it.second }.toSet())
    }
    private fun awaitGuides(locale: String, origin: GuideOrigin) {
        rule.waitUntil(45000) { vm.state.value.let { state -> state.locale == locale && !state.guidesLoading
            && state.guides.any { it.id == guideId && it.locale == locale && it.origin == origin } } }
        rule.runOnIdle {
            val state = vm.state.value
            val profile = requireNotNull(state.profile)
            assertEquals(profileId, profile.id)
            assertTrue(profile.verified)
            assertEquals(manualSetId, profile.manualSetId)
            assertEquals(manualVersion, profile.manualVersion)
            assertGuide(state.guides.single { it.id == guideId }, locale, origin)
        }
    }
    private fun locale(tag: String, origin: GuideOrigin) {
        if (vm.state.value.locale != tag) {
            rule.runOnIdle { vm.language() }
            clickText(vm.content.languages.single { it.tag == tag }.native)
        }
        awaitGuides(tag, origin)
    }
    private fun guide(locale: String, origin: GuideOrigin) {
        val deadline = SystemClock.elapsedRealtime() + 45000
        fun remaining() = (deadline - SystemClock.elapsedRealtime()).coerceAtLeast(1L)
        rule.waitUntil(remaining()) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
        rule.runOnIdle { vm.go(Page.GUIDES) }
        rule.waitUntil(remaining()) { vm.state.value.let { state -> state.page == Page.GUIDES
            && state.locale == locale && !state.guidesLoading && state.ux.known && !state.ux.restricted
            && state.guides.any { it.id == guideId && it.locale == locale && it.origin == origin } } }
        rule.waitForIdle()
        check(SystemClock.elapsedRealtime() <= deadline) { "Guide UI did not settle within the existing 45-second deadline" }
        rule.onNodeWithText(rawGuide(locale).getString("title")).assertExists()
            .performScrollTo().assertIsDisplayed().performClick()
        rule.runOnIdle {
            assertEquals(Page.GUIDE, vm.state.value.page)
            assertGuide(requireNotNull(vm.state.value.selectedGuide), locale, origin)
        }
        rule.onNodeWithTag("guide_origin_${origin.name}").performScrollTo().assertIsDisplayed()
        assertOfficialSourceNodes()
    }
    private fun assertOfficialSourceNodes() {
        rule.onNodeWithTag("guide_manual_sources").assertExists()
        officialUrls.forEach { url -> rule.onNodeWithText(url).assertExists() }
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
    private fun enterQuestion() {
        clickText(vm.content.copy("ko-KR").get("ui_af7d9b9636de"))
        rule.onNodeWithTag("question_input").performScrollTo()
            .performTextInput("문을 닫기 전에 무엇을 확인해야 하나요?")
        rule.onNodeWithTag("ai_send").performScrollTo().assertIsNotEnabled()
        clickTag("ai_consent")
        clickTag("ai_send")
        rule.waitUntil(150000) { vm.state.value.let { !it.busy && (it.error != null || it.answerStatus.isNotBlank()) } }
    }
    private fun assertCleanSession(pendingDeletion: Boolean) {
        rule.runOnIdle {
            val state = vm.state.value
            assertEquals(Page.PROFILE, state.page)
            assertFalse(state.sessionStarted)
            assertNull(state.profile)
            assertEquals("ko-KR", state.locale)
            assertEquals("", state.answer)
            assertEquals("", state.translation)
            assertEquals("", state.translationDraft)
            assertEquals("", state.lastAiRequestId)
            assertTrue(state.citations.isEmpty())
            assertTrue(state.actions.isEmpty())
            assertNull(state.selectedGuide)
            assertNull(state.reading.value)
            assertEquals(ReadStatus.NOT_REQUESTED, state.reading.status)
            assertEquals(pendingDeletion, state.deletionPending)
        }
    }

    @Test fun firstOfflineThenOnlineThenOfflineKeepsReviewedGuides() {
        assumeTrue(arguments.getString("validateOfflineGuides") == "true")
        prepare(firstProcess = true)
        assertTrue("The separate QA package must begin without a downloaded public-guide cache",
            cacheFiles().isEmpty())
        assertFalse(vm.state.value.deletionPending)
        withFailureCapture {
            rule.waitUntil(45000) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
            rule.onNodeWithTag("profile_$profileId").performScrollTo().performClick()
            clickText("한국어")
            reading("CLOSED")
            for ((tag, phase) in listOf("ko-KR" to "BUNDLED_KO", "en" to "BUNDLED_EN", "ja-JP" to "BUNDLED_JA")) {
                currentPhase = phase
                locale(tag, GuideOrigin.BUNDLED)
                guide(tag, GuideOrigin.BUNDLED)
                assertEquals("UNAVAILABLE", vm.state.value.guideConnection)
                assertTrue(cacheFiles().isEmpty())
                capture(phase)
            }

            locale("ko-KR", GuideOrigin.BUNDLED)
            rule.runOnIdle { vm.go(Page.STATUS) }
            reading("CLOSED")
            rule.onNodeWithTag("related_door_guide").assertDoesNotExist()
            val beforeOpen = vm.state.value.eventLog.count { it.contains("CALLBACK_RECEIVED:RANGE_VERIFIED:value=1") }
            currentPhase = "SDK_BUNDLED_OPEN"
            signal("request-open")
            reading("OPEN")
            rule.waitUntil(15000) { vm.state.value.eventLog.count { it.contains("CALLBACK_RECEIVED:RANGE_VERIFIED:value=1") } > beforeOpen }
            clickTag("related_door_guide")
            rule.runOnIdle { assertGuide(requireNotNull(vm.state.value.selectedGuide), "ko-KR", GuideOrigin.BUNDLED) }
            assertOfficialSourceNodes()
            rule.onNodeWithTag("guide_live_door_status").performScrollTo()
                .assertTextContains(vm.content.copy("ko-KR").get("ui_86b92bfd7c71"), substring = true)
            capture("SDK_BUNDLED_OPEN")
            val beforeClose = vm.state.value.eventLog.count { it.contains("CALLBACK_RECEIVED:RANGE_VERIFIED:value=0") }
            currentPhase = "SDK_BUNDLED_CLOSED"
            signal("request-close")
            reading("CLOSED")
            rule.waitUntil(15000) { vm.state.value.eventLog.count { it.contains("CALLBACK_RECEIVED:RANGE_VERIFIED:value=0") } > beforeClose }
            rule.onNodeWithTag("related_door_guide").assertDoesNotExist()
            rule.onNodeWithTag("guide_live_door_status").performScrollTo()
                .assertTextContains(vm.content.copy("ko-KR").get("ui_f70cce500477"), substring = true)
            capture("SDK_BUNDLED_CLOSED")

            currentPhase = "OFFLINE_AI_FAILURE"
            enterQuestion()
            rule.runOnIdle {
                val state = vm.state.value
                assertNotNull(state.error)
                assertEquals("", state.answer)
                assertTrue(state.citations.isEmpty())
                assertTrue(state.actions.isEmpty())
                assertFalse(state.busy)
            }
            rule.onNodeWithTag("assistant_saved_guides").performScrollTo().assertIsDisplayed().assertIsEnabled()
            capture("OFFLINE_AI_FAILURE")
            currentPhase = "OFFLINE_SAVED_GUIDE"
            clickTag("assistant_saved_guides")
            rule.waitUntil(15000) { vm.state.value.page in listOf(Page.GUIDE, Page.GUIDES) }
            if (vm.state.value.page == Page.GUIDES) guide("ko-KR", GuideOrigin.BUNDLED)
            rule.runOnIdle { assertGuide(requireNotNull(vm.state.value.selectedGuide), "ko-KR", GuideOrigin.BUNDLED) }
            assertOfficialSourceNodes()
            capture("OFFLINE_SAVED_GUIDE")

            signal("request-online")
            waitSignal("online-ready")
            for ((tag, phase) in listOf("ko-KR" to "SERVER_KO", "en" to "SERVER_EN", "ja-JP" to "SERVER_JA")) {
                currentPhase = phase
                if (vm.state.value.locale != tag) {
                    rule.runOnIdle { vm.language() }
                    clickText(vm.content.languages.single { it.tag == tag }.native)
                }
                rule.runOnIdle { vm.go(Page.GUIDES) }
                rule.waitUntil(45000) { !vm.state.value.guidesLoading }
                clickTag("refresh_guides")
                awaitGuides(tag, GuideOrigin.SERVER)
                assertEquals("CONNECTED", vm.state.value.guideConnection)
                val profile = requireNotNull(vm.state.value.profile)
                assertGuide(vm.content.cachedGuides(profile, tag).single { it.id == guideId }, tag, GuideOrigin.CACHE)
                assertTrue(cacheFiles().isNotEmpty())
                guide(tag, GuideOrigin.SERVER)
                capture(phase)
            }
            currentPhase = "LIVE_LOCAL_ASK_KO"
            locale("ko-KR", GuideOrigin.SERVER)
            guide("ko-KR", GuideOrigin.SERVER)
            enterQuestion()
            rule.runOnIdle {
                val state = vm.state.value
                assertNull(state.error)
                assertEquals("ANSWERED", state.answerStatus)
                assertEquals("LIVE", state.answerMode)
                assertEquals(AiProvider.OLLAMA_LOCAL, state.answerProvider)
                assertEquals(arguments.getString("expectedLocalModel") ?: "qwen3:4b", state.answerModel)
                val raw = rawGuide("ko-KR")
                val unit = answerUnits(raw).entries.single { it.value == state.answer }.key
                val sourceIds = if (unit == "body") strings(raw.getJSONArray("sources").let { sources ->
                    JSONArray((0 until sources.length()).map { sources.getJSONObject(it).getString("source_id") })
                }) else {
                    val steps = raw.getJSONArray("steps")
                    val step = (0 until steps.length()).map { steps.getJSONObject(it) }
                        .single { "step:${it.getString("step_id")}" == unit }
                    strings(step.getJSONArray("source_ids"))
                }
                val sources = raw.getJSONArray("sources")
                val expected = (0 until sources.length()).map { sources.getJSONObject(it) }
                    .filter { it.getString("source_id") in sourceIds }
                    .map { it.getString("title") to it.getString("url") }.toSet()
                assertEquals(expected, state.citations.toSet())
                assertEquals(state.citations.size, state.citations.toSet().size)
            }
            rule.onNodeWithTag("ai_processing").performScrollTo().assertIsDisplayed()
            capture("LIVE_LOCAL_ASK_KO")

            val publicFiles = cacheFiles()
            currentPhase = "OFFLINE_SESSION_ENDED"
            signal("request-offline-again")
            waitSignal("offline-ready")
            rule.runOnIdle { vm.endSession() }
            rule.waitUntil(45000) { vm.state.value.deletionPending }
            assertCleanSession(pendingDeletion = true)
            assertEquals(publicFiles, cacheFiles())
            capture("OFFLINE_SESSION_ENDED")
            currentPhase = "NEW_USER_CACHE_EN"
            rule.onNodeWithTag("profile_$profileId").performScrollTo().performClick()
            clickText(vm.content.languages.single { it.tag == "en" }.native)
            reading("CLOSED")
            awaitGuides("en", GuideOrigin.CACHE)
            guide("en", GuideOrigin.CACHE)
            assertEquals("UNAVAILABLE", vm.state.value.guideConnection)
            assertEquals("", vm.state.value.answer)
            assertEquals("", vm.state.value.translation)
            assertTrue(vm.state.value.deletionPending)
            capture("NEW_USER_CACHE_EN")
            rule.runOnIdle { vm.endSession() }
            assertCleanSession(pendingDeletion = true)
            assertEquals(publicFiles, cacheFiles())
        }
        file("phase1-done").writeText("pass\n")
    }

    @Test fun restartRecoversPendingDeletionAndPublicCache() {
        assumeTrue(arguments.getString("validateOfflineDeletion") == "true")
        prepare(firstProcess = false)
        withFailureCapture {
            currentPhase = "RESTART_QUEUE_PENDING"
            rule.waitUntil(45000) { vm.state.value.deletionPending }
            assertCleanSession(pendingDeletion = true)
            capture("RESTART_QUEUE_PENDING", secondProcess = true)
            currentPhase = "RESTART_CACHE_PRESERVED"
            val publicFiles = cacheFiles()
            assertTrue(publicFiles.isNotEmpty())
            // A newly constructed repository reads actual persisted files after the host restarted this process.
            val content = ContentRepository(rule.activity)
            val profile = content.profiles.single { it.id == profileId }
            val cached = content.cachedGuides(profile, "en")
            assertGuide(cached.single { it.id == guideId }, "en", GuideOrigin.CACHE)
            capture("RESTART_CACHE_PRESERVED", secondProcess = true,
                extra = JSONObject().put("cache_en_count", cached.size).put("cache_en_origin", GuideOrigin.CACHE.name))
            currentPhase = "SERVER_DELETION_CONFIRMED"
            signal("request-recovery-online")
            waitSignal("recovery-online-ready")
            rule.onNodeWithTag("deletion_retry").performScrollTo().assertIsDisplayed().assertIsEnabled().performClick()
            rule.waitUntil(45000) { !vm.state.value.deletionPending }
            assertCleanSession(pendingDeletion = false)
            assertEquals(publicFiles, cacheFiles())
            capture("SERVER_DELETION_CONFIRMED", secondProcess = true)
        }
        file("done").writeText("pass\n")
    }

    /** Focused diagnosis only: preserves the existing QA cache and unconfirmed deletion queue. */
    @Test fun cachedSessionCanReenterAfterEnd() {
        assumeTrue(arguments.getString("validateCachedReentry") == "true")
        prepare(firstProcess = true, requireEmptyCache = false)
        withFailureCapture {
            val publicFiles = cacheFiles()
            assertTrue("Diagnostic requires the preserved downloaded cache", publicFiles.isNotEmpty())
            assertCleanSession(pendingDeletion = true)
            for (phase in listOf("CACHED_REENTRY_FIRST", "CACHED_REENTRY_SECOND")) {
                currentPhase = phase
                rule.waitUntil(45000) { vm.state.value.ux.known && !vm.state.value.ux.restricted }
                rule.onNodeWithTag("profile_$profileId").performScrollTo().performClick()
                clickText(vm.content.languages.single { it.tag == "en" }.native)
                reading("CLOSED")
                awaitGuides("en", GuideOrigin.CACHE)
                guide("en", GuideOrigin.CACHE)
                assertEquals("UNAVAILABLE", vm.state.value.guideConnection)
                assertTrue(vm.state.value.deletionPending)
                assertEquals("", vm.state.value.answer)
                assertEquals("", vm.state.value.translation)
                capture(phase)
                rule.runOnIdle { vm.endSession() }
                assertCleanSession(pendingDeletion = true)
                assertEquals(publicFiles, cacheFiles())
            }
        }
        file("cached-reentry-done").writeText("pass\n")
    }
}
