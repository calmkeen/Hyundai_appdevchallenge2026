package com.carcue.app

import java.net.IDN
import java.net.URI
import java.net.URLDecoder

/** Metadata used to decide whether server or cached content is safe to display. No Android I/O. */
internal data class PublishedGuideRecord(
    val id: String,
    val profileIds: List<String>,
    val manualSetId: String?,
    val sourceVersion: String?,
    val topic: String,
    val title: String,
    val body: String,
    val locale: String,
    val sourceLocale: String,
    val lifecycle: String,
    val translationReviewStatus: String,
    val glossaryVersion: String?,
    val sources: List<PublishedGuideSource>,
    val steps: List<PublishedGuideStep>,
) {
    fun publicationIdentity() = if (lifecycle == "PUBLISHED" && manualSetId != null && sourceVersion != null)
        PublishedGuideIdentity(id, locale, manualSetId, sourceVersion) else null

    fun toGuide() = Guide(id, title, body, steps.map { it.title to it.body },
        sources.map { "${it.title} · ${it.section}" to it.url }, locale,
        steps.map { it.id }, steps.map { it.officialCautions }, manualSetId, sourceVersion, profileIds,
        publicationVerified = true, officialSources = sources.map { OfficialSource(it.id, it.url, sourceLocale) }) // Called only after the publication gate accepts this record.
}

internal data class PublishedGuideIdentity(val id: String, val locale: String, val manualSetId: String, val sourceVersion: String)

/** Collect raw identities first: a malformed duplicate must not make the other published record appear unique. */
internal fun <T> decodeUnambiguousPublishedGuides(
    raw: List<T>,
    identity: (T) -> PublishedGuideIdentity?,
    decode: (T) -> PublishedGuideRecord?,
): List<PublishedGuideRecord> {
    val identified = raw.map { it to identity(it) }
    val collisions = identified.mapNotNull { it.second }.groupingBy { it }.eachCount().filterValues { it > 1 }.keys
    return identified.mapNotNull { (record, key) -> if (key != null && key in collisions) null else decode(record) }
}

internal data class PublishedGuideSource(
    val id: String,
    val title: String,
    val url: String,
    val version: String?,
    val section: String?,
    val verificationStatus: String,
)

internal data class PublishedGuideStep(
    val id: String,
    val order: Int,
    val title: String,
    val body: String,
    val officialCautions: List<String>,
    val sourceIds: List<String>,
)

internal class GuidePublicationPolicy(
    private val profiles: List<Profile>,
    private val locales: Set<String>,
) {
    fun published(records: List<PublishedGuideRecord>, profile: Profile, locale: String): List<PublishedGuideRecord> {
        // A caller cannot turn an unverified catalog profile into an approved one by copying its ID.
        if (profiles.singleOrNull { it.id == profile.id } != profile || !verified(profile) || locale !in locales) return emptyList()
        val collisions = records.mapNotNull { it.publicationIdentity() }.groupingBy { it }
            .eachCount().filterValues { it > 1 }.keys
        return records.filter { it.publicationIdentity() !in collisions && publishable(it, profile, locale) }
    }

    private fun verified(profile: Profile) = profile.verified && profile.id.isNotBlank() &&
        profile.year > 0 && profile.market.matches(Regex("[A-Z]{2}")) &&
        !profile.manualSetId.isNullOrBlank() && !profile.manualVersion.isNullOrBlank()

    private fun publishable(g: PublishedGuideRecord, profile: Profile, locale: String): Boolean {
        if (g.lifecycle != "PUBLISHED" || g.id.isBlank() || g.title.isBlank() || g.body.isBlank() || g.topic.isBlank() ||
            g.locale != locale || g.sourceLocale !in locales || g.manualSetId != profile.manualSetId ||
            g.sourceVersion != profile.manualVersion || profile.id !in g.profileIds || g.profileIds.isEmpty()) return false
        if (g.profileIds.any { id -> profiles.singleOrNull { it.id == id }?.let {
                !verified(it) || it.manualSetId != g.manualSetId || it.manualVersion != g.sourceVersion
            } != false }) return false
        if (g.translationReviewStatus !in setOf("NOT_APPLICABLE", "REVIEWED") ||
            (g.locale != g.sourceLocale && (g.translationReviewStatus != "REVIEWED" || g.glossaryVersion.isNullOrBlank()))) return false
        if (g.sources.isEmpty() || g.sources.map { it.id }.toSet().size != g.sources.size ||
            g.sources.any { it.id.isBlank() || it.title.isBlank() || it.verificationStatus != "VERIFIED" ||
                it.version != g.sourceVersion || it.section.isNullOrBlank() || !usableHttps(it.url) }) return false
        val sourceIds = g.sources.map { it.id }.toSet()
        if (g.steps.map { it.id }.toSet().size != g.steps.size) return false
        return g.steps.withIndex().all { (index, step) ->
            step.id.isNotBlank() && step.order == index + 1 && step.title.isNotBlank() && step.body.isNotBlank() &&
                step.sourceIds.isNotEmpty() && step.sourceIds.all { it in sourceIds }
        }
    }

    private fun usableHttps(value: String): Boolean {
        return try {
            if (value.isEmpty() || value.any { it.isWhitespace() } || '\\' in value ||
                URLDecoder.decode(value, "UTF-8").any { it.code < 32 || it.code == 127 }) return false
            val uri = URI(value)
            val authority = uri.rawAuthority ?: return false
            if (!uri.scheme.equals("https", ignoreCase = true) || '@' in authority || authority.endsWith(':')) return false
            // Parse the DNS authority explicitly: URI.host is null for otherwise valid international DNS names.
            val colon = authority.lastIndexOf(':')
            val host = if (colon >= 0) {
                val port = authority.substring(colon + 1)
                val portNumber = port.toIntOrNull()
                if (!port.matches(Regex("[0-9]+")) || portNumber == null || portNumber !in 1..65535) return false
                authority.substring(0, colon)
            } else authority
            val labels = IDN.toASCII(host.trimEnd('.'), IDN.USE_STD3_ASCII_RULES).split('.')
            host.length <= 253 && labels.size >= 2 && !labels.all { label -> label.all { it.isDigit() } } &&
                labels.all { it.matches(Regex("[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?")) }
        } catch (_: Exception) { false }
    }
}
