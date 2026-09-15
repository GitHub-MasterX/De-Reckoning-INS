"""The fixed list of blackouts every round-2 method is scored on. Rules: round2/DECISIONS.md."""
import numpy as np
import pandas as pd

START_EVERY_M = 250.0         # a start point every 250 m travelled
START_SPEED = 4.2             # m/s at the start (round-1 rule)
MIN_HISTORY_S = 300.0         # GNSS history before the start, for step-2 calibration
CHECKPOINTS = (50, 100, 200, 500, 1000)
MOVING_MIN = 1.4/3.6          # m/s — "moving" set: never slower (round-1 rule)
STOPGO_MAX_S = 600.0          # "stopgo" set: the checkpoint must be reached within 10 min

COLUMNS = (["drive", "driver", "session", "row_start", "t_start", "history_s"]
           + [f"{k}_{c}" for c in CHECKPOINTS for k in ("end", "moving", "stopgo")])


def build(S):
    """One row per start point; for each checkpoint its end row and which sets it is valid in."""
    n = len(S.t)
    good = (np.isfinite(S.acc).all(1) & np.isfinite(S.gyr).all(1) & np.isfinite(S.v)
            & np.isfinite(S.lat) & np.isfinite(S.lon) & np.isfinite(S.heading) & ~S.dropout)
    bad = np.concatenate(([0], np.cumsum(~good)))           # bad rows before each index
    slow = np.concatenate(([0], np.cumsum(S.v <= MOVING_MIN)))
    starts = np.unique(np.searchsorted(S.dist, np.arange(START_EVERY_M, S.dist[-1], START_EVERY_M)))
    starts = starts[starts < n]
    starts = starts[(S.v[starts] > START_SPEED) & (S.t[starts] - S.t[0] >= MIN_HISTORY_S)]
    rows = []
    for i in starts:
        r = dict(drive=S.drive, driver=S.driver, session=S.session, row_start=int(i),
                 t_start=round(float(S.t[i]), 3), history_s=round(float(S.t[i] - S.t[0]), 1))
        for c in CHECKPOINTS:
            j = int(np.searchsorted(S.dist, S.dist[i] + c))
            clean = j < n and bad[j + 1] == bad[i]
            r[f"end_{c}"] = j if j < n else -1
            r[f"moving_{c}"] = bool(clean and slow[j + 1] == slow[i])
            r[f"stopgo_{c}"] = bool(clean and S.t[j] - S.t[i] <= STOPGO_MAX_S)
        rows.append(r)
    return pd.DataFrame(rows, columns=COLUMNS)
