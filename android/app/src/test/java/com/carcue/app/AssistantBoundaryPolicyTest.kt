package com.carcue.app

import org.junit.Assert.*
import org.junit.Test

/** Synthetic state-boundary tests. No SDK/HTTP/AI values are injected into the app. */
class AssistantBoundaryPolicyTest {
    private val profile = Profile("official", "Vehicle", 2024, "KR", true, "manual", "v1")
    private val guide = Guide("door-guide", "Guide", "Registered original", emptyList(), emptyList(),
        locale = "ko-KR", manualSetId = "manual", sourceVersion = "v1", profileIds = listOf("official"), publicationVerified = true)
    private fun state(page: Page = Page.ASK) = UiState(page = page, sessionEpoch = 7, profile = profile,
        locale = "ko-KR", sessionStarted = true, reading = Reading(source = Source.MOCK), ux = UxState(true, false),
        answer = "Complete original answer", answerLocale = "ko-KR", answerStatus = "ANSWERED", answerRequestId = "answer-1",
        selectedGuide = guide, guides = listOf(guide))
    private fun translation() = state(Page.TRANSLATE).copy(translationDraft = "Original source", translationOriginal = "Original source",
        translationKind = "ANSWER", translationSourceLocale = "ko-KR", translation = "Earlier English translation",
        translationTargetLocale = "en", translationReview = "REVIEWED", translationMode = "LIVE",
        translationProvider = AiProvider.STORED_GUIDE)

    @Test fun choosingANewLanguageClearsOnlyTheOldTranslationAndItsResultMetadata() {
        val before = translation()
        val after = AssistantBoundaryPolicy.languageChanged(before, "ja-JP")
        assertEquals("ja-JP", after.locale)
        assertEquals("", after.translation); assertEquals("", after.translationTargetLocale)
        assertEquals("", after.translationReview); assertEquals("", after.translationMode)
        assertEquals(AiProvider.UNKNOWN, after.translationProvider); assertNull(after.translationModel)
        assertEquals(before.translationOriginal, after.translationOriginal)
        assertEquals(before.translationDraft, after.translationDraft)
        assertEquals(before.translationSourceLocale, after.translationSourceLocale)
        assertEquals(before.translationKind, after.translationKind)
        assertEquals(before.answer, after.answer); assertEquals("ko-KR", after.answerLocale)
        assertEquals(before.profile, after.profile); assertEquals(before.selectedGuide, after.selectedGuide)
    }

    @Test fun selectingTheSameLanguageDoesNotDestroyACompletedResult() {
        val state = translation()
        assertSame(state, AssistantBoundaryPolicy.languageChanged(state, state.locale))
    }

    @Test fun consentNeverCarriesAcrossSessionProfileLocalePageKindSourceOrOriginalDraft() {
        val original = translation()
        val consent = AssistantBoundaryPolicy.consentScope(original)
        for (changed in listOf(original.copy(sessionEpoch = 8), original.copy(profile = profile.copy(id = "other")),
            original.copy(locale = "en"), original.copy(page = Page.ASK), original.copy(translationKind = "GUIDE"),
            original.copy(translationSourceLocale = "en"), original.copy(translationDraft = "Another original"))) {
            assertNotEquals(consent, AssistantBoundaryPolicy.consentScope(changed))
            assertFalse(AssistantBoundaryPolicy.canRevoke(changed, consent))
        }
    }

    @Test fun sdkUpdatesAndRequestProgressDoNotPretendThatConsentWasRevoked() {
        val original = state()
        val progressed = original.copy(busy = true, lastAiRequestId = "new-request", answerRequestId = "", answer = "",
            reading = original.reading.copy(status = ReadStatus.ERROR, errorCode = "Synthetic read error"))
        assertEquals(AssistantBoundaryPolicy.consentScope(original), AssistantBoundaryPolicy.consentScope(progressed))
        assertTrue(AssistantBoundaryPolicy.canRevoke(progressed, AssistantBoundaryPolicy.consentScope(original)))
    }

