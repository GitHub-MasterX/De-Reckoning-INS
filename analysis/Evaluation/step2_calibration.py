"""Round 2 · Step 2 — honest start state and gyro calibration from GNSS history only.

At every blackout start, calibrations are fitted from rows before the start (core/calibration.py):
  rate                 axis from the 10 Hz course rate over all history, scale 1, bias median over all history
                       (the winner among the rate fits of the first run: out/step2_run_v1.txt)
  window               axis, scale and bias from turning accumulated over 10 s windows of all history
  window_recent_bias   the same axis and scale, bias from a median over the last 300 s
A window fit without enough turning history falls back to `rate` — an engine uses what it has.
Reference, not honest: round-1's rate_yaw — axis fitted to the car's CAN yaw rate, bias from stops found in the
car's true speed, scale 1.

  1  calibration fit at every start point
  2  heading error: calibrated gyro turning through each blackout against the true change of course
  3  choice on the tuning drivers A+B only  -> round2/out/Config/calibration_choice.txt
  4  the chosen calibration by driving condition, moving and stop-and-go
Outputs: round2/out/Pipeline_Data/calibration.parquet, heading_errors.parquet.
Rules: round2/DECISIONS.md.  Run from the repo root:  .venv/bin/python3 round2/step2_calibration.py"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, context, calibration, engine_input

T0 = time.time()
TUNE, TEST = ["A", "B"], ["D", "E"]
SPLITS = (("A+B (tuning)", TUNE), ("D+E (test)", TEST))
VARIANTS = ("rate", "window", "window_recent_bias")
REF = "round1_can_ref"
TARGETS = (("moving", 200), ("moving", 1000), ("stopgo", 1000))
SIGN_MIN_TURN_DEG = 30.0
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*106}\n{t}\n{'='*106}")

BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet")
recs, cals = [], []
for (drive, session), g in BL.groupby(["drive", "session"], sort=False):
    driver = g.driver.iloc[0]
    S = sessions.load(drive, driver, int(session))
    C = calibration.Calibrator(S)
    raw = pd.read_parquet(ROOT/f"data/clean/{drive}.parquet", columns=["session", "aligned_valid", "rate_yaw"])
    ref = raw.rate_yaw.to_numpy(float)[(raw.session.to_numpy() == session) & raw.aligned_valid.to_numpy()]
    mv = (S.v > 5) & np.isfinite(ref)
    ref = np.nan_to_num(ref)*np.sign(np.corrcoef(ref[mv], C.rate[mv])[0, 1])       # sign from truth: reference only
    for b in g.itertuples(index=False):
        i = b.row_start
        rate = C.at(i, axis_window_s=None, bias_window_s=1e9)
        own = {"rate": rate, "window": C.at_windows(i), "window_recent_bias": C.at_windows(i, recent_bias_s=300.0)}
        used = {name: (cal if cal is not None else rate) for name, cal in own.items()}
        for name, cal in used.items():
            if cal is not None:
                cals.append(dict(driver=driver, drive=drive, session=int(session), row_start=int(i), variant=name,
                                 own_fit=own[name] is not None, method=cal.method, axis_x=cal.axis[0],
                                 axis_y=cal.axis[1], axis_z=cal.axis[2], scale=cal.scale, bias=cal.bias,
                                 r_fit=cal.r_fit, fit_s=cal.fit_s, turn_windows=cal.turn_windows))
        for sset, c in TARGETS:
            if not getattr(b, f"{sset}_{c}"):
                continue
            j = getattr(b, f"end_{c}")
            true_turn = C.psi[j] - C.psi[i]                                      # scoring only
            dt = np.clip(np.diff(S.t[i:j+1]), 0.0, None)
            for name in VARIANTS + (REF,):
                if name == REF:
                    turn = float(ref[i:j] @ dt)
                elif used[name] is None:
                    continue
                else:
                    inp = engine_input.build(S, used[name], i, j)                # what the engine is given
                    turn = float(inp.turn_rate()[:-1] @ dt)
                big = abs(np.degrees(true_turn)) >= SIGN_MIN_TURN_DEG
                recs.append(dict(driver=driver, drive=drive, session=int(session), row_start=int(i), set=sset,
                                 checkpoint=c, band=getattr(b, f"band_{c}"), variant=name,
                                 true_deg=float(np.degrees(true_turn)), gyro_deg=float(np.degrees(turn)),
                                 err_deg=float(np.degrees(abs(turn - true_turn))),
                                 wrong_sign=float(np.sign(turn) != np.sign(true_turn)) if big else np.nan))
E = pd.DataFrame(recs)
K = pd.DataFrame(cals)
E.to_parquet(ROOT/"outputs/Pipeline_Data/heading_errors.parquet", index=False)
K.to_parquet(ROOT/"outputs/Pipeline_Data/calibration.parquet", index=False)
log(f"{len(K):,} calibrations at {BL.shape[0]:,} start points; {len(E):,} heading-error records")

# ───────────────────────── 1 · calibration fit ─────────────────────────
head("1 · CALIBRATION FIT — at every start point, from history only")
print(f"  {'variant':<20}{'split':<14}{'starts':>8}{'own fit':>9}{'fit r':>8}{'scale (median)':>16}"
      f"{'scale 10-90%':>15}{'turn windows':>14}")
for name in VARIANTS:
    for lab, who in SPLITS:
        q = K[(K.variant == name) & K.driver.isin(who)]
        print(f"  {name:<20}{lab:<14}{len(q):>8,}{100*q.own_fit.mean():>8.0f}%{q.r_fit.median():>8.3f}"
              f"{q.scale.median():>16.2f}{q.scale.quantile(.1):>8.2f}-{q.scale.quantile(.9):.2f}"
              f"{q.turn_windows.median():>14.0f}")
print(f"\n  start points with no calibration at all: {BL.shape[0] - K[K.variant == 'rate'].shape[0]}")
print("  scale = true turn per unit of gyro turn; 1.00 would mean the phone reports turns fully")

# ───────────────────────── 2 · heading error ─────────────────────────
def row(q):
    if not len(q):
        return f"{'-':>48}"
    return (f"{q.err_deg.median():>7.1f}°{q.err_deg.quantile(.9):>8.1f}°{100*(q.err_deg > 5).mean():>7.0f}%"
            f"{100*(q.err_deg > 10).mean():>7.0f}%{100*q.wrong_sign.mean():>9.1f}%")

for sset, c in (("moving", 1000), ("moving", 200)):
    head(f"2 · HEADING ERROR at {c} m, {sset} set — |gyro turning − true change of course|")
    print(f"  {'variant':<20}{'split':<14}{'blackouts':>10}{'median':>8}{'90th %':>9}{'> 5°':>8}{'> 10°':>8}"
          f"{'wrong sign':>12}")
    for name in VARIANTS + (REF,):
        for lab, who in SPLITS:
            q = E[(E.variant == name) & (E.set == sset) & (E.checkpoint == c) & E.driver.isin(who)]
            print(f"  {name:<20}{lab:<14}{len(q):>10,}{row(q)}")
    print(f"  wrong sign = gyro turned the opposite way, counted on blackouts whose true turn is at least "
          f"{SIGN_MIN_TURN_DEG:g}°")

# ───────────────────────── 3 · choice on A+B ─────────────────────────
head("3 · CHOICE — lowest median heading error at 1 km on the tuning drivers A+B (moving set)")
tune = E[E.driver.isin(TUNE) & (E.set == "moving") & (E.checkpoint == 1000)]
score = {name: tune[tune.variant == name].err_deg.median() for name in VARIANTS}
choice = min(score, key=score.get)
for name in VARIANTS:
    print(f"  {name:<20}{score[name]:>6.2f}°{'   <- chosen' if name == choice else ''}")
(ROOT/"outputs/Config/calibration_choice.txt").write_text(choice + "\n")
print(f"\n  written: round2/out/Config/calibration_choice.txt = {choice}")

# ───────────────────────── 4 · chosen by driving condition ─────────────────────────
head(f"4 · CHOSEN ({choice}) vs ROUND-1 REFERENCE — median heading error at 1 km by driving condition")
print(f"  {'group':<7}{'km/h':>7}{'set':>8}" + "".join(f"{lab:>31}" for lab, _ in SPLITS))
print(f"  {'':<22}" + "".join(f"{'chosen  |  reference  (n)':>31}" for _ in SPLITS))
for sset in ("moving", "stopgo"):
    for lo, hi, name in context.BANDS:
        cells = []
        for _, who in SPLITS:
            q = E[(E.set == sset) & (E.checkpoint == 1000) & (E.band == name) & E.driver.isin(who)]
            a, r = q[q.variant == choice].err_deg, q[q.variant == REF].err_deg
            cells.append(f"{a.median():.1f}°  |  {r.median():.1f}°  ({len(a):,})" if len(a) else "-")
        label = f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"
        print(f"  {name:<7}{label:>7}{sset:>8}" + "".join(f"{x:>31}" for x in cells))
log("done")
