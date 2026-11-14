package com.carcue.app

/** Logical ownership only: no Android API, clock, scheduler, or fabricated UX value.
 * One foreground start has a finite retry budget. A successful GET does not refill
 * that budget. Losing an attempt invalidates both its known and unknown callbacks.
 */
internal class UxConnectionGate(retryDelaysMillis: List<Long> = listOf(1_000L, 3_000L, 10_000L)) {
    data class Attempt(val epoch: Long, val number: Long)
    data class Retry(val epoch: Long, val failedAttempt: Long, val delayMillis: Long)

    private val delays = retryDelaysMillis.toList().also { require(it.all { delay -> delay >= 0 }) }
    private var epoch = 0L
    private var sequence = 0L
    private var active = false
    private var usedRetries = 0
    private var current: Attempt? = null
    private var pending: Retry? = null
    private var freshGet = false

    fun start(): Attempt {
        stop()
        active = true
        usedRetries = 0
        return newAttempt()
    }

    fun stop() {
        epoch++
        active = false
        current = null
        pending = null
        freshGet = false
    }

    fun isCurrent(attempt: Attempt) = active && current == attempt
    fun isPending(retry: Retry) = active && retry.epoch == epoch && pending == retry

    fun acceptGet(attempt: Attempt): Boolean {
        if (!isCurrent(attempt)) return false
        freshGet = true
        return true
    }

    fun acceptCallback(attempt: Attempt) = isCurrent(attempt) && freshGet

    fun fail(attempt: Attempt): Retry? {
        if (!isCurrent(attempt)) return null
        current = null
        freshGet = false
        pending = if (usedRetries < delays.size) Retry(epoch, attempt.number, delays[usedRetries++]) else null
        return pending
    }

    fun beginRetry(retry: Retry): Attempt? {
        if (!isPending(retry)) return null
        pending = null
        return newAttempt()
    }

    private fun newAttempt() = Attempt(epoch, ++sequence).also {
        current = it
        freshGet = false
    }
}