    @Test fun lateLanguageSelectionRequiresTheCurrentLanguagePageAndActualAllowedUx() {
        val language = state(Page.LANGUAGE).copy(sessionStarted = false)
        val scope = AssistantBoundaryPolicy.actionScope(language)
        assertTrue(AssistantBoundaryPolicy.canChooseLanguage(language, scope, true))
        for (changed in listOf(language.copy(page = Page.HOME), language.copy(sessionEpoch = 8),
            language.copy(locale = "en"), language.copy(profile = null), language.copy(ux = UxState()),
            language.copy(ux = UxState(true, true, 80)))) {
            assertFalse(AssistantBoundaryPolicy.canChooseLanguage(changed, scope, true))
        }
        assertFalse(AssistantBoundaryPolicy.canChooseLanguage(language, scope, false))
    }

    @Test fun sendRequiresTheCurrentAssistantPageSessionAndUxAtTheTap() {
        val original = state()
        val scope = AssistantBoundaryPolicy.actionScope(original)
        assertTrue(AssistantBoundaryPolicy.canSend(original, scope, true, false))
        for (changed in listOf(original.copy(sessionStarted = false), original.copy(sessionEpoch = 8),
            original.copy(profile = profile.copy(id = "other")), original.copy(page = Page.TRANSLATE),
            original.copy(locale = "ja-JP"), original.copy(ux = UxState()), original.copy(ux = UxState(true, true, 80)),
            original.copy(answerRequestId = "a-new-answer"), original.copy(busy = true))) {
            assertFalse(AssistantBoundaryPolicy.canSend(changed, scope, true, false))
        }
        assertFalse(AssistantBoundaryPolicy.canSend(original, scope, false, false))
        assertFalse(AssistantBoundaryPolicy.canSend(original, scope, true, true))
    }

