package com.carcue.app

import java.net.URI

data class OfficialSource(val id: String, val url: String, val sourceLocale: String)
data class OfficialCitation(val sourceId: String, val guideId: String, val profileId: String,
    val manualSetId: String, val sourceVersion: String, val url: String)
data class SupportContact(val id: String, val kind: String, val title: String, val url: String,
    val market: String, val sourceLocale: String, val verified: Boolean)
data class OfficialActionScope(val epoch: Int, val profileId: String?, val locale: String)
enum class ExternalOpenResult { INTENT_DISPATCHED, NO_HANDLER, REJECTED }
enum class ExternalOpenRoute { STANDARD, PLEOS_AVD_STOCK }
data class ExternalResource(val id: String, val title: String, val url: String, val market: String, val sourceLocale: String)
data class ExternalResourceNotice(val resource: ExternalResource, val result: ExternalOpenResult,
    val route: ExternalOpenRoute = ExternalOpenRoute.STANDARD)

/** Bundled reviewed registration is authoritative; server/model URLs are never executable targets. */
internal class OfficialResourcePolicy(
    private val profiles: List<Profile>,
    private val manuals: List<Pair<Profile, Guide>>,
) {
    fun scope(state: UiState) = OfficialActionScope(state.sessionEpoch, state.profile?.id, state.locale)

    private fun profile(state: UiState, expected: OfficialActionScope): Profile? {
        if (!state.sessionStarted || !state.ux.known || state.ux.restricted || scope(state) != expected) return null
        return state.profile?.takeIf { it.verified && !it.manualSetId.isNullOrBlank() && !it.manualVersion.isNullOrBlank() &&
            profiles.singleOrNull { p -> p.id == it.id } == it }
    }

    fun support(state: UiState, expected: OfficialActionScope, id: String): ExternalResource? {
        if (!validId(id)) return null
        val profile = profile(state, expected) ?: return null
        val contact = profile.supportContacts.singleOrNull { it.id == id } ?: return null
        if (!contact.verified || contact.kind != "WEBSITE" || contact.market != profile.market ||
            contact.title.isBlank() || contact.sourceLocale.isBlank() || !https(contact.url)) return null
        return ExternalResource(contact.id, contact.title, contact.url, contact.market, contact.sourceLocale)
    }

    fun guideSource(state: UiState, expected: OfficialActionScope, guideId: String, sourceId: String): ExternalResource? {
        if (!validId(sourceId)) return null
        val profile = profile(state, expected) ?: return null
        if (state.page != Page.GUIDE) return null
        val guide = state.selectedGuide?.takeIf { it.id == guideId } ?: return null
        // In the current language an authoritative empty/withdrawn snapshot disables an old button.
        if (guide.locale == state.locale && state.guides.none { it == guide }) return null
        return manual(profile, guide, sourceId)
    }

    fun citation(state: UiState, expected: OfficialActionScope, requestId: String, sourceId: String): ExternalResource? {
        if (!validId(sourceId)) return null
        val profile = profile(state, expected) ?: return null
        if (state.page != Page.ASK || requestId.isBlank() || state.answerRequestId != requestId ||
            state.answerStatus != "ANSWERED" || state.answer.isBlank()) return null
        val c = state.officialCitations.singleOrNull { it.sourceId == sourceId } ?: return null
        if (c.profileId != profile.id || c.manualSetId != profile.manualSetId || c.sourceVersion != profile.manualVersion) return null
        val guide = state.guides.singleOrNull { it.id == c.guideId && it.locale == state.locale } ?: return null
        return manual(profile, guide, sourceId)?.takeIf { it.url == c.url }
    }

    private fun manual(profile: Profile, guide: Guide, id: String): ExternalResource? {
        if (!guide.publicationVerified || profile.id !in guide.profileIds || guide.manualSetId != profile.manualSetId ||
            guide.sourceVersion != profile.manualVersion) return null
        val source = guide.officialSources.singleOrNull { it.id == id } ?: return null
        val registered = manuals.singleOrNull { (p, g) -> p == profile && g.id == guide.id &&
            g.locale == guide.locale && g.manualSetId == guide.manualSetId && g.sourceVersion == guide.sourceVersion }?.second ?: return null
        val original = registered.officialSources.singleOrNull { it.id == id } ?: return null
        if (source != original || !https(original.url)) return null
        val title = registered.sources.getOrNull(registered.officialSources.indexOf(original))?.first ?: return null
        return ExternalResource(id, title, original.url, profile.market, original.sourceLocale)
    }

    private fun validId(id: String) = id.matches(Regex("[A-Za-z0-9][A-Za-z0-9._-]{0,127}"))

    private fun https(url: String) = try {
        val uri = URI(url)
        uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null && uri.port == -1 &&
            !url.any { it.isWhitespace() || it.code < 32 } && '\\' !in url &&
            !java.net.URLDecoder.decode(url, "UTF-8").any { it.code < 32 || it.code == 127 }
    } catch (_: Exception) { false }
}
