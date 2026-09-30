package com.sih2026.nav.ui.components;

import androidx.compose.animation.core.AnimationConstants;
import androidx.compose.foundation.BackgroundKt;
import androidx.compose.foundation.BorderKt;
import androidx.compose.foundation.ClickableKt;
import androidx.compose.foundation.layout.Arrangement;
import androidx.compose.foundation.layout.BoxKt;
import androidx.compose.foundation.layout.BoxScopeInstance;
import androidx.compose.foundation.layout.ColumnKt;
import androidx.compose.foundation.layout.ColumnScope;
import androidx.compose.foundation.layout.ColumnScopeInstance;
import androidx.compose.foundation.layout.PaddingKt;
import androidx.compose.foundation.layout.RowKt;
import androidx.compose.foundation.layout.RowScope;
import androidx.compose.foundation.layout.RowScopeInstance;
import androidx.compose.foundation.layout.SizeKt;
import androidx.compose.foundation.layout.SpacerKt;
import androidx.compose.foundation.lazy.LazyDslKt;
import androidx.compose.foundation.lazy.LazyItemScope;
import androidx.compose.foundation.lazy.LazyListScope;
import androidx.compose.foundation.shape.RoundedCornerShapeKt;
import androidx.compose.material3.ModalBottomSheet_androidKt;
import androidx.compose.material3.SheetState;
import androidx.compose.material3.TextKt;
import androidx.compose.runtime.Applier;
import androidx.compose.runtime.ComposablesKt;
import androidx.compose.runtime.Composer;
import androidx.compose.runtime.ComposerKt;
import androidx.compose.runtime.CompositionLocalMap;
import androidx.compose.runtime.MutableState;
import androidx.compose.runtime.RecomposeScopeImplKt;
import androidx.compose.runtime.ScopeUpdateScope;
import androidx.compose.runtime.SkippableUpdater;
import androidx.compose.runtime.SnapshotStateKt__SnapshotStateKt;
import androidx.compose.runtime.Updater;
import androidx.compose.runtime.internal.ComposableLambdaKt;
import androidx.compose.ui.Alignment;
import androidx.compose.ui.Modifier;
import androidx.compose.ui.draw.ClipKt;
import androidx.compose.ui.graphics.Color;
import androidx.compose.ui.layout.LayoutKt;
import androidx.compose.ui.layout.MeasurePolicy;
import androidx.compose.ui.node.ComposeUiNode;
import androidx.compose.ui.text.TextLayoutResult;
import androidx.compose.ui.text.TextStyle;
import androidx.compose.ui.text.font.FontFamily;
import androidx.compose.ui.text.font.FontStyle;
import androidx.compose.ui.text.font.FontWeight;
import androidx.compose.ui.text.font.GenericFontFamily;
import androidx.compose.ui.text.style.TextAlign;
import androidx.compose.ui.text.style.TextDecoration;
import androidx.compose.ui.unit.Dp;
import androidx.compose.ui.unit.TextUnitKt;
import com.sih2026.nav.data.model.ClipInfo;
import com.sih2026.nav.data.model.EngineMode;
import com.sih2026.nav.ui.theme.ColorKt;
import java.util.Arrays;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import kotlin.Metadata;
import kotlin.Unit;
import kotlin.collections.CollectionsKt;
import kotlin.jvm.functions.Function0;
import kotlin.jvm.functions.Function1;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.functions.Function3;
import kotlin.jvm.functions.Function4;
import kotlin.jvm.internal.Intrinsics;
import kotlin.jvm.internal.StringCompanionObject;

