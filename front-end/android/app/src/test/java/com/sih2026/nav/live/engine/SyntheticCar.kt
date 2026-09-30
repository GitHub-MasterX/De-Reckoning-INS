package com.sih2026.nav.live.engine

import java.util.Random
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A simulated car with a phone in a tilted mount, for testing the 248 Hz engine where the truth is known.
 *
 * Gravity and a slowly changing 1.5% slope, accelerometer and gyro biases and noise, 27 Hz engine vibration, road
 * vibration at 12–90 Hz growing with speed, speed breakers (a sharp pitch and a vertical jolt), sensor events at 250 Hz
 * with timing jitter, and GPS once a second with 2 m position noise. It tests the code, not the roads.
 *
 *   leaning     a two-wheeler: it leans into every corner so the cornering force stays along its own vertical, and
 *               the phone rolls with it
 *   wobbleDeg   a phone in a hand or a bag: it tilts back and forth against the vehicle by this much
 */
class SyntheticCar(seed: Long, private val leaning: Boolean = false, private val wobbleDeg: Double = 0.0) {
    /** A piece of driving: how long, the acceleration towards a target speed, the turn rate (rad/s, clockwise). */
    data class Piece(val seconds: Double, val targetSpeed: Double, val accel: Double, val turn: Double)

    interface Sink {
        fun accelerometer(tNs: Long, x: Double, y: Double, z: Double)
        fun gyroscope(tNs: Long, x: Double, y: Double, z: Double)
        fun fix(fix: Fix)
        /** Called after each 4 ms step: time (s), true speed (m/s), true stopped state. */
        fun truth(time: Double, speed: Double, stopped: Boolean) {}
    }

    val rng = Random(seed)
    val mount = rotation(-10.0, 75.0, 30.0)
    private val accBias = doubleArrayOf(0.06, -0.04, 0.09)
    private val gyrBias = doubleArrayOf(0.002, -0.0015, 0.001)
    private val g = 9.80665
    private val dt = 0.004
    val lat0 = 10.93
    val lon0 = 78.75

    var time = 0.0; private set
    var speed = 0.0; private set
    var trip = 0.0; private set
    private var psi = 0.0
    private var east = 0.0
    private var north = 0.0
    private var nextFix = 1.0
    private var nextBump = Double.POSITIVE_INFINITY
    private var bumpT = -1.0
    var bumps = 0; private set
    private var lean = 0.0
    private val wobblePhase = DoubleArray(2) { rng.nextDouble() * 2 * PI }
    private val phases = DoubleArray(6) { rng.nextDouble() * 2 * PI }
    private val freqs = DoubleArray(6) { 12.0 + rng.nextDouble() * 78.0 }

    /** Speed breakers every `spacingM` metres of driving from now on. */
    fun speedBreakers(spacingM: Double) { nextBump = trip + spacingM; bumpSpacing = spacingM }
    private var bumpSpacing = 150.0

    fun drive(pieces: List<Piece>, sink: Sink) {
        for (piece in pieces) {
            var elapsed = 0.0
            while (elapsed < piece.seconds) {
                val a = when {
                    speed < piece.targetSpeed - 1e-6 -> minOf(piece.accel, (piece.targetSpeed - speed) / dt)
                    speed > piece.targetSpeed + 1e-6 -> -minOf(piece.accel, (speed - piece.targetSpeed) / dt)
                    else -> 0.0
                }
                speed = maxOf(0.0, speed + a * dt)
                val r = if (speed > 0.5) piece.turn else 0.0
                psi += r * dt
                east += speed * sin(psi) * dt
                north += speed * cos(psi) * dt
                trip += speed * dt
                time += dt
                elapsed += dt

                val grade = 0.015 * sin(2 * PI * time / 120.0)
                if (trip >= nextBump && speed > 2.0) { bumpT = 0.0; nextBump += bumpSpacing; bumps++ }
                var pitchRate = 0.0; var jolt = 0.0
                if (bumpT >= 0.0) {
                    pitchRate = if (bumpT < 0.3) 0.6 else -0.6
                    jolt = 4.0 * sin(PI * bumpT / 0.3)
                    bumpT += dt
                    if (bumpT >= 0.6) bumpT = -1.0
                }
                // a two-wheeler leans towards the lean that balances the cornering force, over about 0.4 s
                val previousLean = lean
                val target = if (leaning) kotlin.math.atan(speed * r / g) else 0.0
                lean += (target - lean) * dt / 0.4
                val leanRate = (lean - previousLean) / dt
                val wob = Math.toRadians(wobbleDeg)
                val wa = wob * sin(2 * PI * 0.35 * time + wobblePhase[0])
                val wb = wob * sin(2 * PI * 0.8 * time + wobblePhase[1])
                val waRate = wob * 2 * PI * 0.35 * cos(2 * PI * 0.35 * time + wobblePhase[0])
                val wbRate = wob * 2 * PI * 0.8 * cos(2 * PI * 0.8 * time + wobblePhase[1])
                val toBike = transpose(rotation(Math.toDegrees(lean), 0.0, 0.0))
                val toHand = transpose(rotation(Math.toDegrees(wa), Math.toDegrees(wb), 0.0))
                val fLevel = doubleArrayOf(a + g * sin(grade), -speed * r, g * cos(grade) + jolt)
                val fPhone = apply(mount, apply(toHand, apply(toBike, fLevel)))
                val wBike = apply(toBike, doubleArrayOf(0.0, -pitchRate, -r)).also { it[0] += leanRate }
                val wHand = apply(toHand, wBike).also { it[0] += waRate; it[1] += wbRate }
                val wPhone = apply(mount, wHand)
                val engine = 0.4 * sin(2 * PI * 27.0 * time)
                var road = 0.0
                for (k in 0 until 6) road += sin(2 * PI * freqs[k] * time + phases[k])
                road *= 0.35 * minOf(speed / 12.0, 1.3)
                val tNs = Math.round(time * 1e9) + (rng.nextGaussian() * 2e5).toLong()
                sink.accelerometer(tNs,
                    fPhone[0] + accBias[0] + engine * 0.6 + road + rng.nextGaussian() * 0.02,
                    fPhone[1] + accBias[1] + engine * 0.3 - road * 0.7 + rng.nextGaussian() * 0.02,
                    fPhone[2] + accBias[2] + engine * 0.7 + road * 0.5 + rng.nextGaussian() * 0.02)
                sink.gyroscope(tNs + 1,
                    wPhone[0] + gyrBias[0] + 0.01 * road + rng.nextGaussian() * 0.002,
                    wPhone[1] + gyrBias[1] - 0.008 * road + rng.nextGaussian() * 0.002,
                    wPhone[2] + gyrBias[2] + 0.004 * engine + rng.nextGaussian() * 0.002)
                sink.truth(time, speed, speed < 0.05)
                if (time >= nextFix) {
                    nextFix += 1.0
                    val ll = Geo.invEnu(east + rng.nextGaussian() * 2, north + rng.nextGaussian() * 2, lat0, lon0)
                    sink.fix(Fix(time, ll[0], ll[1], maxOf(0.0, speed + rng.nextGaussian() * 0.1),
                        if (speed >= 1.0) (Math.toDegrees(psi) + rng.nextGaussian() + 360) % 360 else Double.NaN, 3.0))
                }
            }
        }
    }

