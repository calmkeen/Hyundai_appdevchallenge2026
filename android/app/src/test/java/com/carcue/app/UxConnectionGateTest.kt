package com.carcue.app

import org.junit.Assert.*
import org.junit.Test

/** Synthetic ownership/backoff tests. No Car service, vehicle or UX values are mocked into the app. */
class UxConnectionGateTest {
    @Test fun aCallbackCannotMakeANewConnectionKnownBeforeItsFreshGet() {
        val gate = UxConnectionGate()
        val attempt = gate.start()
        assertFalse(gate.acceptCallback(attempt))
        assertTrue(gate.acceptGet(attempt))
        assertTrue(gate.acceptCallback(attempt))
    }

    @Test fun aFailedAttemptCannotPublishALateKnownValueWhileWaitingToRetry() {
        val gate = UxConnectionGate()
        val old = gate.start()
        assertTrue(gate.acceptGet(old))
        assertNotNull(gate.fail(old))
        assertFalse(gate.acceptCallback(old))
        assertFalse(gate.acceptGet(old))
    }

    @Test fun retryUsesANewAttemptAndRequiresItsOwnGet() {
        val gate = UxConnectionGate()
        val old = gate.start()
        gate.acceptGet(old)
        val retry = requireNotNull(gate.fail(old))
        val fresh = requireNotNull(gate.beginRetry(retry))
        assertNotEquals(old, fresh)
        assertFalse(gate.acceptGet(old))
        assertFalse(gate.acceptCallback(old))
        assertFalse(gate.acceptCallback(fresh))
        assertTrue(gate.acceptGet(fresh))
        assertTrue(gate.acceptCallback(fresh))
    }

    @Test fun lateDisconnectFromOldAttemptCannotInvalidateTheFreshConnection() {
        val gate = UxConnectionGate()
        val old = gate.start()
        val fresh = requireNotNull(gate.beginRetry(requireNotNull(gate.fail(old))))
        gate.acceptGet(fresh)
        assertNull(gate.fail(old))
        assertTrue(gate.isCurrent(fresh))
        assertTrue(gate.acceptCallback(fresh))
    }

    @Test fun stopInvalidatesBothCallbacksAndPendingRetryWithoutStartingAnotherAttempt() {
        val gate = UxConnectionGate()
        val attempt = gate.start()
        val retry = requireNotNull(gate.fail(attempt))
        gate.stop()
        assertFalse(gate.isPending(retry))
        assertNull(gate.beginRetry(retry))
        assertFalse(gate.acceptGet(attempt))
        assertFalse(gate.acceptCallback(attempt))
        assertNull(gate.fail(attempt))
    }

    @Test fun stopAlsoSuppressesALateCallbackFromAPreviouslyKnownConnection() {
        val gate = UxConnectionGate()
        val attempt = gate.start()
        gate.acceptGet(attempt)
        gate.stop()
        assertFalse(gate.acceptCallback(attempt))
        assertFalse(gate.acceptGet(attempt))
    }

    @Test fun oneFailureCanConsumeOnlyOneBackoffAndOneScheduledTicket() {
        val gate = UxConnectionGate()
        val first = gate.start()
        val retry = requireNotNull(gate.fail(first))
        assertEquals(1_000L, retry.delayMillis)
        assertNull(gate.fail(first))
        val second = requireNotNull(gate.beginRetry(retry))
        assertNull(gate.beginRetry(retry))
        assertEquals(3_000L, requireNotNull(gate.fail(second)).delayMillis)
    }

    @Test fun backoffIsFiniteEvenIfEveryRetryObtainsAFreshGetBeforeDisconnecting() {
        val gate = UxConnectionGate()
        var attempt = gate.start()
        for (delay in listOf(1_000L, 3_000L, 10_000L)) {
            assertTrue(gate.acceptGet(attempt))
            val retry = requireNotNull(gate.fail(attempt))
            assertEquals(delay, retry.delayMillis)
            attempt = requireNotNull(gate.beginRetry(retry))
        }
        gate.acceptGet(attempt)
        assertNull(gate.fail(attempt))
        assertFalse(gate.isCurrent(attempt))
        assertFalse(gate.acceptGet(attempt))
        assertFalse(gate.acceptCallback(attempt))
    }

    @Test fun aNewForegroundStartRefillsBudgetButOldTicketsAndCallbacksRemainInvalid() {
        val gate = UxConnectionGate(listOf(12L))
        val old = gate.start()
        val oldRetry = requireNotNull(gate.fail(old))
        val restarted = gate.start()
        assertNull(gate.beginRetry(oldRetry))
        assertFalse(gate.acceptGet(old))
        assertTrue(gate.isCurrent(restarted))
        assertEquals(12L, requireNotNull(gate.fail(restarted)).delayMillis)
    }

    @Test fun anEmptyRetryBudgetFailsClosedAfterTheInitialAttempt() {
        val gate = UxConnectionGate(emptyList())
        val attempt = gate.start()
        assertNull(gate.fail(attempt))
        assertFalse(gate.isCurrent(attempt))
        assertFalse(gate.acceptCallback(attempt))
    }
}
