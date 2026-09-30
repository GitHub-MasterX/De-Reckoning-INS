package com.sih2026.nav.domain.engine;

import com.sih2026.nav.data.model.ClipInfo;
import kotlin.Metadata;
import kotlin.jvm.internal.DefaultConstructorMarker;
import kotlin.jvm.internal.Intrinsics;

/* JADX INFO: compiled from: ReplayNavEngine.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000,\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0000\n\u0002\u0010\u0007\n\u0002\b)\n\u0002\u0010\u000e\n\u0000\b\u0087\b\u0018\u00002\u00020\u0001B\u007f\u0012\n\b\u0002\u0010\u0002\u001a\u0004\u0018\u00010\u0003\u0012\b\b\u0002\u0010\u0004\u001a\u00020\u0005\u0012\b\b\u0002\u0010\u0006\u001a\u00020\u0005\u0012\b\b\u0002\u0010\u0007\u001a\u00020\b\u0012\b\b\u0002\u0010\t\u001a\u00020\n\u0012\b\b\u0002\u0010\u000b\u001a\u00020\n\u0012\b\b\u0002\u0010\f\u001a\u00020\n\u0012\b\b\u0002\u0010\r\u001a\u00020\n\u0012\b\b\u0002\u0010\u000e\u001a\u00020\n\u0012\b\b\u0002\u0010\u000f\u001a\u00020\n\u0012\b\b\u0002\u0010\u0010\u001a\u00020\b\u0012\b\b\u0002\u0010\u0011\u001a\u00020\b¢\u0006\u0002\u0010\u0012J\u000b\u0010#\u001a\u0004\u0018\u00010\u0003HÆ\u0003J\t\u0010$\u001a\u00020\nHÆ\u0003J\t\u0010%\u001a\u00020\bHÆ\u0003J\t\u0010&\u001a\u00020\bHÆ\u0003J\t\u0010'\u001a\u00020\u0005HÆ\u0003J\t\u0010(\u001a\u00020\u0005HÆ\u0003J\t\u0010)\u001a\u00020\bHÆ\u0003J\t\u0010*\u001a\u00020\nHÆ\u0003J\t\u0010+\u001a\u00020\nHÆ\u0003J\t\u0010,\u001a\u00020\nHÆ\u0003J\t\u0010-\u001a\u00020\nHÆ\u0003J\t\u0010.\u001a\u00020\nHÆ\u0003J\u0083\u0001\u0010/\u001a\u00020\u00002\n\b\u0002\u0010\u0002\u001a\u0004\u0018\u00010\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00052\b\b\u0002\u0010\u0006\u001a\u00020\u00052\b\b\u0002\u0010\u0007\u001a\u00020\b2\b\b\u0002\u0010\t\u001a\u00020\n2\b\b\u0002\u0010\u000b\u001a\u00020\n2\b\b\u0002\u0010\f\u001a\u00020\n2\b\b\u0002\u0010\r\u001a\u00020\n2\b\b\u0002\u0010\u000e\u001a\u00020\n2\b\b\u0002\u0010\u000f\u001a\u00020\n2\b\b\u0002\u0010\u0010\u001a\u00020\b2\b\b\u0002\u0010\u0011\u001a\u00020\bHÆ\u0001J\u0013\u00100\u001a\u00020\b2\b\u00101\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u00102\u001a\u00020\u0005HÖ\u0001J\t\u00103\u001a\u000204HÖ\u0001R\u0013\u0010\u0002\u001a\u0004\u0018\u00010\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014R\u0011\u0010\u000b\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\u0016R\u0011\u0010\f\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u0017\u0010\u0016R\u0011\u0010\r\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u0018\u0010\u0016R\u0011\u0010\t\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u0019\u0010\u0016R\u0011\u0010\u0004\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u001a\u0010\u001bR\u0011\u0010\u0007\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b\u001c\u0010\u001dR\u0011\u0010\u000e\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u001e\u0010\u0016R\u0011\u0010\u000f\u001a\u00020\n¢\u0006\b\n\u0000\u001a\u0004\b\u001f\u0010\u0016R\u0011\u0010\u0010\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b \u0010\u001dR\u0011\u0010\u0011\u001a\u00020\b¢\u0006\b\n\u0000\u001a\u0004\b!\u0010\u001dR\u0011\u0010\u0006\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\"\u0010\u001b¨\u00065"}, d2 = {"Lcom/sih2026/nav/domain/engine/ReplayProgress;", "", "clip", "Lcom/sih2026/nav/data/model/ClipInfo;", "frame", "", "totalFrames", "inBlackout", "", "elapsedS", "", "distanceM", "driftM", "driftPct", "noMapDriftM", "noMapDriftPct", "onMap", "playing", "(Lcom/sih2026/nav/data/model/ClipInfo;IIZFFFFFFZZ)V", "getClip", "()Lcom/sih2026/nav/data/model/ClipInfo;", "getDistanceM", "()F", "getDriftM", "getDriftPct", "getElapsedS", "getFrame", "()I", "getInBlackout", "()Z", "getNoMapDriftM", "getNoMapDriftPct", "getOnMap", "getPlaying", "getTotalFrames", "component1", "component10", "component11", "component12", "component2", "component3", "component4", "component5", "component6", "component7", "component8", "component9", "copy", "equals", "other", "hashCode", "toString", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class ReplayProgress {
    public static final int $stable = 0;
    private final ClipInfo clip;
    private final float distanceM;
    private final float driftM;
    private final float driftPct;
    private final float elapsedS;
    private final int frame;
    private final boolean inBlackout;
    private final float noMapDriftM;
    private final float noMapDriftPct;
    private final boolean onMap;
    private final boolean playing;
    private final int totalFrames;

    public ReplayProgress() {
        this(null, 0, 0, false, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, false, false, 4095, null);
    }

    public ReplayProgress(ClipInfo clipInfo, int i, int i2, boolean z, float f, float f2, float f3, float f4, float f5, float f6, boolean z2, boolean z3) {
        this.clip = clipInfo;
        this.frame = i;
        this.totalFrames = i2;
        this.inBlackout = z;
        this.elapsedS = f;
        this.distanceM = f2;
        this.driftM = f3;
        this.driftPct = f4;
        this.noMapDriftM = f5;
        this.noMapDriftPct = f6;
        this.onMap = z2;
        this.playing = z3;
    }

    public /* synthetic */ ReplayProgress(ClipInfo clipInfo, int i, int i2, boolean z, float f, float f2, float f3, float f4, float f5, float f6, boolean z2, boolean z3, int i3, DefaultConstructorMarker defaultConstructorMarker) {
        this((i3 & 1) != 0 ? null : clipInfo, (i3 & 2) != 0 ? 0 : i, (i3 & 4) != 0 ? 0 : i2, (i3 & 8) != 0 ? false : z, (i3 & 16) != 0 ? 0.0f : f, (i3 & 32) != 0 ? 0.0f : f2, (i3 & 64) != 0 ? 0.0f : f3, (i3 & 128) != 0 ? 0.0f : f4, (i3 & 256) != 0 ? 0.0f : f5, (i3 & 512) == 0 ? f6 : 0.0f, (i3 & 1024) != 0 ? false : z2, (i3 & 2048) == 0 ? z3 : false);
    }

    /* JADX INFO: renamed from: component1, reason: from getter */
    public final ClipInfo getClip() {
        return this.clip;
    }

    /* JADX INFO: renamed from: component10, reason: from getter */
    public final float getNoMapDriftPct() {
        return this.noMapDriftPct;
    }

    /* JADX INFO: renamed from: component11, reason: from getter */
    public final boolean getOnMap() {
        return this.onMap;
    }

    /* JADX INFO: renamed from: component12, reason: from getter */
    public final boolean getPlaying() {
        return this.playing;
    }

    /* JADX INFO: renamed from: component2, reason: from getter */
    public final int getFrame() {
        return this.frame;
    }

    /* JADX INFO: renamed from: component3, reason: from getter */
    public final int getTotalFrames() {
        return this.totalFrames;
    }

    /* JADX INFO: renamed from: component4, reason: from getter */
    public final boolean getInBlackout() {
        return this.inBlackout;
    }

    /* JADX INFO: renamed from: component5, reason: from getter */
    public final float getElapsedS() {
        return this.elapsedS;
    }

    /* JADX INFO: renamed from: component6, reason: from getter */
    public final float getDistanceM() {
        return this.distanceM;
    }

    /* JADX INFO: renamed from: component7, reason: from getter */
    public final float getDriftM() {
        return this.driftM;
    }

    /* JADX INFO: renamed from: component8, reason: from getter */
    public final float getDriftPct() {
        return this.driftPct;
    }

    /* JADX INFO: renamed from: component9, reason: from getter */
    public final float getNoMapDriftM() {
        return this.noMapDriftM;
    }

    public final ReplayProgress copy(ClipInfo clip, int frame, int totalFrames, boolean inBlackout, float elapsedS, float distanceM, float driftM, float driftPct, float noMapDriftM, float noMapDriftPct, boolean onMap, boolean playing) {
        return new ReplayProgress(clip, frame, totalFrames, inBlackout, elapsedS, distanceM, driftM, driftPct, noMapDriftM, noMapDriftPct, onMap, playing);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof ReplayProgress)) {
            return false;
        }
        ReplayProgress replayProgress = (ReplayProgress) other;
        return Intrinsics.areEqual(this.clip, replayProgress.clip) && this.frame == replayProgress.frame && this.totalFrames == replayProgress.totalFrames && this.inBlackout == replayProgress.inBlackout && Float.compare(this.elapsedS, replayProgress.elapsedS) == 0 && Float.compare(this.distanceM, replayProgress.distanceM) == 0 && Float.compare(this.driftM, replayProgress.driftM) == 0 && Float.compare(this.driftPct, replayProgress.driftPct) == 0 && Float.compare(this.noMapDriftM, replayProgress.noMapDriftM) == 0 && Float.compare(this.noMapDriftPct, replayProgress.noMapDriftPct) == 0 && this.onMap == replayProgress.onMap && this.playing == replayProgress.playing;
    }

    public final ClipInfo getClip() {
        return this.clip;
    }

    public final float getDistanceM() {
        return this.distanceM;
    }

    public final float getDriftM() {
        return this.driftM;
    }

    public final float getDriftPct() {
        return this.driftPct;
    }

    public final float getElapsedS() {
        return this.elapsedS;
    }

    public final int getFrame() {
        return this.frame;
    }

    public final boolean getInBlackout() {
        return this.inBlackout;
    }

    public final float getNoMapDriftM() {
        return this.noMapDriftM;
    }

    public final float getNoMapDriftPct() {
        return this.noMapDriftPct;
    }

    public final boolean getOnMap() {
        return this.onMap;
    }

    public final boolean getPlaying() {
        return this.playing;
    }

    public final int getTotalFrames() {
        return this.totalFrames;
    }

    public int hashCode() {
        return ((((((((((((((((((((((this.clip == null ? 0 : this.clip.hashCode()) * 31) + Integer.hashCode(this.frame)) * 31) + Integer.hashCode(this.totalFrames)) * 31) + Boolean.hashCode(this.inBlackout)) * 31) + Float.hashCode(this.elapsedS)) * 31) + Float.hashCode(this.distanceM)) * 31) + Float.hashCode(this.driftM)) * 31) + Float.hashCode(this.driftPct)) * 31) + Float.hashCode(this.noMapDriftM)) * 31) + Float.hashCode(this.noMapDriftPct)) * 31) + Boolean.hashCode(this.onMap)) * 31) + Boolean.hashCode(this.playing);
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("ReplayProgress(clip=").append(this.clip).append(", frame=").append(this.frame).append(", totalFrames=").append(this.totalFrames).append(", inBlackout=").append(this.inBlackout).append(", elapsedS=").append(this.elapsedS).append(", distanceM=").append(this.distanceM).append(", driftM=").append(this.driftM).append(", driftPct=").append(this.driftPct).append(", noMapDriftM=").append(this.noMapDriftM).append(", noMapDriftPct=").append(this.noMapDriftPct).append(", onMap=").append(this.onMap).append(", playing=");
        sb.append(this.playing).append(')');
        return sb.toString();
    }
}
