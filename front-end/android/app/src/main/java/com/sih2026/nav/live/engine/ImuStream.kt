package com.sih2026.nav.live.engine

/**
 * Turns the phone's full-rate sensor events (about 250 Hz) into the engine's 10 Hz rows — the same code on the phone
 * (LiveSensors) and when a recorded drive is replayed on a computer, so both see identical rows.
 *
 * Each row carries two views of the same 100 ms:
 *   sample   the latest accelerometer and gyroscope sample at the tick, as a phone logging at 10 Hz keeps it. Round 1's
 *            stop classifier and the round-2 engine were built on exactly this, vibration folded in and all.
 *   mean     the time-weighted mean over every sample since the previous row. The gyro mean is the exact rotation of
 *            the interval divided by its length, so heading integrates every sample; the accelerometer mean averages
 *            away road and engine vibration (10–100 Hz) that a single sample would fold into the vehicle's own
 *            0–2 Hz acceleration. This is what the 248 Hz engine reads.
 *
 * Rows tick on the gyroscope's clock every 100 ms; a gap in the stream restarts the ticking.
 */
class ImuStream(private val onRow: (Row) -> Unit) {

    class Row(
        val tNs: Long,
        val accSample: DoubleArray,
        val gyrSample: DoubleArray,
        val accMean: DoubleArray,
        val gyrMean: DoubleArray,
        val accCount: Int,
        val gyrCount: Int
    )

    private val lastAcc = DoubleArray(3)
    private var haveAcc = false
    private var lastAccT = 0L
    private val accSum = DoubleArray(3)
    private var accWeight = 0.0
    private var accCount = 0

    private var lastGyrT = 0L
    private val gyrSum = DoubleArray(3)
    private var gyrWeight = 0.0
    private var gyrCount = 0

    private var nextTickNs = 0L
    private var lastRowT = 0L

    fun accelerometer(t: Long, x: Double, y: Double, z: Double) {
        if (haveAcc && t > lastAccT) {
            val w = (t - lastAccT) / 1e9                    // each sample stands for the time since the one before
            accSum[0] += x * w; accSum[1] += y * w; accSum[2] += z * w
            accWeight += w
        }
        lastAcc[0] = x; lastAcc[1] = y; lastAcc[2] = z
        lastAccT = t
        haveAcc = true
        accCount++
    }

    fun gyroscope(t: Long, x: Double, y: Double, z: Double) {
        if (lastGyrT != 0L && t > lastGyrT) {
            val w = (t - lastGyrT) / 1e9
            gyrSum[0] += x * w; gyrSum[1] += y * w; gyrSum[2] += z * w
            gyrWeight += w
        }
        lastGyrT = t
        gyrCount++
        if (!haveAcc) return
        if (nextTickNs == 0L) nextTickNs = t
        if (t < nextTickNs) return
        val sample = doubleArrayOf(x, y, z)
        val row = Row(
            tNs = t,
            accSample = lastAcc.copyOf(),
            gyrSample = sample,
            accMean = if (accWeight > 0) DoubleArray(3) { accSum[it] / accWeight } else lastAcc.copyOf(),
            gyrMean = if (gyrWeight > 0) DoubleArray(3) { gyrSum[it] / gyrWeight } else sample.copyOf(),
            accCount = accCount,
            gyrCount = gyrCount
        )
        accSum.fill(0.0); accWeight = 0.0; accCount = 0
        gyrSum.fill(0.0); gyrWeight = 0.0; gyrCount = 0
        lastRowT = t
        nextTickNs += ROW_NS
        if (nextTickNs <= t) nextTickNs = t + ROW_NS          // a gap in the stream: start ticking again from here
        onRow(row)
    }

    companion object {
        const val ROW_NS = 100_000_000L
    }
}
