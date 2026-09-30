package com.sih2026.nav.data.model;

import kotlin.Metadata;
import kotlin.jvm.internal.Intrinsics;

/* JADX INFO: compiled from: ReplayClip.kt */
/* JADX INFO: loaded from: classes9.dex */
@Metadata(d1 = {"\u00004\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u0006\n\u0000\n\u0002\u0010\u0013\n\u0002\b\u0002\n\u0002\u0010\u0014\n\u0002\b\n\n\u0002\u0010\u0018\n\u0002\b*\b\u0007\u0018\u00002\u00020\u0001Bµ\u0001\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\u0006\u0010\u0006\u001a\u00020\u0007\u0012\u0006\u0010\b\u001a\u00020\t\u0012\u0006\u0010\n\u001a\u00020\t\u0012\u0006\u0010\u000b\u001a\u00020\f\u0012\u0006\u0010\r\u001a\u00020\f\u0012\u0006\u0010\u000e\u001a\u00020\t\u0012\u0006\u0010\u000f\u001a\u00020\t\u0012\u0006\u0010\u0010\u001a\u00020\f\u0012\u0006\u0010\u0011\u001a\u00020\f\u0012\u0006\u0010\u0012\u001a\u00020\f\u0012\u0006\u0010\u0013\u001a\u00020\t\u0012\u0006\u0010\u0014\u001a\u00020\t\u0012\u0006\u0010\u0015\u001a\u00020\f\u0012\u0006\u0010\u0016\u001a\u00020\u0017\u0012\u0006\u0010\u0018\u001a\u00020\t\u0012\u0006\u0010\u0019\u001a\u00020\t\u0012\u0006\u0010\u001a\u001a\u00020\f\u0012\u0006\u0010\u001b\u001a\u00020\f\u0012\u0006\u0010\u001c\u001a\u00020\f\u0012\u0006\u0010\u001d\u001a\u00020\f¢\u0006\u0002\u0010\u001eR\u0011\u0010\u001f\u001a\u00020\u00058F¢\u0006\u0006\u001a\u0004\b \u0010!R\u0011\u0010\u001a\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b\"\u0010#R\u0011\u0010\u001b\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b$\u0010#R\u0011\u0010\u0006\u001a\u00020\u0007¢\u0006\b\n\u0000\u001a\u0004\b%\u0010&R\u0011\u0010\u0004\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b'\u0010!R\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b(\u0010)R\u0011\u0010*\u001a\u00020\u00058F¢\u0006\u0006\u001a\u0004\b+\u0010!R\u0011\u0010\u000b\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b,\u0010#R\u0011\u0010\b\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b-\u0010.R\u0011\u0010\n\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b/\u0010.R\u0011\u0010\r\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b0\u0010#R\u0011\u0010\u001c\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b1\u0010#R\u0011\u0010\u001d\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b2\u0010#R\u0011\u0010\u0018\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b3\u0010.R\u0011\u0010\u0019\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b4\u0010.R\u0011\u0010\u0015\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b5\u0010#R\u0011\u0010\u0013\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b6\u0010.R\u0011\u0010\u0014\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b7\u0010.R\u0011\u0010\u0016\u001a\u00020\u0017¢\u0006\b\n\u0000\u001a\u0004\b8\u00109R\u0011\u0010:\u001a\u00020\u00058F¢\u0006\u0006\u001a\u0004\b;\u0010!R\u0011\u0010\u0012\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b<\u0010#R\u0011\u0010\u0010\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b=\u0010#R\u0011\u0010\u000e\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b>\u0010.R\u0011\u0010\u000f\u001a\u00020\t¢\u0006\b\n\u0000\u001a\u0004\b?\u0010.R\u0011\u0010\u0011\u001a\u00020\f¢\u0006\b\n\u0000\u001a\u0004\b@\u0010#¨\u0006A"}, d2 = {"Lcom/sih2026/nav/data/model/ReplayClip;", "", "info", "Lcom/sih2026/nav/data/model/ClipInfo;", "hz", "", "engineSpeedKmh", "", "leadInLat", "", "leadInLon", "leadInHeading", "", "leadInSpeedKmh", "trueLat", "trueLon", "trueHeading", "trueSpeedKmh", "trueDistM", "pfLat", "pfLon", "pfHeading", "pfOnMap", "", "noMapLat", "noMapLon", "driftM", "driftPct", "noMapDriftM", "noMapDriftPct", "(Lcom/sih2026/nav/data/model/ClipInfo;ID[D[D[F[F[D[D[F[F[F[D[D[F[Z[D[D[F[F[F[F)V", "blackoutFrames", "getBlackoutFrames", "()I", "getDriftM", "()[F", "getDriftPct", "getEngineSpeedKmh", "()D", "getHz", "getInfo", "()Lcom/sih2026/nav/data/model/ClipInfo;", "leadInFrames", "getLeadInFrames", "getLeadInHeading", "getLeadInLat", "()[D", "getLeadInLon", "getLeadInSpeedKmh", "getNoMapDriftM", "getNoMapDriftPct", "getNoMapLat", "getNoMapLon", "getPfHeading", "getPfLat", "getPfLon", "getPfOnMap", "()[Z", "totalFrames", "getTotalFrames", "getTrueDistM", "getTrueHeading", "getTrueLat", "getTrueLon", "getTrueSpeedKmh", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class ReplayClip {
    public static final int $stable = 8;
    private final float[] driftM;
    private final float[] driftPct;
    private final double engineSpeedKmh;
    private final int hz;
    private final ClipInfo info;
    private final float[] leadInHeading;
    private final double[] leadInLat;
    private final double[] leadInLon;
    private final float[] leadInSpeedKmh;
    private final float[] noMapDriftM;
    private final float[] noMapDriftPct;
    private final double[] noMapLat;
    private final double[] noMapLon;
    private final float[] pfHeading;
    private final double[] pfLat;
    private final double[] pfLon;
    private final boolean[] pfOnMap;
    private final float[] trueDistM;
    private final float[] trueHeading;
    private final double[] trueLat;
    private final double[] trueLon;
    private final float[] trueSpeedKmh;

    public ReplayClip(ClipInfo info, int i, double d, double[] leadInLat, double[] leadInLon, float[] leadInHeading, float[] leadInSpeedKmh, double[] trueLat, double[] trueLon, float[] trueHeading, float[] trueSpeedKmh, float[] trueDistM, double[] pfLat, double[] pfLon, float[] pfHeading, boolean[] pfOnMap, double[] noMapLat, double[] noMapLon, float[] driftM, float[] driftPct, float[] noMapDriftM, float[] noMapDriftPct) {
        Intrinsics.checkNotNullParameter(info, "info");
        Intrinsics.checkNotNullParameter(leadInLat, "leadInLat");
        Intrinsics.checkNotNullParameter(leadInLon, "leadInLon");
        Intrinsics.checkNotNullParameter(leadInHeading, "leadInHeading");
        Intrinsics.checkNotNullParameter(leadInSpeedKmh, "leadInSpeedKmh");
        Intrinsics.checkNotNullParameter(trueLat, "trueLat");
        Intrinsics.checkNotNullParameter(trueLon, "trueLon");
        Intrinsics.checkNotNullParameter(trueHeading, "trueHeading");
        Intrinsics.checkNotNullParameter(trueSpeedKmh, "trueSpeedKmh");
        Intrinsics.checkNotNullParameter(trueDistM, "trueDistM");
        Intrinsics.checkNotNullParameter(pfLat, "pfLat");
        Intrinsics.checkNotNullParameter(pfLon, "pfLon");
        Intrinsics.checkNotNullParameter(pfHeading, "pfHeading");
        Intrinsics.checkNotNullParameter(pfOnMap, "pfOnMap");
        Intrinsics.checkNotNullParameter(noMapLat, "noMapLat");
        Intrinsics.checkNotNullParameter(noMapLon, "noMapLon");
        Intrinsics.checkNotNullParameter(driftM, "driftM");
        Intrinsics.checkNotNullParameter(driftPct, "driftPct");
        Intrinsics.checkNotNullParameter(noMapDriftM, "noMapDriftM");
        Intrinsics.checkNotNullParameter(noMapDriftPct, "noMapDriftPct");
        this.info = info;
        this.hz = i;
        this.engineSpeedKmh = d;
        this.leadInLat = leadInLat;
        this.leadInLon = leadInLon;
        this.leadInHeading = leadInHeading;
        this.leadInSpeedKmh = leadInSpeedKmh;
        this.trueLat = trueLat;
        this.trueLon = trueLon;
        this.trueHeading = trueHeading;
        this.trueSpeedKmh = trueSpeedKmh;
        this.trueDistM = trueDistM;
        this.pfLat = pfLat;
        this.pfLon = pfLon;
        this.pfHeading = pfHeading;
        this.pfOnMap = pfOnMap;
        this.noMapLat = noMapLat;
        this.noMapLon = noMapLon;
        this.driftM = driftM;
        this.driftPct = driftPct;
        this.noMapDriftM = noMapDriftM;
        this.noMapDriftPct = noMapDriftPct;
    }

    public final int getBlackoutFrames() {
        return this.trueLat.length;
    }

    public final float[] getDriftM() {
        return this.driftM;
    }

    public final float[] getDriftPct() {
        return this.driftPct;
    }

    public final double getEngineSpeedKmh() {
        return this.engineSpeedKmh;
    }

    public final int getHz() {
        return this.hz;
    }

    public final ClipInfo getInfo() {
        return this.info;
    }

    public final int getLeadInFrames() {
        return this.leadInLat.length;
    }

    public final float[] getLeadInHeading() {
        return this.leadInHeading;
    }

    public final double[] getLeadInLat() {
        return this.leadInLat;
    }

    public final double[] getLeadInLon() {
        return this.leadInLon;
    }

    public final float[] getLeadInSpeedKmh() {
        return this.leadInSpeedKmh;
    }

    public final float[] getNoMapDriftM() {
        return this.noMapDriftM;
    }

    public final float[] getNoMapDriftPct() {
        return this.noMapDriftPct;
    }

    public final double[] getNoMapLat() {
        return this.noMapLat;
    }

    public final double[] getNoMapLon() {
        return this.noMapLon;
    }

    public final float[] getPfHeading() {
        return this.pfHeading;
    }

    public final double[] getPfLat() {
        return this.pfLat;
    }

    public final double[] getPfLon() {
        return this.pfLon;
    }

    public final boolean[] getPfOnMap() {
        return this.pfOnMap;
    }

    public final int getTotalFrames() {
        return getLeadInFrames() + getBlackoutFrames();
    }

    public final float[] getTrueDistM() {
        return this.trueDistM;
    }

    public final float[] getTrueHeading() {
        return this.trueHeading;
    }

    public final double[] getTrueLat() {
        return this.trueLat;
    }

    public final double[] getTrueLon() {
        return this.trueLon;
    }

    public final float[] getTrueSpeedKmh() {
        return this.trueSpeedKmh;
    }
}
