package com.sih2026.nav.live.engine

import java.io.BufferedReader
import java.io.EOFException
import java.io.File
import java.io.InputStreamReader
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.util.Locale
import java.util.zip.GZIPInputStream
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Replays drives recorded by the phone through the same engine code the phone runs, and scores them the way round 2
 * scored IO-VNBD: a blackout starts every 250 m of GPS distance once there are 5 minutes of history and the car moves
 * above 15 km/h, and runs 1 km; drift is measured at 50, 100, 200, 500 and 1000 m against the phone's own GPS.
 *
 * Rows are rebuilt from the raw events in file order through ImuStream, exactly as LiveSensors built them live.
 * Also measured: the stop classifier against GPS speed, and the 248 Hz speed estimate against GPS speed.
 */
object DriveReplay {
    val CHECKPOINTS = intArrayOf(50, 100, 200, 500, 1000)
    val BANDS = listOf("under 40", "40-50", "50-70", "70+")

    class Record(val drive: String, val metres: Int, val avgKmh: Double, val stopped: Boolean,
                 val round2: Double, val round2NoMap: Double, val full: Double, val fullNoMap: Double,
                 val oracle: DoubleArray? = null, val tiltRate: Double = Double.NaN)

    private class Scheduled(val b: LiveEngineCore.Blackout, var next: Int = 0, var stopped: Boolean = false)

    /** A blackout switched on and off by hand during the drive, replayed at the same moments. */
    class Manual(val drive: String, val startMin: Double, var minutes: Double = 0.0, var score: BlackoutScore? = null,
                 val at500: Array<BlackoutScore?> = arrayOfNulls(1), val at1000: Array<BlackoutScore?> = arrayOfNulls(1))

    val manualBlackouts = ArrayList<Manual>()

    fun band(kmh: Double) = when {
        kmh < 40 -> "under 40"
        kmh < 50 -> "40-50"
        kmh < 70 -> "50-70"
        else -> "70+"
    }

