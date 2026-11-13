package com.carcue.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val Blue = Color(0xFF2859E8)
private val Ink = Color(0xFF152132)
private val Muted = Color(0xFF526176)
private val Pale = Color(0xFFF4F7FC)
private val Line = Color(0xFFDCE4F1)

@Composable
fun CarCueApp(vm: CarCueViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    val ko = vm.content.copy(state.locale)
    fun get(key: String) = ko.get(key)
    val language = vm.content.languages.find { it.tag == state.locale }
    val focus = LocalFocusManager.current
    val restricted = !state.ux.known || state.ux.restricted
    val gated = restricted && state.page in listOf(Page.PROFILE,Page.LANGUAGE,Page.GUIDES,Page.GUIDE,Page.ASK,Page.TRANSLATE)
    LaunchedEffect(restricted) { if (restricted) focus.clearFocus(force = true) }
    BackHandler(enabled = state.sessionStarted && state.page != Page.HOME) { vm.back() }
    MaterialTheme(colorScheme = lightColorScheme(primary = Blue, onPrimary = Color.White, background = Color.White,
        surface = Color.White, onSurface = Ink, secondary = Muted)) {
        CompositionLocalProvider(androidx.compose.ui.platform.LocalLayoutDirection provides if (language?.rtl == true) LayoutDirection.Rtl else LayoutDirection.Ltr) {
            Surface(Modifier.fillMaxSize()) {
                Column(Modifier.safeDrawingPadding()) {
                    Row(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                        TextButton(onClick = { if (state.sessionStarted) vm.go(Page.HOME) }) {
                            Text("CarCue", fontSize = 28.sp, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.weight(1f))
                        if (BuildConfig.IS_MOCK) Text("MOCK · " + get("ui_141e2592b7e9"), color = Color(0xFF8B4B00), fontSize = 15.sp)
                        else Text("PLEOS · " + get("ui_daf3c51bca8c"), color = Muted, fontSize = 14.sp)
                        if (state.sessionStarted) TextButton(onClick = vm::language, enabled = !restricted) { Text(language?.native ?: state.locale) }
                    }
                    HorizontalDivider(color = Line)
                    if (language?.uiStatus == "PLANNED") Notice(get("ui_c92b33651170"))
                    if (restricted) Notice(get("ui_8c21f2cd26d0"))
                    BoxWithConstraints(Modifier.weight(1f)) {
                        val wide = maxWidth >= 800.dp && state.sessionStarted
                        Row(Modifier.fillMaxSize()) {
                            if (wide) Sidebar(state, vm, ko, restricted)
                            Column(Modifier.weight(1f)) {
                                if (!wide && state.sessionStarted) {
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                                        TextButton(onClick = { vm.go(Page.STATUS) }) { Text(get("ui_e10195a1239f")) }
                                        TextButton(onClick = { vm.go(Page.GUIDES) }, enabled = !restricted) { Text(get("ui_e2e1efb2ea75")) }
                                        TextButton(onClick = vm::openAssistant, enabled = !restricted) { Text(get("ui_70e6bde5c047")) }
                                        TextButton(onClick = { vm.go(Page.SETTINGS) }) { Text(get("ui_6b75cf511717")) }
                                    }
                                }
                                key(state.page, state.sessionStarted) {
                                    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(if (wide) 32.dp else 20.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                                        state.error?.let { code ->
                                            Notice(when (code) {
                                                "PROFILE_NOT_FOUND" -> get("ui_e750450bf461")
                                                "PARK_REQUIRED" -> get("ui_5bf44155337d")
                                                "CONSENT_REQUIRED" -> get("ui_f21529f8757a")
                                                "TRANSLATION_UNAVAILABLE" -> get("ui_241983579b6f")
                                                else -> get("ui_91a49aa8ca0f")
                                            }, error = true)
                                        }
                                        if (gated) {
                                            Heading(get("ui_a8af1bdc6df6"), get("ui_50afa257b1c5"))
                                            Action(get("ui_6b02921768d6")) { if (state.sessionStarted) vm.go(Page.STATUS) else vm.openReadOnlyStatus() }
                                        } else when (state.page) {
                                            Page.PROFILE -> ProfileScreen(vm, state, ko)
                                            Page.LANGUAGE -> LanguageScreen(vm, state, ko)
                                            Page.HOME -> HomeScreen(vm, state, ko)
                                            Page.STATUS -> StatusScreen(vm, state, ko)
                                            Page.DETAIL -> DetailScreen(vm, state, ko)
                                            Page.GUIDES -> GuidesScreen(vm, state, ko)
                                            Page.GUIDE -> GuideScreen(vm, state, ko)
                                            Page.ASK, Page.TRANSLATE -> AssistantScreen(vm, state, ko)
                                            Page.SETTINGS -> SettingsScreen(vm, state, ko)
                                        }
                                        Spacer(Modifier.height(12.dp))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable private fun Sidebar(s: UiState, vm: CarCueViewModel, ko: UiCopy, restricted: Boolean) {
    Column(Modifier.width(228.dp).fillMaxHeight().background(Pale).padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(if (s.profile == null) "CarCue" else "Hyundai", color = Muted, fontSize = 15.sp)
        Text(s.profile?.name ?: "—", fontSize = 25.sp, fontWeight = FontWeight.Bold)
        if (s.profile != null) Text("${s.profile.year} · ${s.profile.market}", color = Muted)
        Text(ko.get(if (s.profile == null) "ui_profile_unknown" else "ui_ca3a352a7386"), color = Color(0xFF8B4B00), fontSize = 13.sp)
        HorizontalDivider(Modifier.padding(vertical = 8.dp), color = Line)
        listOf(Page.HOME to ko.get("ui_034999faab05"), Page.STATUS to ko.get("ui_fc73f9507b0a"),
            Page.GUIDES to ko.get("ui_96918379aa24"), Page.ASK to ko.get("ui_7a087ed8150b")).forEach { (page, title) ->
            val selected = s.page == page || page == Page.STATUS && s.page == Page.DETAIL || page == Page.GUIDES && s.page == Page.GUIDE || page == Page.ASK && s.page == Page.TRANSLATE
            if (selected) Button(onClick = { vm.go(page) }, modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp), shape = RoundedCornerShape(10.dp)) { Text(title, fontSize = 17.sp) }
            else TextButton(onClick = { vm.go(page) }, enabled = !restricted || page in listOf(Page.HOME,Page.STATUS), modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp)) { Text(title, fontSize = 17.sp, color = if (restricted && page !in listOf(Page.HOME,Page.STATUS)) Muted else Ink) }
        }
        Spacer(Modifier.weight(1f))
        TextButton(onClick = { vm.go(Page.SETTINGS) }, modifier = Modifier.fillMaxWidth()) { Text(ko.get("ui_8b1858a51ec7")) }
    }
}
@Composable private fun Heading(title: String, subtitle: String) {
    Text(title, fontSize = 30.sp, lineHeight = 40.sp, fontWeight = FontWeight.Bold, color = Ink)
    Text(subtitle, color = Muted, fontSize = 17.sp, lineHeight = 26.sp)
}
@Composable private fun Notice(text: String, error: Boolean = false) {
    Surface(color = if (error) Color(0xFFFFF4EB) else Pale, shape = RoundedCornerShape(10.dp), modifier = Modifier.fillMaxWidth()) {
        Text(text, Modifier.padding(16.dp), fontSize = 15.sp, lineHeight = 23.sp, color = if (error) Color(0xFF884316) else Muted)
    }
}
@Composable private fun Action(title: String, enabled: Boolean = true, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp), shape = RoundedCornerShape(12.dp)) {
        Text(title, fontSize = 18.sp, lineHeight = 25.sp)
    }
}
@Composable private fun Panel(title: String, detail: String, highlight: Boolean = false, onClick: (() -> Unit)? = null) {
    Surface(onClick = { onClick?.invoke() }, enabled = onClick != null, color = if (highlight) Blue else Color.White,
        border = if (highlight) null else BorderStroke(1.dp, Line), shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, color = if (highlight) Color.White else Ink, fontWeight = FontWeight.SemiBold, fontSize = 21.sp, lineHeight = 29.sp)
            Text(detail, color = if (highlight) Color.White else Muted, fontSize = 16.sp, lineHeight = 25.sp)
        }
    }
}
@Composable private fun ProfileScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    Heading(ko.get("ui_8d18a8f56cc2"), ko.get("ui_b491620e8764"))
    Notice(ko.get("ui_6fc3f26a9b34"))
    vm.content.profiles.forEach { p ->
        Panel("${p.name} · ${p.year}", "${p.market} · BEV · ${p.id}\n" + ko.get("ui_cc624e1afe01"), onClick = { vm.chooseProfile(p) })
    }
    if (s.deletionPending) Notice(ko.get("ui_74c30739d02d"))
    Text(ko.get("ui_ce0d787f948e"), color = Muted, fontSize = 14.sp)
}
@Composable private fun LanguageScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    var query by remember { mutableStateOf("") }
    Heading(ko.get("ui_c8c8ce7e9632"), "${s.profile?.name} · ${s.profile?.year} · ${s.profile?.market}")
    OutlinedTextField(query, { query = it.take(100) }, label = { Text(ko.get("ui_d585be7b3815")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
    vm.content.languages.filter { query.isBlank() || (it.native + it.korean + it.tag).contains(query, ignoreCase = true) }.forEach { language ->
        OutlinedButton(onClick = { vm.chooseLanguage(language.tag) }, modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp), shape = RoundedCornerShape(12.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) { Text(language.native, fontSize = 19.sp, color = Ink); Text(language.korean + " · " + language.tag, fontSize = 13.sp, color = Muted) }
                Text(if (language.uiStatus == "PLANNED") ko.get("ui_47626091d586") else ko.get("ui_88234c294ba7"), fontSize = 12.sp)
            }
        }
    }
}
@Composable private fun HomeScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    Heading(ko.get("ui_f5d47b042bda"), ko.get("ui_feca0d91b81e"))
    BoxWithConstraints {
        if (maxWidth >= 760.dp) Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            HomeStatusCard(vm, ko, Modifier.weight(1f))
            VehicleSceneCard(s.reading, ko, Modifier.weight(1f), interactive = false, profile = s.profile)
        } else Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            HomeStatusCard(vm, ko)
            VehicleSceneCard(s.reading, ko, interactive = false, profile = s.profile)
        }
    }
    Panel(ko.get("ui_96918379aa24"), ko.get("ui_b5935d7ba17c"), onClick = { vm.go(Page.GUIDES) })
    Panel(ko.get("ui_7a087ed8150b"), ko.get("ui_1a3926f02365"), onClick = vm::openAssistant)
}
@Composable private fun HomeStatusCard(vm: CarCueViewModel, ko: UiCopy, modifier: Modifier = Modifier) {
    Surface(modifier, color = Blue, shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.fillMaxWidth().padding(28.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(ko.get("ui_f02c2d11a01d"), color = Color.White, fontSize = 27.sp, fontWeight = FontWeight.Bold, lineHeight = 37.sp)
            Text(if (BuildConfig.IS_MOCK) ko.get("ui_f1eeaedd7e3c") else ko.get("ui_939f7daa4e4e"), color = Color.White)
            Button(onClick = { vm.go(Page.STATUS) }, colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Blue), shape = RoundedCornerShape(10.dp), modifier = Modifier.heightIn(min = 60.dp)) { Text(ko.get("ui_516e0278f12b"), fontSize = 18.sp) }
        }
    }
}
private fun Reading.description(ko: UiCopy): String = when {
    capability == Capability.UNSUPPORTED -> ko.get("ui_320e56840e38")
    capability == Capability.CHECK_FAILED -> ko.get("ui_21feab3eaf5d")
    status == ReadStatus.LOADING -> ko.get("ui_777eced9ebf5")
    status == ReadStatus.ERROR -> ko.get("ui_e2e286b9fa93")
    status == ReadStatus.STALE -> ko.get("ui_a02318b2fa61")
    status == ReadStatus.VALUE -> when (value) { "OPEN" -> ko.get("ui_86b92bfd7c71"); "CLOSED" -> ko.get("ui_f70cce500477"); else -> ko.get("ui_5c5529c4ea48").replace("{value}", value.orEmpty()) }
    else -> ko.get("ui_fee8ea990bf9")
}
@Composable private fun StatusScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    Heading(ko.get("ui_fc73f9507b0a"), ko.get("ui_4915df98c8b8"))
    Action(ko.get("ui_3b6510d9d5ee"), s.reading.status != ReadStatus.LOADING) { vm.refresh() }
    val interactive = s.ux.known && !s.ux.restricted
    val demo: ((String) -> Unit)? = if (BuildConfig.IS_MOCK && interactive) vm::scenario else null
    BoxWithConstraints {
        if (maxWidth >= 760.dp) Row(horizontalArrangement = Arrangement.spacedBy(18.dp)) {
            VehicleSceneCard(s.reading, ko, Modifier.weight(1f), interactive, demo, profile = s.profile)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(16.dp)) { DoorReadingPanel(vm, s, ko) }
        } else Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            DoorReadingPanel(vm, s, ko)
            VehicleSceneCard(s.reading, ko, interactive = interactive, onScenario = demo, profile = s.profile)
        }
    }
    Panel(ko.get("ui_c5c585276916"), ko.get("ui_d694ff301ced"))
    Panel(ko.get("ui_1f1301d87291"), ko.get("ui_39e55b90c4c8"))
    Notice(ko.get("ui_a5f57b36a3a7").replace("{internet}", s.internetAvailable?.toString() ?: "UNKNOWN").replace("{server}", s.serverConnection).replace("{vehicle}", s.vehicleConnection))
}
@Composable private fun DoorReadingPanel(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    Panel(ko.get("ui_5f00d4793151"), s.reading.description(ko), highlight = s.reading.status == ReadStatus.VALUE && s.reading.value == "OPEN", onClick = { vm.go(Page.DETAIL) })
    Text("${s.reading.source} · ${s.reading.capability} · ${s.reading.status}", color = Muted, fontSize = 14.sp)
    s.reading.receivedAt?.let { Text((ko.get("ui_cc088cb58015")) + DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneId.systemDefault()).format(it), fontSize = 14.sp, color = Muted) }
    s.reading.previousValue?.let { Notice((ko.get("ui_467deb9ffd72")) + it + ko.get("ui_4a8f8d4b04bf")) }
}
@Composable private fun DoorDiagram(open: Boolean) {
    Canvas(Modifier.fillMaxWidth().height(170.dp).semantics { contentDescription = "Physical front-left door location (ROW_1_LEFT), not necessarily the driver door" }) {
        val w = size.width; val h = size.height; val left = w/2-48; val right = w/2+48
        drawRoundRect(Pale, androidx.compose.ui.geometry.Offset(left, 8f), androidx.compose.ui.geometry.Size(96f, h-16f), androidx.compose.ui.geometry.CornerRadius(22f))
        drawRoundRect(Blue, androidx.compose.ui.geometry.Offset(left, 8f), androidx.compose.ui.geometry.Size(96f, h-16f), androidx.compose.ui.geometry.CornerRadius(22f), style = Stroke(3f))
        drawLine(Blue, androidx.compose.ui.geometry.Offset(left+12, h*.28f), androidx.compose.ui.geometry.Offset(right-12, h*.28f), 3f)
        drawLine(if (open) Color(0xFFAD5C00) else Blue, androidx.compose.ui.geometry.Offset(left, h*.34f), androidx.compose.ui.geometry.Offset(if (open) left-50 else left, h*.60f), 6f)
        drawLine(Blue, androidx.compose.ui.geometry.Offset(right, h*.34f), androidx.compose.ui.geometry.Offset(right, h*.60f), 3f)
    }
}
@Composable private fun DetailScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    Heading(s.reading.description(ko), ko.get("ui_27fb61365bb5"))
    VehicleSceneCard(s.reading, ko, interactive = s.ux.known && !s.ux.restricted, profile = s.profile)
    Notice(ko.get("ui_94ee6190b2e4"))
    Action(ko.get("ui_3b6510d9d5ee"), s.reading.status != ReadStatus.LOADING) { vm.refresh() }
    OutlinedButton(onClick = { vm.go(Page.GUIDES) }, modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp)) { Text(ko.get("ui_1577a2d2afdc")) }
    OutlinedButton(onClick = vm::openAssistant, modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp)) { Text(ko.get("ui_d6b8c2700dd3")) }
    Text(ko.get("ui_fc613175a649"), color = Muted)
}
@Composable private fun GuidesScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    var query by remember { mutableStateOf("") }
    Heading(ko.get("ui_96918379aa24"), "${s.profile?.name} · ${s.profile?.year} · ${s.profile?.market}")
    OutlinedTextField(query, { query = it.take(100) }, label = { Text(ko.get("ui_5f3488318abb")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
    val guides = s.guides.filter { (it.title + it.body).contains(query, true) }
    if (guides.isEmpty()) Notice(ko.get("ui_7af6433d25e9"))
    guides.forEach { guide -> Panel(guide.title, guide.body, onClick = { vm.openGuide(guide) }) }
    if (BuildConfig.IS_MOCK) Surface(onClick = { vm.openGuide(Guide("__layout_preview__", ko.get("ui_817e34c0f4e8"), ko.get("ui_275b15c57746"),
        listOf((ko.get("ui_3e7fa72af50a")) to (ko.get("ui_d1c1fb5dfe7f")),
            (ko.get("ui_6389dba531a5")) to (ko.get("ui_0f89f99fff78")),
            (ko.get("ui_6a9bd682c497")) to (ko.get("ui_41867308eace"))), emptyList(), locale = s.locale)) }, modifier = Modifier.fillMaxWidth().testTag("guide_image_card"),
        shape = RoundedCornerShape(16.dp), border = BorderStroke(1.dp, Line), color = Color.White) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            GuidePreviewPhoto(ko)
            Text(ko.get("ui_5973dc193878"), color = Blue, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
        }
    }
    Action(ko.get("ui_0812f118b535")) { vm.openAssistant() }
}
@Composable private fun GuideScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    val guide = s.selectedGuide ?: return
    val step = guide.steps.getOrNull(s.guideStep)
    Heading(guide.title, guide.body)
    if (guide.id == "__layout_preview__") Notice(ko.get("ui_a94f7c5cbf98"))
    Text("${s.guideStep+1} / ${guide.steps.size.coerceAtLeast(1)}", color = Blue, fontWeight = FontWeight.Bold, fontSize = 22.sp,
        style = LocalTextStyle.current.copy(textDirection = TextDirection.Ltr))
    if (guide.locale != s.locale) Notice(ko.get("ui_original_locale").replace("{locale}", guide.locale))
    if (guide.id == "__layout_preview__") BoxWithConstraints {
        if (maxWidth >= 760.dp) Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Box(Modifier.weight(1f)) { if (s.guideStep == 1) GuidePreviewPhoto(ko) else VehicleModel3D(s.reading, ko, Modifier.fillMaxWidth().height(180.dp), interactive = false) }
            Column(Modifier.weight(1f)) { step?.let { Panel(it.first, it.second) } }
        } else Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (s.guideStep == 1) GuidePreviewPhoto(ko) else VehicleModel3D(s.reading, ko, Modifier.fillMaxWidth().height(180.dp), interactive = false)
            step?.let { Panel(it.first, it.second) }
        }
    } else step?.let { Panel(it.first, it.second) }
    guide.cautions.getOrNull(s.guideStep)?.forEach { Notice(it, error = true) }
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        OutlinedButton(onClick = { vm.step(-1) }, enabled = s.guideStep > 0, modifier = Modifier.weight(1f).heightIn(min = 60.dp)) { Text(ko.get("ui_da7e61c67cc5")) }
        Button(onClick = { vm.step(1) }, enabled = s.guideStep+1 < guide.steps.size, modifier = Modifier.weight(1f).heightIn(min = 60.dp)) { Text(ko.get("ui_aef613c6612d")) }
    }
    Sources(guide.sources, ko)
    if (!guide.id.startsWith("__")) OutlinedButton(onClick = { vm.openTranslation(guide.body, "GUIDE", guide.locale) }) { Text(ko.get("ui_translate_guide")) }
    Action(ko.get("ui_af7d9b9636de")) { vm.openAssistant() }
}
@Composable private fun Sources(sources: List<Pair<String, String>>, ko: UiCopy) {
    val handler = LocalUriHandler.current
    if (sources.isNotEmpty()) Text(ko.get("ui_f483cda99083"), fontWeight = FontWeight.SemiBold, fontSize = 19.sp)
    sources.forEach { (title, url) -> TextButton(onClick = { if (url.startsWith("https://")) handler.openUri(url) }) { Text(title) } }
}
@Composable private fun AssistantScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    var input by remember(s.page, s.translationDraft) { mutableStateOf(if (s.page == Page.TRANSLATE) s.translationDraft else "") }
    var consent by remember { mutableStateOf(false) }
    val translate = s.page == Page.TRANSLATE
    Heading(if (translate) ko.get("ui_21d615f3f8da") else ko.get("ui_029f6d65e9db"),
        ko.get("ui_c59c7d532980"))
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        FilterChip(selected = !translate, onClick = { vm.go(Page.ASK) }, label = { Text(ko.get("ui_81e47212bc91")) })
        FilterChip(selected = translate, onClick = { vm.go(Page.TRANSLATE) }, label = { Text(ko.get("ui_03270bdd0c07")) })
    }
    OutlinedTextField(input, { input = it.take(if (translate) 3000 else 2000) }, label = { Text(if (translate) ko.get("ui_7ff647e2d1c8") else ko.get("ui_252ee2182be5")) }, modifier = Modifier.fillMaxWidth().testTag("question_input"), minLines = 3, enabled = !s.busy)
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(consent, { consent = it }, enabled = !s.busy)
        Text(ko.get("ui_e2c47f0a9a27"), fontSize = 14.sp, lineHeight = 22.sp)
    }
    Action(if (s.busy) ko.get("ui_62d6724cd18d") else if (translate) ko.get("ui_e592e2e100ab") else ko.get("ui_12d7bd98bbd6"), input.isNotBlank() && !s.busy && consent) { vm.send(input, translate, consent = consent) }
    if (s.busy) { LinearProgressIndicator(Modifier.fillMaxWidth()); TextButton(onClick = vm::cancelRequest) { Text(ko.get("ui_25fa53c0d70d")) } }
    if (s.error?.startsWith("SERVER") == true || s.error?.startsWith("HTTP_") == true) OutlinedButton(onClick = { vm.send(input, translate, retry = true, consent = consent) }, enabled = !s.busy && consent) { Text(ko.get("ui_16c72fd12cf2")) }
    if (translate && s.translationOriginal.isNotEmpty()) {
        Panel(ko.get("ui_0201f36241b8"), s.translationOriginal)
        if (s.translation.isNotEmpty()) Panel(ko.get("ui_372ae2e0ffb4"), s.translation)
        Text("${s.answerMode} · ${s.translationReview}", color = Muted)
    } else if (!translate && s.answer.isNotEmpty()) {
        Panel(ko.get("ui_2b2ab898a3e7"), s.answer)
        Text((ko.get("ui_e17400f68f7b")) + s.answerMode + ko.get("ui_203cc8718a2b"), color = Muted, fontSize = 14.sp)
        Sources(s.citations, ko)
        OutlinedButton(onClick = { vm.openTranslation(s.answer, "ANSWER", s.answerLocale) }) { Text(ko.get("ui_translate_answer")) }
        s.actions.forEach { (kind, id) ->
            when (kind) {
                "REFRESH_STATUS" -> if (id == "door.position") TextButton(onClick = vm::refresh) { Text(ko.get("ui_3b6510d9d5ee")) }
                "SELECT_PROFILE" -> TextButton(onClick = { vm.go(Page.PROFILE) }) { Text(ko.get("ui_confirm_profile")) }
                "OPEN_GUIDE" -> s.guides.find { it.id == id }?.let { guide -> TextButton(onClick = { vm.openGuide(guide) }) { Text(ko.get("ui_open_guide")) } }
            }
        }
    }
    TextButton(onClick = vm::back) { Text(ko.get("ui_7812fd4be3f4")) }
}
@Composable private fun SettingsScreen(vm: CarCueViewModel, s: UiState, ko: UiCopy) {
    var confirm by remember { mutableStateOf(false) }
    Heading(ko.get("ui_6b75cf511717"), ko.get("ui_7755a2a560f6"))
    Panel(ko.get("ui_587de113f790"), "${s.profile?.name} · ${s.profile?.year} · ${s.profile?.market}\n${s.locale}")
    OutlinedButton(onClick = { vm.go(Page.PROFILE) }, enabled = s.ux.known && !s.ux.restricted, modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp)) { Text(ko.get("ui_0a651ab9b144")) }
    if (BuildConfig.IS_MOCK) {
        Text(ko.get("ui_d85f3e3f0a01"), fontWeight = FontWeight.Bold)
        listOf("OPEN", "CLOSED", "UNAVAILABLE", "ERROR", "UNSUPPORTED", "CHECK_FAILED", "STALE", "RESTRICTED", "UX_UNKNOWN", "PARKED").chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { row.forEach { scenario -> OutlinedButton(onClick = { vm.scenario(scenario) }, modifier = Modifier.weight(1f).heightIn(min = 56.dp)) { Text(scenario, fontSize = 13.sp) } } }
        }
    }
    Notice(ko.get("ui_b791275db7bd"))
    Action(ko.get("ui_48af33bc151c")) { confirm = true }
    if (s.deletionPending) Text(ko.get("ui_cc3578c46b23"), color = Muted)
    Panel(ko.get("ui_model_credit_title"), "3D: andikapratamaw (2022), Dogan Ulus (2026)\nMPL-2.0 AND CC-BY-4.0\nhttps://github.com/vevalabs/openx-assets\nhttps://sketchfab.com/andikapratamaw\nhttps://www.mozilla.org/MPL/2.0/\nhttps://creativecommons.org/licenses/by/4.0/\n" + ko.get("ui_model_credit_notice"))
    if (s.eventLog.isNotEmpty()) {
        Text(ko.get("ui_2f65004bce0e"), fontWeight = FontWeight.Bold)
        Text(s.eventLog.takeLast(8).joinToString("\n"), fontSize = 12.sp, color = Muted)
    }
    if (confirm) AlertDialog(onDismissRequest = { confirm = false }, title = { Text(ko.get("ui_a934c90be0af")) },
        text = { Text(ko.get("ui_4e1c5ad41153")) },
        confirmButton = { TextButton(onClick = { confirm = false; vm.endSession() }) { Text(ko.get("ui_a827222cef89")) } },
        dismissButton = { TextButton(onClick = { confirm = false }) { Text(ko.get("ui_040aff729eb9")) } })
}
