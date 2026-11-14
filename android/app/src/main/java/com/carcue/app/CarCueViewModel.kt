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
import kotlinx.coroutines.flow.update
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.UUID

class CarCueViewModel(application: Application) : AndroidViewModel(application) {
    val content = ContentRepository(application)
    private val source = if (BuildConfig.IS_MOCK) Source.MOCK else Source.PLEOS
    private val repository: VehicleRepository = PlatformVehicleRepository(application)
    private val uxMonitor: UxMonitor = createUxMonitor(application)
    private val api = CarCueApi()
    private val deletion = DeletionQueue(application)
    private val guideRequests = GuideRequestGate()
    private val mutable = MutableStateFlow(UiState(reading = Reading(source = source), deletionPending = deletion.pending()))
    val state = mutable.asStateFlow()
    private var remote: RemoteSession? = null
    @Volatile private var generation = 0
    private var requestJob: Job? = null
    private var requestId: String? = null
    private var retryInput: String? = null
    private var retryIsTranslation = false
    private var languageReturn = Page.HOME
    private var assistantReturn = Page.HOME
    private var active = false
    private var started = false
    @Volatile private var operation = 0
    private val connectivity = application.getSystemService(ConnectivityManager::class.java)
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
            mutable.update { it.copy(internetAvailable = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)) }
        }
        override fun onLost(network: Network) { mutable.update { it.copy(internetAvailable = false) } }
    }

    init {
        deletion.recoverAbandonedSession()
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
        viewModelScope.launch { withContext(Dispatchers.IO) { deletion.retry(api) }; mutable.update { it.copy(deletionPending = deletion.pending()) } }
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
        mutable.update { it.copy(locale = tag, page = languageReturn) }
        if (!mutable.value.sessionStarted) {
            mutable.update { it.copy(sessionStarted = true) }; startVehicle()
        }
        loadGuides()
    }
    fun language() { languageReturn = mutable.value.page; go(Page.LANGUAGE) }
    fun go(page: Page) {
        if (mutable.value.sessionStarted && isLong(page) && restricted()) { mutable.update { it.copy(error = "PARK_REQUIRED") }; return }
        mutable.update { it.copy(page = page, error = null) }
        if (page == Page.GUIDES) loadGuides()
    }
    fun openAssistant() { assistantReturn = mutable.value.page; go(Page.ASK) }
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
    fun step(delta: Int) { mutable.update { it.copy(guideStep = (it.guideStep + delta).coerceIn(0, (it.selectedGuide?.steps?.size ?: 1).minus(1).coerceAtLeast(0))) } }
    private fun loadGuides() {
        val p = mutable.value.profile ?: return
        val locale = mutable.value.locale
        val ticket = generation
        val request = guideRequests.begin(p, locale)
        viewModelScope.launch {
            val cached = withContext(Dispatchers.IO) { content.cachedGuides(p, locale) }
            if (ticket == generation && locale == mutable.value.locale && guideRequests.isCurrent(request)) mutable.update { it.copy(guides = cached) }
            try {
                val data = withContext(Dispatchers.IO) { api.guides(p.id, locale) }
                val guides = withContext(Dispatchers.IO) {
                    guideRequests.commitIfCurrent(request) { content.saveGuides(p, locale, data) }
                } ?: return@launch
                if (ticket == generation && locale == mutable.value.locale && guideRequests.isCurrent(request)) mutable.update { it.copy(guides = guides, serverConnection = "CONNECTED") }
            } catch (_: CancellationException) { /* no late response */ }
            catch (e: Exception) { if (ticket == generation && locale == mutable.value.locale && guideRequests.isCurrent(request)) mutable.update { it.copy(serverConnection = if (e is ApiFailure) "HTTP_${e.status}" else "UNAVAILABLE") } }
        }
    }
    fun send(input: String, translate: Boolean = false, retry: Boolean = false, consent: Boolean = false) {
        val current = mutable.value
        if (input.isBlank() || input.length > (if (translate) 3000 else 2000) || current.busy || restricted() || !current.sessionStarted) return
        if (!consent) { mutable.update { it.copy(error = "CONSENT_REQUIRED") }; return }
        val profile = current.profile ?: return
        val ticket = generation
        val op = ++operation
        if (!retry || retryInput != input || retryIsTranslation != translate) requestId = UUID.randomUUID().toString()
        retryInput = input; retryIsTranslation = translate
        mutable.update { it.copy(busy = true, error = null, answer = if (!translate) "" else it.answer,
            citations = if (!translate) emptyList() else it.citations,
            actions = if (!translate) emptyList() else it.actions,
            translation = if (translate) "" else it.translation, translationOriginal = if (translate) "" else it.translationOriginal) }
        requestJob = viewModelScope.launch {
            try {
                val session = remote ?: withContext(Dispatchers.IO) {
                    api.start(profile.id, current.locale).also { created -> deletion.registerCreated(created) { ticket == generation && op == operation } }
                }
                if (ticket != generation || op != operation) return@launch
                remote = session
                val data = JSONObject().put("request_id", requestId).put("session_id", session.id).put("profile_id", profile.id)
                if (translate) {
                    data.put("source_locale", if (input == current.translationDraft) current.translationSourceLocale else "auto")
                        .put("target_locale", current.locale).put("text", input).put("content_kind", if (input == current.translationDraft) current.translationKind else "QUESTION")
                    if (current.translationKind == "GUIDE" && input == current.translationDraft) data.put("guide_id", current.selectedGuide?.id)
                } else {
                    data.put("locale", current.locale).put("question", input)
                    data.put("guide_context", JSONObject().put("guide_id", current.selectedGuide?.id?.takeUnless { it.startsWith("__") } ?: JSONObject.NULL)
                        .put("step_id", current.selectedGuide?.stepIds?.getOrNull(current.guideStep) ?: JSONObject.NULL))
                    val r = current.reading.expired(Instant.now(), BuildConfig.STATE_TTL_MS)
                    data.put("vehicle_context", JSONArray().put(JSONObject().put("property_id", r.propertyId).put("area_id", r.areaId)
                        .put("value", r.value ?: JSONObject.NULL).put("read_status", r.status.name)
                        .put("received_at", r.receivedAt?.toString() ?: JSONObject.NULL).put("source", r.source.name)))
                }
                val result = withContext(Dispatchers.IO) { if (translate) api.translate(data, session) else api.ask(data, session) }
                if (ticket != generation || op != operation || !mutable.value.sessionStarted || restricted()) return@launch
                if (translate) mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", answerMode = result.getString("mode"),
                    translationOriginal = result.getString("original_text"), translation = result.optString("translated_text").takeUnless { t -> t == "null" } ?: "",
                    translationReview = result.getString("review_status"), error = if (result.getString("status") == "TRANSLATED") null else "TRANSLATION_UNAVAILABLE") }
                else {
                    val c = result.getJSONArray("citations")
                    val citations = (0 until c.length()).map { c.getJSONObject(it).let { s -> s.getString("title") to s.getString("url") } }
                    val a = result.getJSONArray("actions")
                    val actions = (0 until a.length()).map { a.getJSONObject(it).let { action -> action.getString("kind") to action.optString("target_id").takeUnless { id -> id == "null" } } }
                    mutable.update { it.copy(busy = false, serverConnection = "CONNECTED", answer = result.getString("answer"), answerMode = result.getString("mode"), answerLocale = result.getString("locale"), citations = citations, actions = actions) }
                }
            } catch (_: CancellationException) { /* no late response */ }
            catch (e: Exception) {
                if (ticket == generation && op == operation) mutable.update { it.copy(busy = false, serverConnection = "UNAVAILABLE", answer = "", citations = emptyList(),
                    error = if (e is ApiFailure) "HTTP_${e.status}" else "SERVER_UNAVAILABLE") }
            } finally { if (ticket == generation && op == operation) mutable.update { it.copy(busy = false) } }
        }
    }
    fun cancelRequest() { operation++; requestJob?.cancel(); requestJob = null; mutable.update { it.copy(busy = false) } }
    private fun clearSession() {
        generation++; guideRequests.invalidate(); cancelRequest(); stopVehicle()
        remote = null
        deletion.finishActive()
        requestId = null; retryInput = null
        mutable.value = UiState(reading = Reading(source = source), ux = mutable.value.ux, internetAvailable = mutable.value.internetAvailable, deletionPending = deletion.pending())
        viewModelScope.launch { withContext(Dispatchers.IO) { deletion.retry(api) }; mutable.update { it.copy(deletionPending = deletion.pending()) } }
    }
    fun endSession() { clearSession() }
    override fun onCleared() { guideRequests.invalidate(); stopVehicle(); uxMonitor.stop(); connectivity.unregisterNetworkCallback(networkCallback); super.onCleared() }
}
