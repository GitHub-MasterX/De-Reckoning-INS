#!/usr/bin/env bash
# =====================================================================================================================
#  make_trichy_clips.sh — put the best blackouts from your own Trichy rides into the replay app as trichy_seg<N>_<k>
#
#  What it does, in order:
#    1. checks the toolchain, the three ride segments and the Tiruchirappalli road network are where they should be
#    2. writes a JVM exporter (TrichyClipExportTest.kt) into the app's tests — it replays each segment through the exact
#       engine the phone runs (LiveEngineCore, 248 Hz engine, frozen settings), the same way DriveReplay does:
#         · an automatic 1 km blackout every 250 m of GPS distance, after 5 min of history, above 15 km/h
#         · plus every blackout you switched on by hand during the ride (at least 200 m long)
#       and records each blackout at 10 Hz: true track (the phone's GPS, the answer key), the 248 Hz engine with the
#       map (cyan arrow) and without it (red dashed trail), plus a 15 s GPS lead-in — the same JSON the replay app
#       already plays for the IO-VNBD clips
#    3. keeps every blackout whose drift averages under 11% of the distance travelled (measured from 100 m into the
#       blackout onwards, with the 248 Hz engine and the map, averaged over every 10 Hz frame) and drops the rest
#    4. writes them into app/src/main/assets/replay/ as trichy_seg1_01.json, ... and adds them to index.json, under one
#       picker chip "TRICHY"; the England (IO-VNBD) clips stay, renamed from their dataset codes to readable names
#    5. builds the APK, and installs it if a phone is connected (USB debugging)
#
#  Nothing in the engine, the settings, the ML model or the ride data is changed. Location traces only go into the app's
#  assets (the app folder is untracked; do not commit those JSON files to a public repo).
#
#  All three Trichy segments were ridden live with the same frozen settings, so they are shown as one group. These
#  clips are the blackouts that went well; the median over every blackout is in round2/phone_data/README.md.
#
#  Run from anywhere:      bash round2/make_trichy_clips.sh
#  Knobs (environment):    CUT_PCT=11  FROM_M=100  MAX_PER_SEG=99  MIN_GAP_M=500  SEGMENTS="1 2 3"  INSTALL=1
#    CUT_PCT      a kept clip averages under this          MIN_GAP_M    how far apart kept automatic blackouts start
#    FROM_M       where measuring starts in the blackout   MAX_PER_SEG  most clips kept from one segment
# =====================================================================================================================
set -euo pipefail

CUT_PCT="${CUT_PCT:-11}"
FROM_M="${FROM_M:-100}"
MAX_PER_SEG="${MAX_PER_SEG:-99}"
MIN_GAP_M="${MIN_GAP_M:-0}"          # 0 = keep every blackout that passes, overlaps and all
SEGMENTS="${SEGMENTS:-1 2 3}"
INSTALL="${INSTALL:-1}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$REPO/front-end/android"
SEGDIR="$REPO/data/phone_data/segments"
NETDIR="$REPO/data/osm/phone"
ASSETS="$APP/app/src/main/assets/replay"
TESTDIR="$APP/app/src/test/java/com/sih2026/nav/live/engine"
PICKER="$APP/app/src/main/java/com/sih2026/nav/ui/components/ClipPickerSheet.kt"
WORK="$APP/app/build/trichy_clips"

export JAVA_HOME="${JAVA_HOME:-$HOME/tools/jdk17}"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
GRADLE="${GRADLE:-$HOME/tools/gradle-8.4/bin/gradle}"
ADB="$ANDROID_HOME/platform-tools/adb"

