package com.carcue.app

interface VehicleRepository {
    fun start(onReading: (Reading) -> Unit, onEvent: (String) -> Unit)
    fun refresh()
    fun stop()
    fun scenario(name: String) {}
}

interface UxMonitor {
    fun start(callback: (UxState) -> Unit)
    fun stop()
}
