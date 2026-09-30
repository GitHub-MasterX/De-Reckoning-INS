package com.sih2026.nav.live.engine

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs

/** The Kotlin features and trees against scikit-learn on 1,000 real IO-VNBD windows. */
class MotionModelTest {
    @Test
    fun matchesScikitLearn() {
        val model = MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes())
        val bytes = javaClass.getResourceAsStream("/motion_fixture.bin")!!.readBytes()
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        check(String(ByteArray(4).also { b.get(it) }) == "MFX1")
        val n = b.int
        var exactFeatures = 0
        var worstFeature = 0.0
        var worstRaw = 0.0
        var decisionsOnPythonFeatures = 0
        var decisionsOnKotlinFeatures = 0
        repeat(n) {
            val acc = DoubleArray(60) { b.double }
            val gyr = DoubleArray(60) { b.double }
            val expected = FloatArray(26) { b.float }
            val raw = b.double
            val stationary = b.get().toInt() != 0
            val f = MotionModel.features(acc, gyr)
            var allExact = true
            for (k in 0 until 26) {
                if (f[k] != expected[k] && !(f[k].isNaN() && expected[k].isNaN())) allExact = false
                if (!f[k].isNaN()) worstFeature = maxOf(worstFeature, abs((f[k] - expected[k]).toDouble()))
            }
            if (allExact) exactFeatures++
            worstRaw = maxOf(worstRaw, abs(model.rawScore(expected) - raw))
            if (model.isStationary(expected) == stationary) decisionsOnPythonFeatures++
            if (model.isStationary(f) == stationary) decisionsOnKotlinFeatures++
        }
        println("motion model: $n windows · all 26 features bit-identical in $exactFeatures · largest feature gap " +
            "%.2e · largest raw-score gap %.2e · decisions equal on Python features $decisionsOnPythonFeatures/$n, "
                .format(worstFeature, worstRaw) + "on Kotlin features $decisionsOnKotlinFeatures/$n")
        assertEquals(n, decisionsOnPythonFeatures)
        assertEquals(n, decisionsOnKotlinFeatures)
        assertTrue(worstRaw < 1e-9)
        assertTrue(worstFeature < 1e-4)
    }
}
