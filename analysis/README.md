# analysis/ — what each script is for

**`analysis/`** holds the 12 scripts you would run again.
**`analysis/archive/`** holds 29 completed investigations — each one answered a question
and its answer is written into the reports. Kept because `data/report/*.md` cites them as
the evidence behind specific numbers. Nothing here needs re-running unless a claim is
challenged.

All scripts use the project venv: `.venv/bin/python3 analysis/<script>.py`

---

## Pipeline — run in this order to rebuild `data/` from the raw dataset

| # | Script | What it does |
|---|---|---|
| 1 | `clean_dataset.py` | Raw IO-VNBD → `data/clean/*.parquet`. Handles latin-1 encoding, two column-naming schemes, case-mismatched filenames (40 of 72 pairs), pair truncation. Keeps all 72 drives, flags the short/stationary ones. Writes `manifest.csv`. |
| 2 | `enrich_dataset.py` | Adds derived columns without touching originals: `session`, `speed_best` (GPS with CAN fallback through dropouts), bias-removed gyro, `stationary`, `gnss_dropout`, `stuck`. |
| 3 | `per_session.py` | Recomputes sync quality and CAN offset **per session** rather than per file. Writes `data/sessions.csv`. |
| 4 | `align_all.py` | Two-stage time alignment across all 83 sessions — coarse GPS-track match (±10 min) then fine gyro-vs-yaw match (±30 s). Writes `data/alignment.csv` with `total_lag`. |
| 5 | `add_alignment.py` | Applies the lags as **new columns** (`veh_idx`, `aligned_valid`, `speed_best_al`, `lag_applied_s`). 98.6% of rows align; originals stay byte-identical. |
| 6 | `align_frame.py` | The alignment engine. Rotates every drive from phone frame into vehicle frame using gravity, gyro projection and horizontal-acceleration PCA. Adds `acc_fwd`, `acc_lat`, `acc_down`, `rate_roll/pitch/yaw`. Writes `data/frame_validation.csv`. |

## Models

| Script | What it does |
|---|---|
| `motion_classifier.py` | **The deployed model.** Stationary-vs-moving classification from IMU alone, leave-one-driver-out. 99.4% accuracy against a 90.3% naive threshold. Also characterises shock events. This is the PS's "detect and filter non-navigation motions" capability. |
| `evaluate.py` | The benchmark harness. Simulates GNSS blackouts and reports drift for coast / model / oracle. The oracle line is the evaluator's own sanity check — it must come out near 1%. |
| `zupt_eval.py` | Measures what the classifier is worth to navigation, with blackouts that allow stops inside them. |

## Figures

| Script | Output |
|---|---|
| `per_driver_plots.py` | Leave-one-driver-out drift curves → `out/plots/drift_pct.png`, `drift_metres.png`, `out/per_driver_drift.csv` |
| `final_plots.py` | Drift vs distance with the speed profile on the same axes, labelled by driving condition → `out/plots/drift_by_condition.png` |
| `make_drawio.py` | The full pipeline architecture diagram → `out/IDR_architecture.drawio` |

---

## archive/ — completed investigations

Grouped by the question each one answered.

### What is this dataset?
| Script | Finding |
|---|---|
| `survey.py` | Everything is 10 Hz, measured on all 144 pairs. Phone GPS updates every ~9 s. |
| `quality_check.py` | CAN and VBOX speed agree at r = 0.9993 — the labels are trustworthy. |
| `audit.py` | Timestamp discontinuities in 7 drives, stuck values in `Vtb1`, and `\|accel\| = 10.10` confirmed **correct** (noisy-vector bias), so nobody "fixes" it later. |
| `gap_dist.py` | Only 3 intervals of 1,070,673 exceed 150 ms — the empty band that justifies the 0.5 s session threshold. |

