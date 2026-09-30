package com.sih2026.nav.domain.engine;

import android.content.Context;
import com.sih2026.nav.data.model.Mode;
import com.sih2026.nav.data.model.NavState;
import com.sih2026.nav.domain.sensor.GnssFix;
import com.sih2026.nav.domain.sensor.ImuSample;
import com.sih2026.nav.domain.sensor.LiveSensorManager;
import java.util.List;
import java.util.concurrent.CancellationException;
import kotlin.KotlinNothingValueException;
import kotlin.Metadata;
import kotlin.ResultKt;
import kotlin.Unit;
import kotlin.collections.CollectionsKt;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.intrinsics.IntrinsicsKt;
import kotlin.coroutines.jvm.internal.DebugMetadata;
import kotlin.coroutines.jvm.internal.SuspendLambda;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.internal.DefaultConstructorMarker;
import kotlin.jvm.internal.Intrinsics;
import kotlinx.coroutines.BuildersKt__Builders_commonKt;
import kotlinx.coroutines.CoroutineScope;
import kotlinx.coroutines.Job;
import kotlinx.coroutines.flow.FlowCollector;
import kotlinx.coroutines.flow.FlowKt;
import kotlinx.coroutines.flow.MutableStateFlow;
import kotlinx.coroutines.flow.StateFlow;
import kotlinx.coroutines.flow.StateFlowKt;

