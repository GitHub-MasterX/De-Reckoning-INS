"""Gyro calibration from GNSS history only — what a phone can do while GNSS still works.

IO-VNBD's phone app logs the gyroscope under a different axis convention from the accelerometer, so
the yaw axis cannot simply be taken from gravity. It is fitted instead, against the GNSS course
(the vehicle's direction of travel), using only rows before the blackout.

Turn-rate model:  turn = scale × (gyro · axis) − bias      (rad/s, clockwise positive like the course)

Two fits:
  at()          axis from the 10 Hz course rate; scale fixed at 1; bias from a median. The 10 Hz rate is
                jittery, which tilts the axis, and it cannot see scale.
  at_windows()  axis, scale and bias from turning accumulated over 10 s windows — jitter averages out.
                Needed because the phones under-report turns by a constant factor (driver E's by about half)."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

FS = 10.0
FIT_MIN_SPEED = 5.0          # m/s — course is reliable above this
HOLD_BELOW = 1.0             # m/s — course is held, not trusted, below this
STOPPED_SPEED = 0.3          # m/s — true turn rate is zero
STRAIGHT_RATE = 0.02         # rad/s — "straight" for bias samples
BIAS_WINDOW_S = 300.0
MIN_FIT_S = 30.0             # the rate fit needs at least 30 s of moving samples
WINDOW_ROWS = 100            # 10 s windows for the window fit
TURN_WINDOW_DEG = 20.0       # a window "contains a turn" above this true change of course
MIN_TURN_WINDOWS = 3         # the window fit needs at least this many turning windows


def course(S):
    """Vehicle course (radians, unwrapped, held while nearly stopped) and its rate (rad/s, clockwise +).
    Used on history rows for calibration, and on blackout rows only for scoring."""
    hd = pd.Series(np.where(S.v >= HOLD_BELOW, S.heading, np.nan)).ffill().bfill().to_numpy()
    psi = np.unwrap(np.radians(hd))
    return psi, np.gradient(psi)*FS


@dataclass(frozen=True)
class Calibration:
    axis: np.ndarray      # (3,) unit vector in the gyro frame
    scale: float          # true turn per unit of gyro turn
    bias: float           # rad/s, in turn-rate units
    r_fit: float          # correlation of the fit on its own data
    fit_s: float          # seconds of data behind the axis
    turn_windows: int     # turning 10 s windows behind the scale (0 for the rate fit)
    method: str


def _corr(c, xtx, xty, yy, sx, sy, n):
    s_h = c @ sx
    cov, var_h, var_y = c @ xty - s_h*sy/n, c @ xtx @ c - s_h**2/n, yy - sy**2/n
    return float(cov/np.sqrt(var_h*var_y)) if var_h > 0 and var_y > 0 else np.nan


class Calibrator:
    """Prefix sums over one session, so a fit on any history costs O(1)."""

    def __init__(self, S):
        self.S = S
        self.psi, self.rate = course(S)
        n = len(S.t)
        ok = np.isfinite(S.gyr).all(1)
        gyr = np.where(ok[:, None], S.gyr, 0.0)
        self.bias_ok = ok & ((S.v < STOPPED_SPEED)
                             | ((S.v > FIT_MIN_SPEED) & (np.abs(self.rate) < STRAIGHT_RATE)))
        # 10 Hz rate fit: course rate against [gyro x, y, z, 1] on moving samples
        fit = ok & (S.v > FIT_MIN_SPEED)
        X = np.c_[gyr, np.ones(n)]*fit[:, None]
        y = np.where(fit, self.rate, 0.0)
        self.Pxx = np.concatenate((np.zeros((1, 4, 4)), np.cumsum(X[:, :, None]*X[:, None, :], axis=0)))
        self.Pxy = np.concatenate((np.zeros((1, 4)), np.cumsum(X*y[:, None], axis=0)))
        self.Pyy = np.concatenate(([0.0], np.cumsum(y*y)))
        self.Pn = np.concatenate(([0], np.cumsum(fit)))
        # 10 s window fit: change of course against [accumulated gyro x, y, z, duration]
        dt = np.r_[np.clip(np.diff(S.t), 0.0, None), 0.0]
        cg = np.vstack((np.zeros(3), np.cumsum(gyr*dt[:, None], axis=0)))
        ct = np.r_[0.0, np.cumsum(dt)]
        bad = np.r_[0, np.cumsum(~fit)]
        a = np.arange(0, n - WINDOW_ROWS, WINDOW_ROWS)
        b = a + WINDOW_ROWS
        keep = bad[b] == bad[a]                         # moving above 5 m/s for the whole window
        a, b = a[keep], b[keep]
        Xw = np.c_[cg[b] - cg[a], ct[b] - ct[a]]
        yw = self.psi[b] - self.psi[a]
        self.win_end = b
        self.Wxx = np.concatenate((np.zeros((1, 4, 4)), np.cumsum(Xw[:, :, None]*Xw[:, None, :], axis=0)))
        self.Wxy = np.concatenate((np.zeros((1, 4)), np.cumsum(Xw*yw[:, None], axis=0)))
        self.Wx = np.concatenate((np.zeros((1, 4)), np.cumsum(Xw, axis=0)))
        self.Wy = np.concatenate(([0.0], np.cumsum(yw)))
        self.Wyy = np.concatenate(([0.0], np.cumsum(yw*yw)))
        self.Wturn = np.concatenate(([0], np.cumsum(np.abs(yw) >= np.radians(TURN_WINDOW_DEG))))

    def _recent_bias(self, end, axis, scale, bias_window_s):
        b0 = max(0, end - int(bias_window_s*FS))
        m = np.flatnonzero(self.bias_ok[b0:end]) + b0
        if len(m) < 50:
            return None
        target = np.where(self.S.v[m] < STOPPED_SPEED, 0.0, self.rate[m])
        return float(np.median(scale*(self.S.gyr[m] @ axis) - target))

    def at(self, i, axis_window_s=None, bias_window_s=BIAS_WINDOW_S):
        """Rate fit from rows before blackout start i (axis_window_s=None: the whole history)."""
        end = max(i - 1, 0)                   # the course rate at row i-1 already reaches row i, the last fix
        a = 0 if axis_window_s is None else max(0, end - int(axis_window_s*FS))
        n = self.Pn[end] - self.Pn[a]
        if n < MIN_FIT_S*FS:
            return None
        xtx, xty, yy = self.Pxx[end] - self.Pxx[a], self.Pxy[end] - self.Pxy[a], self.Pyy[end] - self.Pyy[a]
        c = np.linalg.lstsq(xtx, xty, rcond=None)[0]
        norm = float(np.linalg.norm(c[:3]))
        if not np.isfinite(norm) or norm == 0.0:
            return None
        r = _corr(c, xtx, xty, yy, xtx[3], xty[3], n)
        axis = c[:3]/norm
        bias = self._recent_bias(end, axis, 1.0, bias_window_s)
        if bias is None:
            return None
        return Calibration(axis=axis, scale=1.0, bias=bias, r_fit=r, fit_s=n/FS, turn_windows=0, method="rate")

    def at_windows(self, i, recent_bias_s=None):
        """Window fit on the 10 s windows that end by row i (the last fix). Bias from the fit's duration term,
        or, with recent_bias_s, from a median over that many seconds before the start."""
        m = int(np.searchsorted(self.win_end, i, side="right"))
        if m < 5 or self.Wturn[m] < MIN_TURN_WINDOWS:
            return None
        xtx, xty, sx, sy, yy = self.Wxx[m], self.Wxy[m], self.Wx[m], self.Wy[m], self.Wyy[m]
        c = np.linalg.lstsq(xtx, xty, rcond=None)[0]
        scale = float(np.linalg.norm(c[:3]))
        if not np.isfinite(scale) or scale == 0.0:
            return None
        axis = c[:3]/scale
        bias = -float(c[3])
        if recent_bias_s is not None:
            bias = self._recent_bias(max(i - 1, 0), axis, scale, recent_bias_s)
            if bias is None:
                return None
        return Calibration(axis=axis, scale=scale, bias=bias, r_fit=_corr(c, xtx, xty, yy, sx, sy, m),
                           fit_s=m*WINDOW_ROWS/FS, turn_windows=int(self.Wturn[m]),
                           method="window" if recent_bias_s is None else "window_recent_bias")


def engine_calibration(C, i, variant):
    """The calibration step 2 chose (round2/out/calibration_choice.txt), with step 2's fallback to the rate fit."""
    rate = C.at(i, axis_window_s=None, bias_window_s=1e9)
    if variant == "rate":
        return rate
    own = C.at_windows(i) if variant == "window" else C.at_windows(i, recent_bias_s=BIAS_WINDOW_S)
    return own if own is not None else rate
