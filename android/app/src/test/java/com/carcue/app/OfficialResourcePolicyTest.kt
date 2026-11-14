package com.carcue.app

import org.junit.Assert.*
import org.junit.Test

/** Pure policy regressions with synthetic registrations and example.test URLs only.
 * No assets, browser, network, actual SDK, device or model is exercised. A Reading.source enum
 * here is a fixture label; success does not mean an Intent was dispatched or a webpage loaded.
 */
class OfficialResourcePolicyTest {
    private val sourceId = "synthetic-manual-source"
    private val guideId = "synthetic-guide"
    private val requestId = "synthetic-answer-request"
    private val url = "https://manual.example.test/2024/ko/door#section-1"
    private val contact = SupportContact("synthetic-support-kr", "WEBSITE", "Synthetic KR support",
        "https://support.example.test/kr", "KR", "ko-KR", true)
    private val profile = Profile("synthetic-car-kr", "Synthetic vehicle", 2024, "KR", true,
        "synthetic-manual-kr", "synthetic-v1", listOf(contact))
    private val locales = listOf("ko-KR", "en", "ja-JP")

    private fun guide(locale: String = "ko-KR", registeredSourceId: String = sourceId): Guide {
        val source = PublishedGuideSource(registeredSourceId, "Synthetic manual", url, profile.manualVersion,
            "Synthetic section", "VERIFIED")
        val record = PublishedGuideRecord(guideId, listOf(profile.id), profile.manualSetId, profile.manualVersion,
            "synthetic-topic", "Synthetic guide $locale", "Synthetic reviewed body $locale", locale, "ko-KR",
            "PUBLISHED", if (locale == "ko-KR") "NOT_APPLICABLE" else "REVIEWED",
            if (locale == "ko-KR") null else "synthetic-glossary-v1", listOf(source),
            listOf(PublishedGuideStep("synthetic-step", 1, "Synthetic step", "Synthetic step body",
                listOf("Synthetic caution"), listOf(registeredSourceId))))
        return GuidePublicationPolicy(listOf(profile), locales.toSet()).published(listOf(record), profile, locale)
            .single().toGuide().copy(origin = GuideOrigin.BUNDLED)
    }
    private fun policy() = OfficialResourcePolicy(listOf(profile), locales.map { profile to guide(it) })
    private fun state(locale: String = "ko-KR"): UiState = UiState(page = Page.GUIDE, sessionEpoch = 7,
        profile = profile, locale = locale, sessionStarted = true, reading = Reading(source = Source.MOCK),
        ux = UxState(known = true, restricted = false), selectedGuide = guide(locale), guides = listOf(guide(locale)))
    private fun citation() = OfficialCitation(sourceId, guideId, profile.id, profile.manualSetId!!,
        profile.manualVersion!!, url)
    private fun answerState(locale: String = "ko-KR") = state(locale).copy(page = Page.ASK,
        answer = "Synthetic preserved Korean answer", answerLocale = "ko-KR", answerStatus = "ANSWERED",
        lastAiRequestId = requestId, answerRequestId = requestId, officialCitations = listOf(citation()))
    private fun assertEveryRouteDenied(current: UiState, expected: OfficialActionScope) {
        val policy = policy()
        assertNull(policy.guideSource(current.copy(page = Page.GUIDE), expected, guideId, sourceId))
        assertNull(policy.support(current, expected, contact.id))
        assertNull(policy.citation(current.copy(page = Page.ASK, answer = "Synthetic answer",
            answerLocale = "ko-KR", answerStatus = "ANSWERED", lastAiRequestId = requestId,
            answerRequestId = requestId,
            officialCitations = listOf(citation())), expected, requestId, sourceId))
    }

