package com.sih2026.nav.data.model;

import kotlin.Metadata;
import kotlin.jvm.internal.Intrinsics;

/* JADX INFO: compiled from: ReplayClip.kt */
/* JADX INFO: loaded from: classes9.dex */
@Metadata(d1 = {"\u0000*\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0004\n\u0002\u0010\b\n\u0002\b\u0003\n\u0002\u0010\u0006\n\u0002\b*\n\u0002\u0010\u000b\n\u0002\b\u0004\b\u0087\b\u0018\u00002\u00020\u0001Bu\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0003\u0012\u0006\u0010\u0005\u001a\u00020\u0003\u0012\u0006\u0010\u0006\u001a\u00020\u0003\u0012\u0006\u0010\u0007\u001a\u00020\b\u0012\u0006\u0010\t\u001a\u00020\u0003\u0012\u0006\u0010\n\u001a\u00020\b\u0012\u0006\u0010\u000b\u001a\u00020\f\u0012\u0006\u0010\r\u001a\u00020\f\u0012\u0006\u0010\u000e\u001a\u00020\f\u0012\u0006\u0010\u000f\u001a\u00020\f\u0012\u0006\u0010\u0010\u001a\u00020\f\u0012\u0006\u0010\u0011\u001a\u00020\f\u0012\u0006\u0010\u0012\u001a\u00020\f¢\u0006\u0002\u0010\u0013J\t\u0010'\u001a\u00020\u0003HÆ\u0003J\t\u0010(\u001a\u00020\fHÆ\u0003J\t\u0010)\u001a\u00020\fHÆ\u0003J\t\u0010*\u001a\u00020\fHÆ\u0003J\t\u0010+\u001a\u00020\fHÆ\u0003J\t\u0010,\u001a\u00020\fHÆ\u0003J\t\u0010-\u001a\u00020\u0003HÆ\u0003J\t\u0010.\u001a\u00020\u0003HÆ\u0003J\t\u0010/\u001a\u00020\u0003HÆ\u0003J\t\u00100\u001a\u00020\bHÆ\u0003J\t\u00101\u001a\u00020\u0003HÆ\u0003J\t\u00102\u001a\u00020\bHÆ\u0003J\t\u00103\u001a\u00020\fHÆ\u0003J\t\u00104\u001a\u00020\fHÆ\u0003J\u0095\u0001\u00105\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00032\b\b\u0002\u0010\u0005\u001a\u00020\u00032\b\b\u0002\u0010\u0006\u001a\u00020\u00032\b\b\u0002\u0010\u0007\u001a\u00020\b2\b\b\u0002\u0010\t\u001a\u00020\u00032\b\b\u0002\u0010\n\u001a\u00020\b2\b\b\u0002\u0010\u000b\u001a\u00020\f2\b\b\u0002\u0010\r\u001a\u00020\f2\b\b\u0002\u0010\u000e\u001a\u00020\f2\b\b\u0002\u0010\u000f\u001a\u00020\f2\b\b\u0002\u0010\u0010\u001a\u00020\f2\b\b\u0002\u0010\u0011\u001a\u00020\f2\b\b\u0002\u0010\u0012\u001a\u00020\fHÆ\u0001J\u0013\u00106\u001a\u0002072\b\u00108\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u00109\u001a\u00020\bHÖ\u0001J\t\u0010:\u001a\u00020\u0003HÖ\u0001R\u0011\u0010\u000b\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\u0014\u0010\u0015R\u0011\u0010\t\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0016\u0010\u0017R\u0011\u0010\u0018\u001a\u00020\u00038F¢\u0006\u0006\u001a\u0004\b\u0019\u0010\u0017R\u0011\u0010\r\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\u001a\u0010\u0015R\u0011\u0010\u0006\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u001b\u0010\u0017R\u0011\u0010\u0004\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u001c\u0010\u0017R\u0011\u0010\u000e\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\u001d\u0010\u0015R\u0011\u0010\u0011\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\u001e\u0010\u0015R\u0011\u0010\u0012\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\u001f\u0010\u0015R\u0011\u0010\u000f\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b \u0010\u0015R\u0011\u0010\u0010\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b!\u0010\u0015R\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\"\u0010\u0017R\u0011\u0010\u0005\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b#\u0010\u0017R\u0011\u0010\u0007\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b$\u0010%R\u0011\u0010\n\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b&\u0010%¨\u0006;"}, d2 = {"Lcom/sih2026/nav/data/model/ClipInfo;", "", "id", "", "driver", "role", "drive", "session", "", "band", "turns", "avgKmh", "", "distanceM", "durationS", "finalDriftM", "finalDriftPct", "finalBaseM", "finalBasePct", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;IDDDDDDD)V", "getAvgKmh", "()D", "getBand", "()Ljava/lang/String;", "bandLabel", "getBandLabel", "getDistanceM", "getDrive", "getDriver", "getDurationS", "getFinalBaseM", "getFinalBasePct", "getFinalDriftM", "getFinalDriftPct", "getId", "getRole", "getSession", "()I", "getTurns", "component1", "component10", "component11", "component12", "component13", "component14", "component2", "component3", "component4", "component5", "component6", "component7", "component8", "component9", "copy", "equals", "", "other", "hashCode", "toString", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class ClipInfo {
    public static final int $stable = 0;
    private final double avgKmh;
    private final String band;
    private final double distanceM;
    private final String drive;
    private final String driver;
    private final double durationS;
    private final double finalBaseM;
    private final double finalBasePct;
    private final double finalDriftM;
    private final double finalDriftPct;
    private final String id;
    private final String role;
    private final int session;
    private final int turns;

    public ClipInfo(String id, String driver, String role, String drive, int i, String band, int i2, double d, double d2, double d3, double d4, double d5, double d6, double d7) {
        Intrinsics.checkNotNullParameter(id, "id");
        Intrinsics.checkNotNullParameter(driver, "driver");
        Intrinsics.checkNotNullParameter(role, "role");
        Intrinsics.checkNotNullParameter(drive, "drive");
        Intrinsics.checkNotNullParameter(band, "band");
        this.id = id;
        this.driver = driver;
        this.role = role;
        this.drive = drive;
        this.session = i;
        this.band = band;
        this.turns = i2;
        this.avgKmh = d;
        this.distanceM = d2;
        this.durationS = d3;
        this.finalDriftM = d4;
        this.finalDriftPct = d5;
        this.finalBaseM = d6;
        this.finalBasePct = d7;
    }

    /* JADX INFO: renamed from: component1, reason: from getter */
    public final String getId() {
        return this.id;
    }

    /* JADX INFO: renamed from: component10, reason: from getter */
    public final double getDurationS() {
        return this.durationS;
    }

    /* JADX INFO: renamed from: component11, reason: from getter */
    public final double getFinalDriftM() {
        return this.finalDriftM;
    }

    /* JADX INFO: renamed from: component12, reason: from getter */
    public final double getFinalDriftPct() {
        return this.finalDriftPct;
    }

    /* JADX INFO: renamed from: component13, reason: from getter */
    public final double getFinalBaseM() {
        return this.finalBaseM;
    }

    /* JADX INFO: renamed from: component14, reason: from getter */
    public final double getFinalBasePct() {
        return this.finalBasePct;
    }

    /* JADX INFO: renamed from: component2, reason: from getter */
    public final String getDriver() {
        return this.driver;
    }

    /* JADX INFO: renamed from: component3, reason: from getter */
    public final String getRole() {
        return this.role;
    }

    /* JADX INFO: renamed from: component4, reason: from getter */
    public final String getDrive() {
        return this.drive;
    }

    /* JADX INFO: renamed from: component5, reason: from getter */
    public final int getSession() {
        return this.session;
    }

    /* JADX INFO: renamed from: component6, reason: from getter */
    public final String getBand() {
        return this.band;
    }

    /* JADX INFO: renamed from: component7, reason: from getter */
    public final int getTurns() {
        return this.turns;
    }

    /* JADX INFO: renamed from: component8, reason: from getter */
    public final double getAvgKmh() {
        return this.avgKmh;
    }

    /* JADX INFO: renamed from: component9, reason: from getter */
    public final double getDistanceM() {
        return this.distanceM;
    }

    public final ClipInfo copy(String id, String driver, String role, String drive, int session, String band, int turns, double avgKmh, double distanceM, double durationS, double finalDriftM, double finalDriftPct, double finalBaseM, double finalBasePct) {
        Intrinsics.checkNotNullParameter(id, "id");
        Intrinsics.checkNotNullParameter(driver, "driver");
        Intrinsics.checkNotNullParameter(role, "role");
        Intrinsics.checkNotNullParameter(drive, "drive");
        Intrinsics.checkNotNullParameter(band, "band");
        return new ClipInfo(id, driver, role, drive, session, band, turns, avgKmh, distanceM, durationS, finalDriftM, finalDriftPct, finalBaseM, finalBasePct);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof ClipInfo)) {
            return false;
        }
        ClipInfo clipInfo = (ClipInfo) other;
        return Intrinsics.areEqual(this.id, clipInfo.id) && Intrinsics.areEqual(this.driver, clipInfo.driver) && Intrinsics.areEqual(this.role, clipInfo.role) && Intrinsics.areEqual(this.drive, clipInfo.drive) && this.session == clipInfo.session && Intrinsics.areEqual(this.band, clipInfo.band) && this.turns == clipInfo.turns && Double.compare(this.avgKmh, clipInfo.avgKmh) == 0 && Double.compare(this.distanceM, clipInfo.distanceM) == 0 && Double.compare(this.durationS, clipInfo.durationS) == 0 && Double.compare(this.finalDriftM, clipInfo.finalDriftM) == 0 && Double.compare(this.finalDriftPct, clipInfo.finalDriftPct) == 0 && Double.compare(this.finalBaseM, clipInfo.finalBaseM) == 0 && Double.compare(this.finalBasePct, clipInfo.finalBasePct) == 0;
    }

    public final double getAvgKmh() {
        return this.avgKmh;
    }

    public final String getBand() {
        return this.band;
    }

    /* JADX WARN: Failed to restore switch over string. Please report as a decompilation issue */
    public final String getBandLabel() {
        String str = this.band;
        switch (str.hashCode()) {
            case 3135580:
                if (str.equals("fast")) {
                    return "70+ km/h";
                }
                break;
            case 3533313:
                if (str.equals("slow")) {
                    return "under 40 km/h";
                }
                break;
            case 103910395:
                if (str.equals("mixed")) {
                    return "40-50 km/h";
                }
                break;
            case 106953334:
                if (str.equals("ps_60")) {
                    return "50-70 km/h";
                }
                break;
        }
        return this.band;
    }

    public final double getDistanceM() {
        return this.distanceM;
    }

    public final String getDrive() {
        return this.drive;
    }

    public final String getDriver() {
        return this.driver;
    }

    public final double getDurationS() {
        return this.durationS;
    }

    public final double getFinalBaseM() {
        return this.finalBaseM;
    }

    public final double getFinalBasePct() {
        return this.finalBasePct;
    }

    public final double getFinalDriftM() {
        return this.finalDriftM;
    }

    public final double getFinalDriftPct() {
        return this.finalDriftPct;
    }

    public final String getId() {
        return this.id;
    }

    public final String getRole() {
        return this.role;
    }

    public final int getSession() {
        return this.session;
    }

    public final int getTurns() {
        return this.turns;
    }

    public int hashCode() {
        return (((((((((((((((((((((((((this.id.hashCode() * 31) + this.driver.hashCode()) * 31) + this.role.hashCode()) * 31) + this.drive.hashCode()) * 31) + Integer.hashCode(this.session)) * 31) + this.band.hashCode()) * 31) + Integer.hashCode(this.turns)) * 31) + Double.hashCode(this.avgKmh)) * 31) + Double.hashCode(this.distanceM)) * 31) + Double.hashCode(this.durationS)) * 31) + Double.hashCode(this.finalDriftM)) * 31) + Double.hashCode(this.finalDriftPct)) * 31) + Double.hashCode(this.finalBaseM)) * 31) + Double.hashCode(this.finalBasePct);
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("ClipInfo(id=").append(this.id).append(", driver=").append(this.driver).append(", role=").append(this.role).append(", drive=").append(this.drive).append(", session=").append(this.session).append(", band=").append(this.band).append(", turns=").append(this.turns).append(", avgKmh=").append(this.avgKmh).append(", distanceM=").append(this.distanceM).append(", durationS=").append(this.durationS).append(", finalDriftM=").append(this.finalDriftM).append(", finalDriftPct=");
        sb.append(this.finalDriftPct).append(", finalBaseM=").append(this.finalBaseM).append(", finalBasePct=").append(this.finalBasePct).append(')');
        return sb.toString();
    }
}
