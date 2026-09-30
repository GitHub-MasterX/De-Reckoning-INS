package com.sih2026.nav.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.GpsFixed
import androidx.compose.material.icons.filled.GpsOff
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih2026.nav.domain.engine.LiveStatus
import com.sih2026.nav.ui.theme.AlertRed
import com.sih2026.nav.ui.theme.CyanAccent
import com.sih2026.nav.ui.theme.EmeraldGreen
import com.sih2026.nav.ui.theme.FullPurple
import com.sih2026.nav.ui.theme.SurfaceCard
import com.sih2026.nav.ui.theme.SurfaceDark
import com.sih2026.nav.ui.theme.TextMuted
import com.sih2026.nav.ui.theme.TextPrimary
import com.sih2026.nav.ui.theme.TextSecondary
import com.sih2026.nav.ui.theme.WarningAmber
import java.util.Locale

/**
 * The live screen. Everything here is measured on this phone: the drift is the distance between the engine's
 * estimate and the GPS fix it was not allowed to use, as a share of the distance GPS says was driven.
 */
@Composable
fun LiveTelemetryOverlay(
    status: LiveStatus,
    showNoMap: Boolean,
    onToggleBlackout: () -> Unit,
    onToggleNoMap: () -> Unit,
    onOpenPicker: () -> Unit,
    onRetryGps: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier.fillMaxSize().padding(16.dp)) {

        // TOP — live, which road network, GPS state
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.TopCenter)
                .clip(RoundedCornerShape(20.dp))
                .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(20.dp)),
            color = SurfaceDark
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "LIVE · THIS PHONE",
                        fontFamily = FontFamily.Monospace,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = CyanAccent
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = status.network,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = if (status.networkLoaded) TextPrimary else TextSecondary,
                        maxLines = 2
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                GnssBadge(status)
                Spacer(modifier = Modifier.width(8.dp))
                Box(
                    modifier = Modifier
                        .clip(CircleShape)
                        .background(CyanAccent)
                        .clickable(onClick = onOpenPicker)
                        .padding(10.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Tune,
                        contentDescription = "Engine and dataset",
                        tint = Color.Black,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }

        // BOTTOM — measured drift, engine state, the blackout switch
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .clip(RoundedCornerShape(24.dp))
                .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(24.dp)),
            color = SurfaceDark
        ) {
            Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                val score = status.score ?: status.lastScore
                val live = status.score != null
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    LiveReadout(
                        label = if (live || score == null) "ROUND 2 · 10 Hz" else "LAST · ROUND 2",
                        value = score?.let { String.format(Locale.US, "%.0f m", it.driftM) } ?: "—",
                        sub = score?.let { String.format(Locale.US, "%.1f%% · no map %.0f m", it.driftPct, it.noMapDriftM) }
                            ?: "no blackout yet",
                        colour = when {
                            score == null -> TextMuted
                            score.driftPct <= 10.0 -> CyanAccent
                            else -> WarningAmber
                        }
                    )
                    LiveReadout(
                        label = if (live || score == null) "248 Hz ENGINE" else "LAST · 248 Hz",
                        value = score?.let { String.format(Locale.US, "%.0f m", it.fullDriftM) } ?: "—",
                        sub = score?.let { String.format(Locale.US, "%.1f%% · no map %.0f m", it.fullDriftPct, it.fullNoMapDriftM) } ?: "",
                        colour = when {
                            score == null -> TextMuted
                            score.fullDriftPct <= 10.0 -> FullPurple
                            else -> WarningAmber
                        }
                    )
                    LiveReadout(
                        label = "DISTANCE (GPS)",
                        value = score?.let { String.format(Locale.US, "%.0f m", it.trueDistanceM) } ?: "—",
                        sub = score?.let { String.format(Locale.US, "%.0f s blacked out", it.elapsedS) } ?: "",
                        colour = TextPrimary
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Chip(
                        text = if (status.stationary) "STOPPED" else "MOVING",
                        colour = if (status.stationary) WarningAmber else EmeraldGreen
                    )
                    Chip(
                        text = String.format(Locale.US, "IMU %.0f/%.0f Hz", status.accHz, status.gyrHz),
                        colour = if (status.gyrHz >= 50f) TextPrimary else WarningAmber
                    )
                    Chip(
                        text = String.format(Locale.US, "GPS %.0f km/h", status.gpsSpeedKmh),
                        colour = TextPrimary
                    )
                    if (status.inBlackout && !status.fullSpeedKmh.isNaN()) {
                        Chip(text = String.format(Locale.US, "248Hz %.0f km/h", status.fullSpeedKmh), colour = FullPurple)
                    }
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = score?.let {
                        String.format(Locale.US, "gyro ×%.2f (%s) · %s · %d speed readings from turns",
                            it.fullCalibration?.scale ?: it.calibration.scale, it.fullCalibration?.method ?: it.calibration.method,
                            if (it.networkUsed == null) "no road network" else if (it.seeded) "on ${it.networkUsed}" else "no road at the fix",
                            it.turnReadings)
                    } ?: status.calibration,
                    fontSize = 11.sp,
                    color = if (status.calibrationFitted || live) TextSecondary else WarningAmber
                )
                if (!live) {
                    Text(
                        text = status.mount,
                        fontSize = 11.sp,
                        color = if (status.mountFitted) TextSecondary else WarningAmber
                    )
                }
                status.message?.let {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(text = it, fontSize = 11.sp, color = AlertRed)
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(20.dp))
                            .background(if (status.inBlackout) AlertRed else WarningAmber)
                            .clickable(enabled = status.hasFix || status.inBlackout, onClick = onToggleBlackout)
                            .padding(vertical = 12.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (status.inBlackout) Icons.Default.GpsFixed else Icons.Default.GpsOff,
                                contentDescription = null,
                                tint = Color.Black,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = when {
                                    status.inBlackout -> "END BLACKOUT"
                                    status.hasFix -> "START BLACKOUT"
                                    else -> "WAITING FOR GPS"
                                },
                                fontFamily = FontFamily.Monospace,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                        }
                    }
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(20.dp))
                            .background(SurfaceCard)
                            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(20.dp))
                            .clickable(onClick = onToggleNoMap)
                            .padding(horizontal = 12.dp, vertical = 12.dp)
                    ) {
                        Text(
                            text = if (showNoMap) "NO-MAP: ON" else "NO-MAP: OFF",
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (showNoMap) AlertRed else TextMuted
                        )
                    }
                }

                if (!status.gpsAllowed) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "TAP TO ALLOW LOCATION AND RETRY GPS",
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = WarningAmber,
                        modifier = Modifier.clickable(onClick = onRetryGps)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceAround) {
                    LegendItem(colour = EmeraldGreen, label = "GPS")
                    LegendItem(colour = CyanAccent, label = "round 2")
                    LegendItem(colour = FullPurple, label = "248 Hz")
                    if (showNoMap) LegendItem(colour = AlertRed, label = "no map")
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = String.format(Locale.US, "● REC %s · %.1f MB", status.recording, status.recordingBytes / 1e6),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 10.sp,
                    color = TextMuted
                )
            }
        }
    }
}

@Composable
private fun GnssBadge(status: LiveStatus) {
    val (text, colour) = when {
        status.inBlackout -> "GNSS HIDDEN" to AlertRed
        status.hasFix -> String.format(Locale.US, "GNSS ±%.0f m", status.fixAccuracyM) to EmeraldGreen
        else -> "ACQUIRING" to WarningAmber
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(colour.copy(alpha = 0.2f))
            .border(1.dp, colour, RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 5.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(colour))
            Spacer(modifier = Modifier.width(6.dp))
            Text(text = text, fontFamily = FontFamily.Monospace, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = colour)
        }
    }
}

@Composable
private fun LiveReadout(label: String, value: String, sub: String, colour: Color) {
    Column {
        Text(text = label, fontFamily = FontFamily.Monospace, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = TextMuted)
        Spacer(modifier = Modifier.height(3.dp))
        Text(text = value, fontFamily = FontFamily.Monospace, fontSize = 22.sp, fontWeight = FontWeight.Bold, color = colour)
        Text(text = sub, fontSize = 11.sp, color = TextSecondary)
    }
}

@Composable
private fun Chip(text: String, colour: Color) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(SurfaceCard)
            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(10.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(text = text, fontFamily = FontFamily.Monospace, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = colour)
    }
}