    @Test fun oldAnswerTranslationCannotOpenAfterTheAnswerOrItsRequestWasReplaced() {
        val original = state()
        val scope = AssistantBoundaryPolicy.actionScope(original)
        assertTrue(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, original.answer, "ANSWER", "ko-KR"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original.copy(answer = "Different answer"), scope, true, original.answer, "ANSWER", "ko-KR"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original.copy(answerRequestId = "answer-2"), scope, true, original.answer, "ANSWER", "ko-KR"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, original.answer, "ANSWER", "en"))
    }

    @Test fun guideTranslationRequiresTheCurrentPublishedBodyAndManualScope() {
        val original = state(Page.GUIDE)
        val scope = AssistantBoundaryPolicy.actionScope(original)
        assertTrue(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, guide.body, "GUIDE", guide.locale))
        for (changed in listOf(original.copy(selectedGuide = null), original.copy(selectedGuide = guide.copy(body = "Updated body")),
            original.copy(selectedGuide = guide.copy(publicationVerified = false)),
            original.copy(selectedGuide = guide.copy(sourceVersion = "v2")), original.copy(page = Page.ASK))) {
            assertFalse(AssistantBoundaryPolicy.canOpenTranslation(changed, scope, true, guide.body, "GUIDE", guide.locale))
        }
    }

    @Test fun noTranslationActionCanBypassUnknownRestrictedBackgroundOrEndedState() {
        val original = state()
        val scope = AssistantBoundaryPolicy.actionScope(original)
        for (changed in listOf(original.copy(sessionStarted = false), original.copy(sessionEpoch = 8),
            original.copy(ux = UxState()), original.copy(ux = UxState(true, true, 80)), original.copy(busy = true))) {
            assertFalse(AssistantBoundaryPolicy.canOpenTranslation(changed, scope, true, original.answer, "ANSWER", "ko-KR"))
        }
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original, scope, false, original.answer, "ANSWER", "ko-KR"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, "input", "UNKNOWN", "auto"))
    }

    @Test fun aTypedQuestionCanOnlyOpenFromTheCurrentAskPageWithAutoDetection() {
        val original = state()
        val scope = AssistantBoundaryPolicy.actionScope(original)
        assertTrue(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, "Typed question?", "QUESTION", "auto"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, "Typed question?", "QUESTION", "en"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, " ", "QUESTION", "auto"))
        assertFalse(AssistantBoundaryPolicy.canOpenTranslation(original, scope, true, "x".repeat(2001), "QUESTION", "auto"))
    }

    @Test fun lateRepliesAreRejectedAfterLocaleUxEndBackgroundPageAndNewOperationBoundaries() {
        val original = state().copy(busy = true)
        val scope = AssistantBoundaryPolicy.consentScope(original)
        assertTrue(AssistantBoundaryPolicy.canApplyReply(original, scope, 4, 4, true))
        for (changed in listOf(original.copy(locale = "en"), original.copy(ux = UxState()),
            original.copy(ux = UxState(true, true, 80)), original.copy(sessionStarted = false),
            original.copy(sessionEpoch = 8), original.copy(page = Page.LANGUAGE), original.copy(busy = false))) {
            assertFalse(AssistantBoundaryPolicy.canApplyReply(changed, scope, 4, 4, true))
        }
        assertFalse(AssistantBoundaryPolicy.canApplyReply(original, scope, 4, 5, true))
        assertFalse(AssistantBoundaryPolicy.canApplyReply(original, scope, 4, 4, false))
    }

    @Test fun aTranslationReplyCannotReplaceANewerSourceOrKind() {
        val original = translation().copy(busy = true)
        val scope = AssistantBoundaryPolicy.consentScope(original)
        for (changed in listOf(original.copy(translationKind = "QUESTION"), original.copy(translationSourceLocale = "ja-JP"),
            original.copy(translationDraft = "Another source"))) {
            assertFalse(AssistantBoundaryPolicy.canApplyReply(changed, scope, 1, 1, true))
        }
    }

    @Test fun matchingRequestIdCannotHideAWrongAnswerOrTranslationTargetLocale() {
        assertTrue(AssistantBoundaryPolicy.replyMatches("request", "ja-JP", "request", "ja-JP"))
        assertFalse(AssistantBoundaryPolicy.replyMatches("request", "ja-JP", "request", "en"))
        assertFalse(AssistantBoundaryPolicy.replyMatches("request", "ja-JP", "old-request", "ja-JP"))
        assertFalse(AssistantBoundaryPolicy.replyMatches("request", "ja-JP", "request", ""))
    }

    @Test fun translationAndLanguageReturnsDoNotOverwriteTheOriginalGuideReturnOrStep() {
        val original = state(Page.GUIDE).copy(guideStep = 1)
        val routes = AssistantReturnPages().enteringAssistant(Page.GUIDE)
            .enteringTranslation(Page.ASK).enteringLanguage(Page.TRANSLATE)
        assertEquals(Page.TRANSLATE, routes.back(Page.LANGUAGE))
        val askAgain = original.copy(page = routes.back(Page.TRANSLATE), locale = "en")
        assertEquals(Page.ASK, askAgain.page)
        val guideAgain = askAgain.copy(page = routes.back(askAgain.page))
        assertEquals(Page.GUIDE, guideAgain.page)
        assertEquals(original.selectedGuide, guideAgain.selectedGuide)
        assertEquals(1, guideAgain.guideStep)
    }

    @Test fun directGuideTranslationReturnsToTheGuideAndRepeatedEntryDoesNotCreateASelfLoop() {
        val routes = AssistantReturnPages().enteringAssistant(Page.GUIDE).enteringAssistant(Page.ASK)
            .enteringTranslation(Page.GUIDE).enteringTranslation(Page.TRANSLATE)
            .enteringLanguage(Page.TRANSLATE).enteringLanguage(Page.LANGUAGE)
        assertEquals(Page.GUIDE, routes.back(Page.ASK))
        assertEquals(Page.GUIDE, routes.back(Page.TRANSLATE))
        assertEquals(Page.TRANSLATE, routes.back(Page.LANGUAGE))
    }

    @Test fun withdrawnGuidesAreRemovedFromEveryReturnPath() {
        val routes = AssistantReturnPages(Page.GUIDE, Page.GUIDE, Page.GUIDE).withoutGuide()
        for (page in listOf(Page.ASK, Page.TRANSLATE, Page.LANGUAGE)) assertEquals(Page.GUIDES, routes.back(page))
    }

    @Test fun aNewSessionHasNoPreviousUsersReturnPath() {
        val old = AssistantReturnPages(Page.GUIDE, Page.DETAIL, Page.TRANSLATE)
        val fresh = AssistantReturnPages()
        assertNotEquals(old, fresh)
        assertEquals(Page.HOME, fresh.back(Page.ASK)); assertEquals(Page.ASK, fresh.back(Page.TRANSLATE))
        assertEquals(Page.HOME, fresh.back(Page.LANGUAGE))
    }
}
