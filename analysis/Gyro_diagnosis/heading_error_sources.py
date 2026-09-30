"""Step-2 diagnosis — where gyro heading error comes from: scale, sign, growth, timing, jitter.

Run on the 10 Hz rate calibration (Calibrator.at over all history, scale 1) — the calibration before the window
fit existed — and on round-1's car-assisted rate_yaw as a reference. Moving 1 km blackouts.
Output: round2/out/heading_error_sources_run.txt"""
import warnings; warnings.filterwarnings("ignore")
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter1d

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, calibration

BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet")
SHIFTS = (-20, -10, -5, 0, 5, 10, 20)          # gyro rows relative to truth, 0.1 s each
rows = []
for (drive, session), g in BL[BL.moving_1000].groupby(["drive", "session"], sort=False):
    S = sessions.load(drive, g.driver.iloc[0], int(session))
    C = calibration.Calibrator(S)
    raw = pd.read_parquet(ROOT/f"data/clean/{drive}.parquet", columns=["session", "aligned_valid", "rate_yaw"])
    ref = raw.rate_yaw.to_numpy(float)[(raw.session.to_numpy() == session) & raw.aligned_valid.to_numpy()]
    mv = (S.v > 5) & np.isfinite(ref)
    ref = np.nan_to_num(ref)*np.sign(np.corrcoef(ref[mv], C.rate[mv])[0, 1])
    n = len(S.t)
    for b in g.itertuples(index=False):
        i, j = b.row_start, b.end_1000
        cal = C.at(i, axis_window_s=None, bias_window_s=1e9)
        if cal is None:
            continue
        dt = np.clip(np.diff(S.t[i:j+1]), 0, None)
        true = C.psi[j] - C.psi[i]
        yaw = S.gyr @ cal.axis - cal.bias
        ps = uniform_filter1d(C.psi[i:j+1], 10)
        seg = yaw[i:j]
        hf = seg - uniform_filter1d(seg, 20)
        fast = S.v[i:j] > 5
        r = dict(driver=b.driver, band=b.band_1000, T=S.t[j]-S.t[i], true=np.degrees(true),
                 est=np.degrees(yaw[i:j] @ dt), est_ref=np.degrees(ref[i:j] @ dt),
                 total_turn=np.degrees(np.abs(np.diff(ps)).sum()),
                 hf_std=np.degrees(hf[fast].std()) if fast.sum() > 50 else np.nan)
        for s in SHIFTS:
            a, z = i + s, j + s
            r[f"err_shift_{s}"] = np.degrees(abs(yaw[a:z] @ dt - true)) if a >= 0 and z <= n else np.nan
        rows.append(r)
D = pd.DataFrame(rows)
D["err"] = (D.est - D.true).abs()
D["err_ref"] = (D.est_ref - D.true).abs()
split = {"A+B": D.driver.isin(["A", "B"]), "D+E": D.driver.isin(["D", "E"])}

print("1 · SCALE — blackouts with a true turn of at least 60°: gyro turn ÷ true turn (median)")
for lab, m in split.items():
    q = D[m & (D.true.abs() >= 60)]
    print(f"  {lab}: n={len(q):,}   rate calibration {np.median(q.est/q.true):.3f}"
          f"   round-1 reference {np.median(q.est_ref/q.true):.3f}")

print("\n2 · SIGN — blackouts with a true turn of at least 30°: gyro turn has the opposite sign")
for lab, m in split.items():
    q = D[m & (D.true.abs() >= 30)]
    print(f"  {lab}: n={len(q):,}   rate calibration {100*(np.sign(q.est) != np.sign(q.true)).mean():.1f}%"
          f"   reference {100*(np.sign(q.est_ref) != np.sign(q.true)).mean():.1f}%")

print("\n3 · GROWTH ON STRAIGHT BLACKOUTS (total turning < 20°): median |error| by duration")
for lab, m in split.items():
    q = D[m & (D.total_turn < 20)]
    cells = []
    for lo, hi in ((0, 45), (45, 60), (60, 90), (90, 1e9)):
        x = q[(q["T"] >= lo) & (q["T"] < hi)]
        cells.append(f"{lo:g}-{hi:g} s: {x.err.median():.1f}° (n={len(x)})" if len(x) else f"{lo:g}-{hi:g} s: -")
    print(f"  {lab}: " + "   ".join(cells))

print("\n4 · ERROR BY TOTAL TURNING in the blackout: median |error|, rate calibration | reference")
for lab, m in split.items():
    cells = []
    for lo, hi in ((0, 20), (20, 90), (90, 270), (270, 1e9)):
        x = D[m & (D.total_turn >= lo) & (D.total_turn < hi)]
        cells.append(f"{lo:g}-{hi:g}°: {x.err.median():.1f}|{x.err_ref.median():.1f}° (n={len(x)})" if len(x) else "-")
    print(f"  {lab}: " + "   ".join(cells))

print("\n5 · TIMING — median |error| when the gyro is shifted against the GPS (+ = gyro later)")
for lab, m in split.items():
    print(f"  {lab}: " + "   ".join(f"{s/10:+.1f} s: {D[m][f'err_shift_{s}'].median():.2f}°" for s in SHIFTS))

print("\n6 · HIGH-FREQUENCY JITTER in the 10 Hz turn rate (moving samples, minus its own 2 s average)")
for lab, m in split.items():
    q = D[m]
    rw = np.degrees(np.radians(q.hf_std)*np.sqrt(q["T"]*0.1))
    print(f"  {lab}: jitter std median {q.hf_std.median():.2f} °/s  ->  random-walk heading error if it were white noise:"
          f" median {rw.median():.1f}°  (compare the straight blackouts above)")
