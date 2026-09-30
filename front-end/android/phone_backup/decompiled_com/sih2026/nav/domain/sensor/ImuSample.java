package com.sih2026.nav.domain.sensor;

import kotlin.Metadata;

/* JADX INFO: compiled from: LiveSensorManager.kt */
/* JADX INFO: loaded from: classes3.dex */
@Metadata(d1 = {"\u0000,\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\t\n\u0000\n\u0002\u0010\u0007\n\u0002\b\u0018\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0000\b\u0087\b\u0018\u00002\u00020\u0001B=\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\u0006\u0010\u0006\u001a\u00020\u0005\u0012\u0006\u0010\u0007\u001a\u00020\u0005\u0012\u0006\u0010\b\u001a\u00020\u0005\u0012\u0006\u0010\t\u001a\u00020\u0005\u0012\u0006\u0010\n\u001a\u00020\u0005¢\u0006\u0002\u0010\u000bJ\t\u0010\u0015\u001a\u00020\u0003HÆ\u0003J\t\u0010\u0016\u001a\u00020\u0005HÆ\u0003J\t\u0010\u0017\u001a\u00020\u0005HÆ\u0003J\t\u0010\u0018\u001a\u00020\u0005HÆ\u0003J\t\u0010\u0019\u001a\u00020\u0005HÆ\u0003J\t\u0010\u001a\u001a\u00020\u0005HÆ\u0003J\t\u0010\u001b\u001a\u00020\u0005HÆ\u0003JO\u0010\u001c\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00052\b\b\u0002\u0010\u0006\u001a\u00020\u00052\b\b\u0002\u0010\u0007\u001a\u00020\u00052\b\b\u0002\u0010\b\u001a\u00020\u00052\b\b\u0002\u0010\t\u001a\u00020\u00052\b\b\u0002\u0010\n\u001a\u00020\u0005HÆ\u0001J\u0013\u0010\u001d\u001a\u00020\u001e2\b\u0010\u001f\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u0010 \u001a\u00020!HÖ\u0001J\t\u0010\"\u001a\u00020#HÖ\u0001R\u0011\u0010\u0004\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\f\u0010\rR\u0011\u0010\u0006\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\rR\u0011\u0010\u0007\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u000f\u0010\rR\u0011\u0010\b\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u0010\u0010\rR\u0011\u0010\t\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\rR\u0011\u0010\n\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\rR\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014¨\u0006$"}, d2 = {"Lcom/sih2026/nav/domain/sensor/ImuSample;", "", "timestampNs", "", "ax", "", "ay", "az", "gx", "gy", "gz", "(JFFFFFF)V", "getAx", "()F", "getAy", "getAz", "getGx", "getGy", "getGz", "getTimestampNs", "()J", "component1", "component2", "component3", "component4", "component5", "component6", "component7", "copy", "equals", "", "other", "hashCode", "", "toString", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class ImuSample {
    public static final int $stable = 0;
    private final float ax;
    private final float ay;
    private final float az;
    private final float gx;
    private final float gy;
    private final float gz;
    private final long timestampNs;

    public ImuSample(long j, float f, float f2, float f3, float f4, float f5, float f6) {
        this.timestampNs = j;
        this.ax = f;
        this.ay = f2;
        this.az = f3;
        this.gx = f4;
        this.gy = f5;
        this.gz = f6;
    }

    /* JADX INFO: renamed from: component1, reason: from getter */
    public final long getTimestampNs() {
        return this.timestampNs;
    }

    /* JADX INFO: renamed from: component2, reason: from getter */
    public final float getAx() {
        return this.ax;
    }

    /* JADX INFO: renamed from: component3, reason: from getter */
    public final float getAy() {
        return this.ay;
    }

    /* JADX INFO: renamed from: component4, reason: from getter */
    public final float getAz() {
        return this.az;
    }

    /* JADX INFO: renamed from: component5, reason: from getter */
    public final float getGx() {
        return this.gx;
    }

    /* JADX INFO: renamed from: component6, reason: from getter */
    public final float getGy() {
        return this.gy;
    }

    /* JADX INFO: renamed from: component7, reason: from getter */
    public final float getGz() {
        return this.gz;
    }

    public final ImuSample copy(long timestampNs, float ax, float ay, float az, float gx, float gy, float gz) {
        return new ImuSample(timestampNs, ax, ay, az, gx, gy, gz);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof ImuSample)) {
            return false;
        }
        ImuSample imuSample = (ImuSample) other;
        return this.timestampNs == imuSample.timestampNs && Float.compare(this.ax, imuSample.ax) == 0 && Float.compare(this.ay, imuSample.ay) == 0 && Float.compare(this.az, imuSample.az) == 0 && Float.compare(this.gx, imuSample.gx) == 0 && Float.compare(this.gy, imuSample.gy) == 0 && Float.compare(this.gz, imuSample.gz) == 0;
    }

    public final float getAx() {
        return this.ax;
    }

    public final float getAy() {
        return this.ay;
    }

    public final float getAz() {
        return this.az;
    }

    public final float getGx() {
        return this.gx;
    }

    public final float getGy() {
        return this.gy;
    }

    public final float getGz() {
        return this.gz;
    }

    public final long getTimestampNs() {
        return this.timestampNs;
    }

    public int hashCode() {
        return (((((((((((Long.hashCode(this.timestampNs) * 31) + Float.hashCode(this.ax)) * 31) + Float.hashCode(this.ay)) * 31) + Float.hashCode(this.az)) * 31) + Float.hashCode(this.gx)) * 31) + Float.hashCode(this.gy)) * 31) + Float.hashCode(this.gz);
    }

    public String toString() {
        return "ImuSample(timestampNs=" + this.timestampNs + ", ax=" + this.ax + ", ay=" + this.ay + ", az=" + this.az + ", gx=" + this.gx + ", gy=" + this.gy + ", gz=" + this.gz + ')';
    }
}
