package com.sih2026.nav.live.engine

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Gyro calibration from GNSS history only — a port of round2/core/calibration.py with step 2's choice ("window").
 *
 * Turn-rate model:  turn = scale × (gyro · axis) − bias   (rad/s, clockwise positive like a compass course)
 *
 *   window fit   axis, scale and bias from the turning accumulated over 10 s windows while moving above 5 m/s;
 *                needs at least 5 windows, 3 of them with a real turn of 20° or more
 *   rate fit     the fallback: axis from the 10 Hz course rate, scale 1, bias from a median; needs 30 s moving
 *   gravity      phone-only last resort before either fit is possible: on Android the accelerometer and gyroscope
 *                share one frame, so the vertical is known from gravity; scale 1, bias from recent stops
 */
data class GyroCalibration(
    val axis: DoubleArray,
    val scale: Double,
    val bias: Double,
    val method: String,
    val turnWindows: Int = 0,
    val fitSeconds: Double = 0.0
) {
    fun turnRate(gx: Double, gy: Double, gz: Double) = scale * (gx * axis[0] + gy * axis[1] + gz * axis[2]) - bias

    /** For "vertical-window": the turn rate from a clockwise rotation about true vertical (TiltTracker), rad/s. */
    fun turnRateVertical(clockwise: Double) = scale * clockwise - bias
}

object Calibration {
    const val FS = 10.0
    private const val FIT_MIN_SPEED = 5.0
    // the 248 Hz engine's fit also learns at town speeds: a two-wheeler's 10 s stretches rarely stay above 18 km/h, and
    // GPS course over 10 s is still sound at 9 km/h (the second ride calibrated never at 18). Round 2 keeps 5 m/s.
    @JvmStatic var VERTICAL_MIN_SPEED = 2.5
    private const val HOLD_BELOW = 1.0
    private const val STOPPED_SPEED = 0.3
    private const val STRAIGHT_RATE = 0.02
    private const val MIN_FIT_S = 30.0
    private const val WINDOW_ROWS = 100
    private val TURN_WINDOW_RAD = Math.toRadians(20.0)
    private const val MIN_TURN_WINDOWS = 3

    /**
     * The calibration the engine uses for a blackout starting at the last history row.
     * t, gyr (n × 3, row by row), v (m/s) and heading (degrees) are the history rows, oldest first; v and heading
     * are GNSS values aligned to the rows, NaN where there was no fix.
     */
    fun engine(t: DoubleArray, gyr: DoubleArray, v: DoubleArray, heading: DoubleArray): GyroCalibration? {
        val h = History(t, gyr, v, heading)
        val i = t.size - 1
        val rate = h.rateFit(i)
        return h.windowFit(i) ?: rate
    }

    /**
     * The window fit on the phone's rotation about true vertical, as TiltTracker follows it row by row — for Android,
     * where the accelerometer and gyroscope share one frame. The free-axis fit above had to be used on IO-VNBD, whose
     * logger mixed axis conventions; with a free axis, riding that only turns about the vertical leaves the other two
     * directions undetermined, a speed breaker's pitch can read as a turn, and a two-wheeler's lean tilts the axis
     * through every corner. Here only scale and bias are fitted: course change over each 10 s window =
     * scale × rotation about vertical − bias × duration. `clockwise` holds −(gyro · up) for each history row, rad/s.
     */
    fun vertical(t: DoubleArray, clockwise: DoubleArray, v: DoubleArray, heading: DoubleArray,
                 minSpeed: Double = VERTICAL_MIN_SPEED): GyroCalibration? {
        val n = t.size
        val gyr = DoubleArray(3 * n) { if (it % 3 == 0) clockwise[it / 3] else 0.0 }
        val h = History(t, gyr, v, heading, minSpeed)
        val dt = DoubleArray(n) { if (it < n - 1) maxOf(t[it + 1] - t[it], 0.0) else 0.0 }
        val cg = DoubleArray(n + 1)
        val ct = DoubleArray(n + 1)
        val bad = IntArray(n + 1)
        for (r in 0 until n) {
            cg[r + 1] = cg[r] + (if (h.ok[r]) clockwise[r] else 0.0) * dt[r]
            ct[r + 1] = ct[r] + dt[r]
            bad[r + 1] = bad[r] + if (h.fit[r]) 0 else 1
        }
        var sgg = 0.0; var sgt = 0.0; var stt = 0.0; var sgy = 0.0; var sty = 0.0
        var m = 0
        var turns = 0
        var a = 0
        val i = n - 1
        while (a < n - WINDOW_ROWS) {
            val b = a + WINDOW_ROWS
            if (b > i) break
            if (bad[b] == bad[a]) {
                val x = cg[b] - cg[a]
                val d = ct[b] - ct[a]
                val y = h.psi[b] - h.psi[a]
                sgg += x * x; sgt += x * d; stt += d * d; sgy += x * y; sty += d * y
                m++
                if (abs(y) >= TURN_WINDOW_RAD) turns++
            }
            a += WINDOW_ROWS
        }
        if (m < 5 || turns < MIN_TURN_WINDOWS) return null
        // y = scale·x + c·d, c = −bias
        val det = sgg * stt - sgt * sgt
        if (det == 0.0 || !det.isFinite()) return null
        val scale = (sgy * stt - sty * sgt) / det
        val c = (sty * sgg - sgy * sgt) / det
        if (!scale.isFinite() || scale <= 0.0) return null
        return GyroCalibration(doubleArrayOf(0.0, 0.0, 0.0), scale, -c, "vertical-window", turns, m * WINDOW_ROWS / FS)
    }

