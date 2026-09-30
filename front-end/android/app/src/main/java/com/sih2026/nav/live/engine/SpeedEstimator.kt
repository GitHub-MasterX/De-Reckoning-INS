package com.sih2026.nav.live.engine

import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Speed during a blackout from the full-rate accelerometer, instead of holding the last GPS speed.
 *
 * A two-state Kalman filter: speed v (m/s) and a slowly wandering forward bias b (m/s²: sensor offset plus road slope).
 *   every row     v moves by the vehicle's forward acceleration minus b (TiltTracker + MountCalibration)
 *   every 2 s     if the vehicle turned steadily through them, its speed is its sideways acceleration divided by its
 *                 turn rate — an absolute reading that does not build up error; dense town riding turns often
 *   stopped       while the stop classifier says stationary, v is zero, and the accelerometer's forward reading
 *                 is the bias itself
 *   reported      the estimate only within 20 s of a reading — a corner, a stop, or the GPS speed at the start;
 *                 otherwise the held GPS speed, because integrated acceleration alone wanders on long straights
 *                 (first real ride)
 * Settings are first guesses from sensor physics. They are to be tuned on recorded drives, not trusted yet.
 */
class SpeedEstimator(private val v0: Double, private val p: Settings = Settings()) {

    data class Settings(
        val speedWalk: Double = 0.15,         // m/s per sqrt(s): what the forward acceleration fails to explain
        val biasWalk: Double = 0.01,          // m/s² per sqrt(s): slope changes
        val sigmaV0: Double = 0.3,            // m/s: the GPS speed at the start
        val sigmaBias0: Double = 0.08,        // m/s²: bias left after mount calibration
        val minTurnRate: Double = 0.10,       // rad/s: steady turning needed for a speed reading
        val maxTurnSpread: Double = 0.30,     // rad/s: how much the turn rate may change within the reading
        val sideNoise: Double = 0.3,          // m/s²: sideways acceleration noise after averaging
        val sideScaleError: Double = 0.08,    // share of the reading: body roll and lever arm
        val stoppedNoise: Double = 0.15,      // m/s²: forward reading noise while stopped (idle vibration)
        val readingRows: Int = ROWS_PER_READING, // rows averaged into one turn reading
        val heldSpeedSigma: Double = 0.0,     // m/s: the last GPS speed as a loose anchor every reading (0 = none)
        // s: how long a corner reading vouches for the estimate. Outside that the reported speed is the held GPS speed:
        // on the first real ride, integrated acceleration wandered on long straights with no corners to correct it.
        // 0 = always report the estimate.
        val confirmSeconds: Double = 20.0,
        val vMax: Double = 45.0
    )

    var v = v0; private set
    private var sinceReading = 0.0          // the GPS speed at the start is a reading too

    /** The speed to use: the estimate while a recent corner reading vouches for it, the held GPS speed otherwise. */
    val speed: Double get() = if (p.confirmSeconds <= 0.0 || sinceReading <= p.confirmSeconds || v == 0.0) v else v0
    val confirmed: Boolean get() = p.confirmSeconds <= 0.0 || sinceReading <= p.confirmSeconds
    var bias = 0.0; private set
    private var p00 = p.sigmaV0 * p.sigmaV0
    private var p01 = 0.0
    private var p11 = p.sigmaBias0 * p.sigmaBias0
    val sigma get() = sqrt(maxOf(p00, 0.0))

    var turnReadings = 0; private set
    var lastTurnSpeed = Double.NaN; private set

    // one-second accumulators
    private var rows = 0
    private var sumTurn = 0.0
    private var minTurn = Double.POSITIVE_INFINITY
    private var maxTurn = Double.NEGATIVE_INFINITY
    private var sumRight = 0.0
    private var sumForward = 0.0
    private var stoppedRows = 0

    /**
     * One 10 Hz row: the vehicle's forward and rightward acceleration (m/s², MountCalibration), its calibrated turn rate
     * (rad/s, clockwise), the stop flag, and the step to the next row (s).
     */
    fun step(aF: Double, aR: Double, turnRate: Double, stationary: Boolean, dt: Double) {
        val d = maxOf(dt, 0.0)
        sinceReading += d
        if (aF.isFinite() && !stationary) {
            v += (aF - bias) * d
            val q00 = p.speedWalk * p.speedWalk * d
            val q11 = p.biasWalk * p.biasWalk * d
            p00 = p00 - 2 * d * p01 + d * d * p11 + q00
            p01 = p01 - d * p11
            p11 = p11 + q11
        }
        if (stationary) {
            update(0.0, doubleArrayOf(1.0, 0.0), 0.05 * 0.05)
            v = 0.0
            sinceReading = 0.0                  // and so is standing still
        }

        rows++
        if (turnRate.isFinite()) {
            sumTurn += turnRate
            minTurn = minOf(minTurn, turnRate); maxTurn = maxOf(maxTurn, turnRate)
        }
        if (aR.isFinite()) sumRight += aR
        if (aF.isFinite()) sumForward += aF
        if (stationary) stoppedRows++
        if (rows == p.readingRows) {
            val r = sumTurn / rows
            val side = sumRight / rows
            if (stoppedRows == 0 && p.heldSpeedSigma > 0) {
                update(v0, doubleArrayOf(1.0, 0.0), p.heldSpeedSigma * p.heldSpeedSigma)   // the held speed, loosely
            }
            if (stoppedRows == rows && aF.isFinite()) {
                update(sumForward / rows, doubleArrayOf(0.0, 1.0), p.stoppedNoise * p.stoppedNoise)   // the bias itself
            } else if (stoppedRows == 0 && abs(r) >= p.minTurnRate && maxTurn - minTurn <= p.maxTurnSpread &&
                minTurn * maxTurn > 0) {
                val z = side / r
                if (z > 0.5 && z < p.vMax) {
                    val rVar = (p.sideNoise / abs(r)).let { it * it } + (p.sideScaleError * z).let { it * it }
                    if (abs(z - v) <= 3 * sqrt(p00 + rVar)) {
                        update(z, doubleArrayOf(1.0, 0.0), rVar)
                        sinceReading = 0.0
                        turnReadings++
                        lastTurnSpeed = z
                    }
                }
            }
            rows = 0; sumTurn = 0.0; sumRight = 0.0; sumForward = 0.0; stoppedRows = 0
            minTurn = Double.POSITIVE_INFINITY; maxTurn = Double.NEGATIVE_INFINITY
        }
        v = v.coerceIn(0.0, p.vMax)
    }

    /** Kalman update with a measurement z of h·[v, bias] and variance rVar. */
    private fun update(z: Double, h: DoubleArray, rVar: Double) {
        val ph0 = p00 * h[0] + p01 * h[1]
        val ph1 = p01 * h[0] + p11 * h[1]
        val s = h[0] * ph0 + h[1] * ph1 + rVar
        if (s <= 0) return
        val k0 = ph0 / s
        val k1 = ph1 / s
        val innovation = z - (h[0] * v + h[1] * bias)
        v += k0 * innovation
        bias += k1 * innovation
        val n00 = p00 - k0 * ph0
        val n01 = p01 - k0 * ph1
        val n11 = p11 - k1 * ph1
        p00 = n00; p01 = n01; p11 = n11
    }

    companion object {
        // two seconds: long enough that a phone wobbling in a hand averages out of the turn rate, short enough to fit
        // inside a corner (1 s and 3 s were worse across the simulated car, handlebar and hand-held rides)
        const val ROWS_PER_READING = 20
    }
}
