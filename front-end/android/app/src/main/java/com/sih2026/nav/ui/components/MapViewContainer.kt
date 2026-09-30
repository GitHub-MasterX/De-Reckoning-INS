package com.sih2026.nav.ui.components

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.drawable.BitmapDrawable
import android.view.MotionEvent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CompassCalibration
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Navigation
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.sih2026.nav.data.model.NavState
import com.sih2026.nav.ui.theme.CyanAccent
import com.sih2026.nav.ui.theme.SurfaceCard
import com.sih2026.nav.ui.theme.TextPrimary
import com.sih2026.nav.ui.utils.HeadingInterpolator
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Overlay
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline

/**
 * The map, with both cursors on it.
 *
 *   truth      where the car actually was, from its own GNSS — the answer key
 *   estimate   where the round-2 engine thought it was, from phone sensors and the road network
 *   no map     the same engine without the road network, for contrast
 *
 * The camera holds both cursors in view, because the whole point is watching them separate.
 */
@Composable
fun MapViewContainer(
    estimate: NavState,
    truth: NavState,
    inBlackout: Boolean,
    truePath: List<GeoPoint>,
    estimatePath: List<GeoPoint>,
    noMapPath: List<GeoPoint>,
    showNoMap: Boolean,
    modifier: Modifier = Modifier,
    full: NavState? = null,                        // live mode: the 248 Hz engine's estimate
    fullPath: List<GeoPoint> = emptyList()
) {
    val context = LocalContext.current
    var isAutoCenter by remember { mutableStateOf(true) }
    var isHeadingUp by remember { mutableStateOf(false) }   // north-up by default: easier to compare two tracks
    var smoothMapOrientation by remember { mutableFloatStateOf(0f) }

    LaunchedEffect(Unit) {
        Configuration.getInstance().userAgentValue = context.packageName
    }

    val mapView = remember {
        MapView(context).apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            controller.setZoom(17.5)
            controller.setCenter(GeoPoint(estimate.lat, estimate.lon))
        }
    }

    val touchOverlay = remember {
        object : Overlay() {
            override fun onTouchEvent(event: MotionEvent, mapView: MapView): Boolean {
                if (event.action == MotionEvent.ACTION_DOWN || event.action == MotionEvent.ACTION_MOVE) {
                    isAutoCenter = false
                }
                return false
            }
        }
    }

    val truthMarker = remember {
        Marker(mapView).apply {
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
            title = "True position (vehicle GNSS)"
            icon = truthPuck(context)
        }
    }

    val estimateMarker = remember {
        Marker(mapView).apply {
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
            title = "Estimated position (dead reckoning + map)"
            icon = estimateArrow(context)
        }
    }

    val fullMarker = remember {
        Marker(mapView).apply {
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
            title = "248 Hz engine (accelerometer speed + map)"
            icon = estimateArrow(context, "#FFA855F7")
        }
    }

    // A circle on the estimate whose radius is the measured error: it passes through the true position.
    val errorCircle = remember {
        Polygon(mapView).apply {
            fillPaint.color = Color.parseColor("#22F59E0B")
            outlinePaint.color = Color.parseColor("#88F59E0B")
            outlinePaint.strokeWidth = 3f
        }
    }

    val truePolyline = remember { trail("#FF10B981", 13f) }
    val estimatePolyline = remember { trail("#FF06B6D4", 11f) }
    val fullPolyline = remember { trail("#FFA855F7", 9f) }
    val noMapPolyline = remember {
        trail("#FFEF4444", 7f).apply {
            outlinePaint.pathEffect = android.graphics.DashPathEffect(floatArrayOf(14f, 12f), 0f)
        }
    }

    LaunchedEffect(mapView) {
        mapView.overlays.add(touchOverlay)
        mapView.overlays.add(noMapPolyline)
        mapView.overlays.add(truePolyline)
        mapView.overlays.add(estimatePolyline)
        mapView.overlays.add(fullPolyline)
        mapView.overlays.add(errorCircle)
        mapView.overlays.add(truthMarker)
        mapView.overlays.add(estimateMarker)
        mapView.overlays.add(fullMarker)
    }

    LaunchedEffect(truePath, estimatePath, noMapPath, showNoMap, fullPath) {
        truePolyline.setPoints(truePath)
        estimatePolyline.setPoints(estimatePath)
        fullPolyline.setPoints(fullPath)
        noMapPolyline.setPoints(if (showNoMap) noMapPath else emptyList())
        mapView.invalidate()
    }

    LaunchedEffect(estimate, truth, inBlackout, isAutoCenter, isHeadingUp, full) {
        val estimateGeo = GeoPoint(estimate.lat, estimate.lon)
        val truthGeo = GeoPoint(truth.lat, truth.lon)
        estimateMarker.position = estimateGeo
        truthMarker.position = truthGeo
        truthMarker.rotation = 0f
        val showFull = full != null && inBlackout && !full.lat.isNaN()
        fullMarker.setVisible(showFull)
        if (showFull) {
            fullMarker.position = GeoPoint(full!!.lat, full.lon)
            val orientation = if (isHeadingUp) smoothMapOrientation else 0f
            fullMarker.rotation = (full.headingDeg + orientation + 360f) % 360f
        }

        if (isHeadingUp) {
            val target = (-estimate.headingDeg + 360f) % 360f
            smoothMapOrientation = HeadingInterpolator.lerpAngleShortestPath(smoothMapOrientation, target, 0.08f)
            mapView.mapOrientation = smoothMapOrientation
            estimateMarker.rotation = (estimate.headingDeg + smoothMapOrientation + 360f) % 360f
        } else {
            smoothMapOrientation = 0f
            mapView.mapOrientation = 0f
            estimateMarker.rotation = estimate.headingDeg
        }

        val gap = maxOf(estimateGeo.distanceToAsDouble(truthGeo),
            if (showFull) GeoPoint(full!!.lat, full.lon).distanceToAsDouble(truthGeo) else 0.0)
        errorCircle.points =
            if (inBlackout && gap > 3.0) Polygon.pointsAsCircle(estimateGeo, gap) else emptyList()

        if (isAutoCenter) {
            // keep both cursors on screen: centre between them, zoom out as they separate
            val mid = GeoPoint((estimate.lat + truth.lat) / 2, (estimate.lon + truth.lon) / 2)
            mapView.controller.setCenter(if (inBlackout) mid else estimateGeo)
            mapView.controller.setZoom(
                when {
                    !inBlackout || gap < 80 -> 17.5
                    gap < 250 -> 16.5
                    gap < 600 -> 15.5
                    gap < 1200 -> 14.5
                    else -> 13.5
                }
            )
        }
        mapView.invalidate()
    }

    DisposableEffect(Unit) {
        onDispose { mapView.onDetach() }
    }

    Box(modifier = modifier) {
        AndroidView(factory = { mapView }, modifier = Modifier.matchParentSize())

        // On the right edge, halfway down: the top bar and the bottom panel both cover the corners.
        Box(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .padding(end = 12.dp)
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                horizontalAlignment = Alignment.End
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(24.dp))
                        .background(SurfaceCard)
                        .border(1.dp, androidx.compose.ui.graphics.Color(0x33FFFFFF), RoundedCornerShape(24.dp))
                        .clickable {
                            isHeadingUp = !isHeadingUp
                            if (!isHeadingUp) mapView.mapOrientation = 0f
                        }
                        .padding(horizontal = 14.dp, vertical = 10.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = if (isHeadingUp) Icons.Default.Navigation else Icons.Default.CompassCalibration,
                            contentDescription = "Map orientation",
                            tint = CyanAccent,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isHeadingUp) "HEADING UP" else "NORTH UP",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }
                }

                // Centre the cursors. Round, larger than the map's other control, and cyan once the map has
                // been dragged away from them, because getting back should never be a hunt.
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(if (isAutoCenter) SurfaceCard else CyanAccent)
                        .border(1.dp, androidx.compose.ui.graphics.Color(0x33FFFFFF), CircleShape)
                        .clickable {
                            isAutoCenter = true
                            // centre at once: during a paused replay nothing else would move the camera
                            val here = GeoPoint(estimate.lat, estimate.lon)
                            val there = GeoPoint(truth.lat, truth.lon)
                            val apart = here.distanceToAsDouble(there)
                            mapView.controller.animateTo(
                                if (inBlackout) GeoPoint((estimate.lat + truth.lat) / 2, (estimate.lon + truth.lon) / 2)
                                else here
                            )
                            mapView.controller.setZoom(
                                when {
                                    !inBlackout || apart < 80 -> 17.5
                                    apart < 250 -> 16.5
                                    apart < 600 -> 15.5
                                    apart < 1200 -> 14.5
                                    else -> 13.5
                                }
                            )
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.MyLocation,
                        contentDescription = "Centre on the cursors",
                        tint = if (isAutoCenter) CyanAccent else androidx.compose.ui.graphics.Color.Black,
                        modifier = Modifier.size(28.dp)
                    )
                }
            }
        }
    }
}

