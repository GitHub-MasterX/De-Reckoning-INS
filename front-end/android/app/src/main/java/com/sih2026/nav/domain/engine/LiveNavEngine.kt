package com.sih2026.nav.domain.engine

import android.content.Context
import android.location.Location
import android.os.Build
import com.sih2026.nav.data.model.Mode
import com.sih2026.nav.data.model.NavState
import com.sih2026.nav.live.engine.BlackoutScore
import com.sih2026.nav.live.engine.Fix
import com.sih2026.nav.live.engine.ImuStream
import com.sih2026.nav.live.engine.LiveEngineCore
import com.sih2026.nav.live.engine.MotionModel
import com.sih2026.nav.live.engine.PfParams
import com.sih2026.nav.live.engine.RoadNetwork
import com.sih2026.nav.live.record.DriveRecorder
import com.sih2026.nav.live.sensor.LiveSensors
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.util.Locale
import java.util.concurrent.Executors

/** What the live screen shows besides the cursors. */
data class LiveStatus(
    val running: Boolean = false,
    val gpsAllowed: Boolean = true,
    val hasFix: Boolean = false,
    val fixAccuracyM: Float = Float.NaN,
    val gpsSpeedKmh: Float = 0f,
    val inBlackout: Boolean = false,
    val stationary: Boolean = false,
    val accHz: Float = 0f,
    val gyrHz: Float = 0f,
    val calibration: String = "waiting for GPS",
    val calibrationFitted: Boolean = false,
    val mount: String = "accelerometer mount: waiting for GPS",
    val mountFitted: Boolean = false,
    val fullSpeedKmh: Float = Float.NaN,
    val fullOnMap: Boolean = false,
    val network: String = "no road network loaded",
    val networkLoaded: Boolean = false,
    val score: BlackoutScore? = null,
    val lastScore: BlackoutScore? = null,
    val onMap: Boolean = false,
    val recording: String = "",
    val recordingBytes: Long = 0L,
    val message: String? = null
)

/**
 * The round-2 engine running on this phone's own sensors.
 *
 * Sensors and GPS arrive on a background thread (LiveSensors); rows and fixes are handed, in order, to one engine
 * thread that owns LiveEngineCore, so the engine is never touched from two threads. The blackout switch hides GPS
 * from the engine only: fixes keep arriving, drawn as the true position and used to measure the drift.
 *
 * Road networks are files pushed to the phone (round2/phone/export_roadnet.py) into
 *   Android/data/com.sih2026.nav.live/files/roadnet/
 * and the first one whose box contains the GPS position is loaded. Recordings go to .../files/drives/.
 */
class LiveNavEngine(private val context: Context) : NavEngine {

    private val _state = MutableStateFlow(EMPTY)                 // the estimate, with the map where there is one
    override val state: StateFlow<NavState> = _state.asStateFlow()

    private val _noMapState = MutableStateFlow(EMPTY)            // the same engine without the map
    val noMapState: StateFlow<NavState> = _noMapState.asStateFlow()

    private val _trueState = MutableStateFlow(EMPTY)             // the phone's own GPS — the answer key
    val trueState: StateFlow<NavState> = _trueState.asStateFlow()

    private val _fullState = MutableStateFlow(EMPTY)             // the 248 Hz engine, with the map where there is one
    val fullState: StateFlow<NavState> = _fullState.asStateFlow()

    private val _status = MutableStateFlow(LiveStatus())
    val status: StateFlow<LiveStatus> = _status.asStateFlow()

    private val engineThread = Executors.newSingleThreadExecutor { Thread(it, "live-engine") }
    private val model by lazy { MotionModel(context.assets.open("live/motion_deploy_all.hgb").use { it.readBytes() }) }
    private var core: LiveEngineCore? = null
    private var sensors: LiveSensors? = null
    private var recorder: DriveRecorder? = null
    private var networkPicked = false
    private var lastPickNs = 0L
    private var rowsSincePreview = 0

