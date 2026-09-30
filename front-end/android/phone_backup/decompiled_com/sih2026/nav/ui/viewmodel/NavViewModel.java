package com.sih2026.nav.ui.viewmodel;

import android.app.Application;
import androidx.core.app.NotificationCompat;
import androidx.lifecycle.AndroidViewModel;
import androidx.lifecycle.ViewModelKt;
import com.sih2026.nav.data.model.ClipInfo;
import com.sih2026.nav.data.model.EngineMode;
import com.sih2026.nav.data.model.Mode;
import com.sih2026.nav.data.model.NavState;
import com.sih2026.nav.domain.engine.LiveMlNavEngine;
import com.sih2026.nav.domain.engine.LiveMlStatus;
import com.sih2026.nav.domain.engine.NavEngine;
import com.sih2026.nav.domain.engine.ReplayNavEngine;
import com.sih2026.nav.domain.engine.ReplayProgress;
import com.sih2026.nav.ui.utils.HeadingInterpolator;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import kotlin.KotlinNothingValueException;
import kotlin.Lazy;
import kotlin.LazyKt;
import kotlin.Metadata;
import kotlin.ResultKt;
import kotlin.Unit;
import kotlin.collections.CollectionsKt;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.intrinsics.IntrinsicsKt;
import kotlin.coroutines.jvm.internal.DebugMetadata;
import kotlin.coroutines.jvm.internal.SuspendLambda;
import kotlin.io.encoding.Base64;
import kotlin.jvm.functions.Function0;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.internal.Intrinsics;
import kotlinx.coroutines.BuildersKt__Builders_commonKt;
import kotlinx.coroutines.CoroutineScope;
import kotlinx.coroutines.CoroutineScopeKt;
import kotlinx.coroutines.DelayKt;
import kotlinx.coroutines.flow.FlowCollector;
import kotlinx.coroutines.flow.FlowKt;
import kotlinx.coroutines.flow.MutableStateFlow;
import kotlinx.coroutines.flow.StateFlow;
import kotlinx.coroutines.flow.StateFlowKt;
import org.json.JSONException;
import org.osmdroid.util.GeoPoint;

