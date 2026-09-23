"""Round 3 · one blackout taken apart — why A's off-road clip sits at 16.6% and what would fix it.

The clip: driver A, drive S4, session 1, blackout from row 44419 (the app's "England ride 4 · off road"). The estimate
runs ahead of the car, leaves the road at a junction for about twenty seconds, rejoins behind it, and averages 16.6%
of the distance travelled over the blackout.

The questions this answers, with numbers rather than opinion:
  1  what the car did, and what the engine assumed it was doing
  2  which single wrong input is responsible — speed, heading, or the map's choice of road — by replacing each with
     the truth in turn and re-measuring (dead reckoning, so the map cannot rescue or spoil the comparison)
  3  whether the map-matched filter recovers once given honest speed
  4  the moment it goes wrong: where the estimate was along the road, which junction it met, and what the gyro said
     about the turn it should have seen

Run from the repo root:  .venv/bin/python3 round2/round3_case_a.py
Output: round2/out/round3_case_a_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion, particle, roadnet, smooth
from core.geo import enu

CASE = dict(drive="S4", driver="A", session=1, row_start=44419)
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())
FLOOR_M = 100.0

def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")


def path_pct(est_e, est_n, true_e, true_n, true_s):
    m = true_s >= FLOOR_M
    pct = 100*np.hypot(est_e - true_e, est_n - true_n)/np.maximum(true_s, 1e-9)
    return float(pct[m].mean()), float(pct[m].max()), float(pct[-1])


def main():
    BL = pd.read_parquet(R2/"out/blackouts.parquet")
    row = BL[(BL.drive == CASE["drive"]) & (BL.session == CASE["session"]) &
             (BL.row_start == CASE["row_start"])].iloc[0]
    S = sessions.load(CASE["drive"], CASE["driver"], CASE["session"])
    C = calibration.Calibrator(S)
    stat = motion.stationary_rows(S, CASE["driver"])[0]
    i, j = int(row.row_start), int(row.end_1000)
    cal = calibration.engine_calibration(C, i, CHOICE)
    inp = engine_input.build(S, cal, i, j)
    n = j - i + 1
    k = slice(i, j + 1)
    true_e, true_n = enu(S.lat[k], S.lon[k], S.lat[i], S.lon[i])
    true_e, true_n = np.asarray(true_e, float), np.asarray(true_n, float)
    true_s = S.dist[k] - S.dist[i]
    v_true = S.v[k]
    psi_true = np.radians(S.heading[k])
    t = inp.t - inp.t[0]

    head("1 · what the car did, and what the engine assumed")
    print(f"  blackout {CASE['driver']}/{CASE['drive']} s{CASE['session']} row {i} — {true_s[-1]:.0f} m in {t[-1]:.0f} s, "
          f"{row.turns_1000} turns, band {row.band_1000}")
    print(f"  speed at the last fix (what the engine holds): {3.6*inp.speed0:.1f} km/h")
    print(f"  the car's own speed: start {3.6*v_true[0]:.0f}, min {3.6*v_true.min():.0f}, "
          f"mean {3.6*v_true.mean():.0f}, end {3.6*v_true[-1]:.0f} km/h")
    for a in range(0, int(t[-1]), 15):
        m = (t >= a) & (t < a + 15)
        if m.any():
            print(f"    {a:3d}-{a+15:3d} s   car {3.6*v_true[m].mean():5.1f} km/h   engine holds "
                  f"{3.6*inp.speed0:5.1f}   error {3.6*(inp.speed0 - v_true[m].mean()):+6.1f} km/h")
    over = np.trapezoid(inp.speed0 - v_true, t)
    print(f"  holding that speed puts the estimate {over:+.0f} m along the road by the end of the blackout")

    head("2 · replace one input with the truth at a time (dead reckoning, no map)")
    stationary = stat[k]
    variants = {
        "as it ran (engine inputs)": dict(),
        "true speed": dict(speed=v_true),
        "true heading": dict(heading=psi_true),
        "true stops only": dict(speed=np.where(v_true < 0.5, 0.0, inp.speed0)),
        "true speed and heading": dict(speed=v_true, heading=psi_true),
    }
    print(f"  {'variant':<28}{'path avg':>10}{'worst':>9}{'end':>9}")
    for name, over_kw in variants.items():
        e, nn, _ = deadreckoning.run(inp, stationary=stationary, **over_kw)
        avg, worst, end = path_pct(e, nn, true_e, true_n, true_s)
        print(f"  {name:<28}{avg:>9.1f}%{worst:>8.1f}%{end:>8.1f}%")

    head("3 · the map-matched filter, as it runs and with honest speed")
    net = roadnet.RoadNetwork()
    rows = list(range(1, n))
    for label, speed0 in (("as it ran (held 74.9 km/h)", inp.speed0),
                          ("started at the car's mean speed", float(v_true.mean())),
                          ("started at the car's slowest", float(v_true.min()))):
        inp2 = engine_input.build(S, cal, i, j)
        inp2 = type(inp2)(**{**inp2.__dict__, "speed0": speed0})
        mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                               FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
        res = particle.run(inp2, net, stationary, rows, params=PARAMS, rng=np.random.default_rng(i), estimator=mt)
        r = np.asarray(res["rows"], np.int64)
        e, nn = smooth.smooth_track(t[r], np.asarray(res["east"], float), np.asarray(res["north"], float),
                                    speed0, FIX["catch_up"], FIX["extra"], close_s=FIX["close_s"],
                                    max_factor=FIX["max_factor"])
        avg, worst, end = path_pct(e, nn, true_e[r], true_n[r], true_s[r])
        cross = np.array([np.min(np.hypot(true_e - e[q], true_n - nn[q])) for q in range(len(r))])
        print(f"  {label:<34} path {avg:5.1f}%   worst {worst:5.1f}%   end {end:5.1f}%   "
              f"furthest off the road {cross.max():5.0f} m")

    head("4 · the moment it goes wrong")
    mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                           FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
    res = particle.run(inp, net, stationary, rows, params=PARAMS, rng=np.random.default_rng(i), estimator=mt)
    r = np.asarray(res["rows"], np.int64)
    e = np.asarray(res["east"], float); nn = np.asarray(res["north"], float)
    cross = np.array([np.min(np.hypot(true_e - e[q], true_n - nn[q])) for q in range(len(r))])
    # how far along the road the estimate thinks it is, against the truth at the same moment
    along = np.array([float(np.argmin(np.hypot(true_e - e[q], true_n - nn[q]))) for q in range(len(r))])
    ahead = np.array([true_s[int(along[q])] - true_s[r[q]] for q in range(len(r))])
    leave = np.flatnonzero(cross > 30)
    dt = np.clip(np.diff(inp.t), 0.0, None)
    turn = inp.turn_rate()
    if len(leave):
        q = int(leave[0])
        tq = t[r[q]]
        print(f"  the estimate leaves the road at {tq:.0f} s, {true_s[r[q]]:.0f} m into the blackout")
        print(f"  at that moment it believes it is {ahead[q]:+.0f} m along the road from where the car actually is")
        print(f"  the car was doing {3.6*v_true[r[q]]:.0f} km/h; the engine was holding {3.6*inp.speed0:.0f} km/h")
        w = (t >= tq - 5) & (t <= tq + 5)
        print(f"  gyro turning over those ten seconds: {np.degrees(np.trapezoid(turn[w], t[w])):+.0f}°, "
              f"the car actually turned {np.degrees(np.arctan2(np.sin(psi_true[w][-1] - psi_true[w][0]), np.cos(psi_true[w][-1] - psi_true[w][0]))):+.0f}°")
        print(f"  it is off the road for {(cross > 30).sum()/10:.0f} s and gets {cross.max():.0f} m away at worst")
        back = np.flatnonzero((cross <= 30) & (np.arange(len(cross)) > q))
        if len(back):
            print(f"  it rejoins the road at {t[r[int(back[0])]]:.0f} s, by then {ahead[int(back[0])]:+.0f} m "
                  f"from where the car is")
    print(f"\n  where the estimate sits along the road, through the blackout:")
    for a in range(0, int(t[-1]), 15):
        m = (t[r] >= a) & (t[r] < a + 15)
        if m.any():
            print(f"    {a:3d}-{a+15:3d} s   {ahead[m].mean():+7.0f} m along   {cross[m].mean():6.0f} m sideways   "
                  f"car {3.6*v_true[r][m].mean():5.1f} km/h")


if __name__ == "__main__":
    main()
