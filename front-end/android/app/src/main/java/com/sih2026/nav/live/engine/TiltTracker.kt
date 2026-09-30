package com.sih2026.nav.live.engine

import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Follows which way is up in the phone's frame, row by row — so the accelerometer can be read against true vertical
 * even when the phone tilts: a two-wheeler leaning into a corner, a phone in a hand or a bag, a holder that flexes.
 *
 *   every row     up (and a horizontal reference direction) turn with the gyro's rotation about horizontal axes.
 *                 Rotation about the vertical is the vehicle turning, not the phone tilting, so it is left out.
 *   when steady   (magnitude near g, hardly turning) the gravity mismatch pulls up back over about 30 s and teaches the
 *                 gyro's own offset (a Mahony filter), slowly enough that speeding up and braking average out
 *
 * Outputs for each row, in a horizontal frame that tilts with nothing:
 *   horizontal    the accelerometer's horizontal part along the reference direction (q1) and across it (q2), m/s²
 *   verticalRate  rotation about true vertical, rad/s, anticlockwise positive (the raw material of heading)
 * A leaning two-wheeler's accelerometer shows almost no sideways force in its own frame — the lean aligns it with the
 * force — but against true vertical the cornering force is all there.
 */
class TiltTracker {
    private var up = DoubleArray(3)
    private val gyroBias = DoubleArray(3)
    private var ref = DoubleArray(3)
    private var initialised = false
    private val start = DoubleArray(3)
    private var startRows = 0

    var q1 = Double.NaN; private set
    var q2 = Double.NaN; private set
    var verticalRate = Double.NaN; private set
    /** Rotation about horizontal axes, rad/s: a hand or a bag moving the phone, a bike leaning, a bump. */
    var tiltRate = Double.NaN; private set

    fun step(accMean: DoubleArray, gyrMean: DoubleArray, dt: Double) {
        if (!(accMean.all { it.isFinite() } && gyrMean.all { it.isFinite() })) return
        if (!initialised) {                                        // up starts as the first second's average
            for (c in 0 until 3) start[c] += accMean[c]
            if (++startRows < START_ROWS) return
            up = MountCalibration.unit(start)
            val k = (0 until 3).minByOrNull { abs(up[it]) }!!
            val axis = DoubleArray(3).also { it[k] = 1.0 }
            ref = MountCalibration.unit(MountCalibration.cross(up, axis))
            initialised = true
        }
        val d = maxOf(0.0, minOf(dt, 1.0))
        val g = sqrt(MountCalibration.dot(accMean, accMean))
        val wRaw = MountCalibration.dot(gyrMean, up)
        // gravity mismatch while steady: the rotation that would carry up onto the accelerometer's direction
        val steady = abs(g - GRAVITY) < STEADY_G && abs(wRaw) < STEADY_TURN && g > 0
        val mismatch = if (steady) MountCalibration.cross(up, DoubleArray(3) { accMean[it] / g }) else DoubleArray(3)
        for (c in 0 until 3) gyroBias[c] += KI * mismatch[c] * d     // learns the gyro's offset about horizontal axes
        val w = DoubleArray(3) { gyrMean[it] - gyroBias[it] - KP * mismatch[it] }
        val wUp = MountCalibration.dot(w, up)
        val tilt = DoubleArray(3) { w[it] - wUp * up[it] }           // rotation about horizontal axes only
        tiltRate = sqrt(MountCalibration.dot(tilt, tilt))
        up = MountCalibration.unit(rotate(up, tilt, -d))
        ref = rotate(ref, tilt, -d)
        val along = MountCalibration.dot(ref, up)
        ref = MountCalibration.unit(DoubleArray(3) { ref[it] - along * up[it] })
        val across = MountCalibration.cross(ref, up)
        val vertical = MountCalibration.dot(accMean, up)
        val h = DoubleArray(3) { accMean[it] - vertical * up[it] }
        q1 = MountCalibration.dot(h, ref)
        q2 = MountCalibration.dot(h, across)
        verticalRate = MountCalibration.dot(gyrMean, up)
    }

    companion object {
        const val GRAVITY = 9.80665
        private const val START_ROWS = 10
        // A Mahony filter on the tilt: the gyro carries up; while steady the gravity mismatch pulls it back (KP) and
        // teaches the gyro's offset (KI). The pull is slow — speeding up or braking barely changes the reading's
        // magnitude (1.5 m/s² forward adds 0.11 m/s² to 9.81) but tilts its direction by 9°, so a fast pull would lean
        // up into every acceleration; over 30 s those average out. Critically damped: KI = KP² / 4.
        private const val TAU = 30.0
        private const val KP = 1.0 / TAU
        private const val KI = KP * KP / 4
        private const val STEADY_G = 0.3         // m/s²: magnitude within this of g counts as steady
        private const val STEADY_TURN = 0.05     // rad/s: and hardly turning

        /** v rotated about axis w (rad/s) for time s: Rodrigues' formula with rotation vector w·s. */
        fun rotate(v: DoubleArray, w: DoubleArray, s: Double): DoubleArray {
            val rx = w[0] * s; val ry = w[1] * s; val rz = w[2] * s
            val theta = sqrt(rx * rx + ry * ry + rz * rz)
            if (theta < 1e-12) return v.copyOf()
            val k = doubleArrayOf(rx / theta, ry / theta, rz / theta)
            val kxv = MountCalibration.cross(k, v)
            val kv = MountCalibration.dot(k, v)
            val c = cos(theta); val sn = sin(theta)
            return DoubleArray(3) { v[it] * c + kxv[it] * sn + k[it] * kv * (1 - c) }
        }
    }
}