    val networkDir: File get() = File(context.getExternalFilesDir(null), "roadnet")
    val driveDir: File get() = File(context.getExternalFilesDir(null), "drives")

    override fun start() {
        if (sensors != null) return
        networkDir.mkdirs()
        val rec = DriveRecorder(driveDir, emptyList())
        val s = LiveSensors(context, rec,
            onRow = { row -> engineThread.execute { onRow(row) } },
            onFix = { loc -> engineThread.execute { onFix(loc) } })
        header(s).forEach { rec.line("# $it") }
        recorder = rec
        sensors = s
        engineThread.execute {
            core = LiveEngineCore(model, PfParams(), System.nanoTime())
            networkPicked = false
            lastPickNs = 0L
        }
        s.start()
        lastKnown()?.let { loc ->                  // somewhere sensible to show until the first GPS fix
            val here = NavState(loc.latitude, loc.longitude, 0f, 0f, Mode.ACQUIRING, loc.accuracy, System.nanoTime())
            _state.value = here; _noMapState.value = here; _trueState.value = here
            engineThread.execute {                 // and the road network for this area, loaded before GPS arrives
                pickNetwork(loc.latitude, loc.longitude)
            }
        }
        _status.value = LiveStatus(
            running = true, gpsAllowed = s.gpsAllowed, recording = rec.file.name,
            network = networkSummary(),
            message = when {
                !s.hasGyroscope -> "This phone has no gyroscope: the engine cannot run."
                !s.gpsAllowed -> "Location permission is off: allow it to get GPS."
                else -> null
            }
        )
    }

    override fun stop() {
        val s = sensors ?: return
        s.stop()
        sensors = null
        val rec = recorder
        recorder = null
        engineThread.execute {
            core = null
            rec?.close()
        }
        _status.value = _status.value.copy(running = false, inBlackout = false)
    }

    override fun setGnssBlackout(enabled: Boolean) {
        engineThread.execute {
            val c = core ?: return@execute
            val now = System.nanoTime()
            if (enabled) {
                val blackout = c.startBlackout()
                if (blackout == null) {
                    publish { it.copy(message = "No GPS fix yet — wait for GNSS OK before starting a blackout.") }
                } else {
                    recorder?.line("B,${android.os.SystemClock.elapsedRealtimeNanos()},1")
                    publish { it.copy(inBlackout = true, score = blackout.current, message = null) }
                }
            } else {
                val score = c.endBlackout()
                recorder?.line("B,${android.os.SystemClock.elapsedRealtimeNanos()},0")
                val fix = c.lastFix
                if (fix != null) {
                    val back = fixState(fix, now)
                    _state.value = back; _noMapState.value = back; _fullState.value = back
                }
                publish { it.copy(inBlackout = false, score = null, lastScore = score ?: it.lastScore) }
            }
        }
    }

