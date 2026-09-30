package com.sih2026.nav.domain.engine;

import android.content.Context;
import androidx.core.app.NotificationCompat;
import com.sih2026.nav.data.model.ClipInfo;
import com.sih2026.nav.data.model.Mode;
import com.sih2026.nav.data.model.NavState;
import com.sih2026.nav.data.model.ReplayClip;
import com.sih2026.nav.data.model.ReplayLoader;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.CancellationException;
import kotlin.Lazy;
import kotlin.LazyKt;
import kotlin.Metadata;
import kotlin.Pair;
import kotlin.ResultKt;
import kotlin.TuplesKt;
import kotlin.Unit;
import kotlin.collections.ArraysKt;
import kotlin.collections.CollectionsKt;
import kotlin.collections.IntIterator;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.intrinsics.IntrinsicsKt;
import kotlin.coroutines.jvm.internal.DebugMetadata;
import kotlin.coroutines.jvm.internal.SuspendLambda;
import kotlin.jvm.functions.Function0;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.internal.DefaultConstructorMarker;
import kotlin.jvm.internal.Intrinsics;
import kotlin.ranges.IntRange;
import kotlin.ranges.RangesKt;
import kotlinx.coroutines.BuildersKt__Builders_commonKt;
import kotlinx.coroutines.CoroutineScope;
import kotlinx.coroutines.CoroutineScopeKt;
import kotlinx.coroutines.DelayKt;
import kotlinx.coroutines.Job;
import kotlinx.coroutines.flow.FlowKt;
import kotlinx.coroutines.flow.MutableStateFlow;
import kotlinx.coroutines.flow.StateFlow;
import kotlinx.coroutines.flow.StateFlowKt;
import org.json.JSONException;

