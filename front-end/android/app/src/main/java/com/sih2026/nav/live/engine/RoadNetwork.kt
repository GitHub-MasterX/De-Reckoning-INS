package com.sih2026.nav.live.engine

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.hypot

/**
 * A drivable road network cut for the phone by round2/phone/export_roadnet.py — the port of round2/core/roadnet.py
 * the particle filter needs: the graph, and the nearest-road search.
 *
 * Python finds nearby roads with a KD-tree over points every 25 m along each segment; here a sorted grid of 25 m
 * cells over the same points plays that part. Both are exhaustive for the radius asked, and the exact distance test
 * that follows is the same, so both return the same roads.
 */
class RoadNetwork(bytes: ByteBuffer) {
    val name: String
    val south: Double
    val west: Double
    val north: Double
    val east: Double

    val nodeLat: DoubleArray
    val nodeLon: DoubleArray
    val segU: IntArray
    val segV: IntArray
    val segLen: DoubleArray
    val segBearing: DoubleArray
    val segClass: ByteArray
    val segMaxspeed: FloatArray
    val segFwd: BooleanArray
    val segBwd: BooleanArray
    val segEdgeFwd: IntArray
    val segEdgeBwd: IntArray
    val edgeTo: IntArray
    val edgeSeg: IntArray
    val edgeDir: ByteArray
    val edgeBearing: DoubleArray
    val outPtr: IntArray
    val outEdges: IntArray

    val edgeLen: DoubleArray
    val edgeRev: IntArray
    private val sx0: DoubleArray
    private val sy0: DoubleArray
    private val sx1: DoubleArray
    private val sy1: DoubleArray

    // nearest-road grid: sorted keys (cell index shifted left 24 bits, plus segment id)
    private val gridKeys: LongArray
    private val gx0: Long
    private val gy0: Long
    private val gRows: Long

    val kmOfRoad: Double get() = segLen.sum() / 1000.0

    init {
        val b = bytes.order(ByteOrder.LITTLE_ENDIAN)
        val magic = ByteArray(4).also { b.get(it) }
        require(String(magic) == "RNW1") { "not a road network file" }
        val n = b.int
        val m = b.int
        val e = b.int
        south = b.double; west = b.double; north = b.double; east = b.double
        name = String(ByteArray(b.int).also { b.get(it) })
        nodeLat = DoubleArray(n) { b.double }
        nodeLon = DoubleArray(n) { b.double }
        segU = IntArray(m) { b.int }
        segV = IntArray(m) { b.int }
        segLen = DoubleArray(m) { b.double }
        segBearing = DoubleArray(m) { b.double }
        segClass = ByteArray(m) { b.get() }
        segMaxspeed = FloatArray(m) { b.float }
        segFwd = BooleanArray(m) { b.get().toInt() != 0 }
        segBwd = BooleanArray(m) { b.get().toInt() != 0 }
        segEdgeFwd = IntArray(m) { b.int }
        segEdgeBwd = IntArray(m) { b.int }
        edgeTo = IntArray(e) { b.int }
        edgeSeg = IntArray(e) { b.int }
        edgeDir = ByteArray(e) { b.get() }
        edgeBearing = DoubleArray(e) { b.double }
        outPtr = IntArray(n + 1) { b.int }
        outEdges = IntArray(e) { b.int }

        edgeLen = DoubleArray(e) { segLen[edgeSeg[it]] }
        edgeRev = IntArray(e) { if (edgeDir[it] > 0) segEdgeBwd[edgeSeg[it]] else segEdgeFwd[edgeSeg[it]] }
        sx0 = DoubleArray(m) { Geo.planeX(nodeLat[segU[it]], nodeLon[segU[it]]) }
        sy0 = DoubleArray(m) { Geo.planeY(nodeLat[segU[it]]) }
        sx1 = DoubleArray(m) { Geo.planeX(nodeLat[segV[it]], nodeLon[segV[it]]) }
        sy1 = DoubleArray(m) { Geo.planeY(nodeLat[segV[it]]) }

        // points every SAMPLE_M along each segment, as roadnet.RoadNetwork samples them
        var total = 0L
        val k = IntArray(m) { maxOf(1, ceil(segLen[it] / SAMPLE_M).toInt()).also { c -> total += c } }
        var minX = Long.MAX_VALUE; var minY = Long.MAX_VALUE; var maxY = Long.MIN_VALUE
        for (s in 0 until m) {
            minX = minOf(minX, cell(minOf(sx0[s], sx1[s]))); minY = minOf(minY, cell(minOf(sy0[s], sy1[s])))
            maxY = maxOf(maxY, cell(maxOf(sy0[s], sy1[s])))
        }
        gx0 = minX - 2; gy0 = minY - 2; gRows = maxY - gy0 + 3
        val keys = LongArray(total.toInt())
        var w = 0
        for (s in 0 until m) {
            for (j in 0 until k[s]) {
                val f = (j + 0.5) / k[s]
                val x = sx0[s] + f * (sx1[s] - sx0[s])
                val y = sy0[s] + f * (sy1[s] - sy0[s])
                keys[w++] = (cellIndex(cell(x), cell(y)) shl 24) or s.toLong()
            }
        }
        keys.sort()
        gridKeys = keys
    }

