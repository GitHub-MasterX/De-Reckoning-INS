package com.sih2026.nav.live.engine

import org.junit.Assert.assertEquals
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.io.RandomAccessFile
import java.nio.channels.FileChannel
import java.util.Random

/** Every Tamil Nadu city network pushed to the phone loads, and its nearest-road search finds its own roads. */
class RoadNetworkTest {
    @Test
    fun cityNetworksLoadAndFindTheirRoads() {
        val files = Fixtures.fixtureDir.listFiles { f -> f.name.endsWith(".roadnet.bin") && f.name != "england.roadnet.bin" }
            ?.sortedBy { it.name }.orEmpty()
        assumeTrue("no city networks exported", files.isNotEmpty())
        for (f in files) {
            val t0 = System.nanoTime()
            val net = RandomAccessFile(f, "r").use { raf -> RoadNetwork(raf.channel.map(FileChannel.MapMode.READ_ONLY, 0, raf.length())) }
            val loadS = (System.nanoTime() - t0) / 1e9
            val rng = Random(0)
            var found = 0
            val tries = 300
            repeat(tries) {
                var s: Int
                do { s = rng.nextInt(net.segU.size) } while (net.segLen[s] < 20.0)
                val lat = (net.nodeLat[net.segU[s]] + net.nodeLat[net.segV[s]]) / 2
                val lon = (net.nodeLon[net.segU[s]] + net.nodeLon[net.segV[s]]) / 2
                val heading = net.segBearing[s] + if (net.segFwd[s]) 0.0 else Math.PI
                val c = net.candidates(lat, lon, heading, 5.0, 10.0)
                if (c.edges.any { net.edgeSeg[it] == s }) found++
            }
            // a filter seeded on a random road, driven straight for 60 s at 10 m/s, must keep a road under it
            val s0 = net.segU.indices.first { net.segLen[it] > 30.0 && net.segFwd[it] }
            val lat0 = (net.nodeLat[net.segU[s0]] + net.nodeLat[net.segV[s0]]) / 2
            val lon0 = (net.nodeLon[net.segU[s0]] + net.nodeLon[net.segV[s0]]) / 2
            val pf = ParticleFilter(net, PfParams(), lat0, lon0, net.segBearing[s0], 10.0, Random(1))
            val dr = DeadReckoning(net.segBearing[s0], 10.0)
            repeat(600) {
                val psi = dr.heading
                dr.step(0.0, false, 0.1)
                pf.step(psi, dr.heading, false, 0.1, dr.east, dr.north)
            }
            val est = pf.estimate(dr.east, dr.north, dr.dist)
            println("%-16s %,7.0f km · loaded %.2f s · nearest-road search found %d/%d · filter seeded %s, after 600 m: %.0f m moved, %d re-seeds"
                .format(net.name, net.kmOfRoad, loadS, found, tries, pf.seeded, Math.hypot(est[0], est[1]), pf.reseeds))
            assertEquals(tries, found)
        }
    }
}
