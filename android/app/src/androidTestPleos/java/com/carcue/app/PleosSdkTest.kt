package com.carcue.app

import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Official Pleos AVD only; the external test driver changes the simulator's front-left door. */
@RunWith(AndroidJUnit4::class)
class PleosSdkTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()
    private val vm get() = ViewModelProvider(rule.activity)[CarCueViewModel::class.java]
    private fun screenshot(name: String) {
        val directory = File(rule.activity.filesDir, "qa").apply { mkdirs() }
        File(directory, "$name.png").outputStream().use {
            rule.onRoot().captureToImage().asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }
    @Test fun getChangeCallbackAndRelease() {
        assertFalse(BuildConfig.IS_MOCK)
        rule.runOnIdle { vm.openReadOnlyStatus() }
        rule.waitUntil(60000) { vm.state.value.reading.status == ReadStatus.VALUE }
        var initial: String? = null
        rule.runOnIdle {
            val reading = vm.state.value.reading
            assertEquals(Source.PLEOS, reading.source)
            assertEquals(Capability.SUPPORTED, reading.capability)
            assertNotNull(reading.receivedAt)
            initial = reading.value
        }
        screenshot("pleos-initial-get")
        android.util.Log.i("CarCueVehicle", "SDK_TEST:UX_STATE:known=${vm.state.value.ux.known}:restricted=${vm.state.value.ux.restricted}:flags=${vm.state.value.ux.flags}")
        android.util.Log.i("CarCueVehicle", "SDK_TEST:INITIAL_CAPTURED:value=$initial")
        rule.waitUntil(120000) { vm.state.value.reading.value != initial &&
            vm.state.value.reading.status == ReadStatus.VALUE && vm.state.value.eventLog.any { it.contains("CALLBACK_RECEIVED") } }
        screenshot("pleos-changed-callback")
        rule.runOnIdle { vm.endSession() }
        rule.runOnIdle {
            assertNull(vm.state.value.reading.value)
            assertFalse(vm.state.value.sessionStarted)
        }
        screenshot("pleos-session-ended")
    }
}