    private fun onRow(row: ImuStream.Row) {
        val c = core ?: return
        val tNs = row.tNs
        val out = c.onRow(tNs / 1e9, row.accSample, row.gyrSample, row.accMean, row.gyrMean)
        val now = System.nanoTime()
        recorder?.line(buildString {
            append("E,").append(tNs).append(',').append(out.lat).append(',').append(out.lon).append(',')
            append(out.noMapLat).append(',').append(out.noMapLon).append(',').append(out.headingDeg.toFloat()).append(',')
            append(if (out.stationary) 1 else 0).append(',').append(if (out.inBlackout) 1 else 0).append(',')
            append(if (out.onMap) 1 else 0).append(',').append(out.fullLat).append(',').append(out.fullLon).append(',')
            append(out.fullSpeedKmh.toFloat()).append(',').append(if (out.fullOnMap) 1 else 0)
        })
        val score = c.score
        if (out.inBlackout && !out.lat.isNaN()) {
            _state.value = NavState(out.lat, out.lon, out.headingDeg.toFloat(), out.speedKmh.toFloat(),
                Mode.DEAD_RECKONING, (score?.driftM ?: 0.0).toFloat(), now)
            _noMapState.value = NavState(out.noMapLat, out.noMapLon, out.headingDeg.toFloat(), out.speedKmh.toFloat(),
                Mode.DEAD_RECKONING, (score?.noMapDriftM ?: 0.0).toFloat(), now)
            _fullState.value = NavState(out.fullLat, out.fullLon, out.fullHeadingDeg.toFloat(), out.fullSpeedKmh.toFloat(),
                Mode.DEAD_RECKONING, (score?.fullDriftM ?: 0.0).toFloat(), now)
        }
        rowsSincePreview++
        val preview = if (!out.inBlackout && rowsSincePreview >= 50) {       // every 5 s while GPS works
            rowsSincePreview = 0
            c.previewCalibration()
        } else null
        val s = sensors
        publish { st ->
            st.copy(
                stationary = out.stationary, inBlackout = out.inBlackout, score = score ?: st.score.takeIf { out.inBlackout },
                onMap = out.onMap, accHz = s?.accHz ?: 0f, gyrHz = s?.gyrHz ?: 0f,
                recordingBytes = recorder?.bytesWritten ?: st.recordingBytes,
                calibration = preview?.let { describe(it.gyroFull) } ?: st.calibration,
                calibrationFitted = preview?.let { it.gyroFull.method == "vertical-window" } ?: st.calibrationFitted,
                mount = preview?.let { describeMount(it.mount) } ?: st.mount,
                mountFitted = preview?.let { it.mount != null } ?: st.mountFitted,
                fullSpeedKmh = if (out.inBlackout) out.fullSpeedKmh.toFloat() else Float.NaN,
                fullOnMap = out.fullOnMap
            )
        }
    }

    private fun onFix(loc: Location) {
        val c = core ?: return
        val fix = Fix(
            t = loc.elapsedRealtimeNanos / 1e9, lat = loc.latitude, lon = loc.longitude,
            speed = if (loc.hasSpeed()) loc.speed.toDouble() else Double.NaN,
            bearing = if (loc.hasBearing()) loc.bearing.toDouble() else Double.NaN,
            accuracyM = if (loc.hasAccuracy()) loc.accuracy.toDouble() else Double.NaN
        )
        c.onFix(fix)
        val now = System.nanoTime()
        val truth = fixState(fix, now)
        _trueState.value = truth
        if (!c.inBlackout) {
            _state.value = truth
            _noMapState.value = truth
            _fullState.value = truth
        }
        val net = c.network
        val outside = net != null && !net.contains(fix.lat, fix.lon)
        if ((net == null || outside) && now - lastPickNs > 60_000_000_000L) pickNetwork(fix.lat, fix.lon)
        publish {
            it.copy(hasFix = true, fixAccuracyM = fix.accuracyM.toFloat(), gpsSpeedKmh = truth.speedKmh,
                score = c.score ?: it.score.takeIf { c.inBlackout })
        }
    }

    /** Loads, off the engine thread, the first pushed road network whose box holds the position. */
    private fun pickNetwork(lat: Double, lon: Double) {
        networkPicked = true
        lastPickNs = System.nanoTime()
        val files = networkDir.listFiles { f -> f.name.endsWith(".roadnet.bin") }?.sortedBy { it.name }.orEmpty()
        val match = files.firstOrNull { f ->
            runCatching {
                RandomAccessFile(f, "r").use { raf ->
                    val head = ByteArray(minOf(raf.length(), 512L).toInt()).also { raf.readFully(it) }
                    val box = RoadNetwork.header(ByteBuffer.wrap(head)).second
                    lat in box[0]..box[2] && lon in box[1]..box[3]
                }
            }.getOrDefault(false)
        }
        if (match == null) {
            publish {
                it.copy(network = if (files.isEmpty()) "no road network on the phone — map-free only"
                else "no road network covers this area — map-free only")
            }
            return
        }
        publish { it.copy(network = "loading ${match.name}…") }
        Thread({
            val result = runCatching {
                RandomAccessFile(match, "r").use { raf ->
                    val buf = raf.channel.map(FileChannel.MapMode.READ_ONLY, 0, raf.length())
                    RoadNetwork(buf)
                }
            }
            engineThread.execute {
                result.onSuccess { net ->
                    core?.network = net
                    publish {
                        it.copy(networkLoaded = true,
                            network = String.format(Locale.US, "road network %s · %,.0f km", net.name, net.kmOfRoad))
                    }
                }.onFailure { e -> publish { it.copy(network = "road network failed to load: ${e.message}") } }
            }
        }, "roadnet-load").start()
    }

