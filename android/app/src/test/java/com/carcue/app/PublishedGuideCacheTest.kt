package com.carcue.app

import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/** Exercises the real file cache with a pure metadata decoder; org.json is an Android platform API. */
class PublishedGuideCacheTest {
    @get:Rule val temporary = TemporaryFolder()
    private val f = GuidePublicationFixtures
    private val responses = mutableMapOf<String, List<PublishedGuideRecord>>()
    private fun cache(policy: GuidePublicationPolicy = f.policy()) = PublishedGuideCache(temporary.root, policy) { responses.getValue(it) }
    private fun payload(records: List<PublishedGuideRecord>): String = "synthetic-response-${responses.size}".also { responses[it] = records }

    @Test fun successfulEmptyResponseInvalidatesDiskCacheAndSurvivesRestart() {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", payload(listOf(f.guide)))
        assertEquals(listOf(f.guide), cache.read(f.profile, "ko-KR"))
        assertTrue(cache.replace(f.profile, "ko-KR", payload(emptyList())).isEmpty())
        assertTrue(cache.read(f.profile, "ko-KR").isEmpty())
        assertTrue(cache().read(f.profile, "ko-KR").isEmpty())
        assertTrue(temporary.root.listFiles().orEmpty().isEmpty())
    }

    @Test fun successfulResponseWithoutPublishableContentAlsoInvalidatesPreviousCache() {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", payload(listOf(f.guide)))
        assertTrue(cache.replace(f.profile, "ko-KR", payload(listOf(f.guide.copy(lifecycle = "DRAFT")))).isEmpty())
        assertTrue(cache().read(f.profile, "ko-KR").isEmpty())
    }

    @Test fun offlineReadIsBoundToProfileManualVersionAndLocale() {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", payload(listOf(f.guide)))
        assertEquals(listOf(f.guide), cache().read(f.profile, "ko-KR"))
        assertTrue(cache.read(f.profile, "en").isEmpty())
        val other = f.profile.copy(id = "fixture-other")
        assertTrue(cache(f.policy(listOf(f.profile, other))).read(other, "ko-KR").isEmpty())
        listOf(f.profile.copy(year = 2025), f.profile.copy(market = "GB"),
            f.profile.copy(manualSetId = "revised-manual"), f.profile.copy(manualVersion = "v2")).forEach { revised ->
            assertTrue(cache(f.policy(listOf(revised))).read(revised, "ko-KR").isEmpty())
        }
        assertTrue(cache(f.policy(listOf(f.profile.copy(verified = false)))).read(f.profile.copy(verified = false), "ko-KR").isEmpty())
    }

    @Test fun everyOfflineReadRevalidatesCachedMetadata() {
        val cache = cache()
        val token = payload(listOf(f.guide))
        cache.replace(f.profile, "ko-KR", token)
        // Represents a cached record whose source metadata is no longer valid, not a network update.
        responses[token] = listOf(f.guide.copy(sources = listOf(f.source.copy(verificationStatus = "UNVERIFIED"))))
        assertTrue(cache.read(f.profile, "ko-KR").isEmpty())
    }

    @Test fun failedResponseDecodePreservesOnlyTheMatchingValidCache() {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", payload(listOf(f.guide)))
        try {
            cache.replace(f.profile, "ko-KR", "invalid-response")
            fail("Malformed response must fail before replacing the cache")
        } catch (_: NoSuchElementException) { }
        assertEquals(listOf(f.guide), cache.read(f.profile, "ko-KR"))
        assertTrue(cache.read(f.profile, "en").isEmpty())
    }

    @Test fun unreadableOrCorruptCachedPayloadIsNeverDisplayed() {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", payload(listOf(f.guide)))
        temporary.root.listFiles()!!.single().writeText("corrupt-cache")
        assertTrue(cache.read(f.profile, "ko-KR").isEmpty())
    }

    @Test fun successfulReplacementLeavesOnlyTheNewCompletePayload() {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", payload(listOf(f.guide)))
        val next = f.guide.copy(id = "guide-2", title = "Synthetic revision")
        cache.replace(f.profile, "ko-KR", payload(listOf(next)))
        assertEquals(listOf(next), cache().read(f.profile, "ko-KR"))
        assertEquals(1, temporary.root.listFiles()!!.size)
        assertTrue(temporary.root.listFiles()!!.none { it.extension == "tmp" })
    }
}
