"""Round 3 · the excursions — when does the estimate leave the road the vehicle is actually on?

A drift of tens of metres along the right road is a dead-reckoning error and a reviewer will accept it. The cursor
sitting in a different street, taking the wrong branch at a junction, or stopping dead while the vehicle drives on is a
different thing entirely, and it is what the worst-moment column of round3_path_metric.py is made of.

This measures those events, on the frozen round-2 filter (nothing retuned), recording the estimate every second:

  off route      how far the estimate is sideways from the path the vehicle actually drove (cross-track), and for how
                 long it stays beyond OFF_M — the "it is in another street" event
  wrong road     the estimate matched to a different OSM way than the true position, both being on a road
  stuck          the estimate barely advancing along the route while the vehicle is moving well
  along only     cross-track small but along-track error large — the acceptable kind: right road, wrong place on it

For each blackout it reports the worst excursion, how long the estimate was away, whether it came back, and what the
same blackout did without the map, so the map's own contribution to these events is visible.

Outputs: round2/out/round3_excursions.parquet, round2/out/round3_excursions_run.txt.
Run from the repo root:  .venv/bin/python3 round2/round3_excursions.py [--limit N]
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
BANDS = ["slow", "mixed", "ps_60", "fast"]
BAND_LABEL = {"slow": "under 40", "mixed": "40-50", "ps_60": "50-70 (PS)", "fast": "70+"}
OFF_M = 30.0                 # beyond this sideways from the driven path, the cursor is in another street
STUCK_MS = 1.5               # advancing slower than this while the vehicle does more than 5 m/s
SAMPLE_S = 1.0
FLOOR_M = 100.0
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*112}\n{t}\n{'='*112}")


def track(S, i, j):
    """The driven path in metres from the start fix, and distance along it."""
    e, n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
    s = np.concatenate(([0.0], np.cumsum(np.hypot(np.diff(e), np.diff(n)))))
    return np.asarray(e, float), np.asarray(n, float), s


def decompose(px, py, tx, ty, ts):
    """Cross-track distance to the driven path, and how far along that path the nearest point lies."""
    cross = np.empty(len(px))
    along = np.empty(len(px))
    for k in range(len(px)):
        d2 = (tx - px[k])**2 + (ty - py[k])**2
        m = int(d2.argmin())
        cross[k] = np.sqrt(d2[m])
        along[k] = ts[m]
    return cross, along


def episodes(flag, t):
    """(count, longest seconds, total seconds) of the stretches where flag is True."""
    if not flag.any():
        return 0, 0.0, 0.0
    d = np.diff(flag.astype(np.int8))
    starts = np.flatnonzero(d == 1) + 1
    ends = np.flatnonzero(d == -1) + 1
    if flag[0]:
        starts = np.r_[0, starts]
    if flag[-1]:
        ends = np.r_[ends, len(flag)]
    lens = np.array([t[min(e, len(t) - 1)] - t[s] for s, e in zip(starts, ends)])
    return len(starts), float(lens.max()), float(lens.sum())


def main():
    limit = arg("--limit", 0)
    head("Round 3 · when does the estimate leave the road the vehicle is on?")
    print(f"  frozen settings {PARAMS} · calibration {CHOICE}")
    print(f"  off route = more than {OFF_M:.0f} m sideways from the driven path · stuck = advancing under "
          f"{STUCK_MS} m/s while the vehicle does 5+ m/s · measured from {FLOOR_M:.0f} m of travel")

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
        de, dn, _ = deadreckoning.run(inp, stationary=stat[i:j + 1])
        tx, ty, ts = track(S, i, j)
        r = np.asarray(res["rows"], np.int64)
        est_e = np.asarray(res["east"], float)
        est_n = np.asarray(res["north"], float)
        t = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3:
            continue

        cross, along = decompose(est_e, est_n, tx, ty, ts)
        base_cross, _ = decompose(de[r], dn[r], tx, ty, ts)
        off = cross > OFF_M
        # how fast the cursor itself moves, and how far it teleports in one step: a wrong-road snap shows up here
        dt = np.diff(t, prepend=t[0] - SAMPLE_S)
        moved = np.hypot(np.diff(est_e, prepend=0.0), np.diff(est_n, prepend=0.0))
        speed_est = moved/np.maximum(dt, 1e-6)
        v_true = S.v[i + r]
        stuck = (speed_est < STUCK_MS) & (v_true > 5.0)
        jump = moved > 20.0                                           # more than 20 m in one second
        n_off, long_off, total_off = episodes(off & keep, t)
        n_stuck, long_stuck, _ = episodes(stuck & keep, t)

        recs.append(dict(
            driver=b.driver, drive=b.drive, session=int(b.session), row_start=i, band=b.band_1000,
            turns=b.turns_1000, since_turn_m=b.since_turn_m_1000,
            worst_cross=float(cross[keep].max()), median_cross=float(np.median(cross[keep])),
            worst_along=float(np.abs(along[keep] - true_s[keep]).max()),
            end_cross=float(cross[-1]), end_along=float(abs(along[-1] - true_s[-1])),
            off_episodes=int(n_off), off_longest_s=float(long_off), off_total_s=float(total_off),
            came_back=bool(n_off > 0 and cross[-1] <= OFF_M),
            stuck_episodes=int(n_stuck), stuck_longest_s=float(long_stuck),
            jumps=int((jump & keep).sum()), worst_jump_m=float(moved[keep].max()),
            base_worst_cross=float(base_cross[keep].max()), base_off=bool((base_cross[keep] > OFF_M).any()),
            worst_pct=float(np.max(100*np.hypot(est_e[keep] - tx[r][keep], est_n[keep] - ty[r][keep])/true_s[keep])),
        ))
    P = pd.DataFrame(recs)
    P.to_parquet(R2/"out/round3_excursions.parquet", index=False)
    log(f"{len(P):,} blackouts -> round2/out/round3_excursions.parquet")

    def table(q, by, order):
        print(f"  {'':<12}{'n':>6}{'off route':>11}{'episodes':>10}{'longest':>9}{'worst':>8}{'came back':>11}"
              f"{'stuck':>8}{'no-map off':>12}")
        print(f"  {'':<12}{'':>6}{'share':>11}{'per b/out':>10}{'s':>9}{'m':>8}{'of those':>11}{'share':>8}{'share':>12}")
        for k in list(order) + ["all"]:
            g = q if k == "all" else q[q[by] == k]
            if g.empty:
                continue
            offs = g[g.off_episodes > 0]
            print(f"  {BAND_LABEL.get(k, k):<12}{len(g):>6}{100*(g.off_episodes > 0).mean():>10.0f}%"
                  f"{g.off_episodes.mean():>10.1f}{offs.off_longest_s.median() if len(offs) else 0:>9.0f}"
                  f"{g.worst_cross.median():>8.0f}{100*offs.came_back.mean() if len(offs) else 0:>10.0f}%"
                  f"{100*(g.stuck_episodes > 0).mean():>7.0f}%{100*g.base_off.mean():>11.0f}%")

    for lab, who in SPLITS:
        head(f"{lab} — excursions by driving condition")
        table(P[P.driver.isin(who)], "band", BANDS)

    head("what the excursions cost, and what kind they are")
    q = P[P.driver.isin(["D", "E"])]
    off = q[q.off_episodes > 0]
    print(f"  test blackouts with at least one off-route moment: {len(off):,} of {len(q):,} ({100*len(off)/len(q):.0f}%)")
    print(f"  of those: worst sideways {off.worst_cross.median():.0f} m (p90 {off.worst_cross.quantile(0.9):.0f} m), "
          f"away for {off.off_total_s.median():.0f} s (p90 {off.off_total_s.quantile(0.9):.0f} s), "
          f"came back {100*off.came_back.mean():.0f}%")
    print(f"  blackouts where the cursor froze while the vehicle drove (>3 s): "
          f"{100*(q.stuck_longest_s >= 3).mean():.0f}%  (any freeze at all: {100*(q.stuck_episodes > 0).mean():.0f}%)")
    print(f"  blackouts where the cursor jumped more than 20 m in one second: {100*(q.jumps > 0).mean():.0f}%  "
          f"(worst jump, median of those: {q[q.jumps > 0].worst_jump_m.median() if (q.jumps > 0).any() else 0:.0f} m)")
    print(f"  worst error that is purely along the road (cross under {OFF_M:.0f} m): "
          f"{q[q.worst_cross <= OFF_M].worst_along.median():.0f} m median")
    print(f"\n  the map's own contribution: off route with the map {100*(q.off_episodes > 0).mean():.0f}%, "
          f"without the map {100*q.base_off.mean():.0f}%")
    print("  (the map-free estimate drifts away smoothly; the map-aided one can jump to a wrong road and back)")
    print("\n  where they happen:")
    for name, m in (("a turn happened in the blackout", q.turns > 0), ("no turn at all", q.turns == 0),
                    ("last turn over 500 m back", q.since_turn_m > 500), ("last turn within 200 m", q.since_turn_m <= 200)):
        g = q[m]
        if len(g):
            print(f"    {name:<32} n={len(g):5d}   off route {100*(g.off_episodes > 0).mean():3.0f}%   "
                  f"worst sideways {g.worst_cross.median():4.0f} m")


if __name__ == "__main__":
    main()
