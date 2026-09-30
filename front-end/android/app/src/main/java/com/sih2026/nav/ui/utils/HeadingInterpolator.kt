package com.sih2026.nav.ui.utils

import com.sih2026.nav.data.model.NavState

class HeadingInterpolator {

    private var previousState: NavState? = null
    private var currentState: NavState? = null

    fun updateState(newState: NavState) {
        if (currentState == null) {
            previousState = newState
            currentState = newState
        } else {
            previousState = currentState
            currentState = newState
        }
    }

    /**
     * Interpolates position and heading between previousState and currentState
     * based on current nanosecond timestamp.
     */
    fun interpolate(nowNs: Long = System.nanoTime()): NavState {
        val prev = previousState ?: return NavState(52.40384, -1.50616, 0f, 0f, com.sih2026.nav.data.model.Mode.ACQUIRING, 10f, nowNs)
        val curr = currentState ?: return prev

        if (prev.timestampNs >= curr.timestampNs) {
            return curr
        }

        val totalDurationNs = (curr.timestampNs - prev.timestampNs).toFloat()
        val elapsedNs = (nowNs - prev.timestampNs).toFloat()
        val rawFraction = elapsedNs / totalDurationNs
        val fraction = rawFraction.coerceIn(0f, 1f)

        val interpLat = prev.lat + (curr.lat - prev.lat) * fraction
        val interpLon = prev.lon + (curr.lon - prev.lon) * fraction
        val interpHeading = lerpAngleShortestPath(prev.headingDeg, curr.headingDeg, fraction)
        val interpSpeed = prev.speedKmh + (curr.speedKmh - prev.speedKmh) * fraction
        val interpUncertainty = prev.uncertaintyM + (curr.uncertaintyM - prev.uncertaintyM) * fraction

        return curr.copy(
            lat = interpLat,
            lon = interpLon,
            headingDeg = interpHeading,
            speedKmh = interpSpeed,
            uncertaintyM = interpUncertainty,
            timestampNs = nowNs
        )
    }

    companion object {
        /**
         * Rotates the shortest way round between two heading angles in degrees (0 to 360).
         */
        fun lerpAngleShortestPath(startDeg: Float, endDeg: Float, fraction: Float): Float {
            var diff = (endDeg - startDeg) % 360f
            if (diff > 180f) {
                diff -= 360f
            } else if (diff < -180f) {
                diff += 360f
            }
            val result = startDeg + diff * fraction
            return (result + 360f) % 360f
        }
    }
}
