package com.carcue.app

import java.time.Instant
import java.util.UUID

enum class AssistantRetry { NONE, RESEND, NEW_REQUEST }
enum class AiProvider { OLLAMA_LOCAL, OPENAI, NOT_CALLED, STORED_GUIDE, UNKNOWN }

data class AssistantGuideContext(val guideId: String, val stepId: String?)
data class AssistantIntent(
    val input: String,
    val translate: Boolean,
    val profileId: String,
    val locale: String,
    val sourceLocale: String = "auto",
    val contentKind: String = "QUESTION",
    val guide: AssistantGuideContext? = null,
)
data class AssistantRequestSnapshot(
    val intent: AssistantIntent,
    val sessionId: String,
    val requestId: String,
    val payload: String,
)

/** In-memory only. A transport retry replays the original body, including the original SDK reading. */
class AssistantRequests(private val nextId: () -> String = { UUID.randomUUID().toString() }) {
    private var previous: AssistantRequestSnapshot? = null

    fun prepare(intent: AssistantIntent, sessionId: String, resend: Boolean, body: (String) -> String): AssistantRequestSnapshot {
        previous?.takeIf { resend && it.intent == intent && it.sessionId == sessionId }?.let { return it }
        val id = nextId()
        return AssistantRequestSnapshot(intent, sessionId, id, body(id)).also { previous = it }
    }

    fun clear() { previous = null }
}

data class AssistantOutcome(val error: String? = null, val retry: AssistantRetry = AssistantRetry.NONE)

object AssistantResponsePolicy {
    fun ask(status: String): AssistantOutcome = when (status) {
        "ANSWERED", "NEED_MORE_INFO", "NO_RELIABLE_SOURCE" -> AssistantOutcome()
        // The server caches this response. A new provider attempt needs a new request ID.
        "TEMPORARILY_UNAVAILABLE" -> AssistantOutcome("AI_UNAVAILABLE", AssistantRetry.NEW_REQUEST)
        else -> AssistantOutcome("SERVER_RESPONSE_INVALID", AssistantRetry.NEW_REQUEST)
    }

    fun translation(status: String): AssistantOutcome = when (status) {
        "TRANSLATED" -> AssistantOutcome()
        "TEMPORARILY_UNAVAILABLE" -> AssistantOutcome("TRANSLATION_UNAVAILABLE", AssistantRetry.NEW_REQUEST)
        else -> AssistantOutcome("SERVER_RESPONSE_INVALID", AssistantRetry.NEW_REQUEST)
    }

    fun expired(status: Int, code: String): Boolean = status == 401 &&
        code in setOf("SESSION_INVALID_OR_EXPIRED", "SESSION_ENDED")

    fun http(status: Int, code: String): AssistantOutcome = when {
        expired(status, code) -> AssistantOutcome("SESSION_EXPIRED", AssistantRetry.NEW_REQUEST)
        status == 409 && code == "REQUEST_ID_REUSED_WITH_DIFFERENT_INPUT" -> AssistantOutcome("HTTP_409", AssistantRetry.NEW_REQUEST)
        status == 408 || status == 429 || status >= 500 -> AssistantOutcome("HTTP_$status", AssistantRetry.RESEND)
        else -> AssistantOutcome("HTTP_$status")
    }

    fun sessionExpired(expires: String, now: Instant): Boolean =
        runCatching { !Instant.parse(expires).isAfter(now) }.getOrDefault(true)

    fun provider(mode: String, value: String): AiProvider = if (mode == "MOCK") AiProvider.NOT_CALLED else
        AiProvider.entries.find { it.name == value } ?: AiProvider.UNKNOWN

    fun model(value: String?): String? = value?.takeIf { it.matches(Regex("[A-Za-z0-9:/._-]{1,128}")) }

    fun guideContext(page: Page, guide: Guide?, step: Int): AssistantGuideContext? =
        guide?.takeIf { page == Page.GUIDE && !it.id.startsWith("__") }
            ?.let { AssistantGuideContext(it.id, it.stepIds.getOrNull(step)) }
}
