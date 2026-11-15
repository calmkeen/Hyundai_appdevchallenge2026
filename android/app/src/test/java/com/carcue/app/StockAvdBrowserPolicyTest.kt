package com.carcue.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StockAvdBrowserPolicyTest {
    @Test fun ordinaryReleaseCannotUseTheImageSpecificRoute() {
        assertFalse(stockAvdBrowserAllowed(false, false, false, 34, "ranchu"))
    }

    @Test fun explicitSubmissionProfilePreservesSdkAvdRoutingWithoutDebugging() {
        assertTrue(stockAvdBrowserAllowed(false, true, false, 34, "ranchu"))
        assertTrue(stockAvdBrowserAllowed(true, false, false, 34, "ranchu"))
    }

    @Test fun submissionFlagCannotEnableMockPhysicalHardwareOrOtherAndroidImages() {
        for (debug in listOf(false, true)) {
            assertFalse(stockAvdBrowserAllowed(debug, true, true, 34, "ranchu"))
            assertFalse(stockAvdBrowserAllowed(debug, true, false, 35, "ranchu"))
            assertFalse(stockAvdBrowserAllowed(debug, true, false, 34, "physical"))
            assertFalse(stockAvdBrowserAllowed(debug, true, false, 34, ""))
        }
    }
}
