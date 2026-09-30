package com.sih2026.nav.ui.theme;

import androidx.compose.material3.Typography;
import androidx.compose.ui.graphics.Shadow;
import androidx.compose.ui.graphics.drawscope.DrawStyle;
import androidx.compose.ui.text.PlatformTextStyle;
import androidx.compose.ui.text.TextStyle;
import androidx.compose.ui.text.font.FontFamily;
import androidx.compose.ui.text.font.FontStyle;
import androidx.compose.ui.text.font.FontSynthesis;
import androidx.compose.ui.text.font.FontWeight;
import androidx.compose.ui.text.font.GenericFontFamily;
import androidx.compose.ui.text.font.SystemFontFamily;
import androidx.compose.ui.text.intl.LocaleList;
import androidx.compose.ui.text.style.BaselineShift;
import androidx.compose.ui.text.style.LineHeightStyle;
import androidx.compose.ui.text.style.TextDecoration;
import androidx.compose.ui.text.style.TextGeometricTransform;
import androidx.compose.ui.text.style.TextIndent;
import androidx.compose.ui.text.style.TextMotion;
import androidx.compose.ui.unit.TextUnitKt;
import kotlin.Metadata;
import kotlin.jvm.internal.DefaultConstructorMarker;

/* JADX INFO: compiled from: Type.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000\n\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\"\u0011\u0010\u0000\u001a\u00020\u0001¢\u0006\b\n\u0000\u001a\u0004\b\u0002\u0010\u0003¨\u0006\u0004"}, d2 = {"Typography", "Landroidx/compose/material3/Typography;", "getTypography", "()Landroidx/compose/material3/Typography;", "app_debug"}, k = 2, mv = {1, 9, 0}, xi = 48)
public final class TypeKt {
    private static final Typography Typography;

    static {
        GenericFontFamily monospace = FontFamily.INSTANCE.getMonospace();
        FontWeight bold = FontWeight.INSTANCE.getBold();
        TextStyle textStyle = new TextStyle(ColorKt.getTextPrimary(), TextUnitKt.getSp(32), bold, (FontStyle) null, (FontSynthesis) null, monospace, (String) null, 0L, (BaselineShift) null, (TextGeometricTransform) null, (LocaleList) null, 0L, (TextDecoration) null, (Shadow) null, (DrawStyle) null, 0, 0, 0L, (TextIndent) null, (PlatformTextStyle) null, (LineHeightStyle) null, 0, 0, (TextMotion) null, 16777176, (DefaultConstructorMarker) null);
        SystemFontFamily systemFontFamily = FontFamily.INSTANCE.getDefault();
        FontWeight bold2 = FontWeight.INSTANCE.getBold();
        TextStyle textStyle2 = new TextStyle(ColorKt.getTextPrimary(), TextUnitKt.getSp(20), bold2, (FontStyle) null, (FontSynthesis) null, systemFontFamily, (String) null, 0L, (BaselineShift) null, (TextGeometricTransform) null, (LocaleList) null, 0L, (TextDecoration) null, (Shadow) null, (DrawStyle) null, 0, 0, 0L, (TextIndent) null, (PlatformTextStyle) null, (LineHeightStyle) null, 0, 0, (TextMotion) null, 16777176, (DefaultConstructorMarker) null);
        SystemFontFamily systemFontFamily2 = FontFamily.INSTANCE.getDefault();
        FontWeight normal = FontWeight.INSTANCE.getNormal();
        TextStyle textStyle3 = new TextStyle(ColorKt.getTextPrimary(), TextUnitKt.getSp(16), normal, (FontStyle) null, (FontSynthesis) null, systemFontFamily2, (String) null, 0L, (BaselineShift) null, (TextGeometricTransform) null, (LocaleList) null, 0L, (TextDecoration) null, (Shadow) null, (DrawStyle) null, 0, 0, 0L, (TextIndent) null, (PlatformTextStyle) null, (LineHeightStyle) null, 0, 0, (TextMotion) null, 16777176, (DefaultConstructorMarker) null);
        SystemFontFamily systemFontFamily3 = FontFamily.INSTANCE.getDefault();
        FontWeight normal2 = FontWeight.INSTANCE.getNormal();
        TextStyle textStyle4 = new TextStyle(ColorKt.getTextSecondary(), TextUnitKt.getSp(14), normal2, (FontStyle) null, (FontSynthesis) null, systemFontFamily3, (String) null, 0L, (BaselineShift) null, (TextGeometricTransform) null, (LocaleList) null, 0L, (TextDecoration) null, (Shadow) null, (DrawStyle) null, 0, 0, 0L, (TextIndent) null, (PlatformTextStyle) null, (LineHeightStyle) null, 0, 0, (TextMotion) null, 16777176, (DefaultConstructorMarker) null);
        GenericFontFamily monospace2 = FontFamily.INSTANCE.getMonospace();
        FontWeight semiBold = FontWeight.INSTANCE.getSemiBold();
        Typography = new Typography(textStyle, null, null, null, textStyle2, null, null, null, null, textStyle3, textStyle4, null, null, null, new TextStyle(ColorKt.getTextMuted(), TextUnitKt.getSp(11), semiBold, (FontStyle) null, (FontSynthesis) null, monospace2, (String) null, 0L, (BaselineShift) null, (TextGeometricTransform) null, (LocaleList) null, 0L, (TextDecoration) null, (Shadow) null, (DrawStyle) null, 0, 0, 0L, (TextIndent) null, (PlatformTextStyle) null, (LineHeightStyle) null, 0, 0, (TextMotion) null, 16777176, (DefaultConstructorMarker) null), 14830, null);
    }

    public static final Typography getTypography() {
        return Typography;
    }
}
