# Cleaned IO-VNBD

72 drives · 29.7 h · 1,341 km · 1,070,741 samples · **10 Hz throughout**

One `.parquet` per drive in `clean/`, described by `manifest.csv`.
Nothing was discarded — degraded drives are **flagged, never deleted**, because a
cheap phone in a real vehicle on a bad day is exactly what this system must survive.

```python
import pandas as pd
d = pd.read_parquet("data/clean/S1.parquet")
m = pd.read_csv("data/manifest.csv")
```

---

## Where the columns come from

Two devices recorded every drive at once: an **Android phone** in a holder, and the
**vehicle's own instrumentation** (VBOX GPS + CAN bus).

> **Phone columns are the model's input. Vehicle columns are the training labels.**
> Vehicle columns must never reach the model at runtime — the problem statement
> forbids any connection to the vehicle's computer. They are the teacher, not the student.

### Phone — model input

| Column | Unit | Notes |
|---|---|---|
| `ax` `ay` `az` | m/s² | accelerometer, **includes gravity** |
| `gx` `gy` `gz` | rad/s | gyroscope, raw |
| `gx_c` `gy_c` `gz_c` | rad/s | gyroscope, **bias removed** (see below) |
| `mx` `my` `mz` | µT | magnetometer — heavily distorted inside a steel car body |
| `t_s` | s | nominal time, `row_index / 10` |
| `t_raw_s` | s | the phone's actual clock — use this, not `t_s`, where they disagree |
| `session` | int | recording-session id (see below) |

### Vehicle — ground truth

| Column | Unit | Notes |
|---|---|---|
| `speed_best` | km/h | **use this as the training label** |
| `speed_src` | str | `gps` / `can` / `gps_only` — which source `speed_best` came from |
| `speed_kmh` | km/h | VBOX GPS speed, raw. Freezes during GNSS dropouts |
| `can_speed` | km/h | CAN bus speed, raw. Immune to GNSS |
| `lat` `lon` | deg | VBOX GPS position |
| `heading` | deg | true heading, 0 = north |
| `yaw_rate` | rad/s | true turn rate — used for alignment and sync checking |
| `lon_acc` `lat_acc` | m/s² | true forward / sideways acceleration |
| `ws_fl` `ws_fr` `ws_rl` `ws_rr` | rad/s | wheel speeds — **labels only, never an input** |
| `steer_deg` | deg | steering angle |
| `engine_rpm` | rev/min | useful for idle detection |
| `brake` | 0/1 | brake applied |
| `gear` | 1–5 | constant in 48/72 drives — mostly unusable |

### Derived flags

| Column | Type | Meaning |
|---|---|---|
| `stationary` | bool | below 1 km/h for at least 2 s. Use for ZUPT and bias estimation |
| `gnss_dropout` | bool | GPS lost lock while the vehicle was moving |
| `stuck` | bool | sensor repeating a stale reading (≥5 identical consecutive samples) |

### Phone GPS — reference only

`phone_lat` `phone_lon` `phone_speed` `phone_gps_acc` — updates roughly **every 9 s** in
most drives, so it is useless as ground truth. Kept for comparison only.

`grav_x` `grav_y` `grav_z` — Android's *fused* gravity estimate. **Not a real sensor.**
Vendor-specific black box; a model leaning on it will not transfer between phones.

---

## The four derived quantities, and how they were computed

### `session` — recording discontinuities

Some files are multiple recording sessions concatenated. In one drive the phone's clock
runs *backwards*; in another there is an **11-minute hole**. A training window spanning
such a break pairs sensor data from one moment with a label from another.

Sample intervals cluster tightly at 100 ms (99.999th percentile = 119 ms). Only **three
intervals out of 1,070,673** exceed 150 ms — they are 1.28 s, 1.37 s and 661 s — plus 8
points where time runs backwards.

A new session starts at any negative jump or any interval **> 0.5 s**. Because no
interval falls between 0.12 s and 1.28 s, *any* threshold in that range gives identical
segmentation — the number is read off the data, not chosen.

**Result:** 83 sessions across 72 drives. 7 drives are split: `S2`, `S3b`, `S4`, `M`,
`Y1`, `Vta17`, `Vtb1`.

> **Rule: no training window may cross a session boundary.**

### `speed_best` — ground truth that survives GNSS dropouts

`speed_kmh` comes from GPS, so it freezes when the receiver loses lock and then snaps
back. Those snaps reach 15 km/h in 0.1 s — that is 4.2 g, physically impossible for a
car, so they are receiver artifacts rather than driving.

`can_speed` is wheel-derived and unaffected by GNSS. The two agree at r = 0.9993.

