package com.sih2026.nav.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih2026.nav.data.model.ClipInfo
import com.sih2026.nav.data.model.EngineMode
import com.sih2026.nav.ui.theme.AlertRed
import com.sih2026.nav.ui.theme.CyanAccent
import com.sih2026.nav.ui.theme.EmeraldGreen
import com.sih2026.nav.ui.theme.SurfaceCard
import com.sih2026.nav.ui.theme.SurfaceDark
import com.sih2026.nav.ui.theme.TextMuted
import com.sih2026.nav.ui.theme.TextPrimary
import com.sih2026.nav.ui.theme.WarningAmber
import com.sih2026.nav.ui.theme.TextSecondary
import java.util.Locale

/**
 * Pick a driver, then one of that driver's recorded blackouts.
 *
 * The "tuning" label matters: the filter's settings were tuned on drivers A and B, so only D and E are
 * evidence of how it behaves on driving it has never seen (round2/DECISIONS.md).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClipPickerSheet(
    engineMode: EngineMode,
    drivers: List<String>,
    clipsByDriver: Map<String, List<ClipInfo>>,
    selectedClipId: String?,
    liveNetworkDir: String,
    liveDriveDir: String,
    onSetEngineMode: (EngineMode) -> Unit,
    onSelect: (ClipInfo) -> Unit,
    onDismiss: () -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val initial = drivers.firstOrNull { d -> clipsByDriver[d]?.any { it.id == selectedClipId } == true }
        ?: drivers.firstOrNull()
    var driver by remember { mutableStateOf(initial) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = SurfaceDark,
        tonalElevation = 16.dp
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp)) {

            Text(
                text = "ENGINE & DATASET CONFIGURATION",
                fontFamily = FontFamily.Monospace,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = CyanAccent
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Replay real IO-VNBD blackouts scored offline, or run the same round-2 engine live on this " +
                    "phone's own sensors.",
                fontSize = 12.sp,
                color = TextSecondary
            )

            Spacer(modifier = Modifier.height(14.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                EngineMode.values().forEach { mode ->
                    EngineModeTab(
                        mode = mode,
                        selected = mode == engineMode,
                        onClick = { onSetEngineMode(mode) },
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // no early return here: an early return inside a composable lambda corrupts Compose's slot table
            if (engineMode == EngineMode.LIVE) {
                LiveInfo(liveNetworkDir = liveNetworkDir, liveDriveDir = liveDriveDir)
            } else {
                Text(
                    text = "SELECT DATASET DRIVER",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextMuted
                )
                Spacer(modifier = Modifier.height(8.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    drivers.forEach { d ->
                        val selected = d == driver
                        val role = clipsByDriver[d]?.firstOrNull()?.role ?: ""
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(if (selected) CyanAccent else SurfaceCard)
                                .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(14.dp))
                                .clickable { driver = d }
                                .padding(horizontal = 4.dp, vertical = 10.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = if (d.length == 1) "DRIVER $d" else d,
                                    maxLines = 1,
                                    fontFamily = FontFamily.Monospace,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (selected) Color.Black else TextPrimary
                                )
                                Text(
                                    text = role,
                                    fontSize = 9.sp,
                                    color = if (selected) Color.Black else TextMuted
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                LazyColumn(
                    modifier = Modifier.heightIn(max = 340.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(clipsByDriver[driver].orEmpty()) { clip ->
                        ClipRow(clip = clip, selected = clip.id == selectedClipId, onSelect = onSelect)
                    }
                }

            }

            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}

@Composable
private fun ClipRow(clip: ClipInfo, selected: Boolean, onSelect: (ClipInfo) -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(SurfaceCard)
            .border(
                1.dp,
                if (selected) CyanAccent else Color(0x22FFFFFF),
                RoundedCornerShape(14.dp)
            )
            .clickable { onSelect(clip) }
            .padding(14.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "${clip.drive} · ${clip.bandLabel}",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = String.format(
                        Locale.US,
                        "%.0f km/h average · %d turns · %.0f s",
                        clip.avgKmh, clip.turns, clip.durationS
                    ),
                    fontSize = 11.sp,
                    color = TextSecondary
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = String.format(Locale.US, "%.1f%%", clip.meanDriftPct),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    // green only when it actually meets the 10% benchmark, along the whole path
                    color = when {
                        clip.meanDriftPct < 10.0 -> EmeraldGreen
                        clip.meanDriftPct < 20.0 -> WarningAmber
                        else -> AlertRed
                    }
                )
                Text(
                    text = String.format(Locale.US, "average · round 2 was %.0f%%", clip.meanBasePct),
                    fontSize = 10.sp,
                    color = AlertRed
                )
            }
        }
    }
}

@Composable
private fun EngineModeTab(mode: EngineMode, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(if (selected) CyanAccent else SurfaceCard)
            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(14.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 8.dp, vertical = 12.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = mode.label,
            fontFamily = FontFamily.Monospace,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            color = if (selected) Color.Black else TextPrimary
        )
    }
}

/** What live mode does, and where its files live on the phone. */
@Composable
private fun LiveInfo(liveNetworkDir: String, liveDriveDir: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(SurfaceCard)
            .border(1.dp, Color(0x22FFFFFF), RoundedCornerShape(14.dp))
            .padding(14.dp)
    ) {
        Text(
            text = "LIVE SENSOR NAVIGATION",
            fontFamily = FontFamily.Monospace,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = EmeraldGreen
        )
        Spacer(modifier = Modifier.height(6.dp))
        listOf(
            "Reads this phone's accelerometer and gyroscope at full rate and its GPS once a second.",
            "While GPS works, the gyro is calibrated from it — drive and turn a few corners first.",
            "START BLACKOUT hides GPS from the engine. GPS keeps recording as the answer key, so the drift " +
                "on screen is measured, not guessed.",
            "Keep the phone fixed in a mount. Recording goes on with the screen off; stop it from the notification " +
                "or by switching back to replay."
        ).forEach {
            Text(text = "• $it", fontSize = 12.sp, color = TextSecondary)
            Spacer(modifier = Modifier.height(3.dp))
        }
        Spacer(modifier = Modifier.height(8.dp))
        Text(text = "Road networks", fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = TextMuted)
        Text(text = liveNetworkDir, fontFamily = FontFamily.Monospace, fontSize = 10.sp, color = TextSecondary)
        Spacer(modifier = Modifier.height(6.dp))
        Text(text = "Recorded drives", fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = TextMuted)
        Text(text = liveDriveDir, fontFamily = FontFamily.Monospace, fontSize = 10.sp, color = TextSecondary)
    }
}
