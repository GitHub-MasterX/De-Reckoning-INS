package com.sih2026.nav.live.engine

import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.BufferedReader
import java.io.EOFException
import java.io.File
import java.io.InputStreamReader
import java.util.zip.GZIPInputStream

/**
 * What the calibrations make of a recorded drive, every two minutes: the gyro fits, the accelerometer mount fit (or why
 * it failed), and GPS speed against the accelerometer's sideways swing in turns.
 * Run:  gradle testDebugUnitTest --tests '*DriveDiagnoseTest*' -Ddrive=/path/to/recording.csv.gz
 */
class DriveDiagnoseTest {
    @Test
    fun diagnose() {
        val path = System.getProperty("drive").orEmpty()
        assumeTrue(path.isNotEmpty() && File(path).isFile)
        val model = MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes())
        val core = LiveEngineCore(model, PfParams(), 1L)
        var lastRowT = 0.0
        var nextReport = Double.NaN
        var t0 = Double.NaN
        val stream = ImuStream { row -> lastRowT = row.tNs / 1e9; core.onRow(lastRowT, row.accSample, row.gyrSample, row.accMean, row.gyrMean) }
        try {
            BufferedReader(InputStreamReader(GZIPInputStream(File(path).inputStream(), 1 shl 16)), 1 shl 16).use { r ->
                while (true) {
                    val line = r.readLine() ?: break
                    if (line.isEmpty() || line[0] == '#') continue
                    val p = line.split(',')
                    when (p[0]) {
                        "A" -> stream.accelerometer(p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble())
                        "G" -> stream.gyroscope(p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble())
                        "L" -> {
                            if (p.size < 13) continue
                            val fix = Fix(p[1].toLong() / 1e9, p[3].toDouble(), p[4].toDouble(),
                                if (p[11] == "1") p[7].toDouble() else Double.NaN, if (p[12] == "1") p[9].toDouble() else Double.NaN, p[6].toDouble())
                            core.onFix(fix)
                            if (t0.isNaN()) { t0 = fix.t; nextReport = fix.t + 120 }
                            if (fix.t >= nextReport) {
                                nextReport += 120
                                val pv = core.previewCalibration()
                                if (pv != null) {
                                    println("%5.1f min · gyro samples %s x%.3f (%d turns) · gyro about vertical %s x%.3f (%d turns) · vehicle axes: %s".format(
                                        (fix.t - t0) / 60, pv.gyro.method, pv.gyro.scale, pv.gyro.turnWindows,
                                        pv.gyroFull.method, pv.gyroFull.scale, pv.gyroFull.turnWindows,
                                        pv.mount?.let { "fitted, sideways scale %.3f, r %.3f, forward scale %.3f".format(it.scaleRight, it.rightFitR, it.scaleForward) }
                                            ?: MountCalibration.lastReason))
                                }
                            }
                        }
                    }
                }
            }
        } catch (e: EOFException) { }
    }
}
