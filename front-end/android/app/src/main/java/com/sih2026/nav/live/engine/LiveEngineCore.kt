package com.sih2026.nav.live.engine

import java.util.Random
import kotlin.math.abs

/** One GNSS fix. t is seconds on the sensor clock (SystemClock.elapsedRealtimeNanos / 1e9). */
data class Fix(
    val t: Double,
    val lat: Double,
    val lon: Double,
    val speed: Double,        // m/s, NaN when the fix has none
    val bearing: Double,      // degrees clockwise from north, NaN when the fix has none
    val accuracyM: Double
)

/** What the engine reports after each 10 Hz row. Positions are NaN until there is something to show. */
data class LiveOutput(
    val t: Double,
    val inBlackout: Boolean,
    val stationary: Boolean,
    // round 2 on 10 Hz samples: with the road network where there is one, and without it
    val lat: Double,
    val lon: Double,
    val headingDeg: Double,
    val speedKmh: Double,
    val noMapLat: Double,
    val noMapLon: Double,
    val onMap: Boolean,
    val ess: Double,
    val reseeds: Int,
    // the 248 Hz engine: full-rate gyro, accelerometer speed
    val fullLat: Double = Double.NaN,
    val fullLon: Double = Double.NaN,
    val fullHeadingDeg: Double = Double.NaN,
    val fullSpeedKmh: Double = Double.NaN,
    val fullSpeedSigmaKmh: Double = Double.NaN,
    val fullNoMapLat: Double = Double.NaN,
    val fullNoMapLon: Double = Double.NaN,
    val fullOnMap: Boolean = false,
    // analysis only (LiveEngineCore.truth set): the 248 Hz engine's map-free estimate with one input replaced by truth —
    // true stops, true speed, true heading, true speed and heading — as lat, lon pairs
    val oracle: DoubleArray? = null
)

/** A blackout's measured result so far, against the GNSS the engines are not allowed to use. */
data class BlackoutScore(
    val elapsedS: Double,
    val trueDistanceM: Double,
    val engineDistanceM: Double,
    val driftM: Double,
    val driftPct: Double,
    val noMapDriftM: Double,
    val noMapDriftPct: Double,
    val calibration: GyroCalibration,
    val networkUsed: String?,
    val seeded: Boolean,
    val fullDriftM: Double = 0.0,
    val fullDriftPct: Double = 0.0,
    val fullNoMapDriftM: Double = 0.0,
    val fullNoMapDriftPct: Double = 0.0,
    val fullCalibration: GyroCalibration? = null,
    val mount: MountCalibration? = null,
    val turnReadings: Int = 0,
    val gpsSpeedKmh: Double = Double.NaN,
    val oracleDriftPct: DoubleArray? = null,   // analysis only: true stops, true speed, true heading, both
    val tiltRateMean: Double = Double.NaN      // mean rotation about horizontal axes over the blackout, rad/s
)

/** What calibration could do if a blackout started now: shown while GPS still works. */
data class CalibrationPreview(val gyro: GyroCalibration, val gyroFull: GyroCalibration, val mount: MountCalibration?)

/**
 * The live engines, free of Android so they can be tested and replayed on recorded drives: 10 Hz rows and GNSS fixes
 * go in, estimates come out.
 *
 *   history    the last 30 minutes of rows and fixes: what calibration may learn from while GNSS works
 *   stops      round 1's classifier on every 20-row window of samples, hop 5, the latest complete window holding
 *   blackout   starts from the last fix: its position, course and speed. Two engines then run side by side:
 *                round 2      gyro samples calibrated on the history, held GPS speed, road network — as validated
 *                248 Hz       every gyro sample, turning about true vertical as TiltTracker follows it (a phone in a
 *                             hand or a bag, a leaning two-wheeler); speed from the accelerometer against true vertical
 *                             (SpeedEstimator) when the recent fit of the vehicle's axes is clearly good, else held
 *                             speed; the same road network
 *              Fixes that keep arriving are never used by either engine — only to score them.
 * Several blackouts may run at once (replaying a drive with a start every 250 m); the live app uses one.
 */
