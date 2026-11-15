package com.carcue.app

import android.app.Application
import android.net.Uri
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.update
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

class CarCueViewModel(application: Application) : AndroidViewModel(application) {
    val content = ContentRepository(application)
    private val source = if (BuildConfig.IS_MOCK) Source.MOCK else Source.PLEOS
    private val repository: VehicleRepository = PlatformVehicleRepository(application)
    private val uxMonitor: UxMonitor = createUxMonitor(application)
    private val api = CarCueApi()
    private val resourceOpener = OfficialResourceOpener(application)
    private val deletion = AppDeletionRecovery.get(application)
    private val guideRequests = GuideRequestGate()
    private val mutable = MutableStateFlow(UiState(reading = Reading(source = source), deletionPending = deletion.pending.value))
    val state = mutable.asStateFlow()
    private var remote: RemoteSession? = null
    @Volatile private var generation = 0
    private var requestJob: Job? = null
    private val assistantRequests = AssistantRequests()
    private val assistantCooldown = AssistantCooldown { android.os.SystemClock.elapsedRealtime() }
    private var cooldownJob: Job? = null
    private var assistantGuideContext: AssistantGuideContext? = null
    private var returnPages = AssistantReturnPages()
    private var active = false
    private var started = false
    @Volatile private var operation = 0
    private val connectivity = application.getSystemService(ConnectivityManager::class.java)
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
            val validated = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            val wasValidated = mutable.value.internetAvailable == true
            mutable.update { it.copy(internetAvailable = validated) }
            if (validated && !wasValidated) deletion.retry()
        }
        override fun onLost(network: Network) { mutable.update { it.copy(internetAvailable = false) } }
    }

    init {
        viewModelScope.launch { deletion.pending.collect { pending -> mutable.update { it.copy(deletionPending = pending) } } }
        connectivity.registerDefaultNetworkCallback(networkCallback)
        viewModelScope.launch {
            while (isActive) {
                delay(5000)
                mutable.update { it.copy(reading = it.reading.expired(Instant.now(), BuildConfig.STATE_TTL_MS)) }
            }
        }
        viewModelScope.launch {
            while (isActive) { delay(30000); if (active && mutable.value.sessionStarted && mutable.value.page in listOf(Page.HOME,Page.STATUS,Page.DETAIL)) repository.refresh() }
        }
    }
    private fun event(text: String) {
        if (BuildConfig.DEBUG && BuildConfig.IS_MOCK) android.util.Log.i("CarCueVehicle", text)
        mutable.update { it.copy(eventLog = (it.eventLog + "${Instant.now()} $text").takeLast(40)) }
    }
    private fun restricted() = !mutable.value.ux.known || mutable.value.ux.restricted
    private fun isLong(page: Page) = page in listOf(Page.PROFILE,Page.LANGUAGE,Page.GUIDES,Page.GUIDE,Page.ASK,Page.TRANSLATE)

    fun foreground() {
        active = true
        mutable.update { it.copy(internetAvailable = connectivity.getNetworkCapabilities(connectivity.activeNetwork)?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED) ?: false) }
        uxMonitor.start { ux ->
            mutable.update { it.copy(ux = ux) }
            if (!ux.known || ux.restricted) cancelRequest()
        }
        if (mutable.value.sessionStarted) startVehicle()
        deletion.retry()
    }
    fun background() {
        active = false; stopVehicle(); uxMonitor.stop()
        cancelRequest()
        mutable.update { it.copy(ux = UxState(), reading = it.reading.copy(status = ReadStatus.STALE, value = null, previousValue = it.reading.value ?: it.reading.previousValue)) }
    }
    private fun startVehicle() {
        if (started || !active) return
        started = true
        val ticket = generation
        repository.start({ reading -> if (generation == ticket) mutable.update { it.copy(reading = reading) } },
            { text -> if (generation == ticket) { event(text); mutable.update { it.copy(vehicleConnection = text) } } })
    }
    private fun stopVehicle() { if (started) { repository.stop(); started = false } }
    fun chooseProfile(profile: Profile) {
        clearSession()
        mutable.update { it.copy(profile = profile, page = Page.LANGUAGE, error = null) }
    }
    fun assistantActionScope(state: UiState) = AssistantBoundaryPolicy.actionScope(state)
    fun chooseLanguage(tag: String, scope: AssistantActionScope = assistantActionScope(mutable.value)) {
        if (content.languages.none { it.tag == tag }) return
        if (!AssistantBoundaryPolicy.canChooseLanguage(mutable.value, scope, active)) { rejectAssistantAction(scope); return }
        if (tag != mutable.value.locale) clearAssistantCooldown()
        cancelRequest()
        assistantRequests.clear()
        mutable.update { AssistantBoundaryPolicy.languageChanged(it, tag).copy(
            page = GuideSelectionPolicy.destination(returnPages.language, it.selectedGuide), externalResource = null, assistantRetry = AssistantRetry.NONE) }
        if (!mutable.value.sessionStarted) {
            mutable.update { it.copy(sessionStarted = true) }; startVehicle()
        }
        loadGuides()
    }
    fun language() { returnPages = returnPages.enteringLanguage(mutable.value.page); go(Page.LANGUAGE) }
    fun go(page: Page) {
        val destination = GuideSelectionPolicy.destination(page, mutable.value.selectedGuide)
        if (mutable.value.sessionStarted && isLong(destination) && restricted()) { mutable.update { it.copy(error = "PARK_REQUIRED") }; return }
        if (destination != mutable.value.page && mutable.value.page in listOf(Page.ASK, Page.TRANSLATE)) {
            cancelRequest()
            assistantRequests.clear()
        }
        if (destination !in listOf(Page.ASK, Page.TRANSLATE, Page.LANGUAGE) ||
            mutable.value.page !in listOf(Page.ASK, Page.TRANSLATE, Page.LANGUAGE)) assistantGuideContext = null
        mutable.update { it.copy(page = destination, error = null) }
        if (destination == Page.GUIDES) loadGuides()
    }
    fun openAssistant() {
        val current = mutable.value
        go(Page.ASK)
        if (mutable.value.page == Page.ASK) {
            returnPages = returnPages.enteringAssistant(current.page)
            assistantGuideContext = AssistantResponsePolicy.guideContext(current.page, current.selectedGuide, current.guideStep)
        }
    }
    fun openTranslation(text: String, kind: String, sourceLocale: String,
        scope: AssistantActionScope = assistantActionScope(mutable.value)) {
        if (!AssistantBoundaryPolicy.canOpenTranslation(mutable.value, scope, active, text, kind, sourceLocale)) {
            rejectAssistantAction(scope); return
        }
        returnPages = returnPages.enteringTranslation(mutable.value.page)
        mutable.update { it.copy(translationDraft = text, translationKind = kind, translationSourceLocale = sourceLocale,
            translation = "", translationOriginal = "", translationTargetLocale = "", translationReview = "", translationMode = "",
            translationProvider = AiProvider.UNKNOWN, translationModel = null) }
        go(Page.TRANSLATE)
    }
    private fun rejectAssistantAction(scope: AssistantActionScope) {
        // An old screen's event must not even replace a new session's error state.
        if (!active || scope != assistantActionScope(mutable.value)) return
        mutable.update { it.copy(error = if (restricted()) "PARK_REQUIRED" else "ASSISTANT_CONTEXT_CHANGED") }
    }
    fun revokeAssistantConsent(scope: AssistantConsentScope) {
        if (!AssistantBoundaryPolicy.canRevoke(mutable.value, scope)) return
        cancelRequest()
        assistantRequests.clear()
    }
    fun back() {
        go(returnPages.back(mutable.value.page))
    }
    fun refresh() { repository.refresh() }
    fun openReadOnlyStatus() {
        mutable.update { it.copy(sessionStarted = true, page = Page.STATUS, error = null) }
        startVehicle()
    }
    fun scenario(name: String) {
        if (!BuildConfig.IS_MOCK) return
        if (name in listOf("RESTRICTED", "PARKED", "UX_UNKNOWN")) {
            mutable.update { it.copy(ux = UxState(known = name != "UX_UNKNOWN", restricted = name != "PARKED")) }
            if (name != "PARKED") cancelRequest()
        } else repository.scenario(name)
    }
    fun clearError() { mutable.update { it.copy(error = null) } }
    fun officialActionScope(state: UiState) = content.officialResources.scope(state)
    fun openGuideSource(scope: OfficialActionScope, guideId: String, sourceId: String) {
        openResource(content.officialResources.guideSource(mutable.value, scope, guideId, sourceId))
    }
    fun openAnswerSource(scope: OfficialActionScope, requestId: String, sourceId: String) {
        openResource(content.officialResources.citation(mutable.value, scope, requestId, sourceId))
    }
    fun openSupport(scope: OfficialActionScope, id: String) {
        openResource(content.officialResources.support(mutable.value, scope, id))
    }
    fun openAssistantResource(scope: OfficialActionScope, requestId: String, kind: String, id: String) {
        val current = mutable.value
        if (current.page != Page.ASK || current.answerRequestId != requestId || (kind to id) !in current.actions) {
            openResource(null); return
        }
        when (kind) {
            "OPEN_MANUAL" -> openAnswerSource(scope, requestId, id)
            "OPEN_SUPPORT" -> openSupport(scope, id)
        }
    }
    private fun openResource(resource: ExternalResource?) {
        if (resource == null || !active) {
            mutable.update { it.copy(error = if (restricted()) "PARK_REQUIRED" else "RESOURCE_UNAVAILABLE", externalResource = null) }
            return
        }
        val result = resourceOpener.open(resource)
        mutable.update { it.copy(externalResource = ExternalResourceNotice(resource, result, resourceOpener.lastRoute), error = null) }
        event("OFFICIAL_RESOURCE $result ${resourceOpener.lastRoute} ${resource.id}")
    }
    fun deepLink(uri: Uri?) {
        if (uri == null) return
        if (uri.scheme != "carcue" || uri.host != "guide" || uri.path !in listOf(null, "", "/")) {
            mutable.update { it.copy(error = "PROFILE_NOT_FOUND", page = Page.PROFILE) }; return
        }
        val id = uri.getQueryParameter("profile_id")
        val profile = content.profiles.singleOrNull { it.id == id }
        if (profile == null) { mutable.update { it.copy(error = "PROFILE_NOT_FOUND", page = Page.PROFILE) }; return }
        if (mutable.value.sessionStarted && restricted()) { mutable.update { it.copy(error = "PARK_REQUIRED") }; return }
        chooseProfile(profile)
    }
    fun openGuide(guide: Guide) {
        val current = mutable.value
        if (!current.sessionStarted) return
        if (restricted()) { mutable.update { it.copy(error = "PARK_REQUIRED") }; return }
        val selected = if (BuildConfig.DEBUG && BuildConfig.IS_MOCK && guide.id == "__layout_preview__") guide
            else current.profile?.let { GuideSelectionPolicy.resolveOpen(guide, it, current.locale, current.guides) }
        if (selected == null) {
            mutable.update { it.copy(error = "GUIDE_UNAVAILABLE") }
            return
        }
        mutable.update { it.copy(selectedGuide = selected, guideStep = 0, externalResource = null) }
        go(Page.GUIDE)
    }
    fun relatedDoorGuide(now: Instant = Instant.now()): Guide? = content.relatedDoorGuide(mutable.value, now)
    fun openRelatedDoorGuide(guideId: String) {
        // The displayed button can outlive its reading. Recheck freshness, UX and metadata at the tap.
        relatedDoorGuide()?.takeIf { it.id == guideId }?.let(::openGuide)
    }
    fun step(delta: Int) { mutable.update { it.copy(guideStep = (it.guideStep + delta).coerceIn(0, (it.selectedGuide?.steps?.size ?: 1).minus(1).coerceAtLeast(0))) } }
    fun refreshGuides() { if (mutable.value.sessionStarted && !restricted()) loadGuides() }
    private fun applyGuides(profile: Profile, locale: String, guides: List<Guide>, connection: String? = null) {
        var removedSelection = false
        mutable.update { current ->
            val selected = GuideSelectionPolicy.reconcile(current.selectedGuide, profile, locale, guides)
            val removed = current.selectedGuide?.publicationVerified == true && selected == null
            removedSelection = removed
            current.copy(guides = guides, selectedGuide = selected,
                guideStep = current.guideStep.coerceAtMost((selected?.steps?.size ?: 1).minus(1).coerceAtLeast(0)),
                page = if (removed && current.page == Page.GUIDE) Page.GUIDES else current.page,
                error = if (removed) "GUIDE_UNAVAILABLE" else current.error,
                guideConnection = connection ?: current.guideConnection,
                guidesLoading = connection == null,
                serverConnection = if (connection == "CONNECTED") connection else current.serverConnection)
        }
        if (removedSelection) {
            assistantGuideContext = null
            returnPages = returnPages.withoutGuide()
        }
    }
    private fun loadGuides() {
        val p = mutable.value.profile ?: return
        val locale = mutable.value.locale
        val ticket = generation
        val request = guideRequests.begin(p, locale)
        mutable.update { it.copy(guides = it.guides.filter { guide -> guide.locale == locale && p.id in guide.profileIds },
            guideConnection = "CONNECTING", guidesLoading = true) }
        viewModelScope.launch {
            val cached = withContext(Dispatchers.IO) { content.cachedGuides(p, locale) }
            if (ticket == generation && locale == mutable.value.locale && guideRequests.isCurrent(request)) applyGuides(p, locale, cached)
            try {
                val data = withContext(Dispatchers.IO) { api.guides(p.id, locale) }
                val guides = withContext(Dispatchers.IO) {
                    guideRequests.commitIfCurrent(request) { content.saveGuides(p, locale, data) }
                } ?: return@launch
                if (ticket == generation && locale == mutable.value.locale && guideRequests.isCurrent(request)) applyGuides(p, locale, guides, "CONNECTED")
            } catch (_: CancellationException) { /* no late response */ }
            catch (e: Exception) { if (ticket == generation && locale == mutable.value.locale && guideRequests.isCurrent(request)) mutable.update { it.copy(
                guideConnection = if (e is ApiFailure) "HTTP_${e.status}" else "UNAVAILABLE", guidesLoading = false,
                serverConnection = if (e is ApiFailure) "HTTP_${e.status}" else "UNAVAILABLE") } }
        }
    }
    fun send(input: String, translate: Boolean = false, retry: Boolean = false, consent: Boolean = false,
        scope: AssistantActionScope = assistantActionScope(mutable.value)) {
        val current = mutable.value
        if (input.isBlank() || input.length > (if (translate) 3000 else 2000) || current.busy || !current.sessionStarted) return
        if (!AssistantBoundaryPolicy.canSend(current, scope, active, translate)) { rejectAssistantAction(scope); return }
        if (!consent) { mutable.update { it.copy(error = "CONSENT_REQUIRED") }; return }
        val waitSeconds = assistantCooldown.remainingSeconds(cooldownScope(current))
        if (waitSeconds > 0) {
            mutable.update { it.copy(error = "HTTP_429", assistantCooldownSeconds = waitSeconds) }
            return
        }
        val profile = current.profile ?: return
        val ticket = generation
        val op = ++operation
        val isDraft = translate && input == current.translationDraft
        val intent = AssistantIntent(input, translate, profile.id, current.locale,
            sourceLocale = if (isDraft) current.translationSourceLocale else "auto",
            contentKind = if (isDraft) current.translationKind else "QUESTION",
            guide = if (translate) {
                if (isDraft && current.translationKind == "GUIDE") current.selectedGuide?.let { AssistantGuideContext(it.id, null) } else null
            } else assistantGuideContext)
        val resend = retry && current.assistantRetry == AssistantRetry.RESEND
        mutable.update { it.copy(busy = true, error = null, answer = if (!translate) "" else it.answer,
            answerStatus = if (!translate) "" else it.answerStatus, answerRequestId = if (!translate) "" else it.answerRequestId, followUpQuestion = if (!translate) "" else it.followUpQuestion,
            assistantRetry = AssistantRetry.NONE, assistantCooldownSeconds = 0,
            citations = if (!translate) emptyList() else it.citations,
            officialCitations = if (!translate) emptyList() else it.officialCitations, externalResource = null,
            actions = if (!translate) emptyList() else it.actions,
            translation = if (translate) "" else it.translation, translationOriginal = if (translate) "" else it.translationOriginal,
            translationTargetLocale = if (translate) "" else it.translationTargetLocale,
            translationReview = if (translate) "" else it.translationReview, translationMode = if (translate) "" else it.translationMode,
            translationProvider = if (translate) AiProvider.UNKNOWN else it.translationProvider,
            translationModel = if (translate) null else it.translationModel) }
        requestJob = viewModelScope.launch {
            try {
                if (remote?.let { AssistantResponsePolicy.sessionExpired(it.expires, Instant.now()) } == true) forgetRemoteSession()
                val session = remote ?: withContext(Dispatchers.IO) {
                    api.start(profile.id, current.locale).also { created -> deletion.registerCreated(created) { ticket == generation && op == operation } }
                }
                if (ticket != generation || op != operation) return@launch
                remote = session
                val snapshot = assistantRequests.prepare(intent, session.id, resend) { id ->
                    val data = JSONObject().put("request_id", id).put("session_id", session.id).put("profile_id", profile.id)
                    if (translate) {
                        data.put("source_locale", intent.sourceLocale).put("target_locale", intent.locale)
                            .put("text", intent.input).put("content_kind", intent.contentKind)
                        intent.guide?.let { data.put("guide_id", it.guideId) }
                    } else {
                        data.put("locale", intent.locale).put("question", intent.input)
                        data.put("guide_context", JSONObject().put("guide_id", intent.guide?.guideId ?: JSONObject.NULL)
                            .put("step_id", intent.guide?.stepId ?: JSONObject.NULL))
                        val r = current.reading.expired(Instant.now(), BuildConfig.STATE_TTL_MS)
                        data.put("vehicle_context", JSONArray().put(JSONObject().put("property_id", r.propertyId).put("area_id", r.areaId)
                            .put("value", r.value ?: JSONObject.NULL).put("read_status", r.status.name)
                            .put("received_at", r.receivedAt?.toString() ?: JSONObject.NULL).put("source", r.source.name)))
                    }
                    data.toString()
                }
                val data = JSONObject(snapshot.payload)
                mutable.update { it.copy(lastAiRequestId = snapshot.requestId) }
                val result = withContext(Dispatchers.IO) { if (translate) api.translate(data, session) else api.ask(data, session) }
                if (ticket != generation || !AssistantBoundaryPolicy.canApplyReply(mutable.value, scope.consent, op, operation, active)) return@launch
                if (!AssistantBoundaryPolicy.replyMatches(snapshot.requestId, intent.locale, result.optString("request_id"),
                        result.optString(if (translate) "target_locale" else "locale"))) {
                    mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", error = "SERVER_RESPONSE_INVALID",
                        assistantRetry = AssistantRetry.NEW_REQUEST, translationOriginal = if (translate) input else it.translationOriginal) }
                    return@launch
                }
                val mode = result.getString("mode")
                val provider = AssistantResponsePolicy.provider(mode, result.optString("ai_provider"))
                val model = AssistantResponsePolicy.model(result.optString("ai_model").takeUnless { it == "null" })
                val status = result.getString("status")
                val outcome = if (translate) AssistantResponsePolicy.translation(status) else AssistantResponsePolicy.ask(status)
                if (translate) mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", translationMode = mode,
                    translationOriginal = result.getString("original_text"), translation = if (status == "TRANSLATED") result.optString("translated_text").takeUnless { t -> t == "null" } ?: "" else "",
                    translationSourceLocale = if (status == "TRANSLATED") result.getString("source_locale") else it.translationSourceLocale,
                    translationTargetLocale = if (status == "TRANSLATED") result.getString("target_locale") else "",
                    translationProvider = provider, translationModel = model, translationReview = result.getString("review_status"),
                    error = outcome.error, assistantRetry = outcome.retry) }
                else {
                    val c = result.getJSONArray("citations")
                    val citations = (0 until c.length()).map { c.getJSONObject(it).let { s -> s.getString("title") to s.getString("url") } }
                    val officialCitations = (0 until c.length()).map { c.getJSONObject(it).let { s ->
                        OfficialCitation(s.getString("source_id"), s.getString("guide_id"), s.getString("profile_id"),
                            s.getString("manual_set_id"), s.getString("source_version"), s.getString("url")) } }
                    val a = result.getJSONArray("actions")
                    val actions = (0 until a.length()).map { a.getJSONObject(it).let { action -> action.getString("kind") to action.optString("target_id").takeUnless { id -> id == "null" } } }
                    mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", answer = if (outcome.error == "SERVER_RESPONSE_INVALID") "" else result.getString("answer"), answerMode = mode,
                        answerLocale = result.getString("locale"), answerStatus = status,
                        answerRequestId = if (outcome.error == "SERVER_RESPONSE_INVALID") "" else snapshot.requestId,
                        followUpQuestion = if (status == "NEED_MORE_INFO") result.optString("follow_up_question").takeUnless { q -> q == "null" } ?: "" else "",
                        answerProvider = provider, answerModel = model, citations = if (outcome.error == "SERVER_RESPONSE_INVALID") emptyList() else citations,
                        officialCitations = if (outcome.error == "SERVER_RESPONSE_INVALID") emptyList() else officialCitations,
                        actions = if (outcome.error == "SERVER_RESPONSE_INVALID") emptyList() else actions,
                        error = outcome.error, assistantRetry = outcome.retry) }
                }
            } catch (_: CancellationException) { /* no late response */ }
            catch (e: Exception) {
                if (ticket == generation && op == operation) {
                    if (e is ApiFailure && AssistantResponsePolicy.expired(e.status, e.code)) forgetRemoteSession()
                    val outcome = if (e is ApiFailure) AssistantResponsePolicy.http(e.status, e.code)
                        else AssistantOutcome("SERVER_UNAVAILABLE", AssistantRetry.RESEND)
                    if (e is ApiFailure && e.status == 429) startAssistantCooldown(e.retryAfterMillis ?: RetryAfterPolicy.FALLBACK_MILLIS)
                    mutable.update { it.copy(busy = false, serverConnection = if (e is ApiFailure && e.status == 429) "HTTP_429" else "UNAVAILABLE", answer = "", answerRequestId = "", followUpQuestion = "", citations = emptyList(), officialCitations = emptyList(), actions = emptyList(),
                        translationOriginal = if (translate) input else it.translationOriginal,
                        error = outcome.error, assistantRetry = outcome.retry) }
                }
            } finally { if (ticket == generation && op == operation) mutable.update { it.copy(busy = false) } }
        }
    }
    private fun forgetRemoteSession() {
        remote = null
        assistantRequests.clear()
        deletion.finishActive()
        mutable.update { it.copy(deletionPending = deletion.pending.value) }
    }
    private fun cooldownScope(state: UiState) = AssistantCooldownScope(state.sessionEpoch, state.profile?.id, state.locale)
    private fun startAssistantCooldown(delayMillis: Long) {
        cooldownJob?.cancel()
        val scope = cooldownScope(mutable.value)
        val remaining = assistantCooldown.start(scope, delayMillis)
        mutable.update { it.copy(assistantCooldownSeconds = remaining) }
        if (remaining == 0L) return
        cooldownJob = viewModelScope.launch {
            while (isActive) {
                delay(1000)
                if (scope != cooldownScope(mutable.value)) return@launch
                val seconds = assistantCooldown.remainingSeconds(scope)
                mutable.update { it.copy(assistantCooldownSeconds = seconds) }
                if (seconds == 0L) break
            }
        }
    }
    private fun clearAssistantCooldown() {
        cooldownJob?.cancel(); cooldownJob = null; assistantCooldown.clear()
        mutable.update { it.copy(assistantCooldownSeconds = 0, error = if (it.error == "HTTP_429") null else it.error) }
    }
    fun cancelRequest() { operation++; requestJob?.cancel(); requestJob = null; mutable.update { it.copy(busy = false) } }
    private fun clearSession() {
        generation++; guideRequests.invalidate(); cancelRequest(); clearAssistantCooldown(); stopVehicle()
        remote = null
        deletion.finishActive()
        assistantRequests.clear(); assistantGuideContext = null
        returnPages = AssistantReturnPages()
        mutable.value = UiState(sessionEpoch = generation, reading = Reading(source = source), ux = mutable.value.ux, internetAvailable = mutable.value.internetAvailable, deletionPending = deletion.pending.value)
    }
    fun endSession() { clearSession() }
    fun retryPendingDeletions() { deletion.retry() }
    override fun onCleared() { clearSession(); uxMonitor.stop(); connectivity.unregisterNetworkCallback(networkCallback); super.onCleared() }
}
