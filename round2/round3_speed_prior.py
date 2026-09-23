"""Round 3 · a speed that decays toward what the road allows, instead of being held for ever.

The engine holds the speed from the last GNSS fix until the blackout ends. On a car that slows down, that is the whole
error (entry 38). No sensor can measure the new speed — the accelerometer cannot (entries 39 and the bridge test) — but
the map knows something the engine ignores: what road this is, and how fast traffic actually goes on it.

So instead of holding v0 for ever:

    v(t) = v_road + (v0 - v_road) x exp(-t / tau)

the speed relaxes from what the car was doing toward what that road usually carries, over tau seconds. v_road comes
from the tagged speed limit where there is one, otherwise from what these drivers actually do on that class of road
(learned on the tuning drivers' own GNSS, never on the test drivers).

Measured as dead reckoning without the map, so the change is visible on its own.
Run from the repo root:  .venv/bin/python3 round2/round3_speed_prior.py [--limit 200]
Output: round2/out/round3_speed_prior_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion, roadnet
from core.geo import enu
from round3_accel_speed import CHOICE, TUNE, FLOOR_M

T0 = time.time()
TAUS = (10.0, 20.0, 40.0, 80.0)

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def road_speeds(net, BL, drivers, cache):
    """What these drivers actually do on each road class, from their own GNSS — the fallback where nothing is tagged."""
    got = {}
    for b in BL[BL.driver.isin(drivers)].head(40).itertuples(index=False):
        S = sessions.load(b.drive, b.driver, int(b.session))
        k = slice(max(0, int(b.row_start) - 3000), int(b.row_start))
        x, y = roadnet.xy(S.lat[k], S.lon[k])
        m = net.match(x, y, np.radians(S.heading[k]))
        seg, v = m["seg"], S.v[k]
        ok = (seg >= 0) & np.isfinite(v) & (v > 1.0)
        for cls, speed in zip(net.seg_class[seg[ok]], v[ok]):
            got.setdefault(int(cls), []).append(float(speed))
    return {c: float(np.median(vs)) for c, vs in got.items() if len(vs) >= 50}


def main():
    limit = arg("--limit", 200)
    head("Round 3 · letting the held speed relax toward what the road carries")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    net = roadnet.RoadNetwork()
    typical = road_speeds(net, BL, TUNE, {})
    print("  typical speed by road class, from the tuning drivers' own driving (m/s): "
          + ", ".join(f"{c}:{v:.1f}" for c, v in sorted(typical.items())))
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]

    rows, cache = [], {}
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
        x, y = roadnet.xy(np.array([S.lat[i]]), np.array([S.lon[i]]))
        m = net.match(x, y, np.radians(np.array([S.heading[i]])))
        seg = int(m["seg"][0])
        if seg < 0:
            continue
        tagged = float(net.seg_maxspeed[seg])/3.6
        v_road = tagged if np.isfinite(tagged) and tagged > 1 else typical.get(int(net.seg_class[seg]), np.nan)
        if not np.isfinite(v_road):
            continue
        inp = engine_input.build(S, cal, i, j)
        t = inp.t - inp.t[0]
        stationary = stat[i:j + 1]
        true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        keep = true_s >= FLOOR_M
        def pct(speed):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(true_e, float), n - np.asarray(true_n, float))/np.maximum(true_s, 1e-9)
            return float(p[keep].mean())
        rec = dict(band=b.band_1000, driver=b.driver, held=pct(None), true=pct(S.v[i:j + 1]),
                   v0=float(inp.speed0), v_road=float(v_road), tagged=bool(np.isfinite(tagged) and tagged > 1))
        for tau in TAUS:
            rec[f"tau{tau:g}"] = pct(v_road + (inp.speed0 - v_road)*np.exp(-t/tau))
        rows.append(rec)
    D = pd.DataFrame(rows)
    D.to_parquet(R2/"out/round3_speed_prior.parquet", index=False)

    head("path average, median over blackouts (dead reckoning, no map)")
    print(f"  {len(D)} blackouts, {100*D.tagged.mean():.0f}% on a road with a tagged limit")
    print(f"  {'held for ever (today)':<28}{D.held.median():>7.1f}%")
    for tau in TAUS:
        col = f"tau{tau:g}"
        print(f"  {'relaxing over ' + str(int(tau)) + ' s':<28}{D[col].median():>7.1f}%"
              f"   better on {100*(D[col] < D.held).mean():3.0f}% of blackouts")
    print(f"  {'true speed (the floor)':<28}{D['true'].median():>7.1f}%")
    head("by driving condition (held / best relaxation / true)")
    best = min(TAUS, key=lambda x: D[f"tau{x:g}"].median())
    print(f"  best relaxation time: {best:.0f} s")
    for band in ("slow", "mixed", "ps_60", "fast"):
        g = D[D.band == band]
        if len(g):
            print(f"    {band:<8} n={len(g):4d}   {g.held.median():6.1f}%  {g[f'tau{best:g}'].median():6.1f}%  "
                  f"{g['true'].median():6.1f}%   under 10%: {100*(g.held < 10).mean():3.0f}% -> "
                  f"{100*(g[f'tau{best:g}'] < 10).mean():3.0f}%")
    print(f"\n  overall under 10%: {100*(D.held < 10).mean():.0f}% -> {100*(D[f'tau{best:g}'] < 10).mean():.0f}%")


if __name__ == "__main__":
    main()
