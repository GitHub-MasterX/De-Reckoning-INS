package com.sih2026.nav;

import android.app.Application;
import kotlin.Metadata;
import org.osmdroid.config.Configuration;
import org.osmdroid.config.DefaultConfigurationProvider;

/* JADX INFO: compiled from: NavApp.kt */
/* JADX INFO: loaded from: classes6.dex */
@Metadata(d1 = {"\u0000\u0012\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0000\b\u0007\u0018\u00002\u00020\u0001B\u0005¢\u0006\u0002\u0010\u0002J\b\u0010\u0003\u001a\u00020\u0004H\u0016¨\u0006\u0005"}, d2 = {"Lcom/sih2026/nav/NavApp;", "Landroid/app/Application;", "()V", "onCreate", "", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class NavApp extends Application {
    public static final int $stable = 0;

    @Override // android.app.Application
    public void onCreate() {
        super.onCreate();
        Configuration.getInstance().load(this, getSharedPreferences(DefaultConfigurationProvider.DEFAULT_USER_AGENT, 0));
    }
}
