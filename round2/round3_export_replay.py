"""Round 3 · replay clips that show the fix — the old cursor and the new one on the same blackout.

The app's replay screen draws three tracks. Round 2 used them for true position / estimate with the map / estimate
without the map. Here the third track is repurposed to the thing worth looking at now:

    green   the vehicle's own GNSS — the answer key, never an engine input
    cyan    round 3: the same filter, reported through mode hysteresis and a speed-limited cursor (core/smooth.py)
    red     round 2: the same filter's raw estimate, which hops between roads

Both cursors come from one run of the filter per clip with the same seed, so any difference on screen is the reporting
layer and nothing else.

Clips are chosen by what the estimate did along the whole path, never by where it happened to finish, and each driver
contributes three: the blackout where round 2 jumped worst (what the fix is for), a typical one (its path average is
the median for that driver), and its best. The reason is written into the clip so the picker can say which is which.

Outputs: round2/out/replay3/*.json and the same files copied into the app's assets.
Run from the repo root:  .venv/bin/python3 round2/round3_export_replay.py [--hz 10]
"""
import warnings; warnings.filterwarnings("ignore")
import json, shutil, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, motion, particle, roadnet, smooth
from core.geo import enu, inv_enu

T0 = time.time()
LEAD_IN_S = 15.0
CHECKPOINT = 1000
FLOOR_M = 100.0
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
FIX = json.loads((R2/"out/round3_report_choice.json").read_text())
OUT = R2/"out/replay3"
ASSETS = R2/"android/app/src/main/assets/replay"

def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)


def candidates():
    """Blackouts already measured both ways: round 2's raw cursor and round 3's, per driver."""
    frames = []
    for path, chosen in ((R2/"out/round3_report_fix_test.parquet", "round 3 (chosen)"),
                         (R2/"out/round3_report_fix_tune.parquet", "both, mild hold")):
        if not path.exists():
            continue
        P = pd.read_parquet(path)
        old = P[P.variant == "round 2 (as published)"].set_index(["drive", "session", "row_start"])
        new = P[P.variant == chosen].set_index(["drive", "session", "row_start"])
        j = old.join(new, lsuffix="_old", rsuffix="_new", how="inner").reset_index()
        frames.append(j)
    C = pd.concat(frames, ignore_index=True)
    return C.rename(columns={"driver_old": "driver", "band_old": "band"})


def pick(C, per_driver=3):
    """Per driver: the blackout round 2 jumped worst on, a typical one, and the best — judged along the path."""
    out = []
    for driver, g in C.groupby("driver"):
        g = g[g.path_new.notna()].copy()
        if g.empty:
            continue
        worst_jump = g.nlargest(1, "worst_jump_old").assign(why="biggest jump in round 2")
        typical = g.iloc[[(g.path_new - g.path_new.median()).abs().argsort().iloc[0]]].assign(why="typical")
        best = g.nsmallest(1, "path_new").assign(why="best")
        take = pd.concat([worst_jump, typical, best]).drop_duplicates(subset=["drive", "session", "row_start"])
        out.append(take.head(per_driver))
    return pd.concat(out, ignore_index=True)


