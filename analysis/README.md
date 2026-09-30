# analysis/ — every script, what it does, and where it fits

`analysis/` holds every diagnostic, evaluation, and model-development script in the project, organized by what
each one is, not which round produced it.

| Folder | Role |
|---|---|
| `Data_pipeline/` | Raw IO-VNBD dataset → cleaned, aligned, frame-rotated parquet files |
| `Models/` | The motion classifier: training, evaluation, ZUPT scoring |
| `Figures/` | Report figures and the architecture diagram |
| `Evaluation/` | The map-constrained engine pipeline: blackout list → calibration → dead reckoning → road network → particle filter → tune → test → failure analysis |
| `Gyro_diagnosis/` | Why gyro heading drifts: scale, jitter, vibration |
| `Map_landmarks/` | OSM landmark coverage, junction density, tunnel lengths |
| `Integrity_checks/` | Proves the engine never leaks ground truth, and that shared code reproduces committed builds exactly |
| `Speed_Model/` | The learned speed model and its full development lineage |
| `Reporting_Metrics/` | The path-average metric, off-route/teleport analysis, and the reporting layer (hysteresis + speed-limited cursor) |
| `Evidence_Not_Deployed/` | Findings cited in the reports but not part of the live pipeline (a rejected arbiter, unproven bump-landmark self-mapping) |
| `archive.zip` | 29 completed round-1 investigations — each answered one question, cited by the reports as evidence. Nothing here needs re-running unless a claim is challenged. |

All scripts use the project venv: `.venv/bin/python3 analysis/<Folder>/<script>.py`, run from the repo root.

---

## Data_pipeline/ — rebuilds `data/` from the raw dataset, in this order

| # | Script | What it does |
|---|---|---|
| 1 | `clean_dataset.py` | Raw IO-VNBD → `data/clean/*.parquet`. Handles latin-1 encoding, two column-naming schemes, case-mismatched filenames, pair truncation. Keeps all 72 drives, flags the short/stationary ones. |
| 2 | `enrich_dataset.py` | Adds derived columns without touching originals: `session`, `speed_best` (GPS with CAN fallback through dropouts), bias-removed gyro, `stationary`, `gnss_dropout`, `stuck`. |
| 3 | `per_session.py` | Recomputes sync quality and CAN offset per session rather than per file. |
| 4 | `align_all.py` | Two-stage time alignment — coarse GPS-track match (±10 min), then fine gyro-vs-yaw match (±30 s). |
| 5 | `add_alignment.py` | Applies the lags as new columns. 98.6% of rows align; originals stay byte-identical. |
| 6 | `align_frame.py` | Rotates every drive from phone frame into vehicle frame using gravity, gyro projection and horizontal-acceleration PCA. |

Outputs land in `data/clean.zip` (unzip before running) and `data/test_outputs/*.csv`.

## Models/

| Script | What it does |
|---|---|
| `motion_classifier.py` | The deployed classifier. Stationary-vs-moving from IMU alone, leave-one-driver-out, 99.4% accuracy against a 90.3% naive threshold. |
| `evaluate.py` | The benchmark harness — simulates GNSS blackouts, reports drift for coast / model / oracle. |
| `zupt_eval.py` | What the classifier is worth to navigation, with blackouts that allow stops inside them. |
| `train_and_save.py`, `train_splits.py`, `load_model.py`, `eval_cache.py`, `drift_all_drivers.py` | Training, leave-one-driver-out splits, loading a saved model, the eval cache builder, per-driver drift evaluation. |

## Figures/

| Script | Output |
|---|---|
| `per_driver_plots.py` | Leave-one-driver-out drift curves → `outputs/plots/` |
| `final_plots.py` | Drift vs. distance with the speed profile, labelled by driving condition |
| `plot_aliasing.py` | The aliasing figure referenced in `MECHANISM.md` |
| `make_drawio.py` | The pipeline architecture diagram |

## Evaluation/ — the map-constrained engine, run in order

`step1_evaluator.py` → `step2_calibration.py` → `step3_deadreckoning.py` → `step4_roadnetwork.py` →
`step5_particlefilter.py` → `step6_tune.py` → `step7_test.py` → `step8_failures.py`, plus
`run_engine_evaluation.py` (results in one command) and `tn_roadnetwork.py` (the Tamil Nadu network).

Needs `data/clean.zip` unzipped, the OSM maps (`data/osm/get_osm_map.sh`, `get_tn_map.sh`), and ~5 GB free RAM for
the map scans.

## Speed_Model/, Reporting_Metrics/, Evidence_Not_Deployed/

The learned speed model's full lineage, the reporting-layer fix, and the two findings kept as cited evidence but
not deployed. Full mechanism and results: `MECHANISM.md` and `CHALLENGES.md` at the repo root README.

---

## Where the outputs go

```
data/clean.zip              72 drives, unzip to data/clean/ before running anything here
data/test_outputs/*.csv     alignment, sync, and session metadata
outputs/                    every result: Config, Pipeline_Data, Results, Map_Diagnostics,
                             Experiment_Results, Data_Diagnostics, Run_Logs, plots
```