    private fun cell(v: Double) = floor(v / SAMPLE_M).toLong()
    private fun cellIndex(cx: Long, cy: Long) = (cx - gx0) * gRows + (cy - gy0)

    fun contains(lat: Double, lon: Double) = lat in south..north && lon in west..east

    /** Every segment id with a sample point in a cell within `reach` metres of (x, y); may repeat ids. */
    private fun nearbySegments(x: Double, y: Double, reach: Double): IntArray {
        val out = ArrayList<Int>()
        for (cx in cell(x - reach)..cell(x + reach)) {
            for (cy in cell(y - reach)..cell(y + reach)) {
                if (cx < gx0 || cy < gy0 || cy - gy0 >= gRows) continue
                val lo = cellIndex(cx, cy) shl 24
                var i = lowerBound(lo)
                while (i < gridKeys.size && (gridKeys[i] ushr 24) == (lo ushr 24)) {
                    out += (gridKeys[i] and 0xFFFFFFL).toInt()
                    i++
                }
            }
        }
        return out.toIntArray()
    }

    private fun lowerBound(key: Long): Int {
        var lo = 0
        var hi = gridKeys.size
        while (lo < hi) {
            val mid = (lo + hi) ushr 1
            if (gridKeys[mid] < key) lo = mid + 1 else hi = mid
        }
        return lo
    }

    class Candidates(val edges: IntArray, val dist: DoubleArray, val dpsi: DoubleArray, val along: DoubleArray) {
        val size get() = edges.size
    }

    /**
     * roadnet.RoadNetwork.candidates: every drivable direction within `radius` of one point whose bearing is within
     * `maxBearingDeg` of `heading` (radians) — edge ids, distance (m), bearing difference (rad), metres along the edge.
     */
    fun candidates(lat: Double, lon: Double, heading: Double, radius: Double, maxBearingDeg: Double): Candidates {
        val x = Geo.planeX(lat, lon)
        val y = Geo.planeY(lat)
        val segs = nearbySegments(x, y, radius + SAMPLE_M / 2 + 1.0).distinct().sorted()
        val keepSeg = ArrayList<Int>(); val keepT = ArrayList<Double>(); val keepD = ArrayList<Double>()
        for (s in segs) {
            val ax = sx0[s]; val ay = sy0[s]
            val dx = sx1[s] - ax; val dy = sy1[s] - ay
            val t = (((x - ax) * dx + (y - ay) * dy) / maxOf(dx * dx + dy * dy, 1e-9)).coerceIn(0.0, 1.0)
            val d = hypot(x - (ax + t * dx), y - (ay + t * dy))
            if (d <= radius) { keepSeg += s; keepT += t; keepD += d }
        }
        val tol = Math.toRadians(maxBearingDeg)
        val edges = ArrayList<Int>(); val dist = ArrayList<Double>(); val dpsi = ArrayList<Double>(); val along = ArrayList<Double>()
        for (sign in intArrayOf(1, -1)) {
            for (k in keepSeg.indices) {
                val s = keepSeg[k]
                if (if (sign > 0) !segFwd[s] else !segBwd[s]) continue
                val dp = abs(Geo.wrap(heading - (segBearing[s] + if (sign > 0) 0.0 else Math.PI)))
                if (dp > tol) continue
                edges += if (sign > 0) segEdgeFwd[s] else segEdgeBwd[s]
                dist += keepD[k]
                dpsi += dp
                along += (if (sign > 0) keepT[k] else 1.0 - keepT[k]) * segLen[s]
            }
        }
        return Candidates(edges.toIntArray(), dist.toDoubleArray(), dpsi.toDoubleArray(), along.toDoubleArray())
    }

    companion object {
        const val SAMPLE_M = 25.0
        val CLASSES = arrayOf(
            "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
            "service", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link", "road"
        )

        /** Reads only the header: name, and the box the network covers (south, west, north, east). */
        fun header(bytes: ByteBuffer): Pair<String, DoubleArray> {
            val b = bytes.order(ByteOrder.LITTLE_ENDIAN)
            val magic = ByteArray(4).also { b.get(it) }
            require(String(magic) == "RNW1") { "not a road network file" }
            b.int; b.int; b.int
            val box = DoubleArray(4) { b.double }
            val name = String(ByteArray(b.int).also { b.get(it) })
            return name to box
        }
    }
}
