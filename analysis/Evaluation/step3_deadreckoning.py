"""Round 2 · Step 3 — map-free 2D dead reckoning: the honest baseline the map has to beat.

Engine (core/deadreckoning.py), per blackout, from core/engine_input.py only:
  heading   last GNSS course + turning from the step-2 calibrated gyro
  speed     last GNSS speed, held; zero while the motion classifier says stationary (ZUPT)
  position  speed × heading, integrated on the phone clock
Stationary detection: the round-1 motion classifier on raw phone IMU, each driver scored by the model trained
without them (core/motion.py).
Diagnostics — truth, reporting only: the engine's speed with the true heading; the true speed with the engine's heading.

  1  classifier on honest input, and the batch features against the feature contract
  2  2D position error by driving condition, moving set, 50 m and 1 km, with the share passing the PS 10%
  3  the same for the stop-and-go set
  4  where the 2D error comes from — speed or heading
  5  what the ZUPT does
  6  per driver
Outputs: round2/out/Pipeline_Data/dr_errors.parquet, step3_run.txt.  Run from the repo root:  .venv/bin/python3 round2/step3_deadreckoning.py"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, blackouts, context, calibration, engine_input, motion, deadreckoning, scoring

T0 = time.time()
TUNE, TEST = ["A", "B"], ["D", "E"]
SPLITS = (("A+B (tuning)", TUNE), ("D+E (test)", TEST))
ORDER = ["E", "B", "A", "D"]
CHOICE = (ROOT/"outputs/Config/calibration_choice.txt").read_text().strip()
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*112}\n{t}\n{'='*112}")
def band_label(lo, hi): return f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"

BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet")
recs, cls, gap = [], [], None
for (drive, session), g in BL.groupby(["drive", "session"], sort=False):
    driver = g.driver.iloc[0]
    S = sessions.load(drive, driver, int(session))
    C = calibration.Calibrator(S)
    stat, starts, stat_w = motion.stationary_rows(S, driver)

    # classifier check: raw gyro (engine) against round 1's input (gyro minus a bias found with truth)
    raw = pd.read_parquet(ROOT/f"data/clean/{drive}.parquet", columns=["session", "aligned_valid", "gx_c", "gy_c", "gz_c"])
    keep = (raw.session.to_numpy() == session) & raw.aligned_valid.to_numpy()
    _, stat_ref = motion.predict_stationary(S.acc, raw.loc[keep, ["gx_c", "gy_c", "gz_c"]].to_numpy(float), driver)
    idx = starts[:, None] + np.arange(motion.WINDOW_SAMPLES)[None, :]
    kmh = 3.6*S.v[idx]
    label = np.where(kmh.max(1) < 1.0, 0, np.where(kmh.min(1) > 5.0, 1, -1))
    cls.append(dict(driver=driver, label=label, engine=stat_w, round1=stat_ref))
    if gap is None:
        pick = np.random.default_rng(0).choice(len(starts), size=min(300, len(starts)), replace=False)
        gap = motion.contract_gap(S.acc, S.gyr, starts[pick])

    for b in g.itertuples(index=False):
        i = b.row_start
        cps = [(sset, c, getattr(b, f"end_{c}")) for c in blackouts.CHECKPOINTS for sset in ("moving", "stopgo")
               if getattr(b, f"{sset}_{c}")]
        if not cps:
            continue
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None:
            continue
        j_max = max(j for _, _, j in cps)
        inp = engine_input.build(S, cal, i, j_max)
        zupt = stat[i:j_max+1]
        runs = {"engine": deadreckoning.run(inp, stationary=zupt),
                "engine_no_zupt": deadreckoning.run(inp),
                "diag_true_heading": deadreckoning.run(inp, stationary=zupt, heading=C.psi[i:j_max+1]),
                "diag_true_speed": deadreckoning.run(inp, speed=S.v[i:j_max+1])}
        for sset, c, j in cps:
            k = j - i
            td = S.dist[j] - S.dist[i]
            for name, (e, n_, d) in runs.items():
                pos, dist = scoring.errors(S, i, j, e[k], n_[k], d[k])
                recs.append(dict(driver=driver, drive=drive, session=int(session), row_start=int(i), set=sset,
                                 checkpoint=c, band=getattr(b, f"band_{c}"), turns=getattr(b, f"turns_{c}"),
                                 since_turn_m=getattr(b, f"since_turn_m_{c}"), variant=name,
                                 pos_err=pos, dist_err=dist, pos_m=pos*td/100))
R = pd.DataFrame(recs)
R.to_parquet(ROOT/"outputs/Pipeline_Data/dr_errors.parquet", index=False)
log(f"calibration: {CHOICE}; {R.row_start.nunique():,} start points; {len(R):,} error records -> round2/out/Pipeline_Data/dr_errors.parquet")

# ───────────────────────── 1 · classifier ─────────────────────────
head("1 · MOTION CLASSIFIER ON HONEST INPUT — every labelled 2 s window of every session, model never saw the driver")
print(f"  batch features vs the feature contract (300 windows): largest difference {gap:.2e}\n")
print(f"  {'split':<14}{'input':<34}{'windows':>9}{'accuracy':>10}{'stationary recall':>19}{'stationary precision':>22}")
for lab, who in SPLITS:
    rows = [x for x in cls if x["driver"] in who]
    y = np.concatenate([x["label"] for x in rows])
    for key, name in (("engine", "raw phone gyro (engine)"), ("round1", "gyro minus truth-found bias (round 1)")):
        p = np.concatenate([x[key] for x in rows])
        m = y >= 0
        yy, pp = y[m], p[m]
        truth_stat, pred_stat = yy == 0, pp
        acc = ((pp & truth_stat) | (~pp & ~truth_stat)).mean()
        rec = (pp & truth_stat).sum()/max(truth_stat.sum(), 1)
        prec = (pp & truth_stat).sum()/max(pred_stat.sum(), 1)
        print(f"  {lab:<14}{name:<34}{m.sum():>9,}{100*acc:>9.1f}%{100*rec:>18.1f}%{100*prec:>21.1f}%")

# ───────────────────────── 2, 3 · by driving condition ─────────────────────────
def cell(q, col="pos_err"):
    if not len(q):
        return "-"
    return f"{q[col].median():.1f}%  pass {100*(q[col] <= 10).mean():.0f}%  (n={len(q):,})"

for number, sset, title in (("2", "moving", "moving set"), ("3", "stopgo", "stop-and-go set")):
    head(f"{number} · ENGINE — 2D POSITION ERROR by driving condition, {title}   (median · share within the PS 10% · blackouts)")
    print(f"  {'group':<7}{'km/h':>7}{'checkpoint':>12}" + "".join(f"{lab:>40}" for lab, _ in SPLITS))
    for lo, hi, name in context.BANDS:
        for c in (50, 1000):
            q = R[(R.variant == "engine") & (R.set == sset) & (R.band == name) & (R.checkpoint == c)]
            print(f"  {name:<7}{band_label(lo, hi):>7}{c:>10} m" + "".join(f"{cell(q[q.driver.isin(who)]):>40}"
                                                                        for _, who in SPLITS))

# ───────────────────────── 4 · error sources ─────────────────────────
head("4 · WHERE THE 2D ERROR COMES FROM — moving set, 1 km, median 2D position error")
print("  engine            : gyro heading + held GNSS speed with ZUPT")
print("  true heading      : the engine's speed with the true heading  -> what the speed alone costs")
print("  true speed        : the true speed with the engine's heading  -> what the heading alone costs")
print("  distance error    : the engine's distance travelled against the true distance\n")
print(f"  {'group':<7}{'km/h':>7}{'split':>15}{'blackouts':>11}{'engine':>10}{'true heading':>14}{'true speed':>12}"
      f"{'distance error':>16}{'median error':>14}")
for lo, hi, name in context.BANDS:
    for lab, who in SPLITS:
        q = R[(R.set == "moving") & (R.checkpoint == 1000) & (R.band == name) & R.driver.isin(who)]
        e = q[q.variant == "engine"]
        if not len(e):
            continue
        print(f"  {name:<7}{band_label(lo, hi):>7}{lab.split()[0]:>15}{len(e):>11,}{e.pos_err.median():>9.1f}%"
              f"{q[q.variant == 'diag_true_heading'].pos_err.median():>13.1f}%"
              f"{q[q.variant == 'diag_true_speed'].pos_err.median():>11.1f}%{e.dist_err.median():>15.1f}%"
              f"{e.pos_m.median():>12.0f} m")

# ───────────────────────── 5 · ZUPT ─────────────────────────
head("5 · WHAT THE ZUPT DOES — median 2D position error at 1 km, with ZUPT | without")
print(f"  {'set':<10}" + "".join(f"{lab:>30}" for lab, _ in SPLITS))
for sset in ("moving", "stopgo"):
    cells = []
    for _, who in SPLITS:
        q = R[(R.set == sset) & (R.checkpoint == 1000) & R.driver.isin(who)]
        cells.append(f"{q[q.variant == 'engine'].pos_err.median():.1f}%  |  {q[q.variant == 'engine_no_zupt'].pos_err.median():.1f}%")
    print(f"  {sset:<10}" + "".join(f"{x:>30}" for x in cells))

# ───────────────────────── 6 · per driver ─────────────────────────
head("6 · PER DRIVER — engine, moving set, median 2D position error | distance error (every blackout equal)")
print(f"  {'checkpoint':<12}" + "".join(f"{'driver ' + D:>20}" for D in ORDER))
for c in blackouts.CHECKPOINTS:
    q = R[(R.variant == "engine") & (R.set == "moving") & (R.checkpoint == c)]
    print(f"  {c:>7} m   " + "".join(f"{q[q.driver == D].pos_err.median():>11.1f}% | {q[q.driver == D].dist_err.median():>4.1f}%"
                                     for D in ORDER))
log("done")
