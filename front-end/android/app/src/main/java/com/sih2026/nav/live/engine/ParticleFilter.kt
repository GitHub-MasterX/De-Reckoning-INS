package com.sih2026.nav.live.engine

import java.util.Random
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.hypot
import kotlin.math.ln
import kotlin.math.sqrt

/** The frozen settings: particle.DEFAULTS overridden by round2/out/pf_params.json (step 6, tuned on A and B only). */
data class PfParams(
    val n: Int = 500,
    val radius0: Double = 25.0,
    val bearing0Deg: Double = 60.0,
    val sigmaPos0: Double = 5.0,
    val sigmaHead0Deg: Double = 15.0,
    val sigmaOff0: Double = 1.5,
    val sigmaV0: Double = 0.04,
    val qSpeed: Double = 0.4,
    val speedPull: Double = 0.0,
    val vMin: Double = 0.5,
    val vMax: Double = 45.0,
    val updateS: Double = 2.0,
    val sigmaTurnDeg: Double = 10.0,
    val sigmaAbsDeg: Double = 15.0,
    val sigmaChoiceDeg: Double = 45.0,
    val classLogprior: DoubleArray = doubleArrayOf(0.0, 0.0, 0.0, 0.0, 0.0, -0.2, -0.4, -0.7, -1.2, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5),
    val speedLimitSlack: Double = 1.25,
    val sigmaLimit: Double = 3.0,
    val essFrac: Double = 0.5,
    val roughOff: Double = 2.0,
    val roughSpeed: Double = 0.3,
    val badDeg: Double = 60.0,
    val badUpdates: Int = 3,
    val reseedRadius: Double = 30.0,
    val clusterM: Double = 40.0,
    val drBlendM: Double = 100.0
)

/**
 * The road-constrained particle filter — round2/core/particle.py, stepped one 10 Hz row at a time.
 *
 * Each particle is a guess: a drivable direction of a road, how far along it, and how fast.
 *   every row      the guess drives on; at a junction it picks an exit, favouring the one nearest the gyro heading
 *   every 2 s      guesses whose roads turned unlike the gyro, or point away from its heading, lose weight;
 *                  when too few carry the weight they are resampled
 *   fallback       if every guess disagrees for 3 updates in a row, it re-seeds around plain dead reckoning
 * The reported estimate hands over from dead reckoning to the map between 100 m and 200 m from the fix.
 *
 * The random numbers differ from numpy's, so a run agrees with Python's statistically, not number for number.
 */
