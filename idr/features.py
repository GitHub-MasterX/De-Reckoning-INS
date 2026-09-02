"""
THE FEATURE CONTRACT.

The saved model expects exactly these 26 numbers, in exactly this order, computed from
exactly this window. Any other implementation — Python, Kotlin, C++ — must reproduce this
function bit-for-bit or the model receives values in the wrong slots and fails silently.

Input : accelerometer and gyroscope, 3 axes each, sampled at 10 Hz.
        Accelerometer in m/s^2 INCLUDING gravity. Gyroscope in rad/s, bias-removed.
Window: 2.0 s (20 samples), stepped 0.5 s (5 samples).
"""
import numpy as np

FS = 10.0                 # Hz — the model was trained at this rate; resample to it
WINDOW_SAMPLES = 20       # 2.0 s
HOP_SAMPLES = 5           # 0.5 s

FEATURE_NAMES = (
    ["acc_mag_mean", "acc_mag_std", "acc_mag_min", "acc_mag_max", "acc_mag_absdiff",
     "gyr_mag_mean", "gyr_mag_std", "gyr_mag_max"]
    + [f"{s}_{ax}" for ax in "xyz" for s in ("acc_std", "acc_absdiff", "gyr_std")]
    + [f"band_{ax}_{b}" for ax in "xyz" for b in ("0.5-1.5Hz", "1.5-3Hz", "3-5Hz")]
)
assert len(FEATURE_NAMES) == 26

_BANDS = ((0.5, 1.5), (1.5, 3.0), (3.0, 5.0))

def extract_features(acc, gyr):
    """One window -> 26 features.  acc, gyr: (WINDOW_SAMPLES, 3) arrays."""
    acc = np.asarray(acc, dtype=np.float64)
    gyr = np.asarray(gyr, dtype=np.float64)
    if acc.shape != (WINDOW_SAMPLES, 3) or gyr.shape != (WINDOW_SAMPLES, 3):
        raise ValueError(f"expected ({WINDOW_SAMPLES}, 3) arrays, got {acc.shape} and {gyr.shape}")
    am = np.linalg.norm(acc, axis=1)
    gm = np.linalg.norm(gyr, axis=1)
    f = [am.mean(), am.std(), am.min(), am.max(), np.abs(np.diff(am)).mean(),
         gm.mean(), gm.std(), gm.max()]
    for c in range(3):
        f += [acc[:, c].std(), np.abs(np.diff(acc[:, c])).mean(), gyr[:, c].std()]
    freqs = np.fft.rfftfreq(WINDOW_SAMPLES, 1/FS)
    for c in range(3):
        power = np.abs(np.fft.rfft(acc[:, c] - acc[:, c].mean()))**2
        for lo, hi in _BANDS:
            f.append(np.log(power[(freqs >= lo) & (freqs < hi)].sum() + 1e-9))
    return np.asarray(f, dtype=np.float32)

def window_stream(acc, gyr):
    """A full recording -> (n_windows, 26). acc, gyr: (n, 3) at 10 Hz."""
    acc, gyr = np.asarray(acc), np.asarray(gyr)
    starts = range(0, len(acc) - WINDOW_SAMPLES, HOP_SAMPLES)
    return np.array([extract_features(acc[i:i+WINDOW_SAMPLES], gyr[i:i+WINDOW_SAMPLES])
                     for i in starts], dtype=np.float32)