So `speed_best` uses GPS normally and substitutes CAN wherever the fix is frozen while
moving, or where an impossible jump occurs. CAN is offset-corrected first (median
−0.22 km/h) so switching sources injects no false speed change at the splice.

**Result:** CAN is used for 0.01% of samples on average (max 0.4%, drive `S3c`). Small,
but it lands exactly on the GNSS-outage stretches — the scenario the benchmark measures.

### `gx_c` `gy_c` `gz_c` — bias-removed gyroscope

A gyroscope reads slightly non-zero even when perfectly still, and that offset integrates
straight into heading error. Bias is the **median** reading across samples below
0.5 km/h, computed **per session** (it drifts with temperature, so one estimate per file
is not enough). Falls back to drive-level, then to zero, if a session has fewer than 50
stationary samples.

**Result:** median bias 0.0005 rad/s — about 1.7° of heading error per minute, tolerable.
But the worst drive reaches 0.062 rad/s, which is **214° per minute**. Uncorrected, that
drive is unusable.

Raw `gx/gy/gz` are untouched. The per-drive maximum is in `manifest.csv` as `gyro_bias_max`.

### `stuck` — stale sensor readings

Only one drive is meaningfully affected: **`Vtb1`**, at 20.4% of samples, including 34.5
consecutive seconds of frozen gyro-X. Every other drive is below 1%. `Vtb1` also holds the
661 s gap and 39 GPS reacquisition jumps — keep it as a degradation stress test, not as
training data.

---

## manifest.csv

| Column | Meaning |
|---|---|
| `drive` | matches the parquet filename |
| `driver` | A, B, D or E — **split on this** |
| `split` | `train` / `test` |
| `n`, `minutes`, `km` | size |
| `v_mean`, `v_max`, `pct_moving` | speed summary |
| `sync_r` | phone↔vehicle time agreement. **1.0 trustworthy, near 0 broken** |
| `lag_s` | seconds the phone data is offset from the vehicle data |
| `sessions` | recording sessions in this drive |
| `pct_can_label` | % of labels taken from CAN instead of GPS |
| `can_offset_kmh` | GPS−CAN offset applied at the splice |
| `pct_dropout`, `pct_stationary`, `pct_stuck` | flag coverage |
| `gyro_bias_max` | largest per-axis bias, rad/s |
| `flags` | `stationary`, `short`, `sync-untestable`, or empty |

---

## Three standing rules

**1. Split by driver, never randomly.** Windows overlap heavily, so a random split puts
near-identical windows in both train and test and leaks the answer. Results look
excellent and mean nothing.

**2. Never cross a session boundary.** See `session` above.

**3. Two drives are held out, for two different purposes.** Neither is trained on.
Evaluation must recompute anything derived rather than read the convenience columns —
otherwise the held-out data gets information the real engine would not have.

| `split` | Drive | Driver in training? | What its number proves |
|---|---|---|---|
| `test` | `Y1` | **no** — driver D held out entirely | generalises to an unseen driver under normal conditions. **This is the headline number.** |
| `stress` | `Vtb1` | yes — driver E is in training | survives degraded hardware. **A robustness number, never quoted as the headline.** |

`Y1` is ordinary realistic driving: 2 h, 58 km, genuine GNSS dropouts, 4 recording
sessions, `sync_r = 0.068`. Hard, but nothing pathological.

`Vtb1` is the worst data in the set: 20.4% stuck samples, 34.5 consecutive seconds of
frozen gyro-X, a 661 s recording gap, and 39 GPS reacquisition jumps. Its driver is
deliberately left in training so the result isolates the effect of the *damage* rather
than confounding it with an unfamiliar driver.

> ⚠️ Driver D has only **one** drive, so `test` is a thin single-drive holdout.
> Consider leave-one-driver-out across all four drivers as well, reporting the worst fold.

---

## Two decisions still open

1. **Sync.** Many drives are time-offset from their vehicle data (`sync_r`, `lag_s`).
   Either shift each drive by its `lag_s`, or keep only high-`sync_r` drives. Training on
   unshifted low-`sync_r` data pairs sensor readings with the wrong moment's speed —
   measured effect: correlation drops from 0.46 to 0.02.
2. **Whether to train on `Vtb1`.** It is genuinely damaged. Recommended as an evaluation
   stress case rather than training data.

---

## What was *not* changed, and why

`|accel|` reads ~10.10 m/s² across the dataset rather than 9.81. This looks like a 3%
calibration error and is not one — the magnitude of a noisy vector is always biased
upward, and 10.05 is the expected value at this sensor's noise level. The drives reading
10.2–10.4 are simply the faster, bumpier ones. **Do not "correct" this.**
