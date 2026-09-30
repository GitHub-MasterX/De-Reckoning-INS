package com.sih2026.nav.domain.sensor;

import kotlin.Metadata;

/* JADX INFO: compiled from: LiveSensorManager.kt */
/* JADX INFO: loaded from: classes3.dex */
@Metadata(d1 = {"\u00006\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u0006\n\u0002\b\u0002\n\u0002\u0010\u0007\n\u0002\b\u0003\n\u0002\u0010\t\n\u0002\b\u0012\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0000\b\u0087\b\u0018\u00002\u00020\u0001B5\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0003\u0012\u0006\u0010\u0005\u001a\u00020\u0006\u0012\u0006\u0010\u0007\u001a\u00020\u0006\u0012\u0006\u0010\b\u001a\u00020\u0006\u0012\u0006\u0010\t\u001a\u00020\n¢\u0006\u0002\u0010\u000bJ\t\u0010\u0015\u001a\u00020\u0003HÆ\u0003J\t\u0010\u0016\u001a\u00020\u0003HÆ\u0003J\t\u0010\u0017\u001a\u00020\u0006HÆ\u0003J\t\u0010\u0018\u001a\u00020\u0006HÆ\u0003J\t\u0010\u0019\u001a\u00020\u0006HÆ\u0003J\t\u0010\u001a\u001a\u00020\nHÆ\u0003JE\u0010\u001b\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00032\b\b\u0002\u0010\u0005\u001a\u00020\u00062\b\b\u0002\u0010\u0007\u001a\u00020\u00062\b\b\u0002\u0010\b\u001a\u00020\u00062\b\b\u0002\u0010\t\u001a\u00020\nHÆ\u0001J\u0013\u0010\u001c\u001a\u00020\u001d2\b\u0010\u001e\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u0010\u001f\u001a\u00020 HÖ\u0001J\t\u0010!\u001a\u00020\"HÖ\u0001R\u0011\u0010\b\u001a\u00020\u0006¢\u0006\b\n\u0000\u001a\u0004\b\f\u0010\rR\u0011\u0010\u0007\u001a\u00020\u0006¢\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\rR\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u000f\u0010\u0010R\u0011\u0010\u0004\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\u0010R\u0011\u0010\u0005\u001a\u00020\u0006¢\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\rR\u0011\u0010\t\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014¨\u0006#"}, d2 = {"Lcom/sih2026/nav/domain/sensor/GnssFix;", "", "lat", "", "lon", "speedKmh", "", "bearingDeg", "accuracyM", "timestampNs", "", "(DDFFFJ)V", "getAccuracyM", "()F", "getBearingDeg", "getLat", "()D", "getLon", "getSpeedKmh", "getTimestampNs", "()J", "component1", "component2", "component3", "component4", "component5", "component6", "copy", "equals", "", "other", "hashCode", "", "toString", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class GnssFix {
    public static final int $stable = 0;
    private final float accuracyM;
    private final float bearingDeg;
    private final double lat;
    private final double lon;
    private final float speedKmh;
    private final long timestampNs;

    public GnssFix(double d, double d2, float f, float f2, float f3, long j) {
        this.lat = d;
        this.lon = d2;
        this.speedKmh = f;
        this.bearingDeg = f2;
        this.accuracyM = f3;
        this.timestampNs = j;
    }

    /* JADX INFO: renamed from: component1, reason: from getter */
    public final double getLat() {
        return this.lat;
    }

    /* JADX INFO: renamed from: component2, reason: from getter */
    public final double getLon() {
        return this.lon;
    }

    /* JADX INFO: renamed from: component3, reason: from getter */
    public final float getSpeedKmh() {
        return this.speedKmh;
    }

    /* JADX INFO: renamed from: component4, reason: from getter */
    public final float getBearingDeg() {
        return this.bearingDeg;
    }

    /* JADX INFO: renamed from: component5, reason: from getter */
    public final float getAccuracyM() {
        return this.accuracyM;
    }

    /* JADX INFO: renamed from: component6, reason: from getter */
    public final long getTimestampNs() {
        return this.timestampNs;
    }

    public final GnssFix copy(double lat, double lon, float speedKmh, float bearingDeg, float accuracyM, long timestampNs) {
        return new GnssFix(lat, lon, speedKmh, bearingDeg, accuracyM, timestampNs);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof GnssFix)) {
            return false;
        }
        GnssFix gnssFix = (GnssFix) other;
        return Double.compare(this.lat, gnssFix.lat) == 0 && Double.compare(this.lon, gnssFix.lon) == 0 && Float.compare(this.speedKmh, gnssFix.speedKmh) == 0 && Float.compare(this.bearingDeg, gnssFix.bearingDeg) == 0 && Float.compare(this.accuracyM, gnssFix.accuracyM) == 0 && this.timestampNs == gnssFix.timestampNs;
    }

    public final float getAccuracyM() {
        return this.accuracyM;
    }

    public final float getBearingDeg() {
        return this.bearingDeg;
    }

    public final double getLat() {
        return this.lat;
    }

    public final double getLon() {
        return this.lon;
    }

    public final float getSpeedKmh() {
        return this.speedKmh;
    }

    public final long getTimestampNs() {
        return this.timestampNs;
    }

    public int hashCode() {
        return (((((((((Double.hashCode(this.lat) * 31) + Double.hashCode(this.lon)) * 31) + Float.hashCode(this.speedKmh)) * 31) + Float.hashCode(this.bearingDeg)) * 31) + Float.hashCode(this.accuracyM)) * 31) + Long.hashCode(this.timestampNs);
    }

    public String toString() {
        return "GnssFix(lat=" + this.lat + ", lon=" + this.lon + ", speedKmh=" + this.speedKmh + ", bearingDeg=" + this.bearingDeg + ", accuracyM=" + this.accuracyM + ", timestampNs=" + this.timestampNs + ')';
    }
}
