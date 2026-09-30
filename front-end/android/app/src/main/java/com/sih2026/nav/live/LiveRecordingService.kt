package com.sih2026.nav.live

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.sih2026.nav.MainActivity
import com.sih2026.nav.NavApp
import com.sih2026.nav.R
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

/**
 * Keeps live mode running — sensors, GPS, the engines and the recording — when the screen is off or the app is in the
 * background, so a drive is recorded end to end. A notification shows it is recording and has a Stop button.
 *
 * It holds a partial wake lock (the CPU stays awake so sensor events keep arriving) and runs as a location foreground
 * service, which Android allows to keep GPS and full-rate sensors while the app is not on screen.
 */
class LiveRecordingService : Service() {

    private var wakeLock: PowerManager.WakeLock? = null
    private val handler = Handler(Looper.getMainLooper())
    private val engine get() = (application as NavApp).liveEngine

    private val refresh = object : Runnable {
        override fun run() {
            if (!_running.value) return
            getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, notification())
            handler.postDelayed(this, 5000)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_RESTART -> {
                engine.stop()
                engine.start()
                return START_NOT_STICKY
            }
        }
        createChannel()
        ServiceCompat.startForeground(
            this, NOTIFICATION_ID, notification(),
            if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION else 0
        )
        if (wakeLock == null) {
            wakeLock = (getSystemService(Context.POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "sih:live-recording").apply { acquire() }
        }
        engine.start()
        _running.value = true
        handler.removeCallbacks(refresh)
        handler.postDelayed(refresh, 5000)
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        _running.value = false
        handler.removeCallbacks(refresh)
        engine.stop()
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < 26) return
        val channel = NotificationChannel(CHANNEL_ID, getString(R.string.nav_service_channel_name), NotificationManager.IMPORTANCE_LOW)
        channel.description = getString(R.string.nav_service_channel_desc)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun notification(): android.app.Notification {
        val s = engine.status.value
        val text = String.format(Locale.US, "IMU %.0f/%.0f Hz · %s · %.1f MB recorded%s",
            s.accHz, s.gyrHz,
            if (s.hasFix) String.format(Locale.US, "GPS ±%.0f m", s.fixAccuracyM) else "GPS acquiring",
            s.recordingBytes / 1e6, if (s.inBlackout) " · BLACKOUT" else "")
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop = PendingIntent.getService(this, 1, Intent(this, LiveRecordingService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentTitle("Recording drive: accelerometer, gyroscope, GPS")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .addAction(0, "Stop", stop)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "sih_live_recording"
        private const val NOTIFICATION_ID = 26168
        private const val ACTION_STOP = "com.sih2026.nav.live.STOP"
        private const val ACTION_RESTART = "com.sih2026.nav.live.RESTART"

        private val _running = MutableStateFlow(false)
        val running: StateFlow<Boolean> = _running.asStateFlow()

        fun start(context: Context) =
            ContextCompat.startForegroundService(context, Intent(context, LiveRecordingService::class.java))

        fun restart(context: Context) =
            context.startService(Intent(context, LiveRecordingService::class.java).setAction(ACTION_RESTART))

        fun stop(context: Context) = context.stopService(Intent(context, LiveRecordingService::class.java))
    }
}
