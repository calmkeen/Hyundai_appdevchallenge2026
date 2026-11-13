package com.carcue.app

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject

private val VisualBlue = Color(0xFF2859E8)
private val VisualInk = Color(0xFF152132)
private val VisualMuted = Color(0xFF526176)

/** Fresh readings alone can determine the model's door pose; unknown is labelled explicitly. */
private fun Reading.visualState(): String = when {
    capability != Capability.SUPPORTED || status != ReadStatus.VALUE -> "unknown"
    value == "OPEN" -> "open"
    value == "CLOSED" -> "closed"
    else -> "unknown"
}

@Composable
fun VehicleSceneCard(reading: Reading, copy: UiCopy, modifier: Modifier = Modifier,
                     interactive: Boolean = true, onScenario: ((String) -> Unit)? = null,
                     profile: Profile? = null) {
    var showModel by remember(profile?.id) { mutableStateOf(true) }
    val photo = !showModel && profile != null
    Surface(modifier, shape = RoundedCornerShape(20.dp), color = Color(0xFFF4F7FC),
        border = BorderStroke(1.dp, Color(0xFFDCE4F1))) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(copy.get(if (photo) "ui_photo_title" else "ui_visual_title"), color = VisualInk, fontWeight = FontWeight.SemiBold, fontSize = 17.sp)
            if (photo) VehicleRealPhoto(profile, copy, height = if (interactive) 180 else 210)
            else VehicleModel3D(reading, copy, Modifier.fillMaxWidth().height(if (interactive) 230.dp else 210.dp), interactive)
            Text(copy.get("ui_visual_" + reading.visualState()), color = if (reading.visualState() == "open") Color(0xFF9A5100) else VisualMuted, fontSize = 14.sp)
            if (!photo) Text(copy.get(if (interactive) "ui_visual_drag" else "ui_visual_shape"), color = VisualMuted, fontSize = 12.sp)
            if (interactive && profile != null) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = { showModel = false }, modifier = Modifier.weight(1f)) { Text(copy.get("ui_photo_tab")) }
                TextButton(onClick = { showModel = true }, modifier = Modifier.weight(1f)) { Text(copy.get("ui_model_tab")) }
            }
            if (onScenario != null && BuildConfig.IS_MOCK) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onScenario("OPEN") }, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(copy.get("ui_visual_demo_open")) }
                OutlinedButton(onClick = { onScenario("CLOSED") }, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(copy.get("ui_visual_demo_closed")) }
            }
        }
    }
}

@Composable
fun VehicleRealPhoto(profile: Profile?, copy: UiCopy, modifier: Modifier = Modifier, height: Int = 190) {
    val context = LocalContext.current
    val entry = remember(profile?.id) {
        val catalog = JSONObject(context.assets.open("illustrations/vehicles.json").bufferedReader().use { it.readText() })
        catalog.optJSONObject(profile?.id.orEmpty())
    }
    if (entry == null) { Text(copy.get("ui_photo_unavailable"), color = VisualMuted); return }
    val image = remember(entry.getString("asset")) {
        val options = BitmapFactory.Options().apply { inSampleSize = 2 }
        context.assets.open(entry.getString("asset")).use { BitmapFactory.decodeStream(it, null, options)!! }.asImageBitmap()
    }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Image(image, contentDescription = copy.get("ui_photo_description").replace("{model}", entry.getString("model")),
            contentScale = if (entry.optString("display") == "crop_bottom") ContentScale.Crop else ContentScale.Fit,
            alignment = androidx.compose.ui.Alignment.BottomCenter,
            modifier = Modifier.fillMaxWidth().height(height.dp).testTag("vehicle_photo"))
        Text(copy.get("ui_photo_notice"), color = VisualMuted, fontSize = 11.sp, lineHeight = 15.sp)
        Text(copy.get("ui_photo_credit").replace("{credit}", entry.getString("author")), color = VisualMuted, fontSize = 10.sp)
    }
}

/** Native OpenGL renders the exported mesh, including depth and hinged door. */
@Composable
fun VehicleModel3D(reading: Reading, copy: UiCopy, modifier: Modifier = Modifier, interactive: Boolean = true) {
    val state = reading.visualState()
    var scene by remember { mutableStateOf<ArticulatedVehicleView?>(null) }
    DisposableEffect(Unit) { onDispose { scene?.releaseScene() } }
    androidx.compose.ui.viewinterop.AndroidView(
        factory = { context -> ArticulatedVehicleView(context).also { scene = it } },
        modifier = modifier.testTag("vehicle_3d").semantics { contentDescription = copy.get("ui_visual_" + state) },
        update = { it.interactive = interactive; it.setDoorState(state) },
    )
}

@Composable
fun GuidePreviewPhoto(copy: UiCopy, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val image = remember { context.assets.open("illustrations/charging-preview.png").use { BitmapFactory.decodeStream(it) }.asImageBitmap() }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Image(image, contentDescription = copy.get("ui_guide_photo"), contentScale = ContentScale.Fit,
            modifier = Modifier.fillMaxWidth().height(190.dp).testTag("guide_preview_image"))
        Text(copy.get("ui_guide_photo_notice"), color = VisualMuted, fontSize = 12.sp)
    }
}
