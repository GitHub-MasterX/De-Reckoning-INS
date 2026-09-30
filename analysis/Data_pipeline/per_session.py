"""
Recompute everything session-wise instead of file-wise.

A "drive" can be several separate recordings stitched together, and each one has its
own clock offset and its own sensor bias. Any quantity computed across a whole file
averages over unrelated recordings and lands on a value that is wrong for all of them.

Writes: sync_r / lag_s columns into each parquet, plus data/test_outputs/sessions.csv.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path

CLEAN = Path("/home/masterx/sih/data/clean")
MAN   = Path("/home/masterx/sih/data/test_outputs/manifest.csv")
FS = 10.0
MIN_SYNC_S   = 30.0    # a session shorter than this cannot be sync-tested
DECIM        = 2       # 5 Hz is ample for turn dynamics
MAX_LAG_S    = 30.0

def sync_quality(W, yaw, fs=FS):
    """Best correlation between any linear mix of the 3 gyro axes and true yaw rate,
    scanned over lag. Three axes, so phone orientation can't be mistaken for a lag."""
    ok = np.isfinite(W).all(1) & np.isfinite(yaw)
    W, yaw = W[ok], yaw[ok]
    n = len(yaw)
    if n < MIN_SYNC_S * fs or np.std(yaw) < 1e-6:
        return np.nan, np.nan
    Wd, yd = W[::DECIM], yaw[::DECIM]
    step = fs / DECIM
    maxlag = int(min(MAX_LAG_S * step, len(yd) // 4))
    best_lag, best_r = 0, 0.0
    for L in range(-maxlag, maxlag + 1):
        if   L < 0: x, y = Wd[-L:], yd[:len(yd)+L]
        elif L > 0: x, y = Wd[:len(Wd)-L], yd[L:]
        else:       x, y = Wd, yd
        if len(x) < 60: continue
        A = np.c_[x, np.ones(len(x))]
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = np.corrcoef(A @ coef, y)[0, 1]
        if np.isfinite(r) and abs(r) > abs(best_r): best_lag, best_r = L, r
    return best_lag / step, best_r

M = pd.read_csv(MAN)
srows = []

for _, r in M.iterrows():
    d = pd.read_parquet(CLEAN / f"{r.drive}.parquet")
    sid = d.session.to_numpy()
    d["sync_r"] = np.nan; d["lag_s"] = np.nan

    for s in np.unique(sid):
        m = sid == s
        sub = d[m]
        lag, rr = sync_quality(sub[["gx","gy","gz"]].to_numpy(), sub.yaw_rate.to_numpy())
        d.loc[m, "sync_r"] = rr
        d.loc[m, "lag_s"]  = lag

        # CAN->GPS offset, per session (was per file)
        gps, can = sub.speed_kmh.to_numpy(), sub.can_speed.to_numpy()
        healthy = (sub.speed_src.to_numpy() == "gps") & np.isfinite(gps) & np.isfinite(can)
        off = float(np.median(gps[healthy] - can[healthy])) if healthy.sum() > 100 else np.nan

        v = sub.speed_best.to_numpy()
        srows.append(dict(
            drive=r.drive, driver=r.driver, split=r.split, session=int(s),
            n=int(m.sum()), minutes=round(m.sum()/FS/60, 1),
            km=round(float(np.nansum(v/3.6/FS)/1000), 2),
            v_mean=round(float(np.nanmean(v)), 1), v_max=round(float(np.nanmax(v)), 1),
            pct_moving=round(100*float(np.mean(v > 1)), 1),
            sync_r=round(rr, 3) if np.isfinite(rr) else np.nan,
            lag_s=round(lag, 2) if np.isfinite(lag) else np.nan,
            can_offset=round(off, 3) if np.isfinite(off) else np.nan,
            pct_stationary=round(100*float(sub.stationary.mean()), 1),
            pct_stuck=round(100*float(sub.stuck.mean()), 2),
            gyro_bias=round(float(np.nanmax([abs(np.median(sub[c][sub.speed_best < 0.5]))
                       if (sub.speed_best < 0.5).sum() >= 50 else 0.0 for c in ("gx","gy","gz")])), 5),
        ))
    d.to_parquet(CLEAN / f"{r.drive}.parquet", index=False)

S = pd.DataFrame(srows)
S.to_csv("/home/masterx/sih/data/test_outputs/sessions.csv", index=False)

# per-drive summary now derived from sessions
agg = S.groupby("drive").agg(sessions=("session","count"),
        sync_r_best=("sync_r","max"), sync_r_worst=("sync_r","min"),
        lag_spread=("lag_s", lambda x: round(float(np.nanmax(x)-np.nanmin(x)),2) if x.notna().any() else np.nan)).reset_index()
M = M.drop(columns=[c for c in agg.columns if c != "drive" and c in M.columns], errors="ignore")
M = M.drop(columns=["sync_r","lag_s"], errors="ignore").merge(agg, on="drive", how="left")
M.to_csv(MAN, index=False)

print(f"{len(S)} sessions across {S.drive.nunique()} drives\n")
tested = S[S.sync_r.notna()]
print(f"sync tested on {len(tested)}/{len(S)} sessions ({len(S)-len(tested)} too short)")
for t in (0.9, 0.8, 0.7, 0.5):
    n = (tested.sync_r.abs() >= t).sum()
    print(f"  |sync_r| >= {t}: {n:>3} sessions  ({tested[tested.sync_r.abs()>=t].minutes.sum()/60:>5.1f} h, "
          f"{tested[tested.sync_r.abs()>=t].km.sum():>6.0f} km)")

print("\n--- multi-session drives: did per-session help? ---")
for drv in sorted(S[S.drive.isin(M[M.sessions>1].drive)].drive.unique()):
    sub = S[S.drive==drv]
    old = {"S2":0.929,"S3b":0.720,"S4":0.347,"M":0.811,"Y1":0.068,"Vta17":np.nan,"Vtb1":0.428}.get(drv, np.nan)
    per = ", ".join(f"s{int(x.session)}:{x.sync_r if pd.notna(x.sync_r) else float('nan'):.3f}@{x.lag_s:+.1f}s"
                    if pd.notna(x.sync_r) else f"s{int(x.session)}:--" for _,x in sub.iterrows())
    print(f"  {drv:<7} whole-file was {old if pd.notna(old) else float('nan'):.3f}  ->  {per}")
