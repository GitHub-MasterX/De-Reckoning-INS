"""Round 3 · the speed that regresses to the mean — holding the last GNSS speed is biased, not merely uncertain.

Measured on the tuning drivers: sixty seconds after the last fix, a car that was doing more than 26 m/s has lost about
5 m/s on average, and one doing less than 8 m/s has gained about 4.5. Holding the last speed is therefore wrong in a
predictable direction, and that matters more than noise: along-track error is the *integral* of the speed error, so
noise partly cancels while a bias accumulates metre by metre.

An earlier attempt (entry 40) aimed the speed at the road's tagged limit and failed, because a limit is not what
traffic does. This aims it at what these drivers actually did, learned as

    v_expected(t) = a(t) x v0 + b(t)

fitted on the tuning drivers alone, separately for fast roads and ordinary ones so it can transfer to a motorway-heavy
driver. It is applied two ways: to dead reckoning, and inside the filter, where every guess is carried by the same
expected change so the spread of guesses is untouched and only their centre moves.

Run from the repo root:  .venv/bin/python3 round2/round3_shrink_speed.py [--limit 200] [--stage tune|test]
Output: round2/out/round3_shrink_speed_run.txt, round3_shrink_{fit,tune,test}.parquet
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion, particle, roadnet, smooth
from core.geo import enu
from round3_accel_speed import CHOICE, TUNE, FLOOR_M
from round3_excursions import track
from round3_report_fix import measure, SAMPLE_S

T0 = time.time()
FS = 10.0
HORIZONS = np.array([0, 5, 10, 15, 20, 30, 45, 60, 80, 100, 120], float)
FAST_LIMIT_MS = 22.0          # a road tagged at 80 km/h or more counts as fast
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def road_is_fast(net, S, i):
    x, y = roadnet.xy(np.array([S.lat[i]]), np.array([S.lon[i]]))
    m = net.match(x, y, np.radians(np.array([S.heading[i]])))
    seg = int(m["seg"][0])
    if seg < 0:
        return False
    lim = float(net.seg_maxspeed[seg])/3.6
    return bool(np.isfinite(lim) and lim >= FAST_LIMIT_MS)


def fit_curves(net, n_fit=500):
    """a(t), b(t) per horizon, on the tuning drivers only: what speed follows a fix of v0, on fast and ordinary roads."""
    BL = pd.read_parquet(R2/"out/blackouts.parquet")
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()]
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(n_fit, len(BL))).astype(int)]
    rows, key, S = [], None, None
    for b in BL.itertuples(index=False):
        if (b.drive, int(b.session)) != key:
            key = (b.drive, int(b.session)); S = sessions.load(b.drive, b.driver, int(b.session))
        i = int(b.row_start)
        v0 = float(S.v[i])
        if not np.isfinite(v0) or v0 < 1.0:
            continue
        fast = road_is_fast(net, S, i)
        for h in HORIZONS:
            k = i + int(h*FS)
            if k < len(S.v) and np.isfinite(S.v[k]):
                rows.append(dict(v0=v0, h=float(h), v=float(S.v[k]), fast=fast))
    F = pd.DataFrame(rows)
    F.to_parquet(R2/"out/round3_shrink_fit.parquet", index=False)
    curves = {}
    for fast in (False, True):
        a_s, b_s = [], []
        for h in HORIZONS:
            g = F[(F.h == h) & (F.fast == fast)]
            if len(g) < 40 or h == 0:
                a_s.append(1.0); b_s.append(0.0); continue
            a, b = np.polyfit(g.v0, g.v, 1)
            a_s.append(float(a)); b_s.append(float(b))
        curves[fast] = (np.array(a_s), np.array(b_s))
    return F, curves


def expected(curves, fast, v0, t):
    a, b = curves[bool(fast)]
    at = np.interp(t, HORIZONS, a)
    bt = np.interp(t, HORIZONS, b)
    return np.clip(at*v0 + bt, 0.5, 45.0)


def main():
    stage = arg("--stage", "tune")
    limit = arg("--limit", 200)
    who = TUNE if stage == "tune" else ["D", "E"]
    head(f"Round 3 · a speed that regresses to the mean — {'tuning A+B' if stage == 'tune' else 'TEST D+E, one run'}")
    net = roadnet.RoadNetwork()
    F, curves = fit_curves(net)
    print(f"  fitted on {len(F):,} samples from the tuning drivers")
    print(f"  {'horizon':<9}{'ordinary road: v_expected':>34}{'fast road':>26}")
    for h in (10, 30, 60, 90):
        a0, b0 = curves[False]; a1, b1 = curves[True]
        e0 = f"{np.interp(h, HORIZONS, a0):.2f} x v0 {np.interp(h, HORIZONS, b0):+.2f}"
        e1 = f"{np.interp(h, HORIZONS, a1):.2f} x v0 {np.interp(h, HORIZONS, b1):+.2f}"
        print(f"  {h:>4.0f} s   {e0:>32}{e1:>26}")

    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(who) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    log(f"{len(BL)} blackouts to score")

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
        fast = road_is_fast(net, S, i)
        v_exp = expected(curves, fast, inp.speed0, t_all)
        true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        keep_dr = true_s >= FLOOR_M
        def dr_pct(speed):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(true_e, float), n - np.asarray(true_n, float))/np.maximum(true_s, 1e-9)
            return float(p[keep_dr].mean())
        rec = dict(driver=b.driver, band=b.band_1000, fast=fast,
                   dr_held=dr_pct(None), dr_shrink=dr_pct(np.where(stationary, 0.0, v_exp)),
                   dr_true=dr_pct(S.v[i:j + 1]))
        # and inside the filter
        tx, ty, ts = track(S, i, j)
        step = max(1, int(round(SAMPLE_S*10)))
        rows = list(range(step, j - i + 1, step))
        if len(rows) >= 5:
            r = np.asarray(rows, np.int64)
            t = inp.t[r] - inp.t[0]
            ts_true = S.dist[i + r] - S.dist[i]
            keep = ts_true >= FLOOR_M
            if keep.sum() >= 3:
                # partial shrinkage: v0 moved a fraction of the way toward what usually happens. Full shrinkage is
                # right on average but wrong for the common case of a car simply keeping its speed.
                targets = [("pf_held", None), ("pf_shrink", v_exp),
                           ("pf_half", inp.speed0 + 0.5*(v_exp - inp.speed0)),
                           ("pf_third", inp.speed0 + 0.33*(v_exp - inp.speed0)),
                           ("pf_slowonly", (inp.speed0 + 0.5*(v_exp - inp.speed0)) if not fast else None)]
                for label, target in targets:
                    mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                            FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
                    res = particle.run(inp, net, stationary, rows, params=PARAMS, rng=np.random.default_rng(i),
                                       estimator=mt, speed_target=target)
                    e, n = smooth.smooth_track(t, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                               inp.speed0, FIX["catch_up"], FIX["extra"],
                                               close_s=FIX["close_s"], max_factor=FIX["max_factor"])
                    m = measure(e, n, t, tx[r], ty[r], ts[r], ts_true, keep, v_true=S.v[i + r])
                    rec[label] = m["path"]
                    rec[label + "_off"] = m["off"]
                    rec[label + "_worst"] = m["worst"]
        recs.append(rec)
    P = pd.DataFrame(recs).dropna(subset=["pf_held", "pf_shrink", "pf_half", "pf_third", "pf_slowonly"])
    P.to_parquet(R2/f"out/round3_shrink_{stage}.parquet", index=False)

    head("dead reckoning, no map (path average, median)")
    print(f"  {'held (today)':<24}{P.dr_held.median():>7.1f}%    under 10% on {100*(P.dr_held < 10).mean():3.0f}%")
    print(f"  {'regressed to the mean':<24}{P.dr_shrink.median():>7.1f}%    under 10% on {100*(P.dr_shrink < 10).mean():3.0f}%")
    print(f"  {'true speed':<24}{P.dr_true.median():>7.1f}%    under 10% on {100*(P.dr_true < 10).mean():3.0f}%")
    head("with the map, through the round-3 reporting layer")
    print(f"  {'variant':<24}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}")
    for label, name in (("pf_held", "held (today)"), ("pf_shrink", "full regression"),
                        ("pf_half", "half way there"), ("pf_third", "a third of the way"),
                        ("pf_slowonly", "half way, ordinary roads only")):
        print(f"  {name:<24}{100*(P[label] < 10).mean():>10.0f}%{P[label].median():>9.1f}%"
              f"{P[label + '_worst'].median():>10.1f}%{100*P[label + '_off'].mean():>10.0f}%")
    for label in ("pf_shrink", "pf_half", "pf_third", "pf_slowonly"):
        print(f"  {label:<14} better on {100*(P[label] < P.pf_held).mean():3.0f}% of blackouts, "
              f"worse on {100*(P[label] > P.pf_held).mean():3.0f}%")
    head("by driving condition (held / regressed, with the map)")
    for band in ("slow", "mixed", "ps_60", "fast"):
        g = P[P.band == band]
        if len(g):
            print(f"  {band:<8} n={len(g):4d}   path {g.pf_held.median():5.1f}% -> half {g.pf_half.median():5.1f}% "
                  f"-> full {g.pf_shrink.median():5.1f}%   under 10% {100*(g.pf_held < 10).mean():3.0f}% -> "
                  f"{100*(g.pf_half < 10).mean():3.0f}% -> {100*(g.pf_shrink < 10).mean():3.0f}%   "
                  f"off route {100*g.pf_held_off.mean():3.0f}% -> {100*g.pf_half_off.mean():3.0f}%")


if __name__ == "__main__":
    main()
