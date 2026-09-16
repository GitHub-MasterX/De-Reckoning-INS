"""Phone · reference runs of the Python engine, so the app's Kotlin port is tested against round 2 itself.

  calibration   20 blackouts: the GNSS history from the session start and the calibration step 2's choice makes of it
  engine        150 moving 1 km blackouts across all four drivers: the engine input, the stop flags, Python's
                map-free dead reckoning on every row, and the particle filter's estimate at each checkpoint with two
                seeds (the gap between the seeds is the noise the port has to fall inside)

The port uses its own random numbers, so its particle filter can only agree statistically; calibration and dead
reckoning are deterministic and must agree to rounding.

Outputs (git-ignored): data/osm/phone/calibration_fixture.bin, data/osm/phone/engine_fixture.bin
File layouts are written next to each writer below; everything is little-endian.
Run from the repo root:  .venv/bin/python3 round2/phone/export_engine_fixture.py"""
import warnings; warnings.filterwarnings("ignore")
import json, struct, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parents[1]
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import blackouts, calibration, deadreckoning, engine_input, motion, particle, roadnet, scoring, sessions

T0 = time.time()
OUT = ROOT/"data/osm/phone"
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
PER_DRIVER = {"A": 40, "B": 40, "D": 30, "E": 40}
N_CALIBRATION = 20
CAL_MAX_ROW = 18_000          # calibration cases start within 30 min of the session start, to keep the file small
SEED_B = 7919
METHOD = {None: 0, "rate": 1, "window": 2, "window_recent_bias": 3}
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)


def put_str(f, s):
    raw = s.encode()
    f.write(struct.pack("<i", len(raw)))
    f.write(raw)


def put(f, a, dtype):
    f.write(np.ascontiguousarray(a).astype(dtype).tobytes())


BL = pd.read_parquet(R2/"out/blackouts.parquet")
BL = BL[BL.moving_1000]
rng = np.random.default_rng(0)
pick = pd.concat([g.sample(min(PER_DRIVER[d], len(g)), random_state=0) for d, g in BL.groupby("driver")])
pick = pick.sort_values(["drive", "session", "row_start"]).reset_index(drop=True)
cal_pick = BL[BL.row_start <= CAL_MAX_ROW].sample(N_CALIBRATION, random_state=1).sort_values(["drive", "session", "row_start"])
net = roadnet.RoadNetwork()
log(f"{len(pick)} engine blackouts, {len(cal_pick)} calibration cases, network {len(net.seg_u):,} segments")

# ───────────── calibration: "CFX1", n i32; per case: id, rows i32 (history rows 0..i inclusive), t f64[rows],
# gyr f64[rows x 3], v f64[rows], heading f64[rows], method i8 (0 none, 1 rate, 2 window), axis f64[3], scale f64, bias f64
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT/"calibration_fixture.bin", "wb") as f:
    f.write(b"CFX1")
    f.write(struct.pack("<i", len(cal_pick)))
    for b in cal_pick.itertuples(index=False):
        S = sessions.load(b.drive, b.driver, int(b.session))
        i = int(b.row_start)
        cal = calibration.engine_calibration(calibration.Calibrator(S), i, CHOICE)
        put_str(f, f"{b.drive}/{b.session}/{i}")
        f.write(struct.pack("<i", i + 1))
        put(f, S.t[:i + 1], "<f8"); put(f, S.gyr[:i + 1], "<f8"); put(f, S.v[:i + 1], "<f8"); put(f, S.heading[:i + 1], "<f8")
        f.write(struct.pack("<b", METHOD[cal.method if cal is not None else None]))
        put(f, cal.axis if cal is not None else np.zeros(3), "<f8")
        f.write(struct.pack("<dd", cal.scale if cal is not None else 0.0, cal.bias if cal is not None else 0.0))
log(f"calibration fixture: {(OUT/'calibration_fixture.bin').stat().st_size/1e6:.1f} MB")

# ───────────── engine: "EFX1", n i32; per blackout: id, driver, lat0 lon0 course0 speed0 f64, axis f64[3], scale f64,
# bias f64, rows i32, t f64[rows], acc f64[rows x 3], gyr f64[rows x 3], stationary i8[rows], dr_east/north/dist f64[rows],
# n_checks i32, per checkpoint: metres i32, row i32 (from the start), truth east north dist f64, seed A east north dist f64,
# seed B east north dist f64
recs, cache = [], {}
with open(OUT/"engine_fixture.bin", "wb") as f:
    f.write(b"EFX1")
    f.write(struct.pack("<i", len(pick)))
    for nb, b in enumerate(pick.itertuples(index=False)):
        key = (b.drive, b.session)
        if key not in cache:
            S = sessions.load(b.drive, b.driver, int(b.session))
            cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
        S, C, stat = cache[key]
        i, j = int(b.row_start), int(b.end_1000)
        cal = calibration.engine_calibration(C, i, CHOICE)
        inp = engine_input.build(S, cal, i, j)
        st = stat[i:j + 1]
        dr = deadreckoning.run(inp, stationary=st)
        checks = [(c, int(getattr(b, f"end_{c}")) - i) for c in blackouts.CHECKPOINTS]
        runs = [particle.run(inp, net, st, [r for _, r in checks], params=PARAMS, rng=np.random.default_rng(seed))
                for seed in (i, i + SEED_B)]
        put_str(f, f"{b.drive}/{b.session}/{i}"); put_str(f, b.driver)
        f.write(struct.pack("<4d", inp.lat0, inp.lon0, inp.course0, inp.speed0))
        put(f, inp.axis, "<f8"); f.write(struct.pack("<dd", inp.scale, inp.bias))
        f.write(struct.pack("<i", len(inp.t)))
        put(f, inp.t, "<f8"); put(f, inp.acc, "<f8"); put(f, inp.gyr, "<f8"); put(f, st, "<i1")
        for a in dr:
            put(f, a, "<f8")
        f.write(struct.pack("<i", len(checks)))
        for (metres, r), ka, kb in zip(checks, range(len(checks)), range(len(checks))):
            te, tn, td = scoring.truth_at(S, i, i + r)
            ra, rb = runs
            f.write(struct.pack("<ii", metres, r))
            f.write(struct.pack("<9d", te, tn, td, ra["east"][ka], ra["north"][ka], ra["dist"][ka],
                                rb["east"][kb], rb["north"][kb], rb["dist"][kb]))
            for seed, run in (("A", ra), ("B", rb)):
                recs.append(dict(driver=b.driver, checkpoint=metres, seed=seed,
                                 err=scoring.errors(S, i, i + r, run["east"][ka], run["north"][ka], run["dist"][ka])[0],
                                 dr=scoring.errors(S, i, i + r, dr[0][r], dr[1][r], dr[2][r])[0]))
        if (nb + 1) % 25 == 0:
            log(f"  {nb + 1}/{len(pick)} blackouts")
log(f"engine fixture: {(OUT/'engine_fixture.bin').stat().st_size/1e6:.1f} MB")

R = pd.DataFrame(recs)
print("\n  Python reference on these blackouts — median 2D drift %, filter seed A / seed B / map-free")
print(R.groupby(["checkpoint", "seed"]).err.median().unstack().assign(
    no_map=R[R.seed == "A"].groupby("checkpoint").dr.median()).round(2).to_string())
