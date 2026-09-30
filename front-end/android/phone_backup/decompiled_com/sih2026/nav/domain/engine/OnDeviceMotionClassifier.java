package com.sih2026.nav.domain.engine;

import com.sih2026.nav.domain.sensor.ImuSample;
import java.util.List;
import kotlin.Metadata;
import kotlin.collections.ArraysKt;
import kotlin.collections.CollectionsKt;
import kotlin.jvm.internal.Intrinsics;
import kotlin.ranges.RangesKt;

/* JADX INFO: compiled from: OnDeviceMotionClassifier.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u00002\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u0007\n\u0000\n\u0002\u0010\u0014\n\u0000\n\u0002\u0010\u0006\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0005\b\u0007\u0018\u0000 \u00122\u00020\u0001:\u0001\u0012B\u0005¢\u0006\u0002\u0010\u0002J \u0010\u0003\u001a\u00020\u00042\u0006\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0007\u001a\u00020\b2\u0006\u0010\t\u001a\u00020\bH\u0002J\u0014\u0010\n\u001a\u00020\u000b2\f\u0010\f\u001a\b\u0012\u0004\u0012\u00020\u000e0\rJ\u0014\u0010\u000f\u001a\u00020\u00062\f\u0010\f\u001a\b\u0012\u0004\u0012\u00020\u000e0\rJ\u0010\u0010\u0010\u001a\u00020\u00042\u0006\u0010\u0005\u001a\u00020\u0006H\u0002J\u0010\u0010\u0011\u001a\u00020\u00042\u0006\u0010\u0005\u001a\u00020\u0006H\u0002¨\u0006\u0013"}, d2 = {"Lcom/sih2026/nav/domain/engine/OnDeviceMotionClassifier;", "", "()V", "bandPassEnergy", "", "arr", "", "lo", "", "hi", "classify", "Lcom/sih2026/nav/domain/engine/MotionMlResult;", "samples", "", "Lcom/sih2026/nav/domain/sensor/ImuSample;", "extractFeatures", "meanAbsDiff", "stdDev", "Companion", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class OnDeviceMotionClassifier {
    public static final int $stable = 0;
    public static final double FS = 10.0d;
    public static final int WINDOW_SAMPLES = 20;

    private final float bandPassEnergy(float[] arr, double lo, double hi) {
        float fAverage = (float) ArraysKt.average(arr);
        float f = 0.0f;
        for (float f2 : arr) {
            float f3 = f2 - fAverage;
            f += f3 * f3;
        }
        return RangesKt.coerceAtLeast(f * ((float) ((hi - lo) / 5.0d)), 1.0E-6f);
    }

    private final float meanAbsDiff(float[] arr) {
        if (arr.length < 2) {
            return 0.0f;
        }
        float fAbs = 0.0f;
        int length = arr.length - 1;
        for (int i = 0; i < length; i++) {
            fAbs += Math.abs(arr[i + 1] - arr[i]);
        }
        return fAbs / (arr.length - 1);
    }

    private final float stdDev(float[] arr) {
        float fAverage = (float) ArraysKt.average(arr);
        float f = 0.0f;
        for (float f2 : arr) {
            float f3 = f2 - fAverage;
            f += f3 * f3;
        }
        return (float) Math.sqrt(f / arr.length);
    }

    public final MotionMlResult classify(List<ImuSample> samples) {
        Intrinsics.checkNotNullParameter(samples, "samples");
        float[] fArrExtractFeatures = extractFeatures(samples);
        float f = fArrExtractFeatures[6];
        boolean z = f < 0.08f && fArrExtractFeatures[7] < 0.25f && fArrExtractFeatures[1] < 0.35f;
        return new MotionMlResult(z, fArrExtractFeatures, z ? RangesKt.coerceIn(1.0f - f, 0.5f, 0.99f) : 0.85f);
    }

    public final float[] extractFeatures(List<ImuSample> samples) {
        int i;
        Intrinsics.checkNotNullParameter(samples, "samples");
        if (!(samples.size() >= 20)) {
            throw new IllegalArgumentException("Expected at least 20 samples".toString());
        }
        List listTake = CollectionsKt.take(samples, 20);
        float[] fArr = new float[20];
        float[] fArr2 = new float[20];
        float[] fArr3 = new float[20];
        float[] fArr4 = new float[20];
        float[] fArr5 = new float[20];
        float[] fArr6 = new float[20];
        float[] fArr7 = new float[20];
        float[] fArr8 = new float[20];
        int i2 = 0;
        for (int i3 = 20; i2 < i3; i3 = 20) {
            ImuSample imuSample = (ImuSample) listTake.get(i2);
            fArr[i2] = imuSample.getAx();
            fArr2[i2] = imuSample.getAy();
            fArr3[i2] = imuSample.getAz();
            fArr4[i2] = imuSample.getGx();
            fArr5[i2] = imuSample.getGy();
            fArr6[i2] = imuSample.getGz();
            fArr7[i2] = (float) Math.sqrt((imuSample.getAx() * imuSample.getAx()) + (imuSample.getAy() * imuSample.getAy()) + (imuSample.getAz() * imuSample.getAz()));
            fArr8[i2] = (float) Math.sqrt((imuSample.getGx() * imuSample.getGx()) + (imuSample.getGy() * imuSample.getGy()) + (imuSample.getGz() * imuSample.getGz()));
            i2++;
        }
        float[] fArr9 = new float[26];
        int i4 = 0 + 1;
        fArr9[0] = (float) ArraysKt.average(fArr7);
        int i5 = i4 + 1;
        fArr9[i4] = stdDev(fArr7);
        int i6 = i5 + 1;
        Float fMinOrNull = ArraysKt.minOrNull(fArr7);
        fArr9[i5] = fMinOrNull != null ? fMinOrNull.floatValue() : 0.0f;
        int i7 = i6 + 1;
        Float fMaxOrNull = ArraysKt.maxOrNull(fArr7);
        fArr9[i6] = fMaxOrNull != null ? fMaxOrNull.floatValue() : 0.0f;
        int i8 = i7 + 1;
        fArr9[i7] = meanAbsDiff(fArr7);
        int i9 = i8 + 1;
        fArr9[i8] = (float) ArraysKt.average(fArr8);
        int i10 = i9 + 1;
        fArr9[i9] = stdDev(fArr8);
        int i11 = i10 + 1;
        Float fMaxOrNull2 = ArraysKt.maxOrNull(fArr8);
        fArr9[i10] = fMaxOrNull2 != null ? fMaxOrNull2.floatValue() : 0.0f;
        List listListOf = CollectionsKt.listOf((Object[]) new float[][]{fArr, fArr2, fArr3});
        List listListOf2 = CollectionsKt.listOf((Object[]) new float[][]{fArr4, fArr5, fArr6});
        int i12 = 0;
        while (true) {
            float[] fArr10 = fArr8;
            i = 3;
            if (i12 >= 3) {
                break;
            }
            int i13 = i11 + 1;
            fArr9[i11] = stdDev((float[]) listListOf.get(i12));
            int i14 = i13 + 1;
            fArr9[i13] = meanAbsDiff((float[]) listListOf.get(i12));
            fArr9[i14] = stdDev((float[]) listListOf2.get(i12));
            i12++;
            i11 = i14 + 1;
            fArr8 = fArr10;
        }
        int i15 = 0;
        int i16 = i11;
        while (i15 < i) {
            int i17 = i15;
            List list = listListOf;
            List list2 = listListOf2;
            float[] fArr11 = fArr9;
            float fBandPassEnergy = bandPassEnergy((float[]) listListOf.get(i15), 0.5d, 1.5d);
            float fBandPassEnergy2 = bandPassEnergy((float[]) list.get(i17), 1.5d, 3.0d);
            float fBandPassEnergy3 = bandPassEnergy((float[]) list.get(i17), 3.0d, 5.0d);
            int i18 = i16 + 1;
            fArr11[i16] = (float) Math.log(fBandPassEnergy + 1.0E-9f);
            int i19 = i18 + 1;
            fArr11[i18] = (float) Math.log(fBandPassEnergy2 + 1.0E-9f);
            i16 = i19 + 1;
            fArr11[i19] = (float) Math.log(1.0E-9f + fBandPassEnergy3);
            i15 = i17 + 1;
            listListOf = list;
            listListOf2 = list2;
            fArr9 = fArr11;
            i = i;
            listTake = listTake;
        }
        return fArr9;
    }
}
