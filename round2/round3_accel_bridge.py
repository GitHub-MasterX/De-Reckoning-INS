"""Round 3 · can 10 Hz forward acceleration bridge the gaps between turn readings?

A speed *reading* from the turn trick needs a corner, so it arrives every 20-40 s at best. But the accelerometer has
something to say at every one of its ten samples a second: how much the speed has *changed*. If that integrates
cleanly for twenty or thirty seconds, then sparse readings plus continuous integration is a speed sensor that reports
all the time — which is what round3_accel_speed.py's theory table says is needed (sigma 2 m/s, every few seconds).

So this measures the only number that decides it: how wrong is the integrated speed change after 5, 10, 20, 30 s?

    a_forward          the accelerometer's component along the vehicle's forward axis, gravity removed
    integrated         its integral over a window, which should equal the car's change of speed
    measured against   the change the vehicle's own GNSS recorded over the same window

Two versions of forward acceleration are tried, because which one is available matters:
    fitted axes    forward = up x right, with right fitted on the GNSS history (as the turn readings use)
    bias removed   the same, minus its own mean over the pre-blackout history (a standing offset from mount pitch
                   and road slope, which is what usually ruins integration)

Tuning drivers only. Run from the repo root:  .venv/bin/python3 round2/round3_accel_bridge.py [--limit 150]
Output: round2/out/round3_accel_bridge_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion
from round3_accel_speed import fit_axes, CHOICE, HISTORY_S, FS, TUNE

T0 = time.time()
WINDOWS_S = (5.0, 10.0, 20.0, 30.0)

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def forward_series(acc, axes):
    """The accelerometer's forward component, m/s², from the fitted axes (forward = up x right)."""
    horiz = acc - np.outer(acc @ axes["up"], axes["up"])
    q1, q2 = horiz @ axes["e1"], horiz @ axes["e2"]
    right = axes["right"]
    fwd = np.array([-right[1], right[0]])              # in the horizontal plane, forward is right turned 90 degrees
    return (q1*fwd[0] + q2*fwd[1])/axes["scale"]


def main():
    limit = arg("--limit", 150)
    head("Round 3 · how far can integrated forward acceleration carry the speed?")
    BL = pd.read_parquet(R2/"out/blackouts.parquet").sort_values(["drive", "session", "row_start"])
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()].reset_index(drop=True)
    BL = BL.iloc[np.linspace(0, len(BL) - 1, min(limit, len(BL))).astype(int)]
    rows, cache = [], {}
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
        turn_hist = cal.scale*(S.gyr[h0:i] @ cal.axis) - cal.bias
        axes = fit_axes(S.acc[h0:i], turn_hist, S.v[h0:i], S.t[h0:i], stat[h0:i])
        if axes is None or axes["r"] < 0.6:
            continue
        # the standing offset, measured on the history where the true change of speed is known
        a_hist = forward_series(S.acc[h0:i], axes)
        dv_hist = np.gradient(S.v[h0:i], S.t[h0:i])
        bias = float(np.median(a_hist - dv_hist))
        inp = engine_input.build(S, cal, i, j)
        a_fwd = forward_series(inp.acc, axes)
        t = inp.t - inp.t[0]
        v_true = S.v[i:j + 1]
        for w_s in WINDOWS_S:
            w = int(w_s*FS)
            for k in range(0, len(t) - w, w):
                dv_true = float(v_true[k + w] - v_true[k])
                for label, series in (("raw", a_fwd), ("bias removed", a_fwd - bias)):
                    dv = float(np.trapezoid(series[k:k + w + 1], t[k:k + w + 1]))
                    rows.append(dict(window=w_s, kind=label, err=dv - dv_true, truth=dv_true,
                                     band=b.band_1000, driver=b.driver))
    D = pd.DataFrame(rows)
    if D.empty:
        print("  nothing to measure")
        return
    head("error in the integrated change of speed, against what the car actually did")
    print(f"  {'window':<10}{'n':>7}{'raw RMS':>12}{'bias removed':>15}{'held speed':>13}")
    for w_s in WINDOWS_S:
        g = D[D.window == w_s]
        raw = g[g.kind == "raw"].err
        deb = g[g.kind == "bias removed"].err
        held = g[g.kind == "raw"].truth          # holding the speed means assuming no change at all
        print(f"  {w_s:>5.0f} s   {len(raw):>7,}{np.sqrt((raw**2).mean()):>11.2f}m/s"
              f"{np.sqrt((deb**2).mean()):>13.2f}m/s{np.sqrt((held**2).mean()):>11.2f}m/s")
    print("\n  'held speed' is the error you get by assuming the speed did not change over the window —")
    print("  the integration has to beat that to be worth anything.")
    head("what it would mean for a bridge between turn readings")
    deb30 = D[(D.window == 30.0) & (D.kind == "bias removed")].err
    deb20 = D[(D.window == 20.0) & (D.kind == "bias removed")].err
    print(f"  a reading every 20 s, integration between: worst error just before the next reading "
          f"~{np.sqrt((deb20**2).mean()):.2f} m/s of drift on top of the reading's own ~4 m/s")
    print(f"  the same at 30 s: ~{np.sqrt((deb30**2).mean()):.2f} m/s")
    print("  (round3_accel_speed.py's table: sigma 2 m/s every 5 s gives 7.3%, sigma 4 m/s every 20 s gives 15.9%)")


if __name__ == "__main__":
    main()
