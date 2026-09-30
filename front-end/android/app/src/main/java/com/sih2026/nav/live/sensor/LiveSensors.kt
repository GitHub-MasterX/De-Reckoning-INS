package com.sih2026.nav.live.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import com.sih2026.nav.live.engine.ImuStream
import com.sih2026.nav.live.record.DriveRecorder

/**
 * The phone's accelerometer, gyroscope and GPS, on one background thread.
 *
 * Every sensor event goes to the recorder at the full rate the phone allows (248 Hz on the Galaxy M17). The engines get
 * 10 Hz rows from ImuStream: the samples at each 100 ms tick (what round 1's classifier and round 2 were built on) and
 * the full-rate means over the interval (what the 248 Hz engine reads). GPS comes from the GPS provider only: network
 * fixes carry no speed or course.
 */
class LiveSensors(
    context: Context,
    private val recorder: DriveRecorder?,
    private val onRow: (ImuStream.Row) -> Unit,
    private val onFix: (Location) -> Unit
) : SensorEventListener, LocationListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    private val thread = HandlerThread("live-sensors").apply { start() }
    private val handler = Handler(thread.looper)

    private val stream = ImuStream { onRow(it) }

    @Volatile var accHz = 0f; private set
    @Volatile var gyrHz = 0f; private set
    @Volatile var gpsAllowed = false; private set
    private var accCount = 0
    private var gyrCount = 0
    private var rateStartNs = 0L

    /** Name, vendor and fastest rate of each sensor used, for the recording's header. */
    val description: List<String> = TYPES.mapNotNull { type ->
        sensorManager.getDefaultSensor(type)?.let { s ->
            "sensor ${s.name} | ${s.vendor} | type ${s.type} | max rate %.1f Hz".format(if (s.minDelay > 0) 1e6 / s.minDelay else 0.0)
        }
    }

    val hasGyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE) != null

    fun start() {
        for (type in TYPES) {
            sensorManager.getDefaultSensor(type)?.let {
                sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_FASTEST, handler)
            }
        }
        gpsAllowed = try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0f, this, thread.looper)
            true
        } catch (e: SecurityException) {
            false
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        try { locationManager.removeUpdates(this) } catch (e: Exception) { }
        thread.quitSafely()
    }

    override fun onSensorChanged(event: SensorEvent) {
        val t = event.timestamp
        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                accCount++
                recorder?.sensor("A", t, event.values, 3)
                stream.accelerometer(t, event.values[0].toDouble(), event.values[1].toDouble(), event.values[2].toDouble())
            }
            Sensor.TYPE_GYROSCOPE -> {
                gyrCount++
                recorder?.sensor("G", t, event.values, 3)
                stream.gyroscope(t, event.values[0].toDouble(), event.values[1].toDouble(), event.values[2].toDouble())
            }
            UNCALIBRATED_ACCELEROMETER -> recorder?.sensor("a", t, event.values, 6)
            Sensor.TYPE_GYROSCOPE_UNCALIBRATED -> recorder?.sensor("g", t, event.values, 6)
            Sensor.TYPE_MAGNETIC_FIELD -> recorder?.sensor("M", t, event.values, 3)
        }
        if (rateStartNs == 0L) rateStartNs = t
        if (t - rateStartNs >= 1_000_000_000L) {
            val s = (t - rateStartNs) / 1e9f
            accHz = accCount / s; gyrHz = gyrCount / s
            accCount = 0; gyrCount = 0; rateStartNs = t
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    override fun onLocationChanged(location: Location) {
        recorder?.fix(location)
        onFix(location)
    }

    @Deprecated("Deprecated in Java")
    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    override fun onProviderEnabled(provider: String) {}
    override fun onProviderDisabled(provider: String) {}

    companion object {
        const val ROW_NS = 100_000_000L
        private val UNCALIBRATED_ACCELEROMETER = if (Build.VERSION.SDK_INT >= 26) Sensor.TYPE_ACCELEROMETER_UNCALIBRATED else -1
        private val TYPES = listOfNotNull(
            Sensor.TYPE_ACCELEROMETER, Sensor.TYPE_GYROSCOPE, Sensor.TYPE_GYROSCOPE_UNCALIBRATED, Sensor.TYPE_MAGNETIC_FIELD,
            UNCALIBRATED_ACCELEROMETER.takeIf { it > 0 }
        )
    }
}
