package com.sih2026.nav.ui.components;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.DashPathEffect;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.drawable.BitmapDrawable;
import android.view.MotionEvent;
import androidx.compose.animation.AnimatedVisibilityKt;
import androidx.compose.animation.AnimatedVisibilityScope;
import androidx.compose.animation.EnterExitTransitionKt;
import androidx.compose.foundation.BackgroundKt;
import androidx.compose.foundation.BorderKt;
import androidx.compose.foundation.ClickableKt;
import androidx.compose.foundation.layout.Arrangement;
import androidx.compose.foundation.layout.BoxKt;
import androidx.compose.foundation.layout.BoxScopeInstance;
import androidx.compose.foundation.layout.PaddingKt;
import androidx.compose.foundation.layout.RowKt;
import androidx.compose.foundation.layout.RowScopeInstance;
import androidx.compose.foundation.layout.SizeKt;
import androidx.compose.foundation.layout.SpacerKt;
import androidx.compose.foundation.shape.RoundedCornerShapeKt;
import androidx.compose.material.icons.Icons;
import androidx.compose.material.icons.filled.CompassCalibrationKt;
import androidx.compose.material.icons.filled.MyLocationKt;
import androidx.compose.material.icons.filled.NavigationKt;
import androidx.compose.material3.IconKt;
import androidx.compose.material3.TextKt;
import androidx.compose.runtime.Applier;
import androidx.compose.runtime.ComposablesKt;
import androidx.compose.runtime.Composer;
import androidx.compose.runtime.ComposerKt;
import androidx.compose.runtime.CompositionLocalMap;
import androidx.compose.runtime.DisposableEffectResult;
import androidx.compose.runtime.DisposableEffectScope;
import androidx.compose.runtime.EffectsKt;
import androidx.compose.runtime.MutableFloatState;
import androidx.compose.runtime.MutableState;
import androidx.compose.runtime.PrimitiveSnapshotStateKt;
import androidx.compose.runtime.ProvidableCompositionLocal;
import androidx.compose.runtime.RecomposeScopeImplKt;
import androidx.compose.runtime.ScopeUpdateScope;
import androidx.compose.runtime.SkippableUpdater;
import androidx.compose.runtime.SnapshotStateKt__SnapshotStateKt;
import androidx.compose.runtime.Updater;
import androidx.compose.runtime.internal.ComposableLambdaKt;
import androidx.compose.ui.Alignment;
import androidx.compose.ui.Modifier;
import androidx.compose.ui.draw.ClipKt;
import androidx.compose.ui.layout.LayoutKt;
import androidx.compose.ui.layout.MeasurePolicy;
import androidx.compose.ui.node.ComposeUiNode;
import androidx.compose.ui.platform.AndroidCompositionLocals_androidKt;
import androidx.compose.ui.text.TextLayoutResult;
import androidx.compose.ui.text.TextStyle;
import androidx.compose.ui.text.font.FontFamily;
import androidx.compose.ui.text.font.FontStyle;
import androidx.compose.ui.text.font.FontWeight;
import androidx.compose.ui.text.style.TextAlign;
import androidx.compose.ui.text.style.TextDecoration;
import androidx.compose.ui.unit.Dp;
import androidx.compose.ui.unit.TextUnitKt;
import androidx.compose.ui.viewinterop.AndroidView_androidKt;
import com.sih2026.nav.data.model.NavState;
import com.sih2026.nav.ui.theme.ColorKt;
import com.sih2026.nav.ui.utils.HeadingInterpolator;
import java.util.List;
import kotlin.Metadata;
import kotlin.ResultKt;
import kotlin.Unit;
import kotlin.collections.CollectionsKt;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.intrinsics.IntrinsicsKt;
import kotlin.coroutines.jvm.internal.DebugMetadata;
import kotlin.coroutines.jvm.internal.SuspendLambda;
import kotlin.jvm.functions.Function0;
import kotlin.jvm.functions.Function1;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.functions.Function3;
import kotlin.jvm.internal.Intrinsics;
import kotlinx.coroutines.CoroutineScope;
import org.osmdroid.api.IMapController;
import org.osmdroid.config.Configuration;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.Marker;
import org.osmdroid.views.overlay.Overlay;
import org.osmdroid.views.overlay.Polygon;
import org.osmdroid.views.overlay.Polyline;

/* JADX INFO: compiled from: MapViewContainer.kt */
/* JADX INFO: loaded from: classes7.dex */
@Metadata(d1 = {"\u0000J\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\u0007\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0007\u001aa\u0010\u0000\u001a\u00020\u00012\u0006\u0010\u0002\u001a\u00020\u00032\u0006\u0010\u0004\u001a\u00020\u00032\u0006\u0010\u0005\u001a\u00020\u00062\f\u0010\u0007\u001a\b\u0012\u0004\u0012\u00020\t0\b2\f\u0010\n\u001a\b\u0012\u0004\u0012\u00020\t0\b2\f\u0010\u000b\u001a\b\u0012\u0004\u0012\u00020\t0\b2\u0006\u0010\f\u001a\u00020\u00062\b\b\u0002\u0010\r\u001a\u00020\u000eH\u0007¢\u0006\u0002\u0010\u000f\u001a\u000e\u0010\u0010\u001a\u00020\u00112\u0006\u0010\u0012\u001a\u00020\u0013\u001a\u0010\u0010\u0014\u001a\u00020\u00152\u0006\u0010\u0016\u001a\u00020\u0017H\u0002\u001a\u0018\u0010\u0018\u001a\u00020\u00192\u0006\u0010\u001a\u001a\u00020\u00112\u0006\u0010\u001b\u001a\u00020\u0013H\u0002\u001a\u0010\u0010\u001c\u001a\u00020\u00152\u0006\u0010\u0016\u001a\u00020\u0017H\u0002¨\u0006\u001d²\u0006\n\u0010\u001e\u001a\u00020\u0006X\u008a\u008e\u0002²\u0006\n\u0010\u001f\u001a\u00020\u0006X\u008a\u008e\u0002²\u0006\n\u0010 \u001a\u00020\u0013X\u008a\u008e\u0002"}, d2 = {"MapViewContainer", "", "estimate", "Lcom/sih2026/nav/data/model/NavState;", "truth", "inBlackout", "", "truePath", "", "Lorg/osmdroid/util/GeoPoint;", "estimatePath", "noMapPath", "showNoMap", "modifier", "Landroidx/compose/ui/Modifier;", "(Lcom/sih2026/nav/data/model/NavState;Lcom/sih2026/nav/data/model/NavState;ZLjava/util/List;Ljava/util/List;Ljava/util/List;ZLandroidx/compose/ui/Modifier;Landroidx/compose/runtime/Composer;II)V", "cardinal", "", "headingDeg", "", "estimateArrow", "Landroid/graphics/drawable/BitmapDrawable;", "context", "Landroid/content/Context;", "trail", "Lorg/osmdroid/views/overlay/Polyline;", "colour", "width", "truthPuck", "app_debug", "isAutoCenter", "isHeadingUp", "smoothMapOrientation"}, k = 2, mv = {1, 9, 0}, xi = 48)
public final class MapViewContainerKt {

