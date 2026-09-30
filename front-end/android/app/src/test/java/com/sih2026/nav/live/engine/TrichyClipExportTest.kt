package com.sih2026.nav.live.engine

import org.junit.Assume.assumeTrue
import org.junit.Test
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

/**
 * Replay clips from the phone's own rides, for the app's replay screen (make_trichy_clips.sh writes and runs this).
 * Each segment runs through LiveEngineCore exactly as DriveReplay runs it; every blackout (automatic every 250 m, and
 * the rider's manual ones) is recorded at 10 Hz and scored frame by frame against GPS interpolated to the frame time.
 * Analysis only: the truth track looks ahead in the recording, the engines never see it.
 */
class TrichyClipExportTest {
    private val cut = (System.getenv("CUT_PCT") ?: "11").toDouble()        // a kept clip averages under this
    private val fromM = (System.getenv("FROM_M") ?: "100").toDouble()      // measured from here into the blackout
    private val maxPerSeg = (System.getenv("MAX_PER_SEG") ?: "99").toInt()
    private val minGapM = (System.getenv("MIN_GAP_M") ?: "0").toDouble()
    private val leadS = 15.0

    private class Truth(val t: DoubleArray, val lat: DoubleArray, val lon: DoubleArray, val speed: DoubleArray,
                        val bearing: DoubleArray, val dist: DoubleArray) {
        private fun idx(time: Double): Int {
            var lo = 0; var hi = t.size - 1
            if (time <= t[0]) return 0
            if (time >= t[hi]) return hi - 1
            while (hi - lo > 1) { val m = (lo + hi) / 2; if (t[m] <= time) lo = m else hi = m }
            return lo
        }
        private fun f(i: Int, time: Double) = ((time - t[i]) / maxOf(t[i + 1] - t[i], 1e-9)).coerceIn(0.0, 1.0)
        fun at(a: DoubleArray, time: Double): Double { val i = idx(time); val k = f(i, time); return a[i] + k * (a[i + 1] - a[i]) }
        fun heading(time: Double): Double {
            val i = idx(time); val k = f(i, time)
            val a = bearing[i]; val b = bearing[i + 1]
            if (a.isNaN()) return if (b.isNaN()) 0.0 else b
            if (b.isNaN()) return a
            val d = Math.toDegrees(Geo.wrap(Math.toRadians(b - a)))
            return ((a + k * d) % 360.0 + 360.0) % 360.0
        }
    }

    private class Frame(val t: Double, val lat: Double, val lon: Double, val heading: Double, val onMap: Boolean,
                        val nmLat: Double, val nmLon: Double)

    private class Rec(val kind: String, val b: LiveEngineCore.Blackout, val startDist: Double) {
        val frames = ArrayList<Frame>()
        var lastT = Double.NaN
        var ended = false
    }

    private class Clip(val seg: Int, val kind: String, val startT: Double, val startDist: Double, val json: (String) -> String,
                       val finalPct: Double, val finalM: Double, val basePct: Double, val baseM: Double,
                       val meanPct: Double, val maxPct: Double, val distM: Double, val durS: Double, val avgKmh: Double,
                       val turns: Int)

    @Test
    fun exportTrichyClips() {
        assumeTrue(System.getenv("TRICHY_EXPORT") == "1")
        val inDir = File(System.getProperty("drive").orEmpty())
        assumeTrue("pass -Ddrive=<folder of seg<N>.csv.gz>", inDir.isDirectory)
        val outDir = File(System.getenv("TRICHY_OUT") ?: error("TRICHY_OUT not set")).also { it.mkdirs() }
        val model = MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes())
        val summary = StringBuilder()
        val chosenAll = ArrayList<Pair<String, Clip>>()

