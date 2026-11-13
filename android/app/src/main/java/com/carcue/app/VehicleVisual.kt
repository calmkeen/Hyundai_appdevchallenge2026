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
import android.content.Context
import android.os.SystemClock
import androidx.compose.ui.graphics.ImageBitmap
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

private val VisualBlue = Color(0xFF2859E8)
private val VisualInk = Color(0xFF152132)
private val VisualMuted = Color(0xFF526176)

/** Fresh readings alone can determine the door pose; unknown is labelled explicitly. */
private fun Reading.visualState(): String = when {
    capability != Capability.SUPPORTED || status != ReadStatus.VALUE -> "unknown"
    value == "OPEN" -> "open"
    value == "CLOSED" -> "closed"
    else -> "unknown"
}

/** The user's exact Pleos recording, rendered inside CarCue as image frames.
 * This is a native app visual, not an embedded/overlaid external system panel.
 */
@Composable
fun VehicleSceneCard(reading: Reading, copy: UiCopy, modifier: Modifier = Modifier,
                     interactive: Boolean = true, onScenario: ((String) -> Unit)? = null,
                     profile: Profile? = null) {
    Surface(modifier, shape = RoundedCornerShape(20.dp), color = Color.White,
        border = BorderStroke(1.dp, Color(0xFFDCE4F1))) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(copy.get("ui_pleos_visual_title"), color = VisualInk, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                PleosSeatbeltVisual(copy, Modifier.width(138.dp).height(75.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(copy.get("ui_pleos_belt_title"), color = VisualInk, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                    Text(copy.get("ui_pleos_belt_notice"), color = VisualMuted, fontSize = 11.sp, lineHeight = 15.sp)
                }
            }
            PleosVehicleVisual(reading, copy, Modifier.fillMaxWidth().height(210.dp))
            Text(copy.get("ui_visual_" + reading.visualState()), color = if (reading.visualState() == "open") Color(0xFF9A5100) else VisualMuted, fontSize = 14.sp)
            Text(copy.get("ui_pleos_source"), color = VisualMuted, fontSize = 11.sp)
            if (onScenario != null && BuildConfig.IS_MOCK && interactive) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onScenario("OPEN") }, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(copy.get("ui_visual_demo_open")) }
                OutlinedButton(onClick = { onScenario("CLOSED") }, modifier = Modifier.weight(1f).heightIn(min = 48.dp)) { Text(copy.get("ui_visual_demo_closed")) }
            }
        }
    }
}

private object PleosReferenceCache {
    private val decoded = mutableMapOf<String, ImageBitmap>()
    private var catalog: JSONObject? = null
    private fun manifest(context: Context): JSONObject = catalog ?: JSONObject(
        context.assets.open("illustrations/pleos-reference/manifest.json").bufferedReader().use { it.readText() }
    ).also { catalog = it }
    private fun image(context: Context, path: String): ImageBitmap {
        val hash = manifest(context).getJSONObject("output_sha256").getString(path)
        return decoded.getOrPut(hash) { context.assets.open(path).use { BitmapFactory.decodeStream(it)!! }.asImageBitmap() }
    }
    fun car(context: Context): List<ImageBitmap> {
        val files = manifest(context).getJSONObject("car").getJSONArray("frames")
        return (0 until files.length()).map { image(context, files.getString(it)) }
    }
    fun belt(context: Context): ImageBitmap = image(context, manifest(context).getJSONObject("seatbelt").getString("asset"))
}

@Composable
fun PleosSeatbeltVisual(copy: UiCopy, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val bitmap = remember { PleosReferenceCache.belt(context) }
    Image(bitmap, contentDescription = copy.get("ui_pleos_belt_image"), contentScale = ContentScale.Fit,
        modifier = modifier.testTag("seatbelt_visual"))
}

@Composable
fun PleosVehicleVisual(reading: Reading, copy: UiCopy, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val frames = remember { PleosReferenceCache.car(context) }
    val state = reading.visualState()
    val target = if (state == "open") frames.lastIndex else 0
    var position by remember { mutableFloatStateOf(target.toFloat()) }
    // Pose timing uses elapsed device time. The recorder also pumps Compose
    // frames during each real-time hold so recompositions remain visible.
    LaunchedEffect(target) {
        val from = position
        if (from != target.toFloat()) {
            val start = SystemClock.uptimeMillis()
            var t: Float
            do {
                t = ((SystemClock.uptimeMillis() - start) / 720f).coerceIn(0f, 1f)
                position = from + (target - from) * t*t*(3f-2f*t)
                if (t < 1f) delay(32)
            } while (t < 1f)
        }
        position = target.toFloat()
    }
    Image(frames[position.roundToInt().coerceIn(frames.indices)],
        contentDescription = copy.get("ui_visual_" + state), contentScale = ContentScale.Fit,
        alpha = if (state == "unknown") 0.35f else 1f,
        modifier = modifier.testTag("pleos_vehicle_visual"))
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