    fun run(files: List<File>, model: MotionModel, stationaryOverride: ((Double) -> Boolean)? = null,
            settings: SpeedEstimator.Settings = SpeedEstimator.Settings(),
            truthFor: ((File) -> ((Double) -> DoubleArray?))? = null, quiet: Boolean = false): List<Record> {
        val records = ArrayList<Record>()
        manualBlackouts.clear()
        var stopTP = 0; var stopFN = 0; var moveTN = 0; var moveFP = 0
        val speedErr = HashMap<String, ArrayList<Double>>()
        val heldErr = HashMap<String, ArrayList<Double>>()

        for (file in files) {
            val core = LiveEngineCore(model, PfParams(), 11L, settings)
            core.stationaryOverride = stationaryOverride
            core.truth = truthFor?.invoke(file)
            var lastOut: LiveOutput? = null
            val stream = ImuStream { row -> lastOut = core.onRow(row.tNs / 1e9, row.accSample, row.gyrSample, row.accMean, row.gyrMean) }
            var firstFix: Fix? = null
            var prev: Fix? = null
            var gpsDist = 0.0
            var nextStart = 250.0
            val active = ArrayList<Scheduled>()
            var rows = 0L; var fixes = 0; var manual = 0
            var truncated = false
            var manualB: LiveEngineCore.Blackout? = null
            var manualRec: Manual? = null
            var t0Ns = 0L
            try {
                BufferedReader(InputStreamReader(GZIPInputStream(file.inputStream(), 1 shl 16)), 1 shl 16).use { reader ->
                    while (true) {
                        val line = reader.readLine() ?: break
                        if (line.isEmpty() || line[0] == '#') continue
                        val p = line.split(',')
                        when (p[0]) {
                            "A" -> stream.accelerometer(p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble())
                            "G" -> {
                                if (t0Ns == 0L) t0Ns = p[1].toLong()
                                val before = lastOut
                                stream.gyroscope(p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble())
                                val out = lastOut
                                if (out != null && out !== before) {
                                    rows++
                                    val f = prev
                                    if (f != null && abs(out.t - f.t) <= 1.0 && !f.speed.isNaN()) {
                                        if (f.speed < 0.3) { if (out.stationary) stopTP++ else stopFN++ }
                                        else if (f.speed > 1.5) { if (out.stationary) moveFP++ else moveTN++ }
                                    }
                                }
                            }
                            "L" -> {
                                if (p.size < 13) continue
                                val fix = Fix(p[1].toLong() / 1e9, p[3].toDouble(), p[4].toDouble(),
                                    if (p[11] == "1") p[7].toDouble() else Double.NaN,
                                    if (p[12] == "1") p[9].toDouble() else Double.NaN, p[6].toDouble())
                                fixes++
                                if (firstFix == null) {
                                    firstFix = fix
                                    core.network = pickNetwork(fix)
                                    println("${file.name}: road network ${core.network?.name ?: "none for this area"}")
                                }
                                val pr = prev
                                if (pr != null && fix.t > pr.t) {
                                    gpsDist += ((if (pr.speed.isNaN()) 0.0 else pr.speed) + (if (fix.speed.isNaN()) 0.0 else fix.speed)) / 2 * (fix.t - pr.t)
                                }
                                prev = fix
                                core.onFix(fix)
                                manualB?.let { mb ->
                                    val sc = mb.current
                                    if (sc.trueDistanceM >= 500 && manualRec!!.at500[0] == null) manualRec!!.at500[0] = sc
                                    if (sc.trueDistanceM >= 1000 && manualRec!!.at1000[0] == null) manualRec!!.at1000[0] = sc
                                }
                                for (s in active) {
                                    val out = s.b.last ?: continue
                                    if (fix.speed.isNaN()) continue
                                    if (fix.speed < 0.5) { s.stopped = true; continue }
                                    val bnd = band(s.b.current.trueDistanceM / maxOf(s.b.current.elapsedS, 1.0) * 3.6)
                                    speedErr.getOrPut(bnd) { ArrayList() } += out.fullSpeedKmh / 3.6 - fix.speed
                                    heldErr.getOrPut(bnd) { ArrayList() } += s.b.speed0 - fix.speed
                                }
                                val done = ArrayList<Scheduled>()
                                for (s in active) {
                                    val sc = s.b.current
                                    while (s.next < CHECKPOINTS.size && sc.trueDistanceM >= CHECKPOINTS[s.next]) {
                                        records += Record(file.name, CHECKPOINTS[s.next], sc.trueDistanceM / maxOf(sc.elapsedS, 1.0) * 3.6,
                                            s.stopped, sc.driftPct, sc.noMapDriftPct, sc.fullDriftPct, sc.fullNoMapDriftPct,
                                            sc.oracleDriftPct?.copyOf(), sc.tiltRateMean)
                                        s.next++
                                    }
                                    if (s.next >= CHECKPOINTS.size) done += s
                                }
                                for (s in done) { core.endBlackout(s.b); active.remove(s) }
                                if (gpsDist >= nextStart) {
                                    nextStart += 250.0
                                    if (fix.t - firstFix!!.t >= 300.0 && !fix.speed.isNaN() && fix.speed > 4.2) {
                                        core.startBlackout()?.let { active += Scheduled(it) }
                                    }
                                }
                            }
                            "B" -> {
                                manual++
                                if (p[2].trim() == "1" && manualB == null) {
                                    manualB = core.startBlackout()
                                    if (manualB != null) {
                                        manualRec = Manual(file.name, (p[1].toLong() - t0Ns) / 60e9)
                                        manualBlackouts += manualRec!!
                                    }
                                } else if (p[2].trim() == "0" && manualB != null) {
                                    manualRec!!.score = manualB!!.current
                                    manualRec!!.minutes = manualB!!.current.elapsedS / 60
                                    core.endBlackout(manualB)
                                    manualB = null
                                }
                            }
                        }
                    }
                }
            } catch (e: EOFException) {
                truncated = true                          // the app was stopped mid-write: use what was read
            }
            println("  %d rows, %d fixes, %.1f km of GPS driving, %d manual blackout switches%s"
                .format(rows, fixes, gpsDist / 1000, manual, if (truncated) " (file ends mid-write)" else ""))
        }

        if (manualBlackouts.isNotEmpty() && !quiet) {
            println("\nyour blackouts, replayed at the moments you switched them (drift against GPS, % of GPS distance):")
            println("  %-5s %6s %8s %7s   %-24s %-24s %-24s".format("start", "length", "GPS dist", "avg", "at 500 m: r2 / 248 Hz", "at 1 km: r2 / 248 Hz", "at the end: r2 / 248 Hz"))
            for (mb in manualBlackouts) {
                val s = mb.score ?: continue
                fun pair(x: BlackoutScore?) = x?.let { "%5.1f%% / %5.1f%%".format(it.driftPct, it.fullDriftPct) } ?: "        —        "
                println("  %4.1fm %5.1fm %7.0fm %4.0fkm/h   %-24s %-24s %5.0fm / %5.0fm (%4.1f%% / %4.1f%%)".format(mb.startMin, mb.minutes,
                    s.trueDistanceM, s.trueDistanceM / maxOf(s.elapsedS, 1.0) * 3.6, pair(mb.at500[0]), pair(mb.at1000[0]),
                    s.driftM, s.fullDriftM, s.driftPct, s.fullDriftPct))
            }
            println("  (round 2 = held GPS speed + gyro samples + map; 248 Hz = accelerometer speed + gyro means + map)")
        }
        if (quiet) return records
        println("\nstop classifier against GPS speed: stopped (< 1 km/h) recognised %d / %d · moving (> 5 km/h) called stopped %d / %d"
            .format(stopTP, stopTP + stopFN, moveFP, moveFP + moveTN))
        if (records.isEmpty()) {
            println("no scored blackouts: a drive needs 5 minutes of GPS history and movement above 15 km/h")
            return records
        }
        println("\nspeed while moving in blackouts, RMS error against GPS (m/s):   held GPS speed · 248 Hz estimate")
        for (bnd in BANDS) {
            val a = heldErr[bnd] ?: continue
            println("  %-9s %6.2f · %6.2f   (%d fixes)".format(bnd, rms(a), rms(speedErr[bnd]!!), a.size))
        }
        println("\n2D drift, median % of distance, by the blackout's average speed — round 2 (10 Hz) against the 248 Hz engine")
        println("  %-9s %6s %5s   %12s %12s   %12s %12s".format("speed", "metres", "n", "round 2 map", "248 Hz map", "round 2 none", "248 Hz none"))
        for (bnd in BANDS + "all") {
            for (m in CHECKPOINTS) {
                val q = records.filter { it.metres == m && (bnd == "all" || band(it.avgKmh) == bnd) }
                if (q.isEmpty()) continue
                println("  %-9s %6d %5d   %11.1f%% %11.1f%%   %11.1f%% %11.1f%%".format(Locale.US, bnd, m, q.size,
                    median(q.map { it.round2 }), median(q.map { it.full }), median(q.map { it.round2NoMap }), median(q.map { it.fullNoMap })))
            }
        }
        return records
    }

