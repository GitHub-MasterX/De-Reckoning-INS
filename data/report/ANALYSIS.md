# IO-VNBD analysis report

What was found in the dataset, what went wrong, and how each problem was solved.

**Outcome:** usable training material went from an apparent **6 drives** to **13.5 h verified
plus 13.5 h usable-noisy**, across all four drivers, with no data discarded.

---

## 1. What the dataset actually is

Measured from the files, not read from the paper.

| | |
|---|---|
| Sample rate | **10 Hz** — phone IMU and vehicle ECU alike, confirmed on all 144 pairs |
| Phone GPS | ~**9 s** between fixes in 124 of 144 files — useless as ground truth |
| Vehicle GPS (VBOX) | **10 Hz** — this is the ground truth |
| Recording | 3 phones (Huawei P20 Pro, Moto G7 Power, BlackBerry Priv) in holders |
| Scale | 72 drives, 29.7 h, 1,341 km, 1.07 M samples |
| Drivers | A (6 drives), B (1), D (1), E (64) |

Two speed sources exist and agree closely — VBOX GPS and CAN bus, **r = 0.9993**, bias
0.26 km/h. That redundancy turned out to matter: CAN is immune to GNSS dropouts.

---

## 2. The central question

The phone file and the vehicle file must describe **the same moments**. If they don't, every
sensor reading is paired with the wrong answer and nothing can be learned from it.

The test used throughout: the phone's **gyroscope** and the car's **yaw-rate sensor** both
measure one physical thing — the car turning. If the files line up, the two traces track each
other. Correlation between them (`sync_r`) measures alignment; the shift that maximises it
(`lag_s`) measures the offset.

Measured impact, before any fixes: training on unaligned data gave **r = 0.017**. On aligned
data, **r = 0.455**. Alignment is the single largest factor in the dataset.

---

## 3. Problems solved, in the order they appeared

### 3.1 · The file won't even open

`UnicodeDecodeError` on all 72 files — headers contain `m/s²`, and byte `0xB2` is invalid
UTF-8. **Fix:** read as latin-1.

### 3.2 · Half the dataset silently disappears

`S-Vta2.csv` pairs with `V-vta2.csv`. Exact-name matching finds no partner and drops the
file with **no error raised**. **Affected 40 of 72 pairs.** **Fix:** case-insensitive matching.

### 3.3 · Column names differ between folders

`GYROSCOPE X/Y/Z` in one folder, `GYROSCOPE Yaw/Pitch/Roll` in another — same data. Code
written against one fails silently against the other.

Worse, the `Yaw/Pitch/Roll` names are **wrong**: vehicle yaw does not land on the axis
called "Yaw". In drive `S1`, the column named *Pitch* matched vehicle yaw at **r = 0.935**
while *Yaw* gave **0.07**. **Fix:** accept both spellings, and never trust axis names —
estimate the mapping from data.

### 3.4 · A single axis mistakes orientation for desync

The first sync test used the best *single* gyro axis. But a tilted phone splits vehicle yaw
across two or three axes, so no single axis matches — which looks identical to a broken file.

| Drive | Best single axis | Three-axis fit |
|---|---|---|
| `S2` | **0.005** | **0.929** |
| `S3a` | 0.200 | 0.972 |

`S2` looked completely broken and was perfectly fine, merely rotated.
**Fix:** fit all three axes jointly (least squares) before correlating.

### 3.5 · One file, several recordings

Some files concatenate separate recording sessions. In `S3b` the phone's clock runs
**backwards**; `Vtb1` contains an **11-minute hole**. Any quantity computed across the whole
file averages over unrelated recordings and is wrong for all of them.

Sample intervals cluster at 100 ms (99.999th percentile 119 ms). Only **3 of 1,070,673**
exceed 150 ms — 1.28 s, 1.37 s and 661 s — plus 8 negative jumps. Because nothing falls
between 0.12 s and 1.28 s, any threshold in that gap gives identical segmentation; **0.5 s**
was taken from that empty band. The number is read off the data, not argued from theory.

**Result — 83 sessions across 72 drives, and computing per session instead of per file:**

| Drive | Whole file | Per session |
|---|---|---|
| `M` | 0.811 | **0.932 / 0.993 / 0.984** (lags +0.8 s, +2.0 s, +3.2 s) |
| `S3b` | 0.720 | **0.834 / 0.998** |
| `S4` | 0.347 | **0.932** / 0.059 / 0.183 |
| `Vtb1` | 0.428 | **0.915** / 0.416 |

