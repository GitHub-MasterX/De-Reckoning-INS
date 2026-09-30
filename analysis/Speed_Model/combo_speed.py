"""Round 3 · the two ideas that survived, together — and one honest test.

Of everything tried for speed, two helped on the tuning drivers and both are narrow by design:

  turn readings   speed = sideways acceleration / turn rate, given to the filter as a measurement, only where the
                  phone's axes fit the GNSS history well (entry 41). Silent on phones that cannot feel a corner.
  regression      a car that was crawling at the last fix is usually faster a minute later, and one that was flying is
                  usually slower (measured: +4.5 m/s for starts under 8 m/s, -5 m/s for starts over 26). Applied only
                  where the effect is strong and the risk small — slow starts — and never on a fast road.

Both leave the common case alone, which is the lesson of every failed attempt: holding the last GNSS speed is a strong
prior, and anything that disturbs it without information costs more than it gains.

Run from the repo root:
    .venv/bin/python3 round2/combo_speed.py --stage tune [--limit 300]
    .venv/bin/python3 round2/combo_speed.py --stage test
Output: round2/out/combo_speed_{stage}.parquet, combo_speed_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"analysis/Speed_Model"))
sys.path.insert(0, str(ROOT/"analysis/Reporting_Metrics"))
from core import sessions, calibration, engine_input, motion, particle, roadnet, smooth
from accel_speed import fit_axes, readings, CHOICE, TUNE, FLOOR_M, MIN_FIT_R, HISTORY_S, FS
from shrink_speed import fit_curves, expected, road_is_fast
from excursions import track
from reporting_layer import measure, SAMPLE_S

T0 = time.time()
PARAMS = json.loads((ROOT/"outputs/Config/pf_params.json").read_text())
FIX = json.loads((ROOT/"outputs/Config/reporting_layer_choice.json").read_text())
SIGMA_OBS = 2.0
SLOW_START_MS = 11.0          # a fix below about 40 km/h: the regime where regression to the mean measurably helped

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")


def main():
    stage = arg("--stage", "tune")
    limit = arg("--limit", 300)
    who = TUNE if stage == "tune" else ["D", "E"]
    head(f"Round 3 · turn readings and regression to the mean, together — "
         f"{'tuning A+B' if stage == 'tune' else 'TEST D+E, one run'}")
    net = roadnet.RoadNetwork()
    _, curves = fit_curves(net)
    BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(who) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    log(f"{len(BL)} blackouts")

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
        stationary = stat[i:j + 1]
        t_all = inp.t - inp.t[0]
        h0 = max(0, i - int(HISTORY_S*FS))
        turn_hist = cal.scale*(S.gyr[h0:i] @ cal.axis) - cal.bias
        axes = fit_axes(S.acc[h0:i], turn_hist, S.v[h0:i], S.t[h0:i], stat[h0:i])
        reads = (readings(inp.acc, inp.turn_rate(), t_all, axes, stationary)
                 if axes is not None and axes["r"] >= MIN_FIT_R else None)
        has_read = reads is not None and bool(np.isfinite(reads).any())
        fast = road_is_fast(net, S, i)
        slow_start = inp.speed0 < SLOW_START_MS and not fast
        target = expected(curves, fast, inp.speed0, t_all) if slow_start else None

        tx, ty, ts = track(S, i, j)
        step = max(1, int(round(SAMPLE_S*10)))
        rows = list(range(step, j - i + 1, step))
        if len(rows) < 5:
            continue
        r = np.asarray(rows, np.int64)
        t = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3:
            continue
        rec = dict(driver=b.driver, band=b.band_1000, row_start=i, has_read=has_read, slow_start=slow_start)
        variants = ((("today", None, None), ("turn readings", reads if has_read else None, None),
                     ("regression", None, target), ("both", reads if has_read else None, target))
                    if stage == "tune" else
                    (("today", None, None), ("both", reads if has_read else None, target)))
        for name, obs, tgt in variants:
            params = dict(PARAMS)
            if obs is not None:
                params["sigma_speed_obs"] = SIGMA_OBS
            mt = smooth.ModeTracker(params.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                    FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
            res = particle.run(inp, net, stationary, rows, params=params, rng=np.random.default_rng(i),
                               estimator=mt, speed_obs=obs, speed_target=tgt)
            e, n = smooth.smooth_track(t, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                       inp.speed0, FIX["catch_up"], FIX["extra"],
                                       close_s=FIX["close_s"], max_factor=FIX["max_factor"])
            m = measure(e, n, t, tx[r], ty[r], ts[r], true_s, keep, v_true=S.v[i + r])
            rec[name] = m["path"]; rec[name + "_off"] = m["off"]; rec[name + "_worst"] = m["worst"]
        recs.append(rec)
    P = pd.DataFrame(recs)
    P.to_parquet(ROOT/f"outputs/Experiment_Results/combo_speed_{stage}.parquet", index=False)

    head("every blackout scored")
    print(f"  {len(P)} blackouts · {100*P.has_read.mean():.0f}% had a turn reading · "
          f"{100*P.slow_start.mean():.0f}% started slow on an ordinary road")
    print(f"\n  {'variant':<18}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}{'better':>9}")
    for name in (("today", "turn readings", "regression", "both") if stage == "tune" else ("today", "both")):
        better = "" if name == "today" else f"{100*(P[name] < P['today']).mean():>8.0f}%"
        print(f"  {name:<18}{100*(P[name] < 10).mean():>10.0f}%{P[name].median():>9.1f}%"
              f"{P[name + '_worst'].median():>10.1f}%{100*P[name + '_off'].mean():>10.0f}%{better}")
    head("where each one acts")
    q = P[P.has_read] if stage == "tune" else P.iloc[0:0]
    if len(q):
        print(f"  blackouts with a turn reading ({len(q)}): under 10% {100*(q['today'] < 10).mean():.0f}% -> "
              f"{100*(q['turn readings'] < 10).mean():.0f}%, path {q['today'].median():.1f}% -> "
              f"{q['turn readings'].median():.1f}%, off route {100*q['today_off'].mean():.0f}% -> "
              f"{100*q['turn readings_off'].mean():.0f}%")
    q = P[P.slow_start]
    if len(q) and "regression" in P:
        print(f"  blackouts starting slow ({len(q)}): under 10% {100*(q['today'] < 10).mean():.0f}% -> "
              f"{100*(q['regression'] < 10).mean():.0f}%, path {q['today'].median():.1f}% -> "
              f"{q['regression'].median():.1f}%, off route {100*q['today_off'].mean():.0f}% -> "
              f"{100*q['regression_off'].mean():.0f}%")
    if stage != "tune":
        q = P[P.slow_start]
        if len(q):
            print(f"  blackouts starting slow ({len(q)}): under 10% {100*(q['today'] < 10).mean():.0f}% -> "
                  f"{100*(q['both'] < 10).mean():.0f}%, path {q['today'].median():.1f}% -> {q['both'].median():.1f}%, "
                  f"off route {100*q['today_off'].mean():.0f}% -> {100*q['both_off'].mean():.0f}%")
    q = P[~P.has_read & ~P.slow_start]
    print(f"  blackouts neither touches ({len(q)}): unchanged by construction "
          f"({'yes' if len(q) == 0 or np.allclose(q['today'], q['both']) else 'NO — check'})")
    head("by driving condition (today -> both)")
    for band in ("slow", "mixed", "ps_60", "fast"):
        g = P[P.band == band]
        if len(g):
            print(f"  {band:<8} n={len(g):4d}   under 10% {100*(g['today'] < 10).mean():3.0f}% -> "
                  f"{100*(g['both'] < 10).mean():3.0f}%   path {g['today'].median():5.1f}% -> {g['both'].median():5.1f}%"
                  f"   off route {100*g['today_off'].mean():3.0f}% -> {100*g['both_off'].mean():3.0f}%")


if __name__ == "__main__":
    main()
