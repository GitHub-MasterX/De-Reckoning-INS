"""Round 3 · a speed model built on the phone's real sampling rate, not on the dataset's.

Every speed model so far used features from 10 Hz rows, because IO-VNBD is a 10 Hz dataset. On our own recordings that
throws away nine tenths of the signal: at 248 Hz the accelerometer can see wheel rotation (about 9 Hz at 60 km/h),
engine firing and tyre roar, all of which scale with speed. That is why IMU speed estimation works in the literature at
100-200 Hz and fails at 10.

It also lets the rider's hand be separated from the road. A hand moving the phone is rotation about horizontal axes,
which the gyroscope sees; road vibration is not. Both go in as features, so the model can discount one.

  features    per 2 s window of the raw stream: energy in sixteen bands from 0.5 to 120 Hz for the vertical force and
              for the gyroscope, the frequency where the vertical spectrum peaks between 4 and 60 Hz (the wheel line),
              spectral centroid and spread, plus how much the phone itself is being rotated (the hand)
  trained     on the outbound ride only, scored on the return — the protocol the rides were recorded for
  compared    against the 10 Hz-feature model (2.77 m/s RMS) and against holding the last GNSS speed (3.18 m/s)

Run from the repo root:  .venv/bin/python3 round2/round3_native_248.py
Output: round2/out/round3_native_248_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import gzip, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from round3_trichy_learned_speed import load_segment, blackouts, SEG, FLOOR_M, TN
from round3_learned_speed import map_feats
from core import roadnet

T0 = time.time()
WIN_S = 2.0
HOP_S = 0.5
BANDS = np.array([0.5, 1, 2, 3, 5, 8, 12, 18, 25, 35, 45, 60, 75, 90, 105, 124.0])
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def raw(path):
    at, av, gt, gv = [], [], [], []
    with gzip.open(path, "rt") as f:
        for line in f:
            c = line[0]
            if c == "A":
                p = line.split(","); at.append(int(p[1])); av.append((float(p[2]), float(p[3]), float(p[4])))
            elif c == "G":
                p = line.split(","); gt.append(int(p[1])); gv.append((float(p[2]), float(p[3]), float(p[4])))
    return (np.array(at)/1e9, np.array(av)), (np.array(gt)/1e9, np.array(gv))


def native_features(acc, gyr, fs=248.0):
    """One row per window from the raw stream: where the shaking sits in frequency, and how much is the hand."""
    (at, av), (gt, gv) = acc, gyr
    n = int(WIN_S*fs); hop = int(HOP_S*fs)
    if len(at) < 2*n:
        return np.zeros((0, 38)), np.zeros(0)
    # the vertical force: gravity is the slow part of the vector
    k = max(3, int(0.4*fs))
    ker = np.ones(k)/k
    slow = np.vstack([np.convolve(av[:, c], ker, mode="same") for c in range(3)]).T
    up = slow/np.maximum(np.linalg.norm(slow, axis=1)[:, None], 1e-6)
    vert = np.einsum("ij,ij->i", av, up)
    horiz = np.linalg.norm(av - vert[:, None]*up, axis=1)
    gmag = np.linalg.norm(gv, axis=1)
    gyr_on_acc = np.interp(at, gt, gmag)                   # the gyroscope on the accelerometer's clock
    # rotation about horizontal axes = the phone being moved by a hand, rather than the vehicle turning
    gup = np.interp(at, gt, np.einsum("ij,ij->i", gv, np.vstack([np.interp(gt, at, up[:, c]) for c in range(3)]).T)) \
        if len(gt) > 10 else np.zeros(len(at))
    tilt = np.sqrt(np.maximum(gyr_on_acc**2 - gup**2, 0.0))
    starts = np.arange(0, len(at) - n, hop)
    freq = np.fft.rfftfreq(n, 1/fs)
    bidx = [np.where((freq >= BANDS[i]) & (freq < BANDS[i + 1]))[0] for i in range(len(BANDS) - 1)]
    wheel = np.where((freq >= 4) & (freq <= 60))[0]
    out = np.empty((len(starts), 38)); ctr = np.empty(len(starts))
    win = np.hanning(n)
    for r, s in enumerate(starts):
        sl = slice(s, s + n)
        v = vert[sl] - vert[sl].mean()
        g = gyr_on_acc[sl] - gyr_on_acc[sl].mean()
        sv = np.abs(np.fft.rfft(v*win))**2
        sg = np.abs(np.fft.rfft(g*win))**2
        f = [np.log1p(sv[b].sum()) for b in bidx] + [np.log1p(sg[b].sum()) for b in bidx]
        pk = wheel[int(np.argmax(sv[wheel]))]
        tot = max(sv.sum(), 1e-9)
        f += [freq[pk], np.log1p(sv[pk]), float((freq*sv).sum()/tot),
              float(np.sqrt(((freq - (freq*sv).sum()/tot)**2*sv).sum()/tot)),
              float(v.std()), float(horiz[sl].std()), float(tilt[sl].mean()), float(tilt[sl].std())]
        out[r] = f
        ctr[r] = at[s + n//2]
    return out, ctr


def main():
    head("Round 3 · a speed model on the raw 248 Hz stream (train outbound, test return)")
    net = roadnet.RoadNetwork(path=TN)
    log("Tamil Nadu network loaded")
    data, feats = {}, {}
    LAGS = (5, 10, 20, 30, 45, 60, 90)
    for n in (1, 3):
        S = load_segment(R2/"phone_data/segments"/SEG[n])
        a, g = raw(R2/"phone_data/segments"/SEG[n])
        F, ct = native_features(a, g)
        v = np.interp(ct, S["t"], S["v"])
        inside = (ct >= S["t"][0]) & (ct <= S["t"][-1]) & np.isfinite(F).all(axis=1)
        F, ct, v = F[inside], ct[inside], v[inside]
        # the same context the 10 Hz model had: the map under the bike, and the speed at a notional fix
        rowidx = np.searchsorted(S["t"], ct).clip(0, len(S["t"]) - 1)
        M = map_feats(net, type("X", (), {"lat": S["lat"], "lon": S["lon"], "heading": S["heading"]}), rowidx)
        data[n] = S
        feats[n] = (F, ct, v, M, rowidx)
        log(f"segment {n}: {len(ct):,} windows of {WIN_S:g} s from the raw stream")

    def with_context(n, lags):
        F, ct, v, M, rowidx = feats[n]
        X, y = [], []
        for lag in lags:
            back = (rowidx - int(lag*10)).clip(0, None)
            ok = rowidx - int(lag*10) >= 0
            if ok.sum() < 50:
                continue
            X.append(np.c_[F[ok], M[ok], data[n]["v"][back[ok]], np.full(ok.sum(), lag, float)])
            y.append(v[ok])
        return np.vstack(X), np.concatenate(y)

    Xtr, ytr = with_context(1, LAGS)
    mdl = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_depth=6,
                                        l2_regularization=1.0, random_state=0).fit(Xtr, ytr)
    F3, cte, yte, M3, rowidx3 = feats[3]
    Xte = None      # built per blackout below, with the real fix speed and elapsed time
    pred = None
    head("1 · a fixed-horizon check, the same one the 10 Hz model was scored on")
    Xchk, ychk = with_context(3, (30,))
    pchk = np.clip(mdl.predict(Xchk), 0.0, 45.0)
    mv = ychk > 1.0
    held_chk = Xchk[:, -2]
    print(f"  {mv.sum():,} windows, 30 s after a notional fix")
    print(f"  native 248 Hz + map + last speed : RMS {np.sqrt(np.mean((pchk[mv] - ychk[mv])**2)):5.2f} m/s")
    print(f"  holding that last speed          : RMS {np.sqrt(np.mean((held_chk[mv] - ychk[mv])**2)):5.2f} m/s")
    print(f"  (the 10 Hz-feature model scored 2.77 m/s inside blackouts; holding, 3.18)")

    head("2 · inside the blackouts, against holding the last GNSS speed")
    S3 = data[3]
    rows = []
    for i, j in blackouts(S3):
        t = S3["t"][i:j + 1]
        v0 = float(S3["v"][i])
        sel = (cte >= S3["t"][i]) & (cte <= S3["t"][j])
        if sel.sum() < 4:
            continue
        Xb = np.c_[F3[sel], M3[sel], np.full(sel.sum(), v0), cte[sel] - S3["t"][i]]
        pb = np.clip(mdl.predict(Xb), 0.0, 45.0)
        v_pred = np.interp(t, cte[sel], pb)
        v_true = S3["v"][i:j + 1]
        mv = v_true > 0.5
        rows.append(dict(v0=v0, rms_held=float(np.sqrt(np.mean((v0 - v_true[mv])**2))),
                         rms_model=float(np.sqrt(np.mean((v_pred[mv] - v_true[mv])**2))),
                         avg_kmh=float(3.6*(S3["dist"][j] - S3["dist"][i])/max(t[-1] - t[0], 1))))
    P = pd.DataFrame(rows)
    print(f"  {len(P)} blackouts: speed error RMS — holding {P.rms_held.median():.2f} m/s, "
          f"native model {P.rms_model.median():.2f} m/s, better on {100*(P.rms_model < P.rms_held).mean():.0f}%")
    P["band"] = pd.cut(P.avg_kmh, [0, 40, 50, 70, 200], labels=["under 40", "40-50", "50-70", "70+"])
    for band, g in P.groupby("band", observed=True):
        if len(g) >= 3:
            print(f"    {str(band):<9} n={len(g):3d}   holding {g.rms_held.median():5.2f}   native {g.rms_model.median():5.2f} m/s")

    head("3 · what the model leans on")
    names = [f"acc {BANDS[i]:g}-{BANDS[i+1]:g}Hz" for i in range(15)] + \
            [f"gyr {BANDS[i]:g}-{BANDS[i+1]:g}Hz" for i in range(15)] + \
            ["wheel peak freq", "wheel peak power", "centroid", "spread", "vert std", "horiz std",
             "hand rotation mean", "hand rotation std"]
    names += ["limit", "road class", "road density", "distance to road", "speed at the fix", "seconds since"]
    from sklearn.inspection import permutation_importance
    sub = np.random.default_rng(0).choice(len(Xchk), size=min(3000, len(Xchk)), replace=False)
    imp = permutation_importance(mdl, Xchk[sub], ychk[sub], n_repeats=3, random_state=0, n_jobs=1)
    order = np.argsort(imp.importances_mean)[::-1][:8]
    for k in order:
        print(f"    {names[k]:<24} {imp.importances_mean[k]:6.3f}")


if __name__ == "__main__":
    main()
