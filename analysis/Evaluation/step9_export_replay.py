"""Round 2 · Step 9 — replay clips for the Android app.

Re-runs the frozen particle filter (out/Config/pf_params.json) on a few real blackouts, recording the whole path, and
writes one JSON per clip holding three tracks at 10 Hz:

  true      the vehicle's own GNSS — the answer key, never an engine input
  filter    the round-2 estimate: gyro calibrated from pre-blackout GNSS history, held speed, road network
  no_map    the same engine without the map, so the app can show what the map buys

Each clip also carries a short GNSS-fused lead-in before the blackout, where all three tracks coincide, so the
app can show the moment GNSS is lost and the estimates start to diverge.

The numbers are produced by exactly the code path step7/step8 use, so a clip's drift matches ROUND2_REPORT.md.

Outputs: round2/out/replay/<clip>.json, round2/out/replay/index.json, and the same files copied into
round2/android/app/src/main/assets/replay/.
Run from the repo root:  .venv/bin/python3 round2/step9_export_replay.py [--per-driver N] [--hz 10]"""
import warnings; warnings.filterwarnings("ignore")
import json, shutil, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, calibration, deadreckoning, engine_input, motion, particle, roadnet, scoring
from core.Engine.geo import enu, inv_enu

T0 = time.time()
LEAD_IN_S = 15.0          # seconds of GNSS-fused driving shown before the blackout starts
CHECKPOINT = 1000         # the 1 km blackouts — the problem statement's headline case
PASS_PCT = 10.0           # a clip must finish inside the benchmark to be worth replaying


def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default


PER_DRIVER = arg("--per-driver", 3)
HZ = arg("--hz", 10)
PARAMS = json.loads((ROOT/"outputs/Config/pf_params.json").read_text())
CHOICE = (ROOT/"outputs/Config/calibration_choice.txt").read_text().strip()
OUT = ROOT/"outputs/replay"
ASSETS = ROOT/"front-end/android/app/src/main/assets/replay"


def log(m):
    print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)


def pick_clips():
    """The clips to export: per driver, urban blackouts where the map helps most *and* the estimate still lands.

    Two rules, both needed:
      urban       a motorway straight is where the map is known to lose (ROUND2_REPORT.md §5), and a replay of
                  one shows two cursors sitting on top of each other for a kilometre
      passing     the filter must finish inside the 10% benchmark. Ranking on improvement alone picks the
                  blackouts where the baseline was worst — A/S2 improves 119% -> 44%, the largest gain in the
                  set, and still ends 437 m from the car. That is a failure case, not a demo."""
    E = pd.read_parquet(ROOT/"outputs/Pipeline_Data/test_errors.parquet")
    E = E[(E.set == "moving") & (E.checkpoint == CHECKPOINT)].copy()
    E["delta"] = E.pf_pos - E.base_pos
    urban = E[E.band.isin(["slow", "mixed", "ps_60"]) & (E.turns >= 2) & (E.pf_pos < PASS_PCT)]
    return pd.concat([q.nsmallest(PER_DRIVER, "delta") for _, q in urban.groupby("driver")])