    @Test fun registeredVerifiedSourceResolvesIndependentlyOfGuideOriginAndVehicleSourceLabel() {
        val policy = policy()
        for (origin in listOf(GuideOrigin.BUNDLED, GuideOrigin.CACHE, GuideOrigin.SERVER)) {
            for (vehicleSource in Source.entries) {
                val currentGuide = guide().copy(origin = origin)
                val state = state().copy(reading = Reading(source = vehicleSource), selectedGuide = currentGuide,
                    guides = listOf(currentGuide))
                val target = requireNotNull(policy.guideSource(state, policy.scope(state), guideId, sourceId))
                assertEquals(sourceId, target.id)
                assertEquals(url, target.url)
                assertEquals(guide().sources.single().first, target.title)
                assertEquals("KR", target.market)
                assertEquals("ko-KR", target.sourceLocale)
            }
        }
    }

    @Test fun endingAndRestartingEvenTheSameProfileInvalidatesTheRenderedSessionEpoch() {
        val original = state()
        val expected = policy().scope(original)
        assertEveryRouteDenied(original.copy(sessionStarted = false), expected)
        assertEveryRouteDenied(original.copy(sessionEpoch = original.sessionEpoch + 1), expected)
        assertEveryRouteDenied(original.copy(sessionStarted = false, profile = null), expected)
    }

    @Test fun uxBecomingUnknownOrRestrictedAtTapBlocksEveryExternalRoute() {
        val original = state()
        val expected = policy().scope(original)
        assertEveryRouteDenied(original.copy(ux = UxState(known = false, restricted = true)), expected)
        assertEveryRouteDenied(original.copy(ux = UxState(known = true, restricted = true)), expected)
        assertEveryRouteDenied(original.copy(ux = UxState(known = false, restricted = false)), expected)
    }

    @Test fun alteredProfileMarketYearAndManualMetadataCannotReuseRegisteredTargets() {
        val policy = policy()
        val changes = listOf(profile.copy(id = "synthetic-other-car"), profile.copy(market = "GB"),
            profile.copy(year = 2025), profile.copy(manualSetId = "synthetic-other-manual"),
            profile.copy(manualVersion = "synthetic-v2"))
        for (changed in changes) {
            val changedState = state().copy(profile = changed)
            // Even a newly captured scope cannot promote an unregistered profile copy.
            assertEveryRouteDenied(changedState, policy.scope(changedState))
        }
    }

    @Test fun unverifiedMissingAndUnregisteredProfileCannotOpenResources() {
        for (changed in listOf(profile.copy(verified = false), profile.copy(manualSetId = null),
            profile.copy(manualVersion = null))) {
            val state = state().copy(profile = changed)
            assertEveryRouteDenied(state, policy().scope(state))
        }
        val emptyRegistry = OfficialResourcePolicy(emptyList(), emptyList())
        val state = state()
        assertNull(emptyRegistry.guideSource(state, emptyRegistry.scope(state), guideId, sourceId))
        assertNull(emptyRegistry.support(state, emptyRegistry.scope(state), contact.id))
    }

    @Test fun currentLocaleWithdrawalAndLeavingTheGuideDisableTheOldSourceButton() {
        val policy = policy()
        val original = state()
        val expected = policy.scope(original)
        assertNull(policy.guideSource(original.copy(guides = emptyList()), expected, guideId, sourceId))
        assertNull(policy.guideSource(original.copy(selectedGuide = null), expected, guideId, sourceId))
        assertNull(policy.guideSource(original.copy(page = Page.ASK), expected, guideId, sourceId))
    }

    @Test fun englishAndJapaneseUiPreserveKoreanMarketSupportAndExplicitOriginalManual() {
        val policy = policy()
        for (locale in listOf("en", "ja-JP")) {
            val state = state(locale).copy(selectedGuide = guide("ko-KR"))
            val expected = policy.scope(state)
            val support = requireNotNull(policy.support(state, expected, contact.id))
            assertEquals("KR", support.market)
            assertEquals("ko-KR", support.sourceLocale)
            assertEquals(contact.url, support.url)
            val manual = requireNotNull(policy.guideSource(state, expected, guideId, sourceId))
            assertEquals("KR", manual.market)
            assertEquals("ko-KR", manual.sourceLocale)
            assertEquals(url, manual.url)
        }
    }

