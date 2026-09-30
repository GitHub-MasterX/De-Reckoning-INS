package com.sih2026.nav.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import com.sih2026.nav.data.model.EngineMode
import com.sih2026.nav.ui.components.ClipPickerSheet
import com.sih2026.nav.ui.components.LiveTelemetryOverlay
import com.sih2026.nav.ui.components.MapViewContainer
import com.sih2026.nav.ui.components.TelemetryOverlay
import com.sih2026.nav.ui.viewmodel.NavViewModel

@Composable
fun MainScreen(viewModel: NavViewModel) {
    val estimate by viewModel.estimateState.collectAsState()
    val truth by viewModel.truthState.collectAsState()
    val progress by viewModel.progress.collectAsState()
    val clip by viewModel.selectedClip.collectAsState()
    val speed by viewModel.playbackSpeed.collectAsState()
    val engineMode by viewModel.engineMode.collectAsState()
    val liveStatus by viewModel.liveStatus.collectAsState()

    val truePath by viewModel.truePath.collectAsState()
    val estimatePath by viewModel.estimatePath.collectAsState()
    val noMapPath by viewModel.noMapPath.collectAsState()
    val fullState by viewModel.fullState.collectAsState()
    val fullPath by viewModel.fullPath.collectAsState()

    var showPicker by remember { mutableStateOf(false) }
    var showNoMap by remember { mutableStateOf(true) }

    val context = LocalContext.current
    val locationGranted = {
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }
    // live mode starts once the location question is answered; without it the sensors still run and record
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        if (engineMode == EngineMode.LIVE) viewModel.restartLive() else viewModel.setEngineMode(EngineMode.LIVE)
    }
    val requestLocation = {
        val wanted = mutableListOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        if (android.os.Build.VERSION.SDK_INT >= 33) wanted += Manifest.permission.POST_NOTIFICATIONS  // the recording notice
        permissionLauncher.launch(wanted.toTypedArray())
    }

    val live = engineMode == EngineMode.LIVE

    Box(modifier = Modifier.fillMaxSize()) {
        MapViewContainer(
            estimate = estimate,
            truth = truth,
            inBlackout = if (live) liveStatus.inBlackout else progress.inBlackout,
            truePath = truePath,
            estimatePath = estimatePath,
            noMapPath = noMapPath,
            showNoMap = showNoMap,
            modifier = Modifier.fillMaxSize(),
            full = if (live) fullState else null,
            fullPath = if (live) fullPath else emptyList()
        )

        if (live) {
            LiveTelemetryOverlay(
                status = liveStatus,
                showNoMap = showNoMap,
                onToggleBlackout = { viewModel.toggleLiveBlackout() },
                onToggleNoMap = { showNoMap = !showNoMap },
                onOpenPicker = { showPicker = true },
                onRetryGps = { if (locationGranted()) viewModel.restartLive() else requestLocation() },
                modifier = Modifier.fillMaxSize()
            )
        } else {
            TelemetryOverlay(
                clip = clip,
                progress = progress,
                estimate = estimate,
                truth = truth,
                playbackSpeed = speed,
                showNoMap = showNoMap,
                onTogglePlay = { viewModel.togglePlay() },
                onRestart = { viewModel.restart() },
                onCycleSpeed = { viewModel.setPlaybackSpeed(if (speed >= 8f) 1f else speed * 2f) },
                onToggleNoMap = { showNoMap = !showNoMap },
                onOpenPicker = { showPicker = true },
                modifier = Modifier.fillMaxSize()
            )
        }

        if (showPicker) {
            ClipPickerSheet(
                engineMode = engineMode,
                drivers = viewModel.drivers,
                clipsByDriver = viewModel.clipsByDriver,
                selectedClipId = clip?.id,
                liveNetworkDir = viewModel.liveNetworkDir,
                liveDriveDir = viewModel.liveDriveDir,
                onSetEngineMode = { mode ->
                    if (mode == EngineMode.LIVE && !locationGranted()) requestLocation() else viewModel.setEngineMode(mode)
                    showPicker = false
                },
                onSelect = {
                    viewModel.selectClip(it)
                    showPicker = false
                },
                onDismiss = { showPicker = false }
            )
        }
    }
}
