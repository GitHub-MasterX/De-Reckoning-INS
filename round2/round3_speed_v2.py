"""Round 3 · two cures for the speed model's one-sided error.

The learned speed beats holding overall, but it fails the same way twice: it under-calls a vehicle that accelerates
hard (driver B's rides), because it predicts what a context *usually* carries, and its errors are one-sided, so they
integrate into lag instead of cancelling.

  trend       the model sees only how much the vehicle is shaking *now*. Give it the change as well — the same
              features five seconds ago — so that a vehicle winding up looks different from one cruising. This needs
              no mount and no calibration: rising road noise is rising speed.
  expansion   a squared-error model predicts the conditional mean, which is shrunk toward the middle. Expanding the
              prediction away from its own mean by a factor undoes the shrinkage: more variance, less bias, and for an
              error that gets integrated along a road, bias is what hurts.

Tuning drivers only, leave-one-session-out. Run:  .venv/bin/python3 round2/round3_speed_v2.py [--limit 250]
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, smooth
from round3_vibration_speed import features as vib_features, HOP
from round3_learned_speed import map_feats
from round3_accel_speed import CHOICE, TUNE, FLOOR_M
from round3_excursions import track
from round3_report_fix import measure, SAMPLE_S

T0 = time.time()
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())
LAGS = (5, 10, 20, 30, 45, 60, 90)
BACK = 10                      # ten windows of half a second: how the shaking looked five seconds ago
def arg(f, d): return type(d)(sys.argv[sys.argv.index(f) + 1]) if f in sys.argv else d
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def windows(S, i=None, j=None):
    """Feature windows with their trend: the shaking now, and how it has changed over the last five seconds."""
    acc = S.acc if i is None else S.acc[i:j + 1]
    gyr = S.gyr if i is None else S.gyr[i:j + 1]
    F, c = vib_features(acc, gyr)
    if len(F) == 0:
        return np.zeros((0, 0)), np.zeros(0, int)
    k = np.arange(0, len(F), max(1, 10//HOP))
    F, c = F[k], c[k]
    prev = np.vstack([F[:1].repeat(min(BACK, len(F)), axis=0), F[:-BACK]])[:len(F)]
    trend = np.log1p(np.maximum(F, 0)) - np.log1p(np.maximum(prev, 0))
    return np.c_[F, trend], (c if i is None else c + i)


def build_table(net, drivers):
    sel = sessions.selected()
    sel = sel[sel.driver.isin(drivers)]
    frames = []
    for r in sel.itertuples(index=False):
        S = sessions.load(r.drive, r.driver, int(r.session))
        if S is None:
            continue
        F, c = windows(S)
        if len(F) == 0:
            continue
        ok = np.isfinite(S.v[c]) & np.isfinite(F).all(axis=1)
        F, c = F[ok], c[ok]
        M = map_feats(net, S, c)
        for lag in LAGS:
            back = c - lag*10
            good = back >= 0
            if good.sum() < 50:
                continue
            frames.append(pd.DataFrame(
                np.c_[F[good], M[good], S.v[back[good]], np.full(good.sum(), lag, float), S.v[c[good]]],
                columns=[f"f{i}" for i in range(F.shape[1])] +
                        ["limit", "road_class", "road_density", "dist_to_road", "v_fix", "lag", "target"]
            ).assign(group=f"{r.drive}_{r.session}"))
        log(f"  {r.drive}/{r.session} ({r.driver})")
    return pd.concat(frames, ignore_index=True)


def main():
    limit = arg("--limit", 250)
    head("Round 3 · trend features and expansion, on the tuning drivers")
    net = roadnet.RoadNetwork()
    D = build_table(net, TUNE)
    feats = [c for c in D.columns if c not in ("target", "group")]
    log(f"{len(D):,} training rows, {len(feats)} features (with the trend)")
    models = {g: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                               l2_regularization=1.0, random_state=0).fit(
        D[D.group != g][feats].to_numpy(float), D[D.group != g].target.to_numpy(float)) for g in D.group.unique()}
    log(f"{len(models)} leave-one-out models")

    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    recs, cache = [], {}
    for nb, b in enumerate(BL.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
            log(f"  scoring {b.drive}/{b.session} — {nb}/{len(BL)}")
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None:
            continue
        inp = engine_input.build(S, cal, i, j)
        st = stat[i:j + 1]
        t = inp.t - inp.t[0]
        F, c = windows(S, i, j)
        if len(F) < 5:
            continue
        X = np.c_[F, map_feats(net, S, c), np.full(len(c), inp.speed0), t[c - i]]
        raw = np.clip(models[f"{b.drive}_{b.session}"].predict(X), 0.0, 45.0)
        tx, ty, ts = track(S, i, j)
        rows = list(range(10, j - i + 1, 10))
        if len(rows) < 5:
            continue
        r = np.asarray(rows, np.int64)
        tt = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3:
            continue
        v_true = S.v[i:j + 1]
        mv = v_true > 0.5
        rec = dict(driver=b.driver, band=b.band_1000, row_start=i, v0=float(inp.speed0),
                   rms_held=float(np.sqrt(np.mean((inp.speed0 - v_true[mv])**2))))
        for name, gain in (("plain", 1.0), ("expand 1.25", 1.25), ("expand 1.5", 1.5)):
            v_hat = raw if gain == 1.0 else np.clip(inp.speed0 + gain*(raw - inp.speed0), 0.0, 45.0)
            v_pred = np.where(st, 0.0, np.interp(np.arange(j - i + 1), c - i, v_hat))
            rec[f"rms_{name}"] = float(np.sqrt(np.mean((v_pred[mv] - v_true[mv])**2)))
            mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                    FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
            res = particle.run(inp, net, st, rows, params=PARAMS, rng=np.random.default_rng(i),
                               estimator=mt, speed_target=v_pred)
            e, n = smooth.smooth_track(tt, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                       inp.speed0, FIX["catch_up"], FIX["extra"],
                                       close_s=FIX["close_s"], max_factor=FIX["max_factor"])
            m = measure(e, n, tt, tx[r], ty[r], ts[r], true_s, keep, v_true=S.v[i + r])
            rec[name], rec[name + "_off"] = m["path"], m["off"]
        # and the engine as it stands today, for the comparison
        mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
        res = particle.run(inp, net, st, rows, params=PARAMS, rng=np.random.default_rng(i), estimator=mt)
        e, n = smooth.smooth_track(tt, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                   inp.speed0, FIX["catch_up"], FIX["extra"],
                                   close_s=FIX["close_s"], max_factor=FIX["max_factor"])
        m = measure(e, n, tt, tx[r], ty[r], ts[r], true_s, keep, v_true=S.v[i + r])
        rec["held"], rec["held_off"] = m["path"], m["off"]
        recs.append(rec)
    P = pd.DataFrame(recs)
    P.to_parquet(R2/"out/round3_speed_v2.parquet", index=False)

    head("speed error inside the blackouts (RMS m/s, median)")
    print(f"  holding {P.rms_held.median():.2f}   trend model {P.rms_plain.median():.2f}   "
          f"expanded 1.25 {P['rms_expand 1.25'].median():.2f}   expanded 1.5 {P['rms_expand 1.5'].median():.2f}")
    head("in the engine (path average)")
    print(f"  {'variant':<20}{'PATH <10%':>11}{'path med':>10}{'off route':>11}")
    for col, name in (("held", "held speed"), ("plain", "trend model"),
                      ("expand 1.25", "trend, expanded 1.25"), ("expand 1.5", "trend, expanded 1.5")):
        print(f"  {name:<20}{100*(P[col] < 10).mean():>10.0f}%{P[col].median():>9.1f}%{100*P[col + '_off'].mean():>10.0f}%")
    print(f"\n  (for reference, the model without trend features scored 72% / 6.4% on this set)")
    head("by driving condition (held -> trend model)")
    for band in ("slow", "mixed", "ps_60", "fast"):
        g = P[P.band == band]
        if len(g):
            print(f"  {band:<8} n={len(g):4d}   under 10% {100*(g.held < 10).mean():3.0f}% -> {100*(g.plain < 10).mean():3.0f}%"
                  f"   path {g.held.median():5.1f}% -> {g.plain.median():5.1f}%")


if __name__ == "__main__":
    main()
