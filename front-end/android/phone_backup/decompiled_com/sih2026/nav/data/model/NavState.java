package com.sih2026.nav.data.model;

import kotlin.Metadata;
import kotlin.jvm.internal.Intrinsics;

/* JADX INFO: compiled from: NavState.kt */
/* JADX INFO: loaded from: classes9.dex */
@Metadata(d1 = {"\u0000>\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u0006\n\u0002\b\u0002\n\u0002\u0010\u0007\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\t\n\u0002\b\u0015\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0000\b\u0087\b\u0018\u00002\u00020\u0001B=\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0003\u0012\u0006\u0010\u0005\u001a\u00020\u0006\u0012\u0006\u0010\u0007\u001a\u00020\u0006\u0012\u0006\u0010\b\u001a\u00020\t\u0012\u0006\u0010\n\u001a\u00020\u0006\u0012\u0006\u0010\u000b\u001a\u00020\f¢\u0006\u0002\u0010\rJ\t\u0010\u0019\u001a\u00020\u0003HÆ\u0003J\t\u0010\u001a\u001a\u00020\u0003HÆ\u0003J\t\u0010\u001b\u001a\u00020\u0006HÆ\u0003J\t\u0010\u001c\u001a\u00020\u0006HÆ\u0003J\t\u0010\u001d\u001a\u00020\tHÆ\u0003J\t\u0010\u001e\u001a\u00020\u0006HÆ\u0003J\t\u0010\u001f\u001a\u00020\fHÆ\u0003JO\u0010 \u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00032\b\b\u0002\u0010\u0005\u001a\u00020\u00062\b\b\u0002\u0010\u0007\u001a\u00020\u00062\b\b\u0002\u0010\b\u001a\u00020\t2\b\b\u0002\u0010\n\u001a\u00020\u00062\b\b\u0002\u0010\u000b\u001a\u00020\fHÆ\u0001J\u0013\u0010!\u001a\u00020\"2\b\u0010#\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u0010$\u001a\u00020%HÖ\u0001J\t\u0010&\u001a\u00020'HÖ\u0001R\u0011\u0010\u0005\u001a\u00020\u0006¢\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\u000fR\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0010\u0010\u0011R\u0011\u0010\u0004\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\u0011R\u0011\u0010\b\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014R\u0011\u0010\u0007\u001a\u00020\u0006¢\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\u000fR\u0011\u0010\u000b\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\u0016\u0010\u0017R\u0011\u0010\n\u001a\u00020\u0006¢\u0006\b\n\u0000\u001a\u0004\b\u0018\u0010\u000f¨\u0006("}, d2 = {"Lcom/sih2026/nav/data/model/NavState;", "", "lat", "", "lon", "headingDeg", "", "speedKmh", "mode", "Lcom/sih2026/nav/data/model/Mode;", "uncertaintyM", "timestampNs", "", "(DDFFLcom/sih2026/nav/data/model/Mode;FJ)V", "getHeadingDeg", "()F", "getLat", "()D", "getLon", "getMode", "()Lcom/sih2026/nav/data/model/Mode;", "getSpeedKmh", "getTimestampNs", "()J", "getUncertaintyM", "component1", "component2", "component3", "component4", "component5", "component6", "component7", "copy", "equals", "", "other", "hashCode", "", "toString", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class NavState {
    public static final int $stable = 0;
    private final float headingDeg;
    private final double lat;
    private final double lon;
    private final Mode mode;
    private final float speedKmh;
    private final long timestampNs;
    private final float uncertaintyM;

    public NavState(double d, double d2, float f, float f2, Mode mode, float f3, long j) {
        Intrinsics.checkNotNullParameter(mode, "mode");
        this.lat = d;
        this.lon = d2;
        this.headingDeg = f;
        this.speedKmh = f2;
        this.mode = mode;
        this.uncertaintyM = f3;
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
    public final float getHeadingDeg() {
        return this.headingDeg;
    }

    /* JADX INFO: renamed from: component4, reason: from getter */
    public final float getSpeedKmh() {
        return this.speedKmh;
    }

    /* JADX INFO: renamed from: component5, reason: from getter */
    public final Mode getMode() {
        return this.mode;
    }

    /* JADX INFO: renamed from: component6, reason: from getter */
    public final float getUncertaintyM() {
        return this.uncertaintyM;
    }

    /* JADX INFO: renamed from: component7, reason: from getter */
    public final long getTimestampNs() {
        return this.timestampNs;
    }

    public final NavState copy(double lat, double lon, float headingDeg, float speedKmh, Mode mode, float uncertaintyM, long timestampNs) {
        Intrinsics.checkNotNullParameter(mode, "mode");
        return new NavState(lat, lon, headingDeg, speedKmh, mode, uncertaintyM, timestampNs);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof NavState)) {
            return false;
        }
        NavState navState = (NavState) other;
        return Double.compare(this.lat, navState.lat) == 0 && Double.compare(this.lon, navState.lon) == 0 && Float.compare(this.headingDeg, navState.headingDeg) == 0 && Float.compare(this.speedKmh, navState.speedKmh) == 0 && this.mode == navState.mode && Float.compare(this.uncertaintyM, navState.uncertaintyM) == 0 && this.timestampNs == navState.timestampNs;
    }

    public final float getHeadingDeg() {
        return this.headingDeg;
    }

    public final double getLat() {
        return this.lat;
    }

    public final double getLon() {
        return this.lon;
    }

    public final Mode getMode() {
        return this.mode;
    }

    public final float getSpeedKmh() {
        return this.speedKmh;
    }

    public final long getTimestampNs() {
        return this.timestampNs;
    }

    public final float getUncertaintyM() {
        return this.uncertaintyM;
    }

    public int hashCode() {
        return (((((((((((Double.hashCode(this.lat) * 31) + Double.hashCode(this.lon)) * 31) + Float.hashCode(this.headingDeg)) * 31) + Float.hashCode(this.speedKmh)) * 31) + this.mode.hashCode()) * 31) + Float.hashCode(this.uncertaintyM)) * 31) + Long.hashCode(this.timestampNs);
    }

    public String toString() {
        return "NavState(lat=" + this.lat + ", lon=" + this.lon + ", headingDeg=" + this.headingDeg + ", speedKmh=" + this.speedKmh + ", mode=" + this.mode + ", uncertaintyM=" + this.uncertaintyM + ", timestampNs=" + this.timestampNs + ')';
    }
}
