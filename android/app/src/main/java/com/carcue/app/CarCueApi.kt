package com.carcue.app

import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject

data class RemoteSession(val id: String, val token: String, val expires: String)
class ApiFailure(val status: Int, val code: String = "UNKNOWN") : Exception("SERVER_$status")

class CarCueApi {
    private fun call(method: String, path: String, data: JSONObject? = null, session: RemoteSession? = null, readTimeoutMillis: Int = 30000): String {
        val base = BuildConfig.SERVER_URL.trimEnd('/')
        require(base.startsWith("https://") || BuildConfig.DEBUG && base.startsWith("http://"))
        val connection = URL(base + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = 8000
            connection.readTimeout = readTimeoutMillis
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            session?.let { connection.setRequestProperty("Authorization", "Bearer ${it.token}") }
            data?.let {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                it.optString("request_id").takeIf { id -> id.isNotBlank() }?.let { id -> connection.setRequestProperty("X-Request-Id", id) }
                connection.outputStream.use { out -> out.write(it.toString().toByteArray(Charsets.UTF_8)) }
            }
            if (connection.responseCode !in 200..299) {
                val code = try { JSONObject(connection.errorStream.bufferedReader().use { it.readText().take(10000) }).optString("detail") } catch (_: Exception) { "UNKNOWN" }
                throw ApiFailure(connection.responseCode, code.takeIf { it.matches(Regex("[A-Z_]{1,100}")) } ?: "UNKNOWN")
            }
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally { connection.disconnect() }
    }
    fun start(profile: String, locale: String): RemoteSession {
        val data = JSONObject(call("POST", "/v1/sessions", JSONObject().put("profile_id", profile).put("locale", locale)))
        return RemoteSession(data.getString("session_id"), data.getString("token"), data.getString("expires_at"))
    }
    fun ask(data: JSONObject, session: RemoteSession) = JSONObject(call("POST", "/v1/ask", data, session, readTimeoutMillis = 130000))
    fun translate(data: JSONObject, session: RemoteSession) = JSONObject(call("POST", "/v1/translate", data, session, readTimeoutMillis = 130000))
    fun delete(session: RemoteSession) { call("DELETE", "/v1/sessions/${session.id}", session = session) }
    fun guides(profile: String, locale: String) = org.json.JSONArray(call("GET", "/v1/guides?profile_id=${java.net.URLEncoder.encode(profile, "UTF-8")}&locale=${java.net.URLEncoder.encode(locale, "UTF-8")}"))
}
