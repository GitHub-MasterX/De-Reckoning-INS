package com.sih2026.nav.live.engine

import com.sih2026.nav.live.engine.Fixtures.doubles
import com.sih2026.nav.live.engine.Fixtures.string
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import kotlin.math.abs

/** Calibration against round2/core/calibration.py on 20 blackouts' GNSS history. */
class CalibrationTest {
    @Test
    fun matchesPython() {
        val b = Fixtures.open(File(Fixtures.fixtureDir, "calibration_fixture.bin"), "CFX1")
        val n = b.int
        val names = arrayOf(null, "rate", "window", "window_recent_bias")
        var worstAxis = 0.0; var worstScale = 0.0; var worstBias = 0.0
        repeat(n) {
            val id = b.string()
            val rows = b.int
            val t = b.doubles(rows); val gyr = b.doubles(3 * rows); val v = b.doubles(rows); val heading = b.doubles(rows)
            val method = names[b.get().toInt()]
            val axis = b.doubles(3); val scale = b.double; val bias = b.double
            val cal = Calibration.engine(t, gyr, v, heading)
            assertEquals("$id method", method, cal?.method)
            if (cal != null) {
                val da = (0 until 3).maxOf { abs(cal.axis[it] - axis[it]) }
                worstAxis = maxOf(worstAxis, da)
                worstScale = maxOf(worstScale, abs(cal.scale - scale))
                worstBias = maxOf(worstBias, abs(cal.bias - bias))
                println("  %-22s %-6s scale %.6f (python %.6f)  bias %+.6f (python %+.6f)  axis gap %.1e"
                    .format(id, cal.method, cal.scale, scale, cal.bias, bias, da))
            }
        }
        println("calibration: $n cases · largest gaps: axis %.2e, scale %.2e, bias %.2e rad/s".format(worstAxis, worstScale, worstBias))
        assertTrue(worstAxis < 1e-6)
        assertTrue(worstScale < 1e-6)
        assertTrue(worstBias < 1e-8)
    }
}
