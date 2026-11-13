package com.carcue.app

import ai.pleos.playground.vehicle.Vehicle
import ai.pleos.playground.vehicle.api.model.area.DoorArea
import ai.pleos.playground.vehicle.api.model.capability.AccessType
import ai.pleos.playground.vehicle.constant.area.DoorValue
import ai.pleos.playground.vehicle.listener.DoorPositionListener
import android.content.Context
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import java.time.Instant

/** Read-only SDK adapter. Compilation/runtime must be verified against the installed SDK. */
class PlatformVehicleRepository(private val context: Context) : VehicleRepository {
    private val handler = Handler(Looper.getMainLooper())
    private var vehicle: Vehicle? = null
    private val area = DoorArea(DoorValue.ROW_1_LEFT)
    private var readingCallback: ((Reading) -> Unit)? = null
    private var eventCallback: ((String) -> Unit)? = null
    private var subscribed = false
    private var epoch = 0
    private var request = 0
    private var eventRevision = 0
    private var loading = false
    private var minimum: Int? = null
    private var maximum: Int? = null
    private var current = Reading(source = Source.PLEOS)
    private var listener: DoorPositionListener? = null

    private fun emit(reading: Reading) { current = reading; readingCallback?.invoke(reading) }
    private fun event(name: String) {
        if (BuildConfig.DEBUG) android.util.Log.i("CarCueVehicle", "PLEOS:$name")
        eventCallback?.invoke("PLEOS:$name")
    }
    private fun failed(code: String, capability: Capability = current.capability) {
        loading = false
        emit(current.copy(capability = capability, status = ReadStatus.ERROR, value = null,
            previousValue = current.value ?: current.previousValue, errorCode = code))
        event(code)
    }
    override fun start(onReading: (Reading) -> Unit, onEvent: (String) -> Unit) {
        stop(); epoch++
        readingCallback = onReading; eventCallback = onEvent
        if (context.checkSelfPermission("pleos.car.permission.CAR_DOORS") != PackageManager.PERMISSION_GRANTED) {
            failed("PERMISSION_DENIED", Capability.UNKNOWN); return
        }
        try {
            vehicle = Vehicle(context.applicationContext)
            vehicle?.initialize()
            event("INITIALIZE_RETURNED_NOT_DATA")
            refresh()
        } catch (_: Exception) { failed("INITIALIZE_FAILED", Capability.UNKNOWN) }
    }
    override fun refresh() {
        if (loading) return
        val sdk = vehicle ?: return
        val ticket = epoch; val readRequest = ++request
        loading = true
        emit(current.copy(status = ReadStatus.LOADING, value = null, previousValue = current.value ?: current.previousValue, checkedAt = Instant.now(), errorCode = null))
        handler.postDelayed({ if (epoch == ticket && request == readRequest && loading) { request++; failed("READ_TIMEOUT") } }, 12000)
        try {
            sdk.getDoor().checkDoorPositionCapabilities(onComplete = { config, bounds ->
                handler.post {
                    if (epoch != ticket || request != readRequest) return@post
                    val found = bounds.entries.firstOrNull { DoorValue.ROW_1_LEFT in it.key.values }
                    if (config.accessType == AccessType.NONE || found == null) {
                        loading = false
                        emit(current.copy(capability = Capability.UNSUPPORTED, status = ReadStatus.NOT_REQUESTED, value = null))
                        event("AREA_UNSUPPORTED"); return@post
                    }
                    minimum = (found.value.minValue as? Number)?.toInt()
                    maximum = (found.value.maxValue as? Number)?.toInt()
                    emit(current.copy(capability = Capability.SUPPORTED))
                    event("CAPABILITY_RECEIVED:ROW_1_LEFT:min=$minimum:max=$maximum:access=${config.accessType.name}")
                    read(ticket, readRequest)
                }
            }, onFailed = { handler.post { if (epoch == ticket && request == readRequest) failed("CAPABILITY_FAILED", Capability.CHECK_FAILED) } })
        } catch (_: Exception) { failed("CAPABILITY_FAILED", Capability.CHECK_FAILED) }
    }
    private fun read(ticket: Int, readRequest: Int) {
        val door = vehicle?.getDoor() ?: return
        val revision = eventRevision
        try {
            door.getCurrentDoorPosition(area = area, onComplete = { position ->
                handler.post {
                    if (epoch != ticket || request != readRequest) return@post
                    loading = false
                    if (revision == eventRevision) receive(position, "GET_RECEIVED")
                    if (!subscribed) {
                        val newListener = object : DoorPositionListener {
                            override fun onPositionUpdated(pos: Int?) { handler.post { if (epoch == ticket) { eventRevision++; receive(pos, "CALLBACK_RECEIVED") } } }
                            override fun onFailed(e: Exception) { handler.post { if (epoch == ticket) failed("CALLBACK_FAILED") } }
                        }
                        try { door.registerDoorPosition(area, newListener); listener = newListener; subscribed = true; event("LISTENER_REGISTERED_NOT_CALLBACK") }
                        catch (_: Exception) { event("LISTENER_REGISTRATION_FAILED") }
                    }
                }
            }, onFailed = { handler.post { if (epoch == ticket && request == readRequest) failed("GET_FAILED") } })
        } catch (_: Exception) { failed("GET_FAILED") }
    }
    private fun receive(raw: Int?, kind: String) {
        val min = minimum; val max = maximum
        val valid = raw != null && min != null && max != null && min <= max && raw in min..max
        // Only the tested binary range/physical area is mapped. Other ranges remain uninterpreted.
        emit(current.copy(capability = Capability.SUPPORTED, status = if (valid) ReadStatus.VALUE else ReadStatus.UNAVAILABLE,
            value = if (valid) doorPositionValue(raw!!, min, max, "ROW_1_LEFT") else null, rawValue = raw?.toString(), receivedAt = if (valid) Instant.now() else current.receivedAt,
            errorCode = if (raw != null && !valid) "UNVERIFIED_OR_OUT_OF_RANGE" else null))
        event(kind + if (valid) ":RANGE_VERIFIED:value=$raw:area=ROW_1_LEFT" else ":NO_NORMALIZED_VALUE")
    }
    override fun stop() {
        epoch++; request++; loading = false
        handler.removeCallbacksAndMessages(null)
        val sdk = vehicle
        try {
            if (subscribed) listener?.let { sdk?.getDoor()?.unregisterDoorPosition(area, it); event("LISTENER_UNREGISTER_RETURNED") }
        } catch (_: Exception) { event("UNREGISTER_FAILED") }
        finally {
            try { sdk?.release(); if (sdk != null) event("RELEASE_RETURNED") } catch (_: Exception) { event("RELEASE_FAILED") }
            vehicle = null; listener = null; subscribed = false; readingCallback = null; eventCallback = null
        }
    }
}
