package com.carcue.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

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
    val languages: List<Language> = array("locales/catalog.json").let { data ->
        (0 until data.length()).map { data.getJSONObject(it) }
            .filter { !BuildConfig.IS_MOCK || it.optBoolean("mock_visible", false) }
            .map { l ->
            Language(l.getString("locale"), l.getString("native_name"), l.getString("display_name"), l.getBoolean("rtl"), l.getString("ui_status")) } }
    // DRAFT handoff templates are intentionally not exposed. Reviewed guides arrive via the API.
    fun parseGuides(data: JSONArray, profile: Profile, locale: String): List<Guide> {
        if (!profile.verified || profile.manualVersion == null || profile.manualSetId == null) return emptyList()
        return (0 until data.length()).mapNotNull { i ->
            val g = data.getJSONObject(i)
            val profiles = g.getJSONArray("profile_ids")
            if (g.getString("lifecycle") != "PUBLISHED" || g.getString("locale") != locale ||
                g.getString("manual_set_id") != profile.manualSetId || g.getString("source_version") != profile.manualVersion ||
                (0 until profiles.length()).none { profiles.getString(it) == profile.id }) return@mapNotNull null
            val sources = g.getJSONArray("sources")
            if (sources.length() == 0 || (0 until sources.length()).any { sources.getJSONObject(it).getString("verification_status") != "VERIFIED" }) return@mapNotNull null
            val steps = g.getJSONArray("steps")
            Guide(g.getString("guide_id"), g.getString("title"), g.getString("body"),
                (0 until steps.length()).map { steps.getJSONObject(it).let { step -> step.getString("title") to step.getString("body") } },
                (0 until sources.length()).map { sources.getJSONObject(it).let { s -> s.getString("title") + " · " + s.getString("section") to s.getString("url") } },
                locale, (0 until steps.length()).map { steps.getJSONObject(it).getString("step_id") },
                (0 until steps.length()).map { index -> steps.getJSONObject(index).getJSONArray("official_cautions").let { warnings ->
                    (0 until warnings.length()).map { warnings.getString(it) }
                } })
        }
    }
    private fun cacheFile(profile: Profile, locale: String): File {
        val key = "${profile.id}:${profile.manualSetId}:${profile.manualVersion}:$locale"
        val hash = MessageDigest.getInstance("SHA-256").digest(key.toByteArray()).joinToString("") { "%02x".format(it) }
        return File(context.filesDir, "public_guides/$hash.json").also { it.parentFile?.mkdirs() }
    }
    fun cachedGuides(profile: Profile, locale: String): List<Guide> = try {
        parseGuides(JSONArray(cacheFile(profile, locale).readText()), profile, locale)
    } catch (_: Exception) { emptyList() }
    fun saveGuides(profile: Profile, locale: String, data: JSONArray): List<Guide> {
        val parsed = parseGuides(data, profile, locale)
        if (parsed.isNotEmpty()) {
            val target = cacheFile(profile, locale)
            val temp = File(target.path + ".tmp")
            temp.writeText(data.toString()); temp.renameTo(target)
        }
        return parsed
    }
}
