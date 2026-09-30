package com.sih2026.nav.live.engine

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.ln
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Round 1's stationary classifier, exactly as trained: the `deploy_all` gradient-boosted trees from
 * models/motion_models.pkl, exported by round2/phone/export_motion_model.py. Nothing is refitted here.
 *
 * The feature contract is idr/features.py: 26 numbers over 20 samples at 10 Hz — accelerometer in m/s² including
 * gravity, gyroscope in rad/s. Sums follow numpy's pairwise order so the float32 features match Python's.
 */
class MotionModel(bytes: ByteArray) {

    private val nFeatures: Int
    private val baseline: Double
    private val feature: Array<IntArray>
    private val threshold: Array<DoubleArray>
    private val left: Array<IntArray>
    private val right: Array<IntArray>
    private val leaf: Array<BooleanArray>
    private val missingLeft: Array<BooleanArray>
    private val value: Array<DoubleArray>

    init {
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val magic = ByteArray(4).also { b.get(it) }
        require(String(magic) == "HGB1") { "not a motion model file" }
        nFeatures = b.int
        val nTrees = b.int
        baseline = b.double
        feature = Array(nTrees) { IntArray(0) }
        threshold = Array(nTrees) { DoubleArray(0) }
        left = Array(nTrees) { IntArray(0) }
        right = Array(nTrees) { IntArray(0) }
        leaf = Array(nTrees) { BooleanArray(0) }
        missingLeft = Array(nTrees) { BooleanArray(0) }
        value = Array(nTrees) { DoubleArray(0) }
        for (t in 0 until nTrees) {
            val n = b.int
            feature[t] = IntArray(n); threshold[t] = DoubleArray(n); left[t] = IntArray(n); right[t] = IntArray(n)
            leaf[t] = BooleanArray(n); missingLeft[t] = BooleanArray(n); value[t] = DoubleArray(n)
            for (k in 0 until n) {
                feature[t][k] = b.int
                threshold[t][k] = b.double
                left[t][k] = b.int
                right[t][k] = b.int
                leaf[t][k] = b.get().toInt() != 0
                missingLeft[t][k] = b.get().toInt() != 0
                value[t][k] = b.double
            }
        }
    }

    /** The summed tree score; scikit-learn predicts "stationary" (class 0) when it is <= 0. */
    fun rawScore(features: FloatArray): Double {
        require(features.size == nFeatures)
        var score = baseline
        for (t in feature.indices) {
            var k = 0
            while (!leaf[t][k]) {
                val v = features[feature[t][k]].toDouble()
                val goLeft = if (v.isNaN()) missingLeft[t][k] else v <= threshold[t][k]
                k = if (goLeft) left[t][k] else right[t][k]
            }
            score += value[t][k]
        }
        return score
    }

    fun isStationary(features: FloatArray): Boolean = rawScore(features) <= 0.0

    companion object {
        const val WINDOW = 20
        const val HOP = 5
        const val FS = 10.0
        private val BANDS = arrayOf(doubleArrayOf(0.5, 1.5), doubleArrayOf(1.5, 3.0), doubleArrayOf(3.0, 5.0))

        /** numpy's pairwise summation (add.reduce) for n <= 128 values starting at `from`. */
        internal fun pwSum(a: DoubleArray, from: Int, n: Int): Double {
            if (n < 8) {
                var s = 0.0
                for (i in 0 until n) s += a[from + i]
                return s
            }
            val r = DoubleArray(8) { a[from + it] }
            var i = 8
            while (i < n - (n % 8)) {
                for (j in 0 until 8) r[j] += a[from + i + j]
                i += 8
            }
            var s = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
            while (i < n) {
                s += a[from + i]; i++
            }
            return s
        }

        private fun mean(a: DoubleArray) = pwSum(a, 0, a.size) / a.size

        private fun std(a: DoubleArray): Double {
            val m = mean(a)
            val sq = DoubleArray(a.size) { val d = a[it] - m; d * d }
            return sqrt(pwSum(sq, 0, sq.size) / sq.size)
        }

        private fun meanAbsDiff(a: DoubleArray): Double {
            val d = DoubleArray(a.size - 1) { abs(a[it + 1] - a[it]) }
            return pwSum(d, 0, d.size) / d.size
        }

        /**
         * The 26 features of idr/features.py for one window. acc and gyr hold 20 rows of x, y, z, row by row
         * (index 3 * row + axis).
         */
        fun features(acc: DoubleArray, gyr: DoubleArray): FloatArray {
            require(acc.size == 3 * WINDOW && gyr.size == 3 * WINDOW)
            val am = DoubleArray(WINDOW) { r -> sqrt(sq3(acc, r)) }
            val gm = DoubleArray(WINDOW) { r -> sqrt(sq3(gyr, r)) }
            val f = ArrayList<Double>(26)
            f += mean(am); f += std(am); f += am.min(); f += am.max(); f += meanAbsDiff(am)
            f += mean(gm); f += std(gm); f += gm.max()
            for (c in 0 until 3) {
                val a = DoubleArray(WINDOW) { acc[3 * it + c] }
                val g = DoubleArray(WINDOW) { gyr[3 * it + c] }
                f += std(a); f += meanAbsDiff(a); f += std(g)
            }
            for (c in 0 until 3) {
                val a = DoubleArray(WINDOW) { acc[3 * it + c] }
                val m = mean(a)
                val x = DoubleArray(WINDOW) { a[it] - m }
                val power = DoubleArray(WINDOW / 2 + 1) { k ->
                    var re = 0.0
                    var im = 0.0
                    for (n in 0 until WINDOW) {
                        val ang = 2 * Math.PI * k * n / WINDOW
                        re += x[n] * cos(ang)
                        im -= x[n] * sin(ang)
                    }
                    val h = hypot(re, im)
                    h * h
                }
                for (band in BANDS) {
                    var s = 0.0
                    for (k in power.indices) {
                        val freq = k * FS / WINDOW
                        if (freq >= band[0] && freq < band[1]) s += power[k]
                    }
                    f += ln(s + 1e-9)
                }
            }
            return FloatArray(26) { f[it].toFloat() }
        }

        private fun sq3(a: DoubleArray, r: Int): Double {
            val x = a[3 * r]; val y = a[3 * r + 1]; val z = a[3 * r + 2]
            return x * x + y * y + z * z
        }
    }
}
