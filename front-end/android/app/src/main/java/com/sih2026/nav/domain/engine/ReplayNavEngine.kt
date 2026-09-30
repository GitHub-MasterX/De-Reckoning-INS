package com.sih2026.nav.domain.engine

import android.content.Context
import com.sih2026.nav.data.model.ClipInfo
import com.sih2026.nav.data.model.Mode
import com.sih2026.nav.data.model.NavState
import com.sih2026.nav.data.model.ReplayClip
import com.sih2026.nav.data.model.ReplayLoader
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Plays back a recorded blackout from the dataset.
 *
 * Nothing here estimates anything: every position was produced offline by the round-2 engine
 * (round2/step9_export_replay.py) and every drift figure is the measured distance between that estimate
 * and the car's own GNSS. The clip runs at its recorded rate — a lead-in with GNSS still available, where
 * all three tracks sit on top of each other, then the blackout, where they separate.
 */
data class ReplayProgress(
    val clip: ClipInfo? = null,
    val frame: Int = 0,
    val totalFrames: Int = 0,
    val inBlackout: Boolean = false,
    val elapsedS: Float = 0f,
    val distanceM: Float = 0f,
    val driftM: Float = 0f,
    val driftPct: Float = 0f,
    val noMapDriftM: Float = 0f,
    val noMapDriftPct: Float = 0f,
    val onMap: Boolean = false,
    val playing: Boolean = false
)

class ReplayNavEngine(
    private val context: Context,
    private val scope: CoroutineScope
) : NavEngine {

    val clips: List<ClipInfo> by lazy { ReplayLoader.index(context) }

    private val _state = MutableStateFlow(EMPTY)                 // the estimate: what the engine believes
    override val state: StateFlow<NavState> = _state.asStateFlow()

    private val _trueState = MutableStateFlow(EMPTY)             // the truth: the car's own GNSS
    val trueState: StateFlow<NavState> = _trueState.asStateFlow()

    private val _noMapState = MutableStateFlow(EMPTY)            // the same engine without the map
    val noMapState: StateFlow<NavState> = _noMapState.asStateFlow()

    private val _progress = MutableStateFlow(ReplayProgress())
    val progress: StateFlow<ReplayProgress> = _progress.asStateFlow()

    private val _speed = MutableStateFlow(1f)                    // playback rate, 1x .. 8x
    val speed: StateFlow<Float> = _speed.asStateFlow()

    private var clip: ReplayClip? = null
    private var job: Job? = null
    private var frame = 0

    /** Loads a clip and parks the cursors at its first frame. Playback starts on [start]. */
    fun select(clipId: String) {
        stop()
        val c = ReplayLoader.load(context, clipId)
        clip = c
        frame = 0
        render(c, 0)
    }

    /** The whole route of a clip, for drawing it before playback reaches the end. */
    fun trueTrack(): List<Pair<Double, Double>> =
        clip?.let { c -> c.trueLat.indices.map { c.trueLat[it] to c.trueLon[it] } } ?: emptyList()

    override fun start() {
        val c = clip ?: return
        if (job?.isActive == true) return
        job = scope.launch {
            while (isActive) {
                render(c, frame)
                if (frame >= c.totalFrames - 1) {
                    _progress.value = _progress.value.copy(playing = false)
                    break
                }
                frame++
                delay((1000f / c.hz / _speed.value).toLong().coerceAtLeast(8L))
            }
        }
        _progress.value = _progress.value.copy(playing = true)
    }

    override fun stop() {
        job?.cancel()
        job = null
        _progress.value = _progress.value.copy(playing = false)
    }

    fun setSpeed(multiplier: Float) {
        _speed.value = multiplier.coerceIn(1f, 8f)
    }

    /** Restarts the clip from its GNSS-fused lead-in. */
    fun restart() {
        val c = clip ?: return
        stop()
        frame = 0
        render(c, 0)
    }

    /**
     * The demo toggle: in a replay the blackout is already recorded, so "on" jumps to the moment GNSS is
     * lost and "off" rewinds to the lead-in before it.
     */
    override fun setGnssBlackout(enabled: Boolean) {
        val c = clip ?: return
        frame = if (enabled) c.leadInFrames else 0
        render(c, frame)
    }

    private fun render(c: ReplayClip, f: Int) {
        val now = System.nanoTime()
        if (f < c.leadInFrames) {
            // GNSS still available: the estimate is the fix, so all three tracks coincide
            val fused = NavState(
                lat = c.leadInLat[f], lon = c.leadInLon[f],
                headingDeg = c.leadInHeading[f], speedKmh = c.leadInSpeedKmh[f],
                mode = Mode.GNSS_FUSED, uncertaintyM = 4f, timestampNs = now
            )
            _state.value = fused
            _trueState.value = fused
            _noMapState.value = fused
            _progress.value = ReplayProgress(
                clip = c.info, frame = f, totalFrames = c.totalFrames, inBlackout = false,
                elapsedS = (f - c.leadInFrames).toFloat() / c.hz,
                playing = _progress.value.playing
            )
            return
        }

        val k = (f - c.leadInFrames).coerceIn(0, c.blackoutFrames - 1)
        _trueState.value = NavState(
            lat = c.trueLat[k], lon = c.trueLon[k],
            headingDeg = c.trueHeading[k], speedKmh = c.trueSpeedKmh[k],
            mode = Mode.GNSS_FUSED, uncertaintyM = 4f, timestampNs = now
        )
        _state.value = NavState(
            lat = c.pfLat[k], lon = c.pfLon[k],
            headingDeg = c.pfHeading[k],
            speedKmh = c.engineSpeedKmh.toFloat(),        // the engine holds the last GNSS speed it saw
            mode = Mode.DEAD_RECKONING,
            uncertaintyM = c.driftM[k],                   // the measured error, not a guess
            timestampNs = now
        )
        _noMapState.value = _state.value.copy(
            lat = c.noMapLat[k], lon = c.noMapLon[k], uncertaintyM = c.noMapDriftM[k]
        )
        _progress.value = ReplayProgress(
            clip = c.info, frame = f, totalFrames = c.totalFrames, inBlackout = true,
            elapsedS = k.toFloat() / c.hz,
            distanceM = c.trueDistM[k],
            driftM = c.driftM[k], driftPct = c.driftPct[k],
            noMapDriftM = c.noMapDriftM[k], noMapDriftPct = c.noMapDriftPct[k],
            onMap = c.pfOnMap[k],
            playing = _progress.value.playing
        )
    }

    private companion object {
        val EMPTY = NavState(
            lat = 52.40384, lon = -1.50616, headingDeg = 0f, speedKmh = 0f,
            mode = Mode.ACQUIRING, uncertaintyM = 0f, timestampNs = 0L
        )
    }
}
