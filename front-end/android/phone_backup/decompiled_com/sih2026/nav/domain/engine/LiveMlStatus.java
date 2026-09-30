package com.sih2026.nav.domain.engine;

import kotlin.Metadata;
import kotlin.jvm.internal.DefaultConstructorMarker;

/* JADX INFO: compiled from: LiveMlNavEngine.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000.\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0004\n\u0002\u0010\u0006\n\u0002\b\u0002\n\u0002\u0010\u0007\n\u0002\b\u0018\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0000\b\u0087\b\u0018\u00002\u00020\u0001BU\u0012\b\b\u0002\u0010\u0002\u001a\u00020\u0003\u0012\b\b\u0002\u0010\u0004\u001a\u00020\u0003\u0012\b\b\u0002\u0010\u0005\u001a\u00020\u0003\u0012\b\b\u0002\u0010\u0006\u001a\u00020\u0003\u0012\b\b\u0002\u0010\u0007\u001a\u00020\b\u0012\b\b\u0002\u0010\t\u001a\u00020\b\u0012\b\b\u0002\u0010\n\u001a\u00020\u000b\u0012\b\b\u0002\u0010\f\u001a\u00020\u000b¢\u0006\u0002\u0010\rJ\t\u0010\u0018\u001a\u00020\u0003HÆ\u0003J\t\u0010\u0019\u001a\u00020\u0003HÆ\u0003J\t\u0010\u001a\u001a\u00020\u0003HÆ\u0003J\t\u0010\u001b\u001a\u00020\u0003HÆ\u0003J\t\u0010\u001c\u001a\u00020\bHÆ\u0003J\t\u0010\u001d\u001a\u00020\bHÆ\u0003J\t\u0010\u001e\u001a\u00020\u000bHÆ\u0003J\t\u0010\u001f\u001a\u00020\u000bHÆ\u0003JY\u0010 \u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00032\b\b\u0002\u0010\u0005\u001a\u00020\u00032\b\b\u0002\u0010\u0006\u001a\u00020\u00032\b\b\u0002\u0010\u0007\u001a\u00020\b2\b\b\u0002\u0010\t\u001a\u00020\b2\b\b\u0002\u0010\n\u001a\u00020\u000b2\b\b\u0002\u0010\f\u001a\u00020\u000bHÆ\u0001J\u0013\u0010!\u001a\u00020\u00032\b\u0010\"\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u0010#\u001a\u00020$HÖ\u0001J\t\u0010%\u001a\u00020&HÖ\u0001R\u0011\u0010\n\u001a\u00020\u000b¢\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\u000fR\u0011\u0010\f\u001a\u00020\u000b¢\u0006\b\n\u0000\u001a\u0004\b\u0010\u0010\u000fR\u0011\u0010\u0006\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\u0012R\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0002\u0010\u0012R\u0011\u0010\u0007\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014R\u0011\u0010\t\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\u0014R\u0011\u0010\u0005\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0016\u0010\u0012R\u0011\u0010\u0004\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0017\u0010\u0012¨\u0006'"}, d2 = {"Lcom/sih2026/nav/domain/engine/LiveMlStatus;", "", "isStationary", "", "serverConnected", "sensorActive", "inBlackout", "lastFixLat", "", "lastFixLon", "accumulatedDriftM", "", "elapsedBlackoutS", "(ZZZZDDFF)V", "getAccumulatedDriftM", "()F", "getElapsedBlackoutS", "getInBlackout", "()Z", "getLastFixLat", "()D", "getLastFixLon", "getSensorActive", "getServerConnected", "component1", "component2", "component3", "component4", "component5", "component6", "component7", "component8", "copy", "equals", "other", "hashCode", "", "toString", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class LiveMlStatus {
    public static final int $stable = 0;
    private final float accumulatedDriftM;
    private final float elapsedBlackoutS;
    private final boolean inBlackout;
    private final boolean isStationary;
    private final double lastFixLat;
    private final double lastFixLon;
    private final boolean sensorActive;
    private final boolean serverConnected;

    public LiveMlStatus() {
        this(false, false, false, false, 0.0d, 0.0d, 0.0f, 0.0f, 255, null);
    }

    public LiveMlStatus(boolean z, boolean z2, boolean z3, boolean z4, double d, double d2, float f, float f2) {
        this.isStationary = z;
        this.serverConnected = z2;
        this.sensorActive = z3;
        this.inBlackout = z4;
        this.lastFixLat = d;
        this.lastFixLon = d2;
        this.accumulatedDriftM = f;
        this.elapsedBlackoutS = f2;
    }

    public /* synthetic */ LiveMlStatus(boolean z, boolean z2, boolean z3, boolean z4, double d, double d2, float f, float f2, int i, DefaultConstructorMarker defaultConstructorMarker) {
        this((i & 1) != 0 ? false : z, (i & 2) != 0 ? false : z2, (i & 4) != 0 ? false : z3, (i & 8) == 0 ? z4 : false, (i & 16) != 0 ? 52.40384d : d, (i & 32) != 0 ? -1.50616d : d2, (i & 64) != 0 ? 0.0f : f, (i & 128) == 0 ? f2 : 0.0f);
    }

    /* JADX INFO: renamed from: component1, reason: from getter */
    public final boolean getIsStationary() {
        return this.isStationary;
    }

    /* JADX INFO: renamed from: component2, reason: from getter */
    public final boolean getServerConnected() {
        return this.serverConnected;
    }

    /* JADX INFO: renamed from: component3, reason: from getter */
    public final boolean getSensorActive() {
        return this.sensorActive;
    }

    /* JADX INFO: renamed from: component4, reason: from getter */
    public final boolean getInBlackout() {
        return this.inBlackout;
    }

    /* JADX INFO: renamed from: component5, reason: from getter */
    public final double getLastFixLat() {
        return this.lastFixLat;
    }

    /* JADX INFO: renamed from: component6, reason: from getter */
    public final double getLastFixLon() {
        return this.lastFixLon;
    }

    /* JADX INFO: renamed from: component7, reason: from getter */
    public final float getAccumulatedDriftM() {
        return this.accumulatedDriftM;
    }

    /* JADX INFO: renamed from: component8, reason: from getter */
    public final float getElapsedBlackoutS() {
        return this.elapsedBlackoutS;
    }

    public final LiveMlStatus copy(boolean isStationary, boolean serverConnected, boolean sensorActive, boolean inBlackout, double lastFixLat, double lastFixLon, float accumulatedDriftM, float elapsedBlackoutS) {
        return new LiveMlStatus(isStationary, serverConnected, sensorActive, inBlackout, lastFixLat, lastFixLon, accumulatedDriftM, elapsedBlackoutS);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof LiveMlStatus)) {
            return false;
        }
        LiveMlStatus liveMlStatus = (LiveMlStatus) other;
        return this.isStationary == liveMlStatus.isStationary && this.serverConnected == liveMlStatus.serverConnected && this.sensorActive == liveMlStatus.sensorActive && this.inBlackout == liveMlStatus.inBlackout && Double.compare(this.lastFixLat, liveMlStatus.lastFixLat) == 0 && Double.compare(this.lastFixLon, liveMlStatus.lastFixLon) == 0 && Float.compare(this.accumulatedDriftM, liveMlStatus.accumulatedDriftM) == 0 && Float.compare(this.elapsedBlackoutS, liveMlStatus.elapsedBlackoutS) == 0;
    }

    public final float getAccumulatedDriftM() {
        return this.accumulatedDriftM;
    }

    public final float getElapsedBlackoutS() {
        return this.elapsedBlackoutS;
    }

    public final boolean getInBlackout() {
        return this.inBlackout;
    }

    public final double getLastFixLat() {
        return this.lastFixLat;
    }

    public final double getLastFixLon() {
        return this.lastFixLon;
    }

    public final boolean getSensorActive() {
        return this.sensorActive;
    }

    public final boolean getServerConnected() {
        return this.serverConnected;
    }

    public int hashCode() {
        return (((((((((((((Boolean.hashCode(this.isStationary) * 31) + Boolean.hashCode(this.serverConnected)) * 31) + Boolean.hashCode(this.sensorActive)) * 31) + Boolean.hashCode(this.inBlackout)) * 31) + Double.hashCode(this.lastFixLat)) * 31) + Double.hashCode(this.lastFixLon)) * 31) + Float.hashCode(this.accumulatedDriftM)) * 31) + Float.hashCode(this.elapsedBlackoutS);
    }

    public final boolean isStationary() {
        return this.isStationary;
    }

    public String toString() {
        return "LiveMlStatus(isStationary=" + this.isStationary + ", serverConnected=" + this.serverConnected + ", sensorActive=" + this.sensorActive + ", inBlackout=" + this.inBlackout + ", lastFixLat=" + this.lastFixLat + ", lastFixLon=" + this.lastFixLon + ", accumulatedDriftM=" + this.accumulatedDriftM + ", elapsedBlackoutS=" + this.elapsedBlackoutS + ')';
    }
}
