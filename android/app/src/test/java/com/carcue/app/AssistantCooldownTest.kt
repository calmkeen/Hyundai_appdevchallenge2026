package com.carcue.app

import java.time.Instant
import org.junit.Assert.*
import org.junit.Test

class AssistantCooldownTest {
    private val receivedAt = Instant.parse("2026-11-15T06:00:00Z")
    private val scope = AssistantCooldownScope(7, "ioniq5-ne1-2024-kr", "ko-KR")

    @Test fun deltaSecondsZeroAndHttpWhitespaceAreHonored() {
        assertEquals(0L, RetryAfterPolicy.delayMillis("0", receivedAt))
        assertEquals(60_000L, RetryAfterPolicy.delayMillis(" \t60\t ", receivedAt))
        assertEquals(1_000L, RetryAfterPolicy.delayMillis("0001", receivedAt))
    }

    @Test fun validLongWaitIsNotShortenedToAnHourOrFallback() {
        assertEquals(86_400_000L, RetryAfterPolicy.delayMillis("86400", receivedAt))
        assertEquals(86_400_000L, RetryAfterPolicy.delayMillis("Mon, 16 Nov 2026 06:00:00 GMT", receivedAt))
        assertEquals(Long.MAX_VALUE, RetryAfterPolicy.delayMillis("9223372036854775807", receivedAt))
        assertEquals(Long.MAX_VALUE, RetryAfterPolicy.delayMillis("999999999999999999999999999999", receivedAt))
    }

    @Test fun httpDateIsMeasuredAtReceiptAndPastDateDoesNotBlock() {
        assertEquals(60_000L, RetryAfterPolicy.delayMillis("Sun, 15 Nov 2026 06:01:00 GMT", receivedAt))
        assertEquals(0L, RetryAfterPolicy.delayMillis("Sun, 15 Nov 2026 06:00:00 GMT", receivedAt))
        assertEquals(0L, RetryAfterPolicy.delayMillis("Sun, 15 Nov 2026 05:59:59 GMT", receivedAt))
    }

    @Test fun futureDateFractionIsRoundedUpToAvoidEarlyRelease() {
        val fractionalReceipt = receivedAt.plusNanos(999_999)
        assertEquals(1_000L, RetryAfterPolicy.delayMillis("Sun, 15 Nov 2026 06:00:01 GMT", fractionalReceipt))
    }

    @Test fun missingMalformedAndInvalidListsUseTheDocumentedFallback() {
        for (header in listOf(null, "", " ", "-1", "+2", "1.5", "60, 120", "not a date", "120\r\n", "١٢٠")) {
            assertEquals(header, 60_000L, RetryAfterPolicy.delayMillis(header, receivedAt))
        }
        assertEquals(60_000L, RetryAfterPolicy.fromHeaders(emptyList(), receivedAt))
    }

    @Test fun duplicateHeadersHonorTheLongestWaitRegardlessOfOrder() {
        assertEquals(120_000L, RetryAfterPolicy.fromHeaders(listOf("120", "10"), receivedAt))
        assertEquals(120_000L, RetryAfterPolicy.fromHeaders(listOf("10", "120"), receivedAt))
        assertEquals(120_000L, RetryAfterPolicy.fromHeaders(listOf("invalid", "120"), receivedAt))
        assertEquals(60_000L, RetryAfterPolicy.fromHeaders(listOf("0", "invalid"), receivedAt))
    }

    @Test fun actualHeaderMapIsCaseInsensitiveAndOnly429CreatesACooldown() {
        val headers = mapOf(null to listOf("HTTP/1.1 429 Too Many Requests"), "retry-after" to listOf("120"),
            "Retry-After" to listOf("30"), "X-Unrelated" to listOf("999999"))
        assertEquals(120_000L, RetryAfterPolicy.forResponse(429, headers, receivedAt))
        assertEquals(60_000L, RetryAfterPolicy.forResponse(429, emptyMap(), receivedAt))
        for (status in listOf(200, 401, 408, 500, 503)) assertNull(RetryAfterPolicy.forResponse(status, headers, receivedAt))
    }

    @Test fun countdownRoundsUpAndAdmitsOnlyAtTheExactMonotonicBoundary() {
        var elapsed = 10_000L
        val gate = AssistantCooldown { elapsed }
        assertEquals(2L, gate.start(scope, 1_001))
        elapsed += 1
        assertEquals(1L, gate.remainingSeconds(scope))
        elapsed += 999
        assertEquals(1L, gate.remainingSeconds(scope))
        elapsed += 1
        assertEquals(0L, gate.remainingSeconds(scope))
    }

    @Test fun dateBasedWaitDoesNotFollowLaterWallClockChanges() {
        var elapsed = 5_000L
        val gate = AssistantCooldown { elapsed }
        val wait = RetryAfterPolicy.delayMillis("Sun, 15 Nov 2026 06:01:00 GMT", receivedAt)
        gate.start(scope, wait)
        // The date was consumed at receipt. A device date change cannot alter an in-progress wait.
        RetryAfterPolicy.delayMillis("Sun, 15 Nov 2026 06:01:00 GMT", receivedAt.plusSeconds(86_400))
        elapsed += 59_999
        assertEquals(1L, gate.remainingSeconds(scope))
        elapsed += 1
        assertEquals(0L, gate.remainingSeconds(scope))
    }

    @Test fun elapsedClockRegressionCannotReleaseTheRequest() {
        var elapsed = 10_000L
        val gate = AssistantCooldown { elapsed }
        gate.start(scope, 60_000)
        elapsed = 9_000
        assertEquals(60L, gate.remainingSeconds(scope))
    }

    @Test fun hugeWaitDoesNotOverflowIntoAnImmediateRetry() {
        var elapsed = Long.MAX_VALUE - 100
        val gate = AssistantCooldown { elapsed }
        assertTrue(gate.start(scope, Long.MAX_VALUE) > 0)
        elapsed += 99
        assertTrue(gate.remainingSeconds(scope) > 0)
    }

    @Test fun cooldownIsSharedByActionsButNotByAnotherContext() {
        var elapsed = 0L
        val gate = AssistantCooldown { elapsed }
        gate.start(scope, 60_000)
        assertEquals(60L, gate.remainingSeconds(scope.copy()))
        for (next in listOf(scope.copy(epoch = 8), scope.copy(profileId = "other"), scope.copy(locale = "en"))) {
            assertEquals(0L, gate.remainingSeconds(next))
        }
        // Merely visiting another page/context does not mutate the original scope's countdown.
        elapsed = 1_000
        assertEquals(59L, gate.remainingSeconds(scope))
    }

    @Test fun explicitBoundaryCleanupCancelsTheOldWaitWithoutAStaleTick() {
        var elapsed = 0L
        val gate = AssistantCooldown { elapsed }
        gate.start(scope, 60_000)
        gate.clear()
        elapsed = 1_000
        assertEquals(0L, gate.remainingSeconds(scope))
        val next = scope.copy(epoch = scope.epoch + 1)
        assertEquals(2L, gate.start(next, 2_000))
        assertEquals(0L, gate.remainingSeconds(scope))
        elapsed += 1_000
        assertEquals(1L, gate.remainingSeconds(next))
    }

    @Test fun zeroWaitDoesNotCreateAHiddenDelay() {
        val gate = AssistantCooldown { 1_000L }
        assertEquals(0L, gate.start(scope, 0))
        assertEquals(0L, gate.remainingSeconds(scope))
    }
}
