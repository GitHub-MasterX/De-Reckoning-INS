"""Round 3 · the turn reading where it actually matters — inside the map filter, at the junction.

Entry 39 fed the accelerometer's turn readings into plain dead reckoning and they were too sparse to help. But the
blackouts that fail do not fail gradually: they fail at a junction, when the filter, carried along at the wrong speed,
meets a fork and takes the wrong branch. A turn reading exists precisely then — it is produced *by* the cornering.

So this gives the reading to the filter instead of to dead reckoning: at each update, guesses whose speed disagrees
with the measured one lose weight. The reading does not have to carry the whole blackout; it only has to be there when
the map is choosing.

Tuning drivers only. Run from the repo root:  .venv/bin/python3 round2/round3_turn_speed_pf.py [--limit 150]
Output: round2/out/round3_turn_speed_pf_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, smooth
from round3_accel_speed import fit_axes, readings, CHOICE, HISTORY_S, FS, TUNE, MIN_FIT_R
from round3_excursions import track, decompose, episodes, OFF_M
from round3_report_fix import measure, FLOOR_M, SAMPLE_S

T0 = time.time()
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())
SIGMAS = (2.0, 4.0, 8.0)          # how much to trust a reading, m/s
CHOSEN = 2.0                      # frozen on A+B (101 blackouts): under 10% 57% -> 61%, off route 29% -> 23%

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    limit = arg("--limit", 150)
    stage = arg("--stage", "tune")
    who = TUNE if stage == "tune" else ["D", "E"]
    sigmas = SIGMAS if stage == "tune" else (CHOSEN,)
    head(f"Round 3 · a speed measured during the turn, given to the map filter — {'tuning A+B' if stage == 'tune' else 'TEST D+E, one run'}")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(who) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    net = roadnet.RoadNetwork()
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
        h0 = max(0, i - int(HISTORY_S*FS))
        turn_hist = cal.scale*(S.gyr[h0:i] @ cal.axis) - cal.bias
        axes = fit_axes(S.acc[h0:i], turn_hist, S.v[h0:i], S.t[h0:i], stat[h0:i])
        usable = axes is not None and axes["r"] >= MIN_FIT_R
        inp = engine_input.build(S, cal, i, j)
        stationary = stat[i:j + 1]
        t_all = inp.t - inp.t[0]
        reads = readings(inp.acc, inp.turn_rate(), t_all, axes, stationary) if usable \
            else np.full(len(t_all), np.nan)
        has_read = bool(np.isfinite(reads).any())
        if stage == "tune" and not has_read:
            continue                                 # tuning looks only where the idea can act
        v_true = S.v[i:j + 1]
        err = np.array([reads[k] - v_true[k] for k in np.flatnonzero(np.isfinite(reads))]) if has_read \
            else np.array([np.nan])
        tx_all, ty_all, ts = track(S, i, j)
        step = max(1, int(round(SAMPLE_S*10)))
        rows = list(range(step, j - i + 1, step))
        r = np.asarray(rows, np.int64)
        t = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3 or len(rows) < 5:
            continue
        for name, obs, sigma in ([("no reading (today)", None, None)] +
                                 [(f"reading, sigma {s:g}" if stage == "tune" else "with turn readings", reads, s)
                                  for s in sigmas]):
            params = dict(PARAMS)
            if sigma is not None:
                params["sigma_speed_obs"] = sigma
            mt = smooth.ModeTracker(params.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                    FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
            res = particle.run(inp, net, stationary, rows, params=params, rng=np.random.default_rng(i),
                               estimator=mt, speed_obs=obs)
            e, n = smooth.smooth_track(t, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                       inp.speed0, FIX["catch_up"], FIX["extra"],
                                       close_s=FIX["close_s"], max_factor=FIX["max_factor"])
            m = measure(e, n, t, tx_all[r], ty_all[r], ts[r], true_s, keep, v_true=S.v[i + r])
            m.update(variant=name, band=b.band_1000, driver=b.driver, row_start=i, has_read=has_read,
                     n_reads=int(np.isfinite(reads).sum()), read_rms=float(np.nanmean(err**2)**0.5))
            recs.append(m)
    P = pd.DataFrame(recs)
    if P.empty:
        print("  no blackout had both usable axes and a reading")
        return
    P.to_parquet(R2/f"out/round3_turn_speed_pf_{stage}.parquet", index=False)
    head("blackouts where the axes fitted and at least one turn reading existed")
    n = P.row_start.nunique()
    print(f"  {n} blackouts, median {P.n_reads.median():.0f} readings each, reading error RMS {P.read_rms.median():.1f} m/s")
    print(f"\n  {'variant':<22}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}{'worst side':>12}")
    for name, g in P.groupby("variant", sort=False):
        print(f"  {name:<22}{100*(g.path < 10).mean():>10.0f}%{g.path.median():>9.1f}%{g.worst.median():>10.1f}%"
              f"{100*g.off.mean():>10.0f}%{g.worst_cross.median():>11.0f}m")
    base = P[P.variant == "no reading (today)"].set_index("row_start").path
    if stage != "tune":
        q = P[P.has_read]
        print(f"\n  of these, {q.row_start.nunique()} blackouts ({100*q.row_start.nunique()/n:.0f}%) actually had a reading;")
        for name, g in q.groupby("variant", sort=False):
            print(f"    {name:<22}{100*(g.path < 10).mean():>10.0f}%{g.path.median():>9.1f}%{g.worst.median():>10.1f}%"
                  f"{100*g.off.mean():>10.0f}%")
    print("\n  against today, per blackout:")
    for s in sigmas:
        q = P[P.variant == (f"reading, sigma {s:g}" if stage == "tune" else "with turn readings")].set_index("row_start").path
        j = pd.concat([base.rename("base"), q.rename("new")], axis=1).dropna()
        print(f"    sigma {s:g}: better on {100*(j.new < j.base).mean():3.0f}%, worse on {100*(j.new > j.base).mean():3.0f}%, "
              f"median change {(j.new - j.base).median():+.1f} points")


if __name__ == "__main__":
    main()
