"""Stationary detection for the engine — the round-1 motion classifier on phone IMU windows.

Feature contract: idr/features.py (26 features over 20-sample windows, hop 5). features_batch reproduces
extract_features for many windows at once (step 3 checks the two agree). Each driver is scored by the model
trained without that driver (`{driver}_holdout` in models/motion_models.pkl).

Gyro input: the raw phone gyro. The contract says "bias-removed" because round 1 removed the bias using stops
found in the car's true speed, which the engine may not use; step 3 measures what dropping that costs."""
import sys
from pathlib import Path
import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from idr.features import FS, WINDOW_SAMPLES, HOP_SAMPLES, extract_features   # noqa: E402

_BANDS = ((0.5, 1.5), (1.5, 3.0), (3.0, 5.0))
_MODELS = None


def models():
    global _MODELS
    if _MODELS is None:
        _MODELS = joblib.load(ROOT/"models/motion_models.pkl")
    return _MODELS


def window_starts(n):
    return np.arange(0, n - WINDOW_SAMPLES, HOP_SAMPLES)


def features_batch(acc, gyr, starts):
    """(len(starts), 26) features — extract_features applied to every window [s, s + 20)."""
    idx = np.asarray(starts)[:, None] + np.arange(WINDOW_SAMPLES)[None, :]
    a = np.asarray(acc, np.float64)[idx]
    g = np.asarray(gyr, np.float64)[idx]
    am = np.linalg.norm(a, axis=2)
    gm = np.linalg.norm(g, axis=2)
    f = [am.mean(1), am.std(1), am.min(1), am.max(1), np.abs(np.diff(am, axis=1)).mean(1),
         gm.mean(1), gm.std(1), gm.max(1)]
    for c in range(3):
        f += [a[:, :, c].std(1), np.abs(np.diff(a[:, :, c], axis=1)).mean(1), g[:, :, c].std(1)]
    freqs = np.fft.rfftfreq(WINDOW_SAMPLES, 1/FS)
    for c in range(3):
        power = np.abs(np.fft.rfft(a[:, :, c] - a[:, :, c].mean(1, keepdims=True), axis=1))**2
        for lo, hi in _BANDS:
            f.append(np.log(power[:, (freqs >= lo) & (freqs < hi)].sum(1) + 1e-9))
    return np.stack(f, axis=1).astype(np.float32)


def contract_gap(acc, gyr, starts):
    """Largest absolute difference between features_batch and the contract function on the given windows."""
    ref = np.array([extract_features(acc[s:s+WINDOW_SAMPLES], gyr[s:s+WINDOW_SAMPLES]) for s in starts])
    return float(np.nanmax(np.abs(features_batch(acc, gyr, starts) - ref)))


def predict_stationary(acc, gyr, driver):
    """Window starts and a stationary flag per window, from the model that never saw this driver."""
    starts = window_starts(len(acc))
    return starts, models()[f"{driver}_holdout"].predict(features_batch(acc, gyr, starts)) == 0


def stationary_rows(S, driver):
    """A stationary flag per row: the latest complete window ending at or before the row (causal)."""
    starts, stat = predict_stationary(S.acc, S.gyr, driver)
    ends = starts + WINDOW_SAMPLES - 1
    k = np.searchsorted(ends, np.arange(len(S.t)), side="right") - 1
    rows = np.zeros(len(S.t), bool)
    rows[k >= 0] = stat[k[k >= 0]]
    return rows, starts, stat
