"""Round 2 · Step 5 — the road-constrained particle filter, on the tuning drivers A and B only.

The filter (core/particle.py) gets only what core/engine_input.py allows: the last GNSS fix, the step-2 gyro
calibration and phone data from the start onward, plus the road network of step 4. D and E stay untouched until
step 7.

  1  what was run and how long it took
  2  2D position error against the step-3 map-free baseline, by driving condition
  3  drift by distance since the last real turn — the landmark-spacing view
  4  diagnostics: guesses surviving, re-seeds, fallbacks
Outputs: round2/out/Pipeline_Data/pf_errors.parquet, step5_run.txt.
Run from the repo root:  .venv/bin/python3 round2/step5_particlefilter.py [--limit N] [--particles N] [--seed N]"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, blackouts, context, calibration, engine_input, motion, particle, roadnet, scoring

T0 = time.time()
TUNE = ["A", "B"]
CHECKS = (50, 200, 1000)
def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
LIMIT, N_PART, SEED = arg("--limit", 40), arg("--particles", 500), arg("--seed", 0)
CHOICE = (ROOT/"outputs/Config/calibration_choice.txt").read_text().strip()
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")

BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet")
BL = BL[BL.driver.isin(TUNE) & BL.moving_1000].sort_values(["drive", "session", "row_start"]).reset_index(drop=True)
if LIMIT and LIMIT < len(BL):
    BL = BL.iloc[np.linspace(0, len(BL) - 1, LIMIT).astype(int)].reset_index(drop=True)   # spread over the sessions
DR = pd.read_parquet(ROOT/"outputs/Pipeline_Data/dr_errors.parquet")
DR = DR[(DR.variant == "engine") & (DR.set == "moving")].set_index(["drive", "session", "row_start", "checkpoint"])
net = roadnet.RoadNetwork()
log(f"network: {len(net.seg_u):,} segments · {len(BL):,} blackouts from {BL.groupby(['drive','session']).ngroups} "
    f"sessions · {N_PART} particles · calibration {CHOICE}")

recs, cache, spent = [], {}, []
for b in BL.itertuples(index=False):
    key = (b.drive, b.session)
    if key not in cache:
        S = sessions.load(b.drive, b.driver, int(b.session))
        cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}   # one session at a time
    S, C, stat = cache[key]
    i = b.row_start
    cps = [(c, getattr(b, f"end_{c}")) for c in CHECKS if getattr(b, f"moving_{c}")]
    if not cps:
        continue
    j_max = max(j for _, j in cps)
    cal = calibration.engine_calibration(C, i, CHOICE)
    if cal is None:
        continue
    inp = engine_input.build(S, cal, i, j_max)
    t0 = time.time()
    res = particle.run(inp, net, stat[i:j_max+1], [j - i for _, j in cps],
                       params=dict(n=N_PART), rng=np.random.default_rng(SEED + i))
    spent.append((time.time() - t0, j_max - i))
    got = {r: k for k, r in enumerate(res["rows"])}
    for c, j in cps:
        k = got.get(j - i)
        if k is None:
            continue
        pos, dist = scoring.errors(S, i, j, res["east"][k], res["north"][k], res["dist"][k])
        base = DR.loc[(b.drive, b.session, i, c)] if (b.drive, b.session, i, c) in DR.index else None
        recs.append(dict(driver=b.driver, drive=b.drive, session=int(b.session), row_start=int(i), checkpoint=c,
                         band=getattr(b, f"band_{c}"), turns=getattr(b, f"turns_{c}"),
                         since_turn_m=getattr(b, f"since_turn_m_{c}"), pf_pos=pos, pf_dist=dist,
                         base_pos=float(base.pos_err) if base is not None else np.nan,
                         base_dist=float(base.dist_err) if base is not None else np.nan,
                         ess=res["ess"][k], on_map=res["on_map"][k], reseeds=res["reseeds"],
                         reseed_failed=res["reseed_failed"], seeded=res["seeded"]))
P = pd.DataFrame(recs)
P.to_parquet(ROOT/"outputs/Pipeline_Data/pf_errors.parquet", index=False)
sec = np.array([s for s, _ in spent])
rows_ = np.array([r for _, r in spent])
log(f"{len(P):,} scored checkpoints · {sec.sum():.0f} s of filtering · {1000*sec.sum()/max(rows_.sum(), 1):.2f} ms "
    f"per simulated second · median {sec.mean():.2f} s per blackout")

head("1 · WHAT RAN")
print(f"  blackouts {P.row_start.nunique():,} (tuning drivers A and B, no stops, 1 km valid) · particles {N_PART} · "
      f"seed {SEED}")
print(f"  seeded on a road {100*P.groupby('row_start').seeded.first().mean():.0f}% · "
      f"re-seeds per blackout {P.groupby('row_start').reseeds.first().mean():.2f} · "
      f"failed re-seeds {P.groupby('row_start').reseed_failed.first().sum():.0f}")

head("2 · 2D POSITION ERROR — particle filter against the step-3 map-free baseline (median, share within 10%)")
print(f"  {'group':<7}{'km/h':>7}{'checkpoint':>12}{'blackouts':>11}{'baseline':>22}{'particle filter':>24}")
for lo, hi, name in context.BANDS:
    for c in CHECKS:
        q = P[(P.band == name) & (P.checkpoint == c)]
        if not len(q):
            continue
        label = f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"
        print(f"  {name:<7}{label:>7}{c:>10} m{len(q):>11,}"
              f"{q.base_pos.median():>15.1f}%  {100*(q.base_pos <= 10).mean():>3.0f}%"
              f"{q.pf_pos.median():>17.1f}%  {100*(q.pf_pos <= 10).mean():>3.0f}%")
print(f"\n  {'all':<7}{'':>7}{'':>12}")
for c in CHECKS:
    q = P[P.checkpoint == c]
    print(f"  {'all':<7}{'':>7}{c:>10} m{len(q):>11,}{q.base_pos.median():>15.1f}%  {100*(q.base_pos <= 10).mean():>3.0f}%"
          f"{q.pf_pos.median():>17.1f}%  {100*(q.pf_pos <= 10).mean():>3.0f}%")

head("3 · BY DISTANCE SINCE THE LAST REAL TURN (or since GPS was lost) — 1 km checkpoint")
q = P[P.checkpoint == 1000]
print(f"  {'distance back':<18}{'blackouts':>11}{'baseline':>14}{'particle filter':>18}")
for lo, hi in ((0, 250), (250, 500), (500, 750), (750, 1e9)):
    s = q[(q.since_turn_m >= lo) & (q.since_turn_m < hi)]
    if not len(s):
        continue
    label = f"{lo:g}-{hi:g} m" if hi < 1e8 else f"over {lo:g} m"
    print(f"  {label:<18}{len(s):>11,}{s.base_pos.median():>13.1f}%{s.pf_pos.median():>17.1f}%")

head("4 · DIAGNOSTICS")
print(f"  effective guesses at the checkpoint (median of {N_PART}): "
      + " · ".join(f"{c} m: {P[P.checkpoint == c].ess.median():.0f}" for c in CHECKS))
print(f"  estimates coming from the map rather than the fallback: "
      + " · ".join(f"{c} m: {100*P[P.checkpoint == c].on_map.mean():.0f}%" for c in CHECKS))
worse = P[(P.checkpoint == 1000) & (P.pf_pos > P.base_pos)]
print(f"  1 km blackouts where the filter did worse than no map: {len(worse)}/{len(P[P.checkpoint == 1000])} "
      f"(median {worse.pf_pos.median():.1f}% against {worse.base_pos.median():.1f}%)" if len(worse) else "")
log("done")
