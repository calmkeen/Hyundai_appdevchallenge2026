package com.carcue.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Only expired-session deletion credentials persist, never question or translation bodies. */
internal class DeletionQueue(context: Context) : SessionDeletionStore {
    private val prefs = context.getSharedPreferences("remote_deletion_only", Context.MODE_PRIVATE)
    @Synchronized private fun read(): List<RemoteSession> {
        val data = JSONArray(prefs.getString("queue", "[]"))
        return (0 until data.length()).map { data.getJSONObject(it).let { s -> RemoteSession(s.getString("id"), s.getString("token"), s.getString("expires")) } }
    }
    @Synchronized private fun write(items: List<RemoteSession>) {
        val array = JSONArray()
        items.forEach { array.put(JSONObject().put("id", it.id).put("token", it.token).put("expires", it.expires)) }
        prefs.edit().putString("queue", array.toString()).commit()
    }
    @Synchronized fun add(session: RemoteSession) { write((read() + session).distinctBy { it.id }) }
    @Synchronized override fun remove(session: RemoteSession) { write(read().filter { it.id != session.id }) }
    @Synchronized fun trackActive(session: RemoteSession?) {
        prefs.edit().putString("active", session?.let { JSONObject().put("id", it.id).put("token", it.token).put("expires", it.expires).toString() }).commit()
    }
    @Synchronized override fun recoverAbandonedSession() {
        prefs.getString("active", null)?.let { JSONObject(it).let { s -> add(RemoteSession(s.getString("id"), s.getString("token"), s.getString("expires"))) } }
        trackActive(null)
    }
    @Synchronized override fun registerCreated(session: RemoteSession, stillCurrent: () -> Boolean) {
        if (stillCurrent()) trackActive(session) else add(session)
    }
    @Synchronized override fun finishActive() {
        prefs.getString("active", null)?.let { JSONObject(it).let { s -> add(RemoteSession(s.getString("id"), s.getString("token"), s.getString("expires"))) } }
        trackActive(null)
    }
    override fun pending(): Boolean = read().isNotEmpty()
    override fun queued(): List<RemoteSession> = read()
}