/* JADX INFO: compiled from: LiveMlNavEngine.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000p\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\t\n\u0000\n\u0002\u0010\u0007\n\u0000\n\u0002\u0010\u0006\n\u0002\b\u0003\n\u0002\u0010\u000b\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\n\n\u0002\u0010\u0002\n\u0002\b\u0006\b\u0007\u0018\u0000 32\u00020\u0001:\u00013B\u001f\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\b\b\u0002\u0010\u0006\u001a\u00020\u0007¢\u0006\u0002\u0010\bJ(\u0010(\u001a\u00020\u00122\u0006\u0010)\u001a\u00020\u00142\u0006\u0010*\u001a\u00020\u00142\u0006\u0010+\u001a\u00020\u00142\u0006\u0010,\u001a\u00020\u0014H\u0002J\b\u0010-\u001a\u00020.H\u0002J\u0010\u0010/\u001a\u00020.2\u0006\u00100\u001a\u00020\u0018H\u0016J\b\u00101\u001a\u00020.H\u0016J\b\u00102\u001a\u00020.H\u0016R\u0014\u0010\t\u001a\b\u0012\u0004\u0012\u00020\u000b0\nX\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\f\u001a\b\u0012\u0004\u0012\u00020\r0\nX\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\u000e\u001a\b\u0012\u0004\u0012\u00020\r0\nX\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u000f\u001a\u00020\u0010X\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u0011\u001a\u00020\u0012X\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0013\u001a\u00020\u0014X\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0015\u001a\u00020\u0014X\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0016\u001a\u00020\u0012X\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u0017\u001a\u00020\u0018X\u0082\u000e¢\u0006\u0002\n\u0000R\u0010\u0010\u0019\u001a\u0004\u0018\u00010\u001aX\u0082\u000e¢\u0006\u0002\n\u0000R\u000e\u0010\u001b\u001a\u00020\u0010X\u0082\u000e¢\u0006\u0002\n\u0000R\u0017\u0010\u001c\u001a\b\u0012\u0004\u0012\u00020\u000b0\u001d¢\u0006\b\n\u0000\u001a\u0004\b\u001e\u0010\u001fR\u000e\u0010 \u001a\u00020!X\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u0004\u001a\u00020\u0005X\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\"\u001a\u00020#X\u0082\u0004¢\u0006\u0002\n\u0000R\u000e\u0010\u0006\u001a\u00020\u0007X\u0082\u0004¢\u0006\u0002\n\u0000R\u001a\u0010$\u001a\b\u0012\u0004\u0012\u00020\r0\u001dX\u0096\u0004¢\u0006\b\n\u0000\u001a\u0004\b%\u0010\u001fR\u0017\u0010&\u001a\b\u0012\u0004\u0012\u00020\r0\u001d¢\u0006\b\n\u0000\u001a\u0004\b'\u0010\u001f¨\u00064"}, d2 = {"Lcom/sih2026/nav/domain/engine/LiveMlNavEngine;", "Lcom/sih2026/nav/domain/engine/NavEngine;", "context", "Landroid/content/Context;", "scope", "Lkotlinx/coroutines/CoroutineScope;", "serverUrl", "", "(Landroid/content/Context;Lkotlinx/coroutines/CoroutineScope;Ljava/lang/String;)V", "_liveStatus", "Lkotlinx/coroutines/flow/MutableStateFlow;", "Lcom/sih2026/nav/domain/engine/LiveMlStatus;", "_state", "Lcom/sih2026/nav/data/model/NavState;", "_trueState", "blackoutStartTimeNs", "", "drHeadingDeg", "", "drLat", "", "drLon", "drSpeedKmh", "inBlackout", "", "job", "Lkotlinx/coroutines/Job;", "lastImuTimeNs", "liveStatus", "Lkotlinx/coroutines/flow/StateFlow;", "getLiveStatus", "()Lkotlinx/coroutines/flow/StateFlow;", "motionClassifier", "Lcom/sih2026/nav/domain/engine/OnDeviceMotionClassifier;", "sensorManager", "Lcom/sih2026/nav/domain/sensor/LiveSensorManager;", "state", "getState", "trueState", "getTrueState", "computeDistanceM", "lat1", "lon1", "lat2", "lon2", "processSensorStep", "", "setGnssBlackout", "enabled", "start", "stop", "Companion", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class LiveMlNavEngine implements NavEngine {
    private final MutableStateFlow<LiveMlStatus> _liveStatus;
    private final MutableStateFlow<NavState> _state;
    private final MutableStateFlow<NavState> _trueState;
    private long blackoutStartTimeNs;
    private final Context context;
    private float drHeadingDeg;
    private double drLat;
    private double drLon;
    private float drSpeedKmh;
    private boolean inBlackout;
    private Job job;
    private long lastImuTimeNs;
    private final StateFlow<LiveMlStatus> liveStatus;
    private final OnDeviceMotionClassifier motionClassifier;
    private final CoroutineScope scope;
    private final LiveSensorManager sensorManager;
    private final String serverUrl;
    private final StateFlow<NavState> state;
    private final StateFlow<NavState> trueState;
    private static final Companion Companion = new Companion(null);
    public static final int $stable = 8;
    private static final NavState INITIAL_STATE = new NavState(52.40384d, -1.50616d, 0.0f, 0.0f, Mode.ACQUIRING, 0.0f, 0);

    /* JADX INFO: compiled from: LiveMlNavEngine.kt */
    @Metadata(d1 = {"\u0000\u0014\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\b\u0082\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002¢\u0006\u0002\u0010\u0002R\u0011\u0010\u0003\u001a\u00020\u0004¢\u0006\b\n\u0000\u001a\u0004\b\u0005\u0010\u0006¨\u0006\u0007"}, d2 = {"Lcom/sih2026/nav/domain/engine/LiveMlNavEngine$Companion;", "", "()V", "INITIAL_STATE", "Lcom/sih2026/nav/data/model/NavState;", "getINITIAL_STATE", "()Lcom/sih2026/nav/data/model/NavState;", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
    private static final class Companion {
        private Companion() {
        }

        public /* synthetic */ Companion(DefaultConstructorMarker defaultConstructorMarker) {
            this();
        }

        public final NavState getINITIAL_STATE() {
            return LiveMlNavEngine.INITIAL_STATE;
        }
    }

    /* JADX INFO: renamed from: com.sih2026.nav.domain.engine.LiveMlNavEngine$start$1, reason: invalid class name */
    /* JADX INFO: compiled from: LiveMlNavEngine.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.domain.engine.LiveMlNavEngine$start$1", f = "LiveMlNavEngine.kt", i = {0}, l = {98}, m = "invokeSuspend", n = {"$this$launch"}, s = {"L$0"})
    static final class AnonymousClass1 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        private /* synthetic */ Object L$0;
        int label;

        /* JADX INFO: renamed from: com.sih2026.nav.domain.engine.LiveMlNavEngine$start$1$1, reason: invalid class name and collision with other inner class name */
        /* JADX INFO: compiled from: LiveMlNavEngine.kt */
        @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
        @DebugMetadata(c = "com.sih2026.nav.domain.engine.LiveMlNavEngine$start$1$1", f = "LiveMlNavEngine.kt", i = {}, l = {72}, m = "invokeSuspend", n = {}, s = {})
        static final class C01661 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
            int label;
            final /* synthetic */ LiveMlNavEngine this$0;

            /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
            C01661(LiveMlNavEngine liveMlNavEngine, Continuation<? super C01661> continuation) {
                super(2, continuation);
                this.this$0 = liveMlNavEngine;
            }

            @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
            public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
                return new C01661(this.this$0, continuation);
            }

            @Override // kotlin.jvm.functions.Function2
            public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
                return ((C01661) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
            }

            @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
            public final Object invokeSuspend(Object obj) {
                Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
                switch (this.label) {
                    case 0:
                        ResultKt.throwOnFailure(obj);
                        StateFlow<GnssFix> latestGnss = this.this$0.sensorManager.getLatestGnss();
                        final LiveMlNavEngine liveMlNavEngine = this.this$0;
                        this.label = 1;
                        if (latestGnss.collect(new FlowCollector() { // from class: com.sih2026.nav.domain.engine.LiveMlNavEngine.start.1.1.1
                            /* JADX WARN: Multi-variable type inference failed */
                            public final Object emit(GnssFix gnssFix, Continuation<? super Unit> continuation) {
                                if (gnssFix == null) {
                                    return Unit.INSTANCE;
                                }
                                liveMlNavEngine._trueState.setValue(new NavState(gnssFix.getLat(), gnssFix.getLon(), gnssFix.getBearingDeg(), gnssFix.getSpeedKmh(), Mode.GNSS_FUSED, gnssFix.getAccuracyM(), gnssFix.getTimestampNs()));
                                if (!liveMlNavEngine.inBlackout) {
                                    liveMlNavEngine.drLat = gnssFix.getLat();
                                    liveMlNavEngine.drLon = gnssFix.getLon();
                                    liveMlNavEngine.drHeadingDeg = gnssFix.getBearingDeg();
                                    liveMlNavEngine.drSpeedKmh = gnssFix.getSpeedKmh();
                                    liveMlNavEngine._state.setValue(liveMlNavEngine._trueState.getValue());
                                    MutableStateFlow mutableStateFlow = liveMlNavEngine._liveStatus;
                                    LiveMlStatus liveMlStatus = (LiveMlStatus) liveMlNavEngine._liveStatus.getValue();
                                    mutableStateFlow.setValue(liveMlStatus.copy((15 & 1) != 0 ? liveMlStatus.isStationary : false, (15 & 2) != 0 ? liveMlStatus.serverConnected : false, (15 & 4) != 0 ? liveMlStatus.sensorActive : false, (15 & 8) != 0 ? liveMlStatus.inBlackout : false, (15 & 16) != 0 ? liveMlStatus.lastFixLat : gnssFix.getLat(), (15 & 32) != 0 ? liveMlStatus.lastFixLon : gnssFix.getLon(), (15 & 64) != 0 ? liveMlStatus.accumulatedDriftM : 0.0f, (15 & 128) != 0 ? liveMlStatus.elapsedBlackoutS : 0.0f));
                                }
                                return Unit.INSTANCE;
                            }

                            @Override // kotlinx.coroutines.flow.FlowCollector
                            public /* bridge */ /* synthetic */ Object emit(Object obj2, Continuation continuation) {
                                return emit((GnssFix) obj2, (Continuation<? super Unit>) continuation);
                            }
                        }, this) == coroutine_suspended) {
                            return coroutine_suspended;
                        }
                        break;
                    case 1:
                        ResultKt.throwOnFailure(obj);
                        break;
                    default:
                        throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
                }
                throw new KotlinNothingValueException();
            }
        }

        AnonymousClass1(Continuation<? super AnonymousClass1> continuation) {
            super(2, continuation);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            AnonymousClass1 anonymousClass1 = LiveMlNavEngine.this.new AnonymousClass1(continuation);
            anonymousClass1.L$0 = obj;
            return anonymousClass1;
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass1) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        /* JADX WARN: Code duplicated, block: B:10:0x0042  */
        /* JADX WARN: Code duplicated, block: B:12:0x0057 A[RETURN] */
        /* JADX WARN: Unsupported multi-entry loop pattern (BACK_EDGE: B:11:0x0055 -> B:13:0x0058). Please report as a decompilation issue!!! */
        /*  JADX ERROR: JadxOverflowException in pass: RegionMakerVisitor
            jadx.core.utils.exceptions.JadxOverflowException: Regions stack size limit reached
            	at jadx.core.utils.ErrorsCounter.addError(ErrorsCounter.java:59)
            	at jadx.core.utils.ErrorsCounter.error(ErrorsCounter.java:31)
            	at jadx.core.dex.attributes.nodes.NotificationAttrNode.addError(NotificationAttrNode.java:19)
            */
        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final java.lang.Object invokeSuspend(java.lang.Object r21) {
            /*
                r20 = this;
                java.lang.Object r0 = kotlin.coroutines.intrinsics.IntrinsicsKt.getCOROUTINE_SUSPENDED()
                r1 = r20
                int r2 = r1.label
                switch(r2) {
                    case 0: goto L1f;
                    case 1: goto L13;
                    default: goto Lb;
                }
            Lb:
                java.lang.IllegalStateException r0 = new java.lang.IllegalStateException
                java.lang.String r2 = "call to 'resume' before 'invoke' with coroutine"
                r0.<init>(r2)
                throw r0
            L13:
                r2 = r20
                r3 = r21
                java.lang.Object r4 = r2.L$0
                kotlinx.coroutines.CoroutineScope r4 = (kotlinx.coroutines.CoroutineScope) r4
                kotlin.ResultKt.throwOnFailure(r3)
                goto L58
            L1f:
                kotlin.ResultKt.throwOnFailure(r21)
                r2 = r20
                r3 = r21
                java.lang.Object r4 = r2.L$0
                kotlinx.coroutines.CoroutineScope r4 = (kotlinx.coroutines.CoroutineScope) r4
                com.sih2026.nav.domain.engine.LiveMlNavEngine$start$1$1 r5 = new com.sih2026.nav.domain.engine.LiveMlNavEngine$start$1$1
                com.sih2026.nav.domain.engine.LiveMlNavEngine r6 = com.sih2026.nav.domain.engine.LiveMlNavEngine.this
                r7 = 0
                r5.<init>(r6, r7)
                r8 = r5
                kotlin.jvm.functions.Function2 r8 = (kotlin.jvm.functions.Function2) r8
                r9 = 3
                r10 = 0
                r6 = 0
                r5 = r4
                kotlinx.coroutines.BuildersKt.launch$default(r5, r6, r7, r8, r9, r10)
            L3c:
                boolean r5 = kotlinx.coroutines.CoroutineScopeKt.isActive(r4)
                if (r5 == 0) goto L9b
                com.sih2026.nav.domain.engine.LiveMlNavEngine r5 = com.sih2026.nav.domain.engine.LiveMlNavEngine.this
                com.sih2026.nav.domain.engine.LiveMlNavEngine.access$processSensorStep(r5)
                r5 = r2
                kotlin.coroutines.Continuation r5 = (kotlin.coroutines.Continuation) r5
                r2.L$0 = r4
                r6 = 1
                r2.label = r6
                r6 = 100
                java.lang.Object r5 = kotlinx.coroutines.DelayKt.delay(r6, r5)
                if (r5 != r0) goto L58
                return r0
            L58:
                com.sih2026.nav.domain.engine.LiveMlNavEngine r5 = com.sih2026.nav.domain.engine.LiveMlNavEngine.this
                kotlinx.coroutines.flow.MutableStateFlow r5 = com.sih2026.nav.domain.engine.LiveMlNavEngine.access$get_liveStatus$p(r5)
                com.sih2026.nav.domain.engine.LiveMlNavEngine r6 = com.sih2026.nav.domain.engine.LiveMlNavEngine.this
                kotlinx.coroutines.flow.MutableStateFlow r6 = com.sih2026.nav.domain.engine.LiveMlNavEngine.access$get_liveStatus$p(r6)
                java.lang.Object r6 = r6.getValue()
                r7 = r6
                com.sih2026.nav.domain.engine.LiveMlStatus r7 = (com.sih2026.nav.domain.engine.LiveMlStatus) r7
                com.sih2026.nav.domain.engine.LiveMlNavEngine r6 = com.sih2026.nav.domain.engine.LiveMlNavEngine.this
                com.sih2026.nav.domain.sensor.LiveSensorManager r6 = com.sih2026.nav.domain.engine.LiveMlNavEngine.access$getSensorManager$p(r6)
                kotlinx.coroutines.flow.StateFlow r6 = r6.isSensorsActive()
                java.lang.Object r6 = r6.getValue()
                java.lang.Boolean r6 = (java.lang.Boolean) r6
                boolean r10 = r6.booleanValue()
                com.sih2026.nav.domain.engine.LiveMlNavEngine r6 = com.sih2026.nav.domain.engine.LiveMlNavEngine.this
                boolean r11 = com.sih2026.nav.domain.engine.LiveMlNavEngine.access$getInBlackout$p(r6)
                r18 = 243(0xf3, float:3.4E-43)
                r19 = 0
                r8 = 0
                r9 = 0
                r12 = 0
                r14 = 0
                r16 = 0
                r17 = 0
                com.sih2026.nav.domain.engine.LiveMlStatus r6 = com.sih2026.nav.domain.engine.LiveMlStatus.copy$default(r7, r8, r9, r10, r11, r12, r14, r16, r17, r18, r19)
                r5.setValue(r6)
                goto L3c
            L9b:
                kotlin.Unit r0 = kotlin.Unit.INSTANCE
                return r0
            */
            throw new UnsupportedOperationException("Method not decompiled: com.sih2026.nav.domain.engine.LiveMlNavEngine.AnonymousClass1.invokeSuspend(java.lang.Object):java.lang.Object");
        }
    }

    public LiveMlNavEngine(Context context, CoroutineScope scope, String serverUrl) {
        Intrinsics.checkNotNullParameter(context, "context");
        Intrinsics.checkNotNullParameter(scope, "scope");
        Intrinsics.checkNotNullParameter(serverUrl, "serverUrl");
        this.context = context;
        this.scope = scope;
        this.serverUrl = serverUrl;
        this.sensorManager = new LiveSensorManager(this.context);
        this.motionClassifier = new OnDeviceMotionClassifier();
        this._state = StateFlowKt.MutableStateFlow(INITIAL_STATE);
        this.state = FlowKt.asStateFlow(this._state);
        this._trueState = StateFlowKt.MutableStateFlow(INITIAL_STATE);
        this.trueState = FlowKt.asStateFlow(this._trueState);
        this._liveStatus = StateFlowKt.MutableStateFlow(new LiveMlStatus(false, false, false, false, 0.0d, 0.0d, 0.0f, 0.0f, 255, null));
        this.liveStatus = FlowKt.asStateFlow(this._liveStatus);
        this.drLat = 52.40384d;
        this.drLon = -1.50616d;
    }

    public /* synthetic */ LiveMlNavEngine(Context context, CoroutineScope coroutineScope, String str, int i, DefaultConstructorMarker defaultConstructorMarker) {
        this(context, coroutineScope, (i & 4) != 0 ? "http://10.0.2.2:8080" : str);
    }

    private final float computeDistanceM(double lat1, double lon1, double lat2, double lon2) {
        double radians = Math.toRadians(lat2 - lat1);
        double radians2 = Math.toRadians(lon2 - lon1);
        double d = 2;
        double dSin = (Math.sin(radians / d) * Math.sin(radians / d)) + (Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) * Math.sin(radians2 / d) * Math.sin(radians2 / d));
        return (float) (6371000.0d * d * Math.atan2(Math.sqrt(dSin), Math.sqrt(((double) 1) - dSin)));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public final void processSensorStep() {
        List<ImuSample> value = this.sensorManager.getWindowStream().getValue();
        if (value.isEmpty()) {
            return;
        }
        long jNanoTime = System.nanoTime();
        float f = this.lastImuTimeNs > 0 ? (jNanoTime - this.lastImuTimeNs) / 1.0E9f : 0.1f;
        this.lastImuTimeNs = jNanoTime;
        boolean zIsStationary = this.motionClassifier.classify(value).isStationary();
        MutableStateFlow<LiveMlStatus> mutableStateFlow = this._liveStatus;
        LiveMlStatus value2 = this._liveStatus.getValue();
        mutableStateFlow.setValue(value2.copy((15 & 1) != 0 ? value2.isStationary : zIsStationary, (15 & 2) != 0 ? value2.serverConnected : false, (15 & 4) != 0 ? value2.sensorActive : false, (15 & 8) != 0 ? value2.inBlackout : false, (15 & 16) != 0 ? value2.lastFixLat : 0.0d, (15 & 32) != 0 ? value2.lastFixLon : 0.0d, (15 & 64) != 0 ? value2.accumulatedDriftM : 0.0f, (15 & 128) != 0 ? value2.elapsedBlackoutS : 0.0f));
        this.drHeadingDeg = ((this.drHeadingDeg + ((float) Math.toDegrees((zIsStationary ? 0.0f : ((ImuSample) CollectionsKt.last((List) value)).getGz()) * f))) + 360.0f) % 360.0f;
        if (zIsStationary) {
            this.drSpeedKmh = 0.0f;
        }
        if (this.inBlackout) {
            float f2 = (this.drSpeedKmh / 3.6f) * f;
            double radians = Math.toRadians(this.drHeadingDeg);
            double dCos = ((double) f2) * Math.cos(radians);
            double dSin = (((double) f2) * Math.sin(radians)) / (Math.cos(Math.toRadians(this.drLat)) * 111139.0d);
            this.drLat += dCos / 111139.0d;
            this.drLon += dSin;
            NavState value3 = this._trueState.getValue();
            float fComputeDistanceM = computeDistanceM(this.drLat, this.drLon, value3.getLat(), value3.getLon());
            float f3 = (jNanoTime - this.blackoutStartTimeNs) / 1.0E9f;
            this._state.setValue(new NavState(this.drLat, this.drLon, this.drHeadingDeg, this.drSpeedKmh, Mode.DEAD_RECKONING, fComputeDistanceM, jNanoTime));
            MutableStateFlow<LiveMlStatus> mutableStateFlow2 = this._liveStatus;
            LiveMlStatus value4 = this._liveStatus.getValue();
            mutableStateFlow2.setValue(value4.copy((15 & 1) != 0 ? value4.isStationary : false, (15 & 2) != 0 ? value4.serverConnected : false, (15 & 4) != 0 ? value4.sensorActive : false, (15 & 8) != 0 ? value4.inBlackout : false, (15 & 16) != 0 ? value4.lastFixLat : 0.0d, (15 & 32) != 0 ? value4.lastFixLon : 0.0d, (15 & 64) != 0 ? value4.accumulatedDriftM : fComputeDistanceM, (15 & 128) != 0 ? value4.elapsedBlackoutS : f3));
        }
    }

    public final StateFlow<LiveMlStatus> getLiveStatus() {
        return this.liveStatus;
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public StateFlow<NavState> getState() {
        return this.state;
    }

    public final StateFlow<NavState> getTrueState() {
        return this.trueState;
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public void setGnssBlackout(boolean enabled) {
        this.inBlackout = enabled;
        if (enabled) {
            this.blackoutStartTimeNs = System.nanoTime();
            return;
        }
        this.blackoutStartTimeNs = 0L;
        MutableStateFlow<LiveMlStatus> mutableStateFlow = this._liveStatus;
        LiveMlStatus value = this._liveStatus.getValue();
        mutableStateFlow.setValue(value.copy((15 & 1) != 0 ? value.isStationary : false, (15 & 2) != 0 ? value.serverConnected : false, (15 & 4) != 0 ? value.sensorActive : false, (15 & 8) != 0 ? value.inBlackout : false, (15 & 16) != 0 ? value.lastFixLat : 0.0d, (15 & 32) != 0 ? value.lastFixLon : 0.0d, (15 & 64) != 0 ? value.accumulatedDriftM : 0.0f, (15 & 128) != 0 ? value.elapsedBlackoutS : 0.0f));
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public void start() {
        Job job = this.job;
        boolean z = false;
        if (job != null && job.isActive()) {
            z = true;
        }
        if (z) {
            return;
        }
        this.sensorManager.start();
        this.job = BuildersKt__Builders_commonKt.launch$default(this.scope, null, null, new AnonymousClass1(null), 3, null);
    }

    @Override // com.sih2026.nav.domain.engine.NavEngine
    public void stop() {
        Job job = this.job;
        if (job != null) {
            Job.DefaultImpls.cancel$default(job, (CancellationException) null, 1, (Object) null);
        }
        this.job = null;
        this.sensorManager.stop();
    }
}
