package com.sih2026.nav.live.engine

import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.util.zip.GZIPInputStream

/**
 * Where the error comes from, on recorded rides: every automatic blackout also runs the 248 Hz engine's map-free dead
 * reckoning with one input replaced by the truth from GPS — the stops, the speed, the heading, then both speed and
 * heading. Whatever error disappears when an input is made perfect is that input's share.
 *
 * Also: does a phone moving in the hand hurt heading? Blackouts are split into thirds by how much the phone rotated
 * about horizontal axes (TiltTracker), and the heading-only error (true speed, the engine's own heading) compared.
 *
 * Run:  gradle testDebugUnitTest --tests '*ErrorSourcesTest*' -Ddrive=<segment or folder>
 */
class ErrorSourcesTest {

    /** GPS speed and course over a whole recording, for truth at any row time (analysis only: it looks ahead). */
    private fun truthOf(file: File): (Double) -> DoubleArray? {
        val t = ArrayList<Double>(); val v = ArrayList<Double>(); val c = ArrayList<Double>()
        try {
            BufferedReader(InputStreamReader(GZIPInputStream(file.inputStream(), 1 shl 16))).use { r ->
                while (true) {
                    val line = r.readLine() ?: break
                    if (!line.startsWith("L,")) continue
                    val p = line.split(',')
                    if (p.size < 13 || p[11] != "1") continue
                    t += p[1].toLong() / 1e9; v += p[7].toDouble()
                    c += if (p[12] == "1" && p[7].toDouble() >= 1.0) Math.toRadians(p[9].toDouble()) else Double.NaN
                }
            }
        } catch (e: java.io.EOFException) { }
        // course held through slow stretches, then unwrapped
        val course = DoubleArray(c.size)
        var last = c.firstOrNull { !it.isNaN() } ?: 0.0
        for (k in c.indices) { if (!c[k].isNaN()) last = c[k]; course[k] = last }
        for (k in 1 until course.size) course[k] = course[k - 1] + Geo.wrap(course[k] - course[k - 1])
        val tt = t.toDoubleArray(); val vv = v.toDoubleArray()
        return { time ->
            if (tt.size < 2 || time < tt[0] || time > tt[tt.size - 1]) null
            else {
                var j = java.util.Arrays.binarySearch(tt, time).let { if (it >= 0) it else -it - 2 }.coerceIn(0, tt.size - 2)
                val f = (time - tt[j]) / (tt[j + 1] - tt[j])
                doubleArrayOf(vv[j] + f * (vv[j + 1] - vv[j]), course[j] + f * (course[j + 1] - course[j]))
            }
        }
    }

    @Test
    fun errorSources() {
        val path = System.getProperty("drive").orEmpty()
        assumeTrue(path.isNotEmpty() && File(path).exists())
        val root = File(path)
        val files = if (root.isDirectory) root.listFiles { f -> f.name.endsWith(".csv.gz") }!!.sortedBy { it.name } else listOf(root)
        val model = MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes())
        for (file in files) {
            val records = DriveReplay.run(listOf(file), model, truthFor = { truthOf(it) }, quiet = true)
                .filter { it.oracle != null }
            println("\n${file.name} — median 2D drift, % of distance, without the map (the 248 Hz engine's dead reckoning)")
            println("  %-10s %6s %4s  %9s %12s %12s %13s %15s   %s".format("speed", "metres", "n", "as it ran", "true stops", "true speed",
                "true heading", "speed+heading", "(with the map, as it ran)"))
            for (band in DriveReplay.BANDS + "all") {
                for (m in intArrayOf(200, 500, 1000)) {
                    val q = records.filter { it.metres == m && (band == "all" || DriveReplay.band(it.avgKmh) == band) }
                    if (q.size < 2) continue
                    fun med(sel: (DriveReplay.Record) -> Double) = Calibration.median(q.map(sel).toDoubleArray())
                    println("  %-10s %6d %4d  %8.1f%% %11.1f%% %11.1f%% %12.1f%% %14.1f%%   (%.1f%%)".format(band, m, q.size,
                        med { it.fullNoMap }, med { it.oracle!![0] }, med { it.oracle!![1] }, med { it.oracle!![2] }, med { it.oracle!![3] }, med { it.full }))
                }
            }
            val at1km = records.filter { it.metres == 1000 && it.tiltRate.isFinite() }.sortedBy { it.tiltRate }
            if (at1km.size >= 6) {
                println("\n  the phone in the hand: blackouts (1 km) in thirds by mean rotation about horizontal axes")
                println("  %-8s %4s %18s %28s %24s".format("third", "n", "rotation (deg/s)", "heading-only error (true speed)", "error with both true"))
                val third = at1km.size / 3
                for ((k, name) in listOf("calmest", "middle", "shakiest").withIndex()) {
                    val q = at1km.subList(k * third, if (k == 2) at1km.size else (k + 1) * third)
                    println("  %-8s %4d %11.1f–%.1f %25.1f%% %23.1f%%".format(name, q.size,
                        Math.toDegrees(q.first().tiltRate), Math.toDegrees(q.last().tiltRate),
                        Calibration.median(q.map { it.oracle!![1] }.toDoubleArray()), Calibration.median(q.map { it.oracle!![3] }.toDoubleArray())))
                }
            }
        }
    }
}
