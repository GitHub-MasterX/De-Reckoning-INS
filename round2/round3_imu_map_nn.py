"""Round 3 · the full learned estimator — IMU, map and the last known speed together.

The rider's question in its strongest form: give a model everything the engine has during a blackout — how the car is
shaking and turning (IMU), what road it is on (the map: class, tagged limit, how built-up it is), and the speed at the
last GNSS fix — and let it predict the speed now.

Set up exactly as it would be used: predict the speed 30 s after a fix, from the IMU in that window, the map under the
car, and the speed the fix reported. The benchmark is what the engine does today — hold that last speed. Map features
are read at the TRUE position, which is generous: inside a blackout the filter only has hypotheses.

Cross-validated by session, so the model is never scored on a session it trained on.
Run from the repo root:  .venv/bin/python3 round2/round3_imu_map_nn.py
Output: round2/out/round3_imu_map_nn_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, roadnet
from round3_vibration_speed import features, HOP
from round3_accel_speed import TUNE

T0 = time.time()
LAG_S = 30                     # how long ago the last fix was
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    head(f"Round 3 · IMU + map + the last known speed, predicting the speed {LAG_S} s later")
    net = roadnet.RoadNetwork()
    sel = sessions.selected()
    sel = sel[sel.driver.isin(TUNE)]
    rows = []
    for r in sel.itertuples(index=False):
        S = sessions.load(r.drive, r.driver, int(r.session))
        if S is None:
            continue
        F, c = features(S.acc, S.gyr)
        if len(F) == 0:
            continue
        keep = np.arange(0, len(F), max(1, 10//HOP))          # one sample a second
        F, c = F[keep], c[keep]
        lag = int(LAG_S*10)
        ok = (c >= lag) & np.isfinite(S.v[c]) & np.isfinite(S.v[np.maximum(c - lag, 0)]) & np.isfinite(F).all(axis=1)
        F, c = F[ok], c[ok]
        if len(c) < 50:
            continue
        x, y = roadnet.xy(S.lat[c], S.lon[c])
        m = net.match(x, y, np.radians(S.heading[c]))
        seg = m["seg"]
        lim = np.where(seg >= 0, net.seg_maxspeed[np.maximum(seg, 0)]/3.6, np.nan)
        cls = np.where(seg >= 0, net.seg_class[np.maximum(seg, 0)], -1)
        # how built-up it is: how many distinct road segments sit within 40 m
        near = net.tree.query_ball_point(np.c_[x, y], r=40.0)
        dens = np.array([len(np.unique(net.sample_seg[np.asarray(q, np.int64)])) if len(q) else 0 for q in near])
        v_fix = S.v[c - lag]
        rows.append(pd.DataFrame(np.c_[F, lim, cls, dens, v_fix, m["d_allowed"], S.v[c]],
                                 columns=[f"imu{k}" for k in range(F.shape[1])] +
                                         ["limit", "road_class", "road_density", "v_fix", "dist_to_road", "target"])
                    .assign(group=f"{r.drive}_{r.session}"))
        log(f"  {r.drive}/{r.session} ({r.driver}) — {len(c):,} samples")
    D = pd.concat(rows, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    D = D[np.isfinite(D.target) & np.isfinite(D.v_fix)]
    feats = [c for c in D.columns if c not in ("target", "group")]
    X, y, g = D[feats].to_numpy(float), D.target.to_numpy(float), D.group.to_numpy()

    head("result")
    print(f"  {len(y):,} samples from {len(np.unique(g))} sessions")
    pred = np.empty_like(y)
    imu_only = [c for c in feats if c.startswith("imu")]
    pred_imu = np.empty_like(y)
    Xi = D[imu_only + ["v_fix"]].to_numpy(float)
    for tr, te in GroupKFold(n_splits=min(5, len(np.unique(g)))).split(X, y, g):
        mdl = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_depth=6,
                                            l2_regularization=1.0, random_state=0).fit(X[tr], y[tr])
        pred[te] = mdl.predict(X[te])
        mdl2 = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_depth=6,
                                             l2_regularization=1.0, random_state=0).fit(Xi[tr], y[tr])
        pred_imu[te] = mdl2.predict(Xi[te])
    def rms(a): return float(np.sqrt(np.mean((a - y)**2)))
    print(f"  holding the last fix (what the engine does today) : RMS {rms(D.v_fix.to_numpy()):5.2f} m/s")
    print(f"  model on IMU + last speed                         : RMS {rms(pred_imu):5.2f} m/s")
    print(f"  model on IMU + map + last speed                   : RMS {rms(pred):5.2f} m/s")
    print(f"  a model that learned nothing (the mean)           : RMS {float(np.sqrt(np.mean((y.mean() - y)**2))):5.2f} m/s")
    print(f"\n  needed to be worth using, per the payoff table: about 2 m/s")
    print(f"  correlation of the full model with the truth: {np.corrcoef(pred, y)[0, 1]:.2f}")
    b = pd.DataFrame(dict(v_fix=D.v_fix, y=y, p=pred))
    print("\n  by how fast the car was at the fix (held / model, RMS m/s):")
    for lo, hi in ((0, 8), (8, 14), (14, 20), (20, 40)):
        q = b[(b.v_fix >= lo) & (b.v_fix < hi)]
        if len(q) > 200:
            print(f"    {lo:2d}-{hi:2d} m/s  n={len(q):6,}   held {np.sqrt(((q.v_fix - q.y)**2).mean()):5.2f}   "
                  f"model {np.sqrt(((q.p - q.y)**2).mean()):5.2f}")


if __name__ == "__main__":
    main()
