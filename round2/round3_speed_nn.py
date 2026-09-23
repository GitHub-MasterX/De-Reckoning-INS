"""Round 3 · how much of the future speed is predictable at all? — the ceiling for any learned speed model.

The rider's idea: train a model to weight or predict the speed the engine should use, instead of holding the last GNSS
speed. A model can only use what is in its inputs, and the IMU cannot see speed at 10 Hz (entries 39-42). But the
moment GNSS dies, the engine does know a great deal of *context*: how the car had been driving for the last minute,
how it was accelerating, what road it is on, how much it had been turning. Regression to the mean (entry 42) used one
line through that; this asks what the best possible use of it is worth.

Gradient boosting (the family round 1's classifier came from), features taken only from before the blackout, targets
the true speed at 10/20/30/45/60/90 s after it. Cross-validated by session, so the model is never scored on a session
it trained on. Compared against holding the last GNSS speed, which is what the engine does today.

Tuning drivers only. Run from the repo root:  .venv/bin/python3 round2/round3_speed_nn.py [--limit 900]
Output: round2/out/round3_speed_nn_run.txt
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
from round3_accel_speed import TUNE

T0 = time.time()
FS = 10.0
HORIZONS = (10, 20, 30, 45, 60, 90)

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*96}\n{t}\n{'='*96}")


def main():
    limit = arg("--limit", 900)
    head("Round 3 · the ceiling for a learned speed model (tuning drivers A+B)")
    BL = pd.read_parquet(R2/"out/blackouts.parquet")
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()]
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    net = roadnet.RoadNetwork()
    rows, key, S = [], None, None
    for nb, b in enumerate(BL.itertuples(index=False)):
        if (b.drive, int(b.session)) != key:
            key = (b.drive, int(b.session)); S = sessions.load(b.drive, b.driver, int(b.session))
            log(f"  {b.drive}/{b.session} — {nb}/{len(BL)}")
        i = int(b.row_start)
        v0 = float(S.v[i])
        if not np.isfinite(v0) or i < 600:
            continue
        # everything the engine legitimately knows at the moment GNSS dies
        hist = S.v[max(0, i - 600):i]
        hist = hist[np.isfinite(hist)]
        if len(hist) < 300:
            continue
        g = S.gyr[max(0, i - 600):i]
        x, y = roadnet.xy(np.array([S.lat[i]]), np.array([S.lon[i]]))
        m = net.match(x, y, np.radians(np.array([S.heading[i]])))
        seg = int(m["seg"][0])
        lim = float(net.seg_maxspeed[seg])/3.6 if seg >= 0 else np.nan
        cls = int(net.seg_class[seg]) if seg >= 0 else -1
        f = dict(v0=v0,
                 mean30=float(hist[-300:].mean()), mean60=float(hist.mean()),
                 std30=float(hist[-300:].std()), std60=float(hist.std()),
                 min60=float(hist.min()), max60=float(hist.max()),
                 accel5=float((S.v[i] - S.v[i - 50])/5.0), accel10=float((S.v[i] - S.v[i - 100])/10.0),
                 accel30=float((S.v[i] - S.v[i - 300])/30.0),
                 share_slow=float((hist < 5).mean()), share_fast=float((hist > 20).mean()),
                 gyro_rms=float(np.sqrt((g**2).sum(axis=1).mean())),
                 limit=lim, road_class=cls, v0_over_limit=v0/lim if np.isfinite(lim) and lim > 1 else np.nan)
        for h in HORIZONS:
            k = i + int(h*FS)
            if k < len(S.v) and np.isfinite(S.v[k]):
                rows.append({**f, "h": h, "target": float(S.v[k]), "group": f"{b.drive}_{b.session}"})
    D = pd.DataFrame(rows)
    log(f"{len(D):,} samples from {D.group.nunique()} sessions")

    head("error in the speed a minute or so after the fix (m/s, cross-validated by session)")
    print(f"  {'horizon':<9}{'n':>7}{'holding v0':>13}{'regression line':>18}{'gradient boosting':>20}{'gain':>9}")
    feats = [c for c in D.columns if c not in ("target", "h", "group")]
    for h in HORIZONS:
        g = D[D.h == h]
        if len(g) < 200:
            continue
        X, y, grp = g[feats].to_numpy(float), g.target.to_numpy(float), g.group.to_numpy()
        held = np.sqrt(np.mean((g.v0.to_numpy() - y)**2))
        # a straight line through v0, cross-validated the same way
        pred_lin = np.empty_like(y); pred_gb = np.empty_like(y)
        for tr, te in GroupKFold(n_splits=min(5, len(np.unique(grp)))).split(X, y, grp):
            c = np.polyfit(g.v0.to_numpy()[tr], y[tr], 1)
            pred_lin[te] = np.polyval(c, g.v0.to_numpy()[te])
            mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_depth=4,
                                                l2_regularization=1.0, random_state=0)
            mdl.fit(X[tr], y[tr])
            pred_gb[te] = mdl.predict(X[te])
        lin = np.sqrt(np.mean((pred_lin - y)**2))
        gb = np.sqrt(np.mean((pred_gb - y)**2))
        print(f"  {h:>4d} s   {len(g):>7,}{held:>12.2f}{lin:>17.2f}{gb:>19.2f}{100*(held - gb)/held:>8.0f}%")
    head("what that means")
    print("  round3_accel_speed.py measured what a speed of a given accuracy is worth, reported every few seconds:")
    print("    sigma 1 m/s -> 6.0% path error,  sigma 2 -> 7.3%,  sigma 4 -> 9.8%,  holding today -> 10.3%")
    print("  a learned model is only worth building if it lands in the left half of that table.")


if __name__ == "__main__":
    main()
