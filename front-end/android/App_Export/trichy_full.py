"""Round 3 · the whole merged engine on our own rides — learned speed, Tamil Nadu map, reporting layer.

trichy_learned_speed.py measured the speed contribution alone (dead reckoning, no map). This runs the finished
engine: the learned speed steering a road-constrained particle filter on the Tamil Nadu network, reported through the
hysteresis and speed-limited cursor.

Trained on the outbound ride, scored on the return. The gate is on the last known speed, because Tamil Nadu's OSM
carries almost no speed limits (entry 44).

Run from the repo root:  .venv/bin/python3 round2/trichy_full.py
Output: round2/out/trichy_full_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[3]
R2 = ROOT/"round2"
sys.path.insert(0, str(R2))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"analysis/Speed_Model"))
from core import roadnet, sessions, calibration, engine_input, particle, smooth
from vibration_speed import features as vib_features, HOP
from learned_speed_model import map_feats
from trichy_learned_speed import load_segment, blackouts, table, SEG, TN, FLOOR_M
from excursions import track, decompose, episodes, OFF_M
from reporting_layer import measure

T0 = time.time()
PARAMS = json.loads((ROOT/"outputs/Config/pf_params.json").read_text())
FIXR = json.loads((ROOT/"outputs/Config/reporting_layer_choice.json").read_text())
GATE_MS = 12.0                 # hold the last speed above this, learn below (entry 44)
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def as_session(S, name):
    n = len(S["t"])
    return sessions.Session(drive=name, driver="TRICHY", session=0, t=S["t"], acc=S["acc"], gyr=S["gyr"],
                            stuck=np.zeros(n, bool), v=S["v"], lat=S["lat"], lon=S["lon"],
                            heading=S["heading"], dropout=np.zeros(n, bool), dist=S["dist"])


def main():
    head("Round 3 · the merged engine on the Trichy return ride (trained on the outbound)")
    net = roadnet.RoadNetwork(path=TN)
    log(f"Tamil Nadu network loaded: {len(net.seg_u):,} segments")
    raw = {n: load_segment(ROOT/"data/phone_data/segments"/f) for n, f in SEG.items()}
    train = table(raw[1], net)
    feats = [c for c in train.columns if c != "target"]
    mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                        l2_regularization=1.0, random_state=0).fit(
        train[feats].to_numpy(float), train.target.to_numpy(float))
    log(f"speed model trained on {len(train):,} rows from the outbound ride")

    Sr = raw[3]
    S = as_session(Sr, "3_return")
    C = calibration.Calibrator(S)
    bl = blackouts(Sr)
    log(f"{len(bl)} blackouts on the return ride")
    F, c = vib_features(Sr["acc"], Sr["gyr"])
    k = np.arange(0, len(F), max(1, 10//HOP))
    F, c = F[k], c[k]
    M = map_feats(net, S, c)
    stat_all = np.zeros(len(Sr["t"]), bool)          # no stop detector in this path: conservative, no ZUPT

    recs = []
    for nb, (i, j) in enumerate(bl):
        cal = calibration.engine_calibration(C, i, "window")
        if cal is None:
            continue
        inp = engine_input.build(S, cal, i, j)
        st = stat_all[i:j + 1]
        t = inp.t - inp.t[0]
        v0 = float(inp.speed0)
        sel = (c >= i) & (c <= j)
        if sel.sum() < 5:
            continue
        X = np.c_[F[sel], M[sel], np.full(sel.sum(), v0), Sr["t"][c[sel]] - Sr["t"][i]]
        v_hat = np.clip(mdl.predict(X), 0.0, 45.0)
        v_pred = np.interp(np.arange(j - i + 1), c[sel] - i, v_hat)
        gated = v_pred if v0 < GATE_MS else None
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
        rec = dict(v0=v0, avg_kmh=float(3.6*true_s[-1]/max(tt[-1], 1.0)))
        for lab, tgt in (("held", None), ("learned", v_pred), ("gated", gated)):
            mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                    FIXR["margin"], FIXR["hold"], FIXR["release_m"], FIXR["min_share"])
            res = particle.run(inp, net, st, rows, params=PARAMS, rng=np.random.default_rng(i),
                               estimator=mt, speed_target=tgt)
            e, n = smooth.smooth_track(tt, np.asarray(res["east"], float), np.asarray(res["north"], float),
                                       v0, FIXR["catch_up"], FIXR["extra"],
                                       close_s=FIXR["close_s"], max_factor=FIXR["max_factor"])
            m = measure(e, n, tt, tx[r], ty[r], ts[r], true_s, keep, v_true=S.v[i + r])
            rec[lab], rec[lab + "_off"], rec[lab + "_worst"] = m["path"], m["off"], m["worst"]
            rec[lab + "_cross"] = m["worst_cross"]
        recs.append(rec)
        if nb % 10 == 0:
            log(f"  {nb}/{len(bl)}")
    P = pd.DataFrame(recs)
    P.to_parquet(ROOT/"outputs/Results/trichy_full.parquet", index=False)
    P["band"] = pd.cut(P.avg_kmh, [0, 40, 50, 70, 200], labels=["under 40", "40-50", "50-70", "70+"])

    head(f"the merged engine on the return ride — {len(P)} blackouts, with the Tamil Nadu map")
    print(f"  {'variant':<28}{'PATH <10%':>11}{'path med':>10}{'worst med':>11}{'off route':>11}{'worst side':>12}")
    for lab, name in (("held", "round 2 speed (held)"), ("learned", "learned speed everywhere"),
                      ("gated", f"learned below {GATE_MS*3.6:.0f} km/h")):
        print(f"  {name:<28}{100*(P[lab] < 10).mean():>10.0f}%{P[lab].median():>9.1f}%{P[lab + '_worst'].median():>10.1f}%"
              f"{100*P[lab + '_off'].mean():>10.0f}%{P[lab + '_cross'].median():>11.0f}m")
    head("by riding condition (path average, median)")
    print(f"  {'band':<10}{'n':>5}{'held':>9}{'learned':>10}{'gated':>9}{'under 10% held -> gated':>26}")
    for band, g in P.groupby("band", observed=True):
        if len(g):
            print(f"  {str(band):<10}{len(g):>5}{g.held.median():>8.1f}%{g.learned.median():>9.1f}%"
                  f"{g.gated.median():>8.1f}%{100*(g.held < 10).mean():>17.0f}% -> {100*(g.gated < 10).mean():.0f}%")


if __name__ == "__main__":
    main()