    @Test fun serverOriginCannotReplaceTheBundledRegisteredSourceUrlOrSourceLocale() {
        val policy = policy()
        val original = guide()
        val mutations = listOf(original.officialSources.single().copy(url = "https://unregistered.example.test/manual"),
            original.officialSources.single().copy(sourceLocale = "en"),
            original.officialSources.single().copy(id = "synthetic-server-invented-source"))
        for (source in mutations) {
            val altered = original.copy(origin = GuideOrigin.SERVER, officialSources = listOf(source))
            val state = state().copy(selectedGuide = altered, guides = listOf(altered))
            assertNull(policy.guideSource(state, policy.scope(state), guideId, source.id))
        }
    }

    @Test fun rawUrlsUnknownTargetsAndAmbiguousSourceRegistrationsAreNotExecutableIds() {
        val policy = policy()
        val state = state()
        for (unknown in listOf(url, "https://support.example.test/kr", "unknown-id", "")) {
            assertNull(policy.guideSource(state, policy.scope(state), guideId, unknown))
            assertNull(policy.support(state, policy.scope(state), unknown))
        }
        val duplicate = guide().copy(officialSources = listOf(guide().officialSources.single(), guide().officialSources.single()))
        val duplicatedState = state.copy(selectedGuide = duplicate, guides = listOf(duplicate))
        assertNull(policy.guideSource(duplicatedState, policy.scope(duplicatedState), guideId, sourceId))
        val unregistered = OfficialResourcePolicy(listOf(profile), emptyList())
        assertNull(unregistered.guideSource(state, unregistered.scope(state), guideId, sourceId))
    }

    @Test fun aFullyBoundAnswerCitationCanResolveAfterUiLanguageChangesWithoutRewritingTheAnswer() {
        val policy = policy()
        for (locale in locales) {
            // Translation B may update the generic audit request ID while answer A remains original.
            val state = answerState(locale).copy(lastAiRequestId = "synthetic-later-translation-request")
            val before = state.answer
            val target = requireNotNull(policy.citation(state, policy.scope(state), requestId, sourceId))
            assertEquals(url, target.url)
            assertEquals("KR", target.market)
            assertEquals("ko-KR", target.sourceLocale)
            assertEquals(before, state.answer)
            assertEquals("ko-KR", state.answerLocale)
            assertEquals(requestId, state.answerRequestId)
            assertNull(policy.citation(state, policy.scope(state), state.lastAiRequestId, sourceId))
        }
    }

    @Test fun citationRequiresTheCurrentAnswerRequestAndAnActiveAskPage() {
        val policy = policy()
        val original = answerState()
        val expected = policy.scope(original)
        assertNull(policy.citation(original, expected, "", sourceId))
        assertNull(policy.citation(original, expected, "synthetic-old-request", sourceId))
        assertNull(policy.citation(original.copy(answerRequestId = "synthetic-new-request"), expected, requestId, sourceId))
        assertNull(policy.citation(original.copy(answerRequestId = ""), expected, requestId, sourceId))
        assertNull(policy.citation(original.copy(page = Page.TRANSLATE), expected, requestId, sourceId))
        assertNull(policy.citation(original.copy(answer = ""), expected, requestId, sourceId))
    }

    @Test fun citationRejectsEachForeignBindingAndCurrentLocaleWithdrawal() {
        val policy = policy()
        val mutations = listOf(citation().copy(profileId = "synthetic-other-car"),
            citation().copy(manualSetId = "synthetic-other-manual"), citation().copy(sourceVersion = "synthetic-v2"),
            citation().copy(guideId = "synthetic-other-guide"), citation().copy(sourceId = "unknown-source"),
            citation().copy(url = "https://unregistered.example.test/manual"))
        for (citation in mutations) {
            val state = answerState().copy(officialCitations = listOf(citation))
            assertNull(policy.citation(state, policy.scope(state), requestId, sourceId))
        }
        val duplicate = answerState().copy(officialCitations = listOf(citation(), citation()))
        assertNull(policy.citation(duplicate, policy.scope(duplicate), requestId, sourceId))
        val withdrawn = answerState("en").copy(guides = emptyList())
        assertNull(policy.citation(withdrawn, policy.scope(withdrawn), requestId, sourceId))
    }

