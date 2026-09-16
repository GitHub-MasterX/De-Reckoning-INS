"""Phone · whole-session reference runs, to test the app's live engine end to end on recorded data.

The live engine (LiveEngineCore.kt) is fed a session row by row as the phone would feed it — 10 Hz sensor rows and GNSS
fixes — and a blackout is switched on at a chosen row. Python's answer for the same blackout is written here, computed
with the stop classifier the phone uses (`deploy_all`), so that when fixes arrive on every row the phone engine must
reproduce Python's calibration and dead reckoning exactly, and with 1 Hz fixes (a real phone) it must stay close.

Output (git-ignored): data/osm/phone/session_fixture.bin, little-endian:
  "SFX1", n i32; per case: id, driver, i i32 (blackout start row), j i32 (row 1 km later), then rows 0..j:
  t f64, acc f64 x3, gyr f64 x3, lat f64, lon f64, heading f64, v f64;
  then Python: method i8 (1 rate, 2 window), axis f64 x3, scale f64, bias f64,
  dead reckoning east north dist f64 at j, truth east north dist f64 at j, filter seed A east north f64, seed B east north f64
Run from the repo root:  .venv/bin/python3 round2/phone/export_session_fixture.py"""
import warnings; warnings.filterwarnings("ignore")
import json, struct, sys
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parents[1]
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import calibration, deadreckoning, engine_input, motion, particle, roadnet, scoring, sessions

OUT = ROOT/"data/osm/phone/session_fixture.bin"
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
METHOD = {"rate": 1, "window": 2}
N_CASES = 8
MAX_ROW = 17_000             # the phone keeps 30 min (18,000 rows) of history; stay inside it so both see the same

BL = pd.read_parquet(R2/"out/blackouts.parquet")
BL = BL[BL.moving_1000 & (BL.row_start >= 6000) & (BL.row_start <= MAX_ROW)]
pick = pd.concat([g.sample(min(2, len(g)), random_state=2) for _, g in BL.groupby("driver")]).head(N_CASES)
net = roadnet.RoadNetwork()
model = motion.models()["deploy_all"]


def put(f, a, dtype="<f8"):
    f.write(np.ascontiguousarray(a).astype(dtype).tobytes())


with open(OUT, "wb") as f:
    f.write(b"SFX1")
    f.write(struct.pack("<i", len(pick)))
    for b in pick.itertuples(index=False):
        S = sessions.load(b.drive, b.driver, int(b.session))
        i = int(b.row_start) - int(b.row_start) % 10          # on a 1 Hz fix row, so both feeds start at the same row
        j = int(np.searchsorted(S.dist, S.dist[i] + 1000.0))
        starts = motion.window_starts(len(S.t))
        stat_w = model.predict(motion.features_batch(S.acc, S.gyr, starts)) == 0
        ends = starts + motion.WINDOW_SAMPLES - 1
        k = np.searchsorted(ends, np.arange(len(S.t)), side="right") - 1
        stat = np.zeros(len(S.t), bool)
        stat[k >= 0] = stat_w[k[k >= 0]]
        cal = calibration.engine_calibration(calibration.Calibrator(S), i, CHOICE)
        inp = engine_input.build(S, cal, i, j)
        dr = deadreckoning.run(inp, stationary=stat[i:j + 1])
        runs = [particle.run(inp, net, stat[i:j + 1], [j - i], params=PARAMS, rng=np.random.default_rng(s)) for s in (i, i + 7919)]
        te, tn, td = scoring.truth_at(S, i, j)
        raw = f"{b.drive}/{b.session}/{i}".encode()
        f.write(struct.pack("<i", len(raw))); f.write(raw)
        f.write(struct.pack("<i", 1)); f.write(b.driver.encode())
        f.write(struct.pack("<ii", i, j))
        r = slice(0, j + 1)
        rows = np.c_[S.t[r], S.acc[r], S.gyr[r], S.lat[r], S.lon[r], S.heading[r], S.v[r]]
        put(f, rows)
        f.write(struct.pack("<b", METHOD[cal.method]))
        put(f, cal.axis); f.write(struct.pack("<dd", cal.scale, cal.bias))
        f.write(struct.pack("<3d", dr[0][-1], dr[1][-1], dr[2][-1]))
        f.write(struct.pack("<3d", te, tn, td))
        f.write(struct.pack("<4d", runs[0]["east"][0], runs[0]["north"][0], runs[1]["east"][0], runs[1]["north"][0]))
        errs = [100*np.hypot(run["east"][0] - te, run["north"][0] - tn)/td for run in runs]
        print(f"  {b.driver} {b.drive}/{b.session} start row {i}, 1 km at row {j}: {cal.method} x{cal.scale:.3f} · "
              f"no map {100*np.hypot(dr[0][-1] - te, dr[1][-1] - tn)/td:.1f}% · filter {errs[0]:.1f}% / {errs[1]:.1f}%")
print(f"-> {OUT.relative_to(ROOT)} ({OUT.stat().st_size/1e6:.1f} MB)")
