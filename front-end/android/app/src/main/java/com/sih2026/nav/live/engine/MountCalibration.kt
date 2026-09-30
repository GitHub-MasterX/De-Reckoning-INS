package com.sih2026.nav.live.engine

import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Which horizontal direction is the vehicle's forward and which its right, learned from GPS while it works — the
 * accelerometer's half of calibration.
 *
 * TiltTracker gives the accelerometer's horizontal part against true vertical in a frame (q1, q2) that follows the
 * phone's tilt but not the vehicle's turning. In that frame the vehicle's right is the direction the reading swings to in
 * turns — turning right at speed v and turn rate r (clockwise positive), it accelerates towards the right at v × r — and
 * forward is up × right. A scale and an offset map each onto the vehicle's own acceleration.
 *
 * The fit uses only the last RECENT_S of history, so a phone that shifted in a hand, a bag or a holder recovers, and it
 * is trusted only when the sideways fit is clearly good; otherwise the 248 Hz engine keeps the held GPS speed.
 * Every signal is averaged over ±1 s so the 1 Hz GPS and the 10 Hz rows describe the same stretch of riding.
 */
class MountCalibration(
    private val right: DoubleArray,         // (q1, q2) components of the vehicle's right
    private val forward: DoubleArray,       // (q1, q2) components of the vehicle's forward
    val scaleForward: Double,
    val offsetForward: Double,
    val scaleRight: Double,
    val offsetRight: Double,
    val turnSamples: Int,
    val rightFitR: Double
) {
    /** The vehicle's forward acceleration, m/s², from one row's horizontal reading. */
    fun forwardAcceleration(q1: Double, q2: Double) = (q1 * forward[0] + q2 * forward[1] - offsetForward) / scaleForward

    /** The vehicle's acceleration towards its right, m/s². */
    fun rightAcceleration(q1: Double, q2: Double) = (q1 * right[0] + q2 * right[1] - offsetRight) / scaleRight

    companion object {
        // the last 10 minutes of history, needing 12 turning samples (6 s of real turning): slow town riding rarely gave
        // 20 in 6 minutes. Chosen on the first ride (22.3% → 18.9% median drift at 1 km, within that ride's noise).
        @JvmStatic var RECENT_S = 600.0
        private const val HALF_WINDOW = 10              // ±1 s of 10 Hz rows
        private const val STEP = 5                      // one sample every 0.5 s
        private const val MIN_SPEED = 2.0               // m/s
        private const val TURN_ACCEL = 1.0              // m/s²: a sample counts as turning above this
        @JvmStatic var MIN_TURN_SAMPLES = 12
        const val MIN_FIT_R = 0.6                       // the sideways fit must explain the swing this well
        private const val MIN_SCALE = 0.6
        private const val MAX_SCALE = 1.5

        /** Why the last fit returned null, or how it went — for diagnostics and the screen. */
        @Volatile var lastReason = ""; private set

        fun dot(a: DoubleArray, b: DoubleArray) = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

        fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(
            a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]
        )

        fun unit(a: DoubleArray): DoubleArray {
            val n = sqrt(dot(a, a))
            return doubleArrayOf(a[0] / n, a[1] / n, a[2] / n)
        }

        /**
         * Fits on history rows, oldest first: t (s), q1 and q2 (TiltTracker's horizontal reading, m/s²), turn (rad/s,
         * clockwise, calibrated), v (GPS speed, m/s, NaN without a fix). Only rows within RECENT_S of the last are used.
         * Null, with lastReason saying why, when the fit is not clearly good.
         */
        fun fit(t: DoubleArray, q1: DoubleArray, q2: DoubleArray, turn: DoubleArray, v: DoubleArray): MountCalibration? {
            val n = t.size
            lastReason = "too little history"
            if (n < 4 * HALF_WINDOW) return null
            val from = t.indexOfFirst { it >= t[n - 1] - RECENT_S }.coerceAtLeast(0)

            val xtx = Array(3) { DoubleArray(3) }
            val xq1 = DoubleArray(3)
            val xq2 = DoubleArray(3)
            val samples = ArrayList<DoubleArray>()
            var turning = 0
            var r0 = from + HALF_WINDOW
            while (r0 < n - HALF_WINDOW) {
                val a = r0 - HALF_WINDOW
                val b = r0 + HALF_WINDOW
                if (v[a].isFinite() && v[b].isFinite() && v[r0].isFinite() && v[r0] > MIN_SPEED && t[b] > t[a]) {
                    var m1 = 0.0; var m2 = 0.0; var tr = 0.0; var ok = true
                    for (r in a..b) {
                        if (!(q1[r].isFinite() && q2[r].isFinite() && turn[r].isFinite())) { ok = false; break }
                        m1 += q1[r]; m2 += q2[r]; tr += turn[r]
                    }
                    if (ok) {
                        val m = (b - a + 1).toDouble()
                        m1 /= m; m2 /= m; tr /= m
                        val aFwd = (v[b] - v[a]) / (t[b] - t[a])
                        val aRight = v[r0] * tr
                        val row = doubleArrayOf(aFwd, aRight, 1.0)
                        for (p in 0 until 3) {
                            for (q in 0 until 3) xtx[p][q] += row[p] * row[q]
                            xq1[p] += row[p] * m1
                            xq2[p] += row[p] * m2
                        }
                        samples += doubleArrayOf(aFwd, aRight, m1, m2)
                        if (abs(aRight) >= TURN_ACCEL) turning++
                    }
                }
                r0 += STEP
            }
            lastReason = "only $turning turning samples in the last ${RECENT_S.toInt() / 60} min (need $MIN_TURN_SAMPLES)"
            if (turning < MIN_TURN_SAMPLES) return null
            lastReason = "fit singular"
            val c1 = solve3(xtx, xq1) ?: return null
            val c2 = solve3(xtx, xq2) ?: return null
            // how the reading moves with rightward acceleration, and with forward acceleration
            val mRight = doubleArrayOf(c1[1], c2[1])
            val sRight = sqrt(mRight[0] * mRight[0] + mRight[1] * mRight[1])
            if (sRight == 0.0) return null
            val y2 = doubleArrayOf(mRight[0] / sRight, mRight[1] / sRight)
            val x2 = doubleArrayOf(y2[1], -y2[0])                         // forward = up × right, in (q1, q2)
            var sForward = c1[0] * x2[0] + c2[0] * x2[1]
            if (sForward < 0.3 || sForward > 3.0) sForward = 1.0          // too little braking in the history to trust
            val offsetRight = c1[2] * y2[0] + c2[2] * y2[1]
            val offsetForward = c1[2] * x2[0] + c2[2] * x2[1]

            var sxy = 0.0; var sxx = 0.0; var syy = 0.0; var sx = 0.0; var sy = 0.0
            for (s in samples) {
                val pred = sRight * s[1]
                val meas = s[2] * y2[0] + s[3] * y2[1] - offsetRight
                sx += pred; sy += meas; sxy += pred * meas; sxx += pred * pred; syy += meas * meas
            }
            val ns = samples.size.toDouble()
            val corr = (sxy - sx * sy / ns) / sqrt(maxOf((sxx - sx * sx / ns) * (syy - sy * sy / ns), 1e-12))
            lastReason = "sideways scale %.2f, fit r %.2f, forward scale %.2f, %d turning of %d samples"
                .format(sRight, corr, sForward, turning, samples.size)
            if (sRight < MIN_SCALE || sRight > MAX_SCALE || corr < MIN_FIT_R) {
                lastReason = "not trusted: $lastReason"
                return null
            }
            return MountCalibration(y2, x2, sForward, offsetForward, sRight, offsetRight, turning, corr)
        }

        private fun solve3(aIn: Array<DoubleArray>, bIn: DoubleArray): DoubleArray? {
            val a = Array(3) { aIn[it].copyOf() }
            val b = bIn.copyOf()
            for (col in 0 until 3) {
                var piv = col
                for (r in col + 1 until 3) if (abs(a[r][col]) > abs(a[piv][col])) piv = r
                if (a[piv][col] == 0.0 || !a[piv][col].isFinite()) return null
                if (piv != col) {
                    val tmp = a[piv]; a[piv] = a[col]; a[col] = tmp
                    val tb = b[piv]; b[piv] = b[col]; b[col] = tb
                }
                for (r in col + 1 until 3) {
                    val f = a[r][col] / a[col][col]
                    for (c in col until 3) a[r][c] -= f * a[col][c]
                    b[r] -= f * b[col]
                }
            }
            val x = DoubleArray(3)
            for (r in 2 downTo 0) {
                var s = b[r]
                for (c in r + 1 until 3) s -= a[r][c] * x[c]
                x[r] = s / a[r][r]
            }
            return if (x.all { it.isFinite() }) x else null
        }
    }
}
