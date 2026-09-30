package com.sih2026.nav.live.engine

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Geodesy, ported from round2/core/geo.py and round2/core/roadnet.py so the phone computes what Python computes.
 *
 *   enu / invEnu   east and north metres around a reference point, from WGS84 radii of curvature
 *   planeX / planeY  the road network's nearest-road plane (roadnet.xy): radii fixed at 52.5° N, as in Python
 */
object Geo {
    private const val A_WGS84 = 6378137.0
    private const val E2_WGS84 = 6.69437999014e-3
    const val TWO_PI = 2 * PI

    private val PHI0 = Math.toRadians(52.5)
    private val M0 = A_WGS84 * (1 - E2_WGS84) / Math.pow(1 - E2_WGS84 * sin(PHI0) * sin(PHI0), 1.5)
    private val N0 = A_WGS84 / sqrt(1 - E2_WGS84 * sin(PHI0) * sin(PHI0))

    /** North-south radius, east-west radius and cos(latitude) at lat0 (degrees). */
    private fun radii(lat0: Double): DoubleArray {
        val phi = Math.toRadians(lat0)
        val s2 = sin(phi) * sin(phi)
        return doubleArrayOf(
            A_WGS84 * (1 - E2_WGS84) / Math.pow(1 - E2_WGS84 * s2, 1.5),
            A_WGS84 / sqrt(1 - E2_WGS84 * s2),
            cos(phi)
        )
    }

    /** East and north metres of (lat, lon) from (lat0, lon0). */
    fun enu(lat: Double, lon: Double, lat0: Double, lon0: Double, out: DoubleArray = DoubleArray(2)): DoubleArray {
        val r = radii(lat0)
        out[0] = Math.toRadians(lon - lon0) * r[1] * r[2]
        out[1] = Math.toRadians(lat - lat0) * r[0]
        return out
    }

    /** Latitude and longitude of a point east and north metres from (lat0, lon0). */
    fun invEnu(east: Double, north: Double, lat0: Double, lon0: Double): DoubleArray {
        val r = radii(lat0)
        return doubleArrayOf(lat0 + Math.toDegrees(north / r[0]), lon0 + Math.toDegrees(east / (r[1] * r[2])))
    }

    fun planeX(lat: Double, lon: Double): Double = Math.toRadians(lon) * N0 * cos(Math.toRadians(lat))
    fun planeY(lat: Double): Double = Math.toRadians(lat) * M0

    /** Angle to [-pi, pi), with Python's floor-modulo semantics. */
    fun wrap(a: Double): Double {
        var m = (a + PI) % TWO_PI                  // exact fmod, then numpy's move to the divisor's sign
        if (m != 0.0 && m < 0) m += TWO_PI
        return m - PI
    }

    /** Great-circle distance in metres, for on-screen drift only. */
    fun haversineM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val h = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
        return 2 * 6371008.8 * Math.atan2(sqrt(h), sqrt(1 - h))
    }
}
