package com.sih2026.nav.ui.components

import androidx.compose.animation.animateColorAsState
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
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih2026.nav.data.model.ClipInfo
import com.sih2026.nav.data.model.NavState
import com.sih2026.nav.domain.engine.ReplayProgress
import com.sih2026.nav.ui.theme.AlertRed
import com.sih2026.nav.ui.theme.CyanAccent
import com.sih2026.nav.ui.theme.EmeraldGreen
import com.sih2026.nav.ui.theme.SurfaceCard
import com.sih2026.nav.ui.theme.SurfaceDark
import com.sih2026.nav.ui.theme.TextMuted
import com.sih2026.nav.ui.theme.TextPrimary
import com.sih2026.nav.ui.theme.TextSecondary
import com.sih2026.nav.ui.theme.WarningAmber
import java.util.Locale

/**
 * Everything on this overlay is measured, not staged: the drift figures are the distance between the two
 * cursors, and the clip's headline numbers come from the offline evaluation that produced the replay.
 */
@Composable
fun TelemetryOverlay(
    clip: ClipInfo?,
    progress: ReplayProgress,
    estimate: NavState,
    truth: NavState,
    playbackSpeed: Float,
    showNoMap: Boolean,
    onTogglePlay: () -> Unit,
    onRestart: () -> Unit,
    onCycleSpeed: () -> Unit,
    onToggleNoMap: () -> Unit,
    onOpenPicker: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier.fillMaxSize().padding(16.dp)) {

        // TOP — which clip is playing, and whether GNSS is up
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
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = clip?.let { "DRIVER ${it.driver} · ${it.role.uppercase(Locale.US)} SET" }
                            ?: "NO CLIP LOADED",
                        fontFamily = FontFamily.Monospace,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = CyanAccent
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = clip?.let {
                            "${it.drive} · ${it.bandLabel} · ${it.turns} turns · 1 km blackout"
                        } ?: "Pick a driver to start",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary,
                        maxLines = 1
                    )
                }
                ModeBadge(inBlackout = progress.inBlackout)
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
                        contentDescription = "Choose driver and clip",
                        tint = Color.Black,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }

        // BOTTOM — the measured numbers and the playback controls
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .clip(RoundedCornerShape(24.dp))
                .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(24.dp)),
            color = SurfaceDark
        ) {
            Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Readout(
                        label = "ROUND 3 CURSOR",
                        value = String.format(Locale.US, "%.0f m", progress.driftM),
                        sub = String.format(Locale.US, "%.1f%% of distance", progress.driftPct),
                        colour = if (progress.driftPct <= 10f) EmeraldGreen else WarningAmber
                    )
                    Readout(
                        label = "ROUND 2 CURSOR",
                        value = String.format(Locale.US, "%.0f m", progress.noMapDriftM),
                        sub = String.format(Locale.US, "%.1f%% of distance", progress.noMapDriftPct),
                        colour = AlertRed
                    )
                    Readout(
                        label = "DISTANCE DRIVEN",
                        value = String.format(Locale.US, "%.0f m", progress.distanceM),
                        sub = String.format(Locale.US, "%.0f s blacked out", progress.elapsedS),
                        colour = TextPrimary
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // progress bar along the clip
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(Color(0xFF334155))
                ) {
                    val done = if (progress.totalFrames > 0)
                        progress.frame.toFloat() / progress.totalFrames else 0f
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(done)
                            .height(4.dp)
                            .clip(RoundedCornerShape(2.dp))
                            .background(CyanAccent)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    ControlButton(
                        icon = if (progress.playing) Icons.Default.Pause else Icons.Default.PlayArrow,
                        label = if (progress.playing) "PAUSE" else "PLAY",
                        highlighted = !progress.playing,
                        onClick = onTogglePlay
                    )
                    ControlButton(icon = Icons.Default.Replay, label = "RESTART", onClick = onRestart)
                    PillButton(
                        text = String.format(Locale.US, "%.0f×", playbackSpeed),
                        onClick = onCycleSpeed
                    )
                    PillButton(
                        text = if (showNoMap) "NO-MAP: ON" else "NO-MAP: OFF",
                        colour = if (showNoMap) AlertRed else TextMuted,
                        onClick = onToggleNoMap
                    )
                    Spacer(modifier = Modifier.weight(1f))
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = String.format(Locale.US, "%.0f km/h", truth.speedKmh),
                            fontFamily = FontFamily.Monospace,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Text(
                            text = "true speed",
                            fontSize = 10.sp,
                            color = TextMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    LegendItem(colour = EmeraldGreen, label = "true position")
                    LegendItem(colour = CyanAccent, label = "round 3 cursor")
                    if (showNoMap) LegendItem(colour = AlertRed, label = "round 2 cursor")
                }
            }
        }
    }
}

@Composable
private fun Readout(label: String, value: String, sub: String, colour: Color) {
    Column {
        Text(
            text = label,
            fontFamily = FontFamily.Monospace,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            color = TextMuted
        )
        Spacer(modifier = Modifier.height(3.dp))
        Text(
            text = value,
            fontFamily = FontFamily.Monospace,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = colour
        )
        Text(text = sub, fontSize = 11.sp, color = TextSecondary)
    }
}

@Composable
private fun ControlButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    highlighted: Boolean = false,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(if (highlighted) CyanAccent else SurfaceCard)
            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(20.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = if (highlighted) Color.Black else TextPrimary,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(5.dp))
            Text(
                text = label,
                fontFamily = FontFamily.Monospace,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = if (highlighted) Color.Black else TextPrimary
            )
        }
    }
}

@Composable
private fun PillButton(text: String, colour: Color = TextPrimary, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(SurfaceCard)
            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(20.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 9.dp)
    ) {
        Text(
            text = text,
            fontFamily = FontFamily.Monospace,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = colour
        )
    }
}

@Composable
fun ModeBadge(inBlackout: Boolean) {
    val (badgeText, badgeColor) = if (inBlackout) "GNSS LOST" to AlertRed else "GNSS OK" to EmeraldGreen
    val animatedColor by animateColorAsState(targetValue = badgeColor, label = "badgeColor")

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(animatedColor.copy(alpha = 0.2f))
            .border(1.dp, animatedColor, RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 5.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(animatedColor)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = badgeText,
                fontFamily = FontFamily.Monospace,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = animatedColor
            )
        }
    }
}

@Composable
fun LegendItem(colour: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .width(16.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(colour)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(text = label, fontSize = 11.sp, color = TextSecondary)
    }
}
