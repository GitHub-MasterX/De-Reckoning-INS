"""Round 3 · the metric that matters — how far off the estimate was ALONG the whole blackout, not only at its end.

Round 2 reported the error at a checkpoint: where the estimate stood when the blackout had covered 50, 100, ... 1000 m.
That rewards an estimate that wanders hundreds of metres away and happens to be near the vehicle when the clock stops.
A driver watching the map would call that a failure, and so should we.

This script re-runs the frozen round-2 filter (out/pf_params.json, nothing retuned) and records the estimate every
second, so each blackout gets two numbers:

    end      2D error as % of distance travelled at the 1 km mark          — round 2's headline
    path     the average of that same % over the whole blackout            — what the estimate actually did

The average starts at FLOOR_M of travel: before that, a few metres of error is a meaningless percentage (5 m at 10 m
travelled is 50%). The same floor is used for the app's clip averages.

The map-free baseline (held speed + calibrated gyro, no map) is measured the same way, for contrast.

Nothing is tuned here and no setting is touched: this is measurement only. Test drivers stay test drivers.

Outputs: round2/out/round3_path_errors.parquet, round2/out/round3_path_metric_run.txt.
Run from the repo root:  .venv/bin/python3 round2/round3_path_metric.py [--limit N]
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, deadreckoning
from core.geo import enu

T0 = time.time()
SPLITS = (("D+E (test)", ["D", "E"]), ("A+B (tuning)", ["A", "B"]))
ORDER = ["E", "B", "A", "D"]
BANDS = ["slow", "mixed", "ps_60", "fast"]
BAND_LABEL = {"slow": "under 40", "mixed": "40-50", "ps_60": "50-70 (PS)", "fast": "70+"}
FLOOR_M = 100.0              # the average is taken from this much distance travelled onwards
SAMPLE_S = 1.0               # the estimate is recorded this often
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")


def pct_along(S, i, rows, east, north):
    """2D error as % of the distance the vehicle had travelled, at each recorded row."""
    j = i + np.asarray(rows, np.int64)
    te, tn = enu(S.lat[j], S.lon[j], S.lat[i], S.lon[i])
    dist = S.dist[j] - S.dist[i]
    err = np.hypot(east - te, north - tn)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(dist > 0, 100*err/dist, np.nan), dist


def main():
    limit = arg("--limit", 0)
    head("Round 3 · error along the whole blackout, against error at its end")
    print(f"  frozen settings {PARAMS} · calibration {CHOICE}")
    print(f"  the estimate is recorded every {SAMPLE_S:g} s; the average runs from {FLOOR_M:.0f} m of travel to 1 km")

    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"]).reset_index(drop=True)
    BL = BL[BL.moving_1000 & BL.end_1000.notna()]
    if limit:
        BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    net = roadnet.RoadNetwork()
    log(f"{len(BL):,} blackouts · network {len(net.seg_u):,} segments")

    recs, cache = [], {}
    for nb, b in enumerate(BL.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
            log(f"  {b.drive}/{b.session} ({b.driver}) — {nb:,}/{len(BL):,}")
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
        res = particle.run(inp, net, stat[i:j + 1], rows, params=PARAMS, rng=np.random.default_rng(i))
        pf_pct, dist = pct_along(S, i, res["rows"], res["east"], res["north"])
        de, dn, _ = deadreckoning.run(inp, stationary=stat[i:j + 1])
        base_pct, _ = pct_along(S, i, res["rows"], de[res["rows"]], dn[res["rows"]])
        m = dist >= FLOOR_M
        if m.sum() < 3:
            continue
        recs.append(dict(driver=b.driver, drive=b.drive, session=int(b.session), row_start=i,
                         band=b.band_1000, turns=b.turns_1000, since_turn_m=b.since_turn_m_1000,
                         pf_end=float(pf_pct[-1]), pf_path=float(np.nanmean(pf_pct[m])),
                         pf_worst=float(np.nanmax(pf_pct[m])),
                         base_end=float(base_pct[-1]), base_path=float(np.nanmean(base_pct[m]))))
    P = pd.DataFrame(recs)
    P.to_parquet(R2/"out/round3_path_errors.parquet", index=False)
    log(f"{len(P):,} blackouts scored -> round2/out/round3_path_errors.parquet")

    def table(q, by, order=None):
        print(f"  {'':<12}{'n':>6}{'END median':>12}{'end <10%':>10}{'PATH median':>13}{'path <10%':>11}"
              f"{'worst median':>14}{'no map path':>13}")
        keys = order or sorted(q[by].unique())
        for k in keys:
            g = q[q[by] == k]
            if g.empty:
                continue
            name = BAND_LABEL.get(k, k)
            print(f"  {name:<12}{len(g):>6}{g.pf_end.median():>11.1f}%{100*(g.pf_end < 10).mean():>9.0f}%"
                  f"{g.pf_path.median():>12.1f}%{100*(g.pf_path < 10).mean():>10.0f}%"
                  f"{g.pf_worst.median():>13.1f}%{g.base_path.median():>12.0f}%")
        print(f"  {'all':<12}{len(q):>6}{q.pf_end.median():>11.1f}%{100*(q.pf_end < 10).mean():>9.0f}%"
              f"{q.pf_path.median():>12.1f}%{100*(q.pf_path < 10).mean():>10.0f}%"
              f"{q.pf_worst.median():>13.1f}%{q.base_path.median():>12.0f}%")

    for lab, who in SPLITS:
        head(f"{lab} — by driver")
        table(P[P.driver.isin(who)], "driver", [d for d in ORDER if d in who])
        head(f"{lab} — by driving condition")
        table(P[P.driver.isin(who)], "band", BANDS)

    head("what the two numbers disagree about")
    q = P
    flat = q[(q.pf_end < 10) & (q.pf_path >= 10)]
    both = q[(q.pf_end < 10) & (q.pf_path < 10)]
    print(f"  blackouts that pass on the end number but fail on the path average: {len(flat):,} "
          f"({100*len(flat)/max(len(q),1):.0f}% of all, {100*len(flat)/max(len(q[q.pf_end < 10]),1):.0f}% of the ones that 'pass')")
    print(f"  blackouts that pass on both:                                        {len(both):,} "
          f"({100*len(both)/max(len(q),1):.0f}%)")
    if len(flat):
        print(f"  in the ones that only look good at the end, the estimate averaged {flat.pf_path.median():.0f}% "
              f"and reached {flat.pf_worst.median():.0f}% at its worst")
    print(f"\n  correlation between the end number and the path average: r = {q.pf_end.corr(q.pf_path):.2f}")
    print("  (that is the point: the end number says little about what the estimate did on the way)")


if __name__ == "__main__":
    main()
