package com.sih2026.nav.live.engine

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.zip.GZIPOutputStream
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * The 248 Hz engine on simulated drives whose truth is known (SyntheticCar). These check the code, not the roads:
 * accuracy on real streets can only come from recorded drives.
 */
class SyntheticDriveTest {
    private val model by lazy { MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes()) }

    /**
     * Eight minutes of town driving teach calibration; then a blackout starts at 61 km/h, brakes to 34 km/h and drives
     * on through corners every ~100 m, a stop and speed breakers every 150 m — the shape of Driver A's slow-town clips.
     */
    @Test
    fun accelerometerSpeedFixesTheHeldSpeedOnASimulatedSlowTown() = slowTownBlackout(SyntheticCar(7), "car, fixed mount")

    /** The same ride on a two-wheeler that leans into every corner, the phone on a handlebar mount. */
    @Test
    fun twoWheelerLeaningWithAHandlebarMount() = slowTownBlackout(SyntheticCar(9, leaning = true), "two-wheeler, leaning, handlebar mount")

    /** The same ride on a two-wheeler that leans into every corner, the phone wobbling ±4° in a hand or a bag. */
    @Test
    fun twoWheelerLeaningWithAPhoneInHand() = slowTownBlackout(SyntheticCar(9, leaning = true, wobbleDeg = 4.0), "two-wheeler, leaning, phone wobbling ±4°")

    /**
     * Eight minutes of town driving teach calibration; then a blackout starts at 61 km/h, brakes to 34 km/h and drives
     * on through corners every ~100 m, a stop and speed breakers every 150 m — the shape of Driver A's slow-town clips.
     */
    private fun slowTownBlackout(car: SyntheticCar, label: String) {
        val settings = SpeedEstimator.Settings(
            readingRows = System.getProperty("readingRows")?.takeIf { it.isNotEmpty() }?.toInt() ?: SpeedEstimator.ROWS_PER_READING,
            maxTurnSpread = System.getProperty("maxTurnSpread")?.takeIf { it.isNotEmpty() }?.toDouble() ?: SpeedEstimator.Settings().maxTurnSpread)
        val core = LiveEngineCore(model, PfParams(), 3L, settings)
        val stops = HashMap<Long, Boolean>()
        core.stationaryOverride = { time -> stops[Math.round(time * 10)] ?: false }
        val stream = ImuStream { row -> core.onRow(row.tNs / 1e9, row.accSample, row.gyrSample, row.accMean, row.gyrMean) }
        val speedErrFull = ArrayList<Double>()
        val speedErrHeld = ArrayList<Double>()
        var blackout: LiveEngineCore.Blackout? = null
        val sink = object : SyntheticCar.Sink {
            override fun accelerometer(tNs: Long, x: Double, y: Double, z: Double) = stream.accelerometer(tNs, x, y, z)
            override fun gyroscope(tNs: Long, x: Double, y: Double, z: Double) = stream.gyroscope(tNs, x, y, z)
            override fun truth(time: Double, speed: Double, stopped: Boolean) { stops[Math.round(time * 10)] = stopped }
            override fun fix(fix: Fix) {
                core.onFix(fix)
                val b = blackout ?: return
                val out = b.last ?: return
                if (car.speed > 0.05) {
                    speedErrFull += out.fullSpeedKmh / 3.6 - car.speed
                    speedErrHeld += b.speed0 - car.speed
                }
            }
        }
        car.drive(listOf(SyntheticCar.Piece(20.0, 0.0, 0.0, 0.0)) + car.townLoop() +
            listOf(SyntheticCar.Piece(12.0, 17.0, 1.6, 0.0), SyntheticCar.Piece(10.0, 17.0, 0.0, 0.0)), sink)
        val b = core.startBlackout()!!
        blackout = b
        car.speedBreakers(150.0)
        car.drive(listOf(SyntheticCar.Piece(5.0, 9.5, 1.9, 0.0)) + car.slowTown(), sink)

        println("$label — calibration at the blackout start:")
        println("  gyro, round 2 (free axis, samples) %s x%.3f · gyro, 248 Hz (about true vertical) %s x%.3f"
            .format(b.cal.method, b.cal.scale, b.calFull.method, b.calFull.scale))
        val m = b.mount
        println("  vehicle axes: " + (m?.let { "fitted, sideways scale %.3f, fit r %.3f, forward scale %.3f from %d turn samples"
            .format(it.scaleRight, it.rightFitR, it.scaleForward, it.turnSamples) } ?: "not fitted — ${MountCalibration.lastReason}"))
        assertTrue(m != null && m.rightFitR > 0.8)
        assertTrue(b.calFull.method == "vertical-window" && abs(b.calFull.scale - 1.0) < 0.05)

        val s = b.current
        fun rms(a: List<Double>) = sqrt(a.sumOf { it * it } / a.size)
        println("  blackout: %.0f s, GPS distance %.0f m, corners every ~100 m, a stop and %d speed breakers".format(s.elapsedS, s.trueDistanceM, car.bumps))
        println("  speed error while moving (RMS):  held GPS speed %.1f m/s · 248 Hz estimate %.1f m/s (%d turn readings)"
            .format(rms(speedErrHeld), rms(speedErrFull), s.turnReadings))
        println("  2D drift, no map:  round 2 (held speed) %.0f m = %.1f%% · 248 Hz engine %.0f m = %.1f%%"
            .format(s.noMapDriftM, s.noMapDriftPct, s.fullNoMapDriftM, s.fullNoMapDriftPct))
        assertTrue(s.fullNoMapDriftPct < s.noMapDriftPct / 2)
        assertTrue(rms(speedErrFull) < 0.6 * rms(speedErrHeld))
    }

    /** A simulated drive written as the phone writes recordings, then replayed and scored by DriveReplay. */
    @Test
    fun recordingReplaysAndScores() {
        val car = SyntheticCar(21)
        val dir = File(System.getProperty("java.io.tmpdir"), "sih_synthetic_drive").apply { mkdirs() }
        val file = File(dir, "drive_synthetic.csv.gz")
        val stops = HashMap<Long, Boolean>()
        GZIPOutputStream(file.outputStream()).bufferedWriter().use { w ->
            w.write("# synthetic drive · SyntheticCar(21)\n")
            val sink = object : SyntheticCar.Sink {
                override fun accelerometer(tNs: Long, x: Double, y: Double, z: Double) { w.write("A,$tNs,$x,$y,$z\n") }
                override fun gyroscope(tNs: Long, x: Double, y: Double, z: Double) { w.write("G,$tNs,$x,$y,$z\n") }
                override fun truth(time: Double, speed: Double, stopped: Boolean) { stops[Math.round(time * 10)] = stopped }
                override fun fix(fix: Fix) {
                    val hasBearing = !fix.bearing.isNaN()
                    w.write("L,${Math.round(fix.t * 1e9)},0,${fix.lat},${fix.lon},0,${fix.accuracyM},${fix.speed},NaN," +
                        "${if (hasBearing) fix.bearing else 0.0},NaN,1,${if (hasBearing) 1 else 0}\n")
                }
            }
            car.drive(listOf(SyntheticCar.Piece(20.0, 0.0, 0.0, 0.0)) + car.townLoop(), sink)
            car.speedBreakers(150.0)
            car.drive(car.slowTown(12) + car.slowTown(12) + car.slowTown(12), sink)
        }
        val records = DriveReplay.run(listOf(file), model, stationaryOverride = { time -> stops[Math.round(time * 10)] ?: false })
        val at1km = records.filter { it.metres == 1000 }
        println("synthetic recording: %.1f MB, %d blackouts scored to 1 km".format(file.length() / 1e6, at1km.size))
        assertTrue(at1km.size >= 5)
        assertTrue(Calibration.median(at1km.map { it.fullNoMap }.toDoubleArray()) <
            Calibration.median(at1km.map { it.round2NoMap }.toDoubleArray()))
    }
}
