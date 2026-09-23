"""Round 3 · the learned speed on our own rides — a two-wheeler, a 248 Hz phone, a Tamil Nadu map.

The learned speed was built and tested on IO-VNBD: cars, a 10 Hz IMU, England. This asks whether the same idea
survives a change of everything — a motorcycle instead of a car, a phone held in a hand instead of fixed in a cabin,
sensors at 248 Hz instead of 10, and roads in Tiruchirappalli instead of Coventry.

Protocol as before, and as the rides were always meant to be used: **trained on the outbound ride, tested on the
return**, with the town ride kept as a second test. Nothing is fitted on the ride it is scored on.

  rows        the recording binned to 10 Hz (the mean of every accelerometer and gyroscope sample in each 100 ms),
              which is what the phone's own engine feeds its 10 Hz path
  features    the same as on IO-VNBD: the shaking, the map under the bike, the speed at the last fix and how long ago
  blackouts   the replay rule: a start every 250 m once there are 5 minutes of history and the bike is above 15 km/h
  scored      speed error against the phone's GNSS, and the path-average position error of dead reckoning

Run from the repo root:  .venv/bin/python3 round2/round3_trichy_learned_speed.py
Output: round2/out/round3_trichy_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import gzip, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import roadnet, deadreckoning
from core.geo import enu
from round3_vibration_speed import features as vib_features, HOP
from round3_learned_speed import map_feats

T0 = time.time()
SEG = {1: "1_outbound.csv.gz", 2: "2_town_tuning.csv.gz", 3: "3_return.csv.gz"}
TN = ROOT/"data/osm/road_network_tn.npz"
FLOOR_M = 100.0
LAGS = (5, 10, 20, 30, 45, 60, 90)

def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def load_segment(path):
    """The recording as 10 Hz rows: time, mean accelerometer, mean gyroscope, and the GNSS interpolated onto them."""
    at, av, gt, gv, ft = [], [], [], [], []
    with gzip.open(path, "rt") as f:
        for line in f:
            if not line or line[0] == "#":
                continue
            p = line.rstrip("\n").split(",")
            if p[0] == "A":
                at.append(int(p[1])); av.append((float(p[2]), float(p[3]), float(p[4])))
            elif p[0] == "G":
                gt.append(int(p[1])); gv.append((float(p[2]), float(p[3]), float(p[4])))
            elif p[0] == "L" and len(p) >= 13:
                ft.append((int(p[1])/1e9, float(p[3]), float(p[4]),
                           float(p[7]) if p[11] == "1" else np.nan,
                           float(p[9]) if p[12] == "1" else np.nan))
    at = np.array(at)/1e9; av = np.array(av); gt = np.array(gt)/1e9; gv = np.array(gv)
    F = np.array(ft)
    t0, t1 = max(at[0], gt[0]), min(at[-1], gt[-1])
    edges = np.arange(t0, t1, 0.1)
    def binned(ts, vs):
        idx = np.clip(np.searchsorted(edges, ts) - 1, 0, len(edges) - 2)
        out = np.zeros((len(edges) - 1, 3)); cnt = np.zeros(len(edges) - 1)
        np.add.at(out, idx, vs); np.add.at(cnt, idx, 1.0)
        cnt = np.where(cnt > 0, cnt, np.nan)
        return out/cnt[:, None]
    acc, gyr = binned(at, av), binned(gt, gv)
    t = edges[:-1] + 0.05
    ok = np.isfinite(acc).all(axis=1) & np.isfinite(gyr).all(axis=1)
    # the GNSS, interpolated onto the same rows; bearings unwrapped so the interpolation does not cross north wrongly
    lat = np.interp(t, F[:, 0], F[:, 1]); lon = np.interp(t, F[:, 0], F[:, 2])
    sp = F[:, 3].copy(); sp[~np.isfinite(sp)] = 0.0
    v = np.interp(t, F[:, 0], sp)
    br = F[:, 4].copy()
    good = np.isfinite(br)
    hd = np.degrees(np.interp(t, F[good, 0], np.unwrap(np.radians(br[good])))) % 360.0
    dist = np.concatenate(([0.0], np.cumsum(0.5*(v[1:] + v[:-1])*np.diff(t))))
    fresh = np.interp(t, F[:, 0], np.arange(len(F)))         # only rows inside the GNSS span are usable
    inside = (t >= F[0, 0]) & (t <= F[-1, 0])
    return dict(t=t[ok & inside], acc=acc[ok & inside], gyr=gyr[ok & inside], v=v[ok & inside],
                lat=lat[ok & inside], lon=lon[ok & inside], heading=hd[ok & inside], dist=dist[ok & inside])


def blackouts(S):
    """The replay rule: a start every 250 m of GNSS distance, after 5 min of history, above 15 km/h, running 1 km."""
    out = []
    next_at = 250.0
    for k in range(len(S["t"])):
        if S["dist"][k] >= next_at:
            next_at += 250.0
            if S["t"][k] - S["t"][0] >= 300 and S["v"][k] > 4.2:
                end = np.searchsorted(S["dist"], S["dist"][k] + 1000.0)
                if end < len(S["t"]):
                    out.append((k, int(end)))
    return out


def table(S, net, lags=LAGS, step=10):
    """Training rows: the shaking now, the map now, the speed a lag ago, and the true speed now."""
    F, c = vib_features(S["acc"], S["gyr"])
    if len(F) == 0:
        return pd.DataFrame()
    k = np.arange(0, len(F), max(1, step//HOP))
    F, c = F[k], c[k]
    M = map_feats(net, type("X", (), {"lat": S["lat"], "lon": S["lon"], "heading": S["heading"]}), c)
    frames = []
    for lag in lags:
        back = c - lag*10
        good = back >= 0
        if good.sum() < 50:
            continue
        frames.append(pd.DataFrame(
            np.c_[F[good], M[good], S["v"][back[good]], np.full(good.sum(), lag, float), S["v"][c[good]]],
            columns=[f"imu{i}" for i in range(F.shape[1])] +
                    ["limit", "road_class", "road_density", "dist_to_road", "v_fix", "lag", "target"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main():
    head("Round 3 · the learned speed on the Trichy rides (train on the outbound, test on the return)")
    net = roadnet.RoadNetwork(path=TN)
    log(f"Tamil Nadu network: {len(net.seg_u):,} segments")
    S = {}
    for n, fn in SEG.items():
        S[n] = load_segment(R2/"phone_data/segments"/fn)
        log(f"segment {n}: {len(S[n]['t']):,} rows, {S[n]['dist'][-1]/1000:.1f} km, "
            f"median {3.6*np.median(S[n]['v'][S[n]['v'] > 1]):.0f} km/h")

    train = table(S[1], net)
    log(f"training rows from the outbound ride: {len(train):,}")
    feats = [c for c in train.columns if c != "target"]
    mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=6,
                                        l2_regularization=1.0, random_state=0).fit(
        train[feats].to_numpy(float), train.target.to_numpy(float))

    for n in (3, 2):
        Sn = S[n]
        bl = blackouts(Sn)
        head(f"segment {n} ({SEG[n]}) — {len(bl)} blackouts")
        if not bl:
            print("  too short for the blackout rule")
            continue
        F, c = vib_features(Sn["acc"], Sn["gyr"])
        k = np.arange(0, len(F), max(1, 10//HOP))
        F, c = F[k], c[k]
        M = map_feats(net, type("X", (), {"lat": Sn["lat"], "lon": Sn["lon"], "heading": Sn["heading"]}), c)
        rows = []
        for i, j in bl:
            t = Sn["t"][i:j + 1] - Sn["t"][i]
            v_true = Sn["v"][i:j + 1]
            v0 = float(Sn["v"][i])
            sel = (c >= i) & (c <= j)
            if sel.sum() < 5:
                continue
            X = np.c_[F[sel], M[sel], np.full(sel.sum(), v0), Sn["t"][c[sel]] - Sn["t"][i]]
            v_hat = np.clip(mdl.predict(X), 0.0, 45.0)
            v_pred = np.interp(np.arange(j - i + 1), c[sel] - i, v_hat)
            e0, n0 = enu(Sn["lat"][i:j + 1], Sn["lon"][i:j + 1], Sn["lat"][i], Sn["lon"][i])
            true_s = Sn["dist"][i:j + 1] - Sn["dist"][i]
            keep = true_s >= FLOOR_M
            psi = np.radians(Sn["heading"][i:j + 1])
            def dr(speed):
                dt = np.diff(t)
                st = speed[:-1]*dt
                e = np.concatenate(([0.0], np.cumsum(st*np.sin(psi[:-1]))))
                nn = np.concatenate(([0.0], np.cumsum(st*np.cos(psi[:-1]))))
                p = 100*np.hypot(e - np.asarray(e0, float), nn - np.asarray(n0, float))/np.maximum(true_s, 1e-9)
                return float(p[keep].mean())
            moving = v_true > 0.5
            lim0 = float(M[sel][0][0]) if sel.sum() else np.nan
            fast_road = np.isfinite(lim0) and lim0 >= 22.0
            # Tamil Nadu OSM has almost no speed limits, so the road-class gate never fires here; the last known
            # speed is the gate that needs no tags at all
            dr_pred, dr_hold = dr(v_pred), dr(np.full(len(t), v0))
            rows.append(dict(v0=v0, limit=lim0, fast_road=fast_road,
                             dr_gated=dr_hold if fast_road else dr_pred,
                             dr_v12=dr_hold if v0 >= 12.0 else dr_pred,
                             dr_v14=dr_hold if v0 >= 14.0 else dr_pred,
                             dr_v16=dr_hold if v0 >= 16.0 else dr_pred, rms_held=float(np.sqrt(np.mean((v0 - v_true[moving])**2))),
                             rms_model=float(np.sqrt(np.mean((v_pred[moving] - v_true[moving])**2))),
                             dr_held=dr(np.full(len(t), v0)), dr_model=dr(v_pred), dr_true=dr(v_true),
                             band="under 40" if 3.6*true_s[-1]/(t[-1] or 1) < 40 else
                                  ("40-50" if 3.6*true_s[-1]/(t[-1] or 1) < 50 else
                                   ("50-70" if 3.6*true_s[-1]/(t[-1] or 1) < 70 else "70+"))))
        P = pd.DataFrame(rows)
        if P.empty:
            print("  nothing scored")
            continue
        print(f"  speed error, RMS m/s:   holding {P.rms_held.median():5.2f}   learned {P.rms_model.median():5.2f}"
              f"   better on {100*(P.rms_model < P.rms_held).mean():3.0f}% of blackouts")
        print(f"  dead reckoning (no map), path average, median:")
        print(f"    holding {P.dr_held.median():5.1f}%   learned {P.dr_model.median():5.1f}%   "
              f"true speed {P.dr_true.median():5.1f}%")
        print(f"    gated (hold on a fast road, learn elsewhere) {P.dr_gated.median():5.1f}%   "
              f"— {100*P.fast_road.mean():.0f}% of blackouts start on a fast road")
        print(f"    under 10%: holding {100*(P.dr_held < 10).mean():3.0f}%   learned {100*(P.dr_model < 10).mean():3.0f}%")
        print("    gated on the last known speed (hold above the threshold, learn below):")
        for col, th in (("dr_v12", 12), ("dr_v14", 14), ("dr_v16", 16)):
            print(f"      above {th*3.6:.0f} km/h hold   path {P[col].median():5.1f}%   "
                  f"under 10% {100*(P[col] < 10).mean():3.0f}%   (applies to {100*(P.v0 < th).mean():.0f}% of blackouts)")
        for band, g in P.groupby("band"):
            if len(g) >= 3:
                print(f"    {band:<9} n={len(g):3d}   held {g.dr_held.median():5.1f}%   learned {g.dr_model.median():5.1f}%"
                      f"   gated {g.dr_gated.median():5.1f}%")


if __name__ == "__main__":
    main()
