package com.carcue.app

import java.time.Duration
import java.time.Instant

internal data class StateGuideRule(
    val id: String,
    val profileId: String,
    val manualSetId: String,
    val sourceVersion: String,
    val propertyId: String,
    val areaId: String,
    val value: String,
    val guideId: String,
    val verificationStatus: String,
)

/** A manual lookup for one tested SDK property/area. It never interprets CLOSED as locked or safe. */
internal class DoorGuidePolicy(
    private val profiles: List<Profile>,
    private val rules: List<StateGuideRule>,
    private val ttlMs: Long,
) {
    fun relatedGuide(profile: Profile?, locale: String, reading: Reading, ux: UxState,
                     guides: List<Guide>, now: Instant): Guide? {
        if (profile == null || profiles.singleOrNull { it.id == profile.id } != profile || !profile.verified ||
            profile.manualSetId.isNullOrBlank() || profile.manualVersion.isNullOrBlank() ||
            !ux.known || ux.restricted || ttlMs <= 0 || reading.source != Source.PLEOS ||
            reading.capability != Capability.SUPPORTED || reading.status != ReadStatus.VALUE ||
            reading.propertyId != "door.position" || reading.areaId != "ROW_1_LEFT" || reading.value != "OPEN" ||
            reading.rawValue != "1" || reading.errorCode != null) return null
        val received = reading.receivedAt ?: return null
        val age = Duration.between(received, now)
        if (age.isNegative || age > Duration.ofMillis(ttlMs)) return null
        val matching = rules.filter { it.verificationStatus == "VERIFIED" && it.id.isNotBlank() &&
            it.profileId == profile.id && it.manualSetId == profile.manualSetId && it.sourceVersion == profile.manualVersion &&
            it.propertyId == reading.propertyId && it.areaId == reading.areaId && it.value == reading.value && it.guideId.isNotBlank() }
        val rule = matching.singleOrNull() ?: return null
        // Ambiguous registered IDs and multiple candidates fail closed instead of picking the first one.
        if (rules.count { it.id == rule.id && it.verificationStatus == "VERIFIED" } != 1) return null
        return guides.filter { it.id == rule.guideId && it.publicationVerified && it.sources.isNotEmpty() &&
            it.locale == locale && profile.id in it.profileIds && it.manualSetId == rule.manualSetId &&
            it.sourceVersion == rule.sourceVersion }.singleOrNull()
    }
}
