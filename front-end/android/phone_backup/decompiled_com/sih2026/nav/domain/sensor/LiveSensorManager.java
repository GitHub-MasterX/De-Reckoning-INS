package com.sih2026.nav.domain.sensor;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import androidx.core.app.NotificationCompat;
import java.util.ArrayList;
import java.util.List;
import kotlin.Deprecated;
import kotlin.Metadata;
import kotlin.Unit;
import kotlin.collections.CollectionsKt;
import kotlin.jvm.internal.Intrinsics;
import kotlinx.coroutines.flow.FlowKt;
import kotlinx.coroutines.flow.MutableStateFlow;
import kotlinx.coroutines.flow.StateFlow;
import kotlinx.coroutines.flow.StateFlowKt;
import org.osmdroid.tileprovider.modules.DatabaseFileArchive;

/* JADX INFO: compiled from: LiveSensorManager.kt */
/* JADX INFO: loaded from: classes3.dex */
@Metadata(d1 = {"\u0000\u008c\u0001\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\b\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u000b\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u0014\n\u0002\b\u0006\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010!\n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0003\b\u0007\u0018\u00002\u00020\u00012\u00020\u0002B\r\u0012\u0006\u0010\u0003\u001a\u00020\u0004¢\u0006\u0002\u0010\u0005J\u001a\u0010%\u001a\u00020&2\b\u0010'\u001a\u0004\u0018\u00010(2\u0006\u0010)\u001a\u00020\u0007H\u0016J\u0010\u0010*\u001a\u00020&2\u0006\u0010+\u001a\u00020,H\u0016J\u0010\u0010-\u001a\u00020&2\u0006\u0010.\u001a\u00020/H\u0016J\u0010\u00100\u001a\u00020&2\u0006\u0010.\u001a\u00020/H\u0016J\u0012\u00101\u001a\u00020&2\b\u00102\u001a\u0004\u0018\u000103H\u0016J$\u00104\u001a\u00020&2\b\u0010.\u001a\u0004\u0018\u00010/2\u0006\u00105\u001a\u00020\u00072\b\u00106\u001a\u0004\u0018\u000107H\u0017J\u0006\u00108\u001a\u00020&J\u0006\u00109\u001a\u00020&R\u000e\u0010\u0006\u001a\u00020\u0007X\u0082D¢\u0006\u0002\n\u0000R\u0014\u0010\b\u001a\b\u0012\u0004\u0012\u00020\n0\tX\u0082\u0004¢\u0006\u0002\n\u0000R\u0016\u0010\u000b\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\f0\tX\u0082\u0004¢\u0006\u0002\n\u0000R\u0016\u0010\r\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\u000e0\tX\u0082\u0004¢\u0006\u0002\n\u0000R\u001a\u0010\u000f\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u000e0\u00100\tX\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u0011\u001a\u00020\nX\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0012\u001a\u00020\nX\u0082\u000e¢\u0006\u0002\n\u0000R\u0017\u0010\u0013\u001a\b\u0012\u0004\u0012\u00020\n0\u0014¢\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0015R\u000e\u0010\u0016\u001a\u00020\u0017X\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0018\u001a\u00020\u0017X\u0082\u000e¢\u0006\u0002\n\u0000R\u0019\u0010\u0019\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\f0\u0014¢\u0006\b\n\u0000\u001a\u0004\b\u001a\u0010\u0015R\u0019\u0010\u001b\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\u000e0\u0014¢\u0006\b\n\u0000\u001a\u0004\b\u001c\u0010\u0015R\u0010\u0010\u001d\u001a\u0004\u0018\u00010\u001eX\u0082\u0004¢\u0006\u0002\n\u0000R\u0010\u0010\u001f\u001a\u0004\u0018\u00010 X\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010!\u001a\b\u0012\u0004\u0012\u00020\u000e0\"X\u0082\u0004¢\u0006\u0002\n\u0000R\u001d\u0010#\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u000e0\u00100\u0014¢\u0006\b\n\u0000\u001a\u0004\b$\u0010\u0015¨\u0006:"}, d2 = {"Lcom/sih2026/nav/domain/sensor/LiveSensorManager;", "Landroid/hardware/SensorEventListener;", "Landroid/location/LocationListener;", "context", "Landroid/content/Context;", "(Landroid/content/Context;)V", "WINDOW_SIZE", "", "_isSensorsActive", "Lkotlinx/coroutines/flow/MutableStateFlow;", "", "_latestGnss", "Lcom/sih2026/nav/domain/sensor/GnssFix;", "_latestSample", "Lcom/sih2026/nav/domain/sensor/ImuSample;", "_windowStream", "", "hasAcc", "hasGyr", "isSensorsActive", "Lkotlinx/coroutines/flow/StateFlow;", "()Lkotlinx/coroutines/flow/StateFlow;", "lastAcc", "", "lastGyr", "latestGnss", "getLatestGnss", "latestSample", "getLatestSample", "locationManager", "Landroid/location/LocationManager;", "sensorManager", "Landroid/hardware/SensorManager;", "windowBuffer", "", "windowStream", "getWindowStream", "onAccuracyChanged", "", "sensor", "Landroid/hardware/Sensor;", "accuracy", "onLocationChanged", "location", "Landroid/location/Location;", "onProviderDisabled", DatabaseFileArchive.COLUMN_PROVIDER, "", "onProviderEnabled", "onSensorChanged", NotificationCompat.CATEGORY_EVENT, "Landroid/hardware/SensorEvent;", "onStatusChanged", NotificationCompat.CATEGORY_STATUS, "extras", "Landroid/os/Bundle;", "start", "stop", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class LiveSensorManager implements SensorEventListener, LocationListener {
    public static final int $stable = 8;
    private final int WINDOW_SIZE;
    private final MutableStateFlow<Boolean> _isSensorsActive;
    private final MutableStateFlow<GnssFix> _latestGnss;
    private final MutableStateFlow<ImuSample> _latestSample;
    private final MutableStateFlow<List<ImuSample>> _windowStream;
    private boolean hasAcc;
    private boolean hasGyr;
    private final StateFlow<Boolean> isSensorsActive;
    private float[] lastAcc;
    private float[] lastGyr;
    private final StateFlow<GnssFix> latestGnss;
    private final StateFlow<ImuSample> latestSample;
    private final LocationManager locationManager;
    private final SensorManager sensorManager;
    private final List<ImuSample> windowBuffer;
    private final StateFlow<List<ImuSample>> windowStream;

    public LiveSensorManager(Context context) {
        Intrinsics.checkNotNullParameter(context, "context");
        Object systemService = context.getSystemService("sensor");
        this.sensorManager = systemService instanceof SensorManager ? (SensorManager) systemService : null;
        Object systemService2 = context.getSystemService("location");
        this.locationManager = systemService2 instanceof LocationManager ? (LocationManager) systemService2 : null;
        this._latestSample = StateFlowKt.MutableStateFlow(null);
        this.latestSample = FlowKt.asStateFlow(this._latestSample);
        this._latestGnss = StateFlowKt.MutableStateFlow(null);
        this.latestGnss = FlowKt.asStateFlow(this._latestGnss);
        this._isSensorsActive = StateFlowKt.MutableStateFlow(false);
        this.isSensorsActive = FlowKt.asStateFlow(this._isSensorsActive);
        this.lastAcc = new float[3];
        this.lastGyr = new float[3];
        this.windowBuffer = new ArrayList();
        this.WINDOW_SIZE = 20;
        this._windowStream = StateFlowKt.MutableStateFlow(CollectionsKt.emptyList());
        this.windowStream = FlowKt.asStateFlow(this._windowStream);
    }

    public final StateFlow<GnssFix> getLatestGnss() {
        return this.latestGnss;
    }

    public final StateFlow<ImuSample> getLatestSample() {
        return this.latestSample;
    }

    public final StateFlow<List<ImuSample>> getWindowStream() {
        return this.windowStream;
    }

    public final StateFlow<Boolean> isSensorsActive() {
        return this.isSensorsActive;
    }

    @Override // android.hardware.SensorEventListener
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    @Override // android.location.LocationListener
    public void onLocationChanged(Location location) {
        Intrinsics.checkNotNullParameter(location, "location");
        this._latestGnss.setValue(new GnssFix(location.getLatitude(), location.getLongitude(), 3.6f * location.getSpeed(), location.getBearing(), location.getAccuracy(), System.nanoTime()));
    }

    @Override // android.location.LocationListener
    public void onProviderDisabled(String provider) {
        Intrinsics.checkNotNullParameter(provider, "provider");
    }

    @Override // android.location.LocationListener
    public void onProviderEnabled(String provider) {
        Intrinsics.checkNotNullParameter(provider, "provider");
    }

    @Override // android.hardware.SensorEventListener
    public void onSensorChanged(SensorEvent event) {
        if (event == null) {
            return;
        }
        long jNanoTime = System.nanoTime();
        switch (event.sensor.getType()) {
            case 1:
                System.arraycopy(event.values, 0, this.lastAcc, 0, 3);
                this.hasAcc = true;
                break;
            case 4:
                System.arraycopy(event.values, 0, this.lastGyr, 0, 3);
                this.hasGyr = true;
                break;
        }
        if (this.hasAcc && this.hasGyr) {
            ImuSample imuSample = new ImuSample(jNanoTime, this.lastAcc[0], this.lastAcc[1], this.lastAcc[2], this.lastGyr[0], this.lastGyr[1], this.lastGyr[2]);
            this._latestSample.setValue(imuSample);
            synchronized (this.windowBuffer) {
                this.windowBuffer.add(imuSample);
                if (this.windowBuffer.size() > this.WINDOW_SIZE) {
                    this.windowBuffer.remove(0);
                }
                if (this.windowBuffer.size() == this.WINDOW_SIZE) {
                    this._windowStream.setValue(new ArrayList(this.windowBuffer));
                }
                Unit unit = Unit.INSTANCE;
            }
        }
    }

    @Override // android.location.LocationListener
    @Deprecated(message = "Deprecated in API 29")
    public void onStatusChanged(String provider, int status, Bundle extras) {
    }

    public final void start() {
        if (this._isSensorsActive.getValue().booleanValue()) {
            return;
        }
        SensorManager sensorManager = this.sensorManager;
        if (sensorManager != null) {
            Sensor defaultSensor = sensorManager.getDefaultSensor(1);
            Sensor defaultSensor2 = sensorManager.getDefaultSensor(4);
            if (defaultSensor != null) {
                sensorManager.registerListener(this, defaultSensor, 1);
            }
            if (defaultSensor2 != null) {
                sensorManager.registerListener(this, defaultSensor2, 1);
            }
        }
        try {
            LocationManager locationManager = this.locationManager;
            if (locationManager != null) {
                locationManager.requestLocationUpdates("gps", 1000L, 1.0f, this);
            }
            LocationManager locationManager2 = this.locationManager;
            if (locationManager2 != null) {
                locationManager2.requestLocationUpdates("network", 1000L, 1.0f, this);
            }
        } catch (SecurityException e) {
        } catch (Exception e2) {
        }
        this._isSensorsActive.setValue(true);
    }

    public final void stop() {
        if (this._isSensorsActive.getValue().booleanValue()) {
            SensorManager sensorManager = this.sensorManager;
            if (sensorManager != null) {
                sensorManager.unregisterListener(this);
            }
            try {
                LocationManager locationManager = this.locationManager;
                if (locationManager != null) {
                    locationManager.removeUpdates(this);
                }
            } catch (Exception e) {
            }
            this._isSensorsActive.setValue(false);
        }
    }
}
