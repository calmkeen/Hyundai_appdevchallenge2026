package com.carcue.app

import java.time.Instant
import org.junit.Assert.*
import org.junit.Test

class ReadingTest {
    @Test fun binaryDoorMappingIsBoundedToTestedRangeAndArea() {
        assertEquals("CLOSED", doorPositionValue(0, 0, 1, "ROW_1_LEFT"))
        assertEquals("OPEN", doorPositionValue(1, 0, 1, "ROW_1_LEFT"))
        assertEquals("1", doorPositionValue(1, 0, 100, "ROW_1_LEFT"))
        assertEquals("1", doorPositionValue(1, 0, 1, "ROW_1_RIGHT"))
    }
    @Test fun nullIsNeverNormal() {
        val unavailable = Reading(source = Source.PLEOS, capability = Capability.SUPPORTED, status = ReadStatus.UNAVAILABLE)
        assertNull(unavailable.value)
        assertNotEquals(ReadStatus.VALUE, unavailable.status)
    }
    @Test fun staleSeparatesHistoricalValueFromCurrent() {
        val now = Instant.parse("2026-11-13T00:00:00Z")
        val original = Reading(source = Source.PLEOS, capability = Capability.SUPPORTED, status = ReadStatus.VALUE, value = "OPEN", receivedAt = now)
        val expired = original.expired(now.plusSeconds(61), 60000)
        assertEquals(ReadStatus.STALE, expired.status)
        assertNull(expired.value)
        assertEquals("OPEN", expired.previousValue)
    }
    @Test fun unchangedCallbacksDoNotInventDisconnect() {
        val now = Instant.now()
        val r = Reading(source = Source.PLEOS, capability = Capability.SUPPORTED, status = ReadStatus.VALUE, value = "CLOSED", receivedAt = now)
        assertEquals(ReadStatus.VALUE, r.expired(now.plusSeconds(30), 60000).status)
    }
    @Test(expected = IllegalArgumentException::class) fun valueRequiresConfirmedSupport() {
        Reading(source = Source.PLEOS, status = ReadStatus.VALUE, value = "0")
    }
    @Test(expected = IllegalArgumentException::class) fun staleCannotPretendToHaveCurrentValue() {
        Reading(source = Source.MOCK, status = ReadStatus.STALE, value = "CLOSED")
    }
}
