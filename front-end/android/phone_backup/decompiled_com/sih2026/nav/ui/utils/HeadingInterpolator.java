package com.sih2026.nav.ui.utils;

import com.sih2026.nav.data.model.Mode;
import com.sih2026.nav.data.model.NavState;
import kotlin.Metadata;
import kotlin.jvm.internal.DefaultConstructorMarker;
import kotlin.jvm.internal.Intrinsics;
import kotlin.ranges.RangesKt;

/* JADX INFO: compiled from: HeadingInterpolator.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000\"\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\t\n\u0000\n\u0002\u0010\u0002\n\u0002\b\u0003\b\u0007\u0018\u0000 \f2\u00020\u0001:\u0001\fB\u0005¢\u0006\u0002\u0010\u0002J\u0010\u0010\u0006\u001a\u00020\u00042\b\b\u0002\u0010\u0007\u001a\u00020\bJ\u000e\u0010\t\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\u0004R\u0010\u0010\u0003\u001a\u0004\u0018\u00010\u0004X\u0082\u000e¢\u0006\u0002\n\u0000R\u0010\u0010\u0005\u001a\u0004\u0018\u00010\u0004X\u0082\u000e¢\u0006\u0002\n\u0000¨\u0006\r"}, d2 = {"Lcom/sih2026/nav/ui/utils/HeadingInterpolator;", "", "()V", "currentState", "Lcom/sih2026/nav/data/model/NavState;", "previousState", "interpolate", "nowNs", "", "updateState", "", "newState", "Companion", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class HeadingInterpolator {
    private NavState currentState;
    private NavState previousState;

    /* JADX INFO: renamed from: Companion, reason: from kotlin metadata */
    public static final Companion INSTANCE = new Companion(null);
    public static final int $stable = 8;

    /* JADX INFO: compiled from: HeadingInterpolator.kt */
    @Metadata(d1 = {"\u0000\u0014\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u0007\n\u0002\b\u0004\b\u0086\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002¢\u0006\u0002\u0010\u0002J\u001e\u0010\u0003\u001a\u00020\u00042\u0006\u0010\u0005\u001a\u00020\u00042\u0006\u0010\u0006\u001a\u00020\u00042\u0006\u0010\u0007\u001a\u00020\u0004¨\u0006\b"}, d2 = {"Lcom/sih2026/nav/ui/utils/HeadingInterpolator$Companion;", "", "()V", "lerpAngleShortestPath", "", "startDeg", "endDeg", "fraction", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
    public static final class Companion {
        private Companion() {
        }

        public /* synthetic */ Companion(DefaultConstructorMarker defaultConstructorMarker) {
            this();
        }

        public final float lerpAngleShortestPath(float startDeg, float endDeg, float fraction) {
            float f = (endDeg - startDeg) % 360.0f;
            if (f > 180.0f) {
                f -= 360.0f;
            } else if (f < -180.0f) {
                f += 360.0f;
            }
            return (((f * fraction) + startDeg) + 360.0f) % 360.0f;
        }
    }

    public static /* synthetic */ NavState interpolate$default(HeadingInterpolator headingInterpolator, long j, int i, Object obj) {
        if ((i & 1) != 0) {
            j = System.nanoTime();
        }
        return headingInterpolator.interpolate(j);
    }

    public final NavState interpolate(long nowNs) {
        NavState navState = this.previousState;
        if (navState == null) {
            return new NavState(52.40384d, -1.50616d, 0.0f, 0.0f, Mode.ACQUIRING, 10.0f, nowNs);
        }
        NavState navState2 = this.currentState;
        if (navState2 == null) {
            return navState;
        }
        if (navState.getTimestampNs() >= navState2.getTimestampNs()) {
            return navState2;
        }
        float fCoerceIn = RangesKt.coerceIn((nowNs - navState.getTimestampNs()) / (navState2.getTimestampNs() - navState.getTimestampNs()), 0.0f, 1.0f);
        return navState2.copy((16 & 1) != 0 ? navState2.lat : navState.getLat() + ((navState2.getLat() - navState.getLat()) * ((double) fCoerceIn)), (16 & 2) != 0 ? navState2.lon : navState.getLon() + ((navState2.getLon() - navState.getLon()) * ((double) fCoerceIn)), (16 & 4) != 0 ? navState2.headingDeg : INSTANCE.lerpAngleShortestPath(navState.getHeadingDeg(), navState2.getHeadingDeg(), fCoerceIn), (16 & 8) != 0 ? navState2.speedKmh : navState.getSpeedKmh() + ((navState2.getSpeedKmh() - navState.getSpeedKmh()) * fCoerceIn), (16 & 16) != 0 ? navState2.mode : null, (16 & 32) != 0 ? navState2.uncertaintyM : navState.getUncertaintyM() + ((navState2.getUncertaintyM() - navState.getUncertaintyM()) * fCoerceIn), (16 & 64) != 0 ? navState2.timestampNs : nowNs);
    }

    public final void updateState(NavState newState) {
        Intrinsics.checkNotNullParameter(newState, "newState");
        if (this.currentState == null) {
            this.previousState = newState;
            this.currentState = newState;
        } else {
            this.previousState = this.currentState;
            this.currentState = newState;
        }
    }
}
