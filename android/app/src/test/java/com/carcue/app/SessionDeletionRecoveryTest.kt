package com.carcue.app

import java.io.IOException
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.*
import org.junit.Test

/** Tests the real coordinator with a store/gateway boundary; no Android ViewModel or network doubles posing as SDK. */
class SessionDeletionRecoveryTest {
    private val first = RemoteSession("session-a", "synthetic-token-a", "2099-01-01T00:00:00Z")
    private val second = RemoteSession("session-b", "synthetic-token-b", "2099-01-01T00:00:00Z")

    private class MemoryStore(active: RemoteSession? = null, queued: List<RemoteSession> = emptyList()) : SessionDeletionStore {
        private var active = active
        private val queue = queued.associateByTo(linkedMapOf()) { it.id }
        @Synchronized override fun pending() = queue.isNotEmpty()
        @Synchronized override fun queued() = queue.values.toList()
        @Synchronized override fun remove(session: RemoteSession) { queue.remove(session.id) }
        @Synchronized override fun recoverAbandonedSession() { finishActive() }
        @Synchronized override fun registerCreated(session: RemoteSession, stillCurrent: () -> Boolean) {
            if (stillCurrent()) active = session else queue[session.id] = session
        }
        @Synchronized override fun finishActive() { active?.let { queue[it.id] = it }; active = null }
        @Synchronized fun active() = active
    }

    private fun recoveryTest(block: suspend (CoroutineScope) -> Unit) = runBlocking {
        val job = SupervisorJob()
        val scope = CoroutineScope(job + Dispatchers.Default)
        try { withTimeout(5000) { block(scope) } }
        finally { job.cancelAndJoin() }
    }

    @Test fun currentSessionIsNotDeletedUntilTheUserFinishes() = recoveryTest { scope ->
        val store = MemoryStore()
        val called = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val recovery = SessionDeletionRecovery(scope, store, delete = { called.complete(Unit); release.await() })
        recovery.registerCreated(first) { true }
        assertEquals(first, store.active())
        assertFalse(recovery.pending.value)
        assertFalse(called.isCompleted)
        recovery.finishActive()
        assertTrue(recovery.pending.value)
        assertNull(store.active())
        called.await()
        release.complete(Unit)
        recovery.pending.filter { !it }.first()
        assertTrue(store.queued().isEmpty())
    }

    @Test fun lateSessionFromACancelledRequestIsImmediatelyPublishedAndDeleted() = recoveryTest { scope ->
        val store = MemoryStore()
        val request = Job().apply { cancel() }
        val called = CompletableDeferred<RemoteSession>()
        val release = CompletableDeferred<Unit>()
        val recovery = SessionDeletionRecovery(scope, store, delete = { called.complete(it); release.await() })
        recovery.registerCreated(first) { request.isActive }
        assertTrue(recovery.pending.value)
        assertEquals(listOf(first), store.queued())
        assertNull(store.active())
        assertEquals(first, called.await())
        release.complete(Unit)
        recovery.pending.filter { !it }.first()
        assertTrue(store.queued().isEmpty())
    }

    @Test fun aLateOldRequestCannotReplaceTheNewUsersActiveSession() = recoveryTest { scope ->
        val store = MemoryStore()
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val recovery = SessionDeletionRecovery(scope, store, delete = { entered.complete(Unit); release.await() })
        recovery.registerCreated(second) { true }
        recovery.registerCreated(first) { false }
        entered.await()
        assertEquals(second, store.active())
        assertEquals(listOf(first), store.queued())
        release.complete(Unit)
        recovery.pending.filter { !it }.first()
        assertEquals(second, store.active())
    }

    @Test fun abandonedActiveSessionIsPendingBeforeTheFirstRetryOrNetworkValidation() = recoveryTest { scope ->
        val store = MemoryStore(active = first)
        val count = AtomicInteger()
        val recovery = SessionDeletionRecovery(scope, store, delete = { count.incrementAndGet(); Unit })
        assertTrue(recovery.pending.value)
        assertNull(store.active())
        assertEquals(0, count.get())
        // Foreground/manual retry works even when the emulator has no validated Internet capability.
        recovery.retry()
        recovery.pending.filter { !it }.first()
        assertEquals(1, count.get())
    }

    @Test fun failedDeletionStopsAfterThreeAttemptsUntilAnotherExplicitTrigger() = recoveryTest { scope ->
        val store = MemoryStore(queued = listOf(first))
        val attempts = Channel<Unit>(Channel.UNLIMITED)
        val count = AtomicInteger()
        val recovery = SessionDeletionRecovery(scope, store, delete = {
            count.incrementAndGet(); attempts.send(Unit); throw IOException("synthetic offline")
        }, retryDelaysMillis = listOf(0L, 0L))
        recovery.retry()
        repeat(3) { attempts.receive() }
        recovery.retrying.filter { !it }.first()
        assertEquals(3, count.get())
        assertTrue(recovery.pending.value)
        assertEquals(listOf(first), store.queued())
        recovery.retry() // Reconnect or the user's deletion-status button starts a new bounded burst.
        repeat(3) { attempts.receive() }
        recovery.retrying.filter { !it }.first()
        assertEquals(6, count.get())
    }

