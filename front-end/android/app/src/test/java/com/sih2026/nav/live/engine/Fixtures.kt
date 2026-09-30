package com.sih2026.nav.live.engine

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Readers for the reference files round2/phone/export_*.py write from the Python engine. */
object Fixtures {
    val fixtureDir = File(System.getProperty("fixtureDir") ?: "../../data/osm/phone")
    val assetDir = File(System.getProperty("assetDir") ?: "src/main/assets")

    fun open(file: File, magic: String): ByteBuffer {
        val b = ByteBuffer.wrap(file.readBytes()).order(ByteOrder.LITTLE_ENDIAN)
        val m = ByteArray(4).also { b.get(it) }
        check(String(m) == magic) { "${file.name}: expected $magic" }
        return b
    }

    fun ByteBuffer.string() = String(ByteArray(int).also { get(it) })
    fun ByteBuffer.doubles(n: Int) = DoubleArray(n) { double }

    class Check(val metres: Int, val row: Int, val truth: DoubleArray, val seedA: DoubleArray, val seedB: DoubleArray)

    class Blackout(
        val id: String, val driver: String,
        val lat0: Double, val lon0: Double, val course0: Double, val speed0: Double,
        val calibration: GyroCalibration,
        val t: DoubleArray, val acc: DoubleArray, val gyr: DoubleArray, val stationary: BooleanArray,
        val drEast: DoubleArray, val drNorth: DoubleArray, val drDist: DoubleArray,
        val checks: List<Check>
    ) {
        val rows get() = t.size
        fun turnRate(r: Int) = calibration.turnRate(gyr[3 * r], gyr[3 * r + 1], gyr[3 * r + 2])
    }

    fun blackouts(): List<Blackout> {
        val b = open(File(fixtureDir, "engine_fixture.bin"), "EFX1")
        return List(b.int) {
            val id = b.string(); val driver = b.string()
            val start = b.doubles(4)
            val axis = b.doubles(3); val scale = b.double; val bias = b.double
            val rows = b.int
            val t = b.doubles(rows); val acc = b.doubles(3 * rows); val gyr = b.doubles(3 * rows)
            val stat = BooleanArray(rows) { b.get().toInt() != 0 }
            val e = b.doubles(rows); val nn = b.doubles(rows); val d = b.doubles(rows)
            val checks = List(b.int) { Check(b.int, b.int, b.doubles(3), b.doubles(3), b.doubles(3)) }
            Blackout(id, driver, start[0], start[1], start[2], start[3], GyroCalibration(axis, scale, bias, "python"),
                t, acc, gyr, stat, e, nn, d, checks)
        }
    }
}
