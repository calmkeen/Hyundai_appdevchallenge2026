package com.carcue.app

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

internal data class GuideRequestScope(val profile: Profile, val locale: String)
internal data class GuideRequestToken(val scope: GuideRequestScope, val sequence: Long)

/** Orders refreshes for each vehicle/manual/language, independently of network completion order. */
internal class GuideRequestGate {
    private var sequence = 0L
    private val latest = mutableMapOf<GuideRequestScope, Long>()
    private val cacheWrites = Mutex()

    @Synchronized fun begin(profile: Profile, locale: String): GuideRequestToken {
        val scope = GuideRequestScope(profile, locale)
        return GuideRequestToken(scope, ++sequence).also { latest[scope] = it.sequence }
    }

    @Synchronized fun isCurrent(token: GuideRequestToken) = latest[token.scope] == token.sequence
    @Synchronized fun invalidate() { latest.clear() }

    suspend fun <T : Any> commitIfCurrent(token: GuideRequestToken, write: () -> T): T? = cacheWrites.withLock {
        // Check inside the write mutex. A newer empty response can never be followed by an old write.
        if (isCurrent(token)) write() else null
    }
}