class LiveEngineCore(
    private val model: MotionModel,
    private val params: PfParams = PfParams(),
    seed: Long = 0L,
    private val speedSettings: SpeedEstimator.Settings = SpeedEstimator.Settings()
) {

    companion object {
        const val HISTORY_ROWS = 18_000                 // 30 min at 10 Hz
        const val HISTORY_S = HISTORY_ROWS / Calibration.FS
        private const val RECENT_ROWS = 100             // estimates kept to meet fixes that arrive late
    }

    private val rng = Random(seed)
    var network: RoadNetwork? = null

    /** Tests on simulated drives only: the true stopped state for a row time, instead of the classifier. */
    var stationaryOverride: ((Double) -> Boolean)? = null

    /**
     * Analysis only, on recorded drives: the true speed (m/s) and course (radians) at a row time, from GPS, so each
     * blackout also runs the 248 Hz engine's dead reckoning with one input replaced by the truth. Never set on the phone.
     */
    var truth: ((Double) -> DoubleArray?)? = null

    // ring buffer of rows
    private val t = DoubleArray(HISTORY_ROWS)
    private val accS = DoubleArray(3 * HISTORY_ROWS)
    private val gyrS = DoubleArray(3 * HISTORY_ROWS)
    private val accM = DoubleArray(3 * HISTORY_ROWS)
    private val gyrM = DoubleArray(3 * HISTORY_ROWS)
    private val stat = BooleanArray(HISTORY_ROWS)
    // TiltTracker's reading of each row: horizontal acceleration against true vertical, and rotation about it
    private val tracker = TiltTracker()
    private val hq1 = DoubleArray(HISTORY_ROWS)
    private val hq2 = DoubleArray(HISTORY_ROWS)
    private val clockwise = DoubleArray(HISTORY_ROWS)
    private val tiltBuf = DoubleArray(HISTORY_ROWS)
    private var rows = 0L
    private var stationaryNow = false

    private val fixes = ArrayDeque<Fix>()
    val lastFix: Fix? get() = fixes.lastOrNull()

    private val active = ArrayList<Blackout>()
    val latest: Blackout? get() = active.lastOrNull()
    val inBlackout get() = active.isNotEmpty()
    val score: BlackoutScore? get() = latest?.current

    private fun slot(row: Long) = (row % HISTORY_ROWS).toInt()
    private val newest get() = rows - 1
    private val oldest get() = maxOf(0L, rows - HISTORY_ROWS)

    /** A 10 Hz row from a source with no full-rate data (a recorded 10 Hz dataset): the means are the samples. */
    fun onRow(time: Double, ax: Double, ay: Double, az: Double, gx: Double, gy: Double, gz: Double): LiveOutput {
        val a = doubleArrayOf(ax, ay, az)
        val g = doubleArrayOf(gx, gy, gz)
        return onRow(time, a, g, a, g)
    }

    /** One 10 Hz row: samples at the tick and full-rate means over the interval (ImuStream.Row). */
    fun onRow(time: Double, accSample: DoubleArray, gyrSample: DoubleArray, accMean: DoubleArray, gyrMean: DoubleArray): LiveOutput {
        val s = slot(rows)
        val dt = if (rows > 0) time - t[slot(rows - 1)] else 0.1
        t[s] = time
        for (c in 0 until 3) {
            accS[3 * s + c] = accSample[c]; gyrS[3 * s + c] = gyrSample[c]
            accM[3 * s + c] = accMean[c]; gyrM[3 * s + c] = gyrMean[c]
        }
        tracker.step(accMean, gyrMean, dt)
        hq1[s] = tracker.q1
        hq2[s] = tracker.q2
        clockwise[s] = -tracker.verticalRate
        tiltBuf[s] = tracker.tiltRate
        if (rows + 1 >= MotionModel.WINDOW && (rows + 1 - MotionModel.WINDOW) % MotionModel.HOP == 0L) {
            val a = DoubleArray(3 * MotionModel.WINDOW)
            val g = DoubleArray(3 * MotionModel.WINDOW)
            for (k in 0 until MotionModel.WINDOW) {
                val w = slot(rows - MotionModel.WINDOW + 1 + k)
                for (c in 0 until 3) { a[3 * k + c] = accS[3 * w + c]; g[3 * k + c] = gyrS[3 * w + c] }
            }
            stationaryNow = model.isStationary(MotionModel.features(a, g))
        }
        stat[s] = stationaryOverride?.invoke(time) ?: stationaryNow
        rows++
        for (b in active) b.advanceTo(newest)
        return output()
    }

    /** Feeds one GNSS fix. During blackouts it only scores the estimates. */
    fun onFix(fix: Fix) {
        fixes.addLast(fix)
        while (fixes.size > 2 && fixes.first().t < fix.t - HISTORY_S) fixes.removeFirst()
        for (b in active) b.score(fix)
    }

    /** Calibrations the engines would use if a blackout started now — for showing readiness while GNSS works. */
    fun previewCalibration(): CalibrationPreview? {
        val fix = lastFix ?: return null
        val end = rowAtOrBefore(fix.t) ?: return null
        val h = history(end)
        val gyroFull = calibrate(h, end, full = true)
        return CalibrationPreview(calibrate(h, end, full = false), gyroFull, fitMount(h, gyroFull))
    }

    /** Starts a blackout from the last fix; null, with nothing changed, if there is no fix or no rows yet. */
    fun startBlackout(): Blackout? {
        val fix = lastFix ?: return null
        val i = rowAtOrBefore(fix.t) ?: return null
        val h = history(i)
        val cal = calibrate(h, i, full = false)
        val calFull = calibrate(h, i, full = true)
        val mount = fitMount(h, calFull)
        val headingRow = h.heading.last()
        val vRow = h.v.last()
        val course = when {
            !fix.bearing.isNaN() && (fix.speed.isNaN() || fix.speed >= 1.0) -> fix.bearing
            !headingRow.isNaN() -> headingRow
            else -> fixes.lastOrNull { !it.bearing.isNaN() && (it.speed.isNaN() || it.speed >= 1.0) }?.bearing ?: 0.0
        }
        val speed = if (!fix.speed.isNaN()) fix.speed else if (!vRow.isNaN()) vRow else 0.0
        val net = network?.takeIf { it.contains(fix.lat, fix.lon) }
        val b = Blackout(fix, i, Math.toRadians(course), speed, cal, calFull, mount, net)
        active += b
        b.advanceTo(newest)
        return b
    }

    /** Ends a blackout (by default the latest); the next fix is used as normal. Returns its final score. */
    fun endBlackout(b: Blackout? = latest): BlackoutScore? {
        if (b == null || !active.remove(b)) return null
        return b.current
    }

    private fun output(): LiveOutput {
        val s = slot(newest)
        latest?.last?.let { return it }
        val fix = lastFix
        return LiveOutput(
            t = t[s], inBlackout = false, stationary = stat[s],
            lat = fix?.lat ?: Double.NaN, lon = fix?.lon ?: Double.NaN,
            headingDeg = fix?.bearing?.takeIf { !it.isNaN() } ?: 0.0,
            speedKmh = (fix?.speed?.takeIf { !it.isNaN() } ?: 0.0) * 3.6,
            noMapLat = fix?.lat ?: Double.NaN, noMapLon = fix?.lon ?: Double.NaN,
            onMap = false, ess = Double.NaN, reseeds = 0
        )
    }

    private fun rowAtOrBefore(time: Double): Long? {
        if (rows == 0L) return null
        var r = newest
        while (r >= oldest && t[slot(r)] > time) r--
        return if (r >= oldest) r else null
    }

    /** History rows oldest..end with GNSS speed and course aligned to each row (linear between fixes, held after). */
    private class History(val first: Long, val t: DoubleArray, val v: DoubleArray, val heading: DoubleArray)

    private fun history(end: Long): History {
        val n = (end - oldest + 1).toInt()
        val tt = DoubleArray(n) { t[slot(oldest + it)] }
        val vv = DoubleArray(n) { Double.NaN }
        val hh = DoubleArray(n) { Double.NaN }
        var j = 0
        for (k in 0 until n) {
            val time = tt[k]
            if (fixes.isEmpty() || time < fixes.first().t) continue
            while (j + 1 < fixes.size && fixes[j + 1].t <= time) j++
            val a = fixes[j]
            if (j == fixes.size - 1 || a.t == time) { vv[k] = a.speed; hh[k] = a.bearing; continue }
            val b = fixes[j + 1]
            val f = (time - a.t) / (b.t - a.t)
            vv[k] = if (a.speed.isNaN() || b.speed.isNaN()) Double.NaN else a.speed + f * (b.speed - a.speed)
            hh[k] = when {
                a.bearing.isNaN() -> b.bearing
                b.bearing.isNaN() -> a.bearing
                else -> {
                    val d = Math.toDegrees(Geo.wrap(Math.toRadians(b.bearing - a.bearing)))
                    ((a.bearing + f * d) % 360.0 + 360.0) % 360.0
                }
            }
        }
        return History(oldest, tt, vv, hh)
    }

    /**
     * Gyro calibration on the history: round 2 uses step 2's free-axis fit on samples, as validated; the 248 Hz engine
     * the same window fit on its rotation about true vertical (TiltTracker), scale 1 until there are turns to fit.
     */
    private fun calibrate(h: History, end: Long, full: Boolean): GyroCalibration {
        val n = h.t.size
        val gyr = if (full) gyrM else gyrS
        val acc = if (full) accM else accS
        val gg = DoubleArray(3 * n)
        for (k in 0 until n) {
            val s = slot(h.first + k)
            for (c in 0 until 3) gg[3 * k + c] = gyr[3 * s + c]
        }
        if (full) {
            val cw = DoubleArray(n) { clockwise[slot(h.first + it)] }
            Calibration.vertical(h.t, cw, h.v, h.heading)?.let { return it }
            // not enough turning yet: scale 1, bias from the stops in the recent history
            val still = (0 until n).filter { stat[slot(h.first + it)] && cw[it].isFinite() }.takeLast(600)
            val bias = if (still.size >= 50) Calibration.median(DoubleArray(still.size) { cw[still[it]] }) else 0.0
            return GyroCalibration(doubleArrayOf(0.0, 0.0, 0.0), 1.0, bias, "vertical-default")
        } else {
            Calibration.engine(h.t, gg, h.v, h.heading)?.let { return it }
        }
        val m = minOf(n, 600)
        val aa = DoubleArray(3 * m); val g2 = DoubleArray(3 * m); val st = BooleanArray(m)
        for (k in 0 until m) {
            val s = slot(end - m + 1 + k)
            for (c in 0 until 3) { aa[3 * k + c] = acc[3 * s + c]; g2[3 * k + c] = gyr[3 * s + c] }
            st[k] = stat[s]
        }
        return Calibration.gravity(aa, g2, st) ?: GyroCalibration(doubleArrayOf(0.0, 0.0, -1.0), 1.0, 0.0, "none")
    }

    /** The vehicle's forward and right in TiltTracker's frame, from the recent history's turns and GPS speed. */
    private fun fitMount(h: History, cal: GyroCalibration): MountCalibration? {
        val n = h.t.size
        val q1 = DoubleArray(n) { hq1[slot(h.first + it)] }
        val q2 = DoubleArray(n) { hq2[slot(h.first + it)] }
        val turn = DoubleArray(n) { cal.turnRateVertical(clockwise[slot(h.first + it)]) }
        return MountCalibration.fit(h.t, q1, q2, turn, h.v)
    }

    inner class Blackout internal constructor(
        val fix: Fix, startRow: Long, course0: Double, val speed0: Double,
        val cal: GyroCalibration, val calFull: GyroCalibration, val mount: MountCalibration?, val net: RoadNetwork?
    ) {
        private val dr = DeadReckoning(course0, speed0)
        private val pf = net?.let { ParticleFilter(it, params, fix.lat, fix.lon, course0, speed0, rng) }
        private val drFull = DeadReckoning(course0, speed0)
        private val speedEstimator = mount?.let { SpeedEstimator(speed0, speedSettings) }
        private val pfFull = net?.let { ParticleFilter(it, params, fix.lat, fix.lon, course0, speed0, rng) }
        private val oracles = if (truth != null) Array(4) { DeadReckoning(course0, speed0) } else null
        private var tiltSum = 0.0
        private var tiltRows = 0
        private var row = startRow                         // the row the engine state belongs to
        var last: LiveOutput? = null; private set
        private val recent = ArrayDeque<LiveOutput>()
        private var truthDist = 0.0
        private var prevFix = fix
        var current = BlackoutScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, cal, net?.name, pf?.seeded ?: false,
            fullCalibration = calFull, mount = mount, gpsSpeedKmh = if (fix.speed.isNaN()) Double.NaN else fix.speed * 3.6)
            private set

        fun advanceTo(target: Long) {
            while (row < target) {
                val s = slot(row)
                val next = slot(row + 1)
                val dt = t[next] - t[s]

                // round 2, as validated: gyro samples, held speed
                val psiNow = dr.heading
                dr.step(cal.turnRate(gyrS[3 * s], gyrS[3 * s + 1], gyrS[3 * s + 2]), stat[s], dt)
                pf?.step(psiNow, dr.heading, stat[s], dt, dr.east, dr.north)
                val est = pf?.estimate(dr.east, dr.north, dr.dist) ?: doubleArrayOf(dr.east, dr.north, dr.dist, 0.0)

                // 248 Hz: rotation about true vertical, accelerometer speed
                val turnFull = calFull.turnRateVertical(clockwise[s]).let { if (it.isFinite()) it else 0.0 }
                val speedBefore = speedEstimator?.speed ?: speed0
                val psiFullNow = drFull.heading
                drFull.stepSpeed(turnFull, if (stat[s]) 0.0 else speedBefore, dt)
                if (speedEstimator != null && mount != null) {
                    speedEstimator.step(mount.forwardAcceleration(hq1[s], hq2[s]), mount.rightAcceleration(hq1[s], hq2[s]),
                        turnFull, stat[s], dt)
                }
                val change = speedEstimator?.let { it.speed - speedBefore } ?: Double.NaN
                pfFull?.step(psiFullNow, drFull.heading, stat[s], dt, drFull.east, drFull.north, change)
                val estFull = pfFull?.estimate(drFull.east, drFull.north, drFull.dist)
                    ?: doubleArrayOf(drFull.east, drFull.north, drFull.dist, 0.0)

                if (tiltBuf[s].isFinite()) { tiltSum += tiltBuf[s]; tiltRows++ }
                val oracleLatLon = oracles?.let { o ->
                    val tr = truth!!.invoke(t[s])
                    val engineSpeed = if (stat[s]) 0.0 else speedBefore
                    if (tr != null) {
                        o[0].stepSpeed(turnFull, if (tr[0] < 0.5) 0.0 else speedBefore, dt)   // true stops
                        o[1].stepSpeed(turnFull, tr[0], dt)                                    // true speed
                        o[2].stepWith(tr[1], engineSpeed, dt)                                   // true heading
                        o[3].stepWith(tr[1], tr[0], dt)                                         // both
                    }
                    DoubleArray(8) { k -> val ll = Geo.invEnu(o[k / 2].east, o[k / 2].north, fix.lat, fix.lon); ll[k % 2] }
                }
                row++
                val ll = Geo.invEnu(est[0], est[1], fix.lat, fix.lon)
                val nm = Geo.invEnu(dr.east, dr.north, fix.lat, fix.lon)
                val fl = Geo.invEnu(estFull[0], estFull[1], fix.lat, fix.lon)
                val fnm = Geo.invEnu(drFull.east, drFull.north, fix.lat, fix.lon)
                val out = LiveOutput(
                    t = t[next], inBlackout = true, stationary = stat[next],
                    lat = ll[0], lon = ll[1],
                    headingDeg = (Math.toDegrees(dr.heading) % 360.0 + 360.0) % 360.0,
                    speedKmh = if (stat[s]) 0.0 else speed0 * 3.6,
                    noMapLat = nm[0], noMapLon = nm[1],
                    onMap = est[3] > 0.5, ess = pf?.ess ?: Double.NaN, reseeds = pf?.reseeds ?: 0,
                    fullLat = fl[0], fullLon = fl[1],
                    fullHeadingDeg = (Math.toDegrees(drFull.heading) % 360.0 + 360.0) % 360.0,
                    fullSpeedKmh = (speedEstimator?.speed ?: speed0) * 3.6,
                    fullSpeedSigmaKmh = (speedEstimator?.sigma ?: Double.NaN) * 3.6,
                    fullNoMapLat = fnm[0], fullNoMapLon = fnm[1],
                    fullOnMap = estFull[3] > 0.5,
                    oracle = oracleLatLon
                )
                last = out
                recent.addLast(out)
                if (recent.size > RECENT_ROWS) recent.removeFirst()
                current = current.copy(elapsedS = t[next] - fix.t, engineDistanceM = est[2],
                    turnReadings = speedEstimator?.turnReadings ?: 0)
            }
        }

        /** A fix the engines may not use: how far each estimate at that moment was from it. */
        fun score(f: Fix) {
            if (f.t <= prevFix.t) return
            val sp0 = if (prevFix.speed.isNaN()) 0.0 else prevFix.speed
            val sp1 = if (f.speed.isNaN()) 0.0 else f.speed
            truthDist += (sp0 + sp1) / 2 * (f.t - prevFix.t)
            prevFix = f
            val at = recent.lastOrNull { it.t <= f.t } ?: recent.firstOrNull() ?: return
            val d = maxOf(truthDist, 1e-9)
            val drift = Geo.haversineM(at.lat, at.lon, f.lat, f.lon)
            val noMap = Geo.haversineM(at.noMapLat, at.noMapLon, f.lat, f.lon)
            val full = Geo.haversineM(at.fullLat, at.fullLon, f.lat, f.lon)
            val fullNoMap = Geo.haversineM(at.fullNoMapLat, at.fullNoMapLon, f.lat, f.lon)
            current = current.copy(
                trueDistanceM = truthDist,
                driftM = drift, driftPct = 100 * drift / d, noMapDriftM = noMap, noMapDriftPct = 100 * noMap / d,
                fullDriftM = full, fullDriftPct = 100 * full / d,
                fullNoMapDriftM = fullNoMap, fullNoMapDriftPct = 100 * fullNoMap / d,
                gpsSpeedKmh = if (f.speed.isNaN()) Double.NaN else f.speed * 3.6,
                oracleDriftPct = at.oracle?.let { o -> DoubleArray(4) { k -> 100 * Geo.haversineM(o[2 * k], o[2 * k + 1], f.lat, f.lon) / d } },
                tiltRateMean = if (tiltRows > 0) tiltSum / tiltRows else Double.NaN
            )
        }
    }

    /** The fix nearest in time to t — for tests and the recorder. */
    fun fixNear(time: Double): Fix? = fixes.minByOrNull { abs(it.t - time) }
}
