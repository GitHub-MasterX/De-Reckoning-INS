"""
Additive enrichment of the cleaned dataset. Adds derived columns; changes nothing
that is already there. Safe to re-run.

  session, t_raw_s     recording-session boundaries from the phone's own clock
  speed_best, speed_src ground truth that survives GNSS dropouts (falls back to CAN)
  gx_c gy_c gz_c        gyroscope with per-session bias removed
  stationary            vehicle at rest (for ZUPT and bias estimation)
  gnss_dropout          GPS lost lock while the vehicle was moving
  stuck                 sensor repeating a stale reading
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path

CLEAN = Path("/home/masterx/sih/data/clean")
RAW   = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset/S-Dataset")
MAN   = Path("/home/masterx/sih/data/manifest.csv")
FS = 10.0

GAP_BREAK_S   = 0.5    # interval above this = recording discontinuity (empty band: 0.12-1.28 s)
JUMP_KMH      = 15.0   # speed change per 0.1 s that is physically impossible (4.2 g)
FROZEN_FIX_N  = 5      # identical GPS fixes while moving = lost lock
MOVING_KMH    = 3.0    # vehicle considered moving above this
STILL_KMH     = 1.0    # vehicle considered stopped below this
STILL_MIN_S   = 2.0    # a stop must last this long to count
BIAS_STILL_KMH= 0.5    # stricter threshold for estimating gyro bias
BIAS_MIN_N    = 50     # samples needed before trusting a bias estimate
STUCK_RUN     = 5      # identical consecutive readings = stale

def run_lengths(a):
    """(start, length) of each run of identical consecutive values."""
    a = np.asarray(a); n = len(a)
    if n == 0: return np.zeros(0,int), np.zeros(0,int)
    chg = np.flatnonzero(a[1:] != a[:-1])
    starts = np.concatenate(([0], chg + 1))
    lens = np.diff(np.concatenate((starts, [n])))
    return starts, lens

def in_long_run(a, minlen):
    """True where a sample sits inside a run of >= minlen identical values."""
    starts, lens = run_lengths(a)
    if len(lens) == 0: return np.zeros(len(a), bool)
    return np.repeat(lens >= minlen, lens)

def sustained(mask, minlen):
    """Keep only True-runs at least minlen long."""
    m = np.asarray(mask, bool)
    starts, lens = run_lengths(m.astype(np.int8))
    if len(lens) == 0: return m
    return np.repeat((lens >= minlen) & m[starts], lens)

M = pd.read_csv(MAN)
extra = []

for _, r in M.iterrows():
    d = pd.read_parquet(CLEAN / f"{r.drive}.parquet")
    n = len(d)

    # ---- 1. sessions from the phone's own clock ------------------------------
    t_raw = np.full(n, np.nan)
    f = RAW / f"S-{r.drive}.csv"
    if f.exists():
        hdr = pd.read_csv(f, encoding="latin-1", nrows=0)
        tc = [c for c in hdr.columns if "TIME SINCE START" in c]
        if tc:
            t = pd.to_numeric(pd.read_csv(f, encoding="latin-1", usecols=tc)[tc[0]],
                              errors="coerce").to_numpy() / 1000.0
            t_raw = t[:n] if len(t) >= n else np.concatenate((t, np.full(n-len(t), np.nan)))
    dt = np.diff(t_raw, prepend=t_raw[0])
    brk = (dt < 0) | (dt > GAP_BREAK_S)
    brk[0] = False
    d["t_raw_s"] = t_raw
    d["session"] = np.cumsum(brk).astype(np.int16)

    # ---- 2. ground truth that survives GNSS dropouts -------------------------
    gps = d.speed_kmh.to_numpy().astype(float)
    can = d.can_speed.to_numpy().astype(float)
    lat, lon = d.lat.to_numpy(), d.lon.to_numpy()

    pos_changed = np.ones(n, bool)
    pos_changed[1:] = (np.diff(lat) != 0) | (np.diff(lon) != 0)
    frozen_fix = in_long_run(np.cumsum(pos_changed), FROZEN_FIX_N)

    can_ok = np.isfinite(can).sum() > 0.5*n and np.nanstd(can) > 0.5
    moving = (can if can_ok else gps) > MOVING_KMH
    dropout = frozen_fix & moving

    jump = np.zeros(n, bool)
    jd = np.abs(np.diff(gps)) > JUMP_KMH
    jump[:-1] |= jd; jump[1:] |= jd

    bad_gps = dropout | jump
    if can_ok:
        healthy = ~bad_gps & np.isfinite(gps) & np.isfinite(can)
        offset = float(np.nanmedian(gps[healthy] - can[healthy])) if healthy.sum() > 100 else 0.0
        d["speed_best"] = np.where(bad_gps, can + offset, gps)
        d["speed_src"]  = np.where(bad_gps, "can", "gps")
    else:
        offset = np.nan
        d["speed_best"] = gps
        d["speed_src"]  = "gps_only"
    d["gnss_dropout"] = dropout

    # ---- 3. gyro bias, per session ------------------------------------------
    v = d.speed_best.to_numpy()
    still_strict = v < BIAS_STILL_KMH
    biases = {}
    for axis in ("gx", "gy", "gz"):
        g = d[axis].to_numpy().astype(float)
        corr = g.copy()
        for s in np.unique(d.session):
            m = d.session.to_numpy() == s
            sel = m & still_strict & np.isfinite(g)
            if sel.sum() >= BIAS_MIN_N:      b = float(np.median(g[sel]))
            elif (still_strict & np.isfinite(g)).sum() >= BIAS_MIN_N:
                                             b = float(np.median(g[still_strict & np.isfinite(g)]))
            else:                            b = 0.0
            corr[m] = g[m] - b
            biases.setdefault(axis, []).append(b)
        d[axis + "_c"] = corr

    # ---- 4. stationary -------------------------------------------------------
    d["stationary"] = sustained(v < STILL_KMH, int(STILL_MIN_S * FS))

    # ---- 5. stuck sensor readings -------------------------------------------
    stuck = np.zeros(n, bool)
    for c in ("ax","ay","az","gx","gy","gz"):
        stuck |= in_long_run(d[c].to_numpy(), STUCK_RUN)
    d["stuck"] = stuck

    d.to_parquet(CLEAN / f"{r.drive}.parquet", index=False)
    extra.append(dict(drive=r.drive,
        sessions=int(d.session.max()) + 1,
        pct_can_label=round(100*float((d.speed_src == "can").mean()), 2),
        can_offset_kmh=round(offset, 3) if np.isfinite(offset) else np.nan,
        pct_dropout=round(100*float(dropout.mean()), 2),
        pct_stationary=round(100*float(d.stationary.mean()), 1),
        pct_stuck=round(100*float(stuck.mean()), 2),
        gyro_bias_max=round(float(np.nanmax([np.abs(b) for bs in biases.values() for b in bs])), 5)))

E = pd.DataFrame(extra)
M = M.drop(columns=[c for c in E.columns if c != "drive" and c in M.columns], errors="ignore")
M = M.merge(E, on="drive", how="left")
M["split"] = np.where(M.driver == "D", "test", "train")
M.to_csv(MAN, index=False)

print(f"ENRICHED {len(M)} drives\n")
print(f"  sessions        : {int(M.sessions.sum())} across {len(M)} drives "
      f"({int((M.sessions>1).sum())} drives split into multiple)")
print(f"  labels from CAN : {M.pct_can_label.mean():.2f}% of samples on average, "
      f"max {M.pct_can_label.max():.1f}% ({M.loc[M.pct_can_label.idxmax(),'drive']})")
print(f"  CAN offset      : median {M.can_offset_kmh.median():+.3f} km/h")
print(f"  GNSS dropouts   : {M.pct_dropout.mean():.2f}% of samples avg, "
      f"{int((M.pct_dropout>0).sum())} drives affected")
print(f"  stationary      : {M.pct_stationary.mean():.1f}% of samples avg")
print(f"  stuck           : {M.pct_stuck.mean():.3f}% of samples avg, "
      f"worst {M.pct_stuck.max():.1f}% ({M.loc[M.pct_stuck.idxmax(),'drive']})")
print(f"  gyro bias       : median {M.gyro_bias_max.median():.5f} rad/s, worst {M.gyro_bias_max.max():.5f}")
print(f"  split           : {(M.split=='train').sum()} train / {(M.split=='test').sum()} test")
print("\nDrives split into multiple sessions:")
print(M[M.sessions > 1][["drive","driver","sessions","n"]].to_string(index=False))
print("\nDrives where GNSS dropped out most:")
print(M.nlargest(6,"pct_dropout")[["drive","driver","pct_dropout","pct_can_label","can_offset_kmh"]].to_string(index=False))
