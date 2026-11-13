package com.carcue.app

import android.car.Car
import android.car.drivingstate.CarUxRestrictions
import android.car.drivingstate.CarUxRestrictionsManager
import android.content.ComponentName
import android.content.Context
import android.content.ServiceConnection
import android.os.IBinder

fun createUxMonitor(context: Context): UxMonitor = try {
    Class.forName("android.car.Car")
    PlatformUxMonitor(context)
} catch (_: ClassNotFoundException) {
    UnavailableUxMonitor()
} catch (_: LinkageError) {
    UnavailableUxMonitor()
}

private class UnavailableUxMonitor : UxMonitor {
    override fun start(callback: (UxState) -> Unit) {
        if (BuildConfig.DEBUG) android.util.Log.i("CarCueVehicle", "UX:UNAVAILABLE:android.car")
        callback(UxState())
    }
    override fun stop() {}
}

/** Safety monitoring is independent of the vehicle data session. Unknown always fails closed. */
class PlatformUxMonitor(private val context: Context) : UxMonitor {
    private var car: Car? = null
    private var manager: CarUxRestrictionsManager? = null
    private var report: ((UxState) -> Unit)? = null
    private val listener = CarUxRestrictionsManager.OnUxRestrictionsChangedListener { restrictions -> apply(restrictions, "CALLBACK") }
    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            try {
                manager = car?.getCarManager(Car.CAR_UX_RESTRICTION_SERVICE) as? CarUxRestrictionsManager
                val m = manager ?: return
                m.registerListener(listener)
                apply(m.currentCarUxRestrictions, "GET")
            } catch (_: Exception) { report?.invoke(UxState()) }
        }
        override fun onServiceDisconnected(name: ComponentName?) { manager = null; report?.invoke(UxState()) }
    }
    private fun apply(restrictions: CarUxRestrictions, origin: String) {
        if (BuildConfig.DEBUG) android.util.Log.i("CarCueVehicle", "UX:$origin:requires=${restrictions.isRequiresDistractionOptimization}:flags=${restrictions.activeRestrictions}")
        report?.invoke(UxState(known = true, restricted = restrictions.isRequiresDistractionOptimization ||
                restrictions.activeRestrictions != CarUxRestrictions.UX_RESTRICTIONS_BASELINE, flags = restrictions.activeRestrictions))
    }
    override fun start(callback: (UxState) -> Unit) {
        stop(); report = callback; callback(UxState())
        try { car = Car.createCar(context.applicationContext, connection); car?.connect() }
        catch (_: Exception) { callback(UxState()) }
    }
    override fun stop() {
        try { manager?.unregisterListener() } catch (_: Exception) {}
        try { car?.disconnect() } catch (_: Exception) {}
        manager = null; car = null; report = null
    }
}