### Can speed be measured from this IMU?
| Script | Finding |
|---|---|
| `spectrum_check.py` | Killed the vibration-frequency idea: dominant frequency vs speed is r = −0.054 at 10 Hz. |
| `speed_baseline.py` | Absolute speed is unlearnable — MAE 18.7 km/h against a 26.5 dummy. |
| `physics_baseline.py` | Integrating acceleration does not beat coasting; fitted scale 0.18–0.42 where 1.0 is correct. Subtracting the at-rest bias made it **8× worse**. |
| `shrink.py` | Sweeping `v₀ + α·Σ(predictions)` — the optimum is **α = 0**. Every prediction has negative value. |
| `full_eval.py` | All strategies under one protocol. Nothing beats coast. |
| `test_r.py` | Showed r and drift disagree: r = 0.61 with a bias that compounds to 22 km/h over a blackout. |

### Are the phone and vehicle files describing the same moments?
| Script | Finding |
|---|---|
| `sync_check.py` | First detection of the sync problem. Single-axis — superseded. |
| `sync_v2.py` | Three-axis joint fit. `S2` went from 0.005 to **0.929** — orientation had been masquerading as desync. |
| `alignment_check.py` | Phone yaw offsets range 2° to 352° across drives. Superseded by `align_frame.py`. |
| `why_flat.py` | Traced the r = 0.017 speed-change result to per-drive frame differences. |
| `gps_align.py` | **The biggest correction.** Offsets of +111 s and +309 s found by widening the search from ±30 s to ±10 min. Recovered 6 hours, including the test set. |
| `final_verdicts.py` | GPS-track separation test, plus an acceleration-based sync attempt that largely failed (2 of 18 sessions). |

### Why is driver E's data noisier? — three hypotheses, all rejected
| Script | Verdict |
|---|---|
| `drift_check.py` | **Clock drift ✗** — phone interval is 0.10000 s, ε ≈ 0. The lag is constant within a session. |
| `mount_stability.py` | **Mount movement ✗** — `S3c` swings 28.9° and scores 0.95; `Vw4` swings 10.4° and scores 0.57. |
| `device_check.py` | **Worse phone ✗** — driver E's gyro is *quieter* (0.029 vs 0.046), identical ADC quantisation. |

### The curvature approach — promising, then retracted
| Script | Finding |
|---|---|
| `turn_physics.py` | Three speed estimators compared. Pointwise `a_lat/ω` = 0.032; regression = 0.438; **map curvature `ω/κ` = 0.824, MAE 4.8 km/h**. |
| `curvature_dr.py` | First blackout result, 10.0%. **Retracted** — indexed the map by true position. |
| `curv_quality.py` | Speed-fix quality against curvature: 30 m bends give 4.5 km/h error, 500 m bends give 34.9 km/h. |
| `curvature_kf.py` | Kalman with regression standard error — 15.6%, worse than a fixed gain. |
| `curv_final.py` | Kalman with physics-derived `R = (σ_ω/κ)²` — 12.1%, still worse. |
| `curv_tune.py` | Filter/gain sweep, 9.7% (96.9 m over 1 km). **Retracted** for the same reason. |
| `closed_loop.py` | **The retraction proof.** Looking up curvature at the engine's *own* estimated position **diverges** — 18.6% at 60 s, worse than coasting. |

### Where is the 10% line?
| Script | Finding |
|---|---|
| `duration_sweep.py` | Drift vs blackout length. Established that the PS's two benchmarks are not equally hard: 5 m / 50 m is met by coasting alone, 100 m / 1 km is not. |

### Contains a documented bug — kept as the record
| Script | Bug |
|---|---|
| `speed_synced.py` | Lag search initialised its best score to **−9**, which no correlation can exceed, so the screen filtered nothing. Results void. |
| `blackout_eval.py` | Stepped every 0.5 s while each prediction covered 2.0 s — a **4× overcount**. Produced the retracted 67.6% figure. |

---

## Where the outputs go

```
data/clean/*.parquet        72 drives, 49 columns
data/manifest.csv           per-drive metadata
data/sessions.csv           per-session detail
data/alignment.csv          final lags (total_lag)
data/frame_validation.csv   alignment engine grading
out/per_driver_drift.csv    benchmark results by driver
out/plots/*.png             drift figures
out/IDR_architecture.drawio pipeline diagram
```

Reports that cite these scripts live in `data/report/`.