    @Test fun absentInvalidAndCrossMarketSupportIsNotOfferedByThePolicy() {
        val invalidContacts = listOf(emptyList(), listOf(contact.copy(verified = false)),
            listOf(contact.copy(market = "GB")), listOf(contact.copy(kind = "PHONE")),
            listOf(contact.copy(title = " ")), listOf(contact.copy(sourceLocale = "")), listOf(contact, contact))
        for (contacts in invalidContacts) {
            val registeredProfile = profile.copy(supportContacts = contacts)
            val policy = OfficialResourcePolicy(listOf(registeredProfile), listOf(registeredProfile to guide()))
            val state = state().copy(profile = registeredProfile)
            assertNull(policy.support(state, policy.scope(state), contact.id))
        }
    }

    @Test fun malformedAndEncodedControlSupportUrlsAreRejectedEvenWhenRegistered() {
        for (invalid in listOf("http://support.example.test/kr", "javascript:alert(1)",
            "https://user:secret@support.example.test/kr", "https://support.example.test:443/kr",
            "https://support.example.test/with space", "https://support.example.test/\\path",
            "https://support.example.test/%0a", "https://support.example.test/%7f")) {
            val registeredProfile = profile.copy(supportContacts = listOf(contact.copy(url = invalid)))
            val policy = OfficialResourcePolicy(listOf(registeredProfile), emptyList())
            val state = state().copy(profile = registeredProfile)
            assertNull("Must reject synthetic unsafe URL: $invalid", policy.support(state, policy.scope(state), contact.id))
        }
    }

    @Test fun nonAnsweredStatusCannotReuseResidualCitationMetadata() {
        val policy = policy()
        for (status in listOf("NO_RELIABLE_SOURCE", "NEED_MORE_INFO", "TEMPORARILY_UNAVAILABLE", "")) {
            val state = answerState().copy(answerStatus = status)
            assertNull(policy.citation(state, policy.scope(state), requestId, sourceId))
        }
    }

    @Test fun registeredIdsMustStillBeBoundedAsciiIdentifiersForEveryExternalRoute() {
        val boundaryId = "s" + "a".repeat(127)
        val cases = listOf("https://manual.example.test/source", "source with space", "s".repeat(129), boundaryId)
        for (registeredId in cases) {
            // These records pass the existing publication gate and are present in the bundled
            // synthetic registry. Registration alone must not turn an invalid ID into an action.
            val registeredGuide = guide(registeredSourceId = registeredId)
            val registeredProfile = profile.copy(supportContacts = listOf(contact.copy(id = registeredId)))
            val policy = OfficialResourcePolicy(listOf(registeredProfile), listOf(registeredProfile to registeredGuide))
            val guideState = state().copy(profile = registeredProfile, selectedGuide = registeredGuide,
                guides = listOf(registeredGuide))
            val answerState = answerState().copy(profile = registeredProfile, guides = listOf(registeredGuide),
                officialCitations = listOf(citation().copy(sourceId = registeredId)))
            val resolved = listOf(policy.support(guideState, policy.scope(guideState), registeredId),
                policy.guideSource(guideState, policy.scope(guideState), guideId, registeredId),
                policy.citation(answerState, policy.scope(answerState), requestId, registeredId))
            for (target in resolved) {
                if (registeredId == boundaryId) {
                    assertEquals("A valid 128-character registered ID remains usable", boundaryId, requireNotNull(target).id)
                } else {
                    assertNull("Invalid registered ID must not be executable: $registeredId", target)
                }
            }
        }
    }
}
