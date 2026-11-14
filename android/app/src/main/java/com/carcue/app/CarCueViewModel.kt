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
    private val deletion = AppDeletionRecovery.get(application)
    private val guideRequests = GuideRequestGate()
    private val mutable = MutableStateFlow(UiState(reading = Reading(source = source), deletionPending = deletion.pending.value))
    val state = mutable.asStateFlow()
    private var remote: RemoteSession? = null
    @Volatile private var generation = 0
    private var requestJob: Job? = null
    private val assistantRequests = AssistantRequests()
    private var assistantGuideContext: AssistantGuideContext? = null
    private var languageReturn = Page.HOME
    private var assistantReturn = Page.HOME
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
        languageReturn = Page.HOME
    }
    fun chooseLanguage(tag: String) {
        if (content.languages.none { it.tag == tag }) return
        cancelRequest()
        assistantRequests.clear()
        mutable.update { it.copy(locale = tag, page = languageReturn, assistantRetry = AssistantRetry.NONE) }
        if (!mutable.value.sessionStarted) {
            mutable.update { it.copy(sessionStarted = true) }; startVehicle()
        }
        loadGuides()
    }
    fun language() { languageReturn = mutable.value.page; go(Page.LANGUAGE) }
    fun go(page: Page) {
        if (mutable.value.sessionStarted && isLong(page) && restricted()) { mutable.update { it.copy(error = "PARK_REQUIRED") }; return }
        if (page !in listOf(Page.ASK, Page.TRANSLATE, Page.LANGUAGE) ||
            mutable.value.page !in listOf(Page.ASK, Page.TRANSLATE, Page.LANGUAGE)) assistantGuideContext = null
        mutable.update { it.copy(page = page, error = null) }
        if (page == Page.GUIDES) loadGuides()
    }
    fun openAssistant() {
        val current = mutable.value
        go(Page.ASK)
        if (mutable.value.page == Page.ASK) {
            assistantReturn = current.page
            assistantGuideContext = AssistantResponsePolicy.guideContext(current.page, current.selectedGuide, current.guideStep)
        }
    }
    fun openTranslation(text: String, kind: String, sourceLocale: String) {
        if (restricted()) return
        assistantReturn = mutable.value.page
        mutable.update { it.copy(translationDraft = text, translationKind = kind, translationSourceLocale = sourceLocale) }
        go(Page.TRANSLATE)
    }
    fun back() {
        val page = mutable.value.page
        go(when (page) { Page.ASK, Page.TRANSLATE -> assistantReturn; Page.GUIDE -> Page.GUIDES; Page.DETAIL -> Page.STATUS; Page.LANGUAGE -> languageReturn; else -> Page.HOME })
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
    fun openGuide(guide: Guide) { mutable.update { it.copy(selectedGuide = guide, guideStep = 0) }; go(Page.GUIDE) }
    fun relatedDoorGuide(now: Instant = Instant.now()): Guide? = content.relatedDoorGuide(mutable.value, now)
    fun openRelatedDoorGuide(guideId: String) {
        // The displayed button can outlive its reading. Recheck freshness, UX and metadata at the tap.
        relatedDoorGuide()?.takeIf { it.id == guideId }?.let(::openGuide)
    }
    fun step(delta: Int) { mutable.update { it.copy(guideStep = (it.guideStep + delta).coerceIn(0, (it.selectedGuide?.steps?.size ?: 1).minus(1).coerceAtLeast(0))) } }
    fun refreshGuides() { if (mutable.value.sessionStarted && !restricted()) loadGuides() }
    private fun applyGuides(profile: Profile, locale: String, guides: List<Guide>, connection: String? = null) {
        mutable.update { current ->
            val selected = GuideSelectionPolicy.reconcile(current.selectedGuide, profile, locale, guides)
            val removed = current.selectedGuide?.publicationVerified == true && selected == null
            current.copy(guides = guides, selectedGuide = selected,
                guideStep = current.guideStep.coerceAtMost((selected?.steps?.size ?: 1).minus(1).coerceAtLeast(0)),
                page = if (removed && current.page == Page.GUIDE) Page.GUIDES else current.page,
                error = if (removed) "GUIDE_UNAVAILABLE" else current.error,
                guideConnection = connection ?: current.guideConnection,
                guidesLoading = connection == null,
                serverConnection = if (connection == "CONNECTED") connection else current.serverConnection)
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
    fun send(input: String, translate: Boolean = false, retry: Boolean = false, consent: Boolean = false) {
        val current = mutable.value
        if (input.isBlank() || input.length > (if (translate) 3000 else 2000) || current.busy || restricted() || !current.sessionStarted) return
        if (!consent) { mutable.update { it.copy(error = "CONSENT_REQUIRED") }; return }
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
            answerStatus = if (!translate) "" else it.answerStatus, followUpQuestion = if (!translate) "" else it.followUpQuestion,
            assistantRetry = AssistantRetry.NONE,
            citations = if (!translate) emptyList() else it.citations,
            actions = if (!translate) emptyList() else it.actions,
            translation = if (translate) "" else it.translation, translationOriginal = if (translate) "" else it.translationOriginal) }
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
                if (ticket != generation || op != operation || !mutable.value.sessionStarted || restricted()) return@launch
                check(result.getString("request_id") == snapshot.requestId) { "Response request mismatch" }
                val mode = result.getString("mode")
                val provider = AssistantResponsePolicy.provider(mode, result.optString("ai_provider"))
                val model = AssistantResponsePolicy.model(result.optString("ai_model").takeUnless { it == "null" })
                val status = result.getString("status")
                val outcome = if (translate) AssistantResponsePolicy.translation(status) else AssistantResponsePolicy.ask(status)
                if (translate) mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", translationMode = mode,
                    translationOriginal = result.getString("original_text"), translation = if (status == "TRANSLATED") result.optString("translated_text").takeUnless { t -> t == "null" } ?: "" else "",
                    translationSourceLocale = if (status == "TRANSLATED") result.getString("source_locale") else it.translationSourceLocale,
                    translationProvider = provider, translationModel = model, translationReview = result.getString("review_status"),
                    error = outcome.error, assistantRetry = outcome.retry) }
                else {
                    val c = result.getJSONArray("citations")
                    val citations = (0 until c.length()).map { c.getJSONObject(it).let { s -> s.getString("title") to s.getString("url") } }
                    val a = result.getJSONArray("actions")
                    val actions = (0 until a.length()).map { a.getJSONObject(it).let { action -> action.getString("kind") to action.optString("target_id").takeUnless { id -> id == "null" } } }
                    mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", answer = if (outcome.error == "SERVER_RESPONSE_INVALID") "" else result.getString("answer"), answerMode = mode,
                        answerLocale = result.getString("locale"), answerStatus = status,
                        followUpQuestion = if (status == "NEED_MORE_INFO") result.optString("follow_up_question").takeUnless { q -> q == "null" } ?: "" else "",
                        answerProvider = provider, answerModel = model, citations = if (outcome.error == "SERVER_RESPONSE_INVALID") emptyList() else citations,
                        actions = if (outcome.error == "SERVER_RESPONSE_INVALID") emptyList() else actions,
                        error = outcome.error, assistantRetry = outcome.retry) }
                }
            } catch (_: CancellationException) { /* no late response */ }
            catch (e: Exception) {
                if (ticket == generation && op == operation) {
                    if (e is ApiFailure && AssistantResponsePolicy.expired(e.status, e.code)) forgetRemoteSession()
                    val outcome = if (e is ApiFailure) AssistantResponsePolicy.http(e.status, e.code)
                        else AssistantOutcome("SERVER_UNAVAILABLE", AssistantRetry.RESEND)
                    mutable.update { it.copy(busy = false, serverConnection = "UNAVAILABLE", answer = "", followUpQuestion = "", citations = emptyList(), actions = emptyList(),
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
    fun cancelRequest() { operation++; requestJob?.cancel(); requestJob = null; mutable.update { it.copy(busy = false) } }
    private fun clearSession() {
        generation++; guideRequests.invalidate(); cancelRequest(); stopVehicle()
        remote = null
        deletion.finishActive()
        assistantRequests.clear(); assistantGuideContext = null
        mutable.value = UiState(reading = Reading(source = source), ux = mutable.value.ux, internetAvailable = mutable.value.internetAvailable, deletionPending = deletion.pending.value)
    }
    fun endSession() { clearSession() }
    fun retryPendingDeletions() { deletion.retry() }
    override fun onCleared() { clearSession(); uxMonitor.stop(); connectivity.unregisterNetworkCallback(networkCallback); super.onCleared() }
}
