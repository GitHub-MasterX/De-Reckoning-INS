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
| `core/` | shared round-2 code: session loading, geodesy, blackout list, scoring |
| `get_osm_map.sh` | downloads the England map (1.6 GB) into `data/osm/` with a progress bar and MD5 check |
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
round2/get_osm_map.sh                                           # once, 1.6 GB
.venv/bin/python3 round2/analysis/osm_landmarks.py              # 91 s
.venv/bin/python3 round2/analysis/landmark_usable.py            # needs osm_landmarks.py
.venv/bin/python3 round2/analysis/osm_junctions.py              # 107 s
.venv/bin/python3 round2/analysis/snap_recheck.py --junctions    # needs osm_junctions.py
```