    /* JADX INFO: renamed from: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$1, reason: invalid class name */
    /* JADX INFO: compiled from: MapViewContainer.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$1", f = "MapViewContainer.kt", i = {}, l = {}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass1 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        final /* synthetic */ Context $context;
        int label;

        /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
        AnonymousClass1(Context context, Continuation<? super AnonymousClass1> continuation) {
            super(2, continuation);
            this.$context = context;
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return new AnonymousClass1(this.$context, continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass1) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    Configuration.getInstance().setUserAgentValue(this.$context.getPackageName());
                    return Unit.INSTANCE;
                default:
                    throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
            }
        }
    }

    /* JADX INFO: renamed from: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$2, reason: invalid class name */
    /* JADX INFO: compiled from: MapViewContainer.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$2", f = "MapViewContainer.kt", i = {}, l = {}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass2 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        final /* synthetic */ Polygon $errorCircle;
        final /* synthetic */ Marker $estimateMarker;
        final /* synthetic */ Polyline $estimatePolyline;
        final /* synthetic */ MapView $mapView;
        final /* synthetic */ Polyline $noMapPolyline;
        final /* synthetic */ MapViewContainerKt$MapViewContainer$touchOverlay$1$1 $touchOverlay;
        final /* synthetic */ Polyline $truePolyline;
        final /* synthetic */ Marker $truthMarker;
        int label;

        /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
        AnonymousClass2(MapView mapView, MapViewContainerKt$MapViewContainer$touchOverlay$1$1 mapViewContainerKt$MapViewContainer$touchOverlay$1$1, Polyline polyline, Polyline polyline2, Polyline polyline3, Polygon polygon, Marker marker, Marker marker2, Continuation<? super AnonymousClass2> continuation) {
            super(2, continuation);
            this.$mapView = mapView;
            this.$touchOverlay = mapViewContainerKt$MapViewContainer$touchOverlay$1$1;
            this.$noMapPolyline = polyline;
            this.$truePolyline = polyline2;
            this.$estimatePolyline = polyline3;
            this.$errorCircle = polygon;
            this.$truthMarker = marker;
            this.$estimateMarker = marker2;
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return new AnonymousClass2(this.$mapView, this.$touchOverlay, this.$noMapPolyline, this.$truePolyline, this.$estimatePolyline, this.$errorCircle, this.$truthMarker, this.$estimateMarker, continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass2) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    this.$mapView.getOverlays().add(this.$touchOverlay);
                    this.$mapView.getOverlays().add(this.$noMapPolyline);
                    this.$mapView.getOverlays().add(this.$truePolyline);
                    this.$mapView.getOverlays().add(this.$estimatePolyline);
                    this.$mapView.getOverlays().add(this.$errorCircle);
                    this.$mapView.getOverlays().add(this.$truthMarker);
                    this.$mapView.getOverlays().add(this.$estimateMarker);
                    return Unit.INSTANCE;
                default:
                    throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
            }
        }
    }

    /* JADX INFO: renamed from: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$3, reason: invalid class name */
    /* JADX INFO: compiled from: MapViewContainer.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$3", f = "MapViewContainer.kt", i = {}, l = {}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass3 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        final /* synthetic */ List<GeoPoint> $estimatePath;
        final /* synthetic */ Polyline $estimatePolyline;
        final /* synthetic */ MapView $mapView;
        final /* synthetic */ List<GeoPoint> $noMapPath;
        final /* synthetic */ Polyline $noMapPolyline;
        final /* synthetic */ boolean $showNoMap;
        final /* synthetic */ List<GeoPoint> $truePath;
        final /* synthetic */ Polyline $truePolyline;
        int label;

        /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
        /* JADX WARN: Multi-variable type inference failed */
        AnonymousClass3(Polyline polyline, List<? extends GeoPoint> list, Polyline polyline2, List<? extends GeoPoint> list2, Polyline polyline3, boolean z, List<? extends GeoPoint> list3, MapView mapView, Continuation<? super AnonymousClass3> continuation) {
            super(2, continuation);
            this.$truePolyline = polyline;
            this.$truePath = list;
            this.$estimatePolyline = polyline2;
            this.$estimatePath = list2;
            this.$noMapPolyline = polyline3;
            this.$showNoMap = z;
            this.$noMapPath = list3;
            this.$mapView = mapView;
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return new AnonymousClass3(this.$truePolyline, this.$truePath, this.$estimatePolyline, this.$estimatePath, this.$noMapPolyline, this.$showNoMap, this.$noMapPath, this.$mapView, continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass3) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    this.$truePolyline.setPoints(this.$truePath);
                    this.$estimatePolyline.setPoints(this.$estimatePath);
                    this.$noMapPolyline.setPoints(this.$showNoMap ? this.$noMapPath : CollectionsKt.emptyList());
                    this.$mapView.invalidate();
                    return Unit.INSTANCE;
                default:
                    throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
            }
        }
    }

    /* JADX INFO: renamed from: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$4, reason: invalid class name */
    /* JADX INFO: compiled from: MapViewContainer.kt */
    @Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0010\u0002\n\u0002\u0018\u0002\u0010\u0000\u001a\u00020\u0001*\u00020\u0002H\u008a@"}, d2 = {"<anonymous>", "", "Lkotlinx/coroutines/CoroutineScope;"}, k = 3, mv = {1, 9, 0}, xi = 48)
    @DebugMetadata(c = "com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$4", f = "MapViewContainer.kt", i = {}, l = {}, m = "invokeSuspend", n = {}, s = {})
    static final class AnonymousClass4 extends SuspendLambda implements Function2<CoroutineScope, Continuation<? super Unit>, Object> {
        final /* synthetic */ Polygon $errorCircle;
        final /* synthetic */ NavState $estimate;
        final /* synthetic */ Marker $estimateMarker;
        final /* synthetic */ boolean $inBlackout;
        final /* synthetic */ MutableState<Boolean> $isAutoCenter$delegate;
        final /* synthetic */ MutableState<Boolean> $isHeadingUp$delegate;
        final /* synthetic */ MapView $mapView;
        final /* synthetic */ MutableFloatState $smoothMapOrientation$delegate;
        final /* synthetic */ NavState $truth;
        final /* synthetic */ Marker $truthMarker;
        int label;

        /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
        AnonymousClass4(NavState navState, NavState navState2, Marker marker, Marker marker2, MapView mapView, Polygon polygon, boolean z, MutableState<Boolean> mutableState, MutableFloatState mutableFloatState, MutableState<Boolean> mutableState2, Continuation<? super AnonymousClass4> continuation) {
            super(2, continuation);
            this.$estimate = navState;
            this.$truth = navState2;
            this.$estimateMarker = marker;
            this.$truthMarker = marker2;
            this.$mapView = mapView;
            this.$errorCircle = polygon;
            this.$inBlackout = z;
            this.$isHeadingUp$delegate = mutableState;
            this.$smoothMapOrientation$delegate = mutableFloatState;
            this.$isAutoCenter$delegate = mutableState2;
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Continuation<Unit> create(Object obj, Continuation<?> continuation) {
            return new AnonymousClass4(this.$estimate, this.$truth, this.$estimateMarker, this.$truthMarker, this.$mapView, this.$errorCircle, this.$inBlackout, this.$isHeadingUp$delegate, this.$smoothMapOrientation$delegate, this.$isAutoCenter$delegate, continuation);
        }

        @Override // kotlin.jvm.functions.Function2
        public final Object invoke(CoroutineScope coroutineScope, Continuation<? super Unit> continuation) {
            return ((AnonymousClass4) create(coroutineScope, continuation)).invokeSuspend(Unit.INSTANCE);
        }

        @Override // kotlin.coroutines.jvm.internal.BaseContinuationImpl
        public final Object invokeSuspend(Object obj) {
            double d;
            IntrinsicsKt.getCOROUTINE_SUSPENDED();
            switch (this.label) {
                case 0:
                    ResultKt.throwOnFailure(obj);
                    GeoPoint geoPoint = new GeoPoint(this.$estimate.getLat(), this.$estimate.getLon());
                    GeoPoint geoPoint2 = new GeoPoint(this.$truth.getLat(), this.$truth.getLon());
                    this.$estimateMarker.setPosition(geoPoint);
                    this.$truthMarker.setPosition(geoPoint2);
                    this.$truthMarker.setRotation(0.0f);
                    if (MapViewContainerKt.MapViewContainer$lambda$4(this.$isHeadingUp$delegate)) {
                        MapViewContainerKt.MapViewContainer$lambda$8(this.$smoothMapOrientation$delegate, HeadingInterpolator.INSTANCE.lerpAngleShortestPath(MapViewContainerKt.MapViewContainer$lambda$7(this.$smoothMapOrientation$delegate), ((-this.$estimate.getHeadingDeg()) + 360.0f) % 360.0f, 0.08f));
                        this.$mapView.setMapOrientation(MapViewContainerKt.MapViewContainer$lambda$7(this.$smoothMapOrientation$delegate));
                        this.$estimateMarker.setRotation(((this.$estimate.getHeadingDeg() + MapViewContainerKt.MapViewContainer$lambda$7(this.$smoothMapOrientation$delegate)) + 360.0f) % 360.0f);
                    } else {
                        MapViewContainerKt.MapViewContainer$lambda$8(this.$smoothMapOrientation$delegate, 0.0f);
                        this.$mapView.setMapOrientation(0.0f);
                        this.$estimateMarker.setRotation(this.$estimate.getHeadingDeg());
                    }
                    double dDistanceToAsDouble = geoPoint.distanceToAsDouble(geoPoint2);
                    this.$errorCircle.setPoints((!this.$inBlackout || dDistanceToAsDouble <= 3.0d) ? CollectionsKt.emptyList() : Polygon.pointsAsCircle(geoPoint, dDistanceToAsDouble));
                    if (MapViewContainerKt.MapViewContainer$lambda$1(this.$isAutoCenter$delegate)) {
                        double d2 = 2;
                        GeoPoint geoPoint3 = new GeoPoint((this.$estimate.getLat() + this.$truth.getLat()) / d2, (this.$estimate.getLon() + this.$truth.getLon()) / d2);
                        IMapController controller = this.$mapView.getController();
                        if (this.$inBlackout) {
                            geoPoint = geoPoint3;
                        }
                        controller.setCenter(geoPoint);
                        IMapController controller2 = this.$mapView.getController();
                        if (!this.$inBlackout || dDistanceToAsDouble < 80.0d) {
                            d = 17.5d;
                        } else if (dDistanceToAsDouble < 250.0d) {
                            d = 16.5d;
                        } else if (dDistanceToAsDouble < 600.0d) {
                            d = 15.5d;
                        } else {
                            d = dDistanceToAsDouble < 1200.0d ? 14.5d : 13.5d;
                        }
                        controller2.setZoom(d);
                    }
                    this.$mapView.invalidate();
                    return Unit.INSTANCE;
                default:
                    throw new IllegalStateException("call to 'resume' before 'invoke' with coroutine");
            }
        }
    }

    public static final void MapViewContainer(final NavState estimate, final NavState truth, final boolean z, final List<? extends GeoPoint> truePath, final List<? extends GeoPoint> estimatePath, final List<? extends GeoPoint> noMapPath, final boolean z2, Modifier modifier, Composer composer, final int i, final int i2) {
        Object objMutableStateOf$default;
        Object objMutableStateOf$default2;
        Object objMutableFloatStateOf;
        Object obj;
        Object obj2;
        Object obj3;
        Object obj4;
        Object obj5;
        Object objTrail;
        Object objTrail2;
        boolean z3;
        Object obj6;
        Function0<ComposeUiNode> function0;
        Function0<ComposeUiNode> function1;
        Function0<ComposeUiNode> function2;
        Function0<ComposeUiNode> function3;
        Function0<ComposeUiNode> function4;
        Intrinsics.checkNotNullParameter(estimate, "estimate");
        Intrinsics.checkNotNullParameter(truth, "truth");
        Intrinsics.checkNotNullParameter(truePath, "truePath");
        Intrinsics.checkNotNullParameter(estimatePath, "estimatePath");
        Intrinsics.checkNotNullParameter(noMapPath, "noMapPath");
        Composer composerStartRestartGroup = composer.startRestartGroup(459019525);
        ComposerKt.sourceInformation(composerStartRestartGroup, "C(MapViewContainer)P(!1,7,2,6!1,4,5)81@3280L7,82@3312L33,83@3369L34,84@3491L36,86@3533L101,90@3654L259,99@3938L350,110@4312L213,118@4552L230,127@4911L224,135@5160L36,136@5224L36,137@5285L163,143@5454L337,153@5797L262,160@6065L1653,199@7724L71,203@7801L2678:MapViewContainer.kt#wl24de");
        Modifier modifier2 = (i2 & 128) != 0 ? Modifier.INSTANCE : modifier;
        if (ComposerKt.isTraceInProgress()) {
            ComposerKt.traceEventStart(459019525, i, -1, "com.sih2026.nav.ui.components.MapViewContainer (MapViewContainer.kt:80)");
        }
        ProvidableCompositionLocal<Context> localContext = AndroidCompositionLocals_androidKt.getLocalContext();
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 2023513938, "CC:CompositionLocal.kt#9igjgp");
        Object objConsume = composerStartRestartGroup.consume(localContext);
        ComposerKt.sourceInformationMarkerEnd(composerStartRestartGroup);
        Context context = (Context) objConsume;
        composerStartRestartGroup.startReplaceableGroup(376343520);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue == Composer.INSTANCE.getEmpty()) {
            objMutableStateOf$default = SnapshotStateKt__SnapshotStateKt.mutableStateOf$default(true, null, 2, null);
            composerStartRestartGroup.updateRememberedValue(objMutableStateOf$default);
        } else {
            objMutableStateOf$default = objRememberedValue;
        }
        final MutableState mutableState = (MutableState) objMutableStateOf$default;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376343577);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue2 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue2 == Composer.INSTANCE.getEmpty()) {
            objMutableStateOf$default2 = SnapshotStateKt__SnapshotStateKt.mutableStateOf$default(false, null, 2, null);
            composerStartRestartGroup.updateRememberedValue(objMutableStateOf$default2);
        } else {
            objMutableStateOf$default2 = objRememberedValue2;
        }
        final MutableState mutableState2 = (MutableState) objMutableStateOf$default2;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376343699);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue3 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue3 == Composer.INSTANCE.getEmpty()) {
            objMutableFloatStateOf = PrimitiveSnapshotStateKt.mutableFloatStateOf(0.0f);
            composerStartRestartGroup.updateRememberedValue(objMutableFloatStateOf);
        } else {
            objMutableFloatStateOf = objRememberedValue3;
        }
        MutableFloatState mutableFloatState = (MutableFloatState) objMutableFloatStateOf;
        composerStartRestartGroup.endReplaceableGroup();
        EffectsKt.LaunchedEffect(Unit.INSTANCE, new AnonymousClass1(context, null), composerStartRestartGroup, 70);
        composerStartRestartGroup.startReplaceableGroup(376343862);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue4 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue4 == Composer.INSTANCE.getEmpty()) {
            MapView mapView = new MapView(context);
            mapView.setTileSource(TileSourceFactory.MAPNIK);
            mapView.setMultiTouchControls(true);
            mapView.getController().setZoom(17.5d);
            mapView.getController().setCenter(new GeoPoint(estimate.getLat(), estimate.getLon()));
            obj = mapView;
            composerStartRestartGroup.updateRememberedValue(obj);
        } else {
            obj = objRememberedValue4;
        }
        final MapView mapView2 = (MapView) obj;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376344146);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue5 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue5 == Composer.INSTANCE.getEmpty()) {
            obj2 = new Overlay() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$touchOverlay$1$1
                @Override // org.osmdroid.views.overlay.Overlay
                public boolean onTouchEvent(MotionEvent event, MapView mapView3) {
                    Intrinsics.checkNotNullParameter(event, "event");
                    Intrinsics.checkNotNullParameter(mapView3, "mapView");
                    if (event.getAction() == 0 || event.getAction() == 2) {
                        MapViewContainerKt.MapViewContainer$lambda$2(mutableState, false);
                    }
                    return false;
                }
            };
            composerStartRestartGroup.updateRememberedValue(obj2);
        } else {
            obj2 = objRememberedValue5;
        }
        MapViewContainerKt$MapViewContainer$touchOverlay$1$1 mapViewContainerKt$MapViewContainer$touchOverlay$1$1 = (MapViewContainerKt$MapViewContainer$touchOverlay$1$1) obj2;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376344520);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue6 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue6 == Composer.INSTANCE.getEmpty()) {
            Marker marker = new Marker(mapView2);
            marker.setAnchor(0.5f, 0.5f);
            marker.setTitle("True position (vehicle GNSS)");
            marker.setIcon(truthPuck(context));
            obj3 = marker;
            composerStartRestartGroup.updateRememberedValue(obj3);
        } else {
            obj3 = objRememberedValue6;
        }
        Marker marker2 = (Marker) obj3;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376344760);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue7 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue7 == Composer.INSTANCE.getEmpty()) {
            Marker marker3 = new Marker(mapView2);
            marker3.setAnchor(0.5f, 0.5f);
            marker3.setTitle("Estimated position (dead reckoning + map)");
            marker3.setIcon(estimateArrow(context));
            composerStartRestartGroup.updateRememberedValue(marker3);
            obj4 = marker3;
        } else {
            obj4 = objRememberedValue7;
        }
        Marker marker4 = (Marker) obj4;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376345119);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue8 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue8 == Composer.INSTANCE.getEmpty()) {
            Polygon polygon = new Polygon(mapView2);
            polygon.getFillPaint().setColor(Color.parseColor("#22F59E0B"));
            polygon.getOutlinePaint().setColor(Color.parseColor("#88F59E0B"));
            polygon.getOutlinePaint().setStrokeWidth(3.0f);
            composerStartRestartGroup.updateRememberedValue(polygon);
            obj5 = polygon;
        } else {
            obj5 = objRememberedValue8;
        }
        Polygon polygon2 = (Polygon) obj5;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376345368);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue9 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue9 == Composer.INSTANCE.getEmpty()) {
            objTrail = trail("#FF10B981", 13.0f);
            composerStartRestartGroup.updateRememberedValue(objTrail);
        } else {
            objTrail = objRememberedValue9;
        }
        Polyline polyline = (Polyline) objTrail;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376345432);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue10 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue10 == Composer.INSTANCE.getEmpty()) {
            objTrail2 = trail("#FF06B6D4", 11.0f);
            composerStartRestartGroup.updateRememberedValue(objTrail2);
        } else {
            objTrail2 = objRememberedValue10;
        }
        Polyline polyline2 = (Polyline) objTrail2;
        composerStartRestartGroup.endReplaceableGroup();
        composerStartRestartGroup.startReplaceableGroup(376345493);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(remember):MapViewContainer.kt#9igjgp");
        Object objRememberedValue11 = composerStartRestartGroup.rememberedValue();
        if (objRememberedValue11 == Composer.INSTANCE.getEmpty()) {
            Polyline polylineTrail = trail("#FFEF4444", 7.0f);
            z3 = false;
            polylineTrail.getOutlinePaint().setPathEffect(new DashPathEffect(new float[]{14.0f, 12.0f}, 0.0f));
            composerStartRestartGroup.updateRememberedValue(polylineTrail);
            obj6 = polylineTrail;
        } else {
            z3 = false;
            obj6 = objRememberedValue11;
        }
        Polyline polyline3 = (Polyline) obj6;
        composerStartRestartGroup.endReplaceableGroup();
        EffectsKt.LaunchedEffect(mapView2, new AnonymousClass2(mapView2, mapViewContainerKt$MapViewContainer$touchOverlay$1$1, polyline3, polyline, polyline2, polygon2, marker2, marker4, null), composerStartRestartGroup, 72);
        EffectsKt.LaunchedEffect(new Object[]{truePath, estimatePath, noMapPath, Boolean.valueOf(z2)}, (Function2<? super CoroutineScope, ? super Continuation<? super Unit>, ? extends Object>) new AnonymousClass3(polyline, truePath, polyline2, estimatePath, polyline3, z2, noMapPath, mapView2, null), composerStartRestartGroup, 72);
        EffectsKt.LaunchedEffect(new Object[]{estimate, truth, Boolean.valueOf(z), Boolean.valueOf(MapViewContainer$lambda$1(mutableState)), Boolean.valueOf(MapViewContainer$lambda$4(mutableState2))}, (Function2<? super CoroutineScope, ? super Continuation<? super Unit>, ? extends Object>) new AnonymousClass4(estimate, truth, marker4, marker2, mapView2, polygon2, z, mutableState2, mutableFloatState, mutableState, null), composerStartRestartGroup, 72);
        EffectsKt.DisposableEffect(Unit.INSTANCE, new Function1<DisposableEffectScope, DisposableEffectResult>() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt.MapViewContainer.5
            {
                super(1);
            }

            @Override // kotlin.jvm.functions.Function1
            public final DisposableEffectResult invoke(DisposableEffectScope DisposableEffect) {
                Intrinsics.checkNotNullParameter(DisposableEffect, "$this$DisposableEffect");
                final MapView mapView3 = mapView2;
                return new DisposableEffectResult() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$5$invoke$$inlined$onDispose$1
                    @Override // androidx.compose.runtime.DisposableEffectResult
                    public void dispose() {
                        mapView3.onDetach();
                    }
                };
            }
        }, composerStartRestartGroup, 6);
        int i3 = (i >> 21) & 14;
        composerStartRestartGroup.startReplaceableGroup(733328855);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
        MeasurePolicy measurePolicyRememberBoxMeasurePolicy = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composerStartRestartGroup, ((i3 >> 3) & 14) | ((i3 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(-1323940314);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
        int currentCompositeKeyHash = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
        CompositionLocalMap currentCompositionLocalMap = composerStartRestartGroup.getCurrentCompositionLocalMap();
        Function0<ComposeUiNode> constructor = ComposeUiNode.INSTANCE.getConstructor();
        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf = LayoutKt.modifierMaterializerOf(modifier2);
        int i4 = ((((i3 << 3) & 112) << 9) & 7168) | 6;
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
        function3ModifierMaterializerOf.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i4 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(2058660585);
        int i5 = (i4 >> 9) & 14;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
        int i6 = ((i3 >> 6) & 112) | 6;
        BoxScopeInstance boxScopeInstance = BoxScopeInstance.INSTANCE;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1301366867, "C204@7836L73,206@7919L2554:MapViewContainer.kt#wl24de");
        AndroidView_androidKt.AndroidView(new Function1<Context, MapView>() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$6$1
            {
                super(1);
            }

            @Override // kotlin.jvm.functions.Function1
            public final MapView invoke(Context it) {
                Intrinsics.checkNotNullParameter(it, "it");
                return mapView2;
            }
        }, boxScopeInstance.matchParentSize(Modifier.INSTANCE), null, composerStartRestartGroup, 0, 4);
        Modifier modifierM563paddingqDBjuR0$default = PaddingKt.m563paddingqDBjuR0$default(boxScopeInstance.align(Modifier.INSTANCE, Alignment.INSTANCE.getBottomEnd()), 0.0f, 0.0f, Dp.m6091constructorimpl(20), Dp.m6091constructorimpl(190), 3, null);
        composerStartRestartGroup.startReplaceableGroup(733328855);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
        MeasurePolicy measurePolicyRememberBoxMeasurePolicy2 = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composerStartRestartGroup, ((0 >> 3) & 14) | ((0 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(-1323940314);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
        int currentCompositeKeyHash2 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
        CompositionLocalMap currentCompositionLocalMap2 = composerStartRestartGroup.getCurrentCompositionLocalMap();
        Function0<ComposeUiNode> constructor2 = ComposeUiNode.INSTANCE.getConstructor();
        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf2 = LayoutKt.modifierMaterializerOf(modifierM563paddingqDBjuR0$default);
        int i7 = ((((0 << 3) & 112) << 9) & 7168) | 6;
        if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
            ComposablesKt.invalidApplier();
        }
        composerStartRestartGroup.startReusableNode();
        if (composerStartRestartGroup.getInserting()) {
            function1 = constructor2;
            composerStartRestartGroup.createNode(function1);
        } else {
            function1 = constructor2;
            composerStartRestartGroup.useNode();
        }
        Composer composerM3273constructorimpl2 = Updater.m3273constructorimpl(composerStartRestartGroup);
        Updater.m3280setimpl(composerM3273constructorimpl2, measurePolicyRememberBoxMeasurePolicy2, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
        Updater.m3280setimpl(composerM3273constructorimpl2, currentCompositionLocalMap2, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash2 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
        if (composerM3273constructorimpl2.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl2.rememberedValue(), Integer.valueOf(currentCompositeKeyHash2))) {
            composerM3273constructorimpl2.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash2));
            composerM3273constructorimpl2.apply(Integer.valueOf(currentCompositeKeyHash2), setCompositeKeyHash2);
        }
        function3ModifierMaterializerOf2.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i7 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(2058660585);
        int i8 = (i7 >> 9) & 14;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
        BoxScopeInstance boxScopeInstance2 = BoxScopeInstance.INSTANCE;
        int i9 = ((0 >> 6) & 112) | 6;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 1543219521, "C211@8079L2384:MapViewContainer.kt#wl24de");
        Arrangement.HorizontalOrVertical horizontalOrVerticalM468spacedBy0680j_4 = Arrangement.INSTANCE.m468spacedBy0680j_4(Dp.m6091constructorimpl(10));
        Alignment.Vertical centerVertically = Alignment.INSTANCE.getCenterVertically();
        composerStartRestartGroup.startReplaceableGroup(693286680);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Row)P(2,1,3)90@4553L58,91@4616L130:Row.kt#2w3rfo");
        Modifier.Companion companion = Modifier.INSTANCE;
        MeasurePolicy measurePolicyRowMeasurePolicy = RowKt.rowMeasurePolicy(horizontalOrVerticalM468spacedBy0680j_4, centerVertically, composerStartRestartGroup, ((432 >> 3) & 14) | ((432 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(-1323940314);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
        int currentCompositeKeyHash3 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
        CompositionLocalMap currentCompositionLocalMap3 = composerStartRestartGroup.getCurrentCompositionLocalMap();
        Function0<ComposeUiNode> constructor3 = ComposeUiNode.INSTANCE.getConstructor();
        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf3 = LayoutKt.modifierMaterializerOf(companion);
        int i10 = ((((432 << 3) & 112) << 9) & 7168) | 6;
        if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
            ComposablesKt.invalidApplier();
        }
        composerStartRestartGroup.startReusableNode();
        if (composerStartRestartGroup.getInserting()) {
            function2 = constructor3;
            composerStartRestartGroup.createNode(function2);
        } else {
            function2 = constructor3;
            composerStartRestartGroup.useNode();
        }
        Composer composerM3273constructorimpl3 = Updater.m3273constructorimpl(composerStartRestartGroup);
        Updater.m3280setimpl(composerM3273constructorimpl3, measurePolicyRowMeasurePolicy, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
        Updater.m3280setimpl(composerM3273constructorimpl3, currentCompositionLocalMap3, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash3 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
        if (composerM3273constructorimpl3.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl3.rememberedValue(), Integer.valueOf(currentCompositeKeyHash3))) {
            composerM3273constructorimpl3.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash3));
            composerM3273constructorimpl3.apply(Integer.valueOf(currentCompositeKeyHash3), setCompositeKeyHash3);
        }
        function3ModifierMaterializerOf3.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i10 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(2058660585);
        int i11 = (i10 >> 9) & 14;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -326681643, "C92@4661L9:Row.kt#2w3rfo");
        int i12 = ((432 >> 6) & 112) | 6;
        RowScopeInstance rowScopeInstance = RowScopeInstance.INSTANCE;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -368594677, "C215@8248L1431,244@9697L752:MapViewContainer.kt#wl24de");
        Modifier modifierM560paddingVpY3zN4 = PaddingKt.m560paddingVpY3zN4(ClickableKt.m241clickableXHw0xAI$default(BorderKt.m218borderxT4_qwU(BackgroundKt.m207backgroundbw27NRU$default(ClipKt.clip(Modifier.INSTANCE, RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(24))), ColorKt.getSurfaceCard(), null, 2, null), Dp.m6091constructorimpl(1), androidx.compose.ui.graphics.ColorKt.Color(872415231), RoundedCornerShapeKt.m829RoundedCornerShape0680j_4(Dp.m6091constructorimpl(24))), false, null, null, new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$6$2$1$1
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
                MapViewContainerKt.MapViewContainer$lambda$5(mutableState2, !MapViewContainerKt.MapViewContainer$lambda$4(mutableState2));
                if (MapViewContainerKt.MapViewContainer$lambda$4(mutableState2)) {
                    return;
                }
                mapView2.setMapOrientation(0.0f);
            }
        }, 7, null), Dp.m6091constructorimpl(14), Dp.m6091constructorimpl(10));
        composerStartRestartGroup.startReplaceableGroup(733328855);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
        MeasurePolicy measurePolicyRememberBoxMeasurePolicy3 = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composerStartRestartGroup, ((0 >> 3) & 14) | ((0 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(-1323940314);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
        int currentCompositeKeyHash4 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
        CompositionLocalMap currentCompositionLocalMap4 = composerStartRestartGroup.getCurrentCompositionLocalMap();
        Function0<ComposeUiNode> constructor4 = ComposeUiNode.INSTANCE.getConstructor();
        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf4 = LayoutKt.modifierMaterializerOf(modifierM560paddingVpY3zN4);
        int i13 = ((((0 << 3) & 112) << 9) & 7168) | 6;
        if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
            ComposablesKt.invalidApplier();
        }
        composerStartRestartGroup.startReusableNode();
        if (composerStartRestartGroup.getInserting()) {
            function3 = constructor4;
            composerStartRestartGroup.createNode(function3);
        } else {
            function3 = constructor4;
            composerStartRestartGroup.useNode();
        }
        Composer composerM3273constructorimpl4 = Updater.m3273constructorimpl(composerStartRestartGroup);
        Updater.m3280setimpl(composerM3273constructorimpl4, measurePolicyRememberBoxMeasurePolicy3, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
        Updater.m3280setimpl(composerM3273constructorimpl4, currentCompositionLocalMap4, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash4 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
        if (composerM3273constructorimpl4.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl4.rememberedValue(), Integer.valueOf(currentCompositeKeyHash4))) {
            composerM3273constructorimpl4.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash4));
            composerM3273constructorimpl4.apply(Integer.valueOf(currentCompositeKeyHash4), setCompositeKeyHash4);
        }
        function3ModifierMaterializerOf4.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i13 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(2058660585);
        int i14 = (i13 >> 9) & 14;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
        BoxScopeInstance boxScopeInstance3 = BoxScopeInstance.INSTANCE;
        int i15 = ((0 >> 6) & 112) | 6;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, 438636771, "C226@8815L846:MapViewContainer.kt#wl24de");
        Alignment.Vertical centerVertically2 = Alignment.INSTANCE.getCenterVertically();
        composerStartRestartGroup.startReplaceableGroup(693286680);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Row)P(2,1,3)90@4553L58,91@4616L130:Row.kt#2w3rfo");
        Modifier.Companion companion2 = Modifier.INSTANCE;
        MeasurePolicy measurePolicyRowMeasurePolicy2 = RowKt.rowMeasurePolicy(Arrangement.INSTANCE.getStart(), centerVertically2, composerStartRestartGroup, ((384 >> 3) & 14) | ((384 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(-1323940314);
        ComposerKt.sourceInformation(composerStartRestartGroup, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
        int currentCompositeKeyHash5 = ComposablesKt.getCurrentCompositeKeyHash(composerStartRestartGroup, 0);
        CompositionLocalMap currentCompositionLocalMap5 = composerStartRestartGroup.getCurrentCompositionLocalMap();
        Function0<ComposeUiNode> constructor5 = ComposeUiNode.INSTANCE.getConstructor();
        Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf5 = LayoutKt.modifierMaterializerOf(companion2);
        int i16 = ((((384 << 3) & 112) << 9) & 7168) | 6;
        if (!(composerStartRestartGroup.getApplier() instanceof Applier)) {
            ComposablesKt.invalidApplier();
        }
        composerStartRestartGroup.startReusableNode();
        if (composerStartRestartGroup.getInserting()) {
            function4 = constructor5;
            composerStartRestartGroup.createNode(function4);
        } else {
            function4 = constructor5;
            composerStartRestartGroup.useNode();
        }
        Composer composerM3273constructorimpl5 = Updater.m3273constructorimpl(composerStartRestartGroup);
        Updater.m3280setimpl(composerM3273constructorimpl5, measurePolicyRowMeasurePolicy2, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
        Updater.m3280setimpl(composerM3273constructorimpl5, currentCompositionLocalMap5, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
        Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash5 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
        if (composerM3273constructorimpl5.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl5.rememberedValue(), Integer.valueOf(currentCompositeKeyHash5))) {
            composerM3273constructorimpl5.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash5));
            composerM3273constructorimpl5.apply(Integer.valueOf(currentCompositeKeyHash5), setCompositeKeyHash5);
        }
        function3ModifierMaterializerOf5.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composerStartRestartGroup)), composerStartRestartGroup, Integer.valueOf((i16 >> 3) & 112));
        composerStartRestartGroup.startReplaceableGroup(2058660585);
        int i17 = (i16 >> 9) & 14;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -326681643, "C92@4661L9:Row.kt#2w3rfo");
        RowScopeInstance rowScopeInstance2 = RowScopeInstance.INSTANCE;
        int i18 = ((384 >> 6) & 112) | 6;
        ComposerKt.sourceInformationMarkerStart(composerStartRestartGroup, -1601829550, "C227@8893L329,233@9247L39,234@9311L328:MapViewContainer.kt#wl24de");
        IconKt.m1934Iconww6aTOc(MapViewContainer$lambda$4(mutableState2) ? NavigationKt.getNavigation(Icons.INSTANCE.getDefault()) : CompassCalibrationKt.getCompassCalibration(Icons.INSTANCE.getDefault()), "Map orientation", SizeKt.m608size3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(20)), ColorKt.getCyanAccent(), composerStartRestartGroup, 3504, 0);
        SpacerKt.Spacer(SizeKt.m613width3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(6)), composerStartRestartGroup, 6);
        TextKt.m2461Text4IGK_g(MapViewContainer$lambda$4(mutableState2) ? "HEADING UP" : "NORTH UP", (Modifier) null, ColorKt.getTextPrimary(), TextUnitKt.getSp(11), (FontStyle) null, FontWeight.INSTANCE.getBold(), (FontFamily) FontFamily.INSTANCE.getMonospace(), 0L, (TextDecoration) null, (TextAlign) null, 0L, 0, false, 0, 0, (Function1<? super TextLayoutResult, Unit>) null, (TextStyle) null, composerStartRestartGroup, 200064, 0, 130962);
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
        AnimatedVisibilityKt.AnimatedVisibility(rowScopeInstance, !MapViewContainer$lambda$1(mutableState), (Modifier) null, EnterExitTransitionKt.fadeIn$default(null, 0.0f, 3, null), EnterExitTransitionKt.fadeOut$default(null, 0.0f, 3, null), (String) null, ComposableLambdaKt.composableLambda(composerStartRestartGroup, -1626764995, true, new Function3<AnimatedVisibilityScope, Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$6$2$1$3
            /* JADX WARN: 'super' call moved to the top of the method (can break code semantics) */
            {
                super(3);
            }

            @Override // kotlin.jvm.functions.Function3
            public /* bridge */ /* synthetic */ Unit invoke(AnimatedVisibilityScope animatedVisibilityScope, Composer composer2, Integer num) {
                invoke(animatedVisibilityScope, composer2, num.intValue());
                return Unit.INSTANCE;
            }

            public final void invoke(AnimatedVisibilityScope AnimatedVisibility, Composer composer2, int i19) {
                Object obj7;
                Intrinsics.checkNotNullParameter(AnimatedVisibility, "$this$AnimatedVisibility");
                ComposerKt.sourceInformation(composer2, "C249@9986L23,245@9799L632:MapViewContainer.kt#wl24de");
                if (ComposerKt.isTraceInProgress()) {
                    ComposerKt.traceEventStart(-1626764995, i19, -1, "com.sih2026.nav.ui.components.MapViewContainer.<anonymous>.<anonymous>.<anonymous>.<anonymous> (MapViewContainer.kt:245)");
                }
                Modifier modifierM207backgroundbw27NRU$default = BackgroundKt.m207backgroundbw27NRU$default(ClipKt.clip(Modifier.INSTANCE, RoundedCornerShapeKt.getCircleShape()), ColorKt.getCyanAccent(), null, 2, null);
                composer2.startReplaceableGroup(438637942);
                ComposerKt.sourceInformation(composer2, "CC(remember):MapViewContainer.kt#9igjgp");
                final MutableState<Boolean> mutableState3 = mutableState;
                Object objRememberedValue12 = composer2.rememberedValue();
                if (objRememberedValue12 == Composer.INSTANCE.getEmpty()) {
                    obj7 = new Function0<Unit>() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt$MapViewContainer$6$2$1$3$1$1
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
                            MapViewContainerKt.MapViewContainer$lambda$2(mutableState3, true);
                        }
                    };
                    composer2.updateRememberedValue(obj7);
                } else {
                    obj7 = objRememberedValue12;
                }
                composer2.endReplaceableGroup();
                Modifier modifierM559padding3ABfNKs = PaddingKt.m559padding3ABfNKs(ClickableKt.m241clickableXHw0xAI$default(modifierM207backgroundbw27NRU$default, false, null, null, (Function0) obj7, 7, null), Dp.m6091constructorimpl(12));
                composer2.startReplaceableGroup(733328855);
                ComposerKt.sourceInformation(composer2, "CC(Box)P(2,1,3)71@3309L67,72@3381L130:Box.kt#2w3rfo");
                MeasurePolicy measurePolicyRememberBoxMeasurePolicy4 = BoxKt.rememberBoxMeasurePolicy(Alignment.INSTANCE.getTopStart(), false, composer2, ((0 >> 3) & 14) | ((0 >> 3) & 112));
                composer2.startReplaceableGroup(-1323940314);
                ComposerKt.sourceInformation(composer2, "CC(Layout)P(!1,2)78@3182L23,80@3272L420:Layout.kt#80mrfh");
                int currentCompositeKeyHash6 = ComposablesKt.getCurrentCompositeKeyHash(composer2, 0);
                CompositionLocalMap currentCompositionLocalMap6 = composer2.getCurrentCompositionLocalMap();
                Function0<ComposeUiNode> constructor6 = ComposeUiNode.INSTANCE.getConstructor();
                Function3<SkippableUpdater<ComposeUiNode>, Composer, Integer, Unit> function3ModifierMaterializerOf6 = LayoutKt.modifierMaterializerOf(modifierM559padding3ABfNKs);
                int i20 = ((((0 << 3) & 112) << 9) & 7168) | 6;
                if (!(composer2.getApplier() instanceof Applier)) {
                    ComposablesKt.invalidApplier();
                }
                composer2.startReusableNode();
                if (composer2.getInserting()) {
                    composer2.createNode(constructor6);
                } else {
                    composer2.useNode();
                }
                Composer composerM3273constructorimpl6 = Updater.m3273constructorimpl(composer2);
                Updater.m3280setimpl(composerM3273constructorimpl6, measurePolicyRememberBoxMeasurePolicy4, ComposeUiNode.INSTANCE.getSetMeasurePolicy());
                Updater.m3280setimpl(composerM3273constructorimpl6, currentCompositionLocalMap6, ComposeUiNode.INSTANCE.getSetResolvedCompositionLocals());
                Function2<ComposeUiNode, Integer, Unit> setCompositeKeyHash6 = ComposeUiNode.INSTANCE.getSetCompositeKeyHash();
                if (composerM3273constructorimpl6.getInserting() || !Intrinsics.areEqual(composerM3273constructorimpl6.rememberedValue(), Integer.valueOf(currentCompositeKeyHash6))) {
                    composerM3273constructorimpl6.updateRememberedValue(Integer.valueOf(currentCompositeKeyHash6));
                    composerM3273constructorimpl6.apply(Integer.valueOf(currentCompositeKeyHash6), setCompositeKeyHash6);
                }
                function3ModifierMaterializerOf6.invoke(SkippableUpdater.m3264boximpl(SkippableUpdater.m3265constructorimpl(composer2)), composer2, Integer.valueOf((i20 >> 3) & 112));
                composer2.startReplaceableGroup(2058660585);
                int i21 = (i20 >> 9) & 14;
                ComposerKt.sourceInformationMarkerStart(composer2, -1253629263, "C73@3426L9:Box.kt#2w3rfo");
                BoxScopeInstance boxScopeInstance4 = BoxScopeInstance.INSTANCE;
                int i22 = ((0 >> 6) & 112) | 6;
                ComposerKt.sourceInformationMarkerStart(composer2, -1601828341, "C252@10102L307:MapViewContainer.kt#wl24de");
                IconKt.m1934Iconww6aTOc(MyLocationKt.getMyLocation(Icons.INSTANCE.getDefault()), "Follow the cursors", SizeKt.m608size3ABfNKs(Modifier.INSTANCE, Dp.m6091constructorimpl(24)), androidx.compose.ui.graphics.Color.INSTANCE.m3769getBlack0d7_KjU(), composer2, 3504, 0);
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
        }), composerStartRestartGroup, (i12 & 14) | 1600512, 18);
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
        ScopeUpdateScope scopeUpdateScopeEndRestartGroup = composerStartRestartGroup.endRestartGroup();
        if (scopeUpdateScopeEndRestartGroup != null) {
            final Modifier modifier3 = modifier2;
            scopeUpdateScopeEndRestartGroup.updateScope(new Function2<Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.components.MapViewContainerKt.MapViewContainer.7
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

                public final void invoke(Composer composer2, int i19) {
                    MapViewContainerKt.MapViewContainer(estimate, truth, z, truePath, estimatePath, noMapPath, z2, modifier3, composer2, RecomposeScopeImplKt.updateChangedFlags(i | 1), i2);
                }
            });
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final boolean MapViewContainer$lambda$1(MutableState<Boolean> mutableState) {
        return mutableState.getValue().booleanValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final void MapViewContainer$lambda$2(MutableState<Boolean> mutableState, boolean z) {
        mutableState.setValue(Boolean.valueOf(z));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final boolean MapViewContainer$lambda$4(MutableState<Boolean> mutableState) {
        return mutableState.getValue().booleanValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final void MapViewContainer$lambda$5(MutableState<Boolean> mutableState, boolean z) {
        mutableState.setValue(Boolean.valueOf(z));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final float MapViewContainer$lambda$7(MutableFloatState mutableFloatState) {
        return mutableFloatState.getFloatValue();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static final void MapViewContainer$lambda$8(MutableFloatState mutableFloatState, float f) {
        mutableFloatState.setFloatValue(f);
    }

    public static final String cardinal(float f) {
        return new String[]{"N", "NE", "E", "SE", "S", "SW", "W", "NW"}[((int) ((22.5f + (((f % 360.0f) + 360.0f) % 360.0f)) / 45.0f)) % 8];
    }

    private static final BitmapDrawable estimateArrow(Context context) {
        Bitmap bitmapCreateBitmap = Bitmap.createBitmap(150, 150, Bitmap.Config.ARGB_8888);
        Intrinsics.checkNotNullExpressionValue(bitmapCreateBitmap, "createBitmap(...)");
        Canvas canvas = new Canvas(bitmapCreateBitmap);
        float f = 150 / 2.0f;
        float f2 = 150 / 2.0f;
        Paint paint = new Paint();
        paint.setColor(Color.parseColor("#3306B6D4"));
        paint.setAntiAlias(true);
        Unit unit = Unit.INSTANCE;
        canvas.drawCircle(f, f2, 30.0f, paint);
        Paint paint2 = new Paint();
        paint2.setColor(-1);
        paint2.setAntiAlias(true);
        Unit unit2 = Unit.INSTANCE;
        canvas.drawCircle(f, f2, 19.0f, paint2);
        Path path = new Path();
        path.moveTo(f, f2 - 26.0f);
        path.lineTo(f + 18.0f, f2 + 18.0f);
        path.lineTo(f, 9.0f + f2);
        path.lineTo(f - 18.0f, 18.0f + f2);
        path.close();
        Paint paint3 = new Paint();
        paint3.setColor(Color.parseColor("#FF06B6D4"));
        paint3.setAntiAlias(true);
        Unit unit3 = Unit.INSTANCE;
        canvas.drawPath(path, paint3);
        Paint paint4 = new Paint();
        paint4.setColor(-1);
        paint4.setStyle(Paint.Style.STROKE);
        paint4.setStrokeWidth(4.0f);
        paint4.setAntiAlias(true);
        Unit unit4 = Unit.INSTANCE;
        canvas.drawPath(path, paint4);
        return new BitmapDrawable(context.getResources(), bitmapCreateBitmap);
    }

    private static final Polyline trail(String str, float f) {
        Polyline polyline = new Polyline();
        polyline.getOutlinePaint().setColor(Color.parseColor(str));
        polyline.getOutlinePaint().setStrokeWidth(f);
        polyline.getOutlinePaint().setStrokeCap(Paint.Cap.ROUND);
        polyline.getOutlinePaint().setStrokeJoin(Paint.Join.ROUND);
        return polyline;
    }

    private static final BitmapDrawable truthPuck(Context context) {
        Bitmap bitmapCreateBitmap = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888);
        Intrinsics.checkNotNullExpressionValue(bitmapCreateBitmap, "createBitmap(...)");
        Canvas canvas = new Canvas(bitmapCreateBitmap);
        float f = 96 / 2.0f;
        Paint paint = new Paint();
        paint.setColor(Color.parseColor("#3310B981"));
        paint.setAntiAlias(true);
        Unit unit = Unit.INSTANCE;
        canvas.drawCircle(f, f, 30.0f, paint);
        Paint paint2 = new Paint();
        paint2.setColor(Color.parseColor("#FF10B981"));
        paint2.setAntiAlias(true);
        Unit unit2 = Unit.INSTANCE;
        canvas.drawCircle(f, f, 18.0f, paint2);
        Paint paint3 = new Paint();
        paint3.setColor(-1);
        paint3.setStyle(Paint.Style.STROKE);
        paint3.setStrokeWidth(5.0f);
        paint3.setAntiAlias(true);
        Unit unit3 = Unit.INSTANCE;
        canvas.drawCircle(f, f, 18.0f, paint3);
        return new BitmapDrawable(context.getResources(), bitmapCreateBitmap);
    }
}