    @Test fun concurrentTriggersCoalesceAndNeverRunTwoDeletesTogether() = recoveryTest { scope ->
        val store = MemoryStore(queued = listOf(first))
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val active = AtomicInteger()
        val maximum = AtomicInteger()
        val count = AtomicInteger()
        val recovery = SessionDeletionRecovery(scope, store, delete = {
            val running = active.incrementAndGet()
            maximum.updateAndGet { previous -> maxOf(previous, running) }
            try {
                if (count.incrementAndGet() == 1) {
                    entered.complete(Unit); release.await(); throw IOException("first connection failed")
                }
            } finally { active.decrementAndGet() }
        }, retryDelaysMillis = listOf(0L, 0L))
        recovery.retry()
        entered.await()
        repeat(20) { recovery.retry() }
        release.complete(Unit)
        recovery.pending.filter { !it }.first()
        assertEquals(1, maximum.get())
        assertEquals(2, count.get())
    }

    @Test fun reconnectWakesBackoffImmediatelyInsteadOfWaitingForItsTimer() = recoveryTest { scope ->
        val store = MemoryStore(queued = listOf(first))
        val restored = AtomicBoolean(false)
        val firstAttempt = CompletableDeferred<Unit>()
        val count = AtomicInteger()
        val recovery = SessionDeletionRecovery(scope, store, delete = {
            count.incrementAndGet()
            if (!restored.get()) { firstAttempt.complete(Unit); throw IOException("offline") }
        }, retryDelaysMillis = listOf(60000L, 60000L))
        recovery.retry()
        firstAttempt.await()
        restored.set(true)
        recovery.retry()
        // The test has a five-second deadline, while the untriggered backoff would be sixty seconds.
        recovery.pending.filter { !it }.first()
        assertEquals(2, count.get())
    }

    @Test fun newWorkDuringTheLastAttemptIsNotLostWhenTheBurstFinishes() = recoveryTest { scope ->
        val store = MemoryStore(queued = listOf(first))
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val count = AtomicInteger()
        val recovery = SessionDeletionRecovery(scope, store, delete = {
            if (count.incrementAndGet() == 1) {
                entered.complete(Unit); release.await(); throw IOException("old request failed")
            }
        }, retryDelaysMillis = emptyList())
        recovery.retry()
        entered.await()
        recovery.registerCreated(second) { false }
        assertTrue(recovery.pending.value)
        release.complete(Unit)
        recovery.pending.filter { !it }.first()
        assertEquals(3, count.get()) // Failed first, then first + newly queued second in the next burst.
        assertTrue(store.queued().isEmpty())
    }

    @Test fun onlyConfirmedExpiryRemovesAnAuthenticationFailure() = recoveryTest { scope ->
        val store = MemoryStore(queued = listOf(first, second))
        val attempts = Channel<Unit>(Channel.UNLIMITED)
        val recovery = SessionDeletionRecovery(scope, store, delete = {
            attempts.send(Unit)
            throw ApiFailure(401, if (it.id == first.id) "SESSION_INVALID_OR_EXPIRED" else "UNKNOWN")
        }, retryDelaysMillis = emptyList())
        recovery.retry()
        repeat(2) { attempts.receive() }
        recovery.retrying.filter { !it }.first()
        assertEquals(listOf(second), store.queued())
        assertTrue(recovery.pending.value)
    }

    @Test fun anUnconfirmedSuccessfulHttpStatusKeepsDeletionCredentials() = recoveryTest { scope ->
        val store = MemoryStore(queued = listOf(first))
        val attempted = CompletableDeferred<Unit>()
        val recovery = SessionDeletionRecovery(scope, store, delete = {
            attempted.complete(Unit); throw ApiFailure(202, "DELETE_NOT_CONFIRMED")
        }, retryDelaysMillis = emptyList())
        recovery.retry()
        attempted.await()
        recovery.retrying.filter { !it }.first()
        assertEquals(listOf(first), store.queued())
        assertTrue(recovery.pending.value)
    }

    @Test fun deleteContractRejectsAcceptedEmptyAndWrongSuccessfulResponses() {
        assertTrue(DeletionConfirmation.confirmed(200, "DELETED"))
        for (status in listOf(201, 202, 204, 299, 401, 500)) assertFalse(DeletionConfirmation.confirmed(status, "DELETED"))
        for (body in listOf(null, "", "PENDING", "deleted", " DELETED")) assertFalse(DeletionConfirmation.confirmed(200, body))
        assertTrue(DeletionConfirmation.expired(401, "SESSION_INVALID_OR_EXPIRED"))
        assertFalse(DeletionConfirmation.expired(401, "UNKNOWN"))
        assertFalse(DeletionConfirmation.expired(403, "SESSION_INVALID_OR_EXPIRED"))
    }
}
