package com.sih2026.nav.domain.engine;

import com.sih2026.nav.data.model.NavState;
import kotlin.Metadata;
import kotlinx.coroutines.flow.StateFlow;

/* JADX INFO: compiled from: NavEngine.kt */
/* JADX INFO: loaded from: classes4.dex */
@Metadata(d1 = {"\u0000$\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0003\bf\u0018\u00002\u00020\u0001J\u0010\u0010\u0007\u001a\u00020\b2\u0006\u0010\t\u001a\u00020\nH&J\b\u0010\u000b\u001a\u00020\bH&J\b\u0010\f\u001a\u00020\bH&R\u0018\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u0003X¦\u0004¢\u0006\u0006\u001a\u0004\b\u0005\u0010\u0006¨\u0006\r"}, d2 = {"Lcom/sih2026/nav/domain/engine/NavEngine;", "", "state", "Lkotlinx/coroutines/flow/StateFlow;", "Lcom/sih2026/nav/data/model/NavState;", "getState", "()Lkotlinx/coroutines/flow/StateFlow;", "setGnssBlackout", "", "enabled", "", "start", "stop", "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public interface NavEngine {
    StateFlow<NavState> getState();

    void setGnssBlackout(boolean enabled);

    void start();

    void stop();
}
