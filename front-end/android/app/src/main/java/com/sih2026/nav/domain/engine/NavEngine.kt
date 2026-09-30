package com.sih2026.nav.domain.engine

import com.sih2026.nav.data.model.NavState
import kotlinx.coroutines.flow.StateFlow

interface NavEngine {
    val state: StateFlow<NavState>
    fun start()
    fun stop()
    fun setGnssBlackout(enabled: Boolean)   // demo toggle for SIH judges
}
