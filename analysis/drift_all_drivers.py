"""
Drift, per driver, using the SAVED models. Nothing retrains.

For every driver the model used is the one that never saw them (`<D>_holdout`), so each
number is honest. Four strategies over identical blackouts:

  coast        hold the GNSS velocity, no AI at all
  +ZUPT        coast, but the saved classifier forces velocity to zero when it says stopped
  model        the speed-change regressor, retrained per fold from cache
  oracle       the true speed changes  (the evaluator's own sanity check)
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, joblib, time
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
M = Path("models"); FS, HOP = 10.0, 5
STEP = HOP/FS                                   # 0.5 s per window step
t0 = time.time()
z = np.load(M/"eval_cache.npz", allow_pickle=True)
X, lab, drv, sess, v_end, dv, moving = (z["X"], z["label"], z["driver"],
                                        z["session"], z["v_end"], z["dv"], z["moving"])
models = joblib.load(M/"motion_models.pkl")
print(f"loaded cache + models in {time.time()-t0:.1f} s\n")

DISTS = [50, 200, 500, 1000, 1500]
rng = np.random.default_rng(0)
rows = []
for D in ["E","B","A","D"]:
    clf = models[f"{D}_holdout"]                          # never saw this driver
    tr = drv != D
    reg = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06,
                                        random_state=0).fit(X[tr], dv[tr])
    te = drv == D
    pred_stat = clf.predict(X[te]) == 0                   # classifier says stationary
    pred_dv   = reg.predict(X[te])
    v_, dv_, sess_, mov_ = v_end[te], dv[te], sess[te], moving[te]
    acc = {k: {d: [] for d in DISTS} for k in ("coast","zupt","model","oracle")}
    for s in np.unique(sess_):
        m = sess_ == s
        v, dvt, ps, pd_, mv = v_[m], dv_[m], pred_stat[m], pred_dv[m], mov_[m]
        cum = np.concatenate(([0], np.cumsum(v)*STEP))
        for dist in DISTS:
            starts = [i for i in range(0, len(v)-10, 4) if v[i] > 4.2]
            if not starts: continue
            for i in rng.choice(starts, size=min(200, len(starts)), replace=False):
                j = np.searchsorted(cum, cum[i] + dist)
                if j >= len(v) or not mv[i:j].all(): continue
                d_true = float(np.sum(v[i:j])*STEP)
                if d_true < dist*0.5: continue
                for key in ("coast","zupt","model","oracle"):
                    ve, de = v[i], 0.0
                    for k in range(i, j):
                        if key == "model":  ve += pd_[k]
                        if key == "oracle": ve += dvt[k]
                        if key == "zupt" and ps[k]: ve = 0.0
                        de += max(ve, 0.0)*STEP
                    acc[key][dist].append(abs(de-d_true)/d_true*100)
    for dist in DISTS:
        if not acc["coast"][dist]: continue
        rows.append(dict(driver=D, dist_m=dist, n=len(acc["coast"][dist]),
            **{k: round(float(np.median(acc[k][dist])), 1) for k in acc}))

import pandas as pd
T = pd.DataFrame(rows); T.to_csv("out/drift_all_drivers.csv", index=False)
NAME = {"E":"steady highway  (the PS scenario)","B":"urban / mixed",
        "A":"urban / mixed","D":"dense urban"}
print("PERCENTAGE DRIFT BY DRIVER   —   models loaded from .pkl, each driver unseen\n")
for D in ["E","B","A","D"]:
    s = T[T.driver == D]
    if not len(s): continue
    print(f"  Driver {D} — {NAME[D]}")
    print(f"    {'distance':>10}{'coast':>9}{'+ZUPT':>9}{'model':>9}{'oracle':>9}{'coast m':>10}{'':>4}")
    for _, r in s.iterrows():
        best = min(r.coast, r.zupt)
        flag = "  PASS" if best < 10 else ""
        print(f"    {int(r.dist_m):>8} m{r.coast:>8.1f}%{r.zupt:>8.1f}%{r.model:>8.1f}%"
              f"{r.oracle:>8.1f}%{r.dist_m*best/100:>9.1f} m{flag}")
    print()
print(f"total wall time: {time.time()-t0:.0f} s")
