"""
Clean IO-VNBD into one canonical file per drive.

Handles the four traps in the raw data:
  1. latin-1 encoding (the m/s2 symbol breaks a plain read_csv)
  2. two different column-naming schemes across folders
  3. V- filenames that differ from S- only in capitalisation
  4. drives that are very short or stationary  -> KEPT, flagged in the manifest

Output: data/clean/<drive>.parquet  +  data/test_outputs/manifest.csv
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path

SYNC = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets")
SRC  = SYNC / "Uncategorised IOVNB Dataset"      # canonical copy: 72 pairs, flat
CAT  = SYNC / "Categorised IOVNB Dataset"        # same drives, grouped by driver
OUT  = Path("/home/masterx/sih/data/clean"); OUT.mkdir(parents=True, exist_ok=True)
FS   = 10.0

def read(p):
    df = pd.read_csv(p, encoding="latin-1", low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df

def pick(df, *prefixes):
    """First column starting with any of the given prefixes."""
    for pre in prefixes:
        for c in df.columns:
            if c.startswith(pre): return c
    return None

def col(df, *prefixes):
    c = pick(df, *prefixes)
    return pd.to_numeric(df[c], errors="coerce").to_numpy() if c else None

# ---- driver map, read from the Categorised folder structure -------------------
driver_of = {}
for group in CAT.iterdir():
    if not group.is_dir(): continue
    letter = group.name.split("(Driver")[-1].strip(" )") if "Driver" in group.name else "?"
    for f in group.rglob("S-*.csv"):
        driver_of[f.stem[2:].lower()] = letter

# ---- sync quality (recorded as metadata, nothing is filtered on it) -----------
def sync_quality(W, yaw_can):
    """Best correlation between any linear mix of the 3 gyro axes and CAN yaw rate,
    scanned over +/-30 s of lag. Uses all 3 axes so phone orientation cannot be
    mistaken for a timing problem."""
    Wd, yd = W[::5], yaw_can[::5]                       # 2 Hz is ample for turn dynamics
    best_lag, best_r = 0, 0.0
    for L in range(-60, 61):
        if   L < 0: x, y = Wd[-L:], yd[:len(yd)+L]
        elif L > 0: x, y = Wd[:len(Wd)-L], yd[L:]
        else:       x, y = Wd, yd
        if len(x) < 300: continue
        A = np.c_[x, np.ones(len(x))]
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = np.corrcoef(A @ coef, y)[0, 1]
        if abs(r) > abs(best_r): best_lag, best_r = L, r
    return best_lag * 0.5, best_r

# ---- main --------------------------------------------------------------------
vfiles = {p.name.lower(): p for p in (SRC / "V-Dataset").iterdir()}
rows, skipped = [], []

for sp in sorted((SRC / "S-Dataset").iterdir()):
    if sp.suffix.lower() != ".csv": continue
    name = sp.stem[2:]                                    # "S-Vta2" -> "Vta2"
    vp = vfiles.get(sp.name.replace("S-", "V-", 1).lower())
    if vp is None:
        skipped.append((name, "no V- pair")); continue

    S, V = read(sp), read(vp)
    n = min(len(S), len(V)); S, V = S.iloc[:n], V.iloc[:n]

    d = pd.DataFrame({
        "t_s":       np.arange(n) / FS,
        "ax":        col(S, "ACCELEROMETER X"),
        "ay":        col(S, "ACCELEROMETER Y"),
        "az":        col(S, "ACCELEROMETER Z"),
        "gx":        col(S, "GYROSCOPE X", "GYROSCOPE Yaw"),
        "gy":        col(S, "GYROSCOPE Y", "GYROSCOPE Pitch"),
        "gz":        col(S, "GYROSCOPE Z", "GYROSCOPE Roll"),
        "mx":        col(S, "MAGNETIC FIELD X"),
        "my":        col(S, "MAGNETIC FIELD Y"),
        "mz":        col(S, "MAGNETIC FIELD Z"),
        "speed_kmh": col(V, "Velocity (km/hr)"),           # VBOX GPS - ground truth
        "lat":       col(V, "Latitude"),
        "lon":       col(V, "Longitude"),
        "can_speed": col(V, "Indicated Vehicle Speed"),     # second opinion on speed
        "yaw_rate":  col(V, "Yaw Rate"),                    # deg/s, for alignment work
        "lon_acc":   col(V, "Indicated Longitudinal Acc"),  # g
        "lat_acc":   col(V, "Indicated Lateral Acc"),       # g
        # --- kept for later use so the data never needs re-cleaning ---
        "heading":     col(V, "Heading"),
        "ws_fl":       col(V, "Wheel Speed Front Left"),
        "ws_fr":       col(V, "Wheel Speed Front Right"),
        "ws_rl":       col(V, "Wheel Speed Rear Left"),
        "ws_rr":       col(V, "Wheel Speed Rear Right"),
        "steer_deg":   col(V, "Steering Angle"),
        "engine_rpm":  col(V, "Engine Speed"),
        "brake":       col(V, "Brake Position"),
        "gear":        col(V, "Gear ("),
        "grav_x":      col(S, "GRAVITY X"),
        "grav_y":      col(S, "GRAVITY Y"),
        "grav_z":      col(S, "GRAVITY Z"),
        "phone_lat":   col(S, "GPS LATITUDE"),
        "phone_lon":   col(S, "GPS LONGITUDE"),
        "phone_speed": col(S, "GPS SPEED"),
        "phone_gps_acc": col(S, "GPS ACCURACY"),
    })

    d["yaw_rate"] = np.radians(d["yaw_rate"])              # -> rad/s
    d["lon_acc"]  = d["lon_acc"] * 9.81                    # -> m/s2
    d["lat_acc"]  = d["lat_acc"] * 9.81

    imu = ["ax","ay","az","gx","gy","gz"]
    before = len(d)
    d = d[np.isfinite(d[imu]).all(axis=1) & np.isfinite(d["speed_kmh"])].reset_index(drop=True)
    if len(d) < 100:
        skipped.append((name, f"only {len(d)} valid rows")); continue

    v_max_kmh = float(np.nanmax(d.speed_kmh))
    flags = []
    if v_max_kmh < 5:      flags.append("stationary")
    if len(d) < 600:       flags.append("short")
    if len(d) >= 600 and np.isfinite(d.yaw_rate).sum() > 500:
        lag_s, sync_r = sync_quality(d[["gx","gy","gz"]].to_numpy(), d["yaw_rate"].to_numpy())
    else:
        lag_s, sync_r = 0.0, float("nan")
        flags.append("sync-untestable")
    d.to_parquet(OUT / f"{name}.parquet", index=False)

    v = d.speed_kmh.to_numpy()
    rows.append(dict(
        drive=name, driver=driver_of.get(name.lower(), "?"),
        n=len(d), dropped=before-len(d), minutes=round(len(d)/FS/60, 1),
        km=round(np.sum(v/3.6/FS)/1000, 2),
        v_mean=round(v.mean(), 1), v_max=round(v.max(), 1),
        pct_moving=round(100*np.mean(v > 1), 1),
        sync_r=round(sync_r, 3), lag_s=lag_s,
        flags="|".join(flags) if flags else "",
    ))

M = pd.DataFrame(rows).sort_values(["driver", "drive"])
M.to_csv("/home/masterx/sih/data/test_outputs/manifest.csv", index=False)

print(f"CLEANED {len(M)} drives  ->  data/clean/*.parquet")
print(f"SKIPPED {len(skipped)}: " + ", ".join(f"{n} ({w})" for n, w in skipped) + "\n")
print(M.to_string(index=False))
print(f"\nTOTAL  {M.minutes.sum()/60:.1f} h   {M.km.sum():.0f} km   "
      f"{M.n.sum():,} samples   {M.dropped.sum():,} rows dropped as invalid")
print(f"flagged: stationary {M['flags'].str.contains('stationary').sum()}, "
      f"short {M['flags'].str.contains('short').sum()}, "
      f"sync-untestable {M['flags'].str.contains('sync-untestable').sum()}, "
      f"clean {(M['flags']=='').sum()}")
print("\nBy driver:")
print(M.groupby("driver").agg(drives=("drive","count"), hours=("minutes", lambda x: round(x.sum()/60,1)),
                              km=("km","sum"), v_max=("v_max","max")).to_string())
