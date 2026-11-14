package com.carcue.app

import android.app.Application
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/** A single queue/worker for every ViewModel; no questions, translations or vehicle readings persist. */
internal object AppDeletionRecovery {
    @Volatile private var instance: SessionDeletionRecovery? = null

    fun get(application: Application): SessionDeletionRecovery = instance ?: synchronized(this) {
        instance ?: run {
            val api = CarCueApi()
            SessionDeletionRecovery(CoroutineScope(SupervisorJob() + Dispatchers.IO), DeletionQueue(application), delete = { api.delete(it) })
                .also { instance = it }
        }
    }
}
