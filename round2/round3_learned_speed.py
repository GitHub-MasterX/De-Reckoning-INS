"""Round 3 · the learned speed estimator, tested in the engine.

round3_imu_map_nn.py showed that a model given the IMU, the map and the speed at the last fix predicts the speed 30 s
later at 3.15 m/s RMS, against 6.09 for holding that speed — and 2.47 against 6.25 when the car was slow at the fix,
which is exactly where the engine fails. That was a measurement on samples across whole sessions. This is the test
that counts: train the model, run it inside the blackouts, and score the same way everything else is scored.

  training     a sample every second of every tuning session, at lags of 5 to 90 s after a notional fix, labelled with
               the true speed. Features: the shaking (2 s window), the map under the car (class, tagged limit, how
               built-up), the speed at the notional fix, and how long ago that was
  honesty      leave-one-session-out: the model that predicts a blackout has never seen that session
  use          the predicted speed becomes the speed the filter's guesses follow (speed_target)
  scored       path average, share under 10%, worst moment, off route — the round-3 reporting layer throughout

Run from the repo root:  .venv/bin/python3 round2/round3_learned_speed.py [--limit 200] [--stage tune|test]
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion, particle, roadnet, smooth
from core.geo import enu
from round3_vibration_speed import features, HOP
from round3_accel_speed import TUNE, CHOICE, FLOOR_M
from round3_excursions import track
from round3_report_fix import measure, SAMPLE_S

T0 = time.time()
LAGS = (5, 10, 20, 30, 45, 60, 90)
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def map_feats(net, S, idx):
    x, y = roadnet.xy(S.lat[idx], S.lon[idx])
    m = net.match(x, y, np.radians(S.heading[idx]))
    seg = m["seg"]
    lim = np.where(seg >= 0, net.seg_maxspeed[np.maximum(seg, 0)]/3.6, np.nan)
    cls = np.where(seg >= 0, net.seg_class[np.maximum(seg, 0)], -1).astype(float)
    near = net.tree.query_ball_point(np.c_[x, y], r=40.0)
    dens = np.array([len(np.unique(net.sample_seg[np.asarray(q, np.int64)])) if len(q) else 0 for q in near], float)
    return np.c_[lim, cls, dens, m["d_allowed"]]


def training_table(net, drivers):
    """One row per second per lag: the shaking now, the map now, the speed a lag ago, and the true speed now."""
    sel = sessions.selected()
    sel = sel[sel.driver.isin(drivers)]
    frames = []
    for r in sel.itertuples(index=False):
        S = sessions.load(r.drive, r.driver, int(r.session))
        if S is None:
            continue
        F, c = features(S.acc, S.gyr)
        if len(F) == 0:
            continue
        k = np.arange(0, len(F), max(1, 10//HOP))
        F, c = F[k], c[k]
        ok = np.isfinite(S.v[c]) & np.isfinite(F).all(axis=1)
        F, c = F[ok], c[ok]
        if len(c) < 100:
            continue
        M = map_feats(net, S, c)
        for lag in LAGS:
            back = c - lag*10
            good = (back >= 0)
            good &= np.isfinite(S.v[np.maximum(back, 0)])
            if good.sum() < 50:
                continue
            frames.append(pd.DataFrame(
                np.c_[F[good], M[good], S.v[back[good]], np.full(good.sum(), lag, float), S.v[c[good]]],
                columns=[f"imu{i}" for i in range(F.shape[1])] +
                        ["limit", "road_class", "road_density", "dist_to_road", "v_fix", "lag", "target"]
            ).assign(group=f"{r.drive}_{r.session}"))
        log(f"  train {r.drive}/{r.session} ({r.driver})")
    return pd.concat(frames, ignore_index=True)


def main():
    stage = arg("--stage", "tune")
    limit = arg("--limit", 200)
    who = TUNE if stage == "tune" else ["D", "E"]
    head(f"Round 3 · the learned speed inside the engine — {'tuning A+B' if stage == 'tune' else 'TEST D+E, one run'}")
    net = roadnet.RoadNetwork()
    D = training_table(net, TUNE)                      # always trained on the tuning drivers only
    feats = [c for c in D.columns if c not in ("target", "group")]
    log(f"{len(D):,} training rows from {D.group.nunique()} sessions")
    models = {}
    for grp in D.group.unique():                        # leave-one-session-out
        tr = D[D.group != grp]
        models[grp] = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                                    l2_regularization=1.0, random_state=0).fit(
            tr[feats].to_numpy(float), tr.target.to_numpy(float))
    everything = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                               l2_regularization=1.0, random_state=0).fit(
        D[feats].to_numpy(float), D.target.to_numpy(float))
    log(f"{len(models)} leave-one-out models fitted")

    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(who) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    recs, cache = [], {}
    for nb, b in enumerate(BL.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
            log(f"  score {b.drive}/{b.session} ({b.driver}) — {nb}/{len(BL)}")
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None:
            continue
        inp = engine_input.build(S, cal, i, j)
        stationary = stat[i:j + 1]
        t = inp.t - inp.t[0]
        # the model's speed for every second of the blackout
        F, c = features(S.acc[i:j + 1], S.gyr[i:j + 1])
        if len(F) == 0:
            continue
        k = np.arange(0, len(F), max(1, 10//HOP))
        F, c = F[k], c[k]
        M = map_feats(net, S, i + c)
        X = np.c_[F, M, np.full(len(c), inp.speed0), t[c]]
        mdl = models.get(f"{b.drive}_{b.session}", everything)
        v_hat = np.clip(mdl.predict(X), 0.0, 45.0)
        v_pred = np.interp(np.arange(j - i + 1), c, v_hat)
        v_pred = np.where(stationary, 0.0, v_pred)
        v_true = S.v[i:j + 1]
        te, tn = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        kd = true_s >= FLOOR_M
        def dr(speed):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(te, float), n - np.asarray(tn, float))/np.maximum(true_s, 1e-9)
            return float(p[kd].mean())
        moving = ~stationary
        rec = dict(driver=b.driver, band=b.band_1000, row_start=i, v0=float(inp.speed0),
                   rms_model=float(np.sqrt(np.mean((v_pred[moving] - v_true[moving])**2))),
                   rms_held=float(np.sqrt(np.mean((inp.speed0 - v_true[moving])**2))),
                   dr_held=dr(None), dr_model=dr(v_pred), dr_true=dr(v_true))
        tx, ty, ts = track(S, i, j)
        rows = list(range(10, j - i + 1, 10))
        if len(rows) >= 5:
            r = np.asarray(rows, np.int64)
            tt = inp.t[r] - inp.t[0]
            ts_true = S.dist[i + r] - S.dist[i]
            keep = ts_true >= FLOOR_M
            if keep.sum() >= 3:
                # the model shrinks fast driving toward the mean, and on a motorway holding is nearly right, so the
                # learned speed is used only where it was measured to help: a fix below about 72 km/h
                gated = v_pred if inp.speed0 < 20.0 else None
                blend = np.where(stationary, 0.0, 0.5*v_pred + 0.5*inp.speed0)
                pairs = ((("pf_held", None), ("pf_model", v_pred), ("pf_gated", gated), ("pf_blend", blend))
                         if stage == "tune" else (("pf_held", None), ("pf_model", v_pred)))
                for label, target in pairs:
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
    need = ["pf_held", "pf_model"] + (["pf_gated", "pf_blend"] if stage == "tune" else [])
    P = pd.DataFrame(recs).dropna(subset=need)
    P.to_parquet(R2/f"out/round3_learned_speed_{stage}.parquet", index=False)

    head("1 · how good is the learned speed inside the blackouts?")
    print(f"  {len(P)} blackouts · model RMS {P.rms_model.median():.2f} m/s · holding {P.rms_held.median():.2f} m/s · "
          f"better on {100*(P.rms_model < P.rms_held).mean():.0f}%")
    head("2 · dead reckoning, no map (path average, median)")
    print(f"  held {P.dr_held.median():5.1f}%   learned {P.dr_model.median():5.1f}%   true {P.dr_true.median():5.1f}%")
    head("3 · with the map, the finished reporting layer")
    print(f"  {'variant':<18}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}")
    names = ((("pf_held", "held (today)"), ("pf_model", "learned speed"),
              ("pf_gated", "learned, under 72 km/h"), ("pf_blend", "half learned, half held"))
             if stage == "tune" else (("pf_held", "held (today)"), ("pf_model", "learned speed")))
    for label, name in names:
        print(f"  {name:<18}{100*(P[label] < 10).mean():>10.0f}%{P[label].median():>9.1f}%"
              f"{P[label + '_worst'].median():>10.1f}%{100*P[label + '_off'].mean():>10.0f}%")
    for label in (("pf_model", "pf_gated", "pf_blend") if stage == "tune" else ("pf_model",)):
        print(f"  {label:<10} better on {100*(P[label] < P.pf_held).mean():3.0f}% of blackouts, "
              f"worse on {100*(P[label] > P.pf_held).mean():3.0f}%")
    head("4 · by driving condition")
    for band in ("slow", "mixed", "ps_60", "fast"):
        g = P[P.band == band]
        if len(g):
            print(f"  {band:<8} n={len(g):4d}   under 10% {100*(g.pf_held < 10).mean():3.0f}% -> "
                  f"{100*(g.pf_model < 10).mean():3.0f}%   "
                  f"path {g.pf_held.median():5.1f}% -> {g.pf_model.median():5.1f}%   "
                  f"off route {100*g.pf_held_off.mean():3.0f}% -> {100*g.pf_model_off.mean():3.0f}%")


if __name__ == "__main__":
    main()
