package com.carcue.app

import java.time.Instant
import org.junit.Assert.*
import org.junit.Test

/** Synthetic policy fixtures only. Runtime SDK evidence comes from the dedicated Pleos instrumentation. */
class DoorGuidePolicyTest {
    private val f = GuidePublicationFixtures
    private val now = Instant.parse("2026-11-14T10:00:00Z")
    private val reading = Reading(source = Source.PLEOS, capability = Capability.SUPPORTED, status = ReadStatus.VALUE,
        value = "OPEN", rawValue = "1", receivedAt = now.minusSeconds(1))
    private val parked = UxState(known = true, restricted = false)
    private val guide = f.guide.toGuide()
    private val rule = StateGuideRule("fixture-door-rule", f.profile.id, "fixture-manual", "v1", "door.position",
        "ROW_1_LEFT", "OPEN", guide.id, "VERIFIED")
    private fun related(profile: Profile? = f.profile, locale: String = "ko-KR", reading: Reading = this.reading,
                        ux: UxState = parked, guides: List<Guide> = listOf(guide), rules: List<StateGuideRule> = listOf(rule),
                        profiles: List<Profile> = listOf(f.profile), instant: Instant = now, ttlMs: Long = 60000) =
        DoorGuidePolicy(profiles, rules, ttlMs).relatedGuide(profile, locale, reading, ux, guides, instant)

    @Test fun freshTestedSdkOpenReadingLinksTheExactPublishedManual() {
        assertSame(guide, related())
        assertEquals("fixture-manual", guide.manualSetId)
        assertEquals("v1", guide.sourceVersion)
        assertEquals(listOf(f.profile.id), guide.profileIds)
        assertTrue(guide.publicationVerified)
    }

    @Test fun closedOrUninterpretedValuesNeverRecommendTheOpenGuide() {
        assertNull(related(reading = reading.copy(value = "CLOSED", rawValue = "0")))
        assertNull(related(reading = reading.copy(value = "50", rawValue = "50")))
        assertNull(related(reading = reading.copy(rawValue = null)))
        assertNull(related(reading = reading.copy(errorCode = "UNVERIFIED_OR_OUT_OF_RANGE")))
    }

    @Test fun mockHistoricalAndNonValueReadingsNeverRecommend() {
        assertNull(related(reading = reading.copy(source = Source.MOCK)))
        ReadStatus.entries.filter { it != ReadStatus.VALUE }.forEach { status ->
            assertNull("A historical OPEN is not current: $status", related(reading = reading.copy(status = status, value = null, previousValue = "OPEN")))
        }
        Capability.entries.filter { it != Capability.SUPPORTED }.forEach { capability ->
            assertNull(related(reading = reading.copy(capability = capability, status = ReadStatus.ERROR, value = null)))
        }
    }

    @Test fun freshnessIsCheckedAtSelectionAndDoesNotTrustTheValueLabelAlone() {
        assertSame(guide, related(reading = reading.copy(receivedAt = now.minusMillis(60000))))
        assertNull(related(reading = reading.copy(receivedAt = now.minusMillis(60001))))
        assertNull(related(reading = reading.copy(receivedAt = now.plusMillis(1))))
        assertNull(related(reading = reading.copy(receivedAt = null)))
        assertNull(related(ttlMs = 0))
        assertNull(related(instant = now.plusSeconds(60)))
    }

    @Test fun onlyTheTestedPhysicalAreaAndPropertyCanMatch() {
        assertNull(related(reading = reading.copy(propertyId = "ev.battery_soc")))
        assertNull(related(reading = reading.copy(areaId = "ROW_1_RIGHT")))
        assertNull(related(reading = reading.copy(areaId = null)))
    }

    @Test fun unknownOrRestrictedUxAlwaysHidesTheRecommendation() {
        assertNull(related(ux = UxState()))
        assertNull(related(ux = UxState(known = true, restricted = true, flags = 80)))
        assertNull(related(ux = UxState(known = false, restricted = false)))
        assertSame(guide, related(ux = parked))
    }

    @Test fun selectedVehicleMustMatchTheKnownVerifiedCatalogIdentity() {
        assertNull(related(profile = null))
        listOf(f.profile.copy(id = "other"), f.profile.copy(year = 2025), f.profile.copy(market = "GB"),
            f.profile.copy(verified = false), f.profile.copy(manualSetId = "other"), f.profile.copy(manualVersion = "v2")).forEach {
            assertNull(related(profile = it))
        }
        val unverified = f.profile.copy(verified = false)
        assertNull(related(profile = unverified, profiles = listOf(unverified)))
        val missingManual = f.profile.copy(manualSetId = null)
        assertNull(related(profile = missingManual, profiles = listOf(missingManual)))
    }

    @Test fun onlyTheExactReviewedRuleCanLinkTheGuide() {
        assertNull(related(rules = emptyList()))
        val invalid = listOf(rule.copy(id = " "), rule.copy(profileId = "other"), rule.copy(manualSetId = "other"),
            rule.copy(sourceVersion = "v2"), rule.copy(propertyId = "other"), rule.copy(areaId = "ROW_1_RIGHT"),
            rule.copy(value = "CLOSED"), rule.copy(guideId = "other"), rule.copy(verificationStatus = "UNVERIFIED"))
        invalid.forEach { assertNull("Invalid rule: $it", related(rules = listOf(it))) }
    }

    @Test fun ambiguityFailsClosed() {
        assertNull(related(rules = listOf(rule, rule)))
        assertNull(related(rules = listOf(rule, rule.copy(id = "another-rule"))))
        assertNull(related(rules = listOf(rule, rule.copy(profileId = "other"))))
        assertNull(related(guides = listOf(guide, guide)))
    }

    @Test fun unpublishedWrongManualOrDifferentLanguageGuidesNeverMatch() {
        val invalid = listOf(guide.copy(id = "other"), guide.copy(publicationVerified = false), guide.copy(sources = emptyList()),
            guide.copy(manualSetId = "other"), guide.copy(sourceVersion = "v2"), guide.copy(profileIds = listOf("other")),
            guide.copy(locale = "en"))
        invalid.forEach { assertNull("Invalid guide: $it", related(guides = listOf(it))) }
        assertNull(related(guides = emptyList()))
        assertNull(related(guides = listOf(Guide("__layout_preview__", "Example", "Not a manual", emptyList(), emptyList()))))
    }

    @Test fun languageSwitchUsesOnlyTheReviewedGuideForThatLanguageWithoutChangingMarket() {
        val english = guide.copy(locale = "en")
        assertSame(english, related(locale = "en", guides = listOf(guide, english)))
        assertNull(related(locale = "ja-JP", guides = listOf(guide, english)))
        assertEquals("KR", f.profile.market)
    }
}
