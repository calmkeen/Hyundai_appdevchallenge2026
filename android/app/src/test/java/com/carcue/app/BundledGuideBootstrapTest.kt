package com.carcue.app

import org.junit.Assert.*
import org.junit.Test

class BundledGuideBootstrapTest {
    @Test fun recordedAllowanceSurvivesUpdatesWithoutAnotherWrite() {
        assertTrue(BundledGuideBootstrap.resolve(true, 10, 20) { error("Recorded decision must not be written again") })
        assertTrue(BundledGuideBootstrap.resolve(true, null, null) { error("Missing timestamps cannot revoke a recorded decision") })
    }

    @Test fun recordedBlockCannotBePromotedByFreshLookingTimestamps() {
        assertFalse(BundledGuideBootstrap.resolve(false, 10, 10) { error("Recorded block must remain unchanged") })
    }

    @Test fun freshInstallationIsAllowedOnlyAfterOneSuccessfulWrite() {
        val writes = mutableListOf<Boolean>()
        assertTrue(BundledGuideBootstrap.resolve(null, 10, 10) { writes.add(it); true })
        assertEquals(listOf(true), writes)
    }

    @Test fun unmarkedUpgradePersistsABlockRatherThanRestoringPotentiallyWithdrawnGuides() {
        val writes = mutableListOf<Boolean>()
        assertFalse(BundledGuideBootstrap.resolve(null, 10, 20) { writes.add(it); true })
        assertEquals(listOf(false), writes)
    }

    @Test fun unavailableOrNonpositiveTimesPersistABlock() {
        listOf(null to 10L, 10L to null, null to null, 0L to 0L, -1L to -1L, 0L to 10L).forEach { (first, updated) ->
            val writes = mutableListOf<Boolean>()
            assertFalse(BundledGuideBootstrap.resolve(null, first, updated) { writes.add(it); true })
            assertEquals(listOf(false), writes)
        }
    }

    @Test fun ReversedTimesAreNotTreatedAsAFreshInstallation() {
        val writes = mutableListOf<Boolean>()
        assertFalse(BundledGuideBootstrap.resolve(null, 20, 10) { writes.add(it); true })
        assertEquals(listOf(false), writes)
    }

    @Test fun failedPersistenceNeverGrantsFreshInstallationBootstrap() {
        assertFalse(BundledGuideBootstrap.resolve(null, 10, 10) { false })
        assertFalse(BundledGuideBootstrap.resolve(null, 10, 20) { false })
    }

    @Test fun persistenceExceptionFailsClosedWithoutRetryingOrGrantingBootstrap() {
        var writes = 0
        assertFalse(BundledGuideBootstrap.resolve(null, 10, 10) { writes++; throw IllegalStateException("Synthetic storage failure") })
        assertEquals(1, writes)
    }
}
