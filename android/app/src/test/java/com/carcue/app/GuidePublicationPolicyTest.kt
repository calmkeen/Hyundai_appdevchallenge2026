package com.carcue.app

import org.junit.Assert.*
import org.junit.Test

/** Synthetic metadata only; these fixtures are not approved vehicle instructions or live API evidence. */
internal object GuidePublicationFixtures {
    val profile = Profile("fixture-car", "Synthetic vehicle", 2024, "KR", true, "fixture-manual", "v1")
    val locales = setOf("ko-KR", "en", "ja-JP")
    val source = PublishedGuideSource("source-1", "Synthetic source", "https://example.test/manual#section-1", "v1", "section-1", "VERIFIED")
    val step = PublishedGuideStep("step-1", 1, "Synthetic step", "Fixture text only.", listOf("Synthetic caution."), listOf("source-1"))
    val guide = PublishedGuideRecord("guide-1", listOf(profile.id), "fixture-manual", "v1", "fixture-topic",
        "Synthetic guide", "Not vehicle instructions.", "ko-KR", "ko-KR", "PUBLISHED", "NOT_APPLICABLE", null,
        listOf(source), listOf(step))
    fun policy(profiles: List<Profile> = listOf(profile)) = GuidePublicationPolicy(profiles, locales)
}

class GuidePublicationPolicyTest {
    private val f = GuidePublicationFixtures
    private fun accepted(guide: PublishedGuideRecord, profile: Profile = f.profile, locale: String = guide.locale) =
        f.policy().published(listOf(guide), profile, locale)
    private fun rejected(guide: PublishedGuideRecord) = assertTrue("Must reject $guide", accepted(guide).isEmpty())

    @Test fun originalReviewedMetadataPreservesDisplayedContent() {
        val guide = accepted(f.guide).single().toGuide()
        assertEquals(f.guide.id, guide.id)
        assertEquals(f.guide.title, guide.title)
        assertEquals(listOf(f.step.title to f.step.body), guide.steps)
        assertEquals(listOf(f.step.id), guide.stepIds)
        assertEquals(listOf(f.step.officialCautions), guide.cautions)
        assertEquals(f.source.url, guide.sources.single().second)
        assertEquals(f.guide.manualSetId, guide.manualSetId)
        assertEquals(f.guide.sourceVersion, guide.sourceVersion)
        assertEquals(f.guide.profileIds, guide.profileIds)
        assertTrue(guide.publicationVerified)
    }

    @Test fun translatedContentRequiresReviewAndGlossaryVersion() {
        val translated = f.guide.copy(locale = "en", translationReviewStatus = "REVIEWED", glossaryVersion = "fixture-glossary-v1")
        assertEquals(listOf(translated), accepted(translated))
        rejected(translated.copy(translationReviewStatus = "UNREVIEWED"))
        rejected(translated.copy(translationReviewStatus = "NOT_APPLICABLE"))
        rejected(translated.copy(glossaryVersion = null))
        rejected(translated.copy(glossaryVersion = "  "))
    }

    @Test fun originalContentAlsoRejectsUnreviewedTranslationStatus() {
        rejected(f.guide.copy(translationReviewStatus = "UNREVIEWED"))
        assertEquals(listOf(f.guide.copy(translationReviewStatus = "REVIEWED")), accepted(f.guide.copy(translationReviewStatus = "REVIEWED")))
    }

    @Test fun callerMustUseTheKnownVerifiedCatalogIdentity() {
        val variants = listOf(f.profile.copy(id = "unknown"), f.profile.copy(verified = false),
            f.profile.copy(year = 2025), f.profile.copy(market = "GB"), f.profile.copy(manualSetId = "other"),
            f.profile.copy(manualVersion = "v2"))
        variants.forEach { assertTrue("Must reject copied profile $it", accepted(f.guide, it).isEmpty()) }
        listOf(f.profile.copy(verified = false), f.profile.copy(manualSetId = null),
            f.profile.copy(manualVersion = " "), f.profile.copy(market = ""), f.profile.copy(year = 0)).forEach {
            assertTrue(f.policy(listOf(it)).published(listOf(f.guide), it, "ko-KR").isEmpty())
        }
    }

    @Test fun everyLinkedProfileMustBeKnownAndUseTheSameReviewedManual() {
        rejected(f.guide.copy(profileIds = listOf("unknown")))
        rejected(f.guide.copy(profileIds = listOf(f.profile.id, "unknown")))
        val other = f.profile.copy(id = "fixture-other", manualVersion = "v2")
        val linked = f.guide.copy(profileIds = listOf(f.profile.id, other.id))
        assertTrue(f.policy(listOf(f.profile, other)).published(listOf(linked), f.profile, "ko-KR").isEmpty())
        val unverified = other.copy(manualVersion = "v1", verified = false)
        assertTrue(f.policy(listOf(f.profile, unverified)).published(listOf(linked), f.profile, "ko-KR").isEmpty())
    }

    @Test fun localeAndManualVersionNeverFallBack() {
        assertTrue(accepted(f.guide, locale = "en").isEmpty())
        rejected(f.guide.copy(locale = "unknown"))
        rejected(f.guide.copy(sourceLocale = "unknown"))
        rejected(f.guide.copy(manualSetId = "other"))
        rejected(f.guide.copy(sourceVersion = "v2"))
    }

