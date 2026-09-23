"""Round 3 · can the filter itself be made to pass the 10% benchmark along the path?

The reporting layer (core/smooth.py) fixed how the position is shown. What is left is the filter's own failures: it
commits to a road that is not the one being driven, and then everything after that is wrong. The question here is
whether that comes from the filter collapsing its hypotheses too early — too few guesses, resampled too eagerly, with
too little spread in speed — and whether more diversity buys a higher share of blackouts under 10%.

Scored the way the professor's benchmark is read from now on: the 2D error averaged along the whole blackout, as a %
of the distance travelled, and the share of blackouts where that average is under 10%. Every variant is reported
through the round-3 reporting layer, so what changes between rows is the filter, not the cursor.

Tuning drivers A and B only. The test drivers are not touched by this file.

Outputs: round2/out/round3_engine_sweep.parquet, round2/out/round3_engine_sweep_run.txt.
Run from the repo root:  .venv/bin/python3 round2/round3_engine_sweep.py [--limit 200]
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, smooth
from round3_excursions import track, decompose, episodes, OFF_M
from round3_report_fix import measure, FLOOR_M, SAMPLE_S

T0 = time.time()
TUNE = ["A", "B"]
BASE = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())

# What might be keeping the filter from holding the right road: too few guesses, resampling as soon as they disagree,
# too little room in speed, and a heading test so tight that the true road is squeezed out at a junction.
VARIANTS = {
    "round 3 (as it stands)": {},
    "same way +0.4": dict(same_way_bonus=0.4),
    "same way +0.7": dict(same_way_bonus=0.7),
    "same way +1.0": dict(same_way_bonus=1.0),
}

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")


def main():
    limit = arg("--limit", 200)
    head("Round 3 · does a less decisive filter pass the benchmark more often?  (tuning drivers A+B)")
    print(f"  baseline {BASE} · reporting {FIX}")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    net = roadnet.RoadNetwork()
    log(f"{len(BL)} blackouts · {len(VARIANTS)} variants")

    recs, cache = [], {}
    for nb, b in enumerate(BL.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
            log(f"  {b.drive}/{b.session} ({b.driver}) — {nb}/{len(BL)}")
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None:
            continue
        inp = engine_input.build(S, cal, i, j)
        step = max(1, int(round(SAMPLE_S*10)))
        rows = list(range(step, j - i + 1, step))
        if len(rows) < 5:
            continue
        tx_all, ty_all, ts = track(S, i, j)
        r = np.asarray(rows, np.int64)
        t = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3:
            continue
        for name, over in VARIANTS.items():
            params = dict(BASE); params.update(over)
            mt = smooth.ModeTracker(params.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                    FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
            res = particle.run(inp, net, stat[i:j + 1], rows, params=params,
                               rng=np.random.default_rng(i), estimator=mt)
            e, n = smooth.smooth_track(t, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                       inp.speed0, FIX["catch_up"], FIX["extra"],
                                       close_s=FIX["close_s"], max_factor=FIX["max_factor"])
            m = measure(e, n, t, tx_all[r], ty_all[r], ts[r], true_s, keep, v_true=S.v[i + r])
            m.update(variant=name, driver=b.driver, band=b.band_1000, row_start=i, drive=b.drive)
            recs.append(m)
    P = pd.DataFrame(recs)
    P.to_parquet(R2/"out/round3_engine_sweep.parquet", index=False)

    head("share of blackouts whose average error along the path is under 10% — the benchmark")
    print(f"  {'variant':<26}{'n':>5}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}"
          f"{'lag':>7}{'seconds':>9}")
    base_t = None
    for name in VARIANTS:
        g = P[P.variant == name]
        if g.empty:
            continue
        print(f"  {name:<26}{len(g):>5}{100*(g.path < 10).mean():>10.0f}%{g.path.median():>9.1f}%"
              f"{g.worst.median():>10.1f}%{100*g.off.mean():>10.0f}%{g.lag_m.median():>6.0f}m")
    head("by driving condition, for the best few")
    best = (P.groupby("variant").apply(lambda g: (g.path < 10).mean()).sort_values(ascending=False).index[:3])
    for name in best:
        g = P[P.variant == name]
        print(f"\n  {name}")
        for band in ("slow", "mixed", "ps_60", "fast"):
            q = g[g.band == band]
            if len(q):
                print(f"    {band:<8} n={len(q):4d}  under 10% {100*(q.path < 10).mean():3.0f}%  "
                      f"path {q.path.median():5.1f}%  off route {100*q.off.mean():3.0f}%")


if __name__ == "__main__":
    main()
