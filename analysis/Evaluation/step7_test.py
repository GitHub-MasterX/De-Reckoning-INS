"""Round 2 · Step 7 — the frozen filter, run once on the test drivers D and E.

Nothing here is chosen: the settings come from round2/out/Config/pf_params.json, frozen in step 6 on A and B alone, and the
filter sees only what core/engine_input.py allows (last GNSS fix, step-2 calibration, phone data) plus the step-4
road network. A and B are reported alongside, as the drivers the settings were tuned on.

  1  what ran
  2  2D position error by driving condition, against the step-3 map-free baseline — the headline
  3  the problem statement's two benchmarks
  4  drift by distance since the last real turn — the landmark-spacing view
  5  per driver, and stop-and-go
  6  diagnostics, and where the filter did worse than no map
Outputs: round2/out/Pipeline_Data/test_errors.parquet, step7_run.txt.
Run from the repo root:  .venv/bin/python3 round2/step7_test.py [--limit N]"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, blackouts, context, calibration, engine_input, motion, particle, roadnet, scoring

T0 = time.time()
SPLITS = (("D+E (test)", ["D", "E"]), ("A+B (tuning)", ["A", "B"]))
ORDER = ["E", "B", "A", "D"]
CHECKS = blackouts.CHECKPOINTS
def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
LIMIT = arg("--limit", 0)
PARAMS = json.loads((ROOT/"outputs/Config/pf_params.json").read_text())
CHOICE = (ROOT/"outputs/Config/calibration_choice.txt").read_text().strip()
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*108}\n{t}\n{'='*108}")
def band_label(lo, hi): return f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"

BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet").sort_values(["drive", "session", "row_start"]).reset_index(drop=True)
BL = BL[BL[[f"{s}_{c}" for s in ("moving", "stopgo") for c in CHECKS]].any(axis=1)]
if LIMIT:
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(LIMIT, len(BL))).astype(int)].reset_index(drop=True)
DR = pd.read_parquet(ROOT/"outputs/Pipeline_Data/dr_errors.parquet")
DR = DR[DR.variant == "engine"].set_index(["drive", "session", "row_start", "set", "checkpoint"])
net = roadnet.RoadNetwork()
log(f"settings {PARAMS} · calibration {CHOICE} · {len(BL):,} start points · network {len(net.seg_u):,} segments")

recs, cache = [], {}
for nb, b in enumerate(BL.itertuples(index=False)):
    key = (b.drive, b.session)
    if key not in cache:
        S = sessions.load(b.drive, b.driver, int(b.session))
        cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
        log(f"  {b.drive}/{b.session} ({b.driver}) — {nb:,}/{len(BL):,} start points done")
    S, C, stat = cache[key]
    i = b.row_start
    cps = [(s, c, getattr(b, f"end_{c}")) for c in CHECKS for s in ("moving", "stopgo") if getattr(b, f"{s}_{c}")]
    cal = calibration.engine_calibration(C, i, CHOICE)
    if not cps or cal is None:
        continue
    j_max = max(j for _, _, j in cps)
    inp = engine_input.build(S, cal, i, j_max)
    res = particle.run(inp, net, stat[i:j_max+1], sorted({j - i for _, _, j in cps}),
                       params=PARAMS, rng=np.random.default_rng(i))
    got = {r: k for k, r in enumerate(res["rows"])}
    for sset, c, j in cps:
        k = got.get(j - i)
        if k is None:
            continue
        pos, dist = scoring.errors(S, i, j, res["east"][k], res["north"][k], res["dist"][k])
        base = DR.loc[(b.drive, b.session, i, sset, c)] if (b.drive, b.session, i, sset, c) in DR.index else None
        recs.append(dict(driver=b.driver, drive=b.drive, session=int(b.session), row_start=int(i), set=sset,
                         checkpoint=c, band=getattr(b, f"band_{c}"), turns=getattr(b, f"turns_{c}"),
                         since_turn_m=getattr(b, f"since_turn_m_{c}"), pf_pos=pos, pf_dist=dist,
                         base_pos=float(base.pos_err) if base is not None else np.nan,
                         base_dist=float(base.dist_err) if base is not None else np.nan,
                         ess=res["ess"][k], on_map=res["on_map"][k], reseeds=res["reseeds"],
                         reseed_failed=res["reseed_failed"], seeded=res["seeded"]))
P = pd.DataFrame(recs)
P.to_parquet(ROOT/"outputs/Pipeline_Data/test_errors.parquet", index=False)
log(f"{len(P):,} scored checkpoints from {P.row_start.nunique():,} blackouts -> round2/out/Pipeline_Data/test_errors.parquet")

head("1 · WHAT RAN")
print(f"  settings frozen in step 6 on A+B only: " + ", ".join(f"{k}={v}" for k, v in PARAMS.items()))
for lab, who in SPLITS:
    q = P[P.driver.isin(who)]
    starts = q.groupby(["drive", "session", "row_start"]).first()
    print(f"  {lab:<14}{q.row_start.nunique():>6,} blackouts · {q.groupby(['drive','session']).ngroups} sessions · "
          f"seeded on a road {100*starts.seeded.mean():.0f}% · re-seeds per blackout {starts.reseeds.mean():.2f} · "
          f"failed re-seeds {int(starts.reseed_failed.sum())}")

head("2 · 2D POSITION ERROR — frozen filter against the step-3 map-free baseline (median · share within the PS 10%)")
for lab, who in SPLITS:
    print(f"\n  {lab}")
    print(f"  {'group':<7}{'km/h':>7}{'checkpoint':>12}{'blackouts':>11}{'baseline':>22}{'particle filter':>24}")
    for lo, hi, name in context.BANDS:
        for c in (50, 1000):
            q = P[(P.set == "moving") & (P.band == name) & (P.checkpoint == c) & P.driver.isin(who)]
            if not len(q):
                continue
            print(f"  {name:<7}{band_label(lo, hi):>7}{c:>10} m{len(q):>11,}"
                  f"{q.base_pos.median():>15.1f}%  {100*(q.base_pos <= 10).mean():>3.0f}%"
                  f"{q.pf_pos.median():>17.1f}%  {100*(q.pf_pos <= 10).mean():>3.0f}%")

head("3 · THE PROBLEM STATEMENT'S BENCHMARKS — 5 m over 50 m, 100 m over 1 km (moving set)")
print(f"  {'split':<14}{'checkpoint':>12}{'blackouts':>11}{'baseline: median · pass':>28}{'filter: median · pass':>26}")
for lab, who in SPLITS:
    for c in (50, 1000):
        q = P[(P.set == "moving") & (P.checkpoint == c) & P.driver.isin(who)]
        print(f"  {lab:<14}{c:>10} m{len(q):>11,}"
              f"{q.base_pos.median():>19.1f}% · {100*(q.base_pos <= 10).mean():>3.0f}%"
              f"{q.pf_pos.median():>19.1f}% · {100*(q.pf_pos <= 10).mean():>3.0f}%")

head("4 · BY DISTANCE SINCE THE LAST REAL TURN (or since GPS was lost) — 1 km, moving set")
print(f"  {'split':<14}{'distance back':<16}{'blackouts':>11}{'baseline':>12}{'filter':>10}")
for lab, who in SPLITS:
    for lo, hi in ((0, 250), (250, 500), (500, 750), (750, 1e9)):
        q = P[(P.set == "moving") & (P.checkpoint == 1000) & P.driver.isin(who)
              & (P.since_turn_m >= lo) & (P.since_turn_m < hi)]
        if not len(q):
            continue
        label = f"{lo:g}-{hi:g} m" if hi < 1e8 else f"over {lo:g} m"
        print(f"  {lab:<14}{label:<16}{len(q):>11,}{q.base_pos.median():>11.1f}%{q.pf_pos.median():>9.1f}%")

head("5 · PER DRIVER AND STOP-AND-GO — median 2D position error, baseline | filter")
print(f"  {'set':<9}{'checkpoint':>12}" + "".join(f"{'driver ' + D:>20}" for D in ORDER))
for sset in ("moving", "stopgo"):
    for c in (50, 1000):
        cells = []
        for D in ORDER:
            q = P[(P.set == sset) & (P.checkpoint == c) & (P.driver == D)]
            cells.append(f"{q.base_pos.median():.1f}% | {q.pf_pos.median():.1f}%" if len(q) else "-")
        print(f"  {sset:<9}{c:>10} m" + "".join(f"{x:>20}" for x in cells))

head("6 · DIAGNOSTICS")
for lab, who in SPLITS:
    q = P[(P.set == "moving") & (P.checkpoint == 1000) & P.driver.isin(who)]
    worse = q[q.pf_pos > q.base_pos]
    print(f"  {lab:<14}effective guesses {q.ess.median():.0f}/{PARAMS.get('n', 500)} · from the map (not the "
          f"fallback) {100*q.on_map.mean():.0f}% · worse than no map {100*len(worse)/max(len(q), 1):.0f}% of blackouts "
          f"(median {worse.pf_pos.median():.1f}% against {worse.base_pos.median():.1f}%)")
log("done")
