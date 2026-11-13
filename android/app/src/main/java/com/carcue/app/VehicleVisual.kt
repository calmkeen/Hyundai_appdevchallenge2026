package com.carcue.app

import android.graphics.BitmapFactory
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.*
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
    var showModel by remember(profile?.id) { mutableStateOf(false) }
    val photo = !showModel && profile != null
    Surface(modifier, shape = RoundedCornerShape(20.dp), color = Color(0xFFF4F7FC),
        border = BorderStroke(1.dp, Color(0xFFDCE4F1))) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(copy.get(if (photo) "ui_photo_title" else "ui_visual_title"), color = VisualInk, fontWeight = FontWeight.SemiBold, fontSize = 17.sp)
            if (photo) VehicleRealPhoto(profile, copy, height = if (interactive) 180 else 210)
            else VehicleModel3D(reading, copy, Modifier.fillMaxWidth().height(210.dp), interactive)
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

private data class V3(val x: Float, val y: Float, val z: Float)
private data class Face(val points: List<V3>, val color: Color, val outline: Boolean = false)

/** A repo-owned procedural mesh, projected in perspective by the native Compose Canvas.
 * It is a generic location illustration, never a scan or an exact model of the selected car.
 * The X-negative side is physical vehicle left, independent of sales market or driver seat.
 */
@Composable
fun VehicleModel3D(reading: Reading, copy: UiCopy, modifier: Modifier = Modifier, interactive: Boolean = true) {
    val door = reading.visualState()
    var yaw by remember { mutableFloatStateOf(35f) }
    val nearSide = if (sin(Math.toRadians(yaw.toDouble())) >= 0) -1f else 1f
    val faces = remember(door, nearSide) { vehicleMesh(door, nearSide) }
    val description = copy.get("ui_visual_" + door)
    Canvas(modifier.testTag("vehicle_3d").semantics { contentDescription = description }
        .pointerInput(interactive) {
            if (interactive) detectDragGestures { change, drag ->
                change.consume()
                yaw = (yaw - drag.x * 0.18f) % 360f
            }
        }) {
        val angle = Math.toRadians(yaw.toDouble())
        val co = cos(angle).toFloat(); val si = sin(angle).toFloat()
        val pitch = 0.37f
        fun camera(v: V3): V3 {
            val x = v.x * co - v.z * si
            val z = v.x * si + v.z * co
            val y = v.y - 0.95f
            return V3(x, y * cos(pitch) + z * sin(pitch), z * cos(pitch) - y * sin(pitch))
        }
        val unit = min(size.width / 5.8f, size.height / 2.8f)
        fun project(v: V3): Offset {
            val p = camera(v)
            val scale = unit * 9f / (9f + p.z)
            return Offset(size.width / 2 - p.x * scale, size.height * .48f - p.y * scale)
        }
        drawOval(Color(0x0D152132), Offset(size.width * .17f, size.height * .73f), Size(size.width * .66f, size.height * .15f))
        faces.sortedByDescending { f -> f.points.map { camera(it).z }.average() }.forEach { face ->
            val path = Path()
            face.points.forEachIndexed { index, v ->
                val p = project(v)
                if (index == 0) path.moveTo(p.x, p.y) else path.lineTo(p.x, p.y)
            }
            path.close()
            drawPath(path, face.color)
            if (face.outline) drawPath(path, Color(0x99526176), style = Stroke(0.8.dp.toPx()))
        }
    }
}

