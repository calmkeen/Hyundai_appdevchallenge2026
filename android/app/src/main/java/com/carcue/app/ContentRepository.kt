package com.carcue.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant

class UiCopy(private val locale: String, private val strings: JSONObject) {
    fun get(key: String): String {
        val translations = strings.getJSONObject(key)
        return translations.optString(locale).ifEmpty { translations.getString("en") }
    }
}

class ContentRepository(private val context: Context) {
    private val strings = JSONObject(context.assets.open("locales/ui.json").bufferedReader().use { it.readText() })
    fun copy(locale: String) = UiCopy(locale, strings)
    private fun array(path: String) = JSONArray(context.assets.open(path).bufferedReader().use { it.readText() })
    val profiles: List<Profile> = array("profiles/catalog.json").let { data ->
        (0 until data.length()).map { data.getJSONObject(it).let { p ->
            Profile(p.getString("profile_id"), p.getString("display_name"), p.getInt("model_year"), p.getString("market_code"), p.getString("verification_status") == "VERIFIED",
                p.optString("manual_set_id").takeUnless { s -> s == "null" || s.isBlank() }, p.optString("manual_version").takeUnless { s -> s == "null" || s.isBlank() }) } }
    }
    private val localeCatalog = array("locales/catalog.json")
    val languages: List<Language> = localeCatalog.let { data ->
        (0 until data.length()).map { data.getJSONObject(it) }
            .filter { !BuildConfig.IS_MOCK || it.optBoolean("mock_visible", false) }
            .map { l ->
            Language(l.getString("locale"), l.getString("native_name"), l.getString("display_name"), l.getBoolean("rtl"), l.getString("ui_status")) } }
    private val guidePolicy by lazy { GuidePublicationPolicy(profiles,
        (0 until localeCatalog.length()).map { localeCatalog.getJSONObject(it).getString("locale") }.toSet()) }
    private val guideCache by lazy { PublishedGuideCache(File(context.filesDir, "public_guides"), guidePolicy) { decodeGuides(JSONArray(it)) } }
    private val stateGuideRules: List<StateGuideRule> by lazy {
        try {
            val data = array("state-guide-rules.json")
            (0 until data.length()).map { data.getJSONObject(it).let { rule ->
                StateGuideRule(rule.text("rule_id"), rule.text("profile_id"), rule.text("manual_set_id"), rule.text("source_version"),
                    rule.text("property_id"), rule.text("area_id"), rule.text("value"), rule.text("guide_id"), rule.text("verification_status")) } }
        } catch (_: Exception) { emptyList() } // Missing/malformed bundled rules never create a recommendation.
    }
    private val doorGuides by lazy { DoorGuidePolicy(profiles, stateGuideRules, BuildConfig.STATE_TTL_MS) }

    fun relatedDoorGuide(state: UiState, now: Instant): Guide? = if (!state.sessionStarted) null else
        doorGuides.relatedGuide(state.profile, state.locale, state.reading, state.ux, state.guides, now)

    // The same publication gate applies to both API results and offline cached results.
    fun parseGuides(data: JSONArray, profile: Profile, locale: String): List<Guide> =
        guidePolicy.published(decodeGuides(data), profile, locale).map { it.toGuide() }
    fun cachedGuides(profile: Profile, locale: String): List<Guide> = guideCache.read(profile, locale).map { it.toGuide() }
    fun saveGuides(profile: Profile, locale: String, data: JSONArray): List<Guide> =
        guideCache.replace(profile, locale, data.toString()).map { it.toGuide() }

    private fun decodeGuides(data: JSONArray): List<PublishedGuideRecord> = decodeUnambiguousPublishedGuides(
        (0 until data.length()).map { data.optJSONObject(it) },
        identity = { it?.publicationIdentity() },
        decode = { raw -> raw?.let { decodeGuide(it) } })

    private fun decodeGuide(g: JSONObject): PublishedGuideRecord? = try {
        val sources = g.getJSONArray("sources")
        val steps = g.getJSONArray("steps")
        PublishedGuideRecord(g.text("guide_id"), g.getJSONArray("profile_ids").texts(), g.nullableText("manual_set_id"),
            g.nullableText("source_version"), g.text("topic"), g.text("title"), g.text("body"), g.text("locale"),
            g.text("source_locale"), g.text("lifecycle"), g.text("translation_review_status"), g.nullableText("glossary_version"),
            (0 until sources.length()).map { sources.getJSONObject(it).let { source ->
                PublishedGuideSource(source.text("source_id"), source.text("title"), source.text("url"),
                    source.nullableText("version"), source.nullableText("section"), source.text("verification_status")) } },
            (0 until steps.length()).map { steps.getJSONObject(it).let { step ->
                val order = step.get("order") as? Number ?: error("Step order must be an integer")
                require(order.toDouble() == order.toInt().toDouble())
                PublishedGuideStep(step.text("step_id"), order.toInt(), step.text("title"), step.text("body"),
                    step.getJSONArray("official_cautions").texts(), step.getJSONArray("source_ids").texts()) } })
    } catch (_: Exception) { null } // An unrelated malformed record must not hide valid records.
}

private fun JSONObject.publicationIdentity(): PublishedGuideIdentity? {
    if (opt("lifecycle") != "PUBLISHED") return null
    val id = opt("guide_id") as? String ?: return null
    val locale = opt("locale") as? String ?: return null
    val manualSetId = opt("manual_set_id") as? String ?: return null
    val version = opt("source_version") as? String ?: return null
    return PublishedGuideIdentity(id, locale, manualSetId, version)
}

private fun JSONObject.text(key: String): String = get(key) as? String ?: error("Expected string: $key")
private fun JSONObject.nullableText(key: String): String? = get(key).let { value ->
    if (value == JSONObject.NULL) null else value as? String ?: error("Expected nullable string: $key")
}
private fun JSONArray.texts(): List<String> = (0 until length()).map { get(it) as? String ?: error("Expected string array") }