/* JADX INFO: compiled from: ClipPickerSheet.kt */
/* JADX INFO: loaded from: classes7.dex */
@Metadata(d1 = {"\u0000D\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0010\u000e\n\u0000\n\u0002\u0010$\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0010\u000b\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0003\u001a}\u0010\u0000\u001a\u00020\u00012\u0006\u0010\u0002\u001a\u00020\u00032\f\u0010\u0004\u001a\b\u0012\u0004\u0012\u00020\u00060\u00052\u0018\u0010\u0007\u001a\u0014\u0012\u0004\u0012\u00020\u0006\u0012\n\u0012\b\u0012\u0004\u0012\u00020\t0\u00050\b2\b\u0010\n\u001a\u0004\u0018\u00010\u00062\u0012\u0010\u000b\u001a\u000e\u0012\u0004\u0012\u00020\u0003\u0012\u0004\u0012\u00020\u00010\f2\u0012\u0010\r\u001a\u000e\u0012\u0004\u0012\u00020\t\u0012\u0004\u0012\u00020\u00010\f2\f\u0010\u000e\u001a\b\u0012\u0004\u0012\u00020\u00010\u000fH\u0007¢\u0006\u0002\u0010\u0010\u001a1\u0010\u0011\u001a\u00020\u00012\u0006\u0010\u0012\u001a\u00020\t2\u0006\u0010\u0013\u001a\u00020\u00142\u0012\u0010\r\u001a\u000e\u0012\u0004\u0012\u00020\t\u0012\u0004\u0012\u00020\u00010\fH\u0003¢\u0006\u0002\u0010\u0015\u001a5\u0010\u0016\u001a\u00020\u00012\u0006\u0010\u0017\u001a\u00020\u00032\u0006\u0010\u0013\u001a\u00020\u00142\f\u0010\r\u001a\b\u0012\u0004\u0012\u00020\u00010\u000f2\b\b\u0002\u0010\u0018\u001a\u00020\u0019H\u0003¢\u0006\u0002\u0010\u001a¨\u0006\u001b²\u0006\f\u0010\u001c\u001a\u0004\u0018\u00010\u0006X\u008a\u008e\u0002"}, d2 = {"ClipPickerSheet", "", "engineMode", "Lcom/sih2026/nav/data/model/EngineMode;", "drivers", "", "", "clipsByDriver", "", "Lcom/sih2026/nav/data/model/ClipInfo;", "selectedClipId", "onSetEngineMode", "Lkotlin/Function1;", "onSelect", "onDismiss", "Lkotlin/Function0;", "(Lcom/sih2026/nav/data/model/EngineMode;Ljava/util/List;Ljava/util/Map;Ljava/lang/String;Lkotlin/jvm/functions/Function1;Lkotlin/jvm/functions/Function1;Lkotlin/jvm/functions/Function0;Landroidx/compose/runtime/Composer;I)V", "ClipRow", "clip", "selected", "", "(Lcom/sih2026/nav/data/model/ClipInfo;ZLkotlin/jvm/functions/Function1;Landroidx/compose/runtime/Composer;I)V", "EngineModeTab", "mode", "modifier", "Landroidx/compose/ui/Modifier;", "(Lcom/sih2026/nav/data/model/EngineMode;ZLkotlin/jvm/functions/Function0;Landroidx/compose/ui/Modifier;Landroidx/compose/runtime/Composer;II)V", "app_debug", "driver"}, k = 2, mv = {1, 9, 0}, xi = 48)
public final class ClipPickerSheetKt {
    public static final void ClipPickerSheet(final EngineMode engineMode, final List<String> drivers, final Map<String, ? extends List<ClipInfo>> clipsByDriver, final String str, final Function1<? super EngineMode, Unit> onSetEngineMode, final Function1<? super ClipInfo, Unit> onSelect, final Function0<Unit> onDismiss, Composer composer, final int i) {
        Object next;
        Object objMutableStateOf$default;
        boolean z;
        boolean z2;
        Intrinsics.checkNotNullParameter(engineMode, "engineMode");
        Intrinsics.checkNotNullParameter(drivers, "drivers");
        Intrinsics.checkNotNullParameter(clipsByDriver, "clipsByDriver");
        Intrinsics.checkNotNullParameter(onSetEngineMode, "onSetEngineMode");
        Intrinsics.checkNotNullParameter(onSelect, "onSelect");
        Intrinsics.checkNotNullParameter(onDismiss, "onDismiss");
        Composer composerStartRestartGroup = composer.startRestartGroup(779683152);
        ComposerKt.sourceInformation(composerStartRestartGroup, "C(ClipPickerSheet)P(2,1!1,6,5,4)58@2365L59,61@2581L36,63@2623L5262:ClipPickerSheet.kt#wl24de");
        if (ComposerKt.isTraceInProgress()) {
            ComposerKt.traceEventStart(779683152, i, -1, "com.sih2026.nav.ui.components.ClipPickerSheet (ClipPickerSheet.kt:57)");
        }
        SheetState sheetStateRememberModalBottomSheetState = ModalBottomSheet_androidKt.rememberModalBottomSheetState(true, null, composerStartRestartGroup, 6, 2);
        Iterator<T> it = drivers.iterator();
        do {
            if (!it.hasNext()) {
                next = null;
                break;
            }
            next = it.next();
            List<ClipInfo> list = clipsByDriver.get((String) next);
            if (list != null) {
                List<ClipInfo> list2 = list;
                if (!(list2 instanceof Collection) || !list2.isEmpty()) {
                    Iterator<T> it2 = list2.iterator();
                    while (true) {
                        if (!it2.hasNext()) {
                            z2 = false;
                            break;
                        } else if (Intrinsics.areEqual(((ClipInfo) it2.next()).getId(), str)) {
                            z2 = true;
                            break;
                        }
                    }
                } else {
                    z2 = false;
                }
                z = z2;
            }
        } while (!z);
        String str2 = (String) next;
        if (str2 == null) {
            str2 = (String) CollectionsKt.firstOrNull((List) drivers);
        }
        String str3 = str2;
        composerStartRestartGroup.startReplaceableGroup(-1588391452);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):ClipPickerSheet.kt#9igjgp");
        Object objRememberedValue = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue == Composer.INSTANCE.getEmpty()) {
            objMutableStateOf$default = SnapshotStateKt__SnapshotStateKt.mutableStateOf$default(str3, null, 2, null);
            composerStartRestartGroup.updateRememberedValue(objMutableStateOf$default);
        } else {
            objMutableStateOf$default = objRememberedValue;
        }
        final MutableState mutableState = (MutableState) objMutableStateOf$default;
        composerStartRestartGroup.endReplaceableGroup();
        ModalBottomSheet_androidKt.m2008ModalBottomSheetdYc4hso(onDismiss, null, sheetStateRememberModalBottomSheetState, 0.0f, null, ColorKt.getSurfaceDark(), 0L, Dp.m6091constructorimpl(16), 0L, null, null, null, ComposableLambdaKt.composableLambda(composerStartRestartGroup, 1036967021, true, new Function3<ColumnScope, Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt.ClipPickerSheet.1
            /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
            /* JADX WARN: Multi-variable type inference failed */
            {
                super(3);
            }

            @Override // kotlin.jvm.functions.Function3
            public /* bridge */ /* synthetic */ Unit invoke(ColumnScope columnScope, Composer composer2, Integer num) {
                invoke(columnScope, composer2, num.intValue());
                return Unit.INSTANCE;
            }

            /* JADX WARN: Code duplicated, block: B:102:0x06db  */
            /* JADX WARN: Code duplicated, block: B:105:0x0778  */
            /* JADX WARN: Code duplicated, block: B:108:0x0784  */
            /* JADX WARN: Code duplicated, block: B:109:0x078a  */
            /* JADX WARN: Code duplicated, block: B:120:0x08a9  */
            /* JADX WARN: Code duplicated, block: B:123:0x08b5  */
            /* JADX WARN: Code duplicated, block: B:124:0x08bb  */
            /* JADX WARN: Code duplicated, block: B:135:0x0991  */
            /* JADX WARN: Code duplicated, block: B:136:0x0998  */
            /* JADX WARN: Code duplicated, block: B:139:0x09d3  */
            /* JADX WARN: Code duplicated, block: B:140:0x09da  */
            /* JADX WARN: Code duplicated, block: B:143:0x0ada  */
            /* JADX WARN: Code duplicated, block: B:145:0x0b76  */
            /* JADX WARN: Code duplicated, block: B:148:0x0b82  */
            /* JADX WARN: Code duplicated, block: B:149:0x0b86  */
            /* JADX WARN: Code duplicated, block: B:160:0x0c9f  */
            /* JADX WARN: Code duplicated, block: B:163:0x0cab  */
            /* JADX WARN: Code duplicated, block: B:164:0x0cb1  */
            /* JADX WARN: Code duplicated, block: B:176:0x0e50  */
            /* JADX WARN: Code duplicated, block: B:182:? A[RETURN, SYNTHETIC] */
            /* JADX WARN: Code duplicated, block: B:55:0x03eb  */
            /* JADX WARN: Code duplicated, block: B:56:0x03ee  */
            /* JADX WARN: Code duplicated, block: B:67:0x047b  */
            /* JADX WARN: Code duplicated, block: B:69:0x054f  */
            /* JADX WARN: Code duplicated, block: B:72:0x055b  */
            /* JADX WARN: Code duplicated, block: B:73:0x0561  */
            /* JADX WARN: Code duplicated, block: B:85:0x0629  */
            /* JADX WARN: Code duplicated, block: B:91:0x0655  */
            /* JADX WARN: Code duplicated, block: B:94:0x067a  */
            /* JADX WARN: Code duplicated, block: B:95:0x067f  */
            public final void invoke(ColumnScope ModalBottomSheet, Composer composer2, int i2) {
                Function0<ComposeUiNode> function0;
                Function0<ComposeUiNode> function1;
                String str4;
                Object obj;
                boolean z3;
                boolean zChanged;
                Object obj2;
                int currentCompositeKeyHash;
                Function0<ComposeUiNode> constructor;
                Composer composerM3273constructorimpl;
                int currentCompositeKeyHash2;
                Function0<ComposeUiNode> constructor2;
                Function0<ComposeUiNode> function2;
                Composer composerM3273constructorimpl2;
                int i3;
                boolean z4;
                int currentCompositeKeyHash3;
                CompositionLocalMap currentCompositionLocalMap;
                Function0<ComposeUiNode> constructor3;
                Function0<ComposeUiNode> function3;
                Composer composerM3273constructorimpl3;
                Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function4;
                boolean z5;
                List<String> list3;
                boolean z6;
                Iterator it3;
                final String str5;
                boolean zAreEqual;
                List<ClipInfo> list4;
                String role;
                long surfaceCard;
                boolean zChanged2;
                Object obj3;
                int currentCompositeKeyHash4;
                Function0<ComposeUiNode> constructor4;
                Function0<ComposeUiNode> function5;
                Composer composerM3273constructorimpl4;
                int currentCompositeKeyHash5;
                Function0<ComposeUiNode> constructor5;
                Function0<ComposeUiNode> function6;
                Composer composerM3273constructorimpl5;
                long textPrimary;
                long textMuted;
                ClipInfo clipInfo;
                Intrinsics.checkNotNullParameter(ModalBottomSheet, "$this$ModalBottomSheet");
                ComposerKt.sourceInformation(composer2, "C69@2797L5082:ClipPickerSheet.kt#wl24de");
                if ((i2 & 81) == 16 && composer2.getSkipping()) {
                    composer2.skipToGroupEnd();
                    return;
                }
                if (ComposerKt.isTraceInProgress()) {
                    ComposerKt.traceEventStart(1036967021, i2, -1, "com.sih2026.nav.ui.components.ClipPickerSheet.<anonymous> (ClipPickerSheet.kt:69)");
                }
                Modifier modifierM560paddingVpY3zN4 = PaddingKt.m560paddingVpY3zN4(SizeKt.fillMaxWidth$default(Modifier.INSTANCE, 0.0f, 1, null), Dp.m6091constructorimpl(20), Dp.m6091constructorimpl(8));
                EngineMode engineMode2 = engineMode;
                final Function1<EngineMode, Unit> function7 = onSetEngineMode;
                List<String> list5 = drivers;
                final Map<String, List<ClipInfo>> map = clipsByDriver;
                final MutableState<String> mutableState2 = mutableState;
                final String str6 = str;
                final Function1<ClipInfo, Unit> function8 = onSelect;
                composer2.startReplaceableGroup(-483455358);
                String str7 = "CC(Column)P(2,3,1)77@3865L61,78@3931L133:Column.kt#2w3rfo";
                ComposerKt.sourceInformation(composer2, "CC(Column)P(2,3,1)77@3865L61,78@3931L133:Column.kt#2w3rfo");
                MeasurePolicy measurePolicyColumnMeasurePolicy = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), Alignment.INSTANCE.getStart(), composer2, ((6 >> 3) & 14) | ((6 >> 3) & 112));
                composer2.startReplaceableGroup(-1323940314);
                ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                int currentCompositeKeyHash6 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                CompositionLocalMap currentCompositionLocalMap2 = composer2.getCurrentCompositionLocalMap();
                Function0<ComposeUiNode> constructor6 = ComposeUiNode.INSTANCE.getConstructor();
                Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf = LayoutKt.modifierMaterializerOf(modifierM560paddingVpY3zN4);
                int i4 = ((((6 << 3) & 112) << 9) & 7168) | 6;
                if (!(composer2.getApplier() instanceof Applier)) {
                    ComposablesKt.invalidApplier();
                }
                composer2.startReusableNode();
                if (composer2.getInserting()) {
                    function0 = constructor6;
                    composer2.createNode(function0);
                } else {
                    function0 = constructor6;
                    composer2.useNode();
                }
                Composer composerM3273constructorimpl6 = Updater.m3273constructorimpl(composer2);
                Updater.m3280setimpl(composerM3273constructorimpl6, measurePolicyColumnMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                Updater.m3280setimpl(composerM3273constructorimpl6, currentCompositionLocalMap2, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                if (composerM3273constructorimpl6.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl6.rememberedValue(), Integer.valueOf(currentCompositeKeyHash6))) {
                    composerM3273constructorimpl6.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash6));
                    composerM3273constructorimpl6.apply(Integer.valueOf(currentCompositeKeyHash6), setCompositeKeyHash);
                }
                function3ModifierMaterializerOf.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i4 >> 3) & 112));
                composer2.startReplaceableGroup(2058660585);
                int i5 = (i4 >> 9) & 14;
                ComposerKt.sourceInformationMarkerStart(composer2, 276693656, "C79@3979L9:Column.kt#2w3rfo");
                ColumnScopeInstance columnScopeInstance = ColumnScopeInstance.INSTANCE;
                int i6 = ((6 >> 6) & 112) | 6;
                ComposerKt.sourceInformationMarkerStart(composer2, 1239101669, "C71@2900L242,78@3155L40,79@3208L208,85@3430L41,88@3519L719,106@4252L41,184@7828L41:ClipPickerSheet.kt#wl24de");
                TextKt.m2461Text4IGK_g("ENGINE & DATASET CONFIGURATION", (Modifier) null, ColorKt.getCyanAccent(), TextUnitKt.getSp(14), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 200070, 0, 130962);
                SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(4)), composer2, 6);
                TextKt.m2461Text4IGK_g("Switch between live real-time ML sensor navigation and offline dataset evaluation replays.", (Modifier) null, ColorKt.getTextSecondary(), TextUnitKt.getSp(12), (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 3462, 0, 131058);
                SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(14)), composer2, 6);
                Modifier modifierFillMaxWidth$default = SizeKt.fillMaxWidth$default(Modifier.INSTANCE, 0.0f, 1, null);
                Arrangement.HorizontalOrVertical horizontalOrVerticalM468spacedBy0680j_4 = Arrangement.INSTANCE.m468spacedBy0680j_4(Dp.m6091constructorimpl(10));
                composer2.startReplaceableGroup(693286680);
                ComposerKt.sourceInformation(composer2, "CC(Row)P(2,1,3)90@4553L58,91@4616L130:Row.kt#2w3rfo");
                MeasurePolicy measurePolicyRowMeasurePolicy = RowKt.rowMeasurePolicy(horizontalOrVerticalM468spacedBy0680j_4, Alignment.INSTANCE.getTop(), composer2, ((54 >> 3) & 14) | ((54 >> 3) & 112));
                composer2.startReplaceableGroup(-1323940314);
                ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                int currentCompositeKeyHash7 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                CompositionLocalMap currentCompositionLocalMap3 = composer2.getCurrentCompositionLocalMap();
                Function0<ComposeUiNode> constructor7 = ComposeUiNode.INSTANCE.getConstructor();
                Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf2 = LayoutKt.modifierMaterializerOf(modifierFillMaxWidth$default);
                int i7 = ((((54 << 3) & 112) << 9) & 7168) | 6;
                if (!(composer2.getApplier() instanceof Applier)) {
                    ComposablesKt.invalidApplier();
                }
                composer2.startReusableNode();
                if (composer2.getInserting()) {
                    function1 = constructor7;
                    composer2.createNode(function1);
                } else {
                    function1 = constructor7;
                    composer2.useNode();
                }
                Composer composerM3273constructorimpl7 = Updater.m3273constructorimpl(composer2);
                Updater.m3280setimpl(composerM3273constructorimpl7, measurePolicyRowMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                Updater.m3280setimpl(composerM3273constructorimpl7, currentCompositionLocalMap3, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash2 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                if (composerM3273constructorimpl7.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl7.rememberedValue(), Integer.valueOf(currentCompositeKeyHash7))) {
                    composerM3273constructorimpl7.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash7));
                    composerM3273constructorimpl7.apply(Integer.valueOf(currentCompositeKeyHash7), setCompositeKeyHash2);
                }
                function3ModifierMaterializerOf2.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i7 >> 3) & 112));
                composer2.startReplaceableGroup(2058660585);
                int i8 = (i7 >> 9) & 14;
                ComposerKt.sourceInformationMarkerStart(composer2, -326681643, "C92@4661L9:Row.kt#2w3rfo");
                int i9 = ((54 >> 6) & 112) | 6;
                RowScopeInstance rowScopeInstance = RowScopeInstance.INSTANCE;
                ComposerKt.sourceInformationMarkerStart(composer2, 444163214, "C95@3832L38,92@3676L264,101@4115L39,98@3957L267:ClipPickerSheet.kt#wl24de");
                EngineMode engineMode3 = EngineMode.REPLAY;
                boolean z7 = engineMode2 == EngineMode.REPLAY;
                composer2.startReplaceableGroup(444163370);
                String str8 = "CC(remember):ClipPickerSheet.kt#9igjgp";
                ComposerKt.sourceInformation(composer2, "CC(remember):ClipPickerSheet.kt#9igjgp");
                boolean zChanged3 = composer2.changed(function7);
                Object objRememberedValue2 = composer2.rememberedValue();
                if (!zChanged3) {
                    str4 = "C79@3979L9:Column.kt#2w3rfo";
                    if (objRememberedValue2 != Composer.INSTANCE.getEmpty()) {
                        obj = objRememberedValue2;
                    }
                    composer2.endReplaceableGroup();
                    ClipPickerSheetKt.EngineModeTab(engineMode3, z7, (Function0) obj, RowScope.weight$default(rowScopeInstance, Modifier.INSTANCE, 1.0f, false, 2, null), composer2, 6, 0);
                    EngineMode engineMode4 = EngineMode.LIVE_ML;
                    if (engineMode2 == EngineMode.LIVE_ML) {
                        z3 = true;
                    } else {
                        z3 = false;
                    }
                    composer2.startReplaceableGroup(444163653);
                    ComposerKt.sourceInformation(composer2, "CC(remember):ClipPickerSheet.kt#9igjgp");
                    zChanged = composer2.changed(function7);
                    Object objRememberedValue3 = composer2.rememberedValue();
                    if (!zChanged || objRememberedValue3 == Composer.INSTANCE.getEmpty()) {
                        obj2 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$1$2$1
                            /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                            /* JADX WARN: Multi-variable type inference failed */
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
                                function7.invoke(EngineMode.LIVE_ML);
                            }
                        };
                        composer2.updateRememberedValue(obj2);
                    } else {
                        obj2 = objRememberedValue3;
                    }
                    composer2.endReplaceableGroup();
                    ClipPickerSheetKt.EngineModeTab(engineMode4, z3, (Function0) obj2, RowScope.weight$default(rowScopeInstance, Modifier.INSTANCE, 1.0f, false, 2, null), composer2, 6, 0);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    composer2.endReplaceableGroup();
                    composer2.endNode();
                    composer2.endReplaceableGroup();
                    composer2.endReplaceableGroup();
                    SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(16)), composer2, 6);
                    if (engineMode2 == EngineMode.REPLAY) {
                        composer2.startReplaceableGroup(1239103131);
                        ComposerKt.sourceInformation(composer2, "109@4362L256,116@4635L40,118@4693L1566,148@6277L41,150@6336L377");
                        TextKt.m2461Text4IGK_g("SELECT DATASET DRIVER", (Modifier) null, ColorKt.getTextMuted(), TextUnitKt.getSp(11), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 200070, 0, 130962);
                        SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(8)), composer2, 6);
                        Arrangement.HorizontalOrVertical horizontalOrVerticalM468spacedBy0680j_5 = Arrangement.INSTANCE.m468spacedBy0680j_4(Dp.m6091constructorimpl(8));
                        composer2.startReplaceableGroup(693286680);
                        ComposerKt.sourceInformation(composer2, "CC(Row)P(2,1,3)90@4553L58,91@4616L130:Row.kt#2w3rfo");
                        Modifier.Companion companion = Modifier.INSTANCE;
                        MeasurePolicy measurePolicyRowMeasurePolicy2 = RowKt.rowMeasurePolicy(horizontalOrVerticalM468spacedBy0680j_5, Alignment.INSTANCE.getTop(), composer2, ((48 >> 3) & 14) | ((48 >> 3) & 112));
                        i3 = (48 << 3) & 112;
                        z4 = false;
                        composer2.startReplaceableGroup(-1323940314);
                        ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                        currentCompositeKeyHash3 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                        currentCompositionLocalMap = composer2.getCurrentCompositionLocalMap();
                        constructor3 = ComposeUiNode.INSTANCE.getConstructor();
                        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf3 = LayoutKt.modifierMaterializerOf(companion);
                        int i10 = ((i3 << 9) & 7168) | 6;
                        if (!(composer2.getApplier() instanceof Applier)) {
                            ComposablesKt.invalidApplier();
                        }
                        composer2.startReusableNode();
                        if (composer2.getInserting()) {
                            function3 = constructor3;
                            composer2.createNode(function3);
                        } else {
                            function3 = constructor3;
                            composer2.useNode();
                        }
                        composerM3273constructorimpl3 = Updater.m3273constructorimpl(composer2);
                        Updater.m3280setimpl(composerM3273constructorimpl3, measurePolicyRowMeasurePolicy2, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                        Updater.m3280setimpl(composerM3273constructorimpl3, currentCompositionLocalMap, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash3 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                        if (!composerM3273constructorimpl3.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl3.rememberedValue(), Integer.valueOf(currentCompositeKeyHash3))) {
                            composerM3273constructorimpl3.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash3));
                            composerM3273constructorimpl3.apply(Integer.valueOf(currentCompositeKeyHash3), setCompositeKeyHash3);
                        }
                        function4 = function3ModifierMaterializerOf3;
                        function4.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i10 >> 3) & 112));
                        composer2.startReplaceableGroup(2058660585);
                        int i11 = (i10 >> 9) & 14;
                        z5 = false;
                        ComposerKt.sourceInformationMarkerStart(composer2, -326681643, "C92@4661L9:Row.kt#2w3rfo");
                        RowScopeInstance rowScopeInstance2 = RowScopeInstance.INSTANCE;
                        int i12 = ((48 >> 6) & 112) | 6;
                        ComposerKt.sourceInformationMarkerStart(composer2, 444164309, "C:ClipPickerSheet.kt#wl24de");
                        composer2.startReplaceableGroup(1239103548);
                        ComposerKt.sourceInformation(composer2, "*127@5288L14,122@4948L1271");
                        list3 = list5;
                        z6 = false;
                        it3 = list3.iterator();
                        while (it3.hasNext()) {
                            List<String> list6 = list3;
                            str5 = (String) it3.next();
                            boolean z8 = z6;
                            zAreEqual = Intrinsics.areEqual(str5, ClipPickerSheetKt.ClipPickerSheet$lambda$3(mutableState2));
                            list4 = map.get(str5);
                            if (list4 != null || (clipInfo = (ClipInfo) CollectionsKt.firstOrNull((List) list4)) == null || (role = clipInfo.getRole()) == null) {
                                role = "";
                            }
                            String str9 = role;
                            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function9 = function4;
                            boolean z9 = z5;
                            int i13 = i3;
                            Modifier modifierClip = ClipKt.clip(Modifier.INSTANCE, RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14)));
                            if (zAreEqual) {
                                surfaceCard = ColorKt.getCyanAccent();
                            } else {
                                surfaceCard = ColorKt.getSurfaceCard();
                            }
                            Iterator it4 = it3;
                            boolean z10 = z4;
                            CompositionLocalMap compositionLocalMap = currentCompositionLocalMap;
                            Modifier modifierM218borderxT4_qwU = BorderKt.m218borderxT4_qwU(BackgroundKt.m207backgroundbw27NRU$default(modifierClip, surfaceCard, null, 2, null), Dp.m6091constructorimpl(1), androidx.compose.ui.graphics.ColorKt.Color(872415231), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14)));
                            composer2.startReplaceableGroup(2142679547);
                            ComposerKt.sourceInformation(composer2, str8);
                            zChanged2 = composer2.changed(str5);
                            Object objRememberedValue4 = composer2.rememberedValue();
                            if (!zChanged2 || objRememberedValue4 == Composer.INSTANCE.getEmpty()) {
                                obj3 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$2$1$1$1
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
                                        mutableState2.setValue(str5);
                                    }
                                };
                                composer2.updateRememberedValue(obj3);
                            } else {
                                obj3 = objRememberedValue4;
                            }
                            composer2.endReplaceableGroup();
                            Modifier modifierM560paddingVpY3zN5 = PaddingKt.m560paddingVpY3zN4(ClickableKt.m241clickableXHw0xAI$default(modifierM218borderxT4_qwU, false, null, null, (Function0) obj3, 7, null), Dp.m6091constructorimpl(16), Dp.m6091constructorimpl(10));
                            composer2.startReplaceableGroup(733328855);
                            ComposerKt.sourceInformation(composer2, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
                            MeasurePolicy measurePolicyRememberBoxMeasurePolicy = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                            composer2.startReplaceableGroup(-1323940314);
                            ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                            currentCompositeKeyHash4 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                            CompositionLocalMap currentCompositionLocalMap4 = composer2.getCurrentCompositionLocalMap();
                            constructor4 = ComposeUiNode.INSTANCE.getConstructor();
                            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf4 = LayoutKt.modifierMaterializerOf(modifierM560paddingVpY3zN5);
                            int i14 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                            if (!(composer2.getApplier() instanceof Applier)) {
                                ComposablesKt.invalidApplier();
                            }
                            composer2.startReusableNode();
                            if (composer2.getInserting()) {
                                function5 = constructor4;
                                composer2.createNode(function5);
                            } else {
                                function5 = constructor4;
                                composer2.useNode();
                            }
                            composerM3273constructorimpl4 = Updater.m3273constructorimpl(composer2);
                            String str10 = str8;
                            Updater.m3280setimpl(composerM3273constructorimpl4, measurePolicyRememberBoxMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                            Updater.m3280setimpl(composerM3273constructorimpl4, currentCompositionLocalMap4, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                            Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash4 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                            if (!composerM3273constructorimpl4.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl4.rememberedValue(), Integer.valueOf(currentCompositeKeyHash4))) {
                                composerM3273constructorimpl4.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash4));
                                composerM3273constructorimpl4.apply(Integer.valueOf(currentCompositeKeyHash4), setCompositeKeyHash4);
                            }
                            function3ModifierMaterializerOf4.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i14 >> 3) & 112));
                            composer2.startReplaceableGroup(2058660585);
                            int i15 = (i14 >> 9) & 14;
                            ComposerKt.sourceInformationMarkerStart(composer2, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
                            BoxScopeInstance boxScopeInstance = BoxScopeInstance.INSTANCE;
                            int i16 = ((0 >> 6) & 112) | 6;
                            ComposerKt.sourceInformationMarkerStart(composer2, 119885874, "C130@5438L755:ClipPickerSheet.kt#wl24de");
                            Alignment.Horizontal centerHorizontally = Alignment.INSTANCE.getCenterHorizontally();
                            composer2.startReplaceableGroup(-483455358);
                            ComposerKt.sourceInformation(composer2, str7);
                            Modifier.Companion companion2 = Modifier.INSTANCE;
                            MeasurePolicy measurePolicyColumnMeasurePolicy2 = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), centerHorizontally, composer2, ((384 >> 3) & 14) | ((384 >> 3) & 112));
                            composer2.startReplaceableGroup(-1323940314);
                            ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                            currentCompositeKeyHash5 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                            CompositionLocalMap currentCompositionLocalMap5 = composer2.getCurrentCompositionLocalMap();
                            constructor5 = ComposeUiNode.INSTANCE.getConstructor();
                            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf5 = LayoutKt.modifierMaterializerOf(companion2);
                            int i17 = ((((384 << 3) & 112) << 9) & 7168) | 6;
                            if (!(composer2.getApplier() instanceof Applier)) {
                                ComposablesKt.invalidApplier();
                            }
                            composer2.startReusableNode();
                            if (composer2.getInserting()) {
                                function6 = constructor5;
                                composer2.createNode(function6);
                            } else {
                                function6 = constructor5;
                                composer2.useNode();
                            }
                            composerM3273constructorimpl5 = Updater.m3273constructorimpl(composer2);
                            String str11 = str7;
                            Updater.m3280setimpl(composerM3273constructorimpl5, measurePolicyColumnMeasurePolicy2, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                            Updater.m3280setimpl(composerM3273constructorimpl5, currentCompositionLocalMap5, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                            Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash5 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                            if (!composerM3273constructorimpl5.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl5.rememberedValue(), Integer.valueOf(currentCompositeKeyHash5))) {
                                composerM3273constructorimpl5.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash5));
                                composerM3273constructorimpl5.apply(Integer.valueOf(currentCompositeKeyHash5), setCompositeKeyHash5);
                            }
                            function3ModifierMaterializerOf5.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i17 >> 3) & 112));
                            composer2.startReplaceableGroup(2058660585);
                            int i18 = (i17 >> 9) & 14;
                            String str12 = str4;
                            ComposerKt.sourceInformationMarkerStart(composer2, 276693656, str12);
                            ColumnScopeInstance columnScopeInstance2 = ColumnScopeInstance.INSTANCE;
                            int i19 = ((384 >> 6) & 112) | 6;
                            ComposerKt.sourceInformationMarkerStart(composer2, 888636592, "C131@5531L373,138@5937L226:ClipPickerSheet.kt#wl24de");
                            String str13 = "DRIVER " + str5;
                            GenericFontFamily monospace = FontFamily.INSTANCE.getMonospace();
                            long sp = TextUnitKt.getSp(12);
                            FontWeight bold = FontWeight.INSTANCE.getBold();
                            if (zAreEqual) {
                                textPrimary = Color.INSTANCE.m3769getBlack0d7_KjU();
                            } else {
                                textPrimary = ColorKt.getTextPrimary();
                            }
                            TextKt.m2461Text4IGK_g(str13, (Modifier) null, textPrimary, sp, (FontStyle) null, bold, (FontFamily) monospace, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 199680, 0, 130962);
                            long sp2 = TextUnitKt.getSp(9);
                            if (zAreEqual) {
                                textMuted = Color.INSTANCE.m3769getBlack0d7_KjU();
                            } else {
                                textMuted = ColorKt.getTextMuted();
                            }
                            TextKt.m2461Text4IGK_g(str9, (Modifier) null, textMuted, sp2, (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 3072, 0, 131058);
                            ComposerKt.sourceInformationMarkerEnd(composer2);
                            ComposerKt.sourceInformationMarkerEnd(composer2);
                            composer2.endReplaceableGroup();
                            composer2.endNode();
                            composer2.endReplaceableGroup();
                            composer2.endReplaceableGroup();
                            ComposerKt.sourceInformationMarkerEnd(composer2);
                            ComposerKt.sourceInformationMarkerEnd(composer2);
                            composer2.endReplaceableGroup();
                            composer2.endNode();
                            composer2.endReplaceableGroup();
                            composer2.endReplaceableGroup();
                            str4 = str12;
                            list3 = list6;
                            z6 = z8;
                            z5 = z9;
                            function4 = function9;
                            it3 = it4;
                            i3 = i13;
                            z4 = z10;
                            currentCompositionLocalMap = compositionLocalMap;
                            str8 = str10;
                            str7 = str11;
                        }
                        composer2.endReplaceableGroup();
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        composer2.endReplaceableGroup();
                        composer2.endNode();
                        composer2.endReplaceableGroup();
                        composer2.endReplaceableGroup();
                        SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(14)), composer2, 6);
                        LazyDslKt.LazyColumn(SizeKt.m596heightInVpY3zN4$default(Modifier.INSTANCE, 0.0f, Dp.m6091constructorimpl(AnimationConstants.DefaultDurationMillis), 1, null), null, null, false, Arrangement.INSTANCE.m468spacedBy0680j_4(Dp.m6091constructorimpl(8)), null, null, false, new Function1<LazyListScope, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3
                            /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                            /* JADX WARN: Multi-variable type inference failed */
                            {
                                super(1);
                            }

                            @Override // kotlin.jvm.functions.Function1
                            public /* bridge */ /* synthetic */ Unit invoke(LazyListScope lazyListScope) {
                                invoke2(lazyListScope);
                                return Unit.INSTANCE;
                            }

                            /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                            public final void invoke2(LazyListScope LazyColumn) {
                                Intrinsics.checkNotNullParameter(LazyColumn, "$this$LazyColumn");
                                final List<ClipInfo> listEmptyList = map.get(ClipPickerSheetKt.ClipPickerSheet$lambda$3(mutableState2));
                                if (listEmptyList == null) {
                                    listEmptyList = CollectionsKt.emptyList();
                                }
                                final String str14 = str6;
                                final Function1<ClipInfo, Unit> function10 = function8;
                                final ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1 clipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1 = new Function1() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1
                                    @Override // kotlin.jvm.functions.Function1
                                    public /* bridge */ /* synthetic */ Object invoke(Object obj4) {
                                        return invoke((ClipInfo) obj4);
                                    }

                                    @Override // kotlin.jvm.functions.Function1
                                    public final Void invoke(ClipInfo clipInfo2) {
                                        return null;
                                    }
                                };
                                LazyColumn.items(listEmptyList.size(), null, new Function1<Integer, Object>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$3
                                    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                                    {
                                        super(1);
                                    }

                                    public final Object invoke(int i20) {
                                        return clipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1.invoke(listEmptyList.get(i20));
                                    }

                                    @Override // kotlin.jvm.functions.Function1
                                    public /* bridge */ /* synthetic */ Object invoke(Integer num) {
                                        return invoke(num.intValue());
                                    }
                                }, ComposableLambdaKt.composableLambdaInstance(-632812321, true, new Function4<LazyItemScope, Integer, Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$4
                                    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                                    {
                                        super(4);
                                    }

                                    @Override // kotlin.jvm.functions.Function4
                                    public /* bridge */ /* synthetic */ Unit invoke(LazyItemScope lazyItemScope, Integer num, Composer composer3, Integer num2) {
                                        invoke(lazyItemScope, num.intValue(), composer3, num2.intValue());
                                        return Unit.INSTANCE;
                                    }

                                    public final void invoke(LazyItemScope lazyItemScope, int i20, Composer composer3, int i21) {
                                        ComposerKt.sourceInformation(composer3, "C148@6730L22:LazyDsl.kt#428nma");
                                        int i22 = i21;
                                        if ((i21 & 14) == 0) {
                                            i22 |= composer3.changed(lazyItemScope) ? 4 : 2;
                                        }
                                        if ((i21 & 112) == 0) {
                                            i22 |= composer3.changed(i20) ? 32 : 16;
                                        }
                                        if ((i22 & 731) == 146 && composer3.getSkipping()) {
                                            composer3.skipToGroupEnd();
                                            return;
                                        }
                                        if (ComposerKt.isTraceInProgress()) {
                                            ComposerKt.traceEventStart(-632812321, i22, -1, "androidx.compose.foundation.lazy.items.<anonymous> (LazyDsl.kt:148)");
                                        }
                                        ClipInfo clipInfo2 = (ClipInfo) listEmptyList.get(i20);
                                        composer3.startReplaceableGroup(2142680853);
                                        ComposerKt.sourceInformation(composer3, "C*155@6594L79:ClipPickerSheet.kt#wl24de");
                                        ClipPickerSheetKt.ClipRow(clipInfo2, Intrinsics.areEqual(clipInfo2.getId(), str14), function10, composer3, ((i22 & 14) >> 3) & 14);
                                        composer3.endReplaceableGroup();
                                        if (ComposerKt.isTraceInProgress()) {
                                            ComposerKt.traceEventEnd();
                                        }
                                    }
                                }));
                            }
                        }, composer2, 24582, 238);
                        composer2.endReplaceableGroup();
                    } else {
                        String str14 = str4;
                        composer2.startReplaceableGroup(1239105520);
                        ComposerKt.sourceInformation(composer2, "159@6751L1049");
                        Modifier modifierM559padding3ABfNKs = PaddingKt.m559padding3ABfNKs(BackgroundKt.m207backgroundbw27NRU$default(ClipKt.clip(SizeKt.fillMaxWidth$default(Modifier.INSTANCE, 0.0f, 1, null), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14))), ColorKt.getSurfaceCard(), null, 2, null), Dp.m6091constructorimpl(16));
                        composer2.startReplaceableGroup(733328855);
                        ComposerKt.sourceInformation(composer2, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
                        MeasurePolicy measurePolicyRememberBoxMeasurePolicy2 = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                        composer2.startReplaceableGroup(-1323940314);
                        ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                        currentCompositeKeyHash = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                        CompositionLocalMap currentCompositionLocalMap6 = composer2.getCurrentCompositionLocalMap();
                        constructor = ComposeUiNode.INSTANCE.getConstructor();
                        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf6 = LayoutKt.modifierMaterializerOf(modifierM559padding3ABfNKs);
                        int i20 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                        if (!(composer2.getApplier() instanceof Applier)) {
                            ComposablesKt.invalidApplier();
                        }
                        composer2.startReusableNode();
                        if (composer2.getInserting()) {
                            composer2.createNode(constructor);
                        } else {
                            composer2.useNode();
                        }
                        composerM3273constructorimpl = Updater.m3273constructorimpl(composer2);
                        Updater.m3280setimpl(composerM3273constructorimpl, measurePolicyRememberBoxMeasurePolicy2, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                        Updater.m3280setimpl(composerM3273constructorimpl, currentCompositionLocalMap6, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash6 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                        if (!composerM3273constructorimpl.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl.rememberedValue(), Integer.valueOf(currentCompositeKeyHash))) {
                            composerM3273constructorimpl.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash));
                            composerM3273constructorimpl.apply(Integer.valueOf(currentCompositeKeyHash), setCompositeKeyHash6);
                        }
                        function3ModifierMaterializerOf6.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i20 >> 3) & 112));
                        composer2.startReplaceableGroup(2058660585);
                        int i21 = (i20 >> 9) & 14;
                        ComposerKt.sourceInformationMarkerStart(composer2, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
                        BoxScopeInstance boxScopeInstance2 = BoxScopeInstance.INSTANCE;
                        int i22 = ((0 >> 6) & 112) | 6;
                        ComposerKt.sourceInformationMarkerStart(composer2, 444166560, "C166@7022L760:ClipPickerSheet.kt#wl24de");
                        composer2.startReplaceableGroup(-483455358);
                        ComposerKt.sourceInformation(composer2, "CC(Column)P(2,3,1)77@3865L61,78@3931L133:Column.kt#2w3rfo");
                        Modifier.Companion companion3 = Modifier.INSTANCE;
                        MeasurePolicy measurePolicyColumnMeasurePolicy3 = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), Alignment.INSTANCE.getStart(), composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                        composer2.startReplaceableGroup(-1323940314);
                        ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                        currentCompositeKeyHash2 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                        CompositionLocalMap currentCompositionLocalMap7 = composer2.getCurrentCompositionLocalMap();
                        constructor2 = ComposeUiNode.INSTANCE.getConstructor();
                        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf7 = LayoutKt.modifierMaterializerOf(companion3);
                        int i23 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                        if (!(composer2.getApplier() instanceof Applier)) {
                            ComposablesKt.invalidApplier();
                        }
                        composer2.startReusableNode();
                        if (composer2.getInserting()) {
                            function2 = constructor2;
                            composer2.createNode(function2);
                        } else {
                            function2 = constructor2;
                            composer2.useNode();
                        }
                        composerM3273constructorimpl2 = Updater.m3273constructorimpl(composer2);
                        Updater.m3280setimpl(composerM3273constructorimpl2, measurePolicyColumnMeasurePolicy3, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                        Updater.m3280setimpl(composerM3273constructorimpl2, currentCompositionLocalMap7, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash7 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                        if (!composerM3273constructorimpl2.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl2.rememberedValue(), Integer.valueOf(currentCompositeKeyHash2))) {
                            composerM3273constructorimpl2.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash2));
                            composerM3273constructorimpl2.apply(Integer.valueOf(currentCompositeKeyHash2), setCompositeKeyHash7);
                        }
                        function3ModifierMaterializerOf7.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i23 >> 3) & 112));
                        composer2.startReplaceableGroup(2058660585);
                        int i24 = (i23 >> 9) & 14;
                        ComposerKt.sourceInformationMarkerStart(composer2, 276693656, str14);
                        ColumnScopeInstance columnScopeInstance3 = ColumnScopeInstance.INSTANCE;
                        int i25 = ((0 >> 6) & 112) | 6;
                        ComposerKt.sourceInformationMarkerStart(composer2, 2142681314, "C167@7055L315,174@7395L40,175@7460L300:ClipPickerSheet.kt#wl24de");
                        TextKt.m2461Text4IGK_g("LIVE SENSOR NAVIGATION ACTIVE", (Modifier) null, ColorKt.getEmeraldGreen(), TextUnitKt.getSp(13), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 200070, 0, 130962);
                        SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(4)), composer2, 6);
                        TextKt.m2461Text4IGK_g("Using device Accelerometer and Gyroscope at 10 Hz with the Round-2 26-feature ML stationarity classifier and GNSS history calibration.", (Modifier) null, ColorKt.getTextSecondary(), TextUnitKt.getSp(12), (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 3462, 0, 131058);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        composer2.endReplaceableGroup();
                        composer2.endNode();
                        composer2.endReplaceableGroup();
                        composer2.endReplaceableGroup();
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        composer2.endReplaceableGroup();
                        composer2.endNode();
                        composer2.endReplaceableGroup();
                        composer2.endReplaceableGroup();
                        composer2.endReplaceableGroup();
                    }
                    SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(20)), composer2, 6);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    composer2.endReplaceableGroup();
                    composer2.endNode();
                    composer2.endReplaceableGroup();
                    composer2.endReplaceableGroup();
                    if (ComposerKt.isTraceInProgress()) {
                        ComposerKt.traceEventEnd();
                    }
                }
                str4 = "C79@3979L9:Column.kt#2w3rfo";
                obj = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$1$1$1
                    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                    /* JADX WARN: Multi-variable type inference failed */
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
                        function7.invoke(EngineMode.REPLAY);
                    }
                };
                composer2.updateRememberedValue(obj);
                composer2.endReplaceableGroup();
                ClipPickerSheetKt.EngineModeTab(engineMode3, z7, (Function0) obj, RowScope.weight$default(rowScopeInstance, Modifier.INSTANCE, 1.0f, false, 2, null), composer2, 6, 0);
                EngineMode engineMode5 = EngineMode.LIVE_ML;
                if (engineMode2 == EngineMode.LIVE_ML) {
                    z3 = true;
                } else {
                    z3 = false;
                }
                composer2.startReplaceableGroup(444163653);
                ComposerKt.sourceInformation(composer2, "CC(remember):ClipPickerSheet.kt#9igjgp");
                zChanged = composer2.changed(function7);
                Object objRememberedValue5 = composer2.rememberedValue();
                if (zChanged) {
                }
                obj2 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$1$2$1
                    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                    /* JADX WARN: Multi-variable type inference failed */
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
                        function7.invoke(EngineMode.LIVE_ML);
                    }
                };
                composer2.updateRememberedValue(obj2);
                composer2.endReplaceableGroup();
                ClipPickerSheetKt.EngineModeTab(engineMode5, z3, (Function0) obj2, RowScope.weight$default(rowScopeInstance, Modifier.INSTANCE, 1.0f, false, 2, null), composer2, 6, 0);
                ComposerKt.sourceInformationMarkerEnd(composer2);
                ComposerKt.sourceInformationMarkerEnd(composer2);
                composer2.endReplaceableGroup();
                composer2.endNode();
                composer2.endReplaceableGroup();
                composer2.endReplaceableGroup();
                SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(16)), composer2, 6);
                if (engineMode2 == EngineMode.REPLAY) {
                    composer2.startReplaceableGroup(1239103131);
                    ComposerKt.sourceInformation(composer2, "109@4362L256,116@4635L40,118@4693L1566,148@6277L41,150@6336L377");
                    TextKt.m2461Text4IGK_g("SELECT DATASET DRIVER", (Modifier) null, ColorKt.getTextMuted(), TextUnitKt.getSp(11), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 200070, 0, 130962);
                    SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(8)), composer2, 6);
                    Arrangement.HorizontalOrVertical horizontalOrVerticalM468spacedBy0680j_6 = Arrangement.INSTANCE.m468spacedBy0680j_4(Dp.m6091constructorimpl(8));
                    composer2.startReplaceableGroup(693286680);
                    ComposerKt.sourceInformation(composer2, "CC(Row)P(2,1,3)90@4553L58,91@4616L130:Row.kt#2w3rfo");
                    Modifier.Companion companion4 = Modifier.INSTANCE;
                    MeasurePolicy measurePolicyRowMeasurePolicy3 = RowKt.rowMeasurePolicy(horizontalOrVerticalM468spacedBy0680j_6, Alignment.INSTANCE.getTop(), composer2, ((48 >> 3) & 14) | ((48 >> 3) & 112));
                    i3 = (48 << 3) & 112;
                    z4 = false;
                    composer2.startReplaceableGroup(-1323940314);
                    ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                    currentCompositeKeyHash3 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                    currentCompositionLocalMap = composer2.getCurrentCompositionLocalMap();
                    constructor3 = ComposeUiNode.INSTANCE.getConstructor();
                    Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf8 = LayoutKt.modifierMaterializerOf(companion4);
                    int i110 = ((i3 << 9) & 7168) | 6;
                    if (!(composer2.getApplier() instanceof Applier)) {
                        ComposablesKt.invalidApplier();
                    }
                    composer2.startReusableNode();
                    if (composer2.getInserting()) {
                        function3 = constructor3;
                        composer2.createNode(function3);
                    } else {
                        function3 = constructor3;
                        composer2.useNode();
                    }
                    composerM3273constructorimpl3 = Updater.m3273constructorimpl(composer2);
                    Updater.m3280setimpl(composerM3273constructorimpl3, measurePolicyRowMeasurePolicy3, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                    Updater.m3280setimpl(composerM3273constructorimpl3, currentCompositionLocalMap, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                    Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash8 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                    if (!composerM3273constructorimpl3.getInserting()) {
                    }
                    composerM3273constructorimpl3.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash3));
                    composerM3273constructorimpl3.apply(Integer.valueOf(currentCompositeKeyHash3), setCompositeKeyHash8);
                    function4 = function3ModifierMaterializerOf8;
                    function4.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i110 >> 3) & 112));
                    composer2.startReplaceableGroup(2058660585);
                    int i111 = (i110 >> 9) & 14;
                    z5 = false;
                    ComposerKt.sourceInformationMarkerStart(composer2, -326681643, "C92@4661L9:Row.kt#2w3rfo");
                    RowScopeInstance rowScopeInstance3 = RowScopeInstance.INSTANCE;
                    int i112 = ((48 >> 6) & 112) | 6;
                    ComposerKt.sourceInformationMarkerStart(composer2, 444164309, "C:ClipPickerSheet.kt#wl24de");
                    composer2.startReplaceableGroup(1239103548);
                    ComposerKt.sourceInformation(composer2, "*127@5288L14,122@4948L1271");
                    list3 = list5;
                    z6 = false;
                    it3 = list3.iterator();
                    while (it3.hasNext()) {
                        List<String> list7 = list3;
                        str5 = (String) it3.next();
                        boolean z11 = z6;
                        zAreEqual = Intrinsics.areEqual(str5, ClipPickerSheetKt.ClipPickerSheet$lambda$3(mutableState2));
                        list4 = map.get(str5);
                        if (list4 != null) {
                            role = "";
                        } else {
                            role = "";
                        }
                        String str15 = role;
                        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function10 = function4;
                        boolean z12 = z5;
                        int i113 = i3;
                        Modifier modifierClip2 = ClipKt.clip(Modifier.INSTANCE, RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14)));
                        if (zAreEqual) {
                            surfaceCard = ColorKt.getCyanAccent();
                        } else {
                            surfaceCard = ColorKt.getSurfaceCard();
                        }
                        Iterator it5 = it3;
                        boolean z13 = z4;
                        CompositionLocalMap compositionLocalMap2 = currentCompositionLocalMap;
                        Modifier modifierM218borderxT4_qwU2 = BorderKt.m218borderxT4_qwU(BackgroundKt.m207backgroundbw27NRU$default(modifierClip2, surfaceCard, null, 2, null), Dp.m6091constructorimpl(1), androidx.compose.ui.graphics.ColorKt.Color(872415231), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14)));
                        composer2.startReplaceableGroup(2142679547);
                        ComposerKt.sourceInformation(composer2, str8);
                        zChanged2 = composer2.changed(str5);
                        Object objRememberedValue6 = composer2.rememberedValue();
                        if (zChanged2) {
                            obj3 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$2$1$1$1
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
                                    mutableState2.setValue(str5);
                                }
                            };
                            composer2.updateRememberedValue(obj3);
                        } else {
                            obj3 = (Function0) new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$2$1$1$1
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
                                    mutableState2.setValue(str5);
                                }
                            };
                            composer2.updateRememberedValue(obj3);
                        }
                        composer2.endReplaceableGroup();
                        Modifier modifierM560paddingVpY3zN6 = PaddingKt.m560paddingVpY3zN4(ClickableKt.m241clickableXHw0xAI$default(modifierM218borderxT4_qwU2, false, null, null, (Function0) obj3, 7, null), Dp.m6091constructorimpl(16), Dp.m6091constructorimpl(10));
                        composer2.startReplaceableGroup(733328855);
                        ComposerKt.sourceInformation(composer2, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
                        MeasurePolicy measurePolicyRememberBoxMeasurePolicy3 = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                        composer2.startReplaceableGroup(-1323940314);
                        ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                        currentCompositeKeyHash4 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                        CompositionLocalMap currentCompositionLocalMap8 = composer2.getCurrentCompositionLocalMap();
                        constructor4 = ComposeUiNode.INSTANCE.getConstructor();
                        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf9 = LayoutKt.modifierMaterializerOf(modifierM560paddingVpY3zN6);
                        int i114 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                        if (!(composer2.getApplier() instanceof Applier)) {
                            ComposablesKt.invalidApplier();
                        }
                        composer2.startReusableNode();
                        if (composer2.getInserting()) {
                            function5 = constructor4;
                            composer2.createNode(function5);
                        } else {
                            function5 = constructor4;
                            composer2.useNode();
                        }
                        composerM3273constructorimpl4 = Updater.m3273constructorimpl(composer2);
                        String str16 = str8;
                        Updater.m3280setimpl(composerM3273constructorimpl4, measurePolicyRememberBoxMeasurePolicy3, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                        Updater.m3280setimpl(composerM3273constructorimpl4, currentCompositionLocalMap8, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash9 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                        if (!composerM3273constructorimpl4.getInserting()) {
                        }
                        composerM3273constructorimpl4.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash4));
                        composerM3273constructorimpl4.apply(Integer.valueOf(currentCompositeKeyHash4), setCompositeKeyHash9);
                        function3ModifierMaterializerOf9.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i114 >> 3) & 112));
                        composer2.startReplaceableGroup(2058660585);
                        int i115 = (i114 >> 9) & 14;
                        ComposerKt.sourceInformationMarkerStart(composer2, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
                        BoxScopeInstance boxScopeInstance3 = BoxScopeInstance.INSTANCE;
                        int i116 = ((0 >> 6) & 112) | 6;
                        ComposerKt.sourceInformationMarkerStart(composer2, 119885874, "C130@5438L755:ClipPickerSheet.kt#wl24de");
                        Alignment.Horizontal centerHorizontally2 = Alignment.INSTANCE.getCenterHorizontally();
                        composer2.startReplaceableGroup(-483455358);
                        ComposerKt.sourceInformation(composer2, str7);
                        Modifier.Companion companion5 = Modifier.INSTANCE;
                        MeasurePolicy measurePolicyColumnMeasurePolicy4 = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), centerHorizontally2, composer2, ((384 >> 3) & 14) | ((384 >> 3) & 112));
                        composer2.startReplaceableGroup(-1323940314);
                        ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                        currentCompositeKeyHash5 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                        CompositionLocalMap currentCompositionLocalMap9 = composer2.getCurrentCompositionLocalMap();
                        constructor5 = ComposeUiNode.INSTANCE.getConstructor();
                        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf10 = LayoutKt.modifierMaterializerOf(companion5);
                        int i117 = ((((384 << 3) & 112) << 9) & 7168) | 6;
                        if (!(composer2.getApplier() instanceof Applier)) {
                            ComposablesKt.invalidApplier();
                        }
                        composer2.startReusableNode();
                        if (composer2.getInserting()) {
                            function6 = constructor5;
                            composer2.createNode(function6);
                        } else {
                            function6 = constructor5;
                            composer2.useNode();
                        }
                        composerM3273constructorimpl5 = Updater.m3273constructorimpl(composer2);
                        String str17 = str7;
                        Updater.m3280setimpl(composerM3273constructorimpl5, measurePolicyColumnMeasurePolicy4, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                        Updater.m3280setimpl(composerM3273constructorimpl5, currentCompositionLocalMap9, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash10 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                        if (!composerM3273constructorimpl5.getInserting()) {
                        }
                        composerM3273constructorimpl5.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash5));
                        composerM3273constructorimpl5.apply(Integer.valueOf(currentCompositeKeyHash5), setCompositeKeyHash10);
                        function3ModifierMaterializerOf10.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i117 >> 3) & 112));
                        composer2.startReplaceableGroup(2058660585);
                        int i118 = (i117 >> 9) & 14;
                        String str18 = str4;
                        ComposerKt.sourceInformationMarkerStart(composer2, 276693656, str18);
                        ColumnScopeInstance columnScopeInstance4 = ColumnScopeInstance.INSTANCE;
                        int i119 = ((384 >> 6) & 112) | 6;
                        ComposerKt.sourceInformationMarkerStart(composer2, 888636592, "C131@5531L373,138@5937L226:ClipPickerSheet.kt#wl24de");
                        String str19 = "DRIVER " + str5;
                        GenericFontFamily monospace2 = FontFamily.INSTANCE.getMonospace();
                        long sp3 = TextUnitKt.getSp(12);
                        FontWeight bold2 = FontWeight.INSTANCE.getBold();
                        if (zAreEqual) {
                            textPrimary = Color.INSTANCE.m3769getBlack0d7_KjU();
                        } else {
                            textPrimary = ColorKt.getTextPrimary();
                        }
                        TextKt.m2461Text4IGK_g(str19, (Modifier) null, textPrimary, sp3, (FontStyle) null, bold2, (FontFamily) monospace2, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 199680, 0, 130962);
                        long sp4 = TextUnitKt.getSp(9);
                        if (zAreEqual) {
                            textMuted = Color.INSTANCE.m3769getBlack0d7_KjU();
                        } else {
                            textMuted = ColorKt.getTextMuted();
                        }
                        TextKt.m2461Text4IGK_g(str15, (Modifier) null, textMuted, sp4, (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 3072, 0, 131058);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        composer2.endReplaceableGroup();
                        composer2.endNode();
                        composer2.endReplaceableGroup();
                        composer2.endReplaceableGroup();
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        ComposerKt.sourceInformationMarkerEnd(composer2);
                        composer2.endReplaceableGroup();
                        composer2.endNode();
                        composer2.endReplaceableGroup();
                        composer2.endReplaceableGroup();
                        str4 = str18;
                        list3 = list7;
                        z6 = z11;
                        z5 = z12;
                        function4 = function10;
                        it3 = it5;
                        i3 = i113;
                        z4 = z13;
                        currentCompositionLocalMap = compositionLocalMap2;
                        str8 = str16;
                        str7 = str17;
                    }
                    composer2.endReplaceableGroup();
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    composer2.endReplaceableGroup();
                    composer2.endNode();
                    composer2.endReplaceableGroup();
                    composer2.endReplaceableGroup();
                    SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(14)), composer2, 6);
                    LazyDslKt.LazyColumn(SizeKt.m596heightInVpY3zN4$default(Modifier.INSTANCE, 0.0f, Dp.m6091constructorimpl(AnimationConstants.DefaultDurationMillis), 1, null), null, null, false, Arrangement.INSTANCE.m468spacedBy0680j_4(Dp.m6091constructorimpl(8)), null, null, false, new Function1<LazyListScope, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3
                        /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                        /* JADX WARN: Multi-variable type inference failed */
                        {
                            super(1);
                        }

                        @Override // kotlin.jvm.functions.Function1
                        public /* bridge */ /* synthetic */ Unit invoke(LazyListScope lazyListScope) {
                            invoke2(lazyListScope);
                            return Unit.INSTANCE;
                        }

                        /* JADX INFO: renamed from: invoke, reason: avoid collision after fix types in other method */
                        public final void invoke2(LazyListScope LazyColumn) {
                            Intrinsics.checkNotNullParameter(LazyColumn, "$this$LazyColumn");
                            final List listEmptyList = map.get(ClipPickerSheetKt.ClipPickerSheet$lambda$3(mutableState2));
                            if (listEmptyList == null) {
                                listEmptyList = CollectionsKt.emptyList();
                            }
                            final String str110 = str6;
                            final Function1 function11 = function8;
                            final Function1 clipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1 = new Function1() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1
                                @Override // kotlin.jvm.functions.Function1
                                public /* bridge */ /* synthetic */ Object invoke(Object obj4) {
                                    return invoke((ClipInfo) obj4);
                                }

                                @Override // kotlin.jvm.functions.Function1
                                public final Void invoke(ClipInfo clipInfo2) {
                                    return null;
                                }
                            };
                            LazyColumn.items(listEmptyList.size(), null, new Function1<Integer, Object>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$3
                                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                                {
                                    super(1);
                                }

                                public final Object invoke(int i26) {
                                    return clipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$1.invoke(listEmptyList.get(i26));
                                }

                                @Override // kotlin.jvm.functions.Function1
                                public /* bridge */ /* synthetic */ Object invoke(Integer num) {
                                    return invoke(num.intValue());
                                }
                            }, ComposableLambdaKt.composableLambdaInstance(-632812321, true, new Function4<LazyItemScope, Integer, Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipPickerSheet$1$1$3$invoke$$inlined$items$default$4
                                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                                {
                                    super(4);
                                }

                                @Override // kotlin.jvm.functions.Function4
                                public /* bridge */ /* synthetic */ Unit invoke(LazyItemScope lazyItemScope, Integer num, Composer composer3, Integer num2) {
                                    invoke(lazyItemScope, num.intValue(), composer3, num2.intValue());
                                    return Unit.INSTANCE;
                                }

                                public final void invoke(LazyItemScope lazyItemScope, int i26, Composer composer3, int i27) {
                                    ComposerKt.sourceInformation(composer3, "C148@6730L22:LazyDsl.kt#428nma");
                                    int i28 = i27;
                                    if ((i27 & 14) == 0) {
                                        i28 |= composer3.changed(lazyItemScope) ? 4 : 2;
                                    }
                                    if ((i27 & 112) == 0) {
                                        i28 |= composer3.changed(i26) ? 32 : 16;
                                    }
                                    if ((i28 & 731) == 146 && composer3.getSkipping()) {
                                        composer3.skipToGroupEnd();
                                        return;
                                    }
                                    if (ComposerKt.isTraceInProgress()) {
                                        ComposerKt.traceEventStart(-632812321, i28, -1, "androidx.compose.foundation.lazy.items.<anonymous> (LazyDsl.kt:148)");
                                    }
                                    ClipInfo clipInfo2 = (ClipInfo) listEmptyList.get(i26);
                                    composer3.startReplaceableGroup(2142680853);
                                    ComposerKt.sourceInformation(composer3, "C*155@6594L79:ClipPickerSheet.kt#wl24de");
                                    ClipPickerSheetKt.ClipRow(clipInfo2, Intrinsics.areEqual(clipInfo2.getId(), str110), function11, composer3, ((i28 & 14) >> 3) & 14);
                                    composer3.endReplaceableGroup();
                                    if (ComposerKt.isTraceInProgress()) {
                                        ComposerKt.traceEventEnd();
                                    }
                                }
                            }));
                        }
                    }, composer2, 24582, 238);
                    composer2.endReplaceableGroup();
                } else {
                    String str110 = str4;
                    composer2.startReplaceableGroup(1239105520);
                    ComposerKt.sourceInformation(composer2, "159@6751L1049");
                    Modifier modifierM559padding3ABfNKs2 = PaddingKt.m559padding3ABfNKs(BackgroundKt.m207backgroundbw27NRU$default(ClipKt.clip(SizeKt.fillMaxWidth$default(Modifier.INSTANCE, 0.0f, 1, null), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14))), ColorKt.getSurfaceCard(), null, 2, null), Dp.m6091constructorimpl(16));
                    composer2.startReplaceableGroup(733328855);
                    ComposerKt.sourceInformation(composer2, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
                    MeasurePolicy measurePolicyRememberBoxMeasurePolicy4 = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                    composer2.startReplaceableGroup(-1323940314);
                    ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                    currentCompositeKeyHash = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                    CompositionLocalMap currentCompositionLocalMap10 = composer2.getCurrentCompositionLocalMap();
                    constructor = ComposeUiNode.INSTANCE.getConstructor();
                    Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf11 = LayoutKt.modifierMaterializerOf(modifierM559padding3ABfNKs2);
                    int i26 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                    if (!(composer2.getApplier() instanceof Applier)) {
                        ComposablesKt.invalidApplier();
                    }
                    composer2.startReusableNode();
                    if (composer2.getInserting()) {
                        composer2.createNode(constructor);
                    } else {
                        composer2.useNode();
                    }
                    composerM3273constructorimpl = Updater.m3273constructorimpl(composer2);
                    Updater.m3280setimpl(composerM3273constructorimpl, measurePolicyRememberBoxMeasurePolicy4, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                    Updater.m3280setimpl(composerM3273constructorimpl, currentCompositionLocalMap10, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                    Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash11 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                    if (!composerM3273constructorimpl.getInserting()) {
                    }
                    composerM3273constructorimpl.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash));
                    composerM3273constructorimpl.apply(Integer.valueOf(currentCompositeKeyHash), setCompositeKeyHash11);
                    function3ModifierMaterializerOf11.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i26 >> 3) & 112));
                    composer2.startReplaceableGroup(2058660585);
                    int i27 = (i26 >> 9) & 14;
                    ComposerKt.sourceInformationMarkerStart(composer2, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
                    BoxScopeInstance boxScopeInstance4 = BoxScopeInstance.INSTANCE;
                    int i28 = ((0 >> 6) & 112) | 6;
                    ComposerKt.sourceInformationMarkerStart(composer2, 444166560, "C166@7022L760:ClipPickerSheet.kt#wl24de");
                    composer2.startReplaceableGroup(-483455358);
                    ComposerKt.sourceInformation(composer2, "CC(Column)P(2,3,1)77@3865L61,78@3931L133:Column.kt#2w3rfo");
                    Modifier.Companion companion6 = Modifier.INSTANCE;
                    MeasurePolicy measurePolicyColumnMeasurePolicy5 = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), Alignment.INSTANCE.getStart(), composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                    composer2.startReplaceableGroup(-1323940314);
                    ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                    currentCompositeKeyHash2 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                    CompositionLocalMap currentCompositionLocalMap11 = composer2.getCurrentCompositionLocalMap();
                    constructor2 = ComposeUiNode.INSTANCE.getConstructor();
                    Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf12 = LayoutKt.modifierMaterializerOf(companion6);
                    int i29 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                    if (!(composer2.getApplier() instanceof Applier)) {
                        ComposablesKt.invalidApplier();
                    }
                    composer2.startReusableNode();
                    if (composer2.getInserting()) {
                        function2 = constructor2;
                        composer2.createNode(function2);
                    } else {
                        function2 = constructor2;
                        composer2.useNode();
                    }
                    composerM3273constructorimpl2 = Updater.m3273constructorimpl(composer2);
                    Updater.m3280setimpl(composerM3273constructorimpl2, measurePolicyColumnMeasurePolicy5, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                    Updater.m3280setimpl(composerM3273constructorimpl2, currentCompositionLocalMap11, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                    Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash12 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                    if (!composerM3273constructorimpl2.getInserting()) {
                    }
                    composerM3273constructorimpl2.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash2));
                    composerM3273constructorimpl2.apply(Integer.valueOf(currentCompositeKeyHash2), setCompositeKeyHash12);
                    function3ModifierMaterializerOf12.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i29 >> 3) & 112));
                    composer2.startReplaceableGroup(2058660585);
                    int i210 = (i29 >> 9) & 14;
                    ComposerKt.sourceInformationMarkerStart(composer2, 276693656, str110);
                    ColumnScopeInstance columnScopeInstance5 = ColumnScopeInstance.INSTANCE;
                    int i211 = ((0 >> 6) & 112) | 6;
                    ComposerKt.sourceInformationMarkerStart(composer2, 2142681314, "C167@7055L315,174@7395L40,175@7460L300:ClipPickerSheet.kt#wl24de");
                    TextKt.m2461Text4IGK_g("LIVE SENSOR NAVIGATION ACTIVE", (Modifier) null, ColorKt.getEmeraldGreen(), TextUnitKt.getSp(13), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 200070, 0, 130962);
                    SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(4)), composer2, 6);
                    TextKt.m2461Text4IGK_g("Using device Accelerometer and Gyroscope at 10 Hz with the Round-2 26-feature ML stationarity classifier and GNSS history calibration.", (Modifier) null, ColorKt.getTextSecondary(), TextUnitKt.getSp(12), (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composer2, 3462, 0, 131058);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    composer2.endReplaceableGroup();
                    composer2.endNode();
                    composer2.endReplaceableGroup();
                    composer2.endReplaceableGroup();
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    ComposerKt.sourceInformationMarkerEnd(composer2);
                    composer2.endReplaceableGroup();
                    composer2.endNode();
                    composer2.endReplaceableGroup();
                    composer2.endReplaceableGroup();
                    composer2.endReplaceableGroup();
                }
                SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(20)), composer2, 6);
                ComposerKt.sourceInformationMarkerEnd(composer2);
                ComposerKt.sourceInformationMarkerEnd(composer2);
                composer2.endReplaceableGroup();
                composer2.endNode();
                composer2.endReplaceableGroup();
                composer2.endReplaceableGroup();
                if (ComposerKt.isTraceInProgress()) {
                    ComposerKt.traceEventEnd();
                }
            }
        }), composerStartRestartGroup, ((i >> 18) & 14) | 12779520, 384, 3930);
        if (ComposerKt.isTraceInProgress()) {
            ComposerKt.traceEventEnd();
        }
        ScopeUpdateScope scopeUpdateScopeEndRestartGroup = composerStartRestartGroup.endRestartGroup();
        if (scopeUpdateScopeEndRestartGroup != null) {
            scopeUpdateScopeEndRestartGroup.updateScope(new Function2<Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt.ClipPickerSheet.2
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                /* JADX WARN: Multi-variable type inference failed */
                {
                    super(2);
                }

                @Override // kotlin.jvm.functions.Function2
                public /* bridge */ /* synthetic */ Unit invoke(Composer composer2, Integer num) {
                    invoke(composer2, num.intValue());
                    return Unit.INSTANCE;
                }

                public final void invoke(Composer composer2, int i2) {
                    ClipPickerSheetKt.ClipPickerSheet(engineMode, drivers, clipsByDriver, str, onSetEngineMode, onSelect, onDismiss, composer2, RecomposeScopeImplKt.updateChangedFlags(i | 1));
                }
            });
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final String ClipPickerSheet$lambda$3(MutableState<String> mutableState) {
        return mutableState.getValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final void ClipRow(final ClipInfo clipInfo, final boolean z, final Function1<? super ClipInfo, Unit> function1, Composer composer, final int i) {
        Object obj;
        Function0<ComposeUiNode> function0;
        Function0<ComposeUiNode> function2;
        Function0<ComposeUiNode> function3;
        Function0<ComposeUiNode> function4;
        Composer composerStartRestartGroup = composer.startRestartGroup(-703074656);
        ComposerKt.sourceInformation(composerStartRestartGroup, "C(ClipRow)P(!1,2)227@9142L18,217@8812L1867:ClipPickerSheet.kt#wl24de");
        int i2 = i;
        if ((i & 14) == 0) {
            i2 |= composerStartRestartGroup.changed(clipInfo) ? 4 : 2;
        }
        if ((i & 112) == 0) {
            i2 |= composerStartRestartGroup.changed(z) ? 32 : 16;
        }
        if ((i & 896) == 0) {
            i2 |= composerStartRestartGroup.changedInstance(function1) ? 256 : 128;
        }
        if ((i2 & 731) == 146 && composerStartRestartGroup.getSkipping()) {
            composerStartRestartGroup.skipToGroupEnd();
        } else {
            if (ComposerKt.isTraceInProgress()) {
                ComposerKt.traceEventStart(-703074656, i2, -1, "com.sih2026.nav.ui.components.ClipRow (ClipPickerSheet.kt:216)");
            }
            Modifier modifierM218borderxT4_qwU = BorderKt.m218borderxT4_qwU(BackgroundKt.m207backgroundbw27NRU$default(ClipKt.clip(SizeKt.fillMaxWidth$default(Modifier.INSTANCE, 0.0f, 1, null), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14))), ColorKt.getSurfaceCard(), null, 2, null), Dp.m6091constructorimpl(1), z ? ColorKt.getCyanAccent() : androidx.compose.ui.graphics.ColorKt.Color(587202559), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14)));
            composerStartRestartGroup.startReplaceableGroup(-662524868);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):ClipPickerSheet.kt#9igjgp");
            boolean z2 = ((i2 & 896) == 256) | ((i2 & 14) == 4);
            Object objRememberedValue = composerStartRestartGroup.rememberedValue();
            if (z2 || objRememberedValue == Composer.INSTANCE.getEmpty()) {
                obj = new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt$ClipRow$1$1
                    /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                    /* JADX WARN: Multi-variable type inference failed */
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
                        function1.invoke(clipInfo);
                    }
                };
                composerStartRestartGroup.updateRememberedValue(obj);
            } else {
                obj = objRememberedValue;
            }
            composerStartRestartGroup.endReplaceableGroup();
            Modifier modifierM559padding3ABfNKs = PaddingKt.m559padding3ABfNKs(ClickableKt.m241clickableXHw0xAI$default(modifierM218borderxT4_qwU, false, null, null, (Function0) obj, 7, null), Dp.m6091constructorimpl(14));
            composerStartRestartGroup.startReplaceableGroup(733328855);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
            MeasurePolicy measurePolicyRememberBoxMeasurePolicy = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composerStartRestartGroup, ((0 >> 3) & 14) | ((0 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(-1323940314);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
            int currentCompositeKeyHash = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
            CompositionLocalMap currentCompositionLocalMap = composerStartRestartGroup.getCurrentCompositionLocalMap();
            Function0<ComposeUiNode> constructor = ComposeUiNode.INSTANCE.getConstructor();
            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf = LayoutKt.modifierMaterializerOf(modifierM559padding3ABfNKs);
            int i3 = ((((0 << 3) & 112) << 9) & 7168) | 6;
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
            function3ModifierMaterializerOf.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i3 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(2058660585);
            int i4 = (i3 >> 9) & 14;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
            BoxScopeInstance boxScopeInstance = BoxScopeInstance.INSTANCE;
            int i5 = ((0 >> 6) & 112) | 6;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 1384322460, "C230@9205L1468:ClipPickerSheet.kt#wl24de");
            Alignment.Vertical centerVertically = Alignment.INSTANCE.getCenterVertically();
            composerStartRestartGroup.startReplaceableGroup(693286680);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Row)P(2,1,3)90@4553L58,91@4616L130:Row.kt#2w3rfo");
            Modifier.Companion companion = Modifier.INSTANCE;
            MeasurePolicy measurePolicyRowMeasurePolicy = RowKt.rowMeasurePolicy(Arrangement.INSTANCE.getStart(), centerVertically, composerStartRestartGroup, ((384 >> 3) & 14) | ((384 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(-1323940314);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
            int currentCompositeKeyHash2 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
            CompositionLocalMap currentCompositionLocalMap2 = composerStartRestartGroup.getCurrentCompositionLocalMap();
            Function0<ComposeUiNode> constructor2 = ComposeUiNode.INSTANCE.getConstructor();
            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf2 = LayoutKt.modifierMaterializerOf(companion);
            int i6 = ((((384 << 3) & 112) << 9) & 7168) | 6;
            if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
                ComposablesKt.invalidApplier();
            }
            composerStartRestartGroup.startReusableNode();
            if (composerStartRestartGroup.getInserting()) {
                function2 = constructor2;
                composerStartRestartGroup.createNode(function2);
            } else {
                function2 = constructor2;
                composerStartRestartGroup.useNode();
            }
            Composer composerM3273constructorimpl2 = Updater.m3273constructorimpl(composerStartRestartGroup);
            Updater.m3280setimpl(composerM3273constructorimpl2, measurePolicyRowMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
            Updater.m3280setimpl(composerM3273constructorimpl2, currentCompositionLocalMap2, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
            Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash2 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
            if (composerM3273constructorimpl2.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl2.rememberedValue(), Integer.valueOf(currentCompositeKeyHash2))) {
                composerM3273constructorimpl2.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash2));
                composerM3273constructorimpl2.apply(Integer.valueOf(currentCompositeKeyHash2), setCompositeKeyHash2);
            }
            function3ModifierMaterializerOf2.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i6 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(2058660585);
            int i7 = (i6 >> 9) & 14;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -326681643, "C92@4661L9:Row.kt#2w3rfo");
            int i8 = ((384 >> 6) & 112) | 6;
            RowScopeInstance rowScopeInstance = RowScopeInstance.INSTANCE;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 1225905535, "C231@9271L747,250@10031L40,251@10084L579:ClipPickerSheet.kt#wl24de");
            Modifier modifierWeight$default = RowScope.weight$default(rowScopeInstance, Modifier.INSTANCE, 1.0f, false, 2, null);
            composerStartRestartGroup.startReplaceableGroup(-483455358);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Column)P(2,3,1)77@3865L61,78@3931L133:Column.kt#2w3rfo");
            MeasurePolicy measurePolicyColumnMeasurePolicy = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), Alignment.INSTANCE.getStart(), composerStartRestartGroup, ((0 >> 3) & 14) | ((0 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(-1323940314);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
            int currentCompositeKeyHash3 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
            CompositionLocalMap currentCompositionLocalMap3 = composerStartRestartGroup.getCurrentCompositionLocalMap();
            Function0<ComposeUiNode> constructor3 = ComposeUiNode.INSTANCE.getConstructor();
            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf3 = LayoutKt.modifierMaterializerOf(modifierWeight$default);
            int i9 = ((((0 << 3) & 112) << 9) & 7168) | 6;
            if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
                ComposablesKt.invalidApplier();
            }
            composerStartRestartGroup.startReusableNode();
            if (composerStartRestartGroup.getInserting()) {
                function3 = constructor3;
                composerStartRestartGroup.createNode(function3);
            } else {
                function3 = constructor3;
                composerStartRestartGroup.useNode();
            }
            Composer composerM3273constructorimpl3 = Updater.m3273constructorimpl(composerStartRestartGroup);
            Updater.m3280setimpl(composerM3273constructorimpl3, measurePolicyColumnMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
            Updater.m3280setimpl(composerM3273constructorimpl3, currentCompositionLocalMap3, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
            Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash3 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
            if (composerM3273constructorimpl3.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl3.rememberedValue(), Integer.valueOf(currentCompositeKeyHash3))) {
                composerM3273constructorimpl3.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash3));
                composerM3273constructorimpl3.apply(Integer.valueOf(currentCompositeKeyHash3), setCompositeKeyHash3);
            }
            function3ModifierMaterializerOf3.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i9 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(2058660585);
            int i10 = (i9 >> 9) & 14;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 276693656, "C79@3979L9:Column.kt#2w3rfo");
            ColumnScopeInstance columnScopeInstance = ColumnScopeInstance.INSTANCE;
            int i11 = ((0 >> 6) & 112) | 6;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1662964775, "C232@9328L270,239@9615L40,240@9672L332:ClipPickerSheet.kt#wl24de");
            TextKt.m2461Text4IGK_g(clipInfo.getDrive() + " · " + clipInfo.getBandLabel(), (Modifier) null, ColorKt.getTextPrimary(), TextUnitKt.getSp(13), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 200064, 0, 130962);
            SpacerKt.Spacer(SizeKt.m594height3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(2)), composerStartRestartGroup, 6);
            StringCompanionObject stringCompanionObject = StringCompanionObject.INSTANCE;
            String str = String.format(Locale.US, "%.0f km/h average · %d turns · %.0f s", Arrays.copyOf(new Object[]{Double.valueOf(clipInfo.getAvgKmh()), Integer.valueOf(clipInfo.getTurns()), Double.valueOf(clipInfo.getDurationS())}, 3));
            Intrinsics.checkNotNullExpressionValue(str, "format(...)");
            TextKt.m2461Text4IGK_g(str, (Modifier) null, ColorKt.getTextSecondary(), TextUnitKt.getSp(11), (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 3456, 0, 131058);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endNode();
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endReplaceableGroup();
            SpacerKt.Spacer(SizeKt.m613width3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(10)), composerStartRestartGroup, 6);
            Alignment.Horizontal end = Alignment.INSTANCE.getEnd();
            composerStartRestartGroup.startReplaceableGroup(-483455358);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Column)P(2,3,1)77@3865L61,78@3931L133:Column.kt#2w3rfo");
            Modifier.Companion companion2 = Modifier.INSTANCE;
            MeasurePolicy measurePolicyColumnMeasurePolicy2 = ColumnKt.columnMeasurePolicy(Arrangement.INSTANCE.getTop(), end, composerStartRestartGroup, ((384 >> 3) & 14) | ((384 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(-1323940314);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
            int currentCompositeKeyHash4 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
            CompositionLocalMap currentCompositionLocalMap4 = composerStartRestartGroup.getCurrentCompositionLocalMap();
            Function0<ComposeUiNode> constructor4 = ComposeUiNode.INSTANCE.getConstructor();
            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf4 = LayoutKt.modifierMaterializerOf(companion2);
            int i12 = ((((384 << 3) & 112) << 9) & 7168) | 6;
            if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
                ComposablesKt.invalidApplier();
            }
            composerStartRestartGroup.startReusableNode();
            if (composerStartRestartGroup.getInserting()) {
                function4 = constructor4;
                composerStartRestartGroup.createNode(function4);
            } else {
                function4 = constructor4;
                composerStartRestartGroup.useNode();
            }
            Composer composerM3273constructorimpl4 = Updater.m3273constructorimpl(composerStartRestartGroup);
            Updater.m3280setimpl(composerM3273constructorimpl4, measurePolicyColumnMeasurePolicy2, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
            Updater.m3280setimpl(composerM3273constructorimpl4, currentCompositionLocalMap4, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
            Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash4 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
            if (composerM3273constructorimpl4.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl4.rememberedValue(), Integer.valueOf(currentCompositeKeyHash4))) {
                composerM3273constructorimpl4.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash4));
                composerM3273constructorimpl4.apply(Integer.valueOf(currentCompositeKeyHash4), setCompositeKeyHash4);
            }
            function3ModifierMaterializerOf4.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i12 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(2058660585);
            int i13 = (i12 >> 9) & 14;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 276693656, "C79@3979L9:Column.kt#2w3rfo");
            ColumnScopeInstance columnScopeInstance2 = ColumnScopeInstance.INSTANCE;
            int i14 = ((384 >> 6) & 112) | 6;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1662963957, "C252@10146L290,259@10453L196:ClipPickerSheet.kt#wl24de");
            StringCompanionObject stringCompanionObject2 = StringCompanionObject.INSTANCE;
            String str2 = String.format(Locale.US, "%.1f%%", Arrays.copyOf(new Object[]{Double.valueOf(clipInfo.getFinalDriftPct())}, 1));
            Intrinsics.checkNotNullExpressionValue(str2, "format(...)");
            TextKt.m2461Text4IGK_g(str2, (Modifier) null, ColorKt.getEmeraldGreen(), TextUnitKt.getSp(16), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 200064, 0, 130962);
            StringCompanionObject stringCompanionObject3 = StringCompanionObject.INSTANCE;
            String str3 = String.format(Locale.US, "was %.0f%% without map", Arrays.copyOf(new Object[]{Double.valueOf(clipInfo.getFinalBasePct())}, 1));
            Intrinsics.checkNotNullExpressionValue(str3, "format(...)");
            TextKt.m2461Text4IGK_g(str3, (Modifier) null, ColorKt.getAlertRed(), TextUnitKt.getSp(10), (FontStyle) null, (FontWeight) null, (FontFamily) null, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 3456, 0, 131058);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endNode();
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endReplaceableGroup();
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endNode();
            composerStartRestartGroup.endReplaceableGroup();
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
        }
        ScopeUpdateScope scopeUpdateScopeEndRestartGroup = composerStartRestartGroup.endRestartGroup();
        if (scopeUpdateScopeEndRestartGroup != null) {
            scopeUpdateScopeEndRestartGroup.updateScope(new Function2<Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt.ClipRow.3
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                /* JADX WARN: Multi-variable type inference failed */
                {
                    super(2);
                }

                @Override // kotlin.jvm.functions.Function2
                public /* bridge */ /* synthetic */ Unit invoke(Composer composer2, Integer num) {
                    invoke(composer2, num.intValue());
                    return Unit.INSTANCE;
                }

                public final void invoke(Composer composer2, int i15) {
                    ClipPickerSheetKt.ClipRow(clipInfo, z, function1, composer2, RecomposeScopeImplKt.updateChangedFlags(i | 1));
                }
            });
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Code duplicated, block: B:82:0x0269  */
    /* JADX WARN: Code duplicated, block: B:83:0x0270  */
    /* JADX WARN: Code duplicated, block: B:86:0x02c2  */
    public static final void EngineModeTab(final EngineMode engineMode, final boolean z, final Function0<Unit> function0, Modifier modifier, Composer composer, final int i, final int i2) {
        Modifier modifier2;
        Modifier modifier3;
        Function0<ComposeUiNode> function1;
        int i3;
        long textPrimary;
        Composer composerStartRestartGroup = composer.startRestartGroup(-225268061);
        ComposerKt.sourceInformation(composerStartRestartGroup, "C(EngineModeTab)P(!1,3,2)196@8041L664:ClipPickerSheet.kt#wl24de");
        int i4 = i;
        if ((i2 & 1) != 0) {
            i4 |= 6;
        } else if ((i & 14) == 0) {
            i4 |= composerStartRestartGroup.changed(engineMode) ? 4 : 2;
        }
        if ((i2 & 2) != 0) {
            i4 |= 48;
        } else if ((i & 112) == 0) {
            i4 |= composerStartRestartGroup.changed(z) ? 32 : 16;
        }
        if ((i2 & 4) != 0) {
            i4 |= 384;
        } else if ((i & 896) == 0) {
            i4 |= composerStartRestartGroup.changedInstance(function0) ? 256 : 128;
        }
        int i5 = i2 & 8;
        if (i5 != 0) {
            i4 |= 3072;
            modifier2 = modifier;
        } else if ((i & 7168) == 0) {
            modifier2 = modifier;
            i4 |= composerStartRestartGroup.changed(modifier2) ? 2048 : 1024;
        } else {
            modifier2 = modifier;
        }
        int i6 = i4;
        if ((i6 & 5851) == 1170 && composerStartRestartGroup.getSkipping()) {
            composerStartRestartGroup.skipToGroupEnd();
            modifier3 = modifier2;
            i3 = i6;
        } else {
            Modifier.Companion companion = i5 != 0 ? Modifier.INSTANCE : modifier2;
            if (ComposerKt.isTraceInProgress()) {
                ComposerKt.traceEventStart(-225268061, i6, -1, "com.sih2026.nav.ui.components.EngineModeTab (ClipPickerSheet.kt:195)");
            }
            Modifier modifierM560paddingVpY3zN4 = PaddingKt.m560paddingVpY3zN4(ClickableKt.m241clickableXHw0xAI$default(BorderKt.m218borderxT4_qwU(BackgroundKt.m207backgroundbw27NRU$default(ClipKt.clip(companion, RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14))), z ? ColorKt.getCyanAccent() : ColorKt.getSurfaceCard(), null, 2, null), Dp.m6091constructorimpl(1), z ? ColorKt.getCyanAccent() : androidx.compose.ui.graphics.ColorKt.Color(872415231), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(14))), false, null, null, function0, 7, null), Dp.m6091constructorimpl(8), Dp.m6091constructorimpl(12));
            Alignment center = Alignment.INSTANCE.getCenter();
            composerStartRestartGroup.startReplaceableGroup(733328855);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
            MeasurePolicy measurePolicyRememberBoxMeasurePolicy = BoxKt.rememberBoxMeasurePolicy(center, false, composerStartRestartGroup, ((48 >> 3) & 14) | ((48 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(-1323940314);
            ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
            int currentCompositeKeyHash = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
            modifier3 = companion;
            CompositionLocalMap currentCompositionLocalMap = composerStartRestartGroup.getCurrentCompositionLocalMap();
            Function0<ComposeUiNode> constructor = ComposeUiNode.INSTANCE.getConstructor();
            Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf = LayoutKt.modifierMaterializerOf(modifierM560paddingVpY3zN4);
            int i7 = ((((48 << 3) & 112) << 9) & 7168) | 6;
            if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
                ComposablesKt.invalidApplier();
            }
            composerStartRestartGroup.startReusableNode();
            if (composerStartRestartGroup.getInserting()) {
                function1 = constructor;
                composerStartRestartGroup.createNode(function1);
            } else {
                function1 = constructor;
                composerStartRestartGroup.useNode();
            }
            Composer composerM3273constructorimpl = Updater.m3273constructorimpl(composerStartRestartGroup);
            Updater.m3280setimpl(composerM3273constructorimpl, measurePolicyRememberBoxMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
            Updater.m3280setimpl(composerM3273constructorimpl, currentCompositionLocalMap, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
            Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
            if (composerM3273constructorimpl.getInserting()) {
                i3 = i6;
            } else {
                i3 = i6;
                if (!Intrinsics.areEqual(composerM3273constructorimpl.rememberedValue(), Integer.valueOf(currentCompositeKeyHash))) {
                }
                function3ModifierMaterializerOf.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i7 >> 3) & 112));
                composerStartRestartGroup.startReplaceableGroup(2058660585);
                int i8 = (i7 >> 9) & 14;
                ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
                BoxScopeInstance boxScopeInstance = BoxScopeInstance.INSTANCE;
                int i9 = ((48 >> 6) & 112) | 6;
                ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -189924733, "C205@8450L249:ClipPickerSheet.kt#wl24de");
                String label = engineMode.getLabel();
                Locale US = Locale.US;
                Intrinsics.checkNotNullExpressionValue(US, "US");
                String upperCase = label.toUpperCase(US);
                Intrinsics.checkNotNullExpressionValue(upperCase, "toUpperCase(...)");
                GenericFontFamily monospace = FontFamily.INSTANCE.getMonospace();
                long sp = TextUnitKt.getSp(11);
                FontWeight bold = FontWeight.INSTANCE.getBold();
                if (z) {
                    textPrimary = Color.INSTANCE.m3769getBlack0d7_KjU();
                } else {
                    textPrimary = ColorKt.getTextPrimary();
                }
                TextKt.m2461Text4IGK_g(upperCase, (Modifier) null, textPrimary, sp, (FontStyle) null, bold, (FontFamily) monospace, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 199680, 0, 130962);
                ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
                ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
                composerStartRestartGroup.endReplaceableGroup();
                composerStartRestartGroup.endNode();
                composerStartRestartGroup.endReplaceableGroup();
                composerStartRestartGroup.endReplaceableGroup();
                if (ComposerKt.isTraceInProgress()) {
                    ComposerKt.traceEventEnd();
                }
            }
            composerM3273constructorimpl.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash));
            composerM3273constructorimpl.apply(Integer.valueOf(currentCompositeKeyHash), setCompositeKeyHash);
            function3ModifierMaterializerOf.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i7 >> 3) & 112));
            composerStartRestartGroup.startReplaceableGroup(2058660585);
            int i10 = (i7 >> 9) & 14;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
            BoxScopeInstance boxScopeInstance2 = BoxScopeInstance.INSTANCE;
            int i11 = ((48 >> 6) & 112) | 6;
            ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -189924733, "C205@8450L249:ClipPickerSheet.kt#wl24de");
            String label2 = engineMode.getLabel();
            Locale US2 = Locale.US;
            Intrinsics.checkNotNullExpressionValue(US2, "US");
            String upperCase2 = label2.toUpperCase(US2);
            Intrinsics.checkNotNullExpressionValue(upperCase2, "toUpperCase(...)");
            GenericFontFamily monospace2 = FontFamily.INSTANCE.getMonospace();
            long sp2 = TextUnitKt.getSp(11);
            FontWeight bold2 = FontWeight.INSTANCE.getBold();
            if (z) {
                textPrimary = Color.INSTANCE.m3769getBlack0d7_KjU();
            } else {
                textPrimary = ColorKt.getTextPrimary();
            }
            TextKt.m2461Text4IGK_g(upperCase2, (Modifier) null, textPrimary, sp2, (FontStyle) null, bold2, (FontFamily) monospace2, 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 199680, 0, 130962);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endNode();
            composerStartRestartGroup.endReplaceableGroup();
            composerStartRestartGroup.endReplaceableGroup();
            if (ComposerKt.isTraceInProgress()) {
                ComposerKt.traceEventEnd();
            }
        }
        ScopeUpdateScope scopeUpdateScopeEndRestartGroup = composerStartRestartGroup.endRestartGroup();
        if (scopeUpdateScopeEndRestartGroup != null) {
            final Modifier modifier4 = modifier3;
            scopeUpdateScopeEndRestartGroup.updateScope(new Function2<Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.ClipPickerSheetKt.EngineModeTab.2
                /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
                {
                    super(2);
                }

                @Override // kotlin.jvm.functions.Function2
                public /* bridge */ /* synthetic */ Unit invoke(Composer composer2, Integer num) {
                    invoke(composer2, num.intValue());
                    return Unit.INSTANCE;
                }

                public final void invoke(Composer composer2, int i12) {
                    ClipPickerSheetKt.EngineModeTab(engineMode, z, function0, modifier4, composer2, RecomposeScopeImplKt.updateChangedFlags(i | 1), i2);
                }
            });
        }
    }
}
