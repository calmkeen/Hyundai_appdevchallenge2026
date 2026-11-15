package com.carcue.app

import java.time.Duration
import java.time.Instant
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/** Retry-After is interpreted once on receipt; waiting never follows later wall-clock changes. */
object RetryAfterPolicy {
    const val FALLBACK_MILLIS = 60_000L
    fun delayMillis(header: String?, receivedAt: Instant): Long {
        if (header == null || header.any { it.code < 32 && it != '\t' || it.code == 127 }) return FALLBACK_MILLIS
        val value = header.trim(' ', '\t')
        if (value.isEmpty()) return FALLBACK_MILLIS
        if (value.all { it in '0'..'9' }) {
            val seconds = value.toLongOrNull() ?: return Long.MAX_VALUE
            return if (seconds > Long.MAX_VALUE / 1000) Long.MAX_VALUE else seconds * 1000
        }
        if (value.length > 256) return FALLBACK_MILLIS
        return runCatching {
            val deadline = ZonedDateTime.parse(value, DateTimeFormatter.RFC_1123_DATE_TIME).toInstant()
            if (!deadline.isAfter(receivedAt)) 0L else runCatching {
                val duration = Duration.between(receivedAt, deadline)
                val millis = duration.toMillis()
                if (millis == Long.MAX_VALUE || duration.minusMillis(millis).isZero) millis else millis + 1
            }.getOrDefault(Long.MAX_VALUE)
        }.getOrDefault(FALLBACK_MILLIS)
    }

    /** Duplicate headers never discard the longest valid wait. A comma-list is not a valid delay. */
    fun fromHeaders(headers: List<String>, receivedAt: Instant): Long =
        headers.maxOfOrNull { delayMillis(it, receivedAt) } ?: FALLBACK_MILLIS

    fun forResponse(status: Int, headers: Map<String?, List<String>?>, receivedAt: Instant): Long? =
        if (status != 429) null else fromHeaders(headers.entries
            .filter { it.key?.equals("Retry-After", ignoreCase = true) == true }.flatMap { it.value.orEmpty() }, receivedAt)
}

data class AssistantCooldownScope(val epoch: Int, val profileId: String?, val locale: String)

/** In-memory, session-scoped admission gate. The injected clock must be monotonic milliseconds. */
class AssistantCooldown(private val elapsedMillis: () -> Long) {
    private var scope: AssistantCooldownScope? = null
    private var startedAt = 0L
    private var duration = 0L

    fun start(nextScope: AssistantCooldownScope, delayMillis: Long): Long {
        scope = nextScope
        startedAt = elapsedMillis().coerceAtLeast(0)
        duration = delayMillis.coerceAtLeast(0)
        return remainingSeconds(nextScope)
    }

    fun remainingSeconds(currentScope: AssistantCooldownScope): Long {
        if (scope != currentScope) return 0
        val now = elapsedMillis().coerceAtLeast(0)
        val elapsed = if (now >= startedAt) now - startedAt else 0 // A regressed clock cannot release early.
        val remaining = (duration - elapsed).coerceAtLeast(0)
        return if (remaining == 0L) 0 else (remaining - 1) / 1000 + 1
    }

    fun clear() { scope = null; startedAt = 0; duration = 0 }
}