/* JADX INFO: compiled from: ReplayNavEngine.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000z\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0007\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0005\n\u0002\u0010\b\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u000b\n\u0002\u0010\u0002\n\u0002\b\u0005\n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0002\b\u0005\n\u0002\u0018\u0002\n\u0002\u0010\u0006\n\u0002\b\u0002\b\u0007\u0018\u0000 ;2\u00020\u0001:\u0001;B\u0015\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005¢\u0006\u0002\u0010\u0006J\u0018\u0010)\u001a\u00020*2\u0006\u0010+\u001a\u00020\u00112\u0006\u0010,\u001a\u00020\u001aH\u0002J\u0006\u0010-\u001a\u00020*J\u000e\u0010.\u001a\u00020*2\u0006\u0010/\u001a\u000200J\u0010\u00101\u001a\u00020*2\u0006\u00102\u001a\u000203H\u0016J\u000e\u00104\u001a\u00020*2\u0006\u00105\u001a\u00020\rJ\b\u00106\u001a\u00020*H\u0016J\b\u00107\u001a\u00020*H\u0016J\u0018\u00108\u001a\u0014\u0012\u0010\u0012\u000e\u0012\u0004\u0012\u00020:\u0012\u0004\u0012\u00020:090\u0013R\u0014\u0010\u0007\u001a\b\u0012\u0004\u0012\u00020\t0\bX\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\n\u001a\b\u0012\u0004\u0012\u00020\u000b0\bX\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\f\u001a\b\u0012\u0004\u0012\u00020\r0\bX\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\u000e\u001a\b\u0012\u0004\u0012\u00020\t0\bX\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\u000f\u001a\b\u0012\u0004\u0012\u00020\t0\bX\u0082\u0004¢\u0006\u0002\n\u0000R\u0010\u0010\u0010\u001a\u0004\u0018\u00010\u0011X\u0082\u000e¢\u0006\u0002\n\u0000R!\u0010\u0012\u001a\b\u0012\u0004\u0012\u00020\u00140\u00138FX\u0086\u0084\u0002¢\u0006\f\n\u0004\b\u0017\u0010\u0018\u001a\u0004\b\u0015\u0010\u0016R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u0019\u001a\u00020\u001aX\u0082\u000e¢\u0006\u0002\n\u0000R\u0010\u0010\u001b\u001a\u0004\u0018\u00010\u001cX\u0082\u000e¢\u0006\u0002\n\u0000R\u0017\u0010\u001d\u001a\b\u0012\u0004\u0012\u00020\t0\u001e¢\u0006\b\n\u0000\u001a\u0004\b\u001f\u0010 R\u0017\u0010!\u001a\b\u0012\u0004\u0012\u00020\u000b0\u001e¢\u0006\b\n\u0000\u001a\u0004\b\"\u0010 R\u000e\u0010\u0004\u001a\u00020\u0005X\u0082\u0004¢\u0006\u0002\n\u0000R\u0017\u0010#\u001a\b\u0012\u0004\u0012\u00020\r0\u001e¢\u0006\b\n\u0000\u001a\u0004\b$\u0010 R\u001a\u0010%\u001a\b\u0012\u0004\u0012\u00020\t0\u001eX\u0096\u0004¢\u0006\b\n\u0000\u001a\u0004\b&\u0010 R\u0017\u0010'\u001a\b\u0012\u0004\u0012\u00020\t0\u001e¢\u0006\b\n\u0000\u001a\u0004\b(\u0010 ¨\u0006<"}, d2 = {"Lcom/sih2026/nav/domain/engine/ReplayNavEngine;", "Lcom/sih2026/nav/domain/engine/NavEngine;", "context", "Landroid/content/Context;", "scope", "Lkotlinx/coroutines/CoroutineScope;", "(Landroid/content/Context;Lkotlinx/coroutines/CoroutineScope;)V", "_noMapState", "Lkotlinx/coroutines/flow/MutableStateFlow;", "Lcom/sih2026/nav/data/model/NavState;", "_progress", "Lcom/sih2026/nav/domain/engine/ReplayProgress;", "_speed", "", "_state", "_trueState", "clip", "Lcom/sih2026/nav/data/model/ReplayClip;", "clips", "", "Lcom/sih2026/nav/data/model/ClipInfo;", "getClips", "()Ljava/util/List;", "clips$delegate", "Lkotlin/Lazy;", "frame", "", "job", "Lkotlinx/coroutines/Job;", "noMapState", "Lkotlinx/coroutines/flow/StateFlow;", "getNoMapState", "()Lkotlinx/coroutines/flow/StateFlow;", NotificationCompat.CATEGORY_PROGRESS, "getProgress", "speed", "getSpeed", "state", "getState", "trueState", "getTrueState", "render", "", "c", "f", "restart", "select", "clipId", "", "setGnssBlackout", "enabled", "", "setSpeed", "multiplier", "start", "stop", "trueTrack", "Lkotlin/Pair;", "", "Companion", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class ReplayNavEngine implements NavEngine {
    private final MutableStateFlow<NavState> _noMapState;
    private final MutableStateFlow<ReplayProgress> _progress;
    private final MutableStateFlow<Float> _speed;
    private final MutableStateFlow<NavState> _state;
    private final MutableStateFlow<NavState> _trueState;
    private ReplayClip clip;

    /* JADX INFO: renamed from: clips$delegate, reason: from kotlin metadata */
    private final Lazy clips;
    private final Context context;
    private int frame;
    private Job job;
    private final StateFlow<NavState> noMapState;
    private final StateFlow<ReplayProgress> progress;
    private final CoroutineScope scope;
    private final StateFlow<Float> speed;
    private final StateFlow<NavState> state;
    private final StateFlow<NavState> trueState;
    private static final Companion Companion = new Companion(null);
    public static final int $stable = 8;
    private static final NavState EMPTY = new NavState(52.40384d, -1.50616d, 0.0f, 0.0f, Mode.ACQUIRING, 0.0f, 0);

    /* JADX INFO: compiled from: ReplayNavEngine.kt */
    @Metadata(d1 = {"\u0000\u0014\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\b\u0082\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002¢\u0006\u0002\u0010\u0002R\u0011\u0010\u0003\u001a\u00020\u0004¢\u0006\b\n\u0000\u001a\u0004\b\u0005\u0010\u0006¨\u0006\u0007"}, d2 = {"Lcom/sih2026/nav/domain/engine/ReplayNavEngine$Companion;", "", "()V", "EMPTY", "Lcom/sih2026/nav/data/model/NavState;", "getEMPTY", "()Lcom/sih2026/nav/data/model/NavState;", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
    private static final class Companion {
        private Companion() {
        }

        public /* synthetic */ Companion(DefaultConstructorMarker defaultConstructorMarker) {
            this();
        }

        public final NavState getEMPTY() {
            return ReplayNavEngine.EMPTY;
        }
    }

    /* JADX INFO: renamed from: com.sih2026.nav.domain.engine.ReplayNavEngine$start$1, reason: invalid class name */
    /* JADX INFO: compiled from: ReplayNavEngine.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.domain.engine.ReplayNavEngine$start$1", f = "ReplayNavEngine.kt", i = {0}, l = {91}, m = "invokeSuspend", n = {"$this$launch"}, s = {"L$0"})
    static final class AnonymousClass1 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        final /* synthetic */ ReplayClip $c;
        private /* synthetic */ Object L$0;
        int label;

        /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
        AnonymousClass1(ReplayClip replayClip, Continuation<? super AnonymousClass1> continuation) {
            super(2, continuation);
            this.$c = replayClip;
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            AnonymousClass1 anonymousClass1 = ReplayNavEngine.this.new AnonymousClass1(this.$c, continuation);
            anonymousClass1.L$0 = obj;
            return anonymousClass1;
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass1) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            AnonymousClass1 anonymousClass1;
            CoroutineScope coroutineScope;
            Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    anonymousClass1 = this;
                    coroutineScope = (CoroutineScope) anonymousClass1.L$0;
                    break;
                case 1:
                    anonymousClass1 = this;
                    coroutineScope = (CoroutineScope) anonymousClass1.L$0;
                    ResultKt.throwOnFailure(obj);
                    break;
                default:
                    throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
            }
            while (CoroutineScopeKt.isActive(coroutineScope)) {
                ReplayNavEngine.this.render(anonymousClass1.$c, ReplayNavEngine.this.frame);
                if (ReplayNavEngine.this.frame >= anonymousClass1.$c.getTotalFrames() - 1) {
                    MutableStateFlow mutableStateFlow = ReplayNavEngine.this._progress;
                    ReplayProgress replayProgress = (ReplayProgress) ReplayNavEngine.this._progress.getValue();
                    mutableStateFlow.setValue(replayProgress.copy((2047 & 1) != 0 ? replayProgress.clip : null, (2047 & 2) != 0 ? replayProgress.frame : 0, (2047 & 4) != 0 ? replayProgress.totalFrames : 0, (2047 & 8) != 0 ? replayProgress.inBlackout : false, (2047 & 16) != 0 ? replayProgress.elapsedS : 0.0f, (2047 & 32) != 0 ? replayProgress.distanceM : 0.0f, (2047 & 64) != 0 ? replayProgress.driftM : 0.0f, (2047 & 128) != 0 ? replayProgress.driftPct : 0.0f, (2047 & 256) != 0 ? replayProgress.noMapDriftM : 0.0f, (2047 & 512) != 0 ? replayProgress.noMapDriftPct : 0.0f, (2047 & 1024) != 0 ? replayProgress.onMap : false, (2047 & 2048) != 0 ? replayProgress.playing : false));
                    return Unit.INSTANCE;
                }
                ReplayNavEngine.this.frame++;
                anonymousClass1.L$0 = coroutineScope;
                anonymousClass1.label = 1;
                if (DelayKt.delay(RangesKt.coerceAtLeast((long) ((1000.0f / anonymousClass1.$c.getHz()) / ((Number) ReplayNavEngine.this._speed.getValue()).floatValue()), 8L), anonymousClass1) == coroutine_suspended) {
                    return coroutine_suspended;
                }
            }
            return Unit.INSTANCE;
        }
    }

    public ReplayNavEngine(Context context, CoroutineScope scope) {
        Intrinsics.checkNotNullParameter(context, "context");
        Intrinsics.checkNotNullParameter(scope, "scope");
        this.context = context;
        this.scope = scope;
        this.clips = LazyKt.lazy(new Function0<List<? extends ClipInfo>>() { // from class: com.sih2026.nav.domain.engine.ReplayNavEngine$clips$2
            {
                super(0);
            }

            @Override // kotlin.jvm.functions.Function0
            public final List<? extends ClipInfo> invoke() {
                return ReplayLoader.INSTANCE.index(this.this$0.context);
            }
        });
        this._state = StateFlowKt.MutableStateFlow(EMPTY);
        this.state = FlowKt.asStateFlow(this._state);
        this._trueState = StateFlowKt.MutableStateFlow(EMPTY);
        this.trueState = FlowKt.asStateFlow(this._trueState);
        this._noMapState = StateFlowKt.MutableStateFlow(EMPTY);
        this.noMapState = FlowKt.asStateFlow(this._noMapState);
        this._progress = StateFlowKt.MutableStateFlow(new ReplayProgress(null, 0, 0, false, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, false, false, 4095, null));
        this.progress = FlowKt.asStateFlow(this._progress);
        this._speed = StateFlowKt.MutableStateFlow(Float.valueOf(1.0f));
        this.speed = FlowKt.asStateFlow(this._speed);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public final void render(ReplayClip c, int f) {
        long jNanoTime = System.nanoTime();
        if (f < c.getLeadInFrames()) {
            NavState navState = new NavState(c.getLeadInLat()[f], c.getLeadInLon()[f], c.getLeadInHeading()[f], c.getLeadInSpeedKmh()[f], Mode.GNSS_FUSED, 4.0f, jNanoTime);
            this._state.setValue(navState);
            this._trueState.setValue(navState);
            this._noMapState.setValue(navState);
            this._progress.setValue(new ReplayProgress(c.getInfo(), f, c.getTotalFrames(), false, (f - c.getLeadInFrames()) / c.getHz(), 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, false, this._progress.getValue().getPlaying(), 2016, null));
            return;
        }
        int iCoerceIn = RangesKt.coerceIn(f - c.getLeadInFrames(), 0, c.getBlackoutFrames() - 1);
        this._trueState.setValue(new NavState(c.getTrueLat()[iCoerceIn], c.getTrueLon()[iCoerceIn], c.getTrueHeading()[iCoerceIn], c.getTrueSpeedKmh()[iCoerceIn], Mode.GNSS_FUSED, 4.0f, jNanoTime));
        this._state.setValue(new NavState(c.getPfLat()[iCoerceIn], c.getPfLon()[iCoerceIn], c.getPfHeading()[iCoerceIn], (float) c.getEngineSpeedKmh(), Mode.DEAD_RECKONING, c.getDriftM()[iCoerceIn], jNanoTime));
        MutableStateFlow<NavState> mutableStateFlow = this._noMapState;
        NavState value = this._state.getValue();
        mutableStateFlow.setValue(value.copy((16 & 1) != 0 ? value.lat : c.getNoMapLat()[iCoerceIn], (16 & 2) != 0 ? value.lon : c.getNoMapLon()[iCoerceIn], (16 & 4) != 0 ? value.headingDeg : 0.0f, (16 & 8) != 0 ? value.speedKmh : 0.0f, (16 & 16) != 0 ? value.mode : null, (16 & 32) != 0 ? value.uncertaintyM : c.getNoMapDriftM()[iCoerceIn], (16 & 64) != 0 ? value.timestampNs : 0L));
        this._progress.setValue(new ReplayProgress(c.getInfo(), f, c.getTotalFrames(), true, iCoerceIn / c.getHz(), c.getTrueDistM()[iCoerceIn], c.getDriftM()[iCoerceIn], c.getDriftPct()[iCoerceIn], c.getNoMapDriftM()[iCoerceIn], c.getNoMapDriftPct()[iCoerceIn], c.getPfOnMap()[iCoerceIn], this._progress.getValue().getPlaying()));
    }

    public final List<ClipInfo> getClips() {
        return (List) this.clips.getValue();
    }

    public final StateFlow<NavState> getNoMapState() {
        return this.noMapState;
    }

    public final StateFlow<ReplayProgress> getProgress() {
        return this.progress;
    }

    public final StateFlow<Float> getSpeed() {
        return this.speed;
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public StateFlow<NavState> getState() {
        return this.state;
    }

    public final StateFlow<NavState> getTrueState() {
        return this.trueState;
    }

    public final void restart() {
        ReplayClip replayClip = this.clip;
        if (replayClip == null) {
            return;
        }
        stop();
        this.frame = 0;
        render(replayClip, 0);
    }

    public final void select(String clipId) throws JSONException {
        Intrinsics.checkNotNullParameter(clipId, "clipId");
        stop();
        ReplayClip replayClipLoad = ReplayLoader.INSTANCE.load(this.context, clipId);
        this.clip = replayClipLoad;
        this.frame = 0;
        render(replayClipLoad, 0);
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public void setGnssBlackout(boolean enabled) {
        ReplayClip replayClip = this.clip;
        if (replayClip == null) {
            return;
        }
        this.frame = enabled ? replayClip.getLeadInFrames() : 0;
        render(replayClip, this.frame);
    }

    public final void setSpeed(float multiplier) {
        this._speed.setValue(Float.valueOf(RangesKt.coerceIn(multiplier, 1.0f, 8.0f)));
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public void start() {
        ReplayClip replayClip = this.clip;
        if (replayClip == null) {
            return;
        }
        Job job = this.job;
        boolean z = false;
        if (job != null && job.isActive()) {
            z = true;
        }
        if (z) {
            return;
        }
        this.job = BuildersKt__Builders_commonKt.launch$default(this.scope, null, null, new AnonymousClass1(replayClip, null), 3, null);
        MutableStateFlow<ReplayProgress> mutableStateFlow = this._progress;
        ReplayProgress value = this._progress.getValue();
        mutableStateFlow.setValue(value.copy((2047 & 1) != 0 ? value.clip : null, (2047 & 2) != 0 ? value.frame : 0, (2047 & 4) != 0 ? value.totalFrames : 0, (2047 & 8) != 0 ? value.inBlackout : false, (2047 & 16) != 0 ? value.elapsedS : 0.0f, (2047 & 32) != 0 ? value.distanceM : 0.0f, (2047 & 64) != 0 ? value.driftM : 0.0f, (2047 & 128) != 0 ? value.driftPct : 0.0f, (2047 & 256) != 0 ? value.noMapDriftM : 0.0f, (2047 & 512) != 0 ? value.noMapDriftPct : 0.0f, (2047 & 1024) != 0 ? value.onMap : false, (2047 & 2048) != 0 ? value.playing : true));
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public void stop() {
        Job job = this.job;
        if (job != null) {
            Job.DefaultImpls.cancel$default(job, (CancellationException) null, 1, (Object) null);
        }
        this.job = null;
        MutableStateFlow<ReplayProgress> mutableStateFlow = this._progress;
        ReplayProgress value = this._progress.getValue();
        mutableStateFlow.setValue(value.copy((2047 & 1) != 0 ? value.clip : null, (2047 & 2) != 0 ? value.frame : 0, (2047 & 4) != 0 ? value.totalFrames : 0, (2047 & 8) != 0 ? value.inBlackout : false, (2047 & 16) != 0 ? value.elapsedS : 0.0f, (2047 & 32) != 0 ? value.distanceM : 0.0f, (2047 & 64) != 0 ? value.driftM : 0.0f, (2047 & 128) != 0 ? value.driftPct : 0.0f, (2047 & 256) != 0 ? value.noMapDriftM : 0.0f, (2047 & 512) != 0 ? value.noMapDriftPct : 0.0f, (2047 & 1024) != 0 ? value.onMap : false, (2047 & 2048) != 0 ? value.playing : false));
    }

    public final List<Pair<Double, Double>> trueTrack() {
        ReplayClip replayClip = this.clip;
        if (replayClip == null) {
            return CollectionsKt.emptyList();
        }
        IntRange indices = ArraysKt.getIndices(replayClip.getTrueLat());
        ArrayList arrayList = new ArrayList(CollectionsKt.collectionSizeOrDefault(indices, 10));
        Iterator<Integer> it = indices.iterator();
        while (it.hasNext()) {
            int iNextInt = ((IntIterator) it).nextInt();
            arrayList.add(TuplesKt.to(Double.valueOf(replayClip.getTrueLat()[iNextInt]), Double.valueOf(replayClip.getTrueLon()[iNextInt])));
        }
        return arrayList;
    }
}
