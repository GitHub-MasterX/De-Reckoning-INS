package com.sih2026.nav

import android.app.Application
import com.sih2026.nav.domain.engine.LiveNavEngine
import org.osmdroid.config.Configuration

class NavApp : Application() {
    /** One live engine for the whole app: the recording service runs it, the screen shows it. */
    val liveEngine by lazy { LiveNavEngine(this) }

    override fun onCreate() {
        super.onCreate()
        // Initialize osmdroid tile cache configuration
        Configuration.getInstance().load(this, getSharedPreferences("osmdroid", MODE_PRIVATE))
    }
}
