"""Leak check — can anything from the true track after a blackout starts reach the engine?

1  Runtime test. For a sample of blackouts from every driver, every ground-truth value AFTER the blackout start —
   vehicle latitude, longitude, course, speed, distance, dropout flag — is overwritten with random garbage, and the
   engine is run again with the same random seed. If the calibration, the stop detection, the map-free dead
   reckoning and the particle filter all come out bit-for-bit identical, nothing after the start can have been used.
2  Static listing. Every line in the engine-path modules that reads a ground-truth field, to be explained.

Output: round2/out/leak_check_run.txt.  Run from the repo root:  .venv/bin/python3 round2/analysis/leak_check.py"""
import warnings; warnings.filterwarnings("ignore")
import json, re, sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
sys.path.insert(0, str(ROOT))
from core import sessions, calibration, deadreckoning, engine_input, motion, particle, roadnet

PARAMS = json.loads((ROOT/"outputs/Config/pf_params.json").read_text())
CHOICE = (ROOT/"outputs/Config/calibration_choice.txt").read_text().strip()
PER_DRIVER = 10
garbage = np.random.default_rng(1)


def poisoned(S, i):
    """A copy of the session with every ground-truth value after row i replaced by random garbage."""
    m = len(S.t) - (i + 1)
    return replace(S,
                   lat=np.r_[S.lat[:i+1], garbage.uniform(-90, 90, m)],
                   lon=np.r_[S.lon[:i+1], garbage.uniform(-180, 180, m)],
                   heading=np.r_[S.heading[:i+1], garbage.uniform(0, 360, m)],
                   v=np.r_[S.v[:i+1], garbage.uniform(0, 60, m)],
                   dist=np.r_[S.dist[:i+1], garbage.uniform(0, 1e5, m)],
                   dropout=np.r_[S.dropout[:i+1], garbage.random(m) < 0.5])


def run_engine(S, driver, i, j, net):
    C = calibration.Calibrator(S)
    stat = motion.stationary_rows(S, driver)[0][i:j+1]
    cal = calibration.engine_calibration(C, i, CHOICE)
    inp = engine_input.build(S, cal, i, j)
    res = particle.run(inp, net, stat, list(range(10, j - i + 1, 10)), params=PARAMS, rng=np.random.default_rng(i))
    return cal, stat, deadreckoning.run(inp, stationary=stat), res


BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet")
BL = BL[BL.moving_1000]
pick = pd.concat([g.sample(min(PER_DRIVER, len(g)), random_state=0) for _, g in BL.groupby("driver")])
net = roadnet.RoadNetwork()

print("1 · RUNTIME TEST — true track after the blackout start replaced by random garbage, engine re-run, same seed\n")
rows, cache = [], {}
for b in pick.sort_values(["drive", "session", "row_start"]).itertuples(index=False):
    key = (b.drive, b.session)
    if key not in cache:
        cache = {key: sessions.load(b.drive, b.driver, int(b.session))}
    S = cache[key]
    i, j = int(b.row_start), int(b.end_1000)
    c1, s1, d1, r1 = run_engine(S, b.driver, i, j, net)
    c2, s2, d2, r2 = run_engine(poisoned(S, i), b.driver, i, j, net)
    rows.append(dict(
        driver=b.driver,
        calibration=bool(np.array_equal(c1.axis, c2.axis) and c1.scale == c2.scale and c1.bias == c2.bias),
        stop_detection=bool(np.array_equal(s1, s2)),
        dead_reckoning=all(np.array_equal(a, z) for a, z in zip(d1, d2)),
        particle_filter=all(np.array_equal(np.asarray(r1[k]), np.asarray(r2[k])) for k in ("east", "north", "dist"))))
T = pd.DataFrame(rows)
print(f"  {'driver':<8}{'blackouts':>10}{'calibration':>14}{'stop detection':>16}{'dead reckoning':>16}{'particle filter':>17}")
for D, q in T.groupby("driver"):
    print(f"  {D:<8}{len(q):>10}" + "".join(f"{f'{q[c].sum()}/{len(q)} same':>{w}}" for c, w in
                                          (("calibration", 14), ("stop_detection", 16),
                                           ("dead_reckoning", 16), ("particle_filter", 17))))
all_same = bool(T[["calibration", "stop_detection", "dead_reckoning", "particle_filter"]].all().all())
print(f"\n  {len(T)} blackouts · {'EVERY OUTPUT IDENTICAL — no ground truth after the start reaches the engine' if all_same else 'DIFFERENCES FOUND — ground truth leaks into the engine'}")

print("\n2 · STATIC LISTING — every read of a ground-truth field in the engine-path modules\n")
TRUTH = re.compile(r"\bS\.(lat|lon|heading|v|dist|dropout)\b|speed_best")
for name in ("engine_input", "particle", "deadreckoning", "motion", "roadnet", "calibration"):
    SUBFOLDER = {"engine_input": "Foundation", "particle": "Engine", "deadreckoning": "Engine",
             "motion": "Engine", "roadnet": "Engine", "calibration": "Engine"}
    path = ROOT/"core"/SUBFOLDER[name]/f"{name}.py"
    hits = [(n, line.rstrip()) for n, line in enumerate(path.read_text().splitlines(), 1) if TRUTH.search(line)]
    print(f"  core/{name}.py — {len(hits)} read{'s' if len(hits) != 1 else ''}")
    for n, line in hits:
        print(f"    {n:>4}: {line.strip()}")
