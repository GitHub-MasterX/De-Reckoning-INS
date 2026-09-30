package com.sih2026.nav.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sih2026.nav.NavApp
import com.sih2026.nav.data.model.ClipInfo
import com.sih2026.nav.data.model.EngineMode
import com.sih2026.nav.data.model.Mode
import com.sih2026.nav.data.model.NavState
import com.sih2026.nav.domain.engine.LiveNavEngine
import com.sih2026.nav.domain.engine.LiveStatus
import com.sih2026.nav.domain.engine.NavEngine
import com.sih2026.nav.domain.engine.ReplayNavEngine
import com.sih2026.nav.domain.engine.ReplayProgress
import com.sih2026.nav.live.LiveRecordingService
import com.sih2026.nav.ui.utils.HeadingInterpolator
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.osmdroid.util.GeoPoint

class NavViewModel(application: Application) : AndroidViewModel(application) {

    private val replayEngine = ReplayNavEngine(application, viewModelScope)
    private val liveEngine: LiveNavEngine = (application as NavApp).liveEngine

    // live mode survives the screen: if the recording service is already running, come back to it
    private val _engineMode = MutableStateFlow(if (LiveRecordingService.running.value) EngineMode.LIVE else EngineMode.REPLAY)
    val engineMode: StateFlow<EngineMode> = _engineMode.asStateFlow()

    val navEngine: NavEngine get() = if (_engineMode.value == EngineMode.REPLAY) replayEngine else liveEngine

    /** Every bundled clip, grouped by the driver who recorded it. */
    val clipsByDriver: Map<String, List<ClipInfo>> by lazy { replayEngine.clips.groupBy { it.driver } }
    val drivers: List<String> by lazy { clipsByDriver.keys.sorted() }

    private val _selectedDriver = MutableStateFlow<String?>(null)
    val selectedDriver: StateFlow<String?> = _selectedDriver.asStateFlow()

    private val _selectedClip = MutableStateFlow<ClipInfo?>(null)
    val selectedClip: StateFlow<ClipInfo?> = _selectedClip.asStateFlow()

    val progress: StateFlow<ReplayProgress> = replayEngine.progress
    val playbackSpeed: StateFlow<Float> = replayEngine.speed
    val liveStatus: StateFlow<LiveStatus> = liveEngine.status

    /** Where the phone keeps pushed road networks and its recordings. */
    val liveNetworkDir: String get() = liveEngine.networkDir.absolutePath
    val liveDriveDir: String get() = liveEngine.driveDir.absolutePath

    // Smoothed for rendering; the underlying data is 10 Hz (estimates) and 1 Hz (live GPS)
    private val estimateInterp = HeadingInterpolator()
    private val truthInterp = HeadingInterpolator()

    private val _estimateState = MutableStateFlow(replayEngine.state.value)
    val estimateState: StateFlow<NavState> = _estimateState.asStateFlow()

    private val _truthState = MutableStateFlow(replayEngine.trueState.value)
    val truthState: StateFlow<NavState> = _truthState.asStateFlow()

    // Trails, built up as the clip plays or the phone drives
    private val _truePath = MutableStateFlow<List<GeoPoint>>(emptyList())
    val truePath: StateFlow<List<GeoPoint>> = _truePath.asStateFlow()

    private val _estimatePath = MutableStateFlow<List<GeoPoint>>(emptyList())
    val estimatePath: StateFlow<List<GeoPoint>> = _estimatePath.asStateFlow()

    private val _noMapPath = MutableStateFlow<List<GeoPoint>>(emptyList())
    val noMapPath: StateFlow<List<GeoPoint>> = _noMapPath.asStateFlow()

    // live mode only: the 248 Hz engine
    private val fullInterp = HeadingInterpolator()
    private val _fullState = MutableStateFlow(liveEngine.fullState.value)
    val fullState: StateFlow<NavState> = _fullState.asStateFlow()
    private val _fullPath = MutableStateFlow<List<GeoPoint>>(emptyList())
    val fullPath: StateFlow<List<GeoPoint>> = _fullPath.asStateFlow()

    private val isReplay get() = _engineMode.value == EngineMode.REPLAY

