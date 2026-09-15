"""Step-2 diagnosis — how much of a real turn the phone gyro reports, by window length and per session.

A constant share across 3 s, 10 s and 30 s windows means a scale error, which can be calibrated; a share that
falls with window length would mean filtering. Whole-session fits — diagnosis only, not an engine calibration.
Output: round2/out/gyro_scale_run.txt"""
import warnings; warnings.filterwarnings("ignore")
import sys
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parents[1]
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration

WIN = {30: 10.0, 100: 20.0, 300: 30.0}           # window rows -> minimum true turn (deg) to count as a turn
pool = {(sp, L, k): [] for sp in ("A+B", "D+E") for L in WIN for k in ("true", "gyro", "ref")}
per = []
for _, r in sessions.selected().iterrows():
    S = sessions.load(r.drive, r.driver, int(r.session))
    if S is None:
        continue
    C = calibration.Calibrator(S)
    n = len(S.t)
    raw = pd.read_parquet(ROOT/f"data/clean/{r.drive}.parquet", columns=["session", "aligned_valid", "rate_yaw"])
    ref = raw.rate_yaw.to_numpy(float)[(raw.session.to_numpy() == r.session) & raw.aligned_valid.to_numpy()]
    mv = (S.v > 5) & np.isfinite(ref)
    ref = np.nan_to_num(ref)*np.sign(np.corrcoef(ref[mv], C.rate[mv])[0, 1])
    cal = C.at(n - 1, axis_window_s=None, bias_window_s=1e9)          # whole session: diagnosis only
    dt = np.r_[np.clip(np.diff(S.t), 0, None), 0.0]
    Cg = np.vstack((np.zeros(3), np.cumsum(S.gyr*dt[:, None], axis=0)))
    Cr = np.r_[0.0, np.cumsum(ref*dt)]
    Tc = np.r_[0.0, np.cumsum(dt)]
    slow = np.r_[0, np.cumsum(S.v <= 5)]
    sp = "A+B" if r.driver in ("A", "B") else "D+E"
    rec = dict(driver=r.driver, drive=r.drive, session=int(r.session), rate_fit_r=cal.r_fit)
    for L, thr in WIN.items():
        a = np.arange(0, n - L, L)
        b = a + L
        keep = (slow[b] - slow[a]) == 0
        a, b = a[keep], b[keep]
        true = np.degrees(C.psi[b] - C.psi[a])
        W = Cg[b] - Cg[a]
        dur = Tc[b] - Tc[a]
        g = np.degrees(W @ cal.axis - cal.bias*dur)
        rf = np.degrees(Cr[b] - Cr[a])
        turn = np.abs(true) >= thr
        pool[(sp, L, "true")] += list(true[turn])
        pool[(sp, L, "gyro")] += list(g[turn])
        pool[(sp, L, "ref")] += list(rf[turn])
        if L == 100:
            rec["turn_windows_10s"] = int(turn.sum())
            rec["reads_10s"] = float((true[turn] @ g[turn])/(true[turn] @ true[turn])) if turn.sum() >= 5 else np.nan
            M = np.c_[W, dur]
            c = np.linalg.lstsq(M, np.radians(true), rcond=None)[0]
            rec["window_fit_r"] = float(np.corrcoef(M @ c, true)[0, 1])
            rec["window_reads"] = float(1/np.linalg.norm(c[:3]))
            rec["axis_angle_deg"] = float(np.degrees(np.arccos(min(1.0, abs(c[:3]/np.linalg.norm(c[:3]) @ cal.axis)))))
    per.append(rec)

print("1 · HOW MUCH OF A REAL TURN THE PHONE GYRO REPORTS, by window length (slope of gyro turn on true turn)")
print(f"  {'split':<6}" + "".join(f"{f'{L/10:g} s windows (turn >= {WIN[L]:g}°)':>34}" for L in WIN))
print(f"  {'':<6}" + "".join(f"{'rate axis | round-1 ref (n)':>34}" for L in WIN))
for sp in ("A+B", "D+E"):
    cells = []
    for L in WIN:
        t = np.array(pool[(sp, L, "true")])
        g = np.array(pool[(sp, L, "gyro")])
        rf = np.array(pool[(sp, L, "ref")])
        cells.append(f"{(t @ g)/(t @ t):.3f} | {(t @ rf)/(t @ t):.3f} ({len(t):,})")
    print(f"  {sp:<6}" + "".join(f"{x:>34}" for x in cells))

P = pd.DataFrame(per)
pd.set_option("display.width", 200)
print("\n2 · PER SESSION — 10 s windows")
print("  reads_10s      share of real turning the gyro reports (axis from the 10 Hz rate fit)")
print("  rate_fit_r     correlation of the 10 Hz rate fit;  window_fit_r  correlation when the axis is fitted on 10 s turns")
print("  window_reads   share of turning reported under the window fit;  axis_angle_deg  angle between the two axes\n")
print(P.round(3).to_string(index=False))
