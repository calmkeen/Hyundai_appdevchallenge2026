package com.carcue.app

/** In-memory UI authority only. No SDK/HTTP/Compose, persistence, or inferred vehicle state. */
data class AssistantConsentScope(val epoch: Int, val profileId: String?, val locale: String, val page: Page,
    val kind: String, val sourceLocale: String, val draft: String)
data class AssistantActionScope(val consent: AssistantConsentScope, val answerRequestId: String, val guideId: String?)

/** Independent return destinations preserve GUIDE -> ASK -> TRANSLATE nesting. */
data class AssistantReturnPages(val assistant: Page = Page.HOME, val translation: Page = Page.ASK, val language: Page = Page.HOME) {
    fun enteringAssistant(from: Page) = if (from in listOf(Page.ASK, Page.TRANSLATE)) this else copy(assistant = from)
    fun enteringTranslation(from: Page) = if (from == Page.TRANSLATE) this else copy(translation = from)
    fun enteringLanguage(from: Page) = if (from == Page.LANGUAGE) this else copy(language = from)
    fun back(page: Page): Page = when (page) {
        Page.ASK -> assistant
        Page.TRANSLATE -> translation
        Page.LANGUAGE -> language
        Page.GUIDE -> Page.GUIDES
        Page.DETAIL -> Page.STATUS
        else -> Page.HOME
    }
    fun withoutGuide() = copy(assistant = if (assistant == Page.GUIDE) Page.GUIDES else assistant,
        translation = if (translation == Page.GUIDE) Page.GUIDES else translation,
        language = if (language == Page.GUIDE) Page.GUIDES else language)
}

object AssistantBoundaryPolicy {
    fun consentScope(state: UiState) = AssistantConsentScope(state.sessionEpoch, state.profile?.id, state.locale, state.page,
        if (state.page == Page.TRANSLATE) state.translationKind else "QUESTION",
        if (state.page == Page.TRANSLATE) state.translationSourceLocale else "auto",
        if (state.page == Page.TRANSLATE) state.translationDraft else "")

    fun actionScope(state: UiState) = AssistantActionScope(consentScope(state),
        if (state.page == Page.ASK) state.answerRequestId else "",
        if (state.page == Page.GUIDE) state.selectedGuide?.id else null)

    private fun permitted(state: UiState, expected: AssistantActionScope, active: Boolean) =
        active && state.profile != null && state.ux.known && !state.ux.restricted && actionScope(state) == expected

    fun canChooseLanguage(state: UiState, expected: AssistantActionScope, active: Boolean) =
        state.page == Page.LANGUAGE && permitted(state, expected, active)

    fun canSend(state: UiState, expected: AssistantActionScope, active: Boolean, translate: Boolean) =
        state.sessionStarted && !state.busy && state.page == (if (translate) Page.TRANSLATE else Page.ASK) && permitted(state, expected, active)

    fun canRevoke(state: UiState, expected: AssistantConsentScope) = state.sessionStarted &&
        state.page in listOf(Page.ASK, Page.TRANSLATE) && consentScope(state) == expected

    fun canApplyReply(state: UiState, expected: AssistantConsentScope, requestOperation: Int,
        currentOperation: Int, active: Boolean) = active && state.busy && state.sessionStarted &&
        state.ux.known && !state.ux.restricted && requestOperation == currentOperation && consentScope(state) == expected

    fun canOpenTranslation(state: UiState, expected: AssistantActionScope, active: Boolean,
        text: String, kind: String, sourceLocale: String): Boolean {
        if (!state.sessionStarted || state.busy || text.isBlank() || text.length > 3000 || !permitted(state, expected, active)) return false
        return when (kind) {
            "ANSWER" -> state.page == Page.ASK && state.answer.isNotBlank() &&
                text == state.answer && sourceLocale == state.answerLocale && sourceLocale.isNotBlank()
            "GUIDE" -> state.page == Page.GUIDE && state.selectedGuide?.let { guide ->
                guide.publicationVerified && text == guide.body && sourceLocale == guide.locale &&
                    state.profile?.id in guide.profileIds && guide.manualSetId == state.profile?.manualSetId &&
                    guide.sourceVersion == state.profile?.manualVersion
            } == true
            "QUESTION" -> state.page == Page.ASK && sourceLocale == "auto" && text.length <= 2000
            else -> false
        }
    }

    /** Completed answers retain their own locale; an old translation is never relabeled as a new target. */
    fun languageChanged(state: UiState, next: String): UiState = if (state.locale == next) state else state.copy(
        locale = next, translation = "", translationTargetLocale = "", translationReview = "", translationMode = "",
        translationProvider = AiProvider.UNKNOWN, translationModel = null)

    fun replyMatches(expectedId: String, expectedLocale: String, actualId: String, actualLocale: String) =
        expectedId.isNotBlank() && expectedLocale.isNotBlank() && expectedId == actualId && expectedLocale == actualLocale
}
