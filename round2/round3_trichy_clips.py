"""Round 3 · Trichy replay clips for the app, through the merged engine.

Each clip shows the same blackout twice: the merged engine (round 1's classifier, the learned speed, round 2's
map-matched filter on the Tamil Nadu network, round 3's reporting layer) against round 2's held-speed cursor.

The outbound and return rides cover one corridor twice and consecutive blackouts overlap by design, so clips are
**deduplicated by route**: no two clips may share more than a fifth of their path. What is left is spread over the
whole trip.

Run from the repo root:  .venv/bin/python3 round2/round3_trichy_clips.py [--per-ride 4]
"""
import warnings; warnings.filterwarnings("ignore")
import json, shutil, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import roadnet, sessions, calibration, engine_input, particle, smooth
from core.geo import enu, inv_enu
from round3_vibration_speed import features as vib_features, HOP
from round3_learned_speed import map_feats
from round3_trichy_learned_speed import load_segment, blackouts, table, SEG, TN, FLOOR_M
from round3_trichy_full import as_session, GATE_MS

T0 = time.time()
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
FIXR = json.loads((R2/"out/round3_report_choice.json").read_text())
OUT = R2/"out/replay_trichy"
ASSETS = R2/"android/app/src/main/assets/replay"
RIDE = {1: "Trichy out", 3: "Trichy back"}
OVERLAP_MAX = 0.20
R = 6371000.0

def arg(f, d): return type(d)(sys.argv[sys.argv.index(f) + 1]) if f in sys.argv else d
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)


