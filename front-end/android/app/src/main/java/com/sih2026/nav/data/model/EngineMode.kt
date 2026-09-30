package com.sih2026.nav.data.model

/** Which engine drives the map: recorded IO-VNBD blackouts, or this phone's own sensors. */
enum class EngineMode(val label: String) {
    REPLAY("REPLAY DATASET CLIPS"),
    LIVE("LIVE PHONE SENSORS")
}