class ParticleFilter(
    private val net: RoadNetwork,
    private val p: PfParams,
    private val lat0: Double,
    private val lon0: Double,
    course0: Double,
    private val speed0: Double,
    private val rng: Random
) {
    private val n = p.n
    private var edge = IntArray(n)
    private var off = DoubleArray(n)
    private var v = DoubleArray(n)
    private var logw = DoubleArray(n)
    private var turn = DoubleArray(n)
    private var dist = DoubleArray(n)
    private val upd = maxOf(1, Math.round(p.updateS * Calibration.FS).toInt())

    val seeded: Boolean
    private var row = 0
    private var bad = 0
    private var psiPrev = course0
    var reseeds = 0; private set
    var reseedFailed = 0; private set
    var fallbackRows = 0; private set
    var ess = Double.NaN; private set

    init {
        seeded = seed(lat0, lon0, course0, speed0, p.radius0)
    }

    private fun seed(lat: Double, lon: Double, course: Double, speed: Double, radius: Double): Boolean {
        val c = net.candidates(lat, lon, course, radius, p.bearing0Deg)
        if (c.size == 0) return false
        val w = DoubleArray(c.size) {
            val a = c.dist[it] / p.sigmaPos0
            val b = c.dpsi[it] / Math.toRadians(p.sigmaHead0Deg)
            exp(-a * a / 2 - b * b / 2)
        }
        val total = w.sum()
        if (!total.isFinite() || total <= 0) return false
        val cdf = DoubleArray(c.size)
        var acc = 0.0
        for (i in w.indices) { acc += w[i] / total; cdf[i] = acc }
        for (k in 0 until n) {
            val u = rng.nextDouble()
            var pick = cdf.indexOfFirst { it > u }
            if (pick < 0) pick = c.size - 1
            edge[k] = c.edges[pick]
            off[k] = (c.along[pick] + rng.nextGaussian() * p.sigmaOff0).coerceIn(0.0, net.edgeLen[edge[k]])
            v[k] = (speed * (1.0 + rng.nextGaussian() * p.sigmaV0)).coerceIn(p.vMin, p.vMax)
            logw[k] = 0.0; turn[k] = 0.0; dist[k] = 0.0
        }
        return true
    }

    /** Moves particles past the ends of their roads, choosing an exit at each junction (particle._advance). */
    private fun advance(psiNow: Double) {
        val sig = Math.toRadians(p.sigmaChoiceDeg)
        val kMax = 6
        val lp = DoubleArray(kMax)
        val cand = IntArray(kMax)
        for (k in 0 until n) {
            var rounds = 0
            while (rounds < 8 && logw[k].isFinite() && off[k] >= net.edgeLen[edge[k]]) {
                rounds++
                off[k] -= net.edgeLen[edge[k]]
                val node = net.edgeTo[edge[k]]
                val base = net.outPtr[node]
                val deg = net.outPtr[node + 1] - base
                if (deg == 0) { logw[k] = Double.NEGATIVE_INFINITY; off[k] = 0.0; break }
                val rev = net.edgeRev[edge[k]]
                var anyAllowed = false
                for (j in 0 until kMax) {
                    if (j >= deg) { lp[j] = Double.NEGATIVE_INFINITY; cand[j] = -1; continue }
                    cand[j] = net.outEdges[base + j]
                    if (cand[j] != rev) anyAllowed = true
                }
                for (j in 0 until minOf(deg, kMax)) {
                    val allowed = if (anyAllowed) cand[j] != rev else true      // U-turn only if nowhere else
                    lp[j] = if (!allowed) Double.NEGATIVE_INFINITY else {
                        val d = Geo.wrap(net.edgeBearing[cand[j]] - psiNow)
                        -(d * d) / (2 * sig * sig) + p.classLogprior[net.segClass[net.edgeSeg[cand[j]]].toInt()]
                    }
                }
                var pick = -1
                var best = Double.NEGATIVE_INFINITY
                for (j in 0 until kMax) {
                    val u = rng.nextDouble().coerceAtLeast(Double.MIN_VALUE)
                    val score = lp[j] - ln(-ln(u))                                 // + Gumbel noise
                    if (pick < 0 || score > best) { best = score; pick = j }
                }
                if (!lp[pick].isFinite()) { logw[k] = Double.NEGATIVE_INFINITY; off[k] = 0.0; break }
                val oldBearing = net.edgeBearing[edge[k]]
                edge[k] = cand[pick]
                turn[k] += Geo.wrap(net.edgeBearing[edge[k]] - oldBearing)
            }
        }
    }

    private fun weights(): DoubleArray? {
        var mx = Double.NEGATIVE_INFINITY
        for (x in logw) if (x.isFinite() && x > mx) mx = x
        if (!mx.isFinite()) return null
        val w = DoubleArray(n) { if (logw[it].isFinite()) exp(logw[it] - mx) else 0.0 }
        val s = w.sum()
        if (s <= 0) return null
        for (i in w.indices) w[i] /= s
        return w
    }

    /**
     * Moves from the current row to the next. `psiNow` is the gyro heading of the current row, `psiNext` of the next,
     * `stationary` belongs to the current row, `dt` is the step to the next row. `drEast`, `drNorth` are the plain
     * dead-reckoning position of the next row, for the fallback.
     */
    fun step(
        psiNow: Double, psiNext: Double, stationary: Boolean, dt: Double, drEast: Double, drNorth: Double,
        speedChange: Double = Double.NaN
    ) {
        if (!seeded) return
        val d = maxOf(dt, 0.0)
        if (!stationary) {
            val sd = p.qSpeed * sqrt(maxOf(d, 1e-6))
            for (k in 0 until n) {
                // round 2: each guess's speed wanders on its own. 248 Hz engine (speedChange given): each guess
                // follows the measured change of speed, and wanders only by what the measurement cannot explain
                val drift = if (speedChange.isNaN()) p.speedPull * (speed0 - v[k]) * d else speedChange
                v[k] = (v[k] + drift + rng.nextGaussian() * sd).coerceIn(p.vMin, p.vMax)
                off[k] += v[k] * d
                dist[k] += v[k] * d
            }
        } else if (!speedChange.isNaN()) {
            for (k in 0 until n) v[k] = (v[k] + speedChange).coerceIn(p.vMin, p.vMax)
        }
        advance(psiNow)
        row++
        if (row % upd != 0) return

        val dPsi = psiNext - psiPrev
        val sTurn = Math.toRadians(p.sigmaTurnDeg)
        val sAbs = Math.toRadians(p.sigmaAbsDeg)
        val mism = DoubleArray(n)
        for (k in 0 until n) {
            mism[k] = Geo.wrap(turn[k] - dPsi)
            logw[k] += -(mism[k] * mism[k]) / (2 * sTurn * sTurn)
            val a = Geo.wrap(net.edgeBearing[edge[k]] - psiNext)
            logw[k] += -(a * a) / (2 * sAbs * sAbs)
            val limit = net.segMaxspeed[net.edgeSeg[edge[k]]] / 3.6
            if (limit.isFinite()) {
                val excess = maxOf(0.0, v[k] - p.speedLimitSlack * limit)
                logw[k] += -(excess * excess) / (2 * p.sigmaLimit * p.sigmaLimit)
            }
            turn[k] = 0.0
        }
        psiPrev = psiNext

        val w = weights()
        if (w == null) {
            bad = p.badUpdates
        } else {
            var minMism = Double.POSITIVE_INFINITY
            for (k in 0 until n) if (logw[k].isFinite()) minMism = minOf(minMism, abs(mism[k]))
            bad = if (Math.toDegrees(minMism) > p.badDeg) bad + 1 else 0
            var sq = 0.0
            for (x in w) sq += x * x
            ess = 1.0 / sq
            if (ess < p.essFrac * n) {
                val cum = DoubleArray(n)
                var acc = 0.0
                for (i in 0 until n) { acc += w[i]; cum[i] = acc }
                val u0 = rng.nextDouble()
                val idx = IntArray(n)
                var j = 0
                for (i in 0 until n) {
                    val target = (u0 + i) / n
                    while (j < n - 1 && cum[j] < target) j++
                    idx[i] = j
                }
                edge = IntArray(n) { edge[idx[it]] }
                off = DoubleArray(n) { off[idx[it]] }
                v = DoubleArray(n) { v[idx[it]] }
                dist = DoubleArray(n) { dist[idx[it]] }
                turn = DoubleArray(n) { turn[idx[it]] }
                for (k in 0 until n) {
                    off[k] = (off[k] + rng.nextGaussian() * p.roughOff).coerceIn(0.0, net.edgeLen[edge[k]])
                    v[k] = (v[k] + rng.nextGaussian() * p.roughSpeed).coerceIn(p.vMin, p.vMax)
                }
                logw = DoubleArray(n)
            } else {
                for (k in 0 until n) logw[k] = ln(maxOf(w[k], 1e-300))
            }
        }
        if (bad >= p.badUpdates) {                     // the map explains nothing: start again on it
            val ll = Geo.invEnu(drEast, drNorth, lat0, lon0)
            val medianV = Calibration.median(v)
            val medianDist = Calibration.median(dist)
            val keep = arrayOf(edge.copyOf(), off.copyOf(), v.copyOf(), logw.copyOf(), turn.copyOf(), dist.copyOf())
            if (seed(ll[0], ll[1], psiNext, medianV, p.reseedRadius)) {
                dist.fill(medianDist)
                reseeds++
            } else {
                edge = keep[0] as IntArray; off = keep[1] as DoubleArray; v = keep[2] as DoubleArray
                logw = keep[3] as DoubleArray; turn = keep[4] as DoubleArray; dist = keep[5] as DoubleArray
                reseedFailed++
            }
            bad = 0
            psiPrev = psiNext
        }
    }

    /**
     * The reported position of the next row: east, north (metres from the fix), distance, and whether it came from
     * the map. drEast/drNorth/drDist are plain dead reckoning at the same row.
     */
    fun estimate(drEast: Double, drNorth: Double, drDist: Double): DoubleArray {
        val w = if (seeded) weights() else null
        if (w == null) {
            fallbackRows++
            return doubleArrayOf(drEast, drNorth, drDist, 0.0)
        }
        val e = DoubleArray(n)
        val nn = DoubleArray(n)
        val tmp = DoubleArray(2)
        for (k in 0 until n) {
            val s = net.edgeSeg[edge[k]]
            val f = (off[k] / maxOf(net.edgeLen[edge[k]], 1e-6)).coerceIn(0.0, 1.0)
            val fwd = net.edgeDir[edge[k]] > 0
            val a = if (fwd) net.segU[s] else net.segV[s]
            val b = if (fwd) net.segV[s] else net.segU[s]
            val lat = net.nodeLat[a] + f * (net.nodeLat[b] - net.nodeLat[a])
            val lon = net.nodeLon[a] + f * (net.nodeLon[b] - net.nodeLon[a])
            Geo.enu(lat, lon, lat0, lon0, tmp)
            e[k] = tmp[0]; nn[k] = tmp[1]
        }
        var best = 0
        for (k in 1 until n) if (w[k] > w[best]) best = k
        var sw = 0.0
        val near = BooleanArray(n) { hypot(e[it] - e[best], nn[it] - nn[best]) <= p.clusterM }
        for (k in 0 until n) if (near[k]) sw += w[k]
        var east = 0.0; var north = 0.0; var d = 0.0
        if (sw <= 0) {
            east = e[best]; north = nn[best]; d = dist[best]
        } else {
            for (k in 0 until n) if (near[k]) { val ww = w[k] / sw; east += ww * e[k]; north += ww * nn[k]; d += ww * dist[k] }
        }
        val share = ((drDist - p.drBlendM) / 100.0).coerceIn(0.0, 1.0)     // hand over from the fix to the map
        return doubleArrayOf(
            share * east + (1 - share) * drEast,
            share * north + (1 - share) * drNorth,
            share * d + (1 - share) * drDist,
            if (share > 0.5) 1.0 else 0.0
        )
    }
}