def build_clip(row, BL, net, cache, hz):
    key = (row.drive, int(row.session))
    if key not in cache:
        S = sessions.load(row.drive, row.driver, int(row.session))
        cache.clear()
        cache[key] = (S, calibration.Calibrator(S), motion.stationary_rows(S, row.driver)[0])
    S, C, stat = cache[key]
    i = int(row.row_start)
    j = int(BL.loc[(row.drive, int(row.session), i), f"end_{CHECKPOINT}"])
    cal = calibration.engine_calibration(C, i, CHOICE)
    if cal is None:
        return None
    inp = engine_input.build(S, cal, i, j)
    rows = list(range(1, j - i + 1))

    old = particle.run(inp, net, stat[i:j + 1], rows, params=PARAMS, rng=np.random.default_rng(i))
    tracker = smooth.ModeTracker(PARAMS.get("cluster_m", particle.DEFAULTS["cluster_m"]),
                                 FIX["margin"], FIX["hold"])
    new = particle.run(inp, net, stat[i:j + 1], rows, params=PARAMS, rng=np.random.default_rng(i), estimator=tracker)

    lat0, lon0 = float(S.lat[i]), float(S.lon[i])
    true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], lat0, lon0)
    true_dist = S.dist[i:j + 1] - S.dist[i]
    k = np.array([0] + new["rows"])
    t_all = inp.t[k] - inp.t[0]
    old_e = np.array([0.0] + old["east"]); old_n = np.array([0.0] + old["north"])
    new_e = np.array([0.0] + new["east"]); new_n = np.array([0.0] + new["north"])
    new_e, new_n = smooth.smooth_track(t_all, new_e, new_n, inp.speed0, FIX["catch_up"], FIX["extra"])
    on_map = np.array([False] + new["on_map"])

    dt = np.clip(np.diff(inp.t), 0.0, None)
    psi = inp.course0 + np.concatenate(([0.0], np.cumsum(inp.turn_rate()[:-1]*dt)))

    step = max(1, int(round(10/hz)))
    sel = k[::step]
    new_lat, new_lon = inv_enu(new_e[::step], new_n[::step], lat0, lon0)
    old_lat, old_lon = inv_enu(old_e[::step], old_n[::step], lat0, lon0)
    dist = np.maximum(true_dist[sel], 1e-6)
    new_m = np.hypot(new_e[::step] - true_e[sel], new_n[::step] - true_n[sel])
    old_m = np.hypot(old_e[::step] - true_e[sel], old_n[::step] - true_n[sel])
    new_pct, old_pct = 100*new_m/dist, 100*old_m/dist
    scored = true_dist[sel] >= FLOOR_M

    lead = int(LEAD_IN_S*10)
    pre = slice(max(0, i - lead), i, step)
    clip = dict(
        id=f"r3_{row.driver}_{row.drive}_s{int(row.session)}_{i}",
        driver=str(row.driver), role="tuning" if row.driver in ("A", "B") else "test",
        drive=str(row.why), session=int(row.session), row_start=i,
        band=str(row.band), turns=int(BL.loc[(row.drive, int(row.session), i), f"turns_{CHECKPOINT}"]),
        avg_kmh=round(float(3.6*true_dist[-1]/(S.t[j] - S.t[i])), 1),
        distance_m=round(float(true_dist[-1]), 1), duration_s=round(float(S.t[j] - S.t[i]), 1), hz=hz,
        tracks="cyan = round 3 (hysteresis + speed-limited cursor), red = round 2's raw estimate, green = GNSS truth",
        final_drift_m=round(float(new_m[-1]), 1), final_drift_pct=round(float(new_pct[-1]), 2),
        final_base_m=round(float(old_m[-1]), 1), final_base_pct=round(float(old_pct[-1]), 2),
        mean_drift_pct=round(float(new_pct[scored].mean()), 2), mean_base_pct=round(float(old_pct[scored].mean()), 2),
        worst_drift_pct=round(float(new_pct[scored].max()), 2), worst_base_pct=round(float(old_pct[scored].max()), 2),
        lead_in=dict(lat=[round(float(v), 7) for v in S.lat[pre]], lon=[round(float(v), 7) for v in S.lon[pre]],
                     heading=[round(float(v), 1) for v in S.heading[pre]],
                     speed_kmh=[round(float(3.6*v), 1) for v in S.v[pre]]),
        t=[round(float(v), 2) for v in (inp.t[sel] - inp.t[0])],
        true_lat=[round(float(v), 7) for v in S.lat[i:j + 1][sel]],
        true_lon=[round(float(v), 7) for v in S.lon[i:j + 1][sel]],
        true_heading=[round(float(v), 1) for v in S.heading[i:j + 1][sel]],
        true_speed_kmh=[round(float(3.6*v), 1) for v in S.v[i:j + 1][sel]],
        true_dist_m=[round(float(v), 1) for v in true_dist[sel]],
        pf_lat=[round(float(v), 7) for v in new_lat], pf_lon=[round(float(v), 7) for v in new_lon],
        pf_heading=[round(float(np.degrees(v) % 360), 1) for v in psi[sel]],
        pf_on_map=[bool(v) for v in on_map[::step]],
        nomap_lat=[round(float(v), 7) for v in old_lat], nomap_lon=[round(float(v), 7) for v in old_lon],
        drift_m=[round(float(v), 1) for v in new_m], drift_pct=[round(float(v), 2) for v in new_pct],
        nomap_drift_m=[round(float(v), 1) for v in old_m], nomap_drift_pct=[round(float(v), 2) for v in old_pct],
        engine_speed_kmh=round(float(3.6*inp.speed0), 1),
    )
    return clip


def main():
    hz = arg("--hz", 10)
    OUT.mkdir(parents=True, exist_ok=True)
    BL = pd.read_parquet(R2/"out/blackouts.parquet").set_index(["drive", "session", "row_start"])
    net = roadnet.RoadNetwork()
    picks = pick(candidates())
    log(f"exporting {len(picks)} clips at {hz} Hz — round 3 against round 2 on the same blackouts")

    index, cache = [], {}
    for row in picks.itertuples(index=False):
        clip = build_clip(row, BL, net, cache, hz)
        if clip is None:
            continue
        (OUT/f"{clip['id']}.json").write_text(json.dumps(clip, separators=(",", ":")))
        index.append({k: clip[k] for k in ("id", "driver", "role", "drive", "session", "band", "turns", "avg_kmh",
                                           "distance_m", "duration_s", "final_drift_m", "final_drift_pct",
                                           "final_base_m", "final_base_pct", "mean_drift_pct", "mean_base_pct")})
        log(f"  {clip['id']:<28} {clip['drive']:<22} {clip['band']:<6} "
            f"path: round 2 {clip['mean_base_pct']:>5.1f}% -> round 3 {clip['mean_drift_pct']:>5.1f}%   "
            f"worst {clip['worst_base_pct']:>5.1f}% -> {clip['worst_drift_pct']:>5.1f}%")

    # replace the app's clips with these: the Trichy ones are rebuilt from round2/phone_data by make_trichy_clips.sh
    for f in ASSETS.glob("*.json"):
        f.unlink()
    for f in OUT.glob("*.json"):
        shutil.copy(f, ASSETS/f.name)
    meta = dict(generated=time.strftime("%Y-%m-%d"), checkpoint_m=CHECKPOINT, hz=hz, params=PARAMS,
                calibration=CHOICE, reporting=FIX, clips=index)
    (OUT/"index.json").write_text(json.dumps(meta, indent=1))
    shutil.copy(OUT/"index.json", ASSETS/"index.json")
    total = sum(f.stat().st_size for f in ASSETS.glob("*.json"))
    log(f"done — {len(index)} clips, {total/1e6:.1f} MB in {ASSETS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
