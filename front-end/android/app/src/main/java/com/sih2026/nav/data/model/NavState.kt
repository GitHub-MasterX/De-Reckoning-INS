package com.sih2026.nav.data.model

data class NavState(
    val lat: Double,
    val lon: Double,
    val headingDeg: Float,     // 0 = north, clockwise
    val speedKmh: Float,
    val mode: Mode,
    val uncertaintyM: Float,   // radius of the confidence circle in meters
    val timestampNs: Long
)