def route_overlap(a, b):
    (la1, lo1), (la2, lo2) = a, b
    k = np.cos(np.radians(la1.mean()))
    x1, y1 = np.radians(lo1)*R*k, np.radians(la1)*R
    x2, y2 = np.radians(lo2)*R*k, np.radians(la2)*R
    step = max(1, len(x1)//60)
    near = sum(1 for i in range(0, len(x1), step) if np.min((x2 - x1[i])**2 + (y2 - y1[i])**2) < 30.0**2)
    return near/len(range(0, len(x1), step))


def main():
    per_ride = arg("--per-ride", 4)
    net = roadnet.RoadNetwork(path=TN)
    log(f"Tamil Nadu network: {len(net.seg_u):,} segments")
    raw = {n: load_segment(R2/"phone_data/segments"/f) for n, f in SEG.items()}
    train = table(raw[1], net)
    feats = [c for c in train.columns if c != "target"]
    mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                        l2_regularization=1.0, random_state=0).fit(
        train[feats].to_numpy(float), train.target.to_numpy(float))
    log(f"speed model trained on the outbound ride ({len(train):,} rows)")

    OUT.mkdir(parents=True, exist_ok=True)
    made, index = [], []
    for seg in (1, 3):
        Sr = raw[seg]
        S = as_session(Sr, f"trichy{seg}")
        C = calibration.Calibrator(S)
        F, c = vib_features(Sr["acc"], Sr["gyr"])
        k = np.arange(0, len(F), max(1, 10//HOP))
        F, c = F[k], c[k]
        M = map_feats(net, S, c)
        stat = np.zeros(len(Sr["t"]), bool)
        kept = 0
        for i, j in blackouts(Sr):
            if kept >= per_ride:
                break
            cal = calibration.engine_calibration(C, i, "window")
            if cal is None:
                continue
            la, lo = Sr["lat"][i:j + 1], Sr["lon"][i:j + 1]
            if any(route_overlap((la, lo), prev) > OVERLAP_MAX for prev in made):
                continue                                   # same stretch of road as a clip we already have
            inp = engine_input.build(S, cal, i, j)
            t = inp.t - inp.t[0]
            v0 = float(inp.speed0)
            sel = (c >= i) & (c <= j)
            if sel.sum() < 5:
                continue
            X = np.c_[F[sel], M[sel], np.full(sel.sum(), v0), Sr["t"][c[sel]] - Sr["t"][i]]
            v_pred = np.interp(np.arange(j - i + 1), c[sel] - i,
                               np.clip(mdl.predict(X), 0.0, 45.0))
            target = v_pred if v0 < GATE_MS else None
            rows = list(range(1, j - i + 1))
            tracks = {}
            for lab, tgt in (("new", target), ("old", None)):
                mt = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                        FIXR["margin"], FIXR["hold"], FIXR["release_m"], FIXR["min_share"]) \
                    if lab == "new" else None
                res = particle.run(inp, net, stat[i:j + 1], rows, params=PARAMS,
                                   rng=np.random.default_rng(i), estimator=mt, speed_target=tgt)
                e = np.r_[0.0, np.asarray(res["east"], float)]
                n = np.r_[0.0, np.asarray(res["north"], float)]
                tt = np.r_[0.0, t[np.asarray(res["rows"], np.int64)]]
                if lab == "new":
                    e, n = smooth.smooth_track(tt, e, n, v0, FIXR["catch_up"], FIXR["extra"],
                                               close_s=FIXR["close_s"], max_factor=FIXR["max_factor"])
                tracks[lab] = (e, n, np.r_[False, np.asarray(res["on_map"], bool)])
            true_e, true_n = enu(la, lo, la[0], lo[0])
            true_e, true_n = np.asarray(true_e, float), np.asarray(true_n, float)
            true_s = Sr["dist"][i:j + 1] - Sr["dist"][i]
            dist = np.maximum(true_s, 1e-6)
            ne, nn, onmap = tracks["new"]
            oe, on_, _ = tracks["old"]
            new_m = np.hypot(ne - true_e, nn - true_n)
            old_m = np.hypot(oe - true_e, on_ - true_n)
            scored = true_s >= FLOOR_M
            lat_n, lon_n = inv_enu(ne, nn, la[0], lo[0])
            lat_o, lon_o = inv_enu(oe, on_, la[0], lo[0])
            psi = inp.course0 + np.concatenate(([0.0], np.cumsum(inp.turn_rate()[:-1]*np.diff(inp.t))))
            kept += 1
            cid = f"trichy_{seg}_{i}"
            avg = 3.6*true_s[-1]/max(t[-1], 1.0)
            clip = dict(
                id=cid, driver="TRICHY", role="live ride",
                drive=f"{RIDE[seg]} {kept}", session=seg, row_start=int(i),
                band="slow" if avg < 40 else ("mixed" if avg < 50 else ("ps_60" if avg < 70 else "fast")),
                turns=int(round(np.abs(np.degrees(np.diff(psi))).sum()/45)),
                avg_kmh=round(float(avg), 1), distance_m=round(float(true_s[-1]), 1),
                duration_s=round(float(t[-1]), 1), hz=10,
                tracks="cyan = merged engine (learned speed + map + reporting), red = round 2's held-speed cursor",
                final_drift_m=round(float(new_m[-1]), 1),
                final_drift_pct=round(float(100*new_m[-1]/dist[-1]), 2),
                final_base_m=round(float(old_m[-1]), 1),
                final_base_pct=round(float(100*old_m[-1]/dist[-1]), 2),
                mean_drift_pct=round(float(np.mean(100*new_m[scored]/dist[scored])), 2),
                mean_base_pct=round(float(np.mean(100*old_m[scored]/dist[scored])), 2),
                lead_in=dict(lat=[round(float(v), 7) for v in Sr["lat"][max(0, i - 150):i]],
                             lon=[round(float(v), 7) for v in Sr["lon"][max(0, i - 150):i]],
                             heading=[round(float(v), 1) for v in Sr["heading"][max(0, i - 150):i]],
                             speed_kmh=[round(float(3.6*v), 1) for v in Sr["v"][max(0, i - 150):i]]),
                t=[round(float(v), 2) for v in t],
                true_lat=[round(float(v), 7) for v in la], true_lon=[round(float(v), 7) for v in lo],
                true_heading=[round(float(v), 1) for v in Sr["heading"][i:j + 1]],
                true_speed_kmh=[round(float(3.6*v), 1) for v in Sr["v"][i:j + 1]],
                true_dist_m=[round(float(v), 1) for v in true_s],
                pf_lat=[round(float(v), 7) for v in lat_n], pf_lon=[round(float(v), 7) for v in lon_n],
                pf_heading=[round(float(np.degrees(v) % 360), 1) for v in psi],
                pf_on_map=[bool(v) for v in onmap],
                nomap_lat=[round(float(v), 7) for v in lat_o], nomap_lon=[round(float(v), 7) for v in lon_o],
                drift_m=[round(float(v), 1) for v in new_m],
                drift_pct=[round(float(100*a/b), 2) for a, b in zip(new_m, dist)],
                nomap_drift_m=[round(float(v), 1) for v in old_m],
                nomap_drift_pct=[round(float(100*a/b), 2) for a, b in zip(old_m, dist)],
                engine_speed_kmh=round(float(3.6*v0), 1))
            (OUT/f"{cid}.json").write_text(json.dumps(clip, separators=(",", ":")))
            made.append((la, lo))
            index.append({k2: clip[k2] for k2 in ("id", "driver", "role", "drive", "session", "band", "turns",
                                                 "avg_kmh", "distance_m", "duration_s", "final_drift_m",
                                                 "final_drift_pct", "final_base_m", "final_base_pct",
                                                 "mean_drift_pct", "mean_base_pct")})
            log(f"  {cid:<18} {clip['drive']:<14} {clip['band']:<6} {avg:3.0f} km/h   "
                f"round 2 {clip['mean_base_pct']:5.1f}% -> merged {clip['mean_drift_pct']:5.1f}%")

    for f in OUT.glob("*.json"):
        shutil.copy(f, ASSETS/f.name)
    idx = json.loads((ASSETS/"index.json").read_text())
    idx["clips"] = [c for c in idx["clips"] if not c["id"].startswith("trichy_")] + index
    (ASSETS/"index.json").write_text(json.dumps(idx, indent=1))
    log(f"done — {len(index)} Trichy clips added, {len(idx['clips'])} in the app")


if __name__ == "__main__":
    main()
