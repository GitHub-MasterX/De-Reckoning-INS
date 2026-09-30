package com.sih2026.nav.ui.screens;

import androidx.compose.foundation.layout.BoxKt;
import androidx.compose.foundation.layout.BoxScopeInstance;
import androidx.compose.foundation.layout.SizeKt;
import androidx.compose.runtime.Applier;
import androidx.compose.runtime.ComposablesKt;
import androidx.compose.runtime.Composer;
import androidx.compose.runtime.ComposerKt;
import androidx.compose.runtime.CompositionLocalMap;
import androidx.compose.runtime.MutableState;
import androidx.compose.runtime.RecomposeScopeImplKt;
import androidx.compose.runtime.ScopeUpdateScope;
import androidx.compose.runtime.SkippableUpdater;
import androidx.compose.runtime.SnapshotStateKt;
import androidx.compose.runtime.SnapshotStateKt__SnapshotStateKt;
import androidx.compose.runtime.State;
import androidx.compose.runtime.Updater;
import androidx.compose.ui.Alignment;
import androidx.compose.ui.Modifier;
import androidx.compose.ui.layout.LayoutKt;
import androidx.compose.ui.layout.MeasurePolicy;
import androidx.compose.ui.node.ComposeUiNode;
import androidx.core.app.NotificationCompat;
import com.sih2026.nav.data.model.ClipInfo;
import com.sih2026.nav.data.model.EngineMode;
import com.sih2026.nav.data.model.NavState;
import com.sih2026.nav.domain.engine.LiveMlStatus;
import com.sih2026.nav.domain.engine.ReplayProgress;
import com.sih2026.nav.ui.components.ClipPickerSheetKt;
import com.sih2026.nav.ui.components.MapViewContainerKt;
import com.sih2026.nav.ui.components.TelemetryOverlayKt;
import com.sih2026.nav.ui.viewmodel.NavViewModel;
import java.util.List;
import java.util.Map;
import kotlin.Metadata;
import kotlin.Unit;
import kotlin.jvm.functions.Function0;
import kotlin.jvm.functions.Function1;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.functions.Function3;
import kotlin.jvm.internal.Intrinsics;
import org.json.JSONException;
import org.osmdroid.util.GeoPoint;