    /** The newest position any provider remembers — for the map only, never for the engine. */
    private fun lastKnown(): Location? = try {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
        lm.getProviders(true).mapNotNull { lm.getLastKnownLocation(it) }.maxByOrNull { it.elapsedRealtimeNanos }
    } catch (e: SecurityException) {
        null
    }

    private fun describeMount(m: com.sih2026.nav.live.engine.MountCalibration?) = if (m == null)
        "accelerometer speed off (held GPS speed): ${com.sih2026.nav.live.engine.MountCalibration.lastReason}"
    else String.format(Locale.US, "accelerometer speed on: fitted from %d turn samples (fit r %.2f)", m.turnSamples, m.rightFitR)

    private fun networkSummary(): String {
        val n = networkDir.listFiles { f -> f.name.endsWith(".roadnet.bin") }?.size ?: 0
        return if (n == 0) "no road network on the phone — map-free only" else "waiting for GPS to pick a road network"
    }

    private fun describe(cal: com.sih2026.nav.live.engine.GyroCalibration) = when (cal.method) {
        "window", "vertical-window" -> String.format(Locale.US, "gyro calibrated ×%.2f from %d turns", cal.scale, cal.turnWindows)
        "vertical-default" -> "gyro not calibrated yet — ride and turn a few corners"
        "rate" -> "gyro axis fitted; turn a few corners to fit its scale"
        "gravity" -> "gyro from gravity only — drive and turn to calibrate"
        else -> "gyro not calibrated"
    }

    private fun header(s: LiveSensors): List<String> = listOf(
        "SIH 2026 live drive · ${Build.MANUFACTURER} ${Build.MODEL} · Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})",
        "times: nanoseconds on SystemClock.elapsedRealtimeNanos, the clock of both sensor events and GPS fixes",
        "engine: round-2 particle filter ${PfParams()} · stop classifier deploy_all · calibration window, fallback rate, then gravity",
        "248 Hz engine: gyro means, mount calibration, speed estimator ${com.sih2026.nav.live.engine.SpeedEstimator.Settings()}",
        "columns: A t,ax,ay,az | G t,gx,gy,gz | a t,ax,ay,az,bx,by,bz | g t,gx,gy,gz,dx,dy,dz | M t,mx,my,mz | " +
            "L t,utc_ms,lat,lon,alt,acc_m,speed,speed_acc,bearing,bearing_acc,has_speed,has_bearing | B t,on | " +
            "E t,lat,lon,nomap_lat,nomap_lon,heading,stationary,blackout,on_map,full_lat,full_lon,full_speed_kmh,full_on_map"
    ) + s.description

    private fun fixState(fix: Fix, now: Long) = NavState(
        lat = fix.lat, lon = fix.lon,
        headingDeg = if (fix.bearing.isNaN()) _trueState.value.headingDeg else fix.bearing.toFloat(),
        speedKmh = if (fix.speed.isNaN()) 0f else (fix.speed * 3.6).toFloat(),
        mode = Mode.GNSS_FUSED,
        uncertaintyM = if (fix.accuracyM.isNaN()) 0f else fix.accuracyM.toFloat(),
        timestampNs = now
    )

    private inline fun publish(change: (LiveStatus) -> LiveStatus) = _status.update(change)

    companion object {
        val EMPTY = NavState(
            lat = 13.0827, lon = 80.2707, headingDeg = 0f, speedKmh = 0f,
            mode = Mode.ACQUIRING, uncertaintyM = 0f, timestampNs = 0L
        )
    }
}
