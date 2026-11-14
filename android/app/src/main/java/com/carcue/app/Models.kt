package com.carcue.app

import java.time.Instant

enum class Capability { UNKNOWN, SUPPORTED, UNSUPPORTED, CHECK_FAILED }
enum class ReadStatus { NOT_REQUESTED, LOADING, VALUE, UNAVAILABLE, ERROR, STALE }
enum class Source { MOCK, PLEOS }
enum class GuideOrigin { NONE, BUNDLED, CACHE, SERVER }
fun doorPositionValue(raw: Int, minimum: Int?, maximum: Int?, area: String): String =
    if (minimum == 0 && maximum == 1 && area == "ROW_1_LEFT") when (raw) {
        0 -> "CLOSED"
        1 -> "OPEN"
        else -> raw.toString()
    } else raw.toString()
data class Reading(
    val propertyId: String = "door.position",
    val areaId: String? = "ROW_1_LEFT",
    val capability: Capability = Capability.UNKNOWN,
    val status: ReadStatus = ReadStatus.NOT_REQUESTED,
    val value: String? = null,
    val rawValue: String? = null,
    val receivedAt: Instant? = null,
    val checkedAt: Instant? = null,
    val source: Source,
    val errorCode: String? = null,
    val previousValue: String? = null,
) {
    init {
        require((status == ReadStatus.VALUE) == (value != null))
        require(status != ReadStatus.VALUE || capability == Capability.SUPPORTED)
    }
    fun expired(now: Instant, ttl: Long): Reading =
        if (status == ReadStatus.VALUE && receivedAt != null && now.toEpochMilli() - receivedAt.toEpochMilli() > ttl)
            copy(status = ReadStatus.STALE, value = null, previousValue = value) else this
}
data class UxState(val known: Boolean = false, val restricted: Boolean = true, val flags: Int = 0)
enum class Page { PROFILE, LANGUAGE, HOME, STATUS, DETAIL, GUIDES, GUIDE, ASK, TRANSLATE, SETTINGS }
data class Profile(val id: String, val name: String, val year: Int, val market: String, val verified: Boolean,
    val manualSetId: String? = null, val manualVersion: String? = null,
    val supportContacts: List<SupportContact> = emptyList())
data class Language(val tag: String, val native: String, val korean: String, val rtl: Boolean, val uiStatus: String)
data class Guide(val id: String, val title: String, val body: String, val steps: List<Pair<String, String>>, val sources: List<Pair<String, String>>,
    val locale: String = "ko-KR", val stepIds: List<String> = emptyList(), val cautions: List<List<String>> = emptyList(),
    val manualSetId: String? = null, val sourceVersion: String? = null, val profileIds: List<String> = emptyList(),
    val publicationVerified: Boolean = false, val origin: GuideOrigin = GuideOrigin.NONE,
    val officialSources: List<OfficialSource> = emptyList())
data class UiState(
    val page: Page = Page.PROFILE,
    val sessionEpoch: Int = 0,
    val profile: Profile? = null,
    val locale: String = "ko-KR",
    val sessionStarted: Boolean = false,
    val reading: Reading,
    val ux: UxState = UxState(),
    val vehicleConnection: String = "NOT_CONNECTED",
    val serverConnection: String = "NOT_CONNECTED",
    val guideConnection: String = "NOT_CONNECTED",
    val guidesLoading: Boolean = false,
    val internetAvailable: Boolean? = null,
    val answer: String = "",
    val answerMode: String = "",
    val answerLocale: String = "",
    val answerStatus: String = "",
    val answerRequestId: String = "",
    val followUpQuestion: String = "",
    val answerProvider: AiProvider = AiProvider.UNKNOWN,
    val answerModel: String? = null,
    val assistantRetry: AssistantRetry = AssistantRetry.NONE,
    val lastAiRequestId: String = "",
    val actions: List<Pair<String, String?>> = emptyList(),
    val citations: List<Pair<String, String>> = emptyList(),
    val officialCitations: List<OfficialCitation> = emptyList(),
    val externalResource: ExternalResourceNotice? = null,
    val busy: Boolean = false,
    val selectedGuide: Guide? = null,
    val guideStep: Int = 0,
    val guides: List<Guide> = emptyList(),
    val translation: String = "",
    val translationOriginal: String = "",
    val translationReview: String = "",
    val translationMode: String = "",
    val translationProvider: AiProvider = AiProvider.UNKNOWN,
    val translationModel: String? = null,
    val translationDraft: String = "",
    val translationKind: String = "QUESTION",
    val translationSourceLocale: String = "auto",
    val error: String? = null,
    val deletionPending: Boolean = false,
    val eventLog: List<String> = emptyList(),
)
