"""Round 2 · Step 6 — tune the particle filter on the tuning drivers A and B only, then freeze it.

Every setting is judged on the same fixed subset of A+B blackouts, with the same seeds. D and E are never read.

Rule, fixed before looking at any result:
  choose the lowest median 2D position error at 1 km, among the settings whose median at 50 m is no more than
  1 point worse than the map-free baseline's; ties go to the smaller share of blackouts made worse at 1 km.
  If no setting clears that bar, the run says so plainly and falls back to the same rule applied to the settings
  within 1 point of the best 50 m result actually achieved — never a silent bypass.
  Refined after the first run with the handover distance (disclosed in EXECUTION_LOG): several settings tied on both
  ruled numbers (50 m and 1 km) and the order then fell to chance, so the 200 m median decides such ties, ahead of
  the share made worse.

Outputs: round2/out/pf_params.json (the frozen settings), out/tuning.csv, step6_run.txt.
Run from the repo root:  .venv/bin/python3 round2/step6_tune.py [--limit N] [--particles N]"""
import warnings; warnings.filterwarnings("ignore")
import itertools, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, scoring

T0 = time.time()
TUNE = ["A", "B"]
CHECKS = (50, 200, 1000)
def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
LIMIT, N_PART = arg("--limit", 120), arg("--particles", 500)
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
GRID = dict(q_speed=(0.25, 0.40), sigma_turn_deg=(10.0,), sigma_abs_deg=(15.0,), dr_blend_m=(100.0,),
            straight_blend_m=(0.0, 150.0, 300.0))
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")

BL = pd.read_parquet(R2/"out/blackouts.parquet")
BL = BL[BL.driver.isin(TUNE) & BL.moving_1000].sort_values(["drive", "session", "row_start"]).reset_index(drop=True)
if LIMIT and LIMIT < len(BL):
    BL = BL.iloc[np.linspace(0, len(BL) - 1, LIMIT).astype(int)].reset_index(drop=True)
DR = pd.read_parquet(R2/"out/dr_errors.parquet")
DR = DR[(DR.variant == "engine") & (DR.set == "moving")].set_index(["drive", "session", "row_start", "checkpoint"])
net = roadnet.RoadNetwork()

# one pass over the blackouts, keeping what every setting needs
JOBS, cache = [], {}
for b in BL.itertuples(index=False):
    key = (b.drive, b.session)
    if key not in cache:
        S = sessions.load(b.drive, b.driver, int(b.session))
        cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
    S, C, stat = cache[key]
    i = b.row_start
    cps = [(c, getattr(b, f"end_{c}")) for c in CHECKS if getattr(b, f"moving_{c}")]
    cal = calibration.engine_calibration(C, i, CHOICE)
    if not cps or cal is None:
        continue
    j_max = max(j for _, j in cps)
    JOBS.append(dict(S=S, i=i, cps=cps, inp=engine_input.build(S, cal, i, j_max), stat=stat[i:j_max+1],
                     base={c: (float(DR.loc[(b.drive, b.session, i, c)].pos_err)
                               if (b.drive, b.session, i, c) in DR.index else np.nan) for c, _ in cps}))
log(f"{len(JOBS)} blackouts prepared from {BL.groupby(['drive','session']).ngroups} sessions · {N_PART} particles · "
    f"{int(np.prod([len(v) for v in GRID.values()]))} settings to try")

BASE = {c: np.nanmedian([j["base"][c] for j in JOBS if c in j["base"]]) for c in CHECKS}
print(f"  map-free baseline on this subset — " + " · ".join(f"{c} m: {BASE[c]:.1f}%" for c in CHECKS))

rows = []
names = list(GRID)
for values in itertools.product(*(GRID[k] for k in names)):
    params = dict(zip(names, values), n=N_PART)
    t0 = time.time()
    err = {c: [] for c in CHECKS}
    worse = {c: [] for c in CHECKS}
    ess = []
    for job in JOBS:
        res = particle.run(job["inp"], net, job["stat"], [j - job["i"] for _, j in job["cps"]],
                           params=params, rng=np.random.default_rng(job["i"]))
        got = {r: k for k, r in enumerate(res["rows"])}
        for c, j in job["cps"]:
            k = got.get(j - job["i"])
            if k is None:
                continue
            pos, _ = scoring.errors(job["S"], job["i"], j, res["east"][k], res["north"][k], res["dist"][k])
            err[c].append(pos)
            worse[c].append(pos > job["base"][c])
            if c == 1000:
                ess.append(res["ess"][k])
    row = dict(zip(names, values))
    row.update({f"p50_{c}": float(np.median(err[c])) for c in CHECKS})
    row.update({f"pass_{c}": float(np.mean(np.array(err[c]) <= 10)) for c in CHECKS})
    row.update(worse_1000=float(np.mean(worse[1000])), ess_1000=float(np.nanmedian(ess)), seconds=time.time() - t0)
    rows.append(row)
    log(f"  {', '.join(f'{k}={v}' for k, v in zip(names, values))}  ->  50 m {row['p50_50']:.1f}% · "
        f"200 m {row['p50_200']:.1f}% · 1 km {row['p50_1000']:.1f}% · worse than no map {100*row['worse_1000']:.0f}%")
TUNING = pd.DataFrame(rows).sort_values("p50_1000").reset_index(drop=True)
TUNING.to_csv(R2/"out/tuning.csv", index=False)

head("1 · EVERY SETTING TRIED, best 1 km first")
show = TUNING.copy()
for c in CHECKS:
    show[f"pass_{c}"] = (100*show[f"pass_{c}"]).round(0)
show["worse_1000"] = (100*show.worse_1000).round(0)
print(show.round(3).to_string(index=False))

head("2 · THE CHOICE")
ok = TUNING[TUNING.p50_50 <= BASE[50] + 1.0]
print(f"  settings whose 50 m median is within 1 point of the baseline's {BASE[50]:.1f}%: {len(ok)} of {len(TUNING)}")
if not len(ok):
    floor = TUNING.p50_50.min()
    ok = TUNING[TUNING.p50_50 <= floor + 1.0]
    print(f"  NONE cleared that bar. Falling back, as the rule says, to the {len(ok)} settings within 1 point of the "
          f"best 50 m result reached here ({floor:.1f}%) — the map cannot beat a fresh fix at 50 m.")
pick = ok.sort_values(["p50_1000", "p50_200", "worse_1000"]).iloc[0]
chosen = {k: (float(pick[k]) if k != "n" else int(pick[k])) for k in names}
chosen["n"] = N_PART
(R2/"out/pf_params.json").write_text(json.dumps(chosen, indent=2) + "\n")
print("  chosen: " + ", ".join(f"{k}={v}" for k, v in chosen.items()))
print(f"  on the tuning subset: 50 m {pick.p50_50:.1f}% (baseline {BASE[50]:.1f}%) · "
      f"200 m {pick.p50_200:.1f}% ({BASE[200]:.1f}%) · 1 km {pick.p50_1000:.1f}% ({BASE[1000]:.1f}%) · "
      f"worse than no map at 1 km {100*pick.worse_1000:.0f}%")
print("  written: round2/out/pf_params.json")
log("done")
