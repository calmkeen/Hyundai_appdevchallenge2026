package com.carcue.app

/**
 * Records whether this installation may bootstrap reviewed bundled guides for an unseen scope.
 * Legacy v1 deleted empty responses, so a missing cache cannot distinguish an unsynced scope
 * from a server withdrawal. An unmarked upgrade therefore starts blocked; timestamps never
 * promote an existing decision. An authoritative v2 snapshot, including empty, takes priority
 * over bootstrap eligibility at the repository boundary.
 */
internal object BundledGuideBootstrap {
    fun resolve(
        recorded: Boolean?,
        firstInstallTime: Long?,
        lastUpdateTime: Long?,
        persist: (Boolean) -> Boolean,
    ): Boolean {
        if (recorded != null) return recorded
        val fresh = firstInstallTime != null && lastUpdateTime != null &&
            firstInstallTime > 0 && lastUpdateTime > 0 && firstInstallTime == lastUpdateTime
        return try {
            persist(fresh) && fresh
        } catch (_: Exception) {
            false
        }
    }
}