/* JADX INFO: compiled from: MainScreen.kt */
/* JADX INFO: loaded from: classes8.dex */
@Metadata(d1 = {"\u0000H\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0007\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u000b\n\u0000\u001a\u0015\u0010\u0000\u001a\u00020\u00012\u0006\u0010\u0002\u001a\u00020\u0003H\u0007¢\u0006\u0002\u0010\u0004¨\u0006\u0005²\u0006\n\u0010\u0006\u001a\u00020\u0007X\u008a\u0084\u0002²\u0006\n\u0010\b\u001a\u00020\tX\u008a\u0084\u0002²\u0006\n\u0010\n\u001a\u00020\u000bX\u008a\u0084\u0002²\u0006\n\u0010\f\u001a\u00020\u000bX\u008a\u0084\u0002²\u0006\n\u0010\r\u001a\u00020\u000eX\u008a\u0084\u0002²\u0006\f\u0010\u000f\u001a\u0004\u0018\u00010\u0010X\u008a\u0084\u0002²\u0006\n\u0010\u0011\u001a\u00020\u0012X\u008a\u0084\u0002²\u0006\u0010\u0010\u0013\u001a\b\u0012\u0004\u0012\u00020\u00150\u0014X\u008a\u0084\u0002²\u0006\u0010\u0010\u0016\u001a\b\u0012\u0004\u0012\u00020\u00150\u0014X\u008a\u0084\u0002²\u0006\u0010\u0010\u0017\u001a\b\u0012\u0004\u0012\u00020\u00150\u0014X\u008a\u0084\u0002²\u0006\n\u0010\u0018\u001a\u00020\u0019X\u008a\u008e\u0002²\u0006\n\u0010\u001a\u001a\u00020\u0019X\u008a\u008e\u0002"}, d2 = {"MainScreen", "", "viewModel", "Lcom/sih2026/nav/ui/viewmodel/NavViewModel;", "(Lcom/sih2026/nav/ui/viewmodel/NavViewModel;Landroidx/compose/runtime/Composer;I)V", "app_debug", "engineMode", "Lcom/sih2026/nav/data/model/EngineMode;", "liveStatus", "Lcom/sih2026/nav/domain/engine/LiveMlStatus;", "estimate", "Lcom/sih2026/nav/data/model/NavState;", "truth", NotificationCompat.CATEGORY_PROGRESS, "Lcom/sih2026/nav/domain/engine/ReplayProgress;", "clip", "Lcom/sih2026/nav/data/model/ClipInfo;", "speed", "", "truePath", "", "Lorg/osmdroid/util/GeoPoint;", "estimatePath", "noMapPath", "showPicker", "", "showNoMap"}, k = 2, mv = {1, 9, 0}, xi = 48)
public final class MainScreenKt {
    public static final void MainScreen(final NavViewModel viewModel, Composer composer, final int i) {
        Function0<ComposeUiNode> function0;
        final MutableState mutableState;
        Object obj;
        Intrinsics.checkNotNullParameter(viewModel, "viewModel");
        Composer composerStartRestartGroup = composer.startRestartGroup(938814776);
        ComposerKt.sourceInformation(composerStartRestartGroup, "C(MainScreen)19@785L16,20@847L16,22@909L16,23@964L16,24@1020L16,25@1076L16,26@1134L16,28@1191L16,29@1255L16,30@1313L16,32@1353L34,33@1409L33,35@1448L1687:MainScreen.kt#bx4x1b");
        if (ComposerKt.isTraceInProgress()) {
            ComposerKt.traceEventStart(938814776, i, -1, "com.sih2026.nav.ui.screens.MainScreen (MainScreen.kt:18)");
        }
        State stateCollectAsState = SnapshotStateKt.collectAsState(viewModel.getEngineMode(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState2 = SnapshotStateKt.collectAsState(viewModel.getLiveMlStatus(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState3 = SnapshotStateKt.collectAsState(viewModel.getEstimateState(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState4 = SnapshotStateKt.collectAsState(viewModel.getTruthState(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState5 = SnapshotStateKt.collectAsState(viewModel.getProgress(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState6 = SnapshotStateKt.collectAsState(viewModel.getSelectedClip(), null, composerStartRestartGroup, 8, 1);
        final State stateCollectAsState7 = SnapshotStateKt.collectAsState(viewModel.getPlaybackSpeed(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState8 = SnapshotStateKt.collectAsState(viewModel.getTruePath(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState9 = SnapshotStateKt.collectAsState(viewModel.getEstimatePath(), null, composerStartRestartGroup, 8, 1);
        State stateCollectAsState10 = SnapshotStateKt.collectAsState(viewModel.getNoMapPath(), null, composerStartRestartGroup, 8, 1);
        composerStartRestartGroup.startReplaceableGroup(-2003797995);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MainScreen.kt#9igjgp");
        Object objRememberedValue = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue == Composer.INSTANCE.getEmpty()) {
            objRememberedValue = SnapshotStateKt__SnapshotStateKt.mutableStateOf$default(false, null, 2, null);
            composerStartRestartGroup.updateRememberedValue(objRememberedValue);
        }
        MutableState mutableState2 = (MutableState) objRememberedValue;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(-2003797939);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MainScreen.kt#9igjgp");
        Object objRememberedValue2 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue2 == Composer.INSTANCE.getEmpty()) {
            objRememberedValue2 = SnapshotStateKt__SnapshotStateKt.mutableStateOf$default(true, null, 2, null);
            composerStartRestartGroup.updateRememberedValue(objRememberedValue2);
        }
        final MutableState mutableState3 = (MutableState) objRememberedValue2;
        composerStartRestartGroup.endReplaceableGroup();
        Modifier modifierFillMaxSize$default = SizeKt.fillMaxSize$default(Modifier.INSTANCE, 0.0f, 1, null);
        composerStartRestartGroup.startReplaceableGroup(733328855);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
        MeasurePolicy measurePolicyRememberBoxMeasurePolicy = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composerStartRestartGroup, ((6 >> 3) & 14) | ((6 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(-1323940314);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
        int currentCompositeKeyHash = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
        CompositionLocalMap currentCompositionLocalMap = composerStartRestartGroup.getCurrentCompositionLocalMap();
        Function0<ComposeUiNode> constructor = ComposeUiNode.INSTANCE.getConstructor();
        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf = LayoutKt.modifierMaterializerOf(modifierFillMaxSize$default);
        int i2 = ((((6 << 3) & 112) << 9) & 7168) | 6;
        if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
            ComposablesKt.invalidApplier();
        }
        composerStartRestartGroup.startReusableNode();
        if (composerStartRestartGroup.getInserting()) {
            function0 = constructor;
            composerStartRestartGroup.createNode(function0);
        } else {
            function0 = constructor;
            composerStartRestartGroup.useNode();
        }
        Composer composerM3273constructorimpl = Updater.m3273constructorimpl(composerStartRestartGroup);
        Updater.m3280setimpl(composerM3273constructorimpl, measurePolicyRememberBoxMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
        Updater.m3280setimpl(composerM3273constructorimpl, currentCompositionLocalMap, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
        if (composerM3273constructorimpl.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl.rememberedValue(), Integer.valueOf(currentCompositeKeyHash))) {
            composerM3273constructorimpl.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash));
            composerM3273constructorimpl.apply(Integer.valueOf(currentCompositeKeyHash), setCompositeKeyHash);
        }
        function3ModifierMaterializerOf.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i2 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(2058660585);
        int i3 = (i2 >> 9) & 14;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
        BoxScopeInstance boxScopeInstance = BoxScopeInstance.INSTANCE;
        int i4 = ((6 >> 6) & 112) | 6;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 1389734086, "C36@1497L388,59@2403L26,61@2535L21,47@1895L718:MainScreen.kt#bx4x1b");
        MapViewContainerKt.MapViewContainer(MainScreen$lambda$2(stateCollectAsState3), MainScreen$lambda$3(stateCollectAsState4), MainScreen$lambda$0(stateCollectAsState) == EngineMode.LIVE_ML ? MainScreen$lambda$1(stateCollectAsState2).getInBlackout() : MainScreen$lambda$4(stateCollectAsState5).getInBlackout(), MainScreen$lambda$7(stateCollectAsState8), MainScreen$lambda$8(stateCollectAsState9), MainScreen$lambda$9(stateCollectAsState10), MainScreen$lambda$14(mutableState3), SizeKt.fillMaxSize$default(Modifier.INSTANCE, 0.0f, 1, null), composerStartRestartGroup, 12881920, 0);
        EngineMode engineModeMainScreen$lambda$0 = MainScreen$lambda$0(stateCollectAsState);
        LiveMlStatus liveMlStatusMainScreen$lambda$1 = MainScreen$lambda$1(stateCollectAsState2);
        ClipInfo clipInfoMainScreen$lambda$5 = MainScreen$lambda$5(stateCollectAsState6);
        ReplayProgress replayProgressMainScreen$lambda$4 = MainScreen$lambda$4(stateCollectAsState5);
        NavState navStateMainScreen$lambda$2 = MainScreen$lambda$2(stateCollectAsState3);
        NavState navStateMainScreen$lambda$3 = MainScreen$lambda$3(stateCollectAsState4);
        float fMainScreen$lambda$6 = MainScreen$lambda$6(stateCollectAsState7);
        boolean zMainScreen$lambda$14 = MainScreen$lambda$14(mutableState3);
        Function0<Unit> function1 = new Function0<Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$1
            {
                super(0);
            }

            @Override // kotlin.jvm.functions.Function0
            public /* bridge */ /* synthetic */ Unit invoke() {
                invoke2();
                return Unit.INSTANCE;
            }

            /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
            public final void invoke2() {
                viewModel.togglePlay();
            }
        };
        Function0<Unit> function2 = new Function0<Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$2
            {
                super(0);
            }

            @Override // kotlin.jvm.functions.Function0
            public /* bridge */ /* synthetic */ Unit invoke() {
                invoke2();
                return Unit.INSTANCE;
            }

            /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
            public final void invoke2() {
                viewModel.restart();
            }
        };
        Function0<Unit> function3 = new Function0<Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$3
            /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
            {
                super(0);
            }

            @Override // kotlin.jvm.functions.Function0
            public /* bridge */ /* synthetic */ Unit invoke() {
                invoke2();
                return Unit.INSTANCE;
            }

            /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
            public final void invoke2() {
                viewModel.setPlaybackSpeed(MainScreenKt.MainScreen$lambda$6(stateCollectAsState7) >= 8.0f ? 1.0f : MainScreenKt.MainScreen$lambda$6(stateCollectAsState7) * 2.0f);
            }
        };
        composerStartRestartGroup.startReplaceableGroup(1389734992);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MainScreen.kt#9igjgp");
        Object objRememberedValue3 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue3 == Composer.INSTANCE.getEmpty()) {
            objRememberedValue3 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$4$1
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                {
                    super(0);
                }

                @Override // kotlin.jvm.functions.Function0
                public /* bridge */ /* synthetic */ Unit invoke() {
                    invoke2();
                    return Unit.INSTANCE;
                }

                /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                public final void invoke2() {
                    MainScreenKt.MainScreen$lambda$15(mutableState3, !MainScreenKt.MainScreen$lambda$14(mutableState3));
                }
            };
            composerStartRestartGroup.updateRememberedValue(objRememberedValue3);
        }
        Function0 function4 = (Function0) objRememberedValue3;
        composerStartRestartGroup.endReplaceableGroup();
        Function1<Boolean, Unit> function5 = new Function1<Boolean, Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$5
            {
                super(1);
            }

            @Override // kotlin.jvm.functions.Function1
            public /* bridge */ /* synthetic */ Unit invoke(Boolean bool) {
                invoke(bool.booleanValue());
                return Unit.INSTANCE;
            }

            public final void invoke(boolean z) {
                viewModel.toggleLiveGnssBlackout(z);
            }
        };
        composerStartRestartGroup.startReplaceableGroup(1389735124);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MainScreen.kt#9igjgp");
        Object objRememberedValue4 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue4 == Composer.INSTANCE.getEmpty()) {
            mutableState = mutableState2;
            objRememberedValue4 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$6$1
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                {
                    super(0);
                }

                @Override // kotlin.jvm.functions.Function0
                public /* bridge */ /* synthetic */ Unit invoke() {
                    invoke2();
                    return Unit.INSTANCE;
                }

                /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                public final void invoke2() {
                    MainScreenKt.MainScreen$lambda$12(mutableState, true);
                }
            };
            composerStartRestartGroup.updateRememberedValue(objRememberedValue4);
        } else {
            mutableState = mutableState2;
        }
        composerStartRestartGroup.endReplaceableGroup();
        TelemetryOverlayKt.TelemetryOverlay(engineModeMainScreen$lambda$0, liveMlStatusMainScreen$lambda$1, clipInfoMainScreen$lambda$5, replayProgressMainScreen$lambda$4, navStateMainScreen$lambda$2, navStateMainScreen$lambda$3, fMainScreen$lambda$6, zMainScreen$lambda$14, function1, function2, function3, function4, function5, (Function0) objRememberedValue4, SizeKt.fillMaxSize$default(Modifier.INSTANCE, 0.0f, 1, null), composerStartRestartGroup, 0, 27696, 0);
        composerStartRestartGroup.startReplaceableGroup(-2003796725);
        ComposerKt.sourceInformation(composerStartRestartGroup, "76@3083L22,66@2653L466");
        if (MainScreen$lambda$11(mutableState)) {
            EngineMode engineModeMainScreen$lambda$1 = MainScreen$lambda$0(stateCollectAsState);
            List<String> drivers = viewModel.getDrivers();
            Map<String, List<ClipInfo>> clipsByDriver = viewModel.getClipsByDriver();
            ClipInfo clipInfoMainScreen$lambda$6 = MainScreen$lambda$5(stateCollectAsState6);
            String id = clipInfoMainScreen$lambda$6 != null ? clipInfoMainScreen$lambda$6.getId() : null;
            Function1<EngineMode, Unit> function6 = new Function1<EngineMode, Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$7
                {
                    super(1);
                }

                @Override // kotlin.jvm.functions.Function1
                public /* bridge */ /* synthetic */ Unit invoke(EngineMode engineMode) {
                    invoke2(engineMode);
                    return Unit.INSTANCE;
                }

                /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                public final void invoke2(EngineMode it) {
                    Intrinsics.checkNotNullParameter(it, "it");
                    viewModel.setEngineMode(it);
                }
            };
            Function1<ClipInfo, Unit> function7 = new Function1<ClipInfo, Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$8
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                {
                    super(1);
                }

                @Override // kotlin.jvm.functions.Function1
                public /* bridge */ /* synthetic */ Unit invoke(ClipInfo clipInfo) throws JSONException {
                    invoke2(clipInfo);
                    return Unit.INSTANCE;
                }

                /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                public final void invoke2(ClipInfo it) throws JSONException {
                    Intrinsics.checkNotNullParameter(it, "it");
                    viewModel.selectClip(it);
                    MainScreenKt.MainScreen$lambda$12(mutableState, false);
                }
            };
            composerStartRestartGroup.startReplaceableGroup(1389735672);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MainScreen.kt#9igjgp");
            Object objRememberedValue5 = composerStartRestartGroup.rememberedValue();
            if (objRememberedValue5 == Composer.INSTANCE.getEmpty()) {
                obj = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt$MainScreen$1$9$1
                    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                    {
                        super(0);
                    }

                    @Override // kotlin.jvm.functions.Function0
                    public /* bridge */ /* synthetic */ Unit invoke() {
                        invoke2();
                        return Unit.INSTANCE;
                    }

                    /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                    public final void invoke2() {
                        MainScreenKt.MainScreen$lambda$12(mutableState, false);
                    }
                };
                composerStartRestartGroup.updateRememberedValue(obj);
            } else {
                obj = objRememberedValue5;
            }
            composerStartRestartGroup.endReplaceableGroup();
            ClipPickerSheetKt.ClipPickerSheet(engineModeMainScreen$lambda$1, drivers, clipsByDriver, id, function6, function7, (Function0) obj, composerStartRestartGroup, 1573440);
        }
        composerStartRestartGroup.endReplaceableGroup();
        ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
        ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.endNode();
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.endReplaceableGroup();
        if (ComposerKt.isTraceInProgress()) {
            ComposerKt.traceEventEnd();
        }
        ScopeUpdateScope scopeUpdateScopeEndRestartGroup = composerStartRestartGroup.endRestartGroup();
        if (scopeUpdateScopeEndRestartGroup != null) {
            scopeUpdateScopeEndRestartGroup.updateScope(new Function2<Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.screens.MainScreenKt.MainScreen.2
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                {
                    super(2);
                }

                @Override // kotlin.jvm.functions.Function2
                public /* bridge */ /* synthetic */ Unit invoke(Composer composer2, Integer num) {
                    invoke(composer2, num.intValue());
                    return Unit.INSTANCE;
                }

                public final void invoke(Composer composer2, int i5) {
                    MainScreenKt.MainScreen(viewModel, composer2, RecomposeScopeImplKt.updateChangedFlags(i | 1));
                }
            });
        }
    }

    private static final EngineMode MainScreen$lambda$0(State<? extends EngineMode> state) {
        return state.getValue();
    }

    private static final LiveMlStatus MainScreen$lambda$1(State<LiveMlStatus> state) {
        return state.getValue();
    }

    private static final boolean MainScreen$lambda$11(MutableState<Boolean> mutableState) {
        return mutableState.getValue().booleanValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final void MainScreen$lambda$12(MutableState<Boolean> mutableState, boolean z) {
        mutableState.setValue(Boolean.valueOf(z));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final boolean MainScreen$lambda$14(MutableState<Boolean> mutableState) {
        return mutableState.getValue().booleanValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final void MainScreen$lambda$15(MutableState<Boolean> mutableState, boolean z) {
        mutableState.setValue(Boolean.valueOf(z));
    }

    private static final NavState MainScreen$lambda$2(State<NavState> state) {
        return state.getValue();
    }

    private static final NavState MainScreen$lambda$3(State<NavState> state) {
        return state.getValue();
    }

    private static final ReplayProgress MainScreen$lambda$4(State<ReplayProgress> state) {
        return state.getValue();
    }

    private static final ClipInfo MainScreen$lambda$5(State<ClipInfo> state) {
        return state.getValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final float MainScreen$lambda$6(State<Float> state) {
        return state.getValue().floatValue();
    }

    private static final List<GeoPoint> MainScreen$lambda$7(State<? extends List<? extends GeoPoint>> state) {
        return (List) state.getValue();
    }

    private static final List<GeoPoint> MainScreen$lambda$8(State<? extends List<? extends GeoPoint>> state) {
        return (List) state.getValue();
    }

    private static final List<GeoPoint> MainScreen$lambda$9(State<? extends List<? extends GeoPoint>> state) {
        return (List) state.getValue();
    }
}
