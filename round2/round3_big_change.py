"""Round 3 · catching only the big speed changes — a dead-zone on integrated acceleration.

Integrating the accelerometer loses to holding the speed on average (entry 40), so it was dropped. But the blackouts
that miss the benchmark are not average ones: they are the blackouts where the car changed speed by ten metres a second
or more. Integration noise is about 3 m/s over five seconds. A real ten-metre-a-second deceleration should stand out
against that, even when small changes cannot be seen at all.

So the change is used only when it is big enough to be believed:

    delta_used = sign(delta) x max(0, |delta| - threshold)

Below the threshold the engine keeps holding the last GNSS speed, exactly as today; above it, the engine follows what
the accelerometer says minus the threshold, so the noise cannot push it around. The forward direction is fitted on the
GNSS history against how the speed was actually changing — that needs no cornering, so it can be fitted on phones that
cannot feel a corner.

Run from the repo root:  .venv/bin/python3 round2/round3_big_change.py [--limit 200] [--stage tune|test]
Output: round2/out/round3_big_change_run.txt, round3_big_change_{stage}.parquet
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
HISTORY_S = 900.0
MIN_FWD_R = 0.5              # the forward direction must track the GNSS change of speed this well to be used
THRESHOLDS = (2.0, 3.0, 5.0)
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def fit_forward(acc, v, t, stationary):
    """The vehicle's forward direction in the phone's frame, from how the GNSS speed changed. No cornering needed."""
    ok = np.isfinite(v) & ~stationary & (v > 2.0)
    if ok.sum() < 300:
        return None
    up = acc.mean(axis=0)
    up = up/np.linalg.norm(up)
    horiz = acc - np.outer(acc @ up, up)
    seed = np.array([1.0, 0.0, 0.0]) if abs(up[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(up, seed); e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    q1, q2 = horiz @ e1, horiz @ e2
    vi = pd.Series(v).interpolate(limit_direction="both").to_numpy()
    a_true = np.gradient(vi, t)
    # smooth both sides to a second: the fit is about real acceleration, not vibration
    k = np.ones(10)/10
    a_s = np.convolve(a_true, k, mode="same")
    q1s, q2s = np.convolve(q1, k, mode="same"), np.convolve(q2, k, mode="same")
    ok &= np.isfinite(a_s) & np.isfinite(q1s) & np.isfinite(q2s)
    if ok.sum() < 300:
        return None
    X = np.c_[a_s[ok], np.ones(ok.sum())]
    c1 = np.linalg.lstsq(X, q1s[ok], rcond=None)[0]
    c2 = np.linalg.lstsq(X, q2s[ok], rcond=None)[0]
    fwd = np.array([c1[0], c2[0]])
    scale = float(np.hypot(*fwd))
    if not (0.2 < scale < 3.0):
        return None
    d = fwd/scale
    meas = q1s[ok]*d[0] + q2s[ok]*d[1] - (c1[1]*d[0] + c2[1]*d[1])
    r = float(np.corrcoef(scale*a_s[ok], meas)[0, 1])
    return dict(up=up, e1=e1, e2=e2, dir=d, scale=scale, offset=float(c1[1]*d[0] + c2[1]*d[1]), r=r)


def delta_v(acc, t, axes):
    """The change of speed since the blackout began, as the accelerometer sees it."""
    horiz = acc - np.outer(acc @ axes["up"], axes["up"])
    q = (horiz @ axes["e1"])*axes["dir"][0] + (horiz @ axes["e2"])*axes["dir"][1]
    a_fwd = (q - axes["offset"])/axes["scale"]
    return np.concatenate(([0.0], np.cumsum(0.5*(a_fwd[1:] + a_fwd[:-1])*np.diff(t))))


def main():
    stage = arg("--stage", "tune")
    limit = arg("--limit", 200)
    who = TUNE if stage == "tune" else ["D", "E"]
    head(f"Round 3 · following only the big speed changes — {'tuning A+B' if stage == 'tune' else 'TEST D+E, one run'}")
    print(f"  the forward direction must fit the GNSS change of speed at r >= {MIN_FWD_R}; "
          f"dead-zone thresholds tried: {THRESHOLDS} m/s")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(who) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    net = roadnet.RoadNetwork()
    recs, fits, cache = [], [], {}
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
        axes = fit_forward(S.acc[h0:i], S.v[h0:i], S.t[h0:i], stat[h0:i])
        fits.append(dict(driver=b.driver, fitted=axes is not None, r=axes["r"] if axes else np.nan,
                         scale=axes["scale"] if axes else np.nan))
        if axes is None or axes["r"] < MIN_FWD_R:
            continue
        inp = engine_input.build(S, cal, i, j)
        stationary = stat[i:j + 1]
        t = inp.t - inp.t[0]
        dv = delta_v(inp.acc, inp.t, axes)
        v_true = S.v[i:j + 1]
        true_change = float(v_true[-1] - v_true[0])
        true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        keep_dr = true_s >= FLOOR_M
        def dr_pct(speed):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(true_e, float), n - np.asarray(true_n, float))/np.maximum(true_s, 1e-9)
            return float(p[keep_dr].mean())
        rec = dict(driver=b.driver, band=b.band_1000, fit_r=axes["r"], true_change=true_change,
                   big=abs(true_change) >= 5.0, dr_held=dr_pct(None), dr_true=dr_pct(v_true),
                   dv_err=float(dv[-1] - true_change))
        speeds = {}
        for th in THRESHOLDS:
            used = np.sign(dv)*np.maximum(0.0, np.abs(dv) - th)
            v = np.clip(inp.speed0 + used, 0.5, 45.0)
            speeds[th] = np.where(stationary, 0.0, v)
            rec[f"dr_th{th:g}"] = dr_pct(speeds[th])
        # and inside the filter, for the middle threshold
        tx, ty, ts = track(S, i, j)
        step = max(1, int(round(SAMPLE_S*10)))
        rows = list(range(step, j - i + 1, step))
        if len(rows) >= 5:
            r = np.asarray(rows, np.int64)
            tt = inp.t[r] - inp.t[0]
            ts_true = S.dist[i + r] - S.dist[i]
            keep = ts_true >= FLOOR_M
            if keep.sum() >= 3:
                for label, target in (("pf_held", None), ("pf_th3", speeds[3.0])):
                    mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                            FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
                    res = particle.run(inp, net, stationary, rows, params=PARAMS, rng=np.random.default_rng(i),
                                       estimator=mt, speed_target=target)
                    e, n = smooth.smooth_track(tt, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                               inp.speed0, FIX["catch_up"], FIX["extra"],
                                               close_s=FIX["close_s"], max_factor=FIX["max_factor"])
                    m = measure(e, n, tt, tx[r], ty[r], ts[r], ts_true, keep, v_true=S.v[i + r])
                    rec[label], rec[label + "_off"], rec[label + "_worst"] = m["path"], m["off"], m["worst"]
        recs.append(rec)
    Fi = pd.DataFrame(fits)
    P = pd.DataFrame(recs)
    if P.empty:
        print("  nothing usable")
        return
    P.to_parquet(R2/f"out/round3_big_change_{stage}.parquet", index=False)

    head("1 · can the forward direction be fitted, and on whose phone?")
    for drv, g in Fi.groupby("driver"):
        print(f"  driver {drv}: fitted on {100*g.fitted.mean():3.0f}% of blackouts, median r {g.r.median():.2f}, "
              f"median scale {g.scale.median():.2f}")

    head("2 · does the integrated change find the big decelerations?")
    print(f"  {len(P)} blackouts with a usable forward fit; {100*P.big.mean():.0f}% of them changed speed by 5+ m/s")
    for lo, hi, name in ((0, 3, "little change"), (3, 7, "3-7 m/s"), (7, 99, "7 m/s or more")):
        g = P[(P.true_change.abs() >= lo) & (P.true_change.abs() < hi)]
        if len(g) >= 5:
            print(f"    {name:<16} n={len(g):4d}   the change it reported was off by {g.dv_err.abs().median():5.2f} m/s "
                  f"(the change itself was {g.true_change.abs().median():5.2f})")

    head("3 · dead reckoning, no map (path average, median)")
    print(f"  {'held (today)':<22}{P.dr_held.median():>7.1f}%   under 10% on {100*(P.dr_held < 10).mean():3.0f}%")
    for th in THRESHOLDS:
        c = f"dr_th{th:g}"
        print(f"  {'dead-zone ' + str(th) + ' m/s':<22}{P[c].median():>7.1f}%   under 10% on {100*(P[c] < 10).mean():3.0f}%"
              f"   better on {100*(P[c] < P.dr_held).mean():3.0f}%")
    print(f"  {'true speed':<22}{P.dr_true.median():>7.1f}%   under 10% on {100*(P.dr_true < 10).mean():3.0f}%")
    print("\n  on the blackouts that changed speed a lot (5+ m/s):")
    g = P[P.big]
    if len(g):
        print(f"    held {g.dr_held.median():5.1f}%   dead-zone 3 {g.dr_th3.median():5.1f}%   true {g.dr_true.median():5.1f}%")

    if "pf_held" in P:
        Q = P.dropna(subset=["pf_held", "pf_th3"])
        head("4 · with the map, through the round-3 reporting layer")
        print(f"  {'variant':<22}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}")
        for label, name in (("pf_held", "held (today)"), ("pf_th3", "dead-zone 3 m/s")):
            print(f"  {name:<22}{100*(Q[label] < 10).mean():>10.0f}%{Q[label].median():>9.1f}%"
                  f"{Q[label + '_worst'].median():>10.1f}%{100*Q[label + '_off'].mean():>10.0f}%")
        print(f"\n  better on {100*(Q.pf_th3 < Q.pf_held).mean():.0f}% of blackouts, "
              f"worse on {100*(Q.pf_th3 > Q.pf_held).mean():.0f}%")
        b = Q[Q.big]
        if len(b) >= 5:
            print(f"  on the {len(b)} that changed speed by 5+ m/s: under 10% "
                  f"{100*(b.pf_held < 10).mean():.0f}% -> {100*(b.pf_th3 < 10).mean():.0f}%, "
                  f"path {b.pf_held.median():.1f}% -> {b.pf_th3.median():.1f}%")


if __name__ == "__main__":
    main()
