package com.sih2026.nav.live.engine

import com.sih2026.nav.live.engine.Fixtures.doubles
import com.sih2026.nav.live.engine.Fixtures.string
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import kotlin.math.abs
import kotlin.math.hypot

/**
 * The live engine fed whole recorded sessions row by row, as the phone feeds it.
 *
 *   fixes on every row   the engine sees what Python saw, so calibration and the map-free position 1 km into the
 *                        blackout must equal Python's
 *   fixes once a second  a real phone: calibration learns from interpolated fixes; results must stay close
 */
class LiveEngineCoreTest {

    private class Case(
        val id: String, val driver: String, val i: Int, val j: Int,
        val rows: DoubleArray, val method: String, val axis: DoubleArray, val scale: Double, val bias: Double,
        val dr: DoubleArray, val truth: DoubleArray, val seedA: DoubleArray, val seedB: DoubleArray
    ) {
        fun col(r: Int, c: Int) = rows[11 * r + c]
    }

    private val cases by lazy {
        val b = Fixtures.open(File(Fixtures.fixtureDir, "session_fixture.bin"), "SFX1")
        List(b.int) {
            val id = b.string(); val driver = b.string()
            val i = b.int; val j = b.int
            val rows = b.doubles(11 * (j + 1))
            val method = if (b.get().toInt() == 2) "window" else "rate"
            Case(id, driver, i, j, rows, method, b.doubles(3), b.double, b.double, b.doubles(3), b.doubles(3), b.doubles(2), b.doubles(2))
        }
    }
    private val model by lazy { MotionModel(File(Fixtures.assetDir, "live/motion_deploy_all.hgb").readBytes()) }
    private val england by lazy { RoadNetwork(ByteBuffer.wrap(File(Fixtures.fixtureDir, "england.roadnet.bin").readBytes())) }

    /** Runs one case; returns the engine's estimate and its map-free estimate at row j as east/north from the start fix. */
    private fun run(c: Case, fixEvery: Int, withNetwork: Boolean, seed: Long): Triple<DoubleArray, DoubleArray, BlackoutScore> {
        val core = LiveEngineCore(model, PfParams(), seed)
        if (withNetwork) core.network = england
        var out: LiveOutput? = null
        var start: BlackoutScore? = null
        for (r in 0..c.j) {
            out = core.onRow(c.col(r, 0), c.col(r, 1), c.col(r, 2), c.col(r, 3), c.col(r, 4), c.col(r, 5), c.col(r, 6))
            if (r % fixEvery == 0) core.onFix(Fix(c.col(r, 0), c.col(r, 7), c.col(r, 8), c.col(r, 10), c.col(r, 9), 3.0))
            if (r == c.i) start = core.startBlackout()?.current
        }
        checkNotNull(start)
        val lat0 = c.col(c.i, 7); val lon0 = c.col(c.i, 8)
        val est = Geo.enu(out!!.lat, out.lon, lat0, lon0)
        val noMap = Geo.enu(out.noMapLat, out.noMapLon, lat0, lon0)
        return Triple(est, noMap, core.score!!)
    }

    @Test
    fun fixesOnEveryRowReproducePython() {
        for (c in cases) {
            val (_, noMap, score) = run(c, fixEvery = 1, withNetwork = false, seed = 1)
            val cal = score.calibration
            assertEquals(c.id, c.method, cal.method)
            val axisGap = (0 until 3).maxOf { abs(cal.axis[it] - c.axis[it]) }
            val posGap = hypot(noMap[0] - c.dr[0], noMap[1] - c.dr[1])
            println("  %-18s %s x%.4f (python x%.4f) axis gap %.1e · map-free position 1 km in: %.2e m from Python's"
                .format(c.id, cal.method, cal.scale, c.scale, axisGap, posGap))
            assertTrue(axisGap < 1e-9 && abs(cal.scale - c.scale) < 1e-9 && abs(cal.bias - c.bias) < 1e-9)
            assertTrue(posGap < 1e-6)
        }
    }

    @Test
    fun oneHzFixesStayClose() {
        println("  case                 calibration (1 Hz vs Python)    no map: phone / python    with map: phone / python A, B")
        val phone = ArrayList<Double>(); val python = ArrayList<Double>()
        for (c in cases) {
            val (est, noMap, score) = run(c, fixEvery = 10, withNetwork = true, seed = 7)
            val td = c.truth[2]
            fun err(e: Double, n: Double) = 100 * hypot(e - c.truth[0], n - c.truth[1]) / td
            val pA = err(c.seedA[0], c.seedA[1]); val pB = err(c.seedB[0], c.seedB[1])
            val k = err(est[0], est[1])
            phone += k; python += (pA + pB) / 2
            println("  %-18s %-6s x%.3f vs x%.3f          %5.1f%% / %5.1f%%          %5.1f%% / %5.1f%%, %5.1f%%   (scored live: %.1f%% at %.0f m)"
                .format(c.id, score.calibration.method, score.calibration.scale, c.scale,
                    err(noMap[0], noMap[1]), err(c.dr[0], c.dr[1]), k, pA, pB, score.driftPct, score.trueDistanceM))
            assertTrue(abs(score.calibration.scale - c.scale) < 0.1)
        }
        println("  median with map: phone %.1f%%, python %.1f%%".format(
            Calibration.median(phone.toDoubleArray()), Calibration.median(python.toDoubleArray())))
    }
}
