"""Evaluation-only context of a blackout, computed from ground truth.

It decides which group a result is reported in and helps explain results. It is never an engine input.
  band        driving condition from the average speed over the blackout (round2/DECISIONS.md)
  real turns  turns and bends of at least 15° in the vehicle's GPS course — the landmarks a gyro can use"""
import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d

BANDS = ((0, 40, "slow"), (40, 50, "mixed"), (50, 70, "ps_60"), (70, np.inf, "fast"))   # km/h, [lo, hi)
TURN_DEG = 15.0
TURN_WINDOW_S = 15.0
FS = 10.0


def band(avg_kmh):
    """Name of the driving-condition group an average speed (km/h) falls in, or None."""
    for lo, hi, name in BANDS:
        if lo <= avg_kmh < hi:
            return name
    return None


def real_turns(S):
    """Apex rows of every turn or bend of at least 15° in the vehicle GPS course: net heading change over a
    centred 15 s window, one apex per turn (the audit's detector, round2/analysis/snap_recheck.py)."""
    w = int(TURN_WINDOW_S*FS)
    half = w//2
    rate = np.gradient(np.unwrap(np.radians(S.heading)))*FS
    rate[S.v < 2] = 0.0                                   # course is meaningless when (nearly) stopped
    h = np.cumsum(rate)/FS
    net = np.zeros(len(h))
    net[half:-half] = h[w:] - h[:-w]
    a = np.abs(net)
    idx = np.flatnonzero((a >= np.radians(TURN_DEG)) & (a == maximum_filter1d(a, size=w))
                         & (uniform_filter1d(S.v, size=w) > 2))
    return np.array([i for k, i in enumerate(idx) if k == 0 or i - idx[k-1] > half], int)
