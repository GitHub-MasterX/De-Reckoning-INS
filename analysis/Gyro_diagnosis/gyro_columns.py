"""Step-2 diagnosis — raw gyro columns per session: a flat, duplicated or stuck axis would explain lost turning.
Output: round2/out/gyro_columns_run.txt"""
import warnings; warnings.filterwarnings("ignore")
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
sys.path.insert(0, str(ROOT))
from core import sessions

rows = []
for _, r in sessions.selected().iterrows():
    S = sessions.load(r.drive, r.driver, int(r.session))
    if S is None:
        continue
    m = S.v > 5
    g = S.gyr[m]
    cc = np.corrcoef(g.T)
    rows.append(dict(driver=r.driver, drive=r.drive, ses=int(r.session),
                     sd_x=np.degrees(g[:, 0].std()), sd_y=np.degrees(g[:, 1].std()), sd_z=np.degrees(g[:, 2].std()),
                     r_xy=cc[0, 1], r_xz=cc[0, 2], r_yz=cc[1, 2],
                     repeat_x=(np.diff(S.gyr[:, 0]) == 0).mean(), repeat_y=(np.diff(S.gyr[:, 1]) == 0).mean(),
                     repeat_z=(np.diff(S.gyr[:, 2]) == 0).mean(), acc_repeat=(np.diff(S.acc[:, 0]) == 0).mean(),
                     g_norm=np.linalg.norm(S.acc[m], axis=1).mean()))
pd.set_option("display.width", 220)
print("gyro columns on moving samples: std (deg/s), axis correlations, share of samples identical to the previous one")
print(pd.DataFrame(rows).round(3).to_string(index=False))
