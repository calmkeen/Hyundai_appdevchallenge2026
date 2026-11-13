package com.carcue.app

import android.content.Context
import java.time.Instant

/** Deterministic fixtures. This build never loads or calls Pleos Vehicle SDK. */
class PlatformVehicleRepository(context: Context) : VehicleRepository {
    private var callback: ((Reading) -> Unit)? = null
    private var event: ((String) -> Unit)? = null
    private var selected = "OPEN"
    override fun start(onReading: (Reading) -> Unit, onEvent: (String) -> Unit) {
        callback = onReading; event = onEvent
        event?.invoke("MOCK:START")
        refresh()
    }
    override fun refresh() {
        val now = Instant.now()
        val cap = when (selected) { "UNSUPPORTED" -> Capability.UNSUPPORTED; "CHECK_FAILED" -> Capability.CHECK_FAILED; else -> Capability.SUPPORTED }
        val status = when (selected) { "UNAVAILABLE" -> ReadStatus.UNAVAILABLE; "ERROR" -> ReadStatus.ERROR; "STALE" -> ReadStatus.STALE
            "UNSUPPORTED", "CHECK_FAILED" -> ReadStatus.NOT_REQUESTED; else -> ReadStatus.VALUE }
        callback?.invoke(Reading(source = Source.MOCK, capability = cap, status = status,
            value = if (status == ReadStatus.VALUE) selected else null,
            receivedAt = if (status == ReadStatus.VALUE) now else null, checkedAt = now,
            previousValue = if (selected == "STALE") "OPEN" else null,
            errorCode = if (selected in listOf("ERROR", "CHECK_FAILED")) "MOCK_FAILURE" else null))
        event?.invoke("MOCK:READ:$selected")
    }
    override fun scenario(name: String) {
        selected = name; refresh()
    }
    override fun stop() { event?.invoke("MOCK:STOP"); callback = null; event = null }
}

class PlatformUxMonitor(context: Context) : UxMonitor {
    override fun start(callback: (UxState) -> Unit) { callback(UxState(known = true, restricted = false)) }
    override fun stop() {}
}

fun createUxMonitor(context: Context): UxMonitor = PlatformUxMonitor(context)
