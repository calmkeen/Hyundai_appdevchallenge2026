package com.carcue.app

import android.car.Car
import android.car.drivingstate.CarUxRestrictions
import android.car.drivingstate.CarUxRestrictionsManager
import android.content.ComponentName
import android.content.Context
import android.content.ServiceConnection
import android.os.Handler
import android.os.IBinder
import android.os.Looper

private fun debugUx(phase: String, error: Throwable? = null) {
    if (BuildConfig.DEBUG) android.util.Log.i("CarCueVehicle", "UX:$phase" + (error?.let { ":${it.javaClass.simpleName}" } ?: ""))
}

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

/** Safety monitoring is independent of the vehicle data session. Unknown always fails closed.
 * The ViewModel calls start/stop on main; all attempt and timer events share that looper.
 */
class PlatformUxMonitor(private val context: Context) : UxMonitor {
    private val handler = Handler(Looper.getMainLooper())
    private val gate = UxConnectionGate()
    private var report: ((UxState) -> Unit)? = null
    private var current: Attempt? = null
    private var retryTask: Runnable? = null

    private inner class Attempt(val token: UxConnectionGate.Attempt) {
        var car: Car? = null
        var manager: CarUxRestrictionsManager? = null
        var listenerRegistered = false
        var closed = false
        val timeout = Runnable { fail(this, "INITIAL_CONNECT_TIMEOUT") }
        val listener = CarUxRestrictionsManager.OnUxRestrictionsChangedListener { restrictions ->
            onMain {
                if (!closed && gate.acceptCallback(token)) apply(restrictions, "CALLBACK")
            }
        }
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName?, binder: IBinder?) = onMain {
                connected(this@Attempt)
            }
            override fun onServiceDisconnected(name: ComponentName?) = onMain {
                fail(this@Attempt, "DISCONNECTED")
            }
        }
    }

    private fun onMain(block: () -> Unit) {
        if (Looper.myLooper() == handler.looper) block() else handler.post { block() }
    }

    private fun requireMainThread() = check(Looper.myLooper() == handler.looper) { "UX lifecycle must run on main" }

    private fun apply(restrictions: CarUxRestrictions, origin: String) {
        if (BuildConfig.DEBUG) android.util.Log.i("CarCueVehicle", "UX:$origin:requires=${restrictions.isRequiresDistractionOptimization}:flags=${restrictions.activeRestrictions}")
        report?.invoke(UxState(known = true, restricted = restrictions.isRequiresDistractionOptimization ||
                restrictions.activeRestrictions != CarUxRestrictions.UX_RESTRICTIONS_BASELINE, flags = restrictions.activeRestrictions))
    }

    override fun start(callback: (UxState) -> Unit) {
        requireMainThread()
        stop()
        report = callback
        val token = gate.start()
        callback(UxState())
        // The callback may synchronously stop or replace this foreground session.
        if (gate.isCurrent(token)) begin(token)
    }

    private fun begin(token: UxConnectionGate.Attempt) {
        if (!gate.isCurrent(token)) return
        val attempt = Attempt(token)
        current = attempt
        debugUx("CONNECT_START")
        debugUx("ATTEMPT:${token.number}")
        handler.postDelayed(attempt.timeout, INITIAL_CONNECT_TIMEOUT_MS)
        var phase = "CREATE_CAR"
        try {
            attempt.car = Car.createCar(context.applicationContext, attempt.connection)
            val car = attempt.car ?: run { fail(attempt, "CAR_UNAVAILABLE"); return }
            phase = "CONNECT"
            car.connect()
            debugUx("CONNECT_RETURNED")
        } catch (error: Exception) { fail(attempt, "ERROR:$phase", error) }
    }

    private fun connected(attempt: Attempt) {
        if (attempt.closed || !gate.isCurrent(attempt.token) || attempt.manager != null) return
        debugUx("SERVICE_CONNECTED")
        debugUx("ATTEMPT_CONNECTED:${attempt.token.number}")
        var phase = "GET_MANAGER"
        try {
            val manager = attempt.car?.getCarManager(Car.CAR_UX_RESTRICTION_SERVICE) as? CarUxRestrictionsManager
                ?: run { fail(attempt, "MANAGER_UNAVAILABLE"); return }
            attempt.manager = manager
            phase = "REGISTER_LISTENER"
            // Set ownership before calling Binder: a call may register remotely and then fail.
            attempt.listenerRegistered = true
            manager.registerListener(attempt.listener)
            phase = "GET_RESTRICTIONS"
            val restrictions = manager.currentCarUxRestrictions
                ?: run { fail(attempt, "GET_UNAVAILABLE"); return }
            if (gate.acceptGet(attempt.token)) {
                handler.removeCallbacks(attempt.timeout)
                apply(restrictions, "GET")
            }
        } catch (error: Exception) { fail(attempt, "ERROR:$phase", error) }
    }

    private fun fail(attempt: Attempt, phase: String, error: Exception? = null) {
        // Invalidate before cleanup; disconnect/unregister can deliver late events.
        if (attempt.closed || !gate.isCurrent(attempt.token)) return
        val retry = gate.fail(attempt.token)
        if (current === attempt) current = null
        handler.removeCallbacks(attempt.timeout)
        debugUx(phase, error)
        debugUx("ATTEMPT_FAILED:${attempt.token.number}:$phase")
        report?.invoke(UxState())
        close(attempt)
        if (retry == null) {
            debugUx("RETRY_EXHAUSTED")
        } else if (gate.isPending(retry)) {
            debugUx("RETRY_SCHEDULED:${retry.delayMillis}")
            val task = object : Runnable {
                override fun run() {
                    if (retryTask === this) retryTask = null
                    gate.beginRetry(retry)?.let(::begin)
                }
            }
            retryTask = task
            handler.postDelayed(task, retry.delayMillis)
        }
    }

    private fun close(attempt: Attempt) {
        if (attempt.closed) return
        attempt.closed = true
        debugUx("ATTEMPT_CLOSED:${attempt.token.number}")
        handler.removeCallbacks(attempt.timeout)
        val manager = attempt.manager
        val car = attempt.car
        attempt.manager = null
        attempt.car = null
        if (attempt.listenerRegistered) {
            attempt.listenerRegistered = false
            try { manager?.unregisterListener() } catch (error: Exception) { debugUx("ERROR:UNREGISTER_LISTENER", error) }
        }
        try { car?.disconnect() } catch (error: Exception) { debugUx("ERROR:DISCONNECT", error) }
    }

    override fun stop() {
        requireMainThread()
        gate.stop()
        report = null
        retryTask?.let(handler::removeCallbacks)
        retryTask = null
        val attempt = current
        current = null
        attempt?.let(::close)
    }

    private companion object {
        const val INITIAL_CONNECT_TIMEOUT_MS = 15_000L
    }
}
