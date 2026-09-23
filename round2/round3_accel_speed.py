"""Round 3 · speed from the accelerometer, at last — does the phone's turn trick work on IO-VNBD's 10 Hz data?

Everything so far estimates position from the gyro and the map, and *assumes* speed: the last GNSS speed, held. Entry
38 showed that assumption is the whole error on the clip that fails. Round 1 did try the accelerometer, as a trained
speed regressor, and it lost to coasting — at 10 Hz, engine and road vibration alias onto the same 0-2 Hz band the
vehicle's own acceleration lives in, so integrating it is hopeless.

This is the other way of using it, the one built for the phone (core is SpeedEstimator.kt): during a steady turn the
vehicle is pushed sideways, and

    sideways acceleration  =  speed x turn rate        so       speed  =  sideways acceleration / turn rate

which needs no integration, so a bias does not accumulate, and it needs no absolute calibration of the accelerometer
beyond knowing which way is sideways. Vibration is beaten by averaging over the whole turn, not by filtering.

Three steps, all on the tuning drivers only:
  1  the vehicle's axes in the phone's frame, fitted on the GNSS history before each blackout (never during it)
  2  the readings themselves during the blackout, against the car's true speed
  3  what they would be worth: dead reckoning with the read speed, against the held speed, against the truth

Outputs: round2/out/round3_accel_speed.parquet, round3_accel_speed_run.txt.
Run from the repo root:  .venv/bin/python3 round2/round3_accel_speed.py [--limit 120]
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion
from core.geo import enu

T0 = time.time()
TUNE = ["A", "B"]
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
FS = 10.0
HISTORY_S = 600.0            # how much GNSS history the axes are fitted on
WINDOW_S = 2.0               # a reading is averaged over this much turning
MIN_TURN = 0.10              # rad/s: below this the division is noise
MAX_SPREAD = 0.30            # rad/s: the turn rate may not change more than this inside the window
MIN_SPEED = 2.0              # m/s
FLOOR_M = 100.0
CONFIRM_S = 20.0             # a reading vouches for the estimate this long; after that, back to the held speed
MIN_FIT_R = 0.6              # the axes are only trusted when the sideways swing really tracks speed x turn rate
                             # (the phone engine's rule; without it, badly fitted blackouts poison the average)

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")


def fit_axes(acc, gyr_turn, v, t, stationary):
    """The vehicle's right and forward in the phone's frame, from GNSS history.

    Gravity is the average accelerometer reading (a car is level on average); what is left is horizontal. In that plane
    the vehicle's right is the direction the reading swings when it corners — speed x turn rate — and forward is the
    direction it swings when the GNSS speed changes. Returns (right, forward, scale_right) or None.
    """
    ok = np.isfinite(v) & np.isfinite(gyr_turn) & ~stationary & (v > MIN_SPEED)
    if ok.sum() < 200:
        return None
    up = acc.mean(axis=0)
    up = up/np.linalg.norm(up)
    horiz = acc - np.outer(acc @ up, up)                        # the horizontal part of every reading
    # two orthogonal directions spanning the horizontal plane
    seed = np.array([1.0, 0.0, 0.0]) if abs(up[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(up, seed); e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    q1, q2 = horiz @ e1, horiz @ e2
    a_lat = v*gyr_turn                                          # what cornering should produce
    a_fwd = np.gradient(v, t)                                   # and what speeding up or braking should produce
    X = np.c_[a_fwd[ok], a_lat[ok], np.ones(ok.sum())]
    try:
        c1, *_ = np.linalg.lstsq(X, q1[ok], rcond=None)
        c2, *_ = np.linalg.lstsq(X, q2[ok], rcond=None)
    except np.linalg.LinAlgError:
        return None
    right = np.array([c1[1], c2[1]])                            # how the reading moves with sideways acceleration
    scale = float(np.hypot(*right))
    if not (0.3 < scale < 3.0):
        return None
    right_dir = right/scale
    pred = scale*a_lat[ok]
    meas = q1[ok]*right_dir[0] + q2[ok]*right_dir[1] - (c1[2]*right_dir[0] + c2[2]*right_dir[1])
    r = float(np.corrcoef(pred, meas)[0, 1])
    offset = float(c1[2]*right_dir[0] + c2[2]*right_dir[1])
    return dict(e1=e1, e2=e2, up=up, right=right_dir, scale=scale, offset=offset, r=r)


def readings(acc, turn, t, axes, stationary):
    """Speed readings during a blackout: one per steady turn, from sideways acceleration divided by turn rate."""
    horiz = acc - np.outer(acc @ axes["up"], axes["up"])
    q = (horiz @ axes["e1"])*axes["right"][0] + (horiz @ axes["e2"])*axes["right"][1]
    a_right = (q - axes["offset"])/axes["scale"]
    w = int(WINDOW_S*FS)
    out = np.full(len(t), np.nan)
    for k in range(0, len(t) - w, w//2):
        sl = slice(k, k + w)
        if stationary[sl].any():
            continue
        r = turn[sl]
        if not np.isfinite(r).all() or abs(r.mean()) < MIN_TURN or r.max() - r.min() > MAX_SPREAD or r.min()*r.max() <= 0:
            continue
        v = a_right[sl].mean()/r.mean()
        if 2.0 < v < 45.0:
            out[k + w - 1] = v
    return out


def held_then_read(speed0, reads, t, gain=1.0, confirm_s=CONFIRM_S):
    """The engine's speed: the held GNSS speed, moved toward each reading by `gain`, for `confirm_s` after it.

    gain = 1 replaces the held speed with the reading outright; gain = 0.5 splits the difference, which costs little
    when a reading is right and costs half as much when it is wrong.
    """
    v = np.full(len(t), speed0)
    belief, last_t = np.nan, -1e9
    for k in range(len(t)):
        if np.isfinite(reads[k]):
            base = belief if np.isfinite(belief) and t[k] - last_t <= confirm_s else speed0
            belief = base + gain*(reads[k] - base)
            last_t = t[k]
        if np.isfinite(belief) and t[k] - last_t <= confirm_s:
            v[k] = belief
    return v


def main():
    global MIN_FIT_R
    MIN_FIT_R = arg("--min-r", MIN_FIT_R)
    limit = arg("--limit", 120)
    head("Round 3 · speed from the accelerometer during turns (tuning drivers A+B)")
    print(f"  a reading needs {WINDOW_S:g} s of steady turning above {MIN_TURN} rad/s; it is trusted for {CONFIRM_S:g} s")
    print(f"  the vehicle's axes are used only when the history fit reaches r >= {MIN_FIT_R:.2f}")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    log(f"{len(BL)} blackouts")

    recs, rows_out, cache = [], [], {}
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
        if axes is not None and axes["r"] < MIN_FIT_R:
            axes = None                      # fitted, but not well enough to divide by
        if axes is None:
            recs.append(dict(driver=b.driver, band=b.band_1000, fitted=False))
            continue
        inp = engine_input.build(S, cal, i, j)
        t = inp.t - inp.t[0]
        turn = inp.turn_rate()
        stationary = stat[i:j + 1]
        reads = readings(inp.acc, turn, t, axes, stationary)
        v_true = S.v[i:j + 1]
        got = np.isfinite(reads)
        for k in np.flatnonzero(got):
            rows_out.append(dict(driver=b.driver, band=b.band_1000, read=reads[k], truth=v_true[k],
                                 held=inp.speed0, fit_r=axes["r"], scale=axes["scale"]))

        true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        m = true_s >= FLOOR_M
        def pct(speed=None):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(true_e, float), n - np.asarray(true_n, float))/np.maximum(true_s, 1e-9)
            return float(p[m].mean())
        rec = dict(driver=b.driver, band=b.band_1000, fitted=True, fit_r=axes["r"], scale=axes["scale"],
                   n_reads=int(got.sum()), held_pct=pct(None), true_pct=pct(v_true))
        for label, gain, conf in (("read_pct", 1.0, CONFIRM_S), ("half_pct", 0.5, CONFIRM_S),
                                  ("third_pct", 0.33, CONFIRM_S), ("half_long_pct", 0.5, 40.0)):
            rec[label] = pct(held_then_read(inp.speed0, reads, t, gain, conf))
        rec["covered"] = float((np.abs(held_then_read(inp.speed0, reads, t) - inp.speed0) > 1e-9).mean())
        recs.append(rec)
    P = pd.DataFrame(recs)
    P.to_parquet(R2/"out/round3_accel_speed.parquet", index=False)
    Rd = pd.DataFrame(rows_out)

    head("1 · could the vehicle's axes be found at all?")
    print(f"  blackouts with axes good enough to use: {100*P.fitted.mean():.0f}% of {len(P)}")
    F = P[P.fitted]
    if len(F):
        print(f"  how well the sideways swing matches speed x turn rate (correlation r): "
              f"median {F.fit_r.median():.2f}, p10 {F.fit_r.quantile(0.1):.2f}, p90 {F.fit_r.quantile(0.9):.2f}")
        print(f"  scale of that swing (1.0 would mean the accelerometer reads it exactly): median {F.scale.median():.2f}")

    head("2 · the readings against the car's true speed")
    if Rd.empty:
        print("  no readings at all")
    else:
        e = Rd.read - Rd.truth
        print(f"  {len(Rd):,} readings over {len(F)} blackouts (median {F.n_reads.median():.0f} per blackout, "
              f"{100*F.covered.median():.0f}% of the blackout covered by a fresh reading)")
        print(f"  error: median {e.median():+.2f} m/s, RMS {np.sqrt((e**2).mean()):.2f}, "
              f"within 2 m/s {100*(e.abs() < 2).mean():.0f}%")
        eh = Rd.held - Rd.truth
        print(f"  the held GNSS speed on the same moments: RMS {np.sqrt((eh**2).mean()):.2f} m/s, "
              f"within 2 m/s {100*(eh.abs() < 2).mean():.0f}%")
        print("\n  by fit quality:")
        for lo, hi in ((0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
            q = Rd[(Rd.fit_r >= lo) & (Rd.fit_r < hi)]
            if len(q) > 20:
                ee = q.read - q.truth
                print(f"    r {lo:.1f}-{hi:.1f}  n={len(q):5d}  RMS {np.sqrt((ee**2).mean()):5.2f} m/s  "
                      f"held {np.sqrt(((q.held - q.truth)**2).mean()):5.2f} m/s")

    head("3 · what it would be worth (dead reckoning, no map, path average)")
    if len(F):
        for label, name in (("held_pct", "held speed (today)"), ("read_pct", "reading replaces it"),
                            ("half_pct", "reading, half weight"), ("third_pct", "reading, third weight"),
                            ("half_long_pct", "half weight, trusted 40 s"), ("true_pct", "true speed (the floor)")):
            better = (F[label] < F.held_pct).mean() if label not in ("held_pct",) else np.nan
            extra = "" if label == "held_pct" else f"   better on {100*better:3.0f}% of blackouts"
            print(f"  {name:<30}{F[label].median():>7.1f}%{extra}")
        print("\n  by driving condition (held / half weight / true):")
        for band in ("slow", "mixed", "ps_60", "fast"):
            g = F[F.band == band]
            if len(g):
                print(f"    {band:<8} n={len(g):4d}   {g.held_pct.median():6.1f}%  {g.half_pct.median():6.1f}%  "
                      f"{g.true_pct.median():6.1f}%")


def theory(limit=80):
    """What a speed sensor would have to be worth: noise added to the truth, and readings at different coverage."""
    head("4 · theory — how good and how frequent would a speed sensor have to be?")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    rng = np.random.default_rng(7)
    rows, cache = [], {}
    for b in BL.itertuples(index=False):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None:
            continue
        inp = engine_input.build(S, cal, i, j)
        stationary = stat[i:j + 1]
        v_true = S.v[i:j + 1]
        t = inp.t - inp.t[0]
        true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        m = true_s >= FLOOR_M
        def pct(speed):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(true_e, float), n - np.asarray(true_n, float))/np.maximum(true_s, 1e-9)
            return float(p[m].mean())
        rec = dict(band=b.band_1000, held=pct(None))
        for sigma in (1.0, 2.0, 4.0, 6.0):
            # a reading every few seconds, each wrong by `sigma` RMS, held between readings
            for every_s in (5.0, 20.0, 60.0):
                v = np.full(len(t), inp.speed0)
                belief, last = np.nan, -1e9
                for k in range(len(t)):
                    if t[k] - last >= every_s:
                        belief = max(0.0, v_true[k] + rng.normal(0.0, sigma))
                        last = t[k]
                    if np.isfinite(belief):
                        v[k] = belief
                rec[f"s{sigma:g}_e{every_s:g}"] = pct(v)
        rows.append(rec)
    T = pd.DataFrame(rows)
    print(f"  {len(T)} blackouts · path average, median · held speed today: {T.held.median():.1f}%")
    print(f"\n  {'reading every':<16}" + "".join(f"{f'sigma {s:g} m/s':>14}" for s in (1.0, 2.0, 4.0, 6.0)))
    for every_s in (5.0, 20.0, 60.0):
        cells = "".join(f"{T[f's{s:g}_e{every_s:g}'].median():>13.1f}%" for s in (1.0, 2.0, 4.0, 6.0))
        print(f"  {every_s:>6.0f} s        {cells}")
    print("\n  share of blackouts under 10% with a reading every 20 s:")
    for s in (1.0, 2.0, 4.0, 6.0):
        print(f"    sigma {s:g} m/s   {100*(T[f's{s:g}_e20'] < 10).mean():3.0f}%   (held speed today: "
              f"{100*(T.held < 10).mean():.0f}%)")


if __name__ == "__main__":
    main()
    theory()
