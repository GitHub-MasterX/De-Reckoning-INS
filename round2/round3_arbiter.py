"""Round 3 · who should decide — an arbiter that picks holding or the learned speed, blackout by blackout.

Round 2's held speed wins where the road is plain and the car keeps its speed; the learned model wins where the car
changes speed and the surroundings say so. A hand-made rule already exploits part of that (hold on fast roads). This
asks whether the choice itself can be learned from what is known when GNSS dies — and what a perfect chooser would be
worth, which is the ceiling for the whole idea.

  features    only what the engine has at the fix: the speed then, the road under it (class, limit, how built-up),
              how the car had been accelerating and turning, and what the speed model itself predicts for the next
              minute (its mean, spread and trend) — the model's own opinion is a legitimate input to the arbiter
  label       which expert actually scored better on that blackout
  honesty     cross-validated by session; the arbiter never decides a blackout from a session it trained on
  ceiling     the oracle arbiter, which knows the answer, is reported as the upper bound

Tuning drivers only. Run:  .venv/bin/python3 round2/round3_arbiter.py [--limit 400]
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, smooth
from round3_vibration_speed import features as vib_features, HOP
from round3_learned_speed import training_table, map_feats
from round3_accel_speed import CHOICE, TUNE, FLOOR_M
from round3_excursions import track
from round3_report_fix import measure

T0 = time.time()
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())
def arg(f, d): return type(d)(sys.argv[sys.argv.index(f) + 1]) if f in sys.argv else d
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    limit = arg("--limit", 400)
    head("Round 3 · can we learn who should decide, holding or the model?")
    net = roadnet.RoadNetwork()
    D = training_table(net, TUNE)
    feats = [c for c in D.columns if c not in ("target", "group")]
    models = {}
    for g in D.group.unique():
        tr = D[D.group != g]
        models[g] = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                                  l2_regularization=1.0, random_state=0).fit(
            tr[feats].to_numpy(float), tr.target.to_numpy(float))
    log(f"speed models ready ({len(models)})")

    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    rows, cache = [], {}
    for nb, b in enumerate(BL.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
            log(f"  {b.drive}/{b.session} — {nb}/{len(BL)}")
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None or i < 300:
            continue
        inp = engine_input.build(S, cal, i, j)
        st = stat[i:j + 1]
        t = inp.t - inp.t[0]
        F, c = vib_features(S.acc[i:j + 1], S.gyr[i:j + 1])
        if len(F) == 0:
            continue
        k = np.arange(0, len(F), max(1, 10//HOP))
        F, c = F[k], c[k]
        M = map_feats(net, S, i + c)
        X = np.c_[F, M, np.full(len(c), inp.speed0), t[c]]
        v_hat = np.clip(models[f"{b.drive}_{b.session}"].predict(X), 0.0, 45.0)
        v_pred = np.where(st, 0.0, np.interp(np.arange(j - i + 1), c, v_hat))
        tx, ty, ts = track(S, i, j)
        rr = list(range(10, j - i + 1, 10))
        if len(rr) < 5:
            continue
        r = np.asarray(rr, np.int64)
        tt = inp.t[r] - inp.t[0]
        true_s = S.dist[i + r] - S.dist[i]
        keep = true_s >= FLOOR_M
        if keep.sum() < 3:
            continue
        got = {}
        for lab, tgt in (("held", None), ("model", v_pred)):
            mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                    FIX["margin"], FIX["hold"], FIX["release_m"], FIX["min_share"])
            res = particle.run(inp, net, st, rr, params=PARAMS, rng=np.random.default_rng(i),
                               estimator=mt, speed_target=tgt)
            e, n = smooth.smooth_track(tt, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                       inp.speed0, FIX["catch_up"], FIX["extra"],
                                       close_s=FIX["close_s"], max_factor=FIX["max_factor"])
            got[lab] = measure(e, n, tt, tx[r], ty[r], ts[r], true_s, keep, v_true=S.v[i + r])["path"]
        mf = M[0] if len(M) else [np.nan]*4
        rows.append(dict(group=f"{b.drive}_{b.session}", driver=b.driver, band=b.band_1000,
                         v0=float(inp.speed0), limit=float(mf[0]), road_class=float(mf[1]),
                         density=float(mf[2]), dist_road=float(mf[3]),
                         accel10=float((S.v[i] - S.v[i - 100])/10.0) if np.isfinite(S.v[i - 100]) else np.nan,
                         accel30=float((S.v[i] - S.v[i - 300])/30.0) if i >= 300 and np.isfinite(S.v[i - 300]) else np.nan,
                         gyro_rms=float(np.sqrt((S.gyr[max(0, i - 600):i]**2).sum(axis=1).mean())),
                         pred_mean=float(np.mean(v_hat)), pred_std=float(np.std(v_hat)),
                         pred_trend=float(v_hat[-1] - v_hat[0]), pred_gap=float(np.mean(v_hat) - inp.speed0),
                         held=got["held"], model=got["model"]))
    P = pd.DataFrame(rows)
    P.to_parquet(R2/"out/round3_arbiter.parquet", index=False)
    head("what each expert scores on its own")
    print(f"  {len(P)} blackouts · always hold: under 10% {100*(P.held < 10).mean():.0f}%, median {P.held.median():.1f}%")
    print(f"  {'':<18} always model: under 10% {100*(P.model < 10).mean():.0f}%, median {P.model.median():.1f}%")
    best = P[["held", "model"]].min(axis=1)
    print(f"  a perfect chooser (the ceiling): under 10% {100*(best < 10).mean():.0f}%, median {best.median():.1f}%")

    head("can the choice be learned?")
    fcols = ["v0", "limit", "road_class", "density", "dist_road", "accel10", "accel30", "gyro_rms",
             "pred_mean", "pred_std", "pred_trend", "pred_gap"]
    X, g = P[fcols].to_numpy(float), P.group.to_numpy()
    y = (P.model < P.held).astype(int).to_numpy()
    pick = np.zeros(len(P), int)
    for tr, te in GroupKFold(n_splits=min(5, len(np.unique(g)))).split(X, y, g):
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, max_depth=4, random_state=0)
        clf.fit(X[tr], y[tr])
        pick[te] = clf.predict(X[te])
    chosen = np.where(pick == 1, P.model, P.held)
    print(f"  the arbiter picks the model on {100*pick.mean():.0f}% of blackouts; it is right {100*(pick == y).mean():.0f}% of the time")
    print(f"  arbiter result: under 10% {100*(chosen < 10).mean():.0f}%, median {np.median(chosen):.1f}%")
    print(f"\n  for comparison — the hand-made rule (hold on fast roads):")
    handmade = np.where(P.limit.fillna(0) >= 22.0, P.held, P.model)
    print(f"  under 10% {100*(handmade < 10).mean():.0f}%, median {np.median(handmade):.1f}%")


if __name__ == "__main__":
    main()
