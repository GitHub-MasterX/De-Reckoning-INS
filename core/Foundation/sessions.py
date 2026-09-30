"""One session loader for every round-2 step, so all steps see the same sessions and row indices.

Row index = position within the session's aligned rows (`session` matches and `aligned_valid`), in
file order. Phone arrays are what the engine may use. Truth arrays are for scoring; the engine may
read GNSS values only from before a blackout starts (the last fix and the calibration history)."""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ["t_raw_s", "ax", "ay", "az", "gx", "gy", "gz", "stuck", "speed_best_al",
           "lat", "lon", "heading", "gnss_dropout", "session", "aligned_valid", "veh_idx"]


def selected():
    """The round-1 session selection: |sync_r| >= 0.40, not Vtb1."""
    a = pd.read_csv(ROOT/"data/test_outputs/alignment.csv")
    a = a[(a.sync_r.abs() >= 0.40) & a.sync_r.notna() & (a.drive != "Vtb1")]
    return a[["drive", "driver", "session"]].reset_index(drop=True)


@dataclass
class Session:
    drive: str
    driver: str
    session: int
    t: np.ndarray         # phone clock, s
    acc: np.ndarray       # (n, 3) accelerometer, m/s², includes gravity   — phone
    gyr: np.ndarray       # (n, 3) gyroscope, rad/s, raw                    — phone
    stuck: np.ndarray     # IMU repeating a stale value                     — phone
    v: np.ndarray         # vehicle speed, m/s                              — truth / pre-blackout GNSS
    lat: np.ndarray       # vehicle position, degrees                       — truth / pre-blackout GNSS
    lon: np.ndarray
    heading: np.ndarray   # vehicle course, degrees clockwise from north    — truth / pre-blackout GNSS
    dropout: np.ndarray   # vehicle GNSS lost lock (position frozen)
    dist: np.ndarray      # vehicle distance travelled since session start, m (speed × phone clock)


def load(drive, driver, session, min_rows=3000):
    base = pd.read_parquet(ROOT/f"data/clean/{drive}.parquet", columns=COLUMNS)
    keep = (base.session.to_numpy() == session) & base.aligned_valid.to_numpy()
    if keep.sum() < min_rows:
        return None
    d = base[keep]
    vi = d.veh_idx.to_numpy()                          # vehicle row for each phone row, lag-corrected
    t = d.t_raw_s.to_numpy(float)
    v = d.speed_best_al.to_numpy(float)/3.6
    step = np.clip(np.diff(t), 0.0, None)              # a few sessions have clock back-steps
    return Session(
        drive=drive, driver=driver, session=int(session), t=t,
        acc=d[["ax", "ay", "az"]].to_numpy(float), gyr=d[["gx", "gy", "gz"]].to_numpy(float),
        stuck=d.stuck.to_numpy(bool), v=v,
        lat=base.lat.to_numpy(float)[vi], lon=base.lon.to_numpy(float)[vi],
        heading=base.heading.to_numpy(float)[vi], dropout=base.gnss_dropout.to_numpy(bool)[vi],
        dist=np.concatenate(([0.0], np.cumsum(v[:-1]*step))))
