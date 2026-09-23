"""Round 3 · speed from how much the car shakes — the last untried sensor route.

Everything else has failed to measure speed: a trained regressor (round 1), the map's curvature (entry 31), turn
readings (entry 39, works only on phones that feel a corner), integrating acceleration (entry 40), road-speed priors
(entry 40), and widening the filter's own speed hypotheses (entry 42 sweep).

This is different in kind. A car shakes more the faster it goes — road roughness excites the suspension, the drivetrain
turns faster, tyres roar. That energy is *noise* to every method above, which is why aliasing does not destroy it: we
do not need the shape of the signal, only how much of it there is.

Round 1 tried the IMU for speed with one model trained across drivers. This fits a model **per session, on that
session's own GNSS history**, the same way the gyro's scale is calibrated per phone (driver E's gyro reads 54% of a
real turn, so a shared model was never going to work). The fit sees only history before the blackout.

  features    over a 2 s window: how much each accelerometer and gyroscope axis wobbles about its own mean, the
              spread of the total force, the jerk, and the energy in four bands from 0.5 to 5 Hz
  target      the GNSS speed over that window
  model       ridge regression on standardised log features, fitted on up to 10 minutes of history
  measured    against the car's true speed during the blackout, and against holding the last GNSS speed

Tuning drivers only. Run from the repo root:  .venv/bin/python3 round2/round3_vibration_speed.py [--limit 120]
Output: round2/out/round3_vibration_speed_run.txt, round3_vibration_speed.parquet
"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion
from core.geo import enu
from round3_accel_speed import CHOICE, TUNE, FLOOR_M

T0 = time.time()
FS = 10.0
WIN = 20                     # 2 s of rows in a feature window
HOP = 5                      # a window every half second
HISTORY_S = 900.0            # up to fifteen minutes of history to fit on
RIDGE = 1.0

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def features(acc, gyr):
    """One row of features per window: how much the car is shaking, in several ways."""
    n = (len(acc) - WIN)//HOP + 1
    if n <= 0:
        return np.zeros((0, 19)), np.zeros(0, int)
    idx = np.arange(n)*HOP
    out = np.empty((n, 19))
    centres = idx + WIN//2
    mag = np.linalg.norm(acc, axis=1)
    for k, a in enumerate(idx):
        sl = slice(a, a + WIN)
        A, G = acc[sl], gyr[sl]
        Ac = A - A.mean(axis=0)
        Gc = G - G.mean(axis=0)
        f = [Ac[:, 0].std(), Ac[:, 1].std(), Ac[:, 2].std(),
             mag[sl].std(), np.abs(np.diff(mag[sl])).mean(),
             Gc[:, 0].std(), Gc[:, 1].std(), Gc[:, 2].std(),
             np.abs(np.diff(A, axis=0)).mean(), np.abs(np.diff(G, axis=0)).mean()]
        # where the shaking sits in frequency, 0.5 to 5 Hz, for the total force and for the gyroscope
        for series in (mag[sl] - mag[sl].mean(), np.linalg.norm(Gc, axis=1)):
            spec = np.abs(np.fft.rfft(series*np.hanning(WIN)))**2
            freq = np.fft.rfftfreq(WIN, 1/FS)
            for lo, hi in ((0.5, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 5.0)):
                band = (freq >= lo) & (freq < hi)
                f.append(float(spec[band].sum()))
        f.append(float(mag[sl].mean()))
        out[k] = f
    return out, centres


def fit_ridge(X, y):
    """Ridge on standardised log features, predicting speed. Returns a callable, or None."""
    if len(X) < 120:
        return None
    Z = np.log1p(np.maximum(X, 0.0))
    mu, sd = Z.mean(axis=0), Z.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    Zs = np.c_[(Z - mu)/sd, np.ones(len(Z))]
    A = Zs.T @ Zs + RIDGE*np.eye(Zs.shape[1])
    A[-1, -1] -= RIDGE                                   # do not shrink the intercept
    try:
        w = np.linalg.solve(A, Zs.T @ y)
    except np.linalg.LinAlgError:
        return None
    def predict(Xn):
        Zn = np.log1p(np.maximum(Xn, 0.0))
        return np.c_[(Zn - mu)/sd, np.ones(len(Zn))] @ w
    fitted = predict(X)
    return predict, float(np.corrcoef(fitted, y)[0, 1]), float(np.sqrt(np.mean((fitted - y)**2)))


def main():
    limit = arg("--limit", 120)
    head("Round 3 · can how much the car shakes tell us how fast it is going?")
    print(f"  model fitted per blackout on up to {HISTORY_S/60:.0f} min of that session's own GNSS history, "
          f"{WIN/FS:g} s windows")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    recs, preds, cache = [], [], {}
    for nb, b in enumerate(BL.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
            log(f"  {b.drive}/{b.session} ({b.driver}) — {nb}/{len(BL)}")
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        if cal is None:
            continue
        h0 = max(0, i - int(HISTORY_S*FS))
        Xh, ch = features(S.acc[h0:i], S.gyr[h0:i])
        if len(Xh) < 120:
            continue
        vh = S.v[h0:i][ch]
        ok = np.isfinite(vh) & np.isfinite(Xh).all(axis=1)
        fit = fit_ridge(Xh[ok], vh[ok])
        if fit is None:
            continue
        predict, fit_r, fit_rms = fit
        Xb, cb = features(S.acc[i:j + 1], S.gyr[i:j + 1])
        if len(Xb) == 0:
            continue
        v_pred_w = np.clip(predict(Xb), 0.0, 45.0)
        v_true = S.v[i:j + 1]
        # spread the window predictions back over every row, and zero them where the classifier says stopped
        v_pred = np.interp(np.arange(j - i + 1), cb, v_pred_w)
        stationary = stat[i:j + 1]
        v_pred = np.where(stationary, 0.0, v_pred)
        inp = engine_input.build(S, cal, i, j)
        true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], S.lat[i], S.lon[i])
        true_s = S.dist[i:j + 1] - S.dist[i]
        keep = true_s >= FLOOR_M
        def pct(speed):
            e, n, _ = deadreckoning.run(inp, stationary=stationary, speed=speed)
            p = 100*np.hypot(e - np.asarray(true_e, float), n - np.asarray(true_n, float))/np.maximum(true_s, 1e-9)
            return float(p[keep].mean())
        moving = ~stationary
        err_pred = v_pred[moving] - v_true[moving]
        err_held = inp.speed0 - v_true[moving]
        # half-and-half: the prediction is noisy, the held speed is biased; the average of the two is often better
        v_half = 0.5*v_pred + 0.5*np.where(stationary, 0.0, inp.speed0)
        recs.append(dict(driver=b.driver, band=b.band_1000, fit_r=fit_r, fit_rms=fit_rms,
                         rms_pred=float(np.sqrt(np.mean(err_pred**2))), rms_held=float(np.sqrt(np.mean(err_held**2))),
                         held_pct=pct(None), pred_pct=pct(v_pred), half_pct=pct(v_half), true_pct=pct(v_true)))
        preds.append(pd.DataFrame(dict(driver=b.driver, pred=v_pred[moving], truth=v_true[moving],
                                       held=inp.speed0)))
    P = pd.DataFrame(recs)
    if P.empty:
        print("  nothing fitted")
        return
    P.to_parquet(R2/"out/round3_vibration_speed.parquet", index=False)
    D = pd.concat(preds, ignore_index=True)

    head("1 · does the shaking track the speed at all?")
    print(f"  {len(P)} blackouts fitted")
    print(f"  fit on the history itself: correlation median {P.fit_r.median():.2f} "
          f"(p10 {P.fit_r.quantile(0.1):.2f}, p90 {P.fit_r.quantile(0.9):.2f}), RMS {P.fit_rms.median():.2f} m/s")
    print(f"  carried into the blackout: RMS {P.rms_pred.median():.2f} m/s against the held speed's "
          f"{P.rms_held.median():.2f} m/s")
    print(f"  better than holding on {100*(P.rms_pred < P.rms_held).mean():.0f}% of blackouts")
    print(f"  overall, over {len(D):,} moving rows: prediction RMS {np.sqrt(((D.pred - D.truth)**2).mean()):.2f} m/s, "
          f"held {np.sqrt(((D.held - D.truth)**2).mean()):.2f} m/s")

    head("2 · what it is worth (dead reckoning, no map, path average)")
    print(f"  {'held speed (today)':<28}{P.held_pct.median():>7.1f}%   under 10% on {100*(P.held_pct < 10).mean():3.0f}%")
    print(f"  {'shaking model':<28}{P.pred_pct.median():>7.1f}%   under 10% on {100*(P.pred_pct < 10).mean():3.0f}%")
    print(f"  {'half of each':<28}{P.half_pct.median():>7.1f}%   under 10% on {100*(P.half_pct < 10).mean():3.0f}%")
    print(f"  {'true speed (the floor)':<28}{P.true_pct.median():>7.1f}%   under 10% on {100*(P.true_pct < 10).mean():3.0f}%")
    print(f"\n  the model beats holding on {100*(P.pred_pct < P.held_pct).mean():.0f}% of blackouts, "
          f"half-and-half on {100*(P.half_pct < P.held_pct).mean():.0f}%")

    head("3 · by driving condition and by how good the fit was")
    print(f"  {'band':<8}{'n':>5}{'held':>9}{'model':>9}{'half':>9}{'true':>9}")
    for band in ("slow", "mixed", "ps_60", "fast"):
        g = P[P.band == band]
        if len(g):
            print(f"  {band:<8}{len(g):>5}{g.held_pct.median():>8.1f}%{g.pred_pct.median():>8.1f}%"
                  f"{g.half_pct.median():>8.1f}%{g.true_pct.median():>8.1f}%")
    print(f"\n  {'fit r':<10}{'n':>5}{'RMS model':>12}{'RMS held':>11}{'held path':>11}{'model path':>12}")
    for lo, hi in ((0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)):
        g = P[(P.fit_r >= lo) & (P.fit_r < hi)]
        if len(g) >= 5:
            print(f"  {lo:.2f}-{hi:.2f}{len(g):>5}{g.rms_pred.median():>11.2f}{g.rms_held.median():>11.2f}"
                  f"{g.held_pct.median():>10.1f}%{g.pred_pct.median():>11.1f}%")


if __name__ == "__main__":
    main()
