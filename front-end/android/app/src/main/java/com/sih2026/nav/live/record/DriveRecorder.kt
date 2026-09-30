package com.sih2026.nav.live.record

import android.location.Location
import java.io.BufferedWriter
import java.io.File
import java.io.FileOutputStream
import java.io.FilterOutputStream
import java.io.OutputStream
import java.io.OutputStreamWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.zip.GZIPOutputStream

/**
 * Every drive, recorded raw — the new dataset. One gzip-compressed CSV per live session, written on its own thread.
 *
 * Lines start with a tag; times are nanoseconds on the sensor clock (SystemClock.elapsedRealtimeNanos):
 *   A  t, ax, ay, az                         accelerometer, m/s² with gravity, every event (up to 250 Hz)
 *   G  t, gx, gy, gz                         gyroscope, rad/s, as Android delivers it
 *   a  t, ax, ay, az, bias x, y, z           accelerometer, uncalibrated
 *   g  t, gx, gy, gz, drift x, y, z          gyroscope, uncalibrated
 *   M  t, mx, my, mz                         magnetometer, µT
 *   L  t, utc ms, lat, lon, alt, accuracy m, speed m/s, speed accuracy, bearing °, bearing accuracy, has speed, has bearing
 *   B  t, 1 | 0                              blackout switched on / off
 *   E  t, lat, lon, no-map lat, no-map lon, heading °, stationary, in blackout, on map   the engine, every 10 Hz row
 * Lines starting with # describe the phone, its sensors and the engine settings.
 * GNSS keeps being recorded during a blackout: the engine never sees it, it is the answer key.
 */
class DriveRecorder(dir: File, header: List<String>) {
    val file: File
    @Volatile var bytesWritten = 0L; private set
    @Volatile var dropped = 0L; private set

    private val queue = LinkedBlockingQueue<String>(400_000)
    @Volatile private var open = true
    private val thread: Thread

    init {
        dir.mkdirs()
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        file = File(dir, "drive_$stamp.csv.gz")
        header.forEach { queue.offer("# $it") }
        thread = Thread({ loop() }, "drive-recorder").apply { start() }
    }

    fun sensor(tag: String, t: Long, v: FloatArray, n: Int) {
        val sb = StringBuilder(64).append(tag).append(',').append(t)
        for (k in 0 until n) sb.append(',').append(v[k])
        offer(sb.toString())
    }

    fun fix(loc: Location) {
        offer(buildString {
            append("L,").append(loc.elapsedRealtimeNanos).append(',').append(loc.time).append(',')
            append(loc.latitude).append(',').append(loc.longitude).append(',').append(loc.altitude).append(',')
            append(loc.accuracy).append(',').append(loc.speed).append(',')
            append(if (android.os.Build.VERSION.SDK_INT >= 26 && loc.hasSpeedAccuracy()) loc.speedAccuracyMetersPerSecond else Float.NaN).append(',')
            append(loc.bearing).append(',')
            append(if (android.os.Build.VERSION.SDK_INT >= 26 && loc.hasBearingAccuracy()) loc.bearingAccuracyDegrees else Float.NaN).append(',')
            append(if (loc.hasSpeed()) 1 else 0).append(',').append(if (loc.hasBearing()) 1 else 0)
        })
    }

    fun line(s: String) = offer(s)

    private fun offer(s: String) {
        if (!open || !queue.offer(s)) dropped++
    }

    fun close() {
        open = false
        thread.join(5000)
    }

    private fun loop() {
        val counting = object : FilterOutputStream(FileOutputStream(file)) {
            override fun write(b: Int) { out.write(b); bytesWritten++ }
            override fun write(b: ByteArray, off: Int, len: Int) { out.write(b, off, len); bytesWritten += len }
        }
        val gz: OutputStream = GZIPOutputStream(counting, 1 shl 16, true)
        BufferedWriter(OutputStreamWriter(gz, Charsets.UTF_8), 1 shl 16).use { w ->
            var lastFlush = System.nanoTime()
            while (open || queue.isNotEmpty()) {
                val s = queue.poll(200, TimeUnit.MILLISECONDS)
                if (s != null) { w.write(s); w.write("\n") }
                if (System.nanoTime() - lastFlush > 2_000_000_000L) {   // a killed app still leaves a readable file
                    w.flush()
                    lastFlush = System.nanoTime()
                }
            }
        }
    }
}