    init {
        drivers.firstOrNull()?.let { selectDriver(it) }

        viewModelScope.launch {
            replayEngine.state.collect { s ->
                if (!isReplay) return@collect
                estimateInterp.updateState(s)
                if (s.mode == Mode.DEAD_RECKONING) {
                    _estimatePath.value = _estimatePath.value + GeoPoint(s.lat, s.lon)
                    val n = replayEngine.noMapState.value
                    _noMapPath.value = _noMapPath.value + GeoPoint(n.lat, n.lon)
                }
            }
        }

        viewModelScope.launch {
            replayEngine.trueState.collect { s ->
                if (!isReplay) return@collect
                truthInterp.updateState(s)
                _truePath.value = _truePath.value + GeoPoint(s.lat, s.lon)
            }
        }

        viewModelScope.launch {
            liveEngine.state.collect { s ->
                if (isReplay || s.timestampNs == 0L) return@collect
                estimateInterp.updateState(s)
                if (s.mode == Mode.DEAD_RECKONING) {
                    _estimatePath.value = (_estimatePath.value + GeoPoint(s.lat, s.lon)).takeLast(MAX_TRAIL)
                    val n = liveEngine.noMapState.value
                    _noMapPath.value = (_noMapPath.value + GeoPoint(n.lat, n.lon)).takeLast(MAX_TRAIL)
                }
            }
        }

        viewModelScope.launch {
            liveEngine.fullState.collect { s ->
                if (isReplay || s.timestampNs == 0L) return@collect
                fullInterp.updateState(s)
                if (s.mode == Mode.DEAD_RECKONING) {
                    _fullPath.value = (_fullPath.value + GeoPoint(s.lat, s.lon)).takeLast(MAX_TRAIL)
                }
            }
        }

        viewModelScope.launch {
            liveEngine.trueState.collect { s ->
                if (isReplay || s.timestampNs == 0L) return@collect
                truthInterp.updateState(s)
                _truePath.value = (_truePath.value + GeoPoint(s.lat, s.lon)).takeLast(MAX_TRAIL)
            }
        }

        // 60 fps render loop
        viewModelScope.launch {
            while (isActive) {
                _estimateState.value = estimateInterp.interpolate()
                _truthState.value = truthInterp.interpolate()
                if (!isReplay) _fullState.value = fullInterp.interpolate()
                delay(16)
            }
        }
    }

    /**
     * Switches engines. Live mode starts the recording service (sensors, GPS, engines, recording — kept running with the
     * screen off); leaving live mode stops it.
     */
    fun setEngineMode(mode: EngineMode) {
        if (_engineMode.value == mode) return
        replayEngine.stop()
        clearTrails()
        _engineMode.value = mode
        if (mode == EngineMode.LIVE) {
            LiveRecordingService.start(getApplication())
            estimateInterp.updateState(liveEngine.state.value)
            truthInterp.updateState(liveEngine.trueState.value)
            fullInterp.updateState(liveEngine.fullState.value)
        } else {
            LiveRecordingService.stop(getApplication())
            selectedClip.value?.let { replayEngine.select(it.id) }
        }
    }

    /** Restarts the live sensors, e.g. after location permission was granted. */
    fun restartLive() {
        if (_engineMode.value != EngineMode.LIVE) return
        if (LiveRecordingService.running.value) LiveRecordingService.restart(getApplication())
        else LiveRecordingService.start(getApplication())
    }

    /** The live demo switch: hide GPS from the engine, or give it back. */
    fun toggleLiveBlackout() {
        val on = !liveStatus.value.inBlackout
        if (on) {
            _estimatePath.value = emptyList()
            _noMapPath.value = emptyList()
            _fullPath.value = emptyList()
            _truePath.value = _truePath.value.takeLast(1)
        }
        liveEngine.setGnssBlackout(on)
    }

    /** Picks a driver and loads that driver's first clip, ready to play. */
    fun selectDriver(driver: String) {
        _selectedDriver.value = driver
        clipsByDriver[driver]?.firstOrNull()?.let { selectClip(it) }
    }

    fun selectClip(clip: ClipInfo) {
        clearTrails()
        _selectedClip.value = clip
        _selectedDriver.value = clip.driver
        replayEngine.select(clip.id)
    }

    fun play() = replayEngine.start()

    fun pause() = replayEngine.stop()

    fun togglePlay() {
        if (progress.value.playing) replayEngine.stop() else replayEngine.start()
    }

    fun restart() {
        clearTrails()
        replayEngine.restart()
    }

    fun setPlaybackSpeed(multiplier: Float) = replayEngine.setSpeed(multiplier)

    private fun clearTrails() {
        _truePath.value = emptyList()
        _estimatePath.value = emptyList()
        _noMapPath.value = emptyList()
        _fullPath.value = emptyList()
    }

    override fun onCleared() {
        super.onCleared()
        replayEngine.stop()                      // live mode belongs to the recording service, not to this screen
    }

    private companion object {
        const val MAX_TRAIL = 6000
    }
}
