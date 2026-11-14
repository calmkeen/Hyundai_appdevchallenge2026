package com.carcue.app

import org.junit.Assert.*
import org.junit.Test

class GuideSelectionPolicyTest {
    private val profile = GuidePublicationFixtures.profile
    private val original = GuidePublicationFixtures.guide.toGuide().copy(origin = GuideOrigin.BUNDLED)

    @Test fun withdrawnSameScopeClosesTheOpenGuide() {
        assertNull(GuideSelectionPolicy.reconcile(original, profile, original.locale, emptyList()))
    }
    @Test fun correctedSameScopeReplacesTheOriginalAndItsOrigin() {
        val updated = original.copy(body = "Corrected synthetic content", origin = GuideOrigin.SERVER)
        assertEquals(updated, GuideSelectionPolicy.reconcile(original, profile, original.locale, listOf(updated)))
    }
    @Test fun switchingUiLanguageDoesNotWithdrawAnotherLanguageOriginal() {
        assertEquals(original, GuideSelectionPolicy.reconcile(original, profile, "ja-JP", emptyList()))
    }
    @Test fun otherProfileVersionOrAmbiguousResponseCannotKeepAnOpenGuide() {
        assertNull(GuideSelectionPolicy.reconcile(original, profile.copy(manualVersion = "v2"), original.locale, listOf(original)))
        assertNull(GuideSelectionPolicy.reconcile(original, profile.copy(id = "other"), original.locale, listOf(original)))
        assertNull(GuideSelectionPolicy.reconcile(original, profile, original.locale, listOf(original, original)))
    }
    @Test fun unreviewedLayoutExampleDoesNotBecomePublishedContent() {
        val preview = original.copy(publicationVerified = false, origin = GuideOrigin.NONE)
        assertEquals(preview, GuideSelectionPolicy.reconcile(preview, profile, preview.locale, emptyList()))
    }
    @Test fun staleTapCannotReopenWithdrawnOrDifferentLocaleContent() {
        assertNull(GuideSelectionPolicy.resolveOpen(original, profile, original.locale, emptyList()))
        assertNull(GuideSelectionPolicy.resolveOpen(original, profile, "ja-JP", listOf(original)))
    }
    @Test fun tapUsesCurrentCanonicalBodyInsteadOfTheCapturedOldObject() {
        val current = original.copy(body = "Corrected synthetic body", origin = GuideOrigin.SERVER)
        assertEquals(current, GuideSelectionPolicy.resolveOpen(original, profile, original.locale, listOf(current)))
    }
    @Test fun missingSelectedGuideCannotNavigateToAnEmptyGuideScreen() {
        assertEquals(Page.GUIDES, GuideSelectionPolicy.destination(Page.GUIDE, null))
        assertEquals(Page.GUIDE, GuideSelectionPolicy.destination(Page.GUIDE, original))
        assertEquals(Page.ASK, GuideSelectionPolicy.destination(Page.ASK, null))
    }
}