    /** Town driving to calibrate on: pull away, cruise, brake, a 90° corner, now and then a stop. */
    fun townLoop(blocks: Int = 12): List<Piece> {
        val out = ArrayList<Piece>()
        repeat(blocks) { k ->
            val cruise = 9.0 + rng.nextDouble() * 5.0
            out += Piece(8.0, cruise, 1.5, 0.0)
            out += Piece(6.0 + rng.nextDouble() * 6, cruise, 0.0, 0.0)
            out += Piece(4.0, 6.0, 2.0, 0.0)
            out += Piece(PI / 2 / 0.35, 6.0, 0.0, if (rng.nextBoolean()) 0.35 else -0.35)
            if (k % 4 == 3) {
                out += Piece(4.0, 0.0, 2.0, 0.0)
                out += Piece(8.0, 0.0, 0.0, 0.0)
            }
        }
        return out
    }

    /** Slow town streets at about 34 km/h: corners every ~100 m, a stop halfway. */
    fun slowTown(blocks: Int = 9): List<Piece> {
        val out = ArrayList<Piece>()
        repeat(blocks) { k ->
            out += Piece(7.0 + rng.nextDouble() * 3, 9.5, 1.5, 0.0)
            out += Piece(PI / 2 / 0.4, 9.0, 0.5, if (k % 2 == 0) 0.4 else -0.4)
            if (k == blocks / 2) {
                out += Piece(4.0, 0.0, 2.5, 0.0)
                out += Piece(10.0, 0.0, 0.0, 0.0)
                out += Piece(6.0, 9.5, 1.6, 0.0)
            }
        }
        return out
    }

    companion object {
        /** Car-to-phone rotation from roll, pitch, yaw in degrees: phone axes = R · car axes (x forward, y left, z up). */
        fun rotation(rollDeg: Double, pitchDeg: Double, yawDeg: Double): Array<DoubleArray> {
            val (a, b, c) = listOf(rollDeg, pitchDeg, yawDeg).map { Math.toRadians(it) }
            val rx = arrayOf(doubleArrayOf(1.0, 0.0, 0.0), doubleArrayOf(0.0, cos(a), -sin(a)), doubleArrayOf(0.0, sin(a), cos(a)))
            val ry = arrayOf(doubleArrayOf(cos(b), 0.0, sin(b)), doubleArrayOf(0.0, 1.0, 0.0), doubleArrayOf(-sin(b), 0.0, cos(b)))
            val rz = arrayOf(doubleArrayOf(cos(c), -sin(c), 0.0), doubleArrayOf(sin(c), cos(c), 0.0), doubleArrayOf(0.0, 0.0, 1.0))
            fun mul(p: Array<DoubleArray>, q: Array<DoubleArray>) = Array(3) { i -> DoubleArray(3) { j -> (0 until 3).sumOf { p[i][it] * q[it][j] } } }
            return mul(rx, mul(ry, rz))
        }

        fun transpose(r: Array<DoubleArray>) = Array(3) { i -> DoubleArray(3) { j -> r[j][i] } }

        fun apply(r: Array<DoubleArray>, v: DoubleArray) = DoubleArray(3) { i -> r[i][0] * v[0] + r[i][1] * v[1] + r[i][2] * v[2] }

        fun angleDeg(a: DoubleArray, b: DoubleArray) = Math.toDegrees(kotlin.math.acos(
            (MountCalibration.dot(a, b) / sqrt(MountCalibration.dot(a, a) * MountCalibration.dot(b, b))).coerceIn(-1.0, 1.0)))
    }
}