        for (file in inDir.listFiles { f -> f.name.matches(Regex("seg\\d+\\.csv\\.gz")) }!!.sortedBy { it.name }) {
            val seg = file.name.removePrefix("seg").substringBefore('.').toInt()
            val truth = readTruth(file)
            println("\nsegment $seg: ${truth.t.size} GPS fixes, %.1f km".format(truth.dist.last() / 1000))
            val clips = replay(seg, file, model, truth)
            val good = clips.filter { it.meanPct < cut }.sortedBy { it.meanPct }       // average under the cut, best first
            val picked = ArrayList<Clip>()
            for (c in good) {
                if (picked.size >= maxPerSeg) break
                if (c.kind == "auto" && picked.any { it.kind == "auto" && abs(it.startDist - c.startDist) < minGapM }) continue
                picked += c
            }
            picked.sortBy { it.startT }
            println("  %d blackouts replayed, %d averaged under %.0f%%, %d kept"
                .format(clips.size, good.size, cut, picked.size))
            File(outDir, "seg${seg}_candidates.csv").printWriter().use { w ->
                w.println("kind,start_min,distance_m,avg_kmh,mean_pct,max_pct,final_pct,nomap_final_pct,kept")
                for (c in clips) w.println("%s,%.2f,%.0f,%.1f,%.2f,%.2f,%.2f,%.2f,%d".format(Locale.US, c.kind,
                    (c.startT - truth.t[0]) / 60, c.distM, c.avgKmh, c.meanPct, c.maxPct, c.finalPct, c.basePct,
                    if (c in picked) 1 else 0))
            }
            picked.forEachIndexed { k, c ->
                val id = "trichy_seg%d_%02d".format(seg, k + 1)
                File(outDir, "$id.json").writeText(c.json(id))
                chosenAll += id to c
                val line = "  %-16s %-6s start %5.1f min  %5.0f m  %3.0f km/h  mean %4.1f%%  max %5.1f%%  end %4.1f%% (%3.0f m)  no map %5.1f%%  %s"
                    .format(Locale.US, id, c.kind, (c.startT - truth.t[0]) / 60, c.distM, c.avgKmh, c.meanPct, c.maxPct,
                        c.finalPct, c.finalM, c.basePct, label(c.seg, c.kind))
                println(line); summary.appendLine(line)
            }
        }
        File(outDir, "trichy_index.json").writeText(buildString {
            append("[\n")
            chosenAll.forEachIndexed { i, (id, c) ->
                append(infoJson(id, c)); if (i < chosenAll.size - 1) append(",\n")
            }
            append("\n]\n")
        })
        File(outDir, "summary.txt").writeText(summary.toString())
        println("\n${chosenAll.size} clips written to $outDir")
    }

    private fun readTruth(file: File): Truth {
        val t = ArrayList<Double>(); val la = ArrayList<Double>(); val lo = ArrayList<Double>()
        val sp = ArrayList<Double>(); val be = ArrayList<Double>()
        try {
            BufferedReader(InputStreamReader(GZIPInputStream(file.inputStream(), 1 shl 16)), 1 shl 16).use { r ->
                while (true) {
                    val line = r.readLine() ?: break
                    if (!line.startsWith("L,")) continue
                    val p = line.split(',')
                    if (p.size < 13) continue
                    val time = p[1].toLong() / 1e9
                    if (t.isNotEmpty() && time <= t.last()) continue
                    t += time; la += p[3].toDouble(); lo += p[4].toDouble()
                    sp += if (p[11] == "1") p[7].toDouble() else Double.NaN
                    be += if (p[12] == "1") p[9].toDouble() else Double.NaN
                }
            }
        } catch (e: EOFException) { }
        val n = t.size
        val speed = DoubleArray(n) { if (sp[it].isNaN()) 0.0 else sp[it] }
        val dist = DoubleArray(n)
        for (i in 1 until n) dist[i] = dist[i - 1] + (speed[i - 1] + speed[i]) / 2 * (t[i] - t[i - 1])   // as scoring does
        // bearings of a near-stopped phone are noise: hold the last moving one
        val bearing = DoubleArray(n) { be[it] }
        for (i in 0 until n) if (speed[i] < 1.0) bearing[i] = if (i > 0) bearing[i - 1] else Double.NaN
        return Truth(t.toDoubleArray(), la.toDoubleArray(), lo.toDoubleArray(), speed, bearing, dist)
    }

    private fun replay(seg: Int, file: File, model: MotionModel, truth: Truth): List<Clip> {
        val core = LiveEngineCore(model, PfParams(), 11L)
        val recs = ArrayList<Rec>()
        val done = ArrayList<Rec>()
        var manual: Rec? = null
        var firstFix: Fix? = null
        var gpsDist = 0.0
        var prev: Fix? = null
        var nextStart = 250.0
        val stream = ImuStream { row ->
            core.onRow(row.tNs / 1e9, row.accSample, row.gyrSample, row.accMean, row.gyrMean)
            for (r in recs) {
                val o = r.b.last ?: continue
                if (o.t == r.lastT) continue
                r.lastT = o.t
                r.frames += Frame(o.t, o.fullLat, o.fullLon, o.fullHeadingDeg, o.fullOnMap, o.fullNoMapLat, o.fullNoMapLon)
            }
        }
        try {
            BufferedReader(InputStreamReader(GZIPInputStream(file.inputStream(), 1 shl 16)), 1 shl 16).use { reader ->
                while (true) {
                    val line = reader.readLine() ?: break
                    if (line.isEmpty() || line[0] == '#') continue
                    val p = line.split(',')
                    when (p[0]) {
                        "A" -> stream.accelerometer(p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble())
                        "G" -> stream.gyroscope(p[1].toLong(), p[2].toDouble(), p[3].toDouble(), p[4].toDouble())
                        "L" -> {
                            if (p.size < 13) continue
                            val fix = Fix(p[1].toLong() / 1e9, p[3].toDouble(), p[4].toDouble(),
                                if (p[11] == "1") p[7].toDouble() else Double.NaN,
                                if (p[12] == "1") p[9].toDouble() else Double.NaN, p[6].toDouble())
                            if (firstFix == null) {
                                firstFix = fix
                                core.network = pickNetwork(fix)
                                println("  road network: ${core.network?.name ?: "none for this area"}")
                            }
                            val pr = prev
                            if (pr != null && fix.t > pr.t) gpsDist += ((if (pr.speed.isNaN()) 0.0 else pr.speed) +
                                (if (fix.speed.isNaN()) 0.0 else fix.speed)) / 2 * (fix.t - pr.t)
                            prev = fix
                            core.onFix(fix)
                            for (r in recs.toList()) {
                                if (r.kind == "auto" && r.b.current.trueDistanceM >= 1000.0) {
                                    core.endBlackout(r.b); recs.remove(r); r.ended = true; done += r
                                }
                            }
                            if (gpsDist >= nextStart) {
                                nextStart += 250.0
                                if (fix.t - firstFix!!.t >= 300.0 && !fix.speed.isNaN() && fix.speed > 4.2) {
                                    core.startBlackout()?.let { recs += Rec("auto", it, gpsDist) }
                                }
                            }
                        }
                        "B" -> {
                            if (p[2].trim() == "1" && manual == null) {
                                manual = core.startBlackout()?.let { Rec("manual", it, gpsDist) }
                                manual?.let { recs += it }
                            } else if (p[2].trim() == "0" && manual != null) {
                                core.endBlackout(manual!!.b); recs.remove(manual!!); manual!!.ended = true; done += manual!!
                                manual = null
                            }
                        }
                    }
                }
            }
        } catch (e: EOFException) { }
        return done.mapNotNull { toClip(seg, it, truth) }
    }

    private fun toClip(seg: Int, r: Rec, tr: Truth): Clip? {
        val fr = r.frames
        if (fr.size < 50) return null
        val t0 = r.b.fix.t
        val d0 = tr.at(tr.dist, t0)
        val n = fr.size
        val tLat = DoubleArray(n) { tr.at(tr.lat, fr[it].t) }
        val tLon = DoubleArray(n) { tr.at(tr.lon, fr[it].t) }
        val tHead = DoubleArray(n) { tr.heading(fr[it].t) }
        val tSpeed = DoubleArray(n) { tr.at(tr.speed, fr[it].t) * 3.6 }
        val tDist = DoubleArray(n) { maxOf(0.0, tr.at(tr.dist, fr[it].t) - d0) }
        val drift = DoubleArray(n) { Geo.haversineM(fr[it].lat, fr[it].lon, tLat[it], tLon[it]) }
        val nmDrift = DoubleArray(n) { Geo.haversineM(fr[it].nmLat, fr[it].nmLon, tLat[it], tLon[it]) }
        fun pct(m: Double, d: Double) = if (d < 1.0) 0.0 else 100 * m / d
        val distM = tDist.last()
        if (distM < 200.0) return null                                  // too short to mean anything
        val scored = (0 until n).filter { tDist[it] >= fromM }
        if (scored.isEmpty()) return null
        val meanPct = scored.sumOf { pct(drift[it], tDist[it]) } / scored.size
        val maxPct = scored.maxOf { pct(drift[it], tDist[it]) }
        val durS = fr.last().t - t0
        val avgKmh = distM / maxOf(durS, 1.0) * 3.6
        var turns = 0
        var ref = tHead[0]
        for (h in tHead) if (abs(Math.toDegrees(Geo.wrap(Math.toRadians(h - ref)))) >= 45.0) { turns++; ref = h }

        // lead-in: the GPS track for the 15 s before the blackout, at 10 Hz
        val leadT = (0 until (leadS * 10).toInt()).map { t0 - leadS + it * 0.1 }.filter { it >= tr.t[0] }
        val band = when { avgKmh < 40 -> "slow"; avgKmh < 50 -> "mixed"; avgKmh < 70 -> "ps_60"; else -> "fast" }
        val finalPct = pct(drift.last(), distM)
        val basePct = pct(nmDrift.last(), distM)

        fun num(x: Double, dec: Int) = if (x.isFinite()) String.format(Locale.US, "%.${dec}f", x) else "0"
        fun arr(xs: DoubleArray, dec: Int) = xs.joinToString(",", "[", "]") { num(it, dec) }
        fun arrL(xs: List<Double>, dec: Int) = arr(xs.toDoubleArray(), dec)
        val json = { id: String ->
            buildString {
                append("{\"id\":\"$id\",\"driver\":\"TRICHY\",\"role\":\"live ride\",")
                append("\"drive\":\"${label(seg, r.kind)}\",\"session\":$seg,")
                append("\"row_start\":0,\"band\":\"$band\",\"turns\":$turns,\"avg_kmh\":${num(avgKmh, 1)},")
                append("\"distance_m\":${num(distM, 1)},\"duration_s\":${num(durS, 1)},\"hz\":10,")
                append("\"engine\":\"248 Hz engine (SIH Nav Live, frozen settings), Samsung M17 hand-held on a two-wheeler\",")
                append("\"final_drift_m\":${num(drift.last(), 1)},\"final_drift_pct\":${num(finalPct, 2)},")
                append("\"final_base_m\":${num(nmDrift.last(), 1)},\"final_base_pct\":${num(basePct, 2)},")
                append("\"mean_drift_pct\":${num(meanPct, 2)},\"max_drift_pct\":${num(maxPct, 2)},")
                append("\"lead_in\":{\"lat\":${arrL(leadT.map { tr.at(tr.lat, it) }, 7)},")
                append("\"lon\":${arrL(leadT.map { tr.at(tr.lon, it) }, 7)},")
                append("\"heading\":${arrL(leadT.map { tr.heading(it) }, 1)},")
                append("\"speed_kmh\":${arrL(leadT.map { tr.at(tr.speed, it) * 3.6 }, 1)}},")
                append("\"t\":${arr(DoubleArray(n) { fr[it].t - t0 }, 2)},")
                append("\"true_lat\":${arr(tLat, 7)},\"true_lon\":${arr(tLon, 7)},\"true_heading\":${arr(tHead, 1)},")
                append("\"true_speed_kmh\":${arr(tSpeed, 1)},\"true_dist_m\":${arr(tDist, 1)},")
                append("\"pf_lat\":${arr(DoubleArray(n) { fr[it].lat }, 7)},\"pf_lon\":${arr(DoubleArray(n) { fr[it].lon }, 7)},")
                append("\"pf_heading\":${arr(DoubleArray(n) { fr[it].heading }, 1)},")
                append("\"pf_on_map\":${fr.joinToString(",", "[", "]") { if (it.onMap) "true" else "false" }},")
                append("\"nomap_lat\":${arr(DoubleArray(n) { fr[it].nmLat }, 7)},\"nomap_lon\":${arr(DoubleArray(n) { fr[it].nmLon }, 7)},")
                append("\"drift_m\":${arr(drift, 1)},\"drift_pct\":${arr(DoubleArray(n) { pct(drift[it], tDist[it]) }, 2)},")
                append("\"nomap_drift_m\":${arr(nmDrift, 1)},\"nomap_drift_pct\":${arr(DoubleArray(n) { pct(nmDrift[it], tDist[it]) }, 2)},")
                append("\"engine_speed_kmh\":${num(if (r.b.speed0.isFinite()) r.b.speed0 * 3.6 else 0.0, 1)},")
                append("\"scored_pos_pct\":${num(finalPct, 2)},\"reported_pf_pct\":${num(finalPct, 2)},\"reported_base_pct\":${num(basePct, 2)}}")
            }
        }
        return Clip(seg, r.kind, t0, r.startDist, json, finalPct, drift.last(), basePct, nmDrift.last(),
            meanPct, maxPct, distM, durS, avgKmh, turns)
    }

    private fun infoJson(id: String, c: Clip): String {
        fun num(x: Double, dec: Int) = String.format(Locale.US, "%.${dec}f", x)
        val band = when { c.avgKmh < 40 -> "slow"; c.avgKmh < 50 -> "mixed"; c.avgKmh < 70 -> "ps_60"; else -> "fast" }
        return "  {\"id\":\"$id\",\"driver\":\"TRICHY\",\"role\":\"live ride\"," +
            "\"drive\":\"${label(c.seg, c.kind)}\",\"session\":${c.seg},\"band\":\"$band\",\"turns\":${c.turns}," +
            "\"avg_kmh\":${num(c.avgKmh, 1)},\"distance_m\":${num(c.distM, 1)},\"duration_s\":${num(c.durS, 1)}," +
            "\"final_drift_m\":${num(c.finalM, 1)},\"final_drift_pct\":${num(c.finalPct, 2)}," +
            "\"final_base_m\":${num(c.baseM, 1)},\"final_base_pct\":${num(c.basePct, 2)}}"
    }

    /** What the picker shows: which ride the clip came from, and whether you switched that blackout on yourself. */
    private fun segName(seg: Int) = when (seg) {
        1 -> "Trichy out"
        2 -> "Trichy town"
        3 -> "Trichy back"
        else -> "Trichy seg $seg"
    }

    private fun label(seg: Int, kind: String) = segName(seg) + if (kind == "manual") " (GPS off by hand)" else ""

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
}
