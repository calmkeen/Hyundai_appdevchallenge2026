package com.carcue.app

import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest

/** Public content cache. Every read is rechecked against the current catalog and publication policy. */
internal class PublishedGuideCache(
    private val directory: File,
    private val policy: GuidePublicationPolicy,
    private val decode: (String) -> List<PublishedGuideRecord>,
) {
    // If local storage fails, a successful server response must still supersede the old in-process cache.
    private val invalidated = mutableSetOf<String>()

    @Synchronized fun read(profile: Profile, locale: String): List<PublishedGuideRecord> {
        val key = key(profile, locale)
        if (key in invalidated) return emptyList()
        return try {
            policy.published(decode(File(directory, "$key.json").readText()), profile, locale)
        } catch (_: Exception) { emptyList() }
    }

    @Synchronized fun replace(profile: Profile, locale: String, payload: String): List<PublishedGuideRecord> {
        // Decode errors are failed responses; they cannot overwrite an existing valid cache.
        val accepted = policy.published(decode(payload), profile, locale)
        val key = key(profile, locale)
        invalidated.add(key)
        try {
            val target = File(directory, "$key.json")
            if (accepted.isEmpty()) {
                if (target.exists() && !target.delete()) throw IOException("Could not invalidate guide cache")
            } else {
                write(target, payload)
            }
            invalidated.remove(key)
        } catch (_: IOException) {
            // Return the fresh server result, but do not fall back to superseded cached content.
        } catch (_: SecurityException) {
            // The same fail-closed rule applies when the filesystem denies access.
        }
        return accepted
    }

    private fun key(profile: Profile, locale: String): String {
        // Length-prefix fields so delimiters inside identifiers cannot collide.
        val identity = listOf(profile.id, profile.year.toString(), profile.market,
            profile.manualSetId.orEmpty(), profile.manualVersion.orEmpty(), locale)
            .joinToString("") { "${it.length}:$it" }
        return MessageDigest.getInstance("SHA-256").digest(identity.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
    }

    private fun write(target: File, payload: String) {
        if (!directory.isDirectory && !directory.mkdirs()) throw IOException("Could not create guide cache")
        val temp = File(directory, "${target.name}.tmp")
        try {
            FileOutputStream(temp).use { output ->
                output.write(payload.toByteArray(Charsets.UTF_8))
                output.fd.sync()
            }
            try {
                Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
            } catch (_: AtomicMoveNotSupportedException) {
                Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING)
            }
        } finally { temp.delete() }
    }
}