say()  { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mSTOP: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------------------------------------------------
say "1/6  checking what is needed"
[ -x "$JAVA_HOME/bin/java" ] || die "no JDK 17 at $JAVA_HOME (set JAVA_HOME)"
[ -x "$GRADLE" ]             || die "no Gradle at $GRADLE (set GRADLE)"
[ -d "$APP/app" ]            || die "no Android app at $APP"
[ -f "$PICKER" ]             || die "no ClipPickerSheet.kt at $PICKER"
[ -f "$ASSETS/index.json" ]  || die "no replay index at $ASSETS/index.json"
[ -f "$APP/app/src/main/assets/live/motion_deploy_all.hgb" ] || die "stop classifier asset missing"
command -v python3 >/dev/null || die "python3 is needed to merge index.json"
ls "$NETDIR"/*.roadnet.bin >/dev/null 2>&1 || die "no road networks in $NETDIR (front-end/android/App_Export/export_roadnet.py)"
[ -f "$NETDIR/tiruchirappalli.roadnet.bin" ] || echo "   warning: no tiruchirappalli.roadnet.bin — clips would have no map"

declare -A SEGFILE=([1]="1_outbound.csv.gz" [2]="2_town_tuning.csv.gz" [3]="3_return.csv.gz")
mkdir -p "$WORK/in"
rm -f "$WORK/in/"*
for s in $SEGMENTS; do
    f="$SEGDIR/${SEGFILE[$s]:-missing}"
    [ -f "$f" ] || die "segment $s not found: $f"
    ln -s "$f" "$WORK/in/seg${s}.csv.gz"
    echo "   segment $s: $(basename "$f") ($(du -h "$f" | cut -f1))"
done
echo "   keep what averages under ${CUT_PCT}% · measured from ${FROM_M} m on · starts ${MIN_GAP_M} m apart · at most ${MAX_PER_SEG} per segment"

# ---------------------------------------------------------------------------------------------------------------------
say "2/6  writing the exporter (TrichyClipExportTest.kt, runs only when TRICHY_EXPORT=1)"
cat > "$TESTDIR/TrichyClipExportTest.kt" <<'KOTLIN'
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
                       val meanPct: Double, val meanBasePct: Double, val maxPct: Double, val distM: Double, val durS: Double, val avgKmh: Double,
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
        val meanBasePct = scored.sumOf { pct(nmDrift[it], tDist[it]) } / scored.size
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
                append("\"mean_drift_pct\":${num(meanPct, 2)},\"mean_base_pct\":${num(meanBasePct, 2)},")
                append("\"max_drift_pct\":${num(maxPct, 2)},")
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
            meanPct, meanBasePct, maxPct, distM, durS, avgKmh, turns)
    }

    private fun infoJson(id: String, c: Clip): String {
        fun num(x: Double, dec: Int) = String.format(Locale.US, "%.${dec}f", x)
        val band = when { c.avgKmh < 40 -> "slow"; c.avgKmh < 50 -> "mixed"; c.avgKmh < 70 -> "ps_60"; else -> "fast" }
        return "  {\"id\":\"$id\",\"driver\":\"TRICHY\",\"role\":\"live ride\"," +
            "\"drive\":\"${label(c.seg, c.kind)}\",\"session\":${c.seg},\"band\":\"$band\",\"turns\":${c.turns}," +
            "\"avg_kmh\":${num(c.avgKmh, 1)},\"distance_m\":${num(c.distM, 1)},\"duration_s\":${num(c.durS, 1)}," +
            "\"final_drift_m\":${num(c.finalM, 1)},\"final_drift_pct\":${num(c.finalPct, 2)}," +
            "\"final_base_m\":${num(c.baseM, 1)},\"final_base_pct\":${num(c.basePct, 2)}," +
            "\"mean_drift_pct\":${num(c.meanPct, 2)},\"mean_base_pct\":${num(c.meanBasePct, 2)}}"
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
KOTLIN
echo "   $TESTDIR/TrichyClipExportTest.kt"

# ---------------------------------------------------------------------------------------------------------------------
say "3/6  replaying the segments through the engine (a few minutes per segment)"
rm -rf "$WORK/out"; mkdir -p "$WORK/out"
cd "$APP"
TRICHY_EXPORT=1 TRICHY_OUT="$WORK/out" CUT_PCT="$CUT_PCT" FROM_M="$FROM_M" MAX_PER_SEG="$MAX_PER_SEG" MIN_GAP_M="$MIN_GAP_M" \
    "$GRADLE" cleanTestDebugUnitTest testDebugUnitTest --no-daemon --console=plain \
    --tests '*TrichyClipExportTest*' -Ddrive="$WORK/in" 2>&1 | tee "$WORK/export_run.txt" \
    | grep -v '^> Task\|^$' || true
grep -q "exportTrichyClips PASSED\|clips written to" "$WORK/export_run.txt" \
    || die "the export did not finish — see $WORK/export_run.txt"
[ -f "$WORK/out/trichy_index.json" ] || die "the export wrote no index (was it skipped? see $WORK/export_run.txt)"
N=$(python3 -c "import json;print(len(json.load(open('$WORK/out/trichy_index.json'))))")
[ "$N" -gt 0 ] || die "no blackout averaged under ${CUT_PCT}%. Try CUT_PCT=15. Every candidate: $WORK/out/seg*_candidates.csv"

# ---------------------------------------------------------------------------------------------------------------------
say "4/6  adding $N clips, and giving the England clips readable names"
rm -f "$ASSETS"/trichy_seg*.json
cp "$WORK/out"/trichy_seg*.json "$ASSETS/"
[ -f "$ASSETS/index.json.before_trichy" ] || cp "$ASSETS/index.json" "$ASSETS/index.json.before_trichy"
FROM_M="$FROM_M" python3 - "$ASSETS" "$WORK/out/trichy_index.json" <<'PY'
import json, os, sys
assets, new_path = sys.argv[1], sys.argv[2]
index_path = os.path.join(assets, "index.json")
index = json.load(open(index_path))
new = json.load(open(new_path))
england = [c for c in index["clips"] if not c["id"].startswith("trichy_")]

# The England clips come from IO-VNBD and are titled with its codes ("S3c", "Vta1a", "Y1"), which say nothing on a
# phone screen. Rename them "England ride N" per driver — deterministic, so re-running gives the same names — and keep
# the dataset code in the clip under dataset_drive so a number can still be traced back.
ride = {}
for c in sorted(england, key=lambda c: c["id"]):
    d = c["driver"]
    ride[d] = ride.get(d, 0) + 1
    code = c.get("dataset_drive", c["drive"])
    name = "England ride %d" % ride[d]
    c["dataset_drive"], c["drive"] = code, name
    path = os.path.join(assets, c["id"] + ".json")
    if os.path.exists(path):                      # the clip file carries its own copy of these fields
        clip = json.load(open(path))
        clip["dataset_drive"], clip["drive"] = code, name
        json.dump(clip, open(path, "w"))
    print("   %-22s driver %s · %-6s -> %s" % (c["id"], d, code, name))

index["clips"] = england + new

# The picker shows the average drift over the blackout, not the one number at its end, so every clip carries its own
# average. The England clips predate it: compute theirs from the tracks already stored in them, the same way.
from_m = float(os.environ.get("FROM_M", "100"))
for c in index["clips"]:
    path = os.path.join(assets, c["id"] + ".json")
    clip = json.load(open(path))
    dist, dr, nm = clip["true_dist_m"], clip["drift_pct"], clip["nomap_drift_pct"]
    k = [i for i in range(len(dist)) if dist[i] >= from_m] or list(range(len(dist)))
    mean = round(sum(dr[i] for i in k) / len(k), 2)
    base = round(sum(nm[i] for i in k) / len(k), 2)
    clip["mean_drift_pct"], clip["mean_base_pct"] = mean, base
    c["mean_drift_pct"], c["mean_base_pct"] = mean, base
    json.dump(clip, open(path, "w"))

json.dump(index, open(index_path, "w"), indent=1)
print("   index.json: %d England clips renamed + %d Trichy clips added, all with their average drift" % (len(england), len(new)))
PY
# the picker's chips read "DRIVER A"; a longer group name is shown as itself ("TRICHY")
if grep -q 'text = "DRIVER \$d",' "$PICKER"; then
    sed -i 's/text = "DRIVER \$d",/text = if (d.length == 1) "DRIVER $d" else d,/' "$PICKER"
    echo "   ClipPickerSheet.kt: group chip shows TRICHY"
fi
du -ch "$ASSETS"/trichy_seg*.json | tail -1 | sed 's/^/   size of the new clips: /'

# ---------------------------------------------------------------------------------------------------------------------
say "5/6  building the APK"
"$GRADLE" assembleDebug --no-daemon --console=plain 2>&1 | tail -5
APK="$APP/app/build/outputs/apk/debug/app-debug.apk"
[ -f "$APK" ] || die "no APK built"

# ---------------------------------------------------------------------------------------------------------------------
say "6/6  installing"
if [ "$INSTALL" = "1" ] && [ -x "$ADB" ] && "$ADB" get-state >/dev/null 2>&1; then
    "$ADB" install -r "$APK" && echo "   installed: open SIH Nav Live → REPLAY DATASET CLIPS → TRICHY"
else
    echo "   no phone connected (or INSTALL=0). Later:  $ADB install -r $APK"
fi

say "the clips"
cat "$WORK/out/summary.txt"
cat <<EOF

   Kept: every blackout whose drift averaged under ${CUT_PCT}% of the distance travelled, from ${FROM_M} m onwards.
   cyan arrow = 248 Hz engine with the Tiruchirappalli map · red dashed = same engine without the map · green = GPS
   TRICHY groups all three live rides (out, town, back); "GPS off by hand" marks the blackouts you switched yourself.
   England clips are now "England ride N" per driver; the IO-VNBD code stays in the clip as dataset_drive.

   These are the blackouts that went well, not a median: over all 56 blackouts of the return ride the engine sits at
   15.8% at 1 km (round2/phone_data/README.md). Every candidate with its score, kept or not:
   $WORK/out/seg*_candidates.csv   ·   full log: $WORK/export_run.txt
   Undo: restore $ASSETS/index.json.before_trichy and delete $ASSETS/trichy_seg*.json
EOF
