package com.sih2026.nav.live.engine

import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * Replays the phone's recorded drives (DriveReplay) and writes every scored checkpoint to data/osm/phone/replay_results.csv.
 * Run from round2/android:  gradle testDebugUnitTest --tests '*DriveReplayTest*' -Ddrive=/path/to/recording_or_folder
 */
class DriveReplayTest {
    @Test
    fun replayRecordedDrives() {
        val path = System.getProperty("drive").orEmpty()
        assumeTrue("pass -Ddrive=<recording or folder> to replay drives", path.isNotEmpty())
        val root = File(path)
        assumeTrue("no such recording or folder: $path", root.exists())
        val files = if (root.isDirectory) root.listFiles { f -> f.name.endsWith(".csv.gz") }!!.sortedBy { it.name } else listOf(root)
        val model = MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes())
        val default = SpeedEstimator.Settings()
        val settings = default.copy(
            heldSpeedSigma = System.getProperty("heldSpeedSigma")?.takeIf { it.isNotEmpty() }?.toDouble() ?: default.heldSpeedSigma,
            confirmSeconds = System.getProperty("confirmSeconds")?.takeIf { it.isNotEmpty() }?.toDouble() ?: default.confirmSeconds)
        System.getProperty("verticalMinSpeed")?.takeIf { it.isNotEmpty() }?.let { Calibration.VERTICAL_MIN_SPEED = it.toDouble() }
        System.getProperty("mountRecentS")?.takeIf { it.isNotEmpty() }?.let { MountCalibration.RECENT_S = it.toDouble() }
        System.getProperty("mountMinTurns")?.takeIf { it.isNotEmpty() }?.let { MountCalibration.MIN_TURN_SAMPLES = it.toInt() }
        println("speed estimator: $settings · gyro fit from %.1f m/s · vehicle axes on the last %.0f s with %d turning samples"
            .format(Calibration.VERTICAL_MIN_SPEED, MountCalibration.RECENT_S, MountCalibration.MIN_TURN_SAMPLES))
        val records = DriveReplay.run(files, model, settings = settings)
        if (records.isNotEmpty()) {
            val out = File(Fixtures.fixtureDir, "replay_results.csv")
            DriveReplay.writeCsv(records, out)
            println("\nevery checkpoint: ${out.absolutePath}")
        }
    }
}
