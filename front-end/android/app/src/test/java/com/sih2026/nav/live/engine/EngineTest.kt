package com.sih2026.nav.live.engine

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.util.Random
import kotlin.math.abs
import kotlin.math.hypot

/**
 * Dead reckoning must agree with Python to rounding. The particle filter uses different random numbers, so it must
 * agree in distribution: on the same 150 blackouts its median 2D drift at each checkpoint is compared with Python's
 * two seeds; wherever Python's two seeds give the identical answer (the hand-over from dead reckoning has not begun)
 * the port must give it too.
 */
class EngineTest {
    private val blackouts by lazy { Fixtures.blackouts() }

    @Test
    fun deadReckoningMatchesPython() {
        var worst = 0.0
        for (bo in blackouts) {
            val dr = DeadReckoning(bo.course0, bo.speed0)
            for (r in 0 until bo.rows - 1) {
                dr.step(bo.turnRate(r), bo.stationary[r], bo.t[r + 1] - bo.t[r])
                worst = maxOf(worst, abs(dr.east - bo.drEast[r + 1]), abs(dr.north - bo.drNorth[r + 1]), abs(dr.dist - bo.drDist[r + 1]))
            }
        }
        println("dead reckoning: ${blackouts.size} blackouts, ${blackouts.sumOf { it.rows }} rows · largest gap from Python %.2e m".format(worst))
        assertTrue(worst < 1e-6)
    }

    @Test
    fun particleFilterMatchesPythonInDistribution() {
        val t0 = System.nanoTime()
        val net = RoadNetwork(ByteBuffer.wrap(File(Fixtures.fixtureDir, "england.roadnet.bin").readBytes()))
        println("network: ${net.name}, %.0f km, loaded and indexed in %.1f s".format(net.kmOfRoad, (System.nanoTime() - t0) / 1e9))
        val metres = blackouts.first().checks.map { it.metres }
        val kotlin = List(2) { metres.associateWith { ArrayList<Double>() } }
        val pyA = metres.associateWith { ArrayList<Double>() }
        val pyB = metres.associateWith { ArrayList<Double>() }
        var deterministic = 0
        var deterministicWorst = 0.0
        var rowsRun = 0L
        val t1 = System.nanoTime()
        for ((nb, bo) in blackouts.withIndex()) {
            for (seed in 0 until 2) {
                val dr = DeadReckoning(bo.course0, bo.speed0)
                val pf = ParticleFilter(net, PfParams(), bo.lat0, bo.lon0, bo.course0, bo.speed0, Random(1000L * nb + seed))
                val atRow = bo.checks.associateBy { it.row }
                for (r in 0 until bo.rows - 1) {
                    val psiNow = dr.heading
                    val dt = bo.t[r + 1] - bo.t[r]
                    dr.step(bo.turnRate(r), bo.stationary[r], dt)
                    pf.step(psiNow, dr.heading, bo.stationary[r], dt, dr.east, dr.north)
                    val c = atRow[r + 1] ?: continue
                    val est = pf.estimate(dr.east, dr.north, dr.dist)
                    val err = 100 * hypot(est[0] - c.truth[0], est[1] - c.truth[1]) / c.truth[2]
                    kotlin[seed][c.metres]!!.add(err)
                    if (seed == 0) {
                        val a = 100 * hypot(c.seedA[0] - c.truth[0], c.seedA[1] - c.truth[1]) / c.truth[2]
                        val b = 100 * hypot(c.seedB[0] - c.truth[0], c.seedB[1] - c.truth[1]) / c.truth[2]
                        pyA[c.metres]!!.add(a); pyB[c.metres]!!.add(b)
                        if (abs(a - b) < 1e-9) {
                            deterministic++
                            deterministicWorst = maxOf(deterministicWorst, abs(err - a))
                        }
                    }
                }
                rowsRun += bo.rows - 1
            }
        }
        val msPerRow = (System.nanoTime() - t1) / 1e6 / rowsRun
        fun median(a: List<Double>) = Calibration.median(a.toDoubleArray())
        println("particle filter: ${blackouts.size} blackouts x 2 seeds, %.3f ms per 10 Hz row on this laptop".format(msPerRow))
        println("  metres   python A   python B   kotlin 1   kotlin 2      (median 2D drift, % of distance)")
        var worstGap = 0.0
        for (m in metres) {
            val a = median(pyA[m]!!); val b = median(pyB[m]!!)
            val k1 = median(kotlin[0][m]!!); val k2 = median(kotlin[1][m]!!)
            println("  %6d   %8.2f   %8.2f   %8.2f   %8.2f".format(m, a, b, k1, k2))
            worstGap = maxOf(worstGap, abs((k1 + k2) / 2 - (a + b) / 2))
        }
        println("  where Python's seeds agree exactly ($deterministic checkpoints): largest Kotlin gap %.2e points".format(deterministicWorst))
        println("  largest gap between the Kotlin and Python seed-averaged medians: %.2f points".format(worstGap))
        assertTrue(deterministicWorst < 1e-6)
        assertTrue(worstGap < 1.0)
    }
}