private fun trail(colour: String, width: Float) = Polyline().apply {
    outlinePaint.color = Color.parseColor(colour)
    outlinePaint.strokeWidth = width
    outlinePaint.strokeCap = Paint.Cap.ROUND
    outlinePaint.strokeJoin = Paint.Join.ROUND
}

/** The truth: a plain green disc, deliberately unlike a navigation arrow. */
private fun truthPuck(context: android.content.Context): BitmapDrawable {
    val size = 96
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val c = size / 2f
    canvas.drawCircle(c, c, 30f, Paint().apply {
        color = Color.parseColor("#3310B981"); isAntiAlias = true
    })
    canvas.drawCircle(c, c, 18f, Paint().apply {
        color = Color.parseColor("#FF10B981"); isAntiAlias = true
    })
    canvas.drawCircle(c, c, 18f, Paint().apply {
        color = Color.WHITE; style = Paint.Style.STROKE; strokeWidth = 5f; isAntiAlias = true
    })
    return BitmapDrawable(context.resources, bitmap)
}

/** The estimate: the arrow the driver would actually see on the phone. */
private fun estimateArrow(context: android.content.Context, colour: String = "#FF06B6D4"): BitmapDrawable {
    val size = 150
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val cx = size / 2f
    val cy = size / 2f

    canvas.drawCircle(cx, cy, 30f, Paint().apply {
        color = Color.parseColor("#3306B6D4"); isAntiAlias = true
    })
    canvas.drawCircle(cx, cy, 19f, Paint().apply {
        color = Color.WHITE; isAntiAlias = true
    })
    val arrow = Path().apply {
        moveTo(cx, cy - 26f)
        lineTo(cx + 18f, cy + 18f)
        lineTo(cx, cy + 9f)
        lineTo(cx - 18f, cy + 18f)
        close()
    }
    canvas.drawPath(arrow, Paint().apply {
        color = Color.parseColor(colour); isAntiAlias = true
    })
    canvas.drawPath(arrow, Paint().apply {
        color = Color.WHITE; style = Paint.Style.STROKE; strokeWidth = 4f; isAntiAlias = true
    })
    return BitmapDrawable(context.resources, bitmap)
}

fun cardinal(headingDeg: Float): String {
    val directions = arrayOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    val normalized = (headingDeg % 360f + 360f) % 360f
    return directions[(((normalized + 22.5f) / 45f).toInt()) % 8]
}