`M`'s three sessions each had a *different* offset. Averaging them destroyed all three.

> **`S4` is the clearest case: session 0 needs +1.8 s, session 1 needs +313.8 s. Same file.**
> Correcting it as a whole wrecks both.

### 3.6 · Some drives have too few turns to verify

The gyro test needs turning. A motorway run has almost none — `Vw14b` has **0%** of samples
above 0.1 rad/s. Low `sync_r` there is *absence of evidence*, not evidence of a problem.

The relationship is measurable: `sync_r` correlates **+0.599** with yaw variability and
**+0.515** with time spent turning.

| Band | Median yaw std | % turning |
|---|---|---|
| r > 0.9 | 0.135 | 21% |
| r 0.3–0.5 | 0.066 | 6.7% |
| r < 0.3 | 0.025 | 0.05% |

**Attempt 1 — switch from gyroscope to accelerometer.** A straight drive still brakes and
accelerates, so phone acceleration was fitted against the vehicle's longitudinal acceleration
instead of turn rate.

**This largely failed.** Of 18 sessions tested, only **2** reached r ≥ 0.7 and 11 reached
r ≥ 0.3. Phone longitudinal acceleration is contaminated by vehicle pitch and gravity, making
it a far weaker alignment signal than rotation.

One useful result did emerge: on `Vfa02` the accelerometer put the lag at **+8.8 s** and the
gyro at **+8.5 s**. Two independent methods agreeing is stronger evidence than either
correlation alone.

**Attempt 2 — align the GPS tracks directly.** This worked, and works on *every* session
regardless of how much it turns. See 3.7.

### 3.7 · The search window was too narrow — the largest error in this analysis

Two sessions scored ~0.06 and were declared dead: `Y1/s3` (111 min — the intended **test
set**) and `S4/s1` (93 min). Both had plenty of turning, so "too few turns" did not apply.

Comparing the phone's GPS track against the vehicle's GPS track:

| Session | Separation |
|---|---|
| `S1/s0` (healthy control) | **24 m** |
| `Y1/s3` | **648 m** |
| `S4/s1` | **1,846 m** |

The first reading was "different journeys — mispaired files." That was wrong. At 30 km/h,
648 m is about 110 seconds of driving. **The offsets were larger than the ±30 s being
searched.** Widening the search to ±10 minutes:

| Session | Offset found | Separation after | `sync_r` before → after |
|---|---|---|---|
| `Y1/s3` | **+111 s** | 648 m → **16 m** | 0.058 → **0.798** |
| `S4/s1` | **+309 s** | 1,846 m → **18 m** | 0.059 → **0.928** |

Nothing was broken. **6.0 hours recovered**, including the test set.

---

## 4. The two-stage alignment procedure

Neither stage alone is sufficient.

```
COARSE   match the two GPS tracks over ±10 min
         finds large offsets (111 s, 309 s, 564 s)
         resolution only ~±5 s — phone GPS updates every 9 s

FINE     match gyro against vehicle yaw-rate over ±30 s
         refines to sub-second
         blind to anything beyond its ±30 s window
```

**Overall effect:**

| Threshold | Before | After |
|---|---|---|
| \|sync_r\| ≥ 0.9 | 9.8 h | **11.3 h** |
| \|sync_r\| ≥ 0.7 | 10.1 h | **13.5 h** |
| \|sync_r\| ≥ 0.5 | 13.2 h | **16.6 h** |

---

## 5. Three hypotheses tested and rejected

Driver E's 66 sessions align well by GPS (20–38 m, same as healthy drives) yet only reach
gyro correlation ~0.5. Three explanations were tested:

| Hypothesis | Test | Result |
|---|---|---|
| **Clock drift** — phone and VBOX oscillators diverging, so a constant shift can't work | measured the phone's true sample interval per session | ✗ **0.10000 s, ~0 ppm.** No drift. Lag is constant within a session |
| **Phone shifted in its holder** — rotation changing mid-drive | fitted the phone→vehicle rotation per 5-minute window | ✗ `S3c` swings **28.9°** and scores 0.95; `Vw4` swings 10.4° and scores 0.57 |
| **A worse phone** — three devices were used | noise floor and ADC quantisation step at standstill | ✗ Driver E's gyro is *quieter* (0.029 vs A's 0.046), identical 0.0001 quantisation — same chip |