/* JADX INFO: compiled from: NavViewModel.kt */
/* JADX INFO: loaded from: classes5.dex */
@Metadata(d1 = {"\u0000\u0092\u0001\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0010$\n\u0002\b\t\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0005\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0007\n\u0002\u0010\u0007\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\n\n\u0002\u0010\u0002\n\u0002\b\u000e\n\u0002\u0010\u000b\n\u0002\b\u0002\b\u0007\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003¢\u0006\u0002\u0010\u0004J\b\u0010F\u001a\u00020GH\u0002J\b\u0010H\u001a\u00020GH\u0014J\u0006\u0010I\u001a\u00020GJ\u0006\u0010J\u001a\u00020GJ\u0006\u0010K\u001a\u00020GJ\u000e\u0010L\u001a\u00020G2\u0006\u0010M\u001a\u00020\u000fJ\u000e\u0010N\u001a\u00020G2\u0006\u0010O\u001a\u00020\u0011J\u000e\u0010P\u001a\u00020G2\u0006\u0010Q\u001a\u00020\u0007J\u000e\u0010R\u001a\u00020G2\u0006\u0010S\u001a\u000206J\u000e\u0010T\u001a\u00020G2\u0006\u0010U\u001a\u00020VJ\u0006\u0010W\u001a\u00020GR\u0014\u0010\u0005\u001a\b\u0012\u0004\u0012\u00020\u00070\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u001a\u0010\b\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\n0\t0\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\u000b\u001a\b\u0012\u0004\u0012\u00020\f0\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u001a\u0010\r\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\n0\t0\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u0016\u0010\u000e\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\u000f0\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u0016\u0010\u0010\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\u00110\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u001a\u0010\u0012\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\n0\t0\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R\u0014\u0010\u0013\u001a\b\u0012\u0004\u0012\u00020\f0\u0006X\u0082\u0004¢\u0006\u0002\n\u0000R-\u0010\u0014\u001a\u0014\u0012\u0004\u0012\u00020\u0011\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u000f0\t0\u00158FX\u0086\u0084\u0002¢\u0006\f\n\u0004\b\u0018\u0010\u0019\u001a\u0004\b\u0016\u0010\u0017R!\u0010\u001a\u001a\b\u0012\u0004\u0012\u00020\u00110\t8FX\u0086\u0084\u0002¢\u0006\f\n\u0004\b\u001d\u0010\u0019\u001a\u0004\b\u001b\u0010\u001cR\u0017\u0010\u001e\u001a\b\u0012\u0004\u0012\u00020\u00070\u001f¢\u0006\b\n\u0000\u001a\u0004\b \u0010!R\u000e\u0010\"\u001a\u00020#X\u0082\u0004¢\u0006\u0002\n\u0000R\u001d\u0010$\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\n0\t0\u001f¢\u0006\b\n\u0000\u001a\u0004\b%\u0010!R\u0017\u0010&\u001a\b\u0012\u0004\u0012\u00020\f0\u001f¢\u0006\b\n\u0000\u001a\u0004\b'\u0010!R\u000e\u0010(\u001a\u00020)X\u0082\u0004¢\u0006\u0002\n\u0000R\u0017\u0010*\u001a\b\u0012\u0004\u0012\u00020+0\u001f¢\u0006\b\n\u0000\u001a\u0004\b,\u0010!R\u0011\u0010-\u001a\u00020.8F¢\u0006\u0006\u001a\u0004\b/\u00100R\u001d\u00101\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\n0\t0\u001f¢\u0006\b\n\u0000\u001a\u0004\b2\u0010!R\u0017\u00103\u001a\b\u0012\u0004\u0012\u00020\f0\u001f¢\u0006\b\n\u0000\u001a\u0004\b4\u0010!R\u0017\u00105\u001a\b\u0012\u0004\u0012\u0002060\u001f¢\u0006\b\n\u0000\u001a\u0004\b7\u0010!R\u0017\u00108\u001a\b\u0012\u0004\u0012\u0002090\u001f¢\u0006\b\n\u0000\u001a\u0004\b:\u0010!R\u000e\u0010;\u001a\u00020<X\u0082\u0004¢\u0006\u0002\n\u0000R\u0019\u0010=\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\u000f0\u001f¢\u0006\b\n\u0000\u001a\u0004\b>\u0010!R\u0019\u0010?\u001a\n\u0012\u0006\u0012\u0004\u0018\u00010\u00110\u001f¢\u0006\b\n\u0000\u001a\u0004\b@\u0010!R\u001d\u0010A\u001a\u000e\u0012\n\u0012\b\u0012\u0004\u0012\u00020\n0\t0\u001f¢\u0006\b\n\u0000\u001a\u0004\bB\u0010!R\u000e\u0010C\u001a\u00020#X\u0082\u0004¢\u0006\u0002\n\u0000R\u0017\u0010D\u001a\b\u0012\u0004\u0012\u00020\f0\u001f¢\u0006\b\n\u0000\u001a\u0004\bE\u0010!¨\u0006X"}, d2 = {"Lcom/sih2026/nav/ui/viewmodel/NavViewModel;", "Landroidx/lifecycle/AndroidViewModel;", "application", "Landroid/app/Application;", "(Landroid/app/Application;)V", "_engineMode", "Lkotlinx/coroutines/flow/MutableStateFlow;", "Lcom/sih2026/nav/data/model/EngineMode;", "_estimatePath", "", "Lorg/osmdroid/util/GeoPoint;", "_estimateState", "Lcom/sih2026/nav/data/model/NavState;", "_noMapPath", "_selectedClip", "Lcom/sih2026/nav/data/model/ClipInfo;", "_selectedDriver", "", "_truePath", "_truthState", "clipsByDriver", "", "getClipsByDriver", "()Ljava/util/Map;", "clipsByDriver$delegate", "Lkotlin/Lazy;", "drivers", "getDrivers", "()Ljava/util/List;", "drivers$delegate", "engineMode", "Lkotlinx/coroutines/flow/StateFlow;", "getEngineMode", "()Lkotlinx/coroutines/flow/StateFlow;", "estimateInterp", "Lcom/sih2026/nav/ui/utils/HeadingInterpolator;", "estimatePath", "getEstimatePath", "estimateState", "getEstimateState", "liveEngine", "Lcom/sih2026/nav/domain/engine/LiveMlNavEngine;", "liveMlStatus", "Lcom/sih2026/nav/domain/engine/LiveMlStatus;", "getLiveMlStatus", "navEngine", "Lcom/sih2026/nav/domain/engine/NavEngine;", "getNavEngine", "()Lcom/sih2026/nav/domain/engine/NavEngine;", "noMapPath", "getNoMapPath", "noMapState", "getNoMapState", "playbackSpeed", "", "getPlaybackSpeed", NotificationCompat.CATEGORY_PROGRESS, "Lcom/sih2026/nav/domain/engine/ReplayProgress;", "getProgress", "replayEngine", "Lcom/sih2026/nav/domain/engine/ReplayNavEngine;", "selectedClip", "getSelectedClip", "selectedDriver", "getSelectedDriver", "truePath", "getTruePath", "truthInterp", "truthState", "getTruthState", "clearTrails", "", "onCleared", "pause", "play", "restart", "selectClip", "clip", "selectDriver", "driver", "setEngineMode", "mode", "setPlaybackSpeed", "multiplier", "toggleLiveGnssBlackout", "enabled", "", "togglePlay", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class NavViewModel extends AndroidViewModel {
    public static final int $stable = 8;
    private final MutableStateFlow<EngineMode> _engineMode;
    private final MutableStateFlow<List<GeoPoint>> _estimatePath;
    private final MutableStateFlow<NavState> _estimateState;
    private final MutableStateFlow<List<GeoPoint>> _noMapPath;
    private final MutableStateFlow<ClipInfo> _selectedClip;
    private final MutableStateFlow<String> _selectedDriver;
    private final MutableStateFlow<List<GeoPoint>> _truePath;
    private final MutableStateFlow<NavState> _truthState;

    /* JADX INFO: renamed from: clipsByDriver$delegate, reason: from kotlin metadata */
    private final Lazy clipsByDriver;

    /* JADX INFO: renamed from: drivers$delegate, reason: from kotlin metadata */
    private final Lazy drivers;
    private final StateFlow<EngineMode> engineMode;
    private final HeadingInterpolator estimateInterp;
    private final StateFlow<List<GeoPoint>> estimatePath;
    private final StateFlow<NavState> estimateState;
    private final LiveMlNavEngine liveEngine;
    private final StateFlow<LiveMlStatus> liveMlStatus;
    private final StateFlow<List<GeoPoint>> noMapPath;
    private final StateFlow<NavState> noMapState;
    private final StateFlow<Float> playbackSpeed;
    private final StateFlow<ReplayProgress> progress;
    private final ReplayNavEngine replayEngine;
    private final StateFlow<ClipInfo> selectedClip;
    private final StateFlow<String> selectedDriver;
    private final StateFlow<List<GeoPoint>> truePath;
    private final HeadingInterpolator truthInterp;
    private final StateFlow<NavState> truthState;

    /* JADX INFO: renamed from: com.sih2026.nav.ui.viewmodel.NavViewModel$2, reason: invalid class name */
    /* JADX INFO: compiled from: NavViewModel.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.viewmodel.NavViewModel$2", f = "NavViewModel.kt", i = {}, l = {Base64.mimeLineLength}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass2 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        int label;

        AnonymousClass2(Continuation<? super AnonymousClass2> continuation) {
            super(2, continuation);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return NavViewModel.this.new AnonymousClass2(continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass2) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    StateFlow<NavState> state = NavViewModel.this.replayEngine.getState();
                    final NavViewModel navViewModel = NavViewModel.this;
                    this.label = 1;
                    if (state.collect(new FlowCollector() { // from class: com.sih2026.nav.ui.viewmodel.NavViewModel.2.1
                        public final Object emit(NavState navState, Continuation<? super Unit> continuation) {
                            if (navViewModel._engineMode.getValue() == EngineMode.REPLAY) {
                                navViewModel.estimateInterp.updateState(navState);
                                if (navState.getMode() == Mode.DEAD_RECKONING) {
                                    navViewModel._estimatePath.setValue(CollectionsKt.plus((Collection<? extends GeoPoint>) navViewModel._estimatePath.getValue(), new GeoPoint(navState.getLat(), navState.getLon())));
                                    NavState value = navViewModel.replayEngine.getNoMapState().getValue();
                                    navViewModel._noMapPath.setValue(CollectionsKt.plus((Collection<? extends GeoPoint>) navViewModel._noMapPath.getValue(), new GeoPoint(value.getLat(), value.getLon())));
                                }
                            }
                            return Unit.INSTANCE;
                        }

                        @Override // kotlinx.coroutines.flow.FlowCollector
                        public /* bridge */ /* synthetic */ Object emit(Object obj2, Continuation continuation) {
                            return emit((NavState) obj2, (Continuation<? super Unit>) continuation);
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

    /* JADX INFO: renamed from: com.sih2026.nav.ui.viewmodel.NavViewModel$3, reason: invalid class name */
    /* JADX INFO: compiled from: NavViewModel.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.viewmodel.NavViewModel$3", f = "NavViewModel.kt", i = {}, l = {89}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass3 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        int label;

        AnonymousClass3(Continuation<? super AnonymousClass3> continuation) {
            super(2, continuation);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return NavViewModel.this.new AnonymousClass3(continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass3) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    StateFlow<NavState> state = NavViewModel.this.liveEngine.getState();
                    final NavViewModel navViewModel = NavViewModel.this;
                    this.label = 1;
                    if (state.collect(new FlowCollector() { // from class: com.sih2026.nav.ui.viewmodel.NavViewModel.3.1
                        public final Object emit(NavState navState, Continuation<? super Unit> continuation) {
                            if (navViewModel._engineMode.getValue() == EngineMode.LIVE_ML) {
                                navViewModel.estimateInterp.updateState(navState);
                                if (navState.getMode() == Mode.DEAD_RECKONING) {
                                    navViewModel._estimatePath.setValue(CollectionsKt.plus((Collection<? extends GeoPoint>) navViewModel._estimatePath.getValue(), new GeoPoint(navState.getLat(), navState.getLon())));
                                }
                            }
                            return Unit.INSTANCE;
                        }

                        @Override // kotlinx.coroutines.flow.FlowCollector
                        public /* bridge */ /* synthetic */ Object emit(Object obj2, Continuation continuation) {
                            return emit((NavState) obj2, (Continuation<? super Unit>) continuation);
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

    /* JADX INFO: renamed from: com.sih2026.nav.ui.viewmodel.NavViewModel$4, reason: invalid class name */
    /* JADX INFO: compiled from: NavViewModel.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.viewmodel.NavViewModel$4", f = "NavViewModel.kt", i = {}, l = {100}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass4 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        int label;

        AnonymousClass4(Continuation<? super AnonymousClass4> continuation) {
            super(2, continuation);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return NavViewModel.this.new AnonymousClass4(continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass4) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    StateFlow<NavState> trueState = NavViewModel.this.replayEngine.getTrueState();
                    final NavViewModel navViewModel = NavViewModel.this;
                    this.label = 1;
                    if (trueState.collect(new FlowCollector() { // from class: com.sih2026.nav.ui.viewmodel.NavViewModel.4.1
                        public final Object emit(NavState navState, Continuation<? super Unit> continuation) {
                            if (navViewModel._engineMode.getValue() == EngineMode.REPLAY) {
                                navViewModel.truthInterp.updateState(navState);
                                navViewModel._truePath.setValue(CollectionsKt.plus((Collection<? extends GeoPoint>) navViewModel._truePath.getValue(), new GeoPoint(navState.getLat(), navState.getLon())));
                            }
                            return Unit.INSTANCE;
                        }

                        @Override // kotlinx.coroutines.flow.FlowCollector
                        public /* bridge */ /* synthetic */ Object emit(Object obj2, Continuation continuation) {
                            return emit((NavState) obj2, (Continuation<? super Unit>) continuation);
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

    /* JADX INFO: renamed from: com.sih2026.nav.ui.viewmodel.NavViewModel$5, reason: invalid class name */
    /* JADX INFO: compiled from: NavViewModel.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.viewmodel.NavViewModel$5", f = "NavViewModel.kt", i = {}, l = {109}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass5 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        int label;

        AnonymousClass5(Continuation<? super AnonymousClass5> continuation) {
            super(2, continuation);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return NavViewModel.this.new AnonymousClass5(continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass5) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    StateFlow<NavState> trueState = NavViewModel.this.liveEngine.getTrueState();
                    final NavViewModel navViewModel = NavViewModel.this;
                    this.label = 1;
                    if (trueState.collect(new FlowCollector() { // from class: com.sih2026.nav.ui.viewmodel.NavViewModel.5.1
                        public final Object emit(NavState navState, Continuation<? super Unit> continuation) {
                            if (navViewModel._engineMode.getValue() == EngineMode.LIVE_ML) {
                                navViewModel.truthInterp.updateState(navState);
                                navViewModel._truePath.setValue(CollectionsKt.plus((Collection<? extends GeoPoint>) navViewModel._truePath.getValue(), new GeoPoint(navState.getLat(), navState.getLon())));
                            }
                            return Unit.INSTANCE;
                        }

                        @Override // kotlinx.coroutines.flow.FlowCollector
                        public /* bridge */ /* synthetic */ Object emit(Object obj2, Continuation continuation) {
                            return emit((NavState) obj2, (Continuation<? super Unit>) continuation);
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

    /* JADX INFO: renamed from: com.sih2026.nav.ui.viewmodel.NavViewModel$6, reason: invalid class name */
    /* JADX INFO: compiled from: NavViewModel.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.viewmodel.NavViewModel$6", f = "NavViewModel.kt", i = {0}, l = {122}, m = "invokeSuspend", n = {"$this$launch"}, s = {"L$0"})
    static final class AnonymousClass6 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        private /* synthetic */ Object L$0;
        int label;

        AnonymousClass6(Continuation<? super AnonymousClass6> continuation) {
            super(2, continuation);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            AnonymousClass6 anonymousClass6 = NavViewModel.this.new AnonymousClass6(continuation);
            anonymousClass6.L$0 = obj;
            return anonymousClass6;
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass6) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            AnonymousClass6 anonymousClass6;
            CoroutineScope coroutineScope;
            Object coroutine_suspended = IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    anonymousClass6 = this;
                    coroutineScope = (CoroutineScope) anonymousClass6.L$0;
                    break;
                case 1:
                    anonymousClass6 = this;
                    coroutineScope = (CoroutineScope) anonymousClass6.L$0;
                    ResultKt.throwOnFailure(obj);
                    break;
                default:
                    throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
            }
            while (CoroutineScopeKt.isActive(coroutineScope)) {
                NavViewModel.this._estimateState.setValue(HeadingInterpolator.interpolate$default(NavViewModel.this.estimateInterp, 0L, 1, null));
                NavViewModel.this._truthState.setValue(HeadingInterpolator.interpolate$default(NavViewModel.this.truthInterp, 0L, 1, null));
                anonymousClass6.L$0 = coroutineScope;
                anonymousClass6.label = 1;
                if (DelayKt.delay(16L, anonymousClass6) == coroutine_suspended) {
                    return coroutine_suspended;
                }
            }
            return Unit.INSTANCE;
        }
    }

    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
    public NavViewModel(Application application) throws JSONException {
        super(application);
        Intrinsics.checkNotNullParameter(application, "application");
        this.replayEngine = new ReplayNavEngine(application, ViewModelKt.getViewModelScope(this));
        this.liveEngine = new LiveMlNavEngine(application, ViewModelKt.getViewModelScope(this), null, 4, null);
        this._engineMode = StateFlowKt.MutableStateFlow(EngineMode.REPLAY);
        this.engineMode = FlowKt.asStateFlow(this._engineMode);
        this.liveMlStatus = this.liveEngine.getLiveStatus();
        this.clipsByDriver = LazyKt.lazy(new Function0<Map<String, ? extends List<? extends ClipInfo>>>() { // from class: com.sih2026.nav.ui.viewmodel.NavViewModel$clipsByDriver$2
            {
                super(0);
            }

            @Override // kotlin.jvm.functions.Function0
            public final Map<String, ? extends List<? extends ClipInfo>> invoke() {
                Object arrayList;
                List<ClipInfo> clips = this.this$0.replayEngine.getClips();
                LinkedHashMap linkedHashMap = new LinkedHashMap();
                for (Object obj : clips) {
                    String driver = ((ClipInfo) obj).getDriver();
                    Object obj2 = linkedHashMap.get(driver);
                    if (obj2 == null) {
                        arrayList = new ArrayList();
                        linkedHashMap.put(driver, arrayList);
                    } else {
                        arrayList = obj2;
                    }
                    ((List) arrayList).add(obj);
                }
                return linkedHashMap;
            }
        });
        this.drivers = LazyKt.lazy(new Function0<List<? extends String>>() { // from class: com.sih2026.nav.ui.viewmodel.NavViewModel$drivers$2
            {
                super(0);
            }

            @Override // kotlin.jvm.functions.Function0
            public final List<? extends String> invoke() {
                return CollectionsKt.sorted(this.this$0.getClipsByDriver().keySet());
            }
        });
        this._selectedDriver = StateFlowKt.MutableStateFlow(null);
        this.selectedDriver = FlowKt.asStateFlow(this._selectedDriver);
        this._selectedClip = StateFlowKt.MutableStateFlow(null);
        this.selectedClip = FlowKt.asStateFlow(this._selectedClip);
        this.progress = this.replayEngine.getProgress();
        this.playbackSpeed = this.replayEngine.getSpeed();
        this.estimateInterp = new HeadingInterpolator();
        this.truthInterp = new HeadingInterpolator();
        this._estimateState = StateFlowKt.MutableStateFlow(this.replayEngine.getState().getValue());
        this.estimateState = FlowKt.asStateFlow(this._estimateState);
        this._truthState = StateFlowKt.MutableStateFlow(this.replayEngine.getTrueState().getValue());
        this.truthState = FlowKt.asStateFlow(this._truthState);
        this.noMapState = this.replayEngine.getNoMapState();
        this._truePath = StateFlowKt.MutableStateFlow(CollectionsKt.emptyList());
        this.truePath = FlowKt.asStateFlow(this._truePath);
        this._estimatePath = StateFlowKt.MutableStateFlow(CollectionsKt.emptyList());
        this.estimatePath = FlowKt.asStateFlow(this._estimatePath);
        this._noMapPath = StateFlowKt.MutableStateFlow(CollectionsKt.emptyList());
        this.noMapPath = FlowKt.asStateFlow(this._noMapPath);
        String str = (String) CollectionsKt.firstOrNull((List) getDrivers());
        if (str != null) {
            selectDriver(str);
        }
        BuildersKt__Builders_commonKt.launch$default(ViewModelKt.getViewModelScope(this), null, null, new AnonymousClass2(null), 3, null);
        BuildersKt__Builders_commonKt.launch$default(ViewModelKt.getViewModelScope(this), null, null, new AnonymousClass3(null), 3, null);
        BuildersKt__Builders_commonKt.launch$default(ViewModelKt.getViewModelScope(this), null, null, new AnonymousClass4(null), 3, null);
        BuildersKt__Builders_commonKt.launch$default(ViewModelKt.getViewModelScope(this), null, null, new AnonymousClass5(null), 3, null);
        BuildersKt__Builders_commonKt.launch$default(ViewModelKt.getViewModelScope(this), null, null, new AnonymousClass6(null), 3, null);
    }

    private final void clearTrails() {
        this._truePath.setValue(CollectionsKt.emptyList());
        this._estimatePath.setValue(CollectionsKt.emptyList());
        this._noMapPath.setValue(CollectionsKt.emptyList());
    }

    public final Map<String, List<ClipInfo>> getClipsByDriver() {
        return (Map) this.clipsByDriver.getValue();
    }

    public final List<String> getDrivers() {
        return (List) this.drivers.getValue();
    }

    public final StateFlow<EngineMode> getEngineMode() {
        return this.engineMode;
    }

    public final StateFlow<List<GeoPoint>> getEstimatePath() {
        return this.estimatePath;
    }

    public final StateFlow<NavState> getEstimateState() {
        return this.estimateState;
    }

    public final StateFlow<LiveMlStatus> getLiveMlStatus() {
        return this.liveMlStatus;
    }

    public final NavEngine getNavEngine() {
        return this._engineMode.getValue() == EngineMode.REPLAY ? this.replayEngine : this.liveEngine;
    }

    public final StateFlow<List<GeoPoint>> getNoMapPath() {
        return this.noMapPath;
    }

    public final StateFlow<NavState> getNoMapState() {
        return this.noMapState;
    }

    public final StateFlow<Float> getPlaybackSpeed() {
        return this.playbackSpeed;
    }

    public final StateFlow<ReplayProgress> getProgress() {
        return this.progress;
    }

    public final StateFlow<ClipInfo> getSelectedClip() {
        return this.selectedClip;
    }

    public final StateFlow<String> getSelectedDriver() {
        return this.selectedDriver;
    }

    public final StateFlow<List<GeoPoint>> getTruePath() {
        return this.truePath;
    }

    public final StateFlow<NavState> getTruthState() {
        return this.truthState;
    }

    @Override // androidx.lifecycle.ViewModel
    protected void onCleared() {
        super.onCleared();
        this.replayEngine.stop();
        this.liveEngine.stop();
    }

    public final void pause() {
        getNavEngine().stop();
    }

    public final void play() {
        getNavEngine().start();
    }

    public final void restart() {
        clearTrails();
        if (this._engineMode.getValue() == EngineMode.REPLAY) {
            this.replayEngine.restart();
        }
    }

    public final void selectClip(ClipInfo clip) throws JSONException {
        Intrinsics.checkNotNullParameter(clip, "clip");
        clearTrails();
        this._selectedClip.setValue(clip);
        this._selectedDriver.setValue(clip.getDriver());
        this.replayEngine.select(clip.getId());
    }

    public final void selectDriver(String driver) throws JSONException {
        ClipInfo clipInfo;
        Intrinsics.checkNotNullParameter(driver, "driver");
        this._selectedDriver.setValue(driver);
        List<ClipInfo> list = getClipsByDriver().get(driver);
        if (list == null || (clipInfo = (ClipInfo) CollectionsKt.firstOrNull((List) list)) == null) {
            return;
        }
        selectClip(clipInfo);
    }

    public final void setEngineMode(EngineMode mode) {
        Intrinsics.checkNotNullParameter(mode, "mode");
        if (this._engineMode.getValue() == mode) {
            return;
        }
        pause();
        clearTrails();
        this._engineMode.setValue(mode);
        if (mode == EngineMode.LIVE_ML) {
            this.liveEngine.start();
        } else {
            this.liveEngine.stop();
        }
    }

    public final void setPlaybackSpeed(float multiplier) {
        this.replayEngine.setSpeed(multiplier);
    }

    public final void toggleLiveGnssBlackout(boolean enabled) {
        this.liveEngine.setGnssBlackout(enabled);
    }

    public final void togglePlay() {
        if (this._engineMode.getValue() != EngineMode.REPLAY) {
            this.liveEngine.start();
        } else if (this.progress.getValue().getPlaying()) {
            this.replayEngine.stop();
        } else {
            this.replayEngine.start();
        }
    }
}
