"""What the engine may see for one blackout — assembled here so later steps cannot reach ground truth.

  start   the last GNSS fix at the blackout start: position, course, speed
  calib   gyro calibration fitted on GNSS history before the start (core/calibration.py)
  phone   phone clock, accelerometer and gyroscope from the start onward

Everything else in a Session (the vehicle track after the start) belongs to the scorer."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class EngineInput:
    lat0: float           # degrees
    lon0: float           # degrees
    course0: float        # radians, clockwise from north
    speed0: float         # m/s
    axis: np.ndarray      # gyro yaw axis, unit vector
    scale: float          # true turn per unit of gyro turn
    bias: float           # rad/s
    t: np.ndarray         # phone clock, s — row 0 is the blackout start
    acc: np.ndarray       # (n, 3) m/s²
    gyr: np.ndarray       # (n, 3) rad/s

    def turn_rate(self):
        """Calibrated turn rate, rad/s, clockwise positive (the same sense as the course)."""
        return self.scale*(self.gyr @ self.axis) - self.bias


def build(S, calib, i, j_last):
    """Engine input for a blackout starting at row i, with phone data up to row j_last."""
    k = slice(i, j_last + 1)
    return EngineInput(lat0=float(S.lat[i]), lon0=float(S.lon[i]), course0=float(np.radians(S.heading[i])),
                       speed0=float(S.v[i]), axis=calib.axis.copy(), scale=float(calib.scale),
                       bias=float(calib.bias), t=S.t[k].copy(), acc=S.acc[k].copy(), gyr=S.gyr[k].copy())
