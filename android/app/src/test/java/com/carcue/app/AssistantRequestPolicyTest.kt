package com.carcue.app

import java.time.Instant
import org.junit.Assert.*
import org.junit.Test

class AssistantRequestPolicyTest {
    private val intent = AssistantIntent("문 상태는 어디에서 확인하나요?", false, "official-profile", "ko-KR")
    private fun requests(): AssistantRequests {
        var id = 0
        return AssistantRequests { "request-${++id}" }
    }

    @Test fun transportRetryReplaysReadingTimestampAndBodyWithoutRebuilding() {
        val requests = requests()
        val original = requests.prepare(intent, "session", false) { "$it|OPEN|2026-11-14T00:00:00Z|VALUE" }
        // A new SDK callback/TTL tick must not change the fingerprint of a request being replayed.
        val retry = requests.prepare(intent, "session", true) { error("Must not rebuild with CLOSED or STALE") }
        assertSame(original, retry)
        assertEquals("request-1|OPEN|2026-11-14T00:00:00Z|VALUE", retry.payload)
        assertEquals(original.requestId, retry.requestId)
    }

    @Test fun providerRetryIsANewRequestEvenWithTheSameQuestion() {
        val requests = requests()
        val original = requests.prepare(intent, "session", false) { "first" }
        assertEquals(AssistantRetry.NEW_REQUEST, AssistantResponsePolicy.ask("TEMPORARILY_UNAVAILABLE").retry)
        val next = requests.prepare(intent, "session", false) { "fresh reading" }
        assertNotEquals(original.requestId, next.requestId)
        assertEquals("fresh reading", next.payload)
    }

    @Test fun changedLanguageContextInputOrSessionNeverReusesAnOldRequestId() {
        val changed = listOf(intent.copy(locale = "en"), intent.copy(input = "A different question"),
            intent.copy(guide = AssistantGuideContext("guide", "step-2")), intent.copy(profileId = "other-profile"),
            intent.copy(translate = true, sourceLocale = "en", contentKind = "ANSWER"))
        for (nextIntent in changed) {
            val requests = requests()
            val first = requests.prepare(intent, "session", false) { "first" }
            assertNotEquals(first.requestId, requests.prepare(nextIntent, "session", true) { "new" }.requestId)
        }
        val requests = requests()
        val first = requests.prepare(intent, "old-session", false) { "first" }
        assertNotEquals(first.requestId, requests.prepare(intent, "new-session", true) { "new" }.requestId)
    }

    @Test fun sessionEndDropsTheInMemoryQuestionSnapshot() {
        val requests = requests()
        val old = requests.prepare(intent, "session", false) { "sensitive text" }
        requests.clear()
        val next = requests.prepare(intent, "session", true) { "new text" }
        assertNotEquals(old.requestId, next.requestId)
        assertEquals("new text", next.payload)
    }

    @Test fun guideContextRequiresExplicitGuidePageAndExcludesPreview() {
        val guide = Guide("door-guide", "Door", "Body", emptyList(), emptyList(), stepIds = listOf("check", "finish"))
        assertEquals(AssistantGuideContext("door-guide", "finish"), AssistantResponsePolicy.guideContext(Page.GUIDE, guide, 1))
        for (page in listOf(Page.HOME, Page.STATUS, Page.ASK, Page.GUIDES)) assertNull(AssistantResponsePolicy.guideContext(page, guide, 1))
        assertNull(AssistantResponsePolicy.guideContext(Page.GUIDE, guide.copy(id = "__preview"), 1))
        assertNull(AssistantResponsePolicy.guideContext(Page.GUIDE, null, 0))
    }

