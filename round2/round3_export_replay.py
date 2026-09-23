"""Round 3 · replay clips that show the fix — the old cursor and the new one on the same blackout.

The app's replay screen draws three tracks. Round 2 used them for true position / estimate with the map / estimate
without the map. Here the third track is repurposed to the thing worth looking at now:

    green   the vehicle's own GNSS — the answer key, never an engine input
    cyan    round 3: the same filter, reported through mode hysteresis and a speed-limited cursor (core/smooth.py)
    red     round 2: the same filter's raw estimate, which hops between roads

Both cursors come from one run of the filter per clip with the same seed, so any difference on screen is the reporting
layer and nothing else.

Which blackouts are shown is decided by a rule fixed before any of them is scored: for each driver, the first blackout
that qualifies in each driving-condition band (under 40, 40-50, 50-70, 70+), earliest first, at most three. Nothing is
chosen for looking good, and nothing is dropped for looking bad. `--originals` replays the old set instead (the clips
step9_export_replay.py picked in round 2 by how they ended, which is the hardest possible sample for a path average).

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


# Kept on screen whatever the rule picks: the blackouts worth watching because they go wrong. A_S4_s1_44419 leaves the
# road by 162 m and comes back — the wrong-branch failure that no summary number conveys.
ALWAYS = {"A_S4_s1_44419": "off road"}


def by_rule(per_driver=3):
    """The demo set, by a rule stated in advance: per driver, the earliest blackout in each condition band."""
    BL = pd.read_parquet(R2/"out/blackouts.parquet")
    BL = BL[BL.moving_1000 & BL.end_1000.notna() & (BL.history_s >= 300)]
    rows = []
    for driver, g in BL.groupby("driver"):
        taken = []
        for band in ("slow", "mixed", "ps_60", "fast"):
            q = g[g.band_1000 == band].sort_values(["drive", "session", "row_start"])
            for r in q.itertuples(index=False):
                # never two clips of the same stretch of road: they replay as the same route twice
                if any(t[:2] == (r.drive, r.session) and abs(t[2] - r.row_start) < 1200 for t in taken):
                    continue
                taken.append((r.drive, int(r.session), int(r.row_start), band, driver))
                break
            if len(taken) >= per_driver:
                break
        for drive, session, start, band, drv in taken:
            rows.append(dict(id=f"{drv}_{drive}_s{session}_{start}", driver=drv, drive=drive, session=session,
                             row_start=start, band=band, role="tuning" if drv in ("A", "B") else "test"))
    for cid, note in ALWAYS.items():
        if cid in {r["id"] for r in rows}:
            continue
        drv, drive, sess, start = cid.split("_")[0], cid.split("_")[1], int(cid.split("_")[2][1:]), int(cid.split("_")[3])
        band = BL[(BL.drive == drive) & (BL.session == sess) & (BL.row_start == start)].band_1000
        rows.append(dict(id=cid, driver=drv, drive=drive, session=sess, row_start=start,
                         band=(band.iloc[0] if len(band) else "slow"),
                         role="tuning" if drv in ("A", "B") else "test", note=note))
    R = pd.DataFrame(rows).sort_values(["driver", "drive", "session", "row_start"]).reset_index(drop=True)
    if "note" not in R:
        R["note"] = None
    R["ride"] = R.groupby("driver").cumcount() + 1
    R["name"] = "England ride " + R.ride.astype(str) + R.note.apply(lambda n: f" · {n}" if isinstance(n, str) else "")
    return R


def originals():
    """The clips the app already had (round2/out/replay/index.json), so the showcase keeps the same examples."""
    idx = json.loads((R2/"out/replay/index.json").read_text())
    rows = []
    for c in idx["clips"]:
        drive, session, start = c["drive"], int(c["session"]), int(c["id"].rsplit("_", 1)[1])
        rows.append(dict(id=c["id"], driver=c["driver"], drive=drive, session=session, row_start=start,
                         band=c["band"], role=c["role"], note=None))
    R = pd.DataFrame(rows).sort_values(["driver", "drive", "session", "row_start"]).reset_index(drop=True)
    R["note"] = None
    # two of the exported blackouts start 14 s apart on the same road (A's 44419 and 44559) and replay as the same
    # route twice; keep the earlier one so nothing is chosen by its score
    keep = []
    for _, g in R.groupby("driver"):
        last = None
        for r in g.itertuples(index=False):
            same_road = last is not None and (r.drive, r.session) == last[:2] and abs(r.row_start - last[2]) < 1200
            if not same_road:
                keep.append(r.id)
                last = (r.drive, r.session, r.row_start)
    R = R[R.id.isin(keep)].reset_index(drop=True)
    # the readable names, numbered per driver exactly as the app numbers them
    R["ride"] = R.groupby("driver").cumcount() + 1
    R["name"] = "England ride " + R.ride.astype(str)
    return R


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
                                 FIX["margin"], FIX["hold"], FIX.get("release_m", 80.0),
                                 FIX.get("min_share", 0.05))
    new = particle.run(inp, net, stat[i:j + 1], rows, params=PARAMS, rng=np.random.default_rng(i), estimator=tracker)

    lat0, lon0 = float(S.lat[i]), float(S.lon[i])
    true_e, true_n = enu(S.lat[i:j + 1], S.lon[i:j + 1], lat0, lon0)
    true_dist = S.dist[i:j + 1] - S.dist[i]
    k = np.array([0] + new["rows"])
    t_all = inp.t[k] - inp.t[0]
    old_e = np.array([0.0] + old["east"]); old_n = np.array([0.0] + old["north"])
    new_e = np.array([0.0] + new["east"]); new_n = np.array([0.0] + new["north"])
    new_e, new_n = smooth.smooth_track(t_all, new_e, new_n, inp.speed0, FIX["catch_up"], FIX["extra"],
                                       close_s=FIX.get("close_s", smooth.CLOSE_S),
                                       max_factor=FIX.get("max_factor", smooth.MAX_FACTOR))
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
        id=str(row.id),
        driver=str(row.driver), role=str(row.role),
        drive=str(row.name), session=int(row.session), row_start=i,
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
    picks = originals() if "--originals" in sys.argv else by_rule()
    log(f"exporting {len(picks)} clips at {hz} Hz — round 3 against round 2 on the same blackouts")

    index, cache = [], {}
    for row in picks.itertuples(index=False):
        clip = build_clip(row, BL, net, cache, hz)
        if clip is None:
            continue
        (OUT/f"{clip['id']}.json").write_text(json.dumps(clip, separators=(",", ":")))
        clip["dataset_drive"] = str(row.drive)          # the IO-VNBD code the name replaced
        index.append({k: clip[k] for k in ("id", "driver", "role", "drive", "dataset_drive", "session", "band",
                                           "turns", "avg_kmh",
                                           "distance_m", "duration_s", "final_drift_m", "final_drift_pct",
                                           "final_base_m", "final_base_pct", "mean_drift_pct", "mean_base_pct")})
        log(f"  {clip['id']:<24} {clip['drive']:<16} {clip['band']:<6} "
            f"path: round 2 {clip['mean_base_pct']:>5.1f}% -> round 3 {clip['mean_drift_pct']:>5.1f}%   "
            f"worst {clip['worst_base_pct']:>5.1f}% -> {clip['worst_drift_pct']:>5.1f}%")

    # replace the app's clips with these: the Trichy ones are rebuilt from round2/phone_data by make_trichy_clips.sh
    for f in ASSETS.glob("*.json"):
        f.unlink()
    wanted = {c["id"] + ".json" for c in index} | {"index.json"}
    for f in OUT.glob("*.json"):                      # only what this export produced: no leftovers from earlier runs
        if f.name in wanted:
            shutil.copy(f, ASSETS/f.name)
    meta = dict(generated=time.strftime("%Y-%m-%d"), checkpoint_m=CHECKPOINT, hz=hz, params=PARAMS,
                calibration=CHOICE, reporting=FIX, clips=index)
    (OUT/"index.json").write_text(json.dumps(meta, indent=1))
    shutil.copy(OUT/"index.json", ASSETS/"index.json")
    total = sum(f.stat().st_size for f in ASSETS.glob("*.json"))
    log(f"done — {len(index)} clips, {total/1e6:.1f} MB in {ASSETS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
