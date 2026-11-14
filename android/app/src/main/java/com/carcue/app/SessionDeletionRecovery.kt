package com.carcue.app

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

internal interface SessionDeletionStore {
    fun pending(): Boolean
    fun queued(): List<RemoteSession>
    fun remove(session: RemoteSession)
    fun recoverAbandonedSession()
    fun registerCreated(session: RemoteSession, stillCurrent: () -> Boolean)
    fun finishActive()
}

internal object DeletionConfirmation {
    fun confirmed(httpStatus: Int, responseStatus: String?): Boolean = httpStatus == 200 && responseStatus == "DELETED"
    fun expired(httpStatus: Int, errorCode: String): Boolean = httpStatus == 401 && errorCode == "SESSION_INVALID_OR_EXPIRED"
}

/** One worker, at most three attempts per trigger burst; new triggers can request a later burst. */
internal class DeletionRetryCoordinator(
    scope: CoroutineScope,
    private val pendingNow: () -> Boolean,
    private val retryOnce: suspend () -> Unit,
    private val retryDelaysMillis: List<Long> = listOf(1000L, 3000L),
) {
    private val signals = Channel<Unit>(Channel.CONFLATED)
    private val mutablePending = MutableStateFlow(pendingNow())
    val pending = mutablePending.asStateFlow()
    private val mutableRetrying = MutableStateFlow(false)
    val retrying = mutableRetrying.asStateFlow()

    init {
        require(retryDelaysMillis.all { it >= 0 })
        scope.launch {
            for (signal in signals) {
                mutableRetrying.value = true
                try {
                    for (attempt in 0..retryDelaysMillis.size) {
                        // This pass includes work queued before it starts. Coalesce those signals.
                        while (signals.tryReceive().isSuccess) { /* one worker owns every drain */ }
                        if (!publishPending()) break
                        try { retryOnce() }
                        catch (cancelled: CancellationException) { throw cancelled }
                        catch (_: Exception) { /* keep pending; never log credentials or response bodies */ }
                        if (!publishPending()) break
                        if (attempt < retryDelaysMillis.size) {
                            // A real reconnect/new session wakes the backoff without starting another worker.
                            withTimeoutOrNull(retryDelaysMillis[attempt]) { signals.receive() }
                        }
                    }
                } finally { mutableRetrying.value = false }
                // A signal arriving during the last pass remains queued for the next bounded burst.
            }
        }
    }

    @Synchronized private fun publishPending(): Boolean = pendingNow().also { mutablePending.value = it }

    fun requestRetry() {
        if (publishPending()) signals.trySend(Unit)
    }
}

/** Shared for the process lifetime; caller/request cancellation cannot abandon newly created sessions. */
internal class SessionDeletionRecovery(
    scope: CoroutineScope,
    private val store: SessionDeletionStore,
    private val delete: suspend (RemoteSession) -> Unit,
    retryDelaysMillis: List<Long> = listOf(1000L, 3000L),
) {
    init { store.recoverAbandonedSession() }
    private val retries = DeletionRetryCoordinator(scope, store::pending, { drain() }, retryDelaysMillis)
    val pending = retries.pending
    val retrying = retries.retrying

    fun registerCreated(session: RemoteSession, stillCurrent: () -> Boolean) {
        store.registerCreated(session, stillCurrent)
        retries.requestRetry()
    }

    fun finishActive() {
        store.finishActive()
        retries.requestRetry()
    }

    fun retry() { retries.requestRetry() }

    private suspend fun drain() {
        for (session in store.queued()) {
            try { delete(session); store.remove(session) }
            catch (cancelled: CancellationException) { throw cancelled }
            catch (error: ApiFailure) {
                if (DeletionConfirmation.expired(error.status, error.code)) store.remove(session)
            }
            catch (_: Exception) { /* retain only deletion credentials until confirmed or expired */ }
        }
    }
}
