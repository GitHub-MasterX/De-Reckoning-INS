package com.sih2026.nav.domain.engine;

import java.util.Arrays;
import kotlin.Metadata;
import kotlin.jvm.internal.Intrinsics;

/* JADX INFO: compiled from: OnDeviceMotionClassifier.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000*\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u000b\n\u0000\n\u0002\u0010\u0014\n\u0000\n\u0002\u0010\u0007\n\u0002\b\r\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0000\b\u0087\b\u0018\u00002\u00020\u0001B\u001d\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\u0006\u0010\u0006\u001a\u00020\u0007¢\u0006\u0002\u0010\bJ\t\u0010\u000e\u001a\u00020\u0003HÆ\u0003J\t\u0010\u000f\u001a\u00020\u0005HÆ\u0003J\t\u0010\u0010\u001a\u00020\u0007HÆ\u0003J'\u0010\u0011\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00052\b\b\u0002\u0010\u0006\u001a\u00020\u0007HÆ\u0001J\u0013\u0010\u0012\u001a\u00020\u00032\b\u0010\u0013\u001a\u0004\u0018\u00010\u0001HÖ\u0003J\t\u0010\u0014\u001a\u00020\u0015HÖ\u0001J\t\u0010\u0016\u001a\u00020\u0017HÖ\u0001R\u0011\u0010\u0006\u001a\u00020\u0007¢\u0006\b\n\u0000\u001a\u0004\b\t\u0010\nR\u0011\u0010\u0004\u001a\u00020\u0005¢\u0006\b\n\u0000\u001a\u0004\b\u000b\u0010\fR\u0011\u0010\u0002\u001a\u00020\u0003¢\u0006\b\n\u0000\u001a\u0004\b\u0002\u0010\r¨\u0006\u0018"}, d2 = {"Lcom/sih2026/nav/domain/engine/MotionMlResult;", "", "isStationary", "", "features", "", "confidence", "", "(Z[FF)V", "getConfidence", "()F", "getFeatures", "()[F", "()Z", "component1", "component2", "component3", "copy", "equals", "other", "hashCode", "", "toString", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final /* data */ class MotionMlResult {
    public static final int $stable = 8;
    private final float confidence;
    private final float[] features;
    private final boolean isStationary;

    public MotionMlResult(boolean z, float[] features, float f) {
        Intrinsics.checkNotNullParameter(features, "features");
        this.isStationary = z;
        this.features = features;
        this.confidence = f;
    }

    public static /* synthetic */ MotionMlResult copy$default(MotionMlResult motionMlResult, boolean z, float[] fArr, float f, int i, Object obj) {
        if ((i & 1) != 0) {
            z = motionMlResult.isStationary;
        }
        if ((i & 2) != 0) {
            fArr = motionMlResult.features;
        }
        if ((i & 4) != 0) {
            f = motionMlResult.confidence;
        }
        return motionMlResult.copy(z, fArr, f);
    }

    /* JADX INFO: renamed from: component1, reason: from getter */
    public final boolean getIsStationary() {
        return this.isStationary;
    }

    /* JADX INFO: renamed from: component2, reason: from getter */
    public final float[] getFeatures() {
        return this.features;
    }

    /* JADX INFO: renamed from: component3, reason: from getter */
    public final float getConfidence() {
        return this.confidence;
    }

    public final MotionMlResult copy(boolean isStationary, float[] features, float confidence) {
        Intrinsics.checkNotNullParameter(features, "features");
        return new MotionMlResult(isStationary, features, confidence);
    }

    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof MotionMlResult)) {
            return false;
        }
        MotionMlResult motionMlResult = (MotionMlResult) other;
        return this.isStationary == motionMlResult.isStationary && Intrinsics.areEqual(this.features, motionMlResult.features) && Float.compare(this.confidence, motionMlResult.confidence) == 0;
    }

    public final float getConfidence() {
        return this.confidence;
    }

    public final float[] getFeatures() {
        return this.features;
    }

    public int hashCode() {
        return (((Boolean.hashCode(this.isStationary) * 31) + Arrays.hashCode(this.features)) * 31) + Float.hashCode(this.confidence);
    }

    public final boolean isStationary() {
        return this.isStationary;
    }

    public String toString() {
        return "MotionMlResult(isStationary=" + this.isStationary + ", features=" + Arrays.toString(this.features) + ", confidence=" + this.confidence + ')';
    }
}
