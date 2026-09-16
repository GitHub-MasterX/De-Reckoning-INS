# Round 2 — map-landmark positioning

Using OpenStreetMap road structure (junctions, roundabouts, bends) and turns detected by the
gyroscope to correct dead-reckoning drift. All round-2 work lives on branch **`round-2`**, inside
this folder.

## Round 1 is frozen

| | |
|---|---|
| **Tag** | `round-1` → commit `02f408a`, exactly as submitted and cleared |
| **Rule on this branch** | nothing outside `round2/` is changed |
| **How to check** | `git diff round-1 --stat` lists only `round2/` paths |
| **Data** | round-2 scripts only *read* `data/clean/` and `data/alignment.csv`; they write to `round2/out/` and the git-ignored `data/osm/` — never to `data/clean/`, `models/` or `out/` |
| **Verified 2026-09-15** | `run_evaluation.py` re-run from the tag in a separate checkout reproduced every committed output byte for byte (1 km drift: E 101.8 m, B 161.1 m, D 196.0 m, A 164.9 m) |

To look at or run round 1 exactly: `git switch --detach round-1`, then `git switch round-2` to come back.

## Contents

| Path | What |
|---|---|
| `MAP_LANDMARK_APPROACH.md` | the approach: idea, feasibility, OSM results, audit, corrections, next steps |
| `EXECUTION_LOG.md` | every run: why, how long, what came out, what went wrong |
| `DECISIONS.md` | the settled rules: weighting, metric, blackout sets, train/test split, design |
| `step1_evaluator.py` | step 1 — builds the fixed blackout list and checks the scoring |
| `step2_calibration.py` | step 2 — gyro calibration from GNSS history only, and the heading error it leaves |
| `step3_deadreckoning.py` | step 3 — map-free 2D dead reckoning, the honest baseline, and where its error comes from |
| `step4_roadnetwork.py` | step 4 — the drivable road network from OSM (`data/osm/road_network.npz`), checked against the true tracks |
| `step5_particlefilter.py` | step 5 — the road-constrained particle filter, tried on the tuning drivers |
| `step6_tune.py` | step 6 — tunes the filter on A and B only and freezes the settings (`out/pf_params.json`) |
| `step7_test.py` | step 7 — runs the frozen filter once on the test drivers D and E |
| `run_round2_evaluation.py` | round-2 results in one command: per driver, per distance, per condition (reads step 7's output) |
| `step8_failures.py` | step 8 — why the filter fails when it fails, and the pictures of it |
| `PROJECT_SUMMARY.md` | **both rounds end to end**: the problem, the dataset, round 1, round 2, the numbers, the caveats, what is open |
| `ROUND2_REPORT.md` | the round-2 report: what was built, the results, the failures, what is open |
| `core/` | shared round-2 code: session loading, geodesy, blackout list, driving-condition context, gyro calibration, engine input, motion classifier, dead reckoning, road network and its build, scoring |
| `analysis/heading_error_sources.py`, `gyro_scale.py`, `gyro_columns.py` | step-2 diagnosis: why gyro heading drifts (scale, jitter, vibration) |
| `get_osm_map.sh` | downloads the England map (1.6 GB) into `data/osm/` with a progress bar and MD5 check |
| `get_tn_map.sh` | downloads the Tamil Nadu map (130 MB, openstreetmap.fr) into `data/osm/`; checks the size and reads every object |
| `tn_roadnetwork.py` | the Tamil Nadu road network (`data/osm/road_network_tn.npz`) by step 4's rules, measured against England on what the filter uses, map faults and tagged landmarks |
| `analysis/roadnet_build_check.py` | proves `core/roadnet_build.py` rebuilds step 4's England network array for array |
| `phone/export_motion_model.py` | round 1's `deploy_all` stop classifier as a tree file for the Android app, plus 1,000 windows scikit-learn scored, for the app's tests |
| `phone/export_roadnet.py` | a road network cut to a box, in the binary layout the app loads (`data/osm/phone/NAME.roadnet.bin`) |
| `phone/export_engine_fixture.py`, `phone/export_session_fixture.py` | Python engine reference runs the app's Kotlin port is tested against (calibration, dead reckoning, filter, whole sessions) |
| `requirements.txt` | round-1 environment + `osmium` |
| `analysis/osm_landmarks.py` | landmark tags along the routes: roundabouts, signals, bumps, bridges, … |
| `analysis/landmark_usable.py` | which of those landmarks the car actually showed (turned at, stopped at) |
| `analysis/osm_junctions.py` | every road junction along the routes, and the turns possible there |
| `analysis/snap_recheck.py` | simulates snapping under `run_evaluation.py`'s blackout rules |
| `analysis/tunnel_lengths.py` | lengths of the mapped road tunnels in the dataset area |
| `out/` | result tables and the console output of each run |

## Running (from the repo root)

Needs `data/clean/` (round-1 cleaning), the map, and about 5 GB of free RAM for the two map scans.

```bash
.venv/bin/pip install -r round2/requirements.txt
.venv/bin/python3 round2/step1_evaluator.py                     # step 1, a few seconds
.venv/bin/python3 round2/step2_calibration.py                   # step 2, seconds (needs step 1)
.venv/bin/python3 round2/step3_deadreckoning.py                 # step 3, seconds (needs steps 1-2)
round2/get_osm_map.sh                                           # once, 1.6 GB
round2/get_tn_map.sh                                            # once, 130 MB — Tamil Nadu
.venv/bin/python3 round2/step4_roadnetwork.py                   # step 4, ~2 min map scan (--reuse: seconds)
.venv/bin/python3 round2/step5_particlefilter.py --limit 200    # step 5, tuning drivers only
.venv/bin/python3 round2/step6_tune.py --limit 120              # step 6, ~1 min, freezes out/pf_params.json
.venv/bin/python3 round2/step7_test.py                          # step 7, the one frozen run on D and E
.venv/bin/python3 round2/run_round2_evaluation.py               # the results, per driver and per distance
.venv/bin/python3 round2/step8_failures.py                      # step 8, why it fails, and the pictures
.venv/bin/python3 round2/tn_roadnetwork.py                      # Tamil Nadu network, ~2.5 min, ~8 GB RAM (--reuse: 50 s)
.venv/bin/python3 round2/analysis/roadnet_build_check.py        # the shared build against step 4, ~1 min, 5 GB RAM
.venv/bin/python3 round2/phone/export_motion_model.py           # phone: classifier trees + test windows
.venv/bin/python3 round2/phone/export_roadnet.py --box S,W,N,E --name NAME   # phone: a road network for an area
.venv/bin/python3 round2/phone/export_engine_fixture.py         # phone: reference runs (needs the England map built)
.venv/bin/python3 round2/phone/export_session_fixture.py        # phone: whole-session reference runs
# then, in round2/android:  gradle testDebugUnitTest  (the Kotlin engine against all of the above)
# replay drives pulled from the phone (adb pull /sdcard/Android/data/com.sih2026.nav.live/files/drives/ <folder>):
#   gradle testDebugUnitTest --tests '*DriveReplayTest*' -Ddrive=<folder>
.venv/bin/python3 round2/analysis/osm_landmarks.py              # 91 s
.venv/bin/python3 round2/analysis/landmark_usable.py            # needs osm_landmarks.py
.venv/bin/python3 round2/analysis/osm_junctions.py              # 107 s
.venv/bin/python3 round2/analysis/snap_recheck.py --junctions    # needs osm_junctions.py
```
