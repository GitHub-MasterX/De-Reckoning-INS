package com.sih2026.nav.ui.theme;

import androidx.compose.material3.ColorScheme;
import androidx.compose.material3.ColorSchemeKt;
import androidx.compose.material3.MaterialThemeKt;
import androidx.compose.runtime.Composer;
import androidx.compose.runtime.ComposerKt;
import androidx.compose.runtime.RecomposeScopeImplKt;
import androidx.compose.runtime.ScopeUpdateScope;
import kotlin.Metadata;
import kotlin.Unit;
import kotlin.jvm.functions.Function2;
import kotlin.jvm.internal.Intrinsics;

/* JADX INFO: compiled from: Theme.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000\u001a\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\u001a \u0010\u0002\u001a\u00020\u00032\u0011\u0010\u0004\u001a\r\u0012\u0004\u0012\u00020\u00030\u0005¢\u0006\u0002\b\u0006H\u0007¢\u0006\u0002\u0010\u0007\"\u000e\u0010\u0000\u001a\u00020\u0001X\u0082\u0004¢\u0006\u0002\n\u0000¨\u0006\b"}, d2 = {"DarkColorScheme", "Landroidx/compose/material3/ColorScheme;", "SIHNavTheme", "", "content", "Lkotlin/Function0;", "Landroidx/compose/runtime/Composable;", "(Lkotlin/jvm/functions/Function2;Landroidx/compose/runtime/Composer;I)V", "app_debug"}, k = 2, mv = {1, 9, 0}, xi = 48)
public final class ThemeKt {
    private static final ColorScheme DarkColorScheme = ColorSchemeKt.m1731darkColorSchemeCXl9yA$default(ColorKt.getCyanAccent(), ColorKt.getDarkBg(), 0, 0, 0, ColorKt.getEmeraldGreen(), ColorKt.getDarkBg(), 0, 0, ColorKt.getWarningAmber(), 0, 0, 0, ColorKt.getDarkBg(), ColorKt.getTextPrimary(), ColorKt.getSurfaceDark(), ColorKt.getTextPrimary(), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -123492, 15, null);

    public static final void SIHNavTheme(final Function2<? super Composer, ? super Integer, Unit> content, Composer composer, final int i) {
        Intrinsics.checkNotNullParameter(content, "content");
        Composer composerStartRestartGroup = composer.startRestartGroup(-528105074);
        ComposerKt.sourceInformation(composerStartRestartGroup, "C(SIHNavTheme)20@540L118:Theme.kt#6edtt");
        int i2 = i;
        if ((i & 14) == 0) {
            i2 |= composerStartRestartGroup.changedInstance(content) ? 4 : 2;
        }
        int i3 = i2;
        if ((i3 & 11) == 2 && composerStartRestartGroup.getSkipping()) {
            composerStartRestartGroup.skipToGroupEnd();
        } else {
            if (ComposerKt.isTraceInProgress()) {
                ComposerKt.traceEventStart(-528105074, i3, -1, "com.sih2026.nav.ui.theme.SIHNavTheme (Theme.kt:19)");
            }
            MaterialThemeKt.MaterialTheme(DarkColorScheme, null, TypeKt.getTypography(), content, composerStartRestartGroup, ((i3 << 9) & 7168) | 390, 2);
            if (ComposerKt.isTraceInProgress()) {
                ComposerKt.traceEventEnd();
            }
        }
        ScopeUpdateScope scopeUpdateScopeEndRestartGroup = composerStartRestartGroup.endRestartGroup();
        if (scopeUpdateScopeEndRestartGroup != null) {
            scopeUpdateScopeEndRestartGroup.updateScope(new Function2<Composer, Integer, Unit>() { // from class: com.sih2026.nav.ui.theme.ThemeKt.SIHNavTheme.1
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

                public final void invoke(Composer composer2, int i4) {
                    ThemeKt.SIHNavTheme(content, composer2, RecomposeScopeImplKt.updateChangedFlags(i | 1));
                }
            });
        }
    }
}
