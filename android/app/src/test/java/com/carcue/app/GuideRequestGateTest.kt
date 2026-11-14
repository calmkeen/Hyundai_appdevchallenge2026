package com.carcue.app

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/** Deterministic request ordering with API doubles and the real file cache; no SDK/device or live API. */
class GuideRequestGateTest {
    @get:Rule val temporary = TemporaryFolder()
    private val f = GuidePublicationFixtures
    private fun cache() = PublishedGuideCache(temporary.root, f.policy()) { payload ->
        when (payload) {
            "synthetic-published" -> listOf(f.guide)
            "synthetic-empty" -> emptyList()
            else -> error("Unexpected synthetic response")
        }
    }

    @Test fun delayedOldResponseCannotRestoreGuidesAfterTheLatestEmptyResponse() = runBlocking {
        val cache = cache()
        cache.replace(f.profile, "ko-KR", "synthetic-published")
        val gate = GuideRequestGate()
        val first = gate.begin(f.profile, "ko-KR")
        val delayedResponse = CompletableDeferred<String>()
        val oldRequest = async(Dispatchers.Default) {
            val data = delayedResponse.await()
            gate.commitIfCurrent(first) { cache.replace(f.profile, "ko-KR", data) }
        }
        val latest = gate.begin(f.profile, "ko-KR")
        assertTrue(gate.commitIfCurrent(latest) { cache.replace(f.profile, "ko-KR", "synthetic-empty") }!!.isEmpty())
        delayedResponse.complete("synthetic-published")
        assertNull(oldRequest.await())
        assertFalse(gate.isCurrent(first)) // The ViewModel also rejects this response before updating its UI state.
        assertTrue(cache().read(f.profile, "ko-KR").isEmpty())
    }

    @Test fun inFlightOldWriteIsSerializedBeforeTheNewEmptyCommit() = runBlocking {
        val cache = cache()
        val gate = GuideRequestGate()
        val first = gate.begin(f.profile, "ko-KR")
        val writeEntered = CompletableDeferred<Unit>()
        val releaseWrite = CountDownLatch(1)
        val oldRequest = async(Dispatchers.Default) {
            gate.commitIfCurrent(first) {
                writeEntered.complete(Unit)
                check(releaseWrite.await(5, TimeUnit.SECONDS)) { "Test did not release the in-flight write" }
                cache.replace(f.profile, "ko-KR", "synthetic-published")
            }
        }
        writeEntered.await()
        val latest = gate.begin(f.profile, "ko-KR")
        val newWriteStarted = CompletableDeferred<Unit>()
        val newRequest = async(Dispatchers.Default) {
            newWriteStarted.complete(Unit)
            gate.commitIfCurrent(latest) { cache.replace(f.profile, "ko-KR", "synthetic-empty") }
        }
        newWriteStarted.await()
        releaseWrite.countDown()
        oldRequest.await()
        assertTrue(newRequest.await()!!.isEmpty())
        assertTrue(cache().read(f.profile, "ko-KR").isEmpty())
    }

    @Test fun differentLanguageScopesDoNotCancelOneAnother() = runBlocking {
        val gate = GuideRequestGate()
        val korean = gate.begin(f.profile, "ko-KR")
        val english = gate.begin(f.profile, "en")
        assertEquals("ko", gate.commitIfCurrent(korean) { "ko" })
        assertEquals("en", gate.commitIfCurrent(english) { "en" })
    }

    @Test fun sessionInvalidationRejectsOutstandingCommits() = runBlocking {
        val gate = GuideRequestGate()
        val request = gate.begin(f.profile, "ko-KR")
        gate.invalidate()
        var wrote = false
        assertNull(gate.commitIfCurrent(request) { wrote = true; "unexpected" })
        assertFalse(wrote)
        val next = gate.begin(f.profile, "ko-KR")
        assertTrue(gate.isCurrent(next))
        assertFalse(gate.isCurrent(request))
    }
}