def build_clip(row, BL, net, cache):
    """One clip: the three tracks, the drift between them, and the context the app shows."""
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
    rows = list(range(1, j - i + 1))                       # record every row: the app replays at 10 Hz
    res = particle.run(inp, net, stat[i:j+1], rows, params=PARAMS, rng=np.random.default_rng(i))
    dr_e, dr_n, dr_d = deadreckoning.run(inp, stationary=stat[i:j+1])

    lat0, lon0 = float(S.lat[i]), float(S.lon[i])
    true_e, true_n = enu(S.lat[i:j+1], S.lon[i:j+1], lat0, lon0)
    true_dist = S.dist[i:j+1] - S.dist[i]

    # the filter reports only at recorded rows; row 0 is the fix itself, where every track starts together
    k = np.array([0] + res["rows"])
    pf_e = np.array([0.0] + res["east"])
    pf_n = np.array([0.0] + res["north"])
    on_map = np.array([False] + res["on_map"])

    # the engine's own heading, the same gyro integration the filter uses (core/particle.py)
    dt = np.clip(np.diff(inp.t), 0.0, None)
    psi = inp.course0 + np.concatenate(([0.0], np.cumsum(inp.turn_rate()[:-1]*dt)))

    step = max(1, int(round(10/HZ)))
    sel = k[::step]
    pf_lat, pf_lon = inv_enu(pf_e[::step], pf_n[::step], lat0, lon0)
    dr_lat, dr_lon = inv_enu(dr_e[sel], dr_n[sel], lat0, lon0)

    drift_m = np.hypot(pf_e[::step] - true_e[sel], pf_n[::step] - true_n[sel])
    base_m = np.hypot(dr_e[sel] - true_e[sel], dr_n[sel] - true_n[sel])
    dist = np.maximum(true_dist[sel], 1e-6)

    # lead-in: GNSS-fused driving before the blackout, all three tracks on the truth
    lead = int(LEAD_IN_S*10)
    a = max(0, i - lead)
    pre = slice(a, i, step)

    clip = dict(
        id=f"{row.driver}_{row.drive}_s{int(row.session)}_{i}",
        driver=str(row.driver),
        role="tuning" if row.driver in ("A", "B") else "test",
        drive=str(row.drive), session=int(row.session), row_start=i,
        band=str(row.band), turns=int(row.turns),
        avg_kmh=round(float(3.6*true_dist[-1]/(S.t[j] - S.t[i])), 1),
        distance_m=round(float(true_dist[-1]), 1),
        duration_s=round(float(S.t[j] - S.t[i]), 1),
        hz=HZ,
        final_drift_m=round(float(drift_m[-1]), 1),
        final_drift_pct=round(float(100*drift_m[-1]/dist[-1]), 2),
        final_base_m=round(float(base_m[-1]), 1),
        final_base_pct=round(float(100*base_m[-1]/dist[-1]), 2),
        lead_in=dict(
            lat=[round(float(v), 7) for v in S.lat[pre]],
            lon=[round(float(v), 7) for v in S.lon[pre]],
            heading=[round(float(v), 1) for v in S.heading[pre]],
            speed_kmh=[round(float(3.6*v), 1) for v in S.v[pre]]),
        t=[round(float(v), 2) for v in (inp.t[sel] - inp.t[0])],
        true_lat=[round(float(v), 7) for v in S.lat[i:j+1][sel]],
        true_lon=[round(float(v), 7) for v in S.lon[i:j+1][sel]],
        true_heading=[round(float(v), 1) for v in S.heading[i:j+1][sel]],
        true_speed_kmh=[round(float(3.6*v), 1) for v in S.v[i:j+1][sel]],
        true_dist_m=[round(float(v), 1) for v in true_dist[sel]],
        pf_lat=[round(float(v), 7) for v in pf_lat],
        pf_lon=[round(float(v), 7) for v in pf_lon],
        pf_heading=[round(float(np.degrees(v) % 360), 1) for v in psi[sel]],
        pf_on_map=[bool(v) for v in on_map[::step]],
        nomap_lat=[round(float(v), 7) for v in dr_lat],
        nomap_lon=[round(float(v), 7) for v in dr_lon],
        drift_m=[round(float(v), 1) for v in drift_m],
        drift_pct=[round(float(v), 2) for v in 100*drift_m/dist],
        nomap_drift_m=[round(float(v), 1) for v in base_m],
        nomap_drift_pct=[round(float(v), 2) for v in 100*base_m/dist],
        # the engine's speed assumption: the last GNSS fix, held (zeroed where the classifier says stationary)
        engine_speed_kmh=round(float(3.6*inp.speed0), 1),
    )
    # the scored figures, recomputed here so a clip can be checked against the report
    pos_pct, dist_pct = scoring.errors(S, i, j, pf_e[-1], pf_n[-1], res["dist"][-1])
    clip["scored_pos_pct"] = round(float(pos_pct), 2)
    clip["scored_dist_pct"] = round(float(dist_pct), 2)
    clip["reported_pf_pct"] = round(float(row.pf_pos), 2)
    clip["reported_base_pct"] = round(float(row.base_pos), 2)
    return clip


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    BL = pd.read_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet").set_index(["drive", "session", "row_start"])
    net = roadnet.RoadNetwork()
    picks = pick_clips()
    log(f"exporting {len(picks)} clips ({PER_DRIVER} per driver) at {HZ} Hz")

    index, cache = [], {}
    for row in picks.sort_values(["driver", "delta"]).itertuples(index=False):
        clip = build_clip(row, BL, net, cache)
        if clip is None:
            log(f"  {row.driver} {row.drive} s{row.session} {row.row_start}: no calibration, skipped")
            continue
        (OUT/f"{clip['id']}.json").write_text(json.dumps(clip, separators=(",", ":")))
        shutil.copy(OUT/f"{clip['id']}.json", ASSETS/f"{clip['id']}.json")
        index.append({k: clip[k] for k in ("id", "driver", "role", "drive", "session", "band", "turns",
                                           "avg_kmh", "distance_m", "duration_s",
                                           "final_drift_m", "final_drift_pct",
                                           "final_base_m", "final_base_pct")})
        log(f"  {clip['id']:<26} {clip['band']:<6} {clip['turns']} turns  "
            f"no map {clip['final_base_pct']:>6.1f}%  with map {clip['final_drift_pct']:>5.1f}%  "
            f"(report says {clip['reported_base_pct']:.1f}% / {clip['reported_pf_pct']:.1f}%)")

    meta = dict(generated=time.strftime("%Y-%m-%d"), checkpoint_m=CHECKPOINT, hz=HZ,
                params=PARAMS, calibration=CHOICE, clips=index)
    (OUT/"index.json").write_text(json.dumps(meta, indent=1))
    shutil.copy(OUT/"index.json", ASSETS/"index.json")

    total = sum(f.stat().st_size for f in ASSETS.glob("*.json"))
    log(f"done — {len(index)} clips, {total/1e6:.1f} MB of assets in {ASSETS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