    @Test fun onlyPublishedContentWithNonblankIdentityAndTextIsVisible() {
        listOf("PLANNED", "DRAFT", "REVIEWED").forEach { rejected(f.guide.copy(lifecycle = it)) }
        rejected(f.guide.copy(id = " "))
        rejected(f.guide.copy(topic = " "))
        rejected(f.guide.copy(title = " "))
        rejected(f.guide.copy(body = " "))
    }

    @Test fun everySourceMustHaveVerifiedVersionSectionAndUsableHttpsUrl() {
        val invalidSources = listOf(f.source.copy(id = " "), f.source.copy(title = " "), f.source.copy(verificationStatus = "UNVERIFIED"),
            f.source.copy(version = null), f.source.copy(version = "v2"), f.source.copy(section = " ")) +
            listOf("http://example.test/manual", "https://", "https:///manual", "https://user:secret@example.test/manual",
                "https://example.test:0/manual", "https://example.test:70000/manual", "https://exa mple.test/manual", "relative/manual",
                "https://localhost/manual", "https://127.0.0.1/manual", "https://[::1]/manual", "https://example.test:/manual",
                "https://example.test/%0a", "https://example.test/%7F", "https://example.test\\manual",
                "https://-invalid.example/manual", "https://invalid_.example/manual", "https://example..test/manual")
                .map { f.source.copy(url = it) }
        invalidSources.forEach { rejected(f.guide.copy(sources = listOf(it))) }
        rejected(f.guide.copy(sources = emptyList()))
        assertEquals(1, accepted(f.guide.copy(sources = listOf(f.source.copy(url = "https://매뉴얼.example.test:443/manual#section")))).size)
    }

    @Test fun duplicateGuideSourceAndStepIdsAreRejected() {
        assertTrue(f.policy().published(listOf(f.guide, f.guide.copy(title = "Conflicting duplicate")), f.profile, "ko-KR").isEmpty())
        rejected(f.guide.copy(sources = listOf(f.source, f.source)))
        rejected(f.guide.copy(steps = listOf(f.step, f.step.copy(order = 2))))
    }

    @Test fun otherLanguageVersionAndDraftWithSameIdDoNotHideThePublishedGuide() {
        val translated = f.guide.copy(locale = "en", translationReviewStatus = "REVIEWED", glossaryVersion = "fixture-glossary-v1")
        val anotherVersion = f.guide.copy(sourceVersion = "v2")
        val anotherManual = f.guide.copy(manualSetId = "fixture-other-manual")
        val draft = f.guide.copy(lifecycle = "DRAFT")
        val records = listOf(f.guide, translated, anotherVersion, anotherManual, draft)
        assertEquals(listOf(f.guide), f.policy().published(records, f.profile, "ko-KR"))
        assertEquals(listOf(translated), f.policy().published(records, f.profile, "en"))
    }

    @Test fun malformedPublishedDuplicateCannotMakeTheValidRecordAppearUnique() {
        // The malformed wire record has the same four identity strings, but title=null prevents DTO decoding.
        data class WireRecord(val identity: PublishedGuideIdentity?, val decoded: PublishedGuideRecord?)
        val valid = WireRecord(f.guide.publicationIdentity(), f.guide)
        val malformed = WireRecord(f.guide.publicationIdentity(), null)
        val decoded = decodeUnambiguousPublishedGuides(listOf(valid, malformed), { it.identity }, { it.decoded })
        assertTrue(decoded.isEmpty())
        // An unrelated malformed record or draft does not collide with the valid published identity.
        assertEquals(listOf(f.guide), decodeUnambiguousPublishedGuides(
            listOf(valid, malformed.copy(identity = null)), { it.identity }, { it.decoded }))
    }

    @Test fun stepsMustBeOrderedAndCiteExistingSources() {
        val invalidSteps = listOf(f.step.copy(id = " "), f.step.copy(order = 0), f.step.copy(order = 2),
            f.step.copy(title = " "), f.step.copy(body = " "),
            f.step.copy(sourceIds = emptyList()), f.step.copy(sourceIds = listOf("unknown")))
        invalidSteps.forEach { rejected(f.guide.copy(steps = listOf(it))) }
        val second = f.step.copy(id = "step-2", order = 2)
        assertEquals(1, accepted(f.guide.copy(steps = listOf(f.step, second))).size)
        rejected(f.guide.copy(steps = listOf(second, f.step)))
    }

    @Test fun contractAllowsGuidesWithoutStepInstructions() {
        assertEquals(1, accepted(f.guide.copy(steps = emptyList())).size)
    }

    @Test fun allowedRepeatedReferencesAndEmptyCautionsDoNotHideAReviewedGuide() {
        val guide = f.guide.copy(profileIds = listOf(f.profile.id, f.profile.id),
            steps = listOf(f.step.copy(sourceIds = listOf(f.source.id, f.source.id), officialCautions = listOf(""))))
        assertEquals(listOf(guide), accepted(guide))
    }
}
