package com.sih2026.nav.data.model

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * One recorded blackout from the IO-VNBD evaluation, exported by round2/step9_export_replay.py.
 *
 * Three tracks are stored at 10 Hz for the same instants:
 *   true    the car's own GNSS — the answer key, never an input to the engine
 *   pf      the round-2 estimate: gyro calibrated from pre-blackout GNSS history, held speed, road network
 *   noMap   the same engine without the map, so the gap between the two shows what the map buys
 */
data class ClipInfo(
    val id: String,
    val driver: String,
    val role: String,          // "test" (D, E) or "tuning" (A, B)
    val drive: String,
    val session: Int,
    val band: String,          // slow / mixed / ps_60 / fast — the driving-condition group
    val turns: Int,
    val avgKmh: Double,
    val distanceM: Double,
    val durationS: Double,
    val finalDriftM: Double,
    val finalDriftPct: Double,
    val finalBaseM: Double,
    val finalBasePct: Double,
    // averages over the blackout, from 100 m in: what the picker shows, since one end-of-blackout number says little
    // about how the estimate behaved on the way there
    val meanDriftPct: Double,
    val meanBasePct: Double
) {
    /** The problem statement's own case is 50-70 km/h; the groups are named in round2/DECISIONS.md. */
    val bandLabel: String
        get() = when (band) {
            "slow" -> "under 40 km/h"
            "mixed" -> "40-50 km/h"
            "ps_60" -> "50-70 km/h"
            "fast" -> "70+ km/h"
            else -> band
        }
}

class ReplayClip(
    val info: ClipInfo,
    val hz: Int,
    val engineSpeedKmh: Double,
    val leadInLat: DoubleArray,
    val leadInLon: DoubleArray,
    val leadInHeading: FloatArray,
    val leadInSpeedKmh: FloatArray,
    val trueLat: DoubleArray,
    val trueLon: DoubleArray,
    val trueHeading: FloatArray,
    val trueSpeedKmh: FloatArray,
    val trueDistM: FloatArray,
    val pfLat: DoubleArray,
    val pfLon: DoubleArray,
    val pfHeading: FloatArray,
    val pfOnMap: BooleanArray,
    val noMapLat: DoubleArray,
    val noMapLon: DoubleArray,
    val driftM: FloatArray,
    val driftPct: FloatArray,
    val noMapDriftM: FloatArray,
    val noMapDriftPct: FloatArray
) {
    val leadInFrames: Int get() = leadInLat.size
    val blackoutFrames: Int get() = trueLat.size
    val totalFrames: Int get() = leadInFrames + blackoutFrames
}

object ReplayLoader {

    // England (IO-VNBD) clips and Trichy clips live in separate asset folders; the id prefix says which.
    private const val ENGLAND_DIR = "England_test"
    private const val TRICHY_DIR = "Trichy_test"
    private fun dirFor(id: String) = if (id.startsWith("trichy_")) TRICHY_DIR else ENGLAND_DIR

    /** The clips bundled with the app, newest export wins. index.json sits at the assets root. */
    fun index(context: Context): List<ClipInfo> {
        val root = JSONObject(readRoot(context, "index.json"))
        val clips = root.getJSONArray("clips")
        return (0 until clips.length()).map { info(clips.getJSONObject(it)) }
    }

    fun load(context: Context, id: String): ReplayClip {
        val o = JSONObject(read(context, dirFor(id), "$id.json"))
        val lead = o.getJSONObject("lead_in")
        return ReplayClip(
            info = info(o),
            hz = o.getInt("hz"),
            engineSpeedKmh = o.getDouble("engine_speed_kmh"),
            leadInLat = doubles(lead.getJSONArray("lat")),
            leadInLon = doubles(lead.getJSONArray("lon")),
            leadInHeading = floats(lead.getJSONArray("heading")),
            leadInSpeedKmh = floats(lead.getJSONArray("speed_kmh")),
            trueLat = doubles(o.getJSONArray("true_lat")),
            trueLon = doubles(o.getJSONArray("true_lon")),
            trueHeading = floats(o.getJSONArray("true_heading")),
            trueSpeedKmh = floats(o.getJSONArray("true_speed_kmh")),
            trueDistM = floats(o.getJSONArray("true_dist_m")),
            pfLat = doubles(o.getJSONArray("pf_lat")),
            pfLon = doubles(o.getJSONArray("pf_lon")),
            pfHeading = floats(o.getJSONArray("pf_heading")),
            pfOnMap = booleans(o.getJSONArray("pf_on_map")),
            noMapLat = doubles(o.getJSONArray("nomap_lat")),
            noMapLon = doubles(o.getJSONArray("nomap_lon")),
            driftM = floats(o.getJSONArray("drift_m")),
            driftPct = floats(o.getJSONArray("drift_pct")),
            noMapDriftM = floats(o.getJSONArray("nomap_drift_m")),
            noMapDriftPct = floats(o.getJSONArray("nomap_drift_pct"))
        )
    }

    private fun info(o: JSONObject) = ClipInfo(
        id = o.getString("id"),
        driver = o.getString("driver"),
        role = o.getString("role"),
        drive = o.getString("drive"),
        session = o.getInt("session"),
        band = o.getString("band"),
        turns = o.getInt("turns"),
        avgKmh = o.getDouble("avg_kmh"),
        distanceM = o.getDouble("distance_m"),
        durationS = o.getDouble("duration_s"),
        finalDriftM = o.getDouble("final_drift_m"),
        finalDriftPct = o.getDouble("final_drift_pct"),
        finalBaseM = o.getDouble("final_base_m"),
        finalBasePct = o.getDouble("final_base_pct"),
        meanDriftPct = o.optDouble("mean_drift_pct", o.getDouble("final_drift_pct")),
        meanBasePct = o.optDouble("mean_base_pct", o.getDouble("final_base_pct"))
    )

    private fun read(context: Context, dir: String, name: String) =
        context.assets.open("$dir/$name").bufferedReader().use { it.readText() }

    private fun readRoot(context: Context, name: String) =
        context.assets.open(name).bufferedReader().use { it.readText() }

    private fun doubles(a: JSONArray) = DoubleArray(a.length()) { a.getDouble(it) }
    private fun floats(a: JSONArray) = FloatArray(a.length()) { a.getDouble(it).toFloat() }
    private fun booleans(a: JSONArray) = BooleanArray(a.length()) { a.getBoolean(it) }
}
