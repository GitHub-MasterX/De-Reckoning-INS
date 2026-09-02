# De-Reckoning-INS

**AI-ML based Intelligent Dead Reckoning for GNSS-denied navigation**
Smart India Hackathon 2026 · Problem Statement **26168** (ISRO)

Keeping a vehicle's position accurate on a dashboard-mounted smartphone when GNSS drops —
in a tunnel, an underpass, a multi-level car park or a deep urban canyon — using only the
phone's own inertial sensors and an offline map.

---

## Results

| Benchmark | Result | |
|---|---|---|
| **5 m drift over 50 m** | **1.3 – 2.6 m** | ✅ met on **all four** drivers |
| **100 m drift over 1 km** | **102 m** (driver E) | misses by 1.8 m under the PS's stated conditions |
| | 161 – 196 m (urban drivers) | |
| **Motion classifier** | **99.4%** | leave-one-driver-out, IMU only |

The problem statement specifies *"100 m over 1 km at a speed of 60 kmph in tunnels."* Driver E
is that condition — steady ~60 km/h, continuous flow — and reaches **10.2% drift**, stable out
to 1.5 km. Urban stop-start driving reaches 16–20%, for reasons documented in
[`ML_MODEL_REPORT.md`](data/report/ML_MODEL_REPORT.md).

---

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 run_evaluation.py          # ~15 s — reproduces every number and figure
```

No retraining. The script loads the saved models and cached features, evaluates drift for all
four drivers at the benchmark distances, scores the classifier, and writes four figures to
`out/plots/`.

---

## What's here

```
run_evaluation.py        one command → all results and figures
requirements.txt         pinned — sklearn pickles are version-sensitive
idr/features.py          THE FEATURE CONTRACT — 26 features, exact order
models/                  trained models + cached features (see below)
analysis/                12 live scripts + 29 archived investigations
data/report/             8 reports
out/                     results, figures, architecture diagram
```

### `models/`

| File | Contents |
|---|---|
| `motion_models.pkl` | six models — one per held-out driver, one 75/25 split, one deployment |
| `features_motion.npz` | 171,440 windows × 26 features (classifier training) |
| `eval_cache.npz` | 182,780 windows with session boundaries and true speed (blackout simulation) |
| `metadata.json` | every score, split definition, and the feature contract |

> `deploy_all` is trained on every driver — **ship it, never quote its own accuracy.** The
> honest figures come from the held-out models.

### `data/report/`

| Document | |
|---|---|
| [`ML_MODEL_REPORT.md`](data/report/ML_MODEL_REPORT.md) | the full report — models, difficulties, per-driver analysis |
| [`BOTTLENECK.md`](data/report/BOTTLENECK.md) | why 10 Hz cannot meet the 1 km benchmark, with the physics |
| [`ANALYSIS.md`](data/report/ANALYSIS.md) | the investigation narrative, including what was retracted |
| [`EXECUTION_LOG.md`](data/report/EXECUTION_LOG.md) | every script: why it ran, what it resolved, what it didn't |
| [`REFERENCES.md`](data/report/REFERENCES.md) | 16 verified references with authority notes |
| [`COLUMNS.md`](data/report/COLUMNS.md) · [`CHANGELOG.md`](data/report/CHANGELOG.md) · [`PLAN.md`](data/report/PLAN.md) | data reference, provenance, per-driver roles |

---

## Key findings

**The gyroscope works. The accelerometer does not.**

| Channel | Measured against the vehicle's own sensors |
|---|---|
| Rotation (yaw rate) | **r = 0.958** — alignment engine at 100% of its theoretical ceiling |
| Forward acceleration | **ceiling r = 0.315** — and 0.05 on one drive |

Speed change comes from forward acceleration, so this is the binding constraint. Two
independent approaches — machine learning and direct physics — failed on the same channel.

**The physical limit, derived rather than asserted:**

```
required accuracy on mean acceleration   0.028 m/s²
random noise over 600 samples            0.020 m/s²   ✓ fine
bias does not average out  →  gravity leak sets the wall:
        θ = 0.028 / 9.81  =  0.16°  of pitch accuracy, continuously
```

At 10 Hz, vibration at 10–100 Hz **folds into** the 0–5 Hz band where the signal lives —
contaminated, not merely noisy, and no filter can separate them. See
[`out/plots/05_sampling_rates.png`](out/plots/05_sampling_rates.png).

**Where machine learning does help:** classification, not regression. A stopped vehicle is a
large, sustained, structural signature; forward acceleration is a small continuous quantity
buried in noise. The classifier reaches 99.4%; the speed regressor makes drift **worse** than
doing nothing, at every blending weight.

---

## Reproducing from raw data

`data/clean/` (229 MB) and `IO-VNBD/` (3.5 GB) are not committed. To rebuild:

```bash
git clone https://github.com/onyekpeu/IO-VNBD.git
cd IO-VNBD && git lfs pull && cd ..

.venv/bin/python3 analysis/clean_dataset.py     # 1 · raw → parquet
.venv/bin/python3 analysis/enrich_dataset.py    # 2 · derived columns
.venv/bin/python3 analysis/per_session.py       # 3 · per-session sync
.venv/bin/python3 analysis/align_all.py         # 4 · two-stage time alignment
.venv/bin/python3 analysis/add_alignment.py     # 5 · apply lags as new columns
.venv/bin/python3 analysis/align_frame.py       # 6 · phone → vehicle frame
.venv/bin/python3 analysis/train_and_save.py    #     retrain and save
```

See [`analysis/README.md`](analysis/README.md) for what every script does.

---

## Dataset

U. Onyekpe, V. Palade, S. Kanarachos, A. Szkolnik, "IO-VNBD: Inertial and Odometry benchmark
dataset for ground vehicle positioning," *Data in Brief*, vol. 35, art. 106885, 2021.
DOI: [10.1016/j.dib.2021.106885](https://doi.org/10.1016/j.dib.2021.106885) ·
[github.com/onyekpeu/IO-VNBD](https://github.com/onyekpeu/IO-VNBD)

Full reference list with authority notes: [`data/report/REFERENCES.md`](data/report/REFERENCES.md)