private fun vehicleMesh(door: String, nearSide: Float): List<Face> = buildList {
    val silver = Color(0xFFCDD5DF); val light = Color(0xFFEDF2F7)
    val darkSilver = Color(0xFF8E9DAF); val glass = Color(0xFF253B53)
    fun face(color: Color, vararg p: V3, outline: Boolean = false) { add(Face(p.toList(), color, outline)) }
    fun ring(y: Float, width: Float, length: Float) = listOf(
        V3(-width*.79f,y,-length), V3(width*.79f,y,-length), V3(width,y,-length*.82f),
        V3(width,y,length*.84f), V3(width*.82f,y,length), V3(-width*.82f,y,length),
        V3(-width,y,length*.84f), V3(-width,y,-length*.82f))
    val bottom = ring(.45f, 1.02f, 2.23f)
    val belt = ring(1.04f, 1.04f, 2.18f)
    for (i in bottom.indices) {
        val j = (i+1)%8
        face(if (i in 4..6) silver else darkSilver, bottom[i], bottom[j], belt[j], belt[i], outline = true)
    }
    add(Face(belt, light, true))
    val lf=V3(-.94f,1.06f,-1.27f); val rf=V3(.94f,1.06f,-1.27f)
    val lr=V3(-.94f,1.06f,1.48f); val rr=V3(.94f,1.06f,1.48f)
    val ltf=V3(-.72f,1.73f,-.73f); val rtf=V3(.72f,1.73f,-.73f)
    val ltr=V3(-.72f,1.73f,.96f); val rtr=V3(.72f,1.73f,.96f)
    face(glass,lf,rf,rtf,ltf,outline=true)
    face(glass,lr,rr,rtr,ltr,outline=true)
    face(glass,rf,rr,rtr,rtf,outline=true)
    face(glass,lf,lr,ltr,ltf,outline=true)
    face(Color(0xFFDDE5EE),ltf,rtf,rtr,ltr,outline=true)
    for (side in listOf(-1f,1f)) {
        face(darkSilver,V3(side*.947f,1.06f,.10f),V3(side*.947f,1.06f,.23f),V3(side*.725f,1.735f,.23f),V3(side*.725f,1.735f,.10f))
        face(darkSilver,V3(side*.94f,1.06f,-1.27f),V3(side*.94f,1.06f,-1.17f),V3(side*.725f,1.735f,-.64f),V3(side*.725f,1.735f,-.73f))
    }
    // The body occludes the opposite wheel pair. Avoid far-side wheels bleeding
    // through the hood in this lightweight painter's-algorithm illustration.
    for (side in listOf(nearSide)) for (z in listOf(-1.43f,1.43f)) {
        val inner=side*.95f; val outer=side*1.14f
        fun wheel(x:Float, radius:Float, a:Double) = V3(x,.39f+radius*sin(a).toFloat(),z+radius*cos(a).toFloat())
        val count=16
        for (i in 0 until count) {
            val a=i*2*PI/count; val b=(i+1)*2*PI/count
            face(Color(0xFF17202D),wheel(inner,.40f,a),wheel(outer,.40f,a),wheel(outer,.40f,b),wheel(inner,.40f,b))
        }
        add(Face((0 until count).map { wheel(outer,.40f,it*2*PI/count) },Color(0xFF202A38)))
        add(Face((0 until count).map { wheel(outer+side*.006f,.25f,it*2*PI/count) },Color(0xFF92A3B6)))
        for (i in 0 until 5) {
            val a=i*2*PI/5
            face(Color(0xFFDCE5EF),wheel(outer+side*.01f,.06f,a-.3),wheel(outer+side*.01f,.23f,a-.16),wheel(outer+side*.01f,.23f,a+.16))
        }
    }
    // Pixel-shaped lamps are decorative geometry; no lighting state is inferred.
    for (side in listOf(-1f,1f)) for (i in 0..2) {
        val x=side*(.48f+i*.11f)
        face(Color(0xFFE7F5FF),V3(x-.04f,.83f,-2.242f),V3(x+.04f,.83f,-2.242f),V3(x+.04f,.94f,-2.242f),V3(x-.04f,.94f,-2.242f))
    }
    face(Color(0xFF253142),V3(-.64f,.51f,-2.244f),V3(.64f,.51f,-2.244f),V3(.64f,.64f,-2.244f),V3(-.64f,.64f,-2.244f))
    val open = door == "open"
    if (open) face(Color(0xFF243246),V3(-1.055f,.56f,-1.2f),V3(-1.055f,.56f,.12f),V3(-1.055f,1.04f,.12f),V3(-1.055f,1.04f,-1.2f))
    fun swung(p:V3):V3 {
        val a=if(open) 1.05f else 0f
        val dx=p.x+1.05f; val dz=p.z+1.22f
        return V3(-1.05f+dx*cos(a)-dz*sin(a),p.y,-1.22f+dx*sin(a)+dz*cos(a))
    }
    val accent=if(open) Color(0xFFD5A15A) else if(door=="closed") silver else Color(0xFFB7C1CF)
    add(Face(listOf(V3(-1.065f,.58f,-1.22f),V3(-1.065f,.58f,.12f),V3(-1.065f,1.04f,.12f),V3(-1.065f,1.04f,-1.22f)).map(::swung),accent,true))
    if(open) add(Face(listOf(lf,V3(-.94f,1.06f,.12f),V3(-.72f,1.70f,.12f),ltf).map(::swung),glass,true))
    add(Face(listOf(V3(-1.074f,.94f,-.14f),V3(-1.074f,.94f,.01f),V3(-1.074f,.98f,.01f),V3(-1.074f,.98f,-.14f)).map(::swung),VisualInk))
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
