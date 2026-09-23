"""Round 3 · fixing what the cursor does — mode hysteresis and a speed-limited cursor, measured.

Two changes, both in how the filter's particles are turned into the one position we report. Neither changes what the
filter believes, neither draws a random number, and with both switched off every round-2 number is reproduced exactly.

  hysteresis   core/smooth.ModeTracker — keep reporting the group of guesses reported last time; hand over only when a
               rival has been MARGIN times better for HOLD updates running, or when the reported group dies
  cursor       core/smooth.smooth_track — the reported point chases the filter at a speed a vehicle could manage,
               max(CATCH_UP x believed speed, speed + EXTRA), so a correction arrives as motion, not as a jump

Reported for every variant, in the order that matters:
  path        average 2D error over the blackout, % of distance travelled (from 100 m of travel onwards)
  end         the same at the 1 km mark — round 2's old headline
  off route   share of blackouts that go more than 30 m sideways of the driven path, and the worst of those
  jump        share of blackouts where the cursor moves more than 20 m in one second, and the worst such step

Protocol: settings are chosen on the tuning drivers A and B; the test drivers D and E are run once with what was
chosen. Run from the repo root:
    .venv/bin/python3 round2/round3_report_fix.py --stage tune    [--limit N]
    .venv/bin/python3 round2/round3_report_fix.py --stage test
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
from core.geo import enu
from round3_excursions import track, decompose, episodes, OFF_M

T0 = time.time()
FLOOR_M = 100.0
SAMPLE_S = 1.0
JUMP_M = 20.0
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
TUNE, TEST = ["A", "B"], ["D", "E"]

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*108}\n{t}\n{'='*108}")


def measure(est_e, est_n, t, tx, ty, ts, true_s, keep, v_true=None):
    """The numbers for one track: path %, end %, off-route behaviour, and whether the cursor outran the vehicle.

    A step counts as a jump when the cursor covers more ground in one second than the vehicle plausibly could —
    half as much again as the vehicle actually moved, plus JUMP_M of slack — so ordinary motorway motion is not
    counted and a hop between roads is.
    """
    pct = 100*np.hypot(est_e - tx, est_n - ty)/np.maximum(true_s, 1e-9)
    cross, along = decompose(est_e, est_n, tx, ty, ts)
    behind = true_s - along                                   # positive: the cursor sits back down the road
    moved = np.hypot(np.diff(est_e, prepend=est_e[0]), np.diff(est_n, prepend=est_n[0]))
    dt = np.diff(t, prepend=t[0] - SAMPLE_S)
    allow = (1.5*np.asarray(v_true, float)*dt + JUMP_M) if v_true is not None else np.full(len(t), JUMP_M)
    n_off, long_off, total_off = episodes((cross > OFF_M) & keep, t)
    # frozen: the cursor barely moving while the vehicle covers ground
    vmoved = np.diff(true_s, prepend=true_s[0])
    frozen = float(((moved < 0.2*np.maximum(vmoved, 1e-6)) & (vmoved > 5.0) & keep).sum())*SAMPLE_S
    return dict(frozen_s=frozen, lag_m=float(np.mean(behind[keep])), lag_worst_m=float(np.max(np.abs(behind[keep]))),
                path=float(np.mean(pct[keep])), end=float(pct[-1]), worst=float(np.max(pct[keep])),
                worst_cross=float(np.max(cross[keep])), off=bool(n_off > 0), off_longest_s=float(long_off),
                jumps=int(((moved > allow) & keep).sum()), worst_jump=float(np.max(moved[keep])),
                worst_excess=float(np.max((moved - allow)[keep])))


def run_variants(drivers, variants, limit=0):
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(drivers) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    if limit:
        BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    net = roadnet.RoadNetwork()
    log(f"{len(BL):,} blackouts · {len(variants)} variants")
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
        tx_all, ty_all, ts = track(S, i, j)
        r = np.asarray(rows, np.int64)
        t = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3:
            continue
        tx, ty = tx_all[r], ty_all[r]
        raw = {}
        for name, v in variants.items():
            src = (f"hyst{v.get('margin', 1.6)}_{v.get('hold', 3)}_{v.get('release_m', 80.0)}_"
                   f"{v.get('min_share', 0.05)}") if v["hysteresis"] else "plain"
            if src not in raw:
                cluster_m = PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"])
                mt = (smooth.ModeTracker(cluster_m, v.get("margin", 1.6), v.get("hold", 3),
                                         v.get("release_m", 80.0), v.get("min_share", 0.05))
                      if v["hysteresis"] else None)
                res = particle.run(inp, net, stat[i:j + 1], rows, params=PARAMS,
                                   rng=np.random.default_rng(i), estimator=mt)
                raw[src] = (np.asarray(res["east"], float), np.asarray(res["north"], float))
            e, n = raw[src]
            if v["smooth"]:
                e, n = smooth.smooth_track(t, e, n, inp.speed0, v.get("catch_up", 1.5), v.get("extra", 3.0),
                                           close_s=v.get("close_s", smooth.CLOSE_S),
                                           max_factor=v.get("max_factor", smooth.MAX_FACTOR))
            m = measure(e, n, t, tx, ty, ts[r], true_s, keep, v_true=S.v[i + r])
            m.update(variant=name, driver=b.driver, drive=b.drive, session=int(b.session), row_start=i,
                     band=b.band_1000)
            recs.append(m)
    return pd.DataFrame(recs)


def report(P, title):
    head(title)
    print(f"  {'variant':<22}{'n':>6}{'PATH med':>10}{'path<10%':>10}{'end med':>9}{'end<10%':>9}"
          f"{'worst med':>11}{'off route':>11}{'worst side':>11}{'jumps':>8}{'worst jump':>11}{'frozen':>9}{'lag':>9}")
    for name, g in P.groupby("variant", sort=False):
        print(f"  {name:<22}{len(g):>6}{g.path.median():>9.1f}%{100*(g.path < 10).mean():>9.0f}%"
              f"{g['end'].median():>8.1f}%{100*(g['end'] < 10).mean():>8.0f}%{g.worst.median():>10.1f}%"
              f"{100*g.off.mean():>10.0f}%{g.worst_cross.median():>10.0f}m{100*(g.jumps > 0).mean():>7.0f}%"
              f"{g.worst_jump.median():>10.0f}m{g.frozen_s.median():>9.1f}s{g.lag_m.median():>9.0f}m")


def main():
    stage = arg("--stage", "tune")
    limit = arg("--limit", 0)
    if stage == "tune":
        variants = {
            "round 2 (as published)": dict(hysteresis=False, smooth=False),
            "cursor only": dict(hysteresis=False, smooth=True),
            "hysteresis only": dict(hysteresis=True, smooth=False),
            "both": dict(hysteresis=True, smooth=True),
            "both, slower cursor": dict(hysteresis=True, smooth=True, catch_up=1.2, extra=2.0),
            "both, mild hold": dict(hysteresis=True, smooth=True, margin=1.3, hold=2),
            "both, firm hold": dict(hysteresis=True, smooth=True, margin=2.5, hold=5),
            "mild hold, quick cursor": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, catch_up=2.0, extra=5.0),
            "mild hold, quicker still": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, catch_up=3.0, extra=8.0),
            "round 3b: catch up in 8 s": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, close_s=8.0),
            "round 3b: catch up in 5 s": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, close_s=5.0),
            "round 3b: 5 s, free mode": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, close_s=5.0,
                                             release_m=50.0),
            "round 3b: 5 s, fast cap": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, close_s=5.0,
                                            max_factor=4.0),
            "cursor, quick close": dict(hysteresis=False, smooth=True, close_s=4.0, max_factor=4.0),
            "light hold": dict(hysteresis=True, smooth=True, margin=1.15, hold=2, release_m=40.0, close_s=6.0),
            "light hold, quick close": dict(hysteresis=True, smooth=True, margin=1.15, hold=1, release_m=40.0,
                                            close_s=4.0, max_factor=4.0),
            "light hold, tight release": dict(hysteresis=True, smooth=True, margin=1.15, hold=2, release_m=25.0,
                                              close_s=4.0, max_factor=4.0),
            "firm hold + along catch-up": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, release_m=80.0,
                                               close_s=6.0),
            "firm hold + quick along": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, release_m=80.0,
                                            close_s=3.0, max_factor=4.0),
            "firm hold, no catch-up": dict(hysteresis=True, smooth=True, margin=1.3, hold=2, release_m=80.0,
                                           close_s=0.0),
        }
        P = run_variants(TUNE, variants, limit)
        P.to_parquet(R2/"out/round3_report_fix_tune.parquet", index=False)
        report(P, "TUNING drivers A+B — choosing the settings (nothing here is a result)")
        print("\n  by driving condition, for the variants that matter:")
        for name in ("round 2 (as published)", "both", "both, firmer hold"):
            q = P[P.variant == name]
            if q.empty:
                continue
            print(f"\n  {name}")
            for band in ("slow", "mixed", "ps_60", "fast"):
                g = q[q.band == band]
                if len(g):
                    print(f"    {band:<8} n={len(g):4d}  path {g.path.median():5.1f}%  off route {100*g.off.mean():3.0f}%"
                          f"  worst sideways {g.worst_cross.median():4.0f} m  jumps {100*(g.jumps > 0).mean():3.0f}%")
    else:
        chosen = json.loads((R2/"out/round3_report_choice.json").read_text())
        variants = {"round 2 (as published)": dict(hysteresis=False, smooth=False), "round 3 (chosen)": chosen}
        P = run_variants(TEST, variants, limit)
        P.to_parquet(R2/"out/round3_report_fix_test.parquet", index=False)
        report(P, f"TEST drivers D+E — one run with the settings chosen on A+B: {chosen}")
        print("\n  by driving condition:")
        for name in variants:
            q = P[P.variant == name]
            print(f"\n  {name}")
            for band in ("slow", "mixed", "ps_60", "fast"):
                g = q[q.band == band]
                if len(g):
                    print(f"    {band:<8} n={len(g):4d}  path {g.path.median():5.1f}%  end {g['end'].median():5.1f}%  "
                          f"off route {100*g.off.mean():3.0f}%  worst sideways {g.worst_cross.median():4.0f} m  "
                          f"jumps {100*(g.jumps > 0).mean():3.0f}%  worst jump {g.worst_jump.median():3.0f} m")


if __name__ == "__main__":
    main()
