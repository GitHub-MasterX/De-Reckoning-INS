"""Round 3 · can a model learn speed from the IMU stream itself, given all the data there is?

The earlier ceiling test (round3_speed_nn.py) asked whether the *future* speed can be predicted from context at the
moment GNSS dies, and used only the few hundred blackout starts. This asks the rider's real question: can a model look
at the accelerometer and gyroscope and say how fast the car is going — trained not on a few hundred samples but on
every second of every session, which is what a network would actually be given.

  training data   a window every second of every tuning session, labelled with the GNSS speed at that moment
  features        the shaking: per-axis spread, total force spread, jerk, and the energy in four bands to 5 Hz,
                  over 2 s and 6 s, plus how much the car is turning
  model           gradient boosting, cross-validated by session so it is never scored on a session it trained on
  benchmark       2 m/s RMS is what the payoff table says is needed to matter; the speed's own spread is what a model
                  that has learned nothing would score
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
from core import sessions
from round3_vibration_speed import features, WIN, HOP
from round3_accel_speed import TUNE

T0 = time.time()
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*96}\n{t}\n{'='*96}")


def main():
    head("Round 3 · learning speed from the IMU, on every second of every session")
    sel = sessions.selected()
    sel = sel[sel.driver.isin(TUNE)]
    X, y, g = [], [], []
    for r in sel.itertuples(index=False):
        S = sessions.load(r.drive, r.driver, int(r.session))
        if S is None:
            continue
        step = 10                                   # a training window every second
        F, c = features(S.acc, S.gyr)
        if len(F) == 0:
            continue
        keep = np.arange(0, len(F), max(1, step//HOP))
        F, c = F[keep], c[keep]
        v = S.v[c]
        ok = np.isfinite(v) & np.isfinite(F).all(axis=1)
        X.append(F[ok]); y.append(v[ok]); g += [f"{r.drive}_{r.session}"]*int(ok.sum())
        log(f"  {r.drive}/{r.session} ({r.driver}) — {int(ok.sum()):,} windows")
    X = np.vstack(X); y = np.concatenate(y); g = np.array(g)
    head("result")
    print(f"  {len(y):,} labelled windows from {len(np.unique(g))} sessions, speed spread {y.std():.2f} m/s")
    pred = np.empty_like(y)
    for tr, te in GroupKFold(n_splits=min(5, len(np.unique(g)))).split(X, y, g):
        m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_depth=6,
                                          l2_regularization=1.0, random_state=0)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    rms = float(np.sqrt(np.mean((pred - y)**2)))
    naive = float(np.sqrt(np.mean((y.mean() - y)**2)))
    print(f"  model, scored on sessions it never saw : RMS {rms:5.2f} m/s")
    print(f"  a model that learned nothing (the mean): RMS {naive:5.2f} m/s")
    print(f"  correlation with the truth: {np.corrcoef(pred, y)[0, 1]:.2f}")
    print(f"\n  needed to beat holding the last GNSS speed, per the payoff table: about 2 m/s")
    # and how it does within a session it HAS seen, which is the optimistic case
    m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_depth=6, random_state=0).fit(X, y)
    print(f"  same model scored on its own training data (optimistic, not a result): "
          f"RMS {float(np.sqrt(np.mean((m.predict(X) - y)**2))):5.2f} m/s")


if __name__ == "__main__":
    main()