    /** Vertical from gravity, clockwise positive: acc holds recent rows (n × 3); stationary flags choose bias rows. */
    fun gravity(acc: DoubleArray, gyr: DoubleArray, stationary: BooleanArray): GyroCalibration? {
        val n = acc.size / 3
        if (n < 20) return null
        var sx = 0.0; var sy = 0.0; var sz = 0.0
        for (r in 0 until n) { sx += acc[3 * r]; sy += acc[3 * r + 1]; sz += acc[3 * r + 2] }
        val norm = sqrt(sx * sx + sy * sy + sz * sz)
        if (norm == 0.0) return null
        val axis = doubleArrayOf(-sx / norm, -sy / norm, -sz / norm)
        val still = (0 until n).filter { stationary[it] }
        val bias = if (still.size >= 50)
            median(DoubleArray(still.size) { k -> val r = still[k]; gyr[3 * r] * axis[0] + gyr[3 * r + 1] * axis[1] + gyr[3 * r + 2] * axis[2] })
        else 0.0
        return GyroCalibration(axis, 1.0, bias, "gravity")
    }

    internal fun median(a: DoubleArray): Double {
        val s = a.sortedArray()
        val m = s.size / 2
        return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) / 2
    }

    private class History(val t: DoubleArray, val gyr: DoubleArray, val v: DoubleArray, heading: DoubleArray,
                          minSpeed: Double = FIT_MIN_SPEED) {
        val n = t.size
        val psi = DoubleArray(n)
        val rate = DoubleArray(n)
        val ok = BooleanArray(n) { r -> gyr[3 * r].isFinite() && gyr[3 * r + 1].isFinite() && gyr[3 * r + 2].isFinite() }
        val fit = BooleanArray(n) { ok[it] && v[it] > minSpeed }

        init {
            // course(): heading while moving, held (ffill, then bfill) while nearly stopped, unwrapped
            val hd = DoubleArray(n) { if (v[it] >= HOLD_BELOW) heading[it] else Double.NaN }
            var last = Double.NaN
            for (r in 0 until n) { if (hd[r].isNaN()) hd[r] = last else last = hd[r] }
            var next = Double.NaN
            for (r in n - 1 downTo 0) { if (hd[r].isNaN()) hd[r] = next else next = hd[r] }
            val p = DoubleArray(n) { Math.toRadians(hd[it]) }
            // np.unwrap
            var correction = 0.0
            if (n > 0) psi[0] = p[0]
            for (r in 1 until n) {
                val dd = p[r] - p[r - 1]
                var ddmod = floorMod(dd + PI, 2 * PI) - PI
                if (ddmod == -PI && dd > 0) ddmod = PI
                var ph = ddmod - dd
                if (abs(dd) < PI) ph = 0.0
                correction += ph
                psi[r] = p[r] + correction
            }
            // np.gradient * FS
            if (n >= 2) {
                rate[0] = (psi[1] - psi[0]) * FS
                rate[n - 1] = (psi[n - 1] - psi[n - 2]) * FS
                for (r in 1 until n - 1) rate[r] = (psi[r + 1] - psi[r - 1]) / 2.0 * FS
            }
        }

        /** numpy's float modulo: exact fmod, moved to the sign of the divisor. */
        private fun floorMod(a: Double, b: Double): Double {
            var m = a % b
            if (m != 0.0 && (b < 0) != (m < 0)) m += b
            return m
        }

        fun biasOk(r: Int) = ok[r] && (v[r] < STOPPED_SPEED || (v[r] > FIT_MIN_SPEED && abs(rate[r]) < STRAIGHT_RATE))

        private fun recentBias(end: Int, axis: DoubleArray, scale: Double): Double? {
            val vals = ArrayList<Double>()
            for (r in 0 until end) {
                if (!biasOk(r)) continue
                val target = if (v[r] < STOPPED_SPEED) 0.0 else rate[r]
                vals += scale * (gyr[3 * r] * axis[0] + gyr[3 * r + 1] * axis[1] + gyr[3 * r + 2] * axis[2]) - target
            }
            if (vals.size < 50) return null
            return median(vals.toDoubleArray())
        }

        /** Calibrator.at(i, axis_window_s=None, bias_window_s=1e9). */
        fun rateFit(i: Int): GyroCalibration? {
            val end = maxOf(i - 1, 0)
            val xtx = Array(4) { DoubleArray(4) }
            val xty = DoubleArray(4)
            var count = 0
            val x = DoubleArray(4)
            for (r in 0 until end) {
                if (!fit[r]) continue
                x[0] = gyr[3 * r]; x[1] = gyr[3 * r + 1]; x[2] = gyr[3 * r + 2]; x[3] = 1.0
                for (a in 0 until 4) {
                    for (b in 0 until 4) xtx[a][b] += x[a] * x[b]
                    xty[a] += x[a] * rate[r]
                }
                count++
            }
            if (count < MIN_FIT_S * FS) return null
            val c = solve4(xtx, xty) ?: return null
            val norm = sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2])
            if (!norm.isFinite() || norm == 0.0) return null
            val axis = doubleArrayOf(c[0] / norm, c[1] / norm, c[2] / norm)
            val bias = recentBias(end, axis, 1.0) ?: return null
            return GyroCalibration(axis, 1.0, bias, "rate", 0, count / FS)
        }

        /** Calibrator.at_windows(i): the 10 s windows laid from the first history row, ending by row i. */
        fun windowFit(i: Int): GyroCalibration? {
            val dt = DoubleArray(n) { if (it < n - 1) maxOf(t[it + 1] - t[it], 0.0) else 0.0 }
            val cg = Array(n + 1) { DoubleArray(3) }
            val ct = DoubleArray(n + 1)
            val bad = IntArray(n + 1)
            for (r in 0 until n) {
                val gx = if (ok[r]) gyr[3 * r] else 0.0
                val gy = if (ok[r]) gyr[3 * r + 1] else 0.0
                val gz = if (ok[r]) gyr[3 * r + 2] else 0.0
                cg[r + 1][0] = cg[r][0] + gx * dt[r]
                cg[r + 1][1] = cg[r][1] + gy * dt[r]
                cg[r + 1][2] = cg[r][2] + gz * dt[r]
                ct[r + 1] = ct[r] + dt[r]
                bad[r + 1] = bad[r] + if (fit[r]) 0 else 1
            }
            val xtx = Array(4) { DoubleArray(4) }
            val xty = DoubleArray(4)
            var m = 0
            var turns = 0
            val x = DoubleArray(4)
            var a = 0
            while (a < n - WINDOW_ROWS) {
                val b = a + WINDOW_ROWS
                if (b > i) break
                if (bad[b] == bad[a]) {
                    x[0] = cg[b][0] - cg[a][0]; x[1] = cg[b][1] - cg[a][1]; x[2] = cg[b][2] - cg[a][2]
                    x[3] = ct[b] - ct[a]
                    val y = psi[b] - psi[a]
                    for (p in 0 until 4) {
                        for (q in 0 until 4) xtx[p][q] += x[p] * x[q]
                        xty[p] += x[p] * y
                    }
                    m++
                    if (abs(y) >= TURN_WINDOW_RAD) turns++
                }
                a += WINDOW_ROWS
            }
            if (m < 5 || turns < MIN_TURN_WINDOWS) return null
            val c = solve4(xtx, xty) ?: return null
            val scale = sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2])
            if (!scale.isFinite() || scale == 0.0) return null
            return GyroCalibration(
                doubleArrayOf(c[0] / scale, c[1] / scale, c[2] / scale), scale, -c[3], "window",
                turns, m * WINDOW_ROWS / FS
            )
        }
    }

    /** Solves the 4 × 4 normal equations by Gaussian elimination with partial pivoting; null if singular. */
    internal fun solve4(aIn: Array<DoubleArray>, bIn: DoubleArray): DoubleArray? {
        val a = Array(4) { aIn[it].copyOf() }
        val b = bIn.copyOf()
        for (col in 0 until 4) {
            var piv = col
            for (r in col + 1 until 4) if (abs(a[r][col]) > abs(a[piv][col])) piv = r
            if (a[piv][col] == 0.0 || !a[piv][col].isFinite()) return null
            if (piv != col) {
                val tmp = a[piv]; a[piv] = a[col]; a[col] = tmp
                val tb = b[piv]; b[piv] = b[col]; b[col] = tb
            }
            for (r in col + 1 until 4) {
                val f = a[r][col] / a[col][col]
                for (c in col until 4) a[r][c] -= f * a[col][c]
                b[r] -= f * b[col]
            }
        }
        val x = DoubleArray(4)
        for (r in 3 downTo 0) {
            var s = b[r]
            for (c in r + 1 until 4) s -= a[r][c] * x[c]
            x[r] = s / a[r][r]
        }
        return if (x.all { it.isFinite() }) x else null
    }
}