The drift model was worth checking explicitly. If the phone sampled at 100.2 ms against the
VBOX's 100.0 ms, then `L(t) = L₀ + εt` with ε = 2000 ppm gives ~25 s of drift over a
211-minute session — easily enough to destroy alignment. Measured ε ≈ 0, so the constant
per-session lag is the complete correction and there is no slope to fit.

**This remains unexplained.** But the GPS tracks prove the pairing and timing are correct, so
the data is valid — just noisier.

---

## 6. Other findings

**Ground truth survives GNSS dropouts.** `speed_kmh` freezes when GPS loses lock, then snaps
back at up to 15 km/h per 0.1 s — **4.2 g**, impossible for a car, so a receiver artifact.
`can_speed` is wheel-derived and unaffected. `speed_best` substitutes CAN on those stretches,
offset-corrected first so the splice injects no false acceleration.

An earlier pass reported 17 drives with ground-truth glitches. Requiring the vehicle to be
**moving** cut that to **4** — most frozen positions were stationary vehicles, which is
correct behaviour.

**Gyro bias is real but modest.** Median 0.0005 rad/s (≈1.7° of heading error per minute),
worst **0.062 rad/s** (≈214° per minute, unusable uncorrected). Estimated per session, since
it drifts with temperature. Median rather than mean — a mean-based estimate came out **10×
too high**, skewed by the phone being handled.

**`|accel|` reads 10.10 m/s², and that is correct.** It looks like a 3% calibration error. It
is not: the magnitude of a noisy vector is always biased upward, and ~10.05 is the expected
value at this noise level. Drives reading 10.2–10.4 are simply the faster, bumpier ones.
**Do not "correct" this.**

**One drive is genuinely damaged.** `Vtb1`: 20.4% stuck samples, 34.5 consecutive seconds of
frozen gyro-X, a 661 s gap, 39 GPS reacquisition jumps. Every other drive is under 1% stuck.
Kept as a degradation stress test.

---

## 7. Preliminary model results

Small, and two of the three carry caveats.

| Experiment | Result | Status |
|---|---|---|
| Absolute speed from IMU | MAE **18.7 km/h** (dummy 26.5) | Valid — the approach fails, as expected |
| Speed change, unaligned data | r = **0.017** | Valid |
| Speed change, aligned data | r = **0.455** | Valid — alignment is what makes it learnable |
| 60 s blackout drift | 67.6% | **Invalid** — evaluator bug, see below |

Absolute speed is not recoverable from a 10 Hz IMU and never was the plan: GNSS supplies
velocity at the moment of blackout, and the model only tracks how it *changes* from there.

---

## 8. Errors made during this analysis

Recorded because each one is a trap the next person will otherwise fall into.

| Error | Consequence | Fix |
|---|---|---|
| Lag search initialised its best score to **−9** | no correlation can exceed 9, so nothing ever beat it — the screen ran and filtered nothing | initialise to 0 |
| Evaluator stepped every **0.5 s** while each prediction covered **2.0 s** | overlapping windows counted 4×, inflating drift | match prediction interval to step |
| Lag searched only **±30 s** | 6 h declared dead, including the test set | coarse GPS stage first, ±10 min |
| Ground-truth glitches counted without requiring motion | 17 drives flagged; really **4** | require `can_speed > 3` km/h |
| Gyro bias from the **mean** | 10× overestimate | use the median |
| Sync screened on a **single** gyro axis | orientation mistaken for desync (`S2`: 0.005 vs 0.929) | fit all three axes |
| 17 drives dropped as too short or stationary | lost the best bias-estimation data | keep everything, flag instead |

---

## 9. Where it stands

| Driver | Drives | Total | Verified | Noisy | Role |
|---|---|---|---|---|---|
| **A** | 6 | 8.6 h / 275 km | **8.5 h** | — | Primary training |
| **B** | 1 | 2.9 h / 105 km | **2.9 h** | — | Test — headline number |
| **D** | 1 | 2.0 h / 59 km | **1.9 h** | — | Test — second holdout |
| **E** | 64 | 16.3 h / 902 km | 0.2 h | **13.5 h** | Bulk training + stress |

**Rules that came out of this:**

1. Split by driver, never randomly
2. Never cross a session boundary
3. Apply lag **per session**, never per file
4. Noisy data trains, clean data grades
5. Never trust an axis name — estimate the mapping

**Still to do:** apply `total_lag` to the files, fix the evaluator, re-baseline.

*See `PLAN.md` for tasks, `CHANGELOG.md` for what changed in the data, `COLUMNS.md` for the
column reference.*
