package com.sih2026.nav.live.engine

import kotlin.math.cos
import kotlin.math.sin

/**
 * Map-free 2D dead reckoning, stepped one 10 Hz row at a time — round2/core/deadreckoning.py.
 *
 *   heading   last GNSS course + turning from the calibrated gyro
 *   speed     last GNSS speed, held; zero while the motion classifier says stationary
 *   position  speed × heading on the phone clock
 *
 * Sums run in the same order as Python's cumulative sums, so the positions agree to rounding.
 */
class DeadReckoning(private val course0: Double, private val speed0: Double) {
    private var turnSum = 0.0
    var east = 0.0; private set
    var north = 0.0; private set
    var dist = 0.0; private set

    /** Heading of the current row, radians clockwise from north. */
    var heading = course0; private set

    /**
     * Moves from the current row to the next: `turnRate` (rad/s) and `stationary` belong to the current row,
     * `dt` is the clock step to the next row.
     */
    fun step(turnRate: Double, stationary: Boolean, dt: Double) = stepSpeed(turnRate, if (stationary) 0.0 else speed0, dt)

    /** The same step with a speed of the caller's (m/s) — the 248 Hz engine's estimate instead of the held one. */
    fun stepSpeed(turnRate: Double, speed: Double, dt: Double) {
        val d = maxOf(dt, 0.0)
        val step = speed * d
        east += step * sin(heading)
        north += step * cos(heading)
        dist += step
        turnSum += turnRate * d
        heading = course0 + turnSum
    }

    /** Analysis only: a step along a heading given from outside (e.g. the true GPS course), radians. */
    fun stepWith(headingNow: Double, speed: Double, dt: Double) {
        val step = speed * maxOf(dt, 0.0)
        east += step * sin(headingNow)
        north += step * cos(headingNow)
        dist += step
        heading = headingNow
    }
}