    @Test fun translationsPreserveExplicitSourceTargetAndKindOnRetry() {
        val requests = requests()
        val translation = intent.copy(translate = true, locale = "ja-JP", sourceLocale = "en", contentKind = "ANSWER")
        val first = requests.prepare(translation, "session", false) { "source=en;target=ja-JP;kind=ANSWER" }
        assertSame(first, requests.prepare(translation, "session", true) { error("Do not auto-detect an explicit source again") })
        assertNotEquals(first.requestId, requests.prepare(translation.copy(sourceLocale = "auto"), "session", true) { "auto" }.requestId)
    }

    @Test fun unavailableAskAndTranslationOfferExplicitNewAttempt() {
        assertEquals(AssistantOutcome("AI_UNAVAILABLE", AssistantRetry.NEW_REQUEST), AssistantResponsePolicy.ask("TEMPORARILY_UNAVAILABLE"))
        assertEquals(AssistantOutcome("TRANSLATION_UNAVAILABLE", AssistantRetry.NEW_REQUEST), AssistantResponsePolicy.translation("TEMPORARILY_UNAVAILABLE"))
        assertEquals(AssistantOutcome(), AssistantResponsePolicy.ask("NEED_MORE_INFO"))
        assertEquals(AssistantOutcome(), AssistantResponsePolicy.ask("NO_RELIABLE_SOURCE"))
        assertEquals(AssistantOutcome(), AssistantResponsePolicy.translation("TRANSLATED"))
        assertEquals("SERVER_RESPONSE_INVALID", AssistantResponsePolicy.ask("unexpected").error)
    }

    @Test fun onlyExpiredSessionCodesDiscardAuthenticationAndRequestSnapshot() {
        for (code in listOf("SESSION_INVALID_OR_EXPIRED", "SESSION_ENDED")) {
            assertTrue(AssistantResponsePolicy.expired(401, code))
            assertEquals(AssistantOutcome("SESSION_EXPIRED", AssistantRetry.NEW_REQUEST), AssistantResponsePolicy.http(401, code))
        }
        assertFalse(AssistantResponsePolicy.expired(401, "UNKNOWN"))
        assertFalse(AssistantResponsePolicy.expired(409, "PROFILE_MISMATCH"))
        assertEquals(AssistantRetry.NONE, AssistantResponsePolicy.http(422, "LOCALE_NOT_REGISTERED").retry)
        assertEquals(AssistantRetry.RESEND, AssistantResponsePolicy.http(503, "UNKNOWN").retry)
        assertEquals(AssistantRetry.RESEND, AssistantResponsePolicy.http(429, "REQUEST_LIMIT").retry)
    }

    @Test fun expiredOrMalformedExpiryIsNotReused() {
        val now = Instant.parse("2026-11-14T00:00:00Z")
        assertTrue(AssistantResponsePolicy.sessionExpired("2026-11-13T23:59:59Z", now))
        assertTrue(AssistantResponsePolicy.sessionExpired(now.toString(), now))
        assertTrue(AssistantResponsePolicy.sessionExpired("invalid", now))
        assertFalse(AssistantResponsePolicy.sessionExpired("2026-11-14T00:00:01Z", now))
    }

    @Test fun liveModeAloneNeverClaimsALocalOrExternalAiCall() {
        assertEquals(AiProvider.UNKNOWN, AssistantResponsePolicy.provider("LIVE", ""))
        assertEquals(AiProvider.UNKNOWN, AssistantResponsePolicy.provider("LIVE", "UNRECOGNIZED"))
        assertEquals(AiProvider.NOT_CALLED, AssistantResponsePolicy.provider("MOCK", "OLLAMA_LOCAL"))
        assertEquals(AiProvider.STORED_GUIDE, AssistantResponsePolicy.provider("LIVE", "STORED_GUIDE"))
        assertEquals(AiProvider.OLLAMA_LOCAL, AssistantResponsePolicy.provider("LIVE", "OLLAMA_LOCAL"))
        assertEquals("qwen3:4b", AssistantResponsePolicy.model("qwen3:4b"))
        assertNull(AssistantResponsePolicy.model("model\ninvalid"))
        assertNull(AssistantResponsePolicy.model(""))
    }
}