    fun writeCsv(records: List<Record>, out: File) {
        out.printWriter().use { w ->
            w.println("drive,metres,avg_kmh,stopped,round2_map_pct,round2_nomap_pct,full_map_pct,full_nomap_pct")
            for (r in records) w.println("%s,%d,%.2f,%d,%.3f,%.3f,%.3f,%.3f".format(Locale.US, r.drive, r.metres, r.avgKmh,
                if (r.stopped) 1 else 0, r.round2, r.round2NoMap, r.full, r.fullNoMap))
        }
    }

    private fun pickNetwork(fix: Fix): RoadNetwork? {
        val files = Fixtures.fixtureDir.listFiles { f -> f.name.endsWith(".roadnet.bin") && f.name != "england.roadnet.bin" }.orEmpty()
        for (f in files.sortedBy { it.name }) {
            val net = RandomAccessFile(f, "r").use { raf ->
                val head = ByteArray(minOf(raf.length(), 512L).toInt()).also { raf.readFully(it) }
                val box = RoadNetwork.header(ByteBuffer.wrap(head)).second
                if (fix.lat in box[0]..box[2] && fix.lon in box[1]..box[3])
                    RoadNetwork(raf.channel.map(FileChannel.MapMode.READ_ONLY, 0, raf.length())) else null
            }
            if (net != null) return net
        }
        return null
    }

    private fun rms(a: List<Double>) = sqrt(a.sumOf { it * it } / maxOf(a.size, 1))
    private fun median(a: List<Double>) = Calibration.median(a.toDoubleArray())
}
