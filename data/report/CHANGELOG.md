# From raw IO-VNBD to `data/clean/` — every change, and why

Complete provenance record. Each entry states **what changed**, **what it affected**, and
**why**. Read alongside `README.md`, which describes the resulting data rather than how it
got there.

**Guiding principle throughout:** the phone's sensor readings are never modified. They are
what a real phone in a real vehicle actually produced, noise and faults included. Only the
*labels* are corrected, and only where they are demonstrably wrong. Everything else is
**additive** — new columns beside the originals, never in place of them.

Scripts: `analysis/clean_dataset.py` → `analysis/enrich_dataset.py`.
Supporting audits: `analysis/audit.py`, `analysis/gap_dist.py`, `analysis/sync_v2.py`.

---

## Stage 0 — Acquisition

### 0.1 · Cloned via Git LFS

**Affected:** all 564 CSVs, 2.06 GB.
**Why:** the repository stores CSVs as LFS pointers. A plain `git clone` yields 134-byte
stubs. `git-lfs` was installed to `~/.local/bin` without sudo.

### 0.2 · Used the *Uncategorised* folder as the single source

**Affected:** 72 S/V pairs kept; the parallel *Categorised* tree ignored as a source.
**Why:** both folders contain the **same drives**, organised two ways — flat, and grouped by
driver. Reading both would have doubled every drive. The Categorised tree is still read, but
only to recover which driver recorded which file.

---

## Stage 1 — Cleaning (`clean_dataset.py`)

### 1.1 · Read as latin-1 rather than UTF-8

**Affected:** all 72 files.
**Why:** headers contain `m/s²`. Under UTF-8 the byte `0xB2` raises `UnicodeDecodeError` and
the file will not load at all. This is the first thing that stops anyone using this dataset.

### 1.2 · Matched V-filenames case-insensitively

**Affected:** **40 of 72 pairs.**
**Why:** `S-Vta2.csv` pairs with `V-vta2.csv`. Exact-name matching silently finds no partner
and drops over half the dataset without an error.

### 1.3 · Unified gyroscope column names

**Affected:** all 72 files in this folder use `GYROSCOPE X/Y/Z`; the Categorised copies use
`GYROSCOPE Yaw/Pitch/Roll`.
**Why:** same data, two names. Code written against one folder fails silently against the
other. Both spellings are now accepted and mapped to `gx/gy/gz`.

> The `Yaw/Pitch/Roll` labels are also **misleading**: vehicle yaw does not land on the axis
> called "Yaw". Measured against the vehicle's own yaw-rate sensor, the best single-axis match
> in drive `S1` was the column named *Pitch* (r = 0.935) while *Yaw* gave 0.07. Do not trust
> the axis names — estimate the mapping from data.

### 1.4 · Truncated each pair to the shorter of the two files

**Affected:** **9 pairs**, 298 rows discarded in total (largest: `Vfa02`, 232 rows).
**Why:** phone and vehicle recordings stop at slightly different moments. Rows past the end of
the shorter file have no counterpart, so they cannot be labelled or verified.

### 1.5 · Renamed columns to short SI names

**Affected:** every column, all 72 drives.
**Why:** `ACCELEROMETER X (m/s²)` → `ax`. Units then live in `README.md` instead of inside
column names, where they cannot be typed reliably or parsed.

### 1.6 · Converted units to SI

**Affected:** `yaw_rate` (deg/s → rad/s), `lon_acc` and `lat_acc` (g → m/s²), all 72 drives.
**Why:** the phone gyroscope reports rad/s while the vehicle reports deg/s. Mixing them is a
57× error waiting to happen. Everything is now SI.

### 1.7 · Dropped rows with unusable IMU or speed

**Affected:** **0 rows.** The filter is retained as a guard.
**Why:** rows without sensor data or without a label cannot be trained on. In practice the
surviving files contain no such rows.

### 1.8 · Kept every drive — including short and stationary ones

**Affected:** 17 drives that an earlier pass had discarded (15 shorter than 60 s, 2 where the
vehicle never moved) are now retained and flagged instead.
**Why:** *reversed after review.* The two stationary drives are the best available data for
measuring sensor bias and training stationary detection — exactly what the algorithm needs.
Short drives are small but not worthless. Filtering belongs at use time, not in the archive.

### 1.9 · Added `t_s`

**Affected:** all 72 drives.
**Why:** convenience time axis, `row_index / 10`. Superseded by `t_raw_s` where the two
disagree — see 2.1.

### 1.10 · Recorded `driver` per drive

**Affected:** all 72 drives — A (6), B (1), D (1), E (64).
**Why:** read from the Categorised folder names. Required, because the data must be split by
driver, never randomly.

### 1.11 · Measured phone↔vehicle time agreement (`sync_r`, `lag_s`)

**Affected:** measured on 57 drives; 15 too short or too still to test.
**Result:** only **4 drives score ≥ 0.9**, 2 more between 0.7 and 0.9, and **51 fall below 0.7**.
**Why:** the phone gyroscope and the vehicle's yaw-rate sensor measure the same physical
rotation, so they should track each other. Sliding one against the other over ±30 s reveals
both the offset (`lag_s`) and whether the pair is trustworthy at all (`sync_r`).

Measured impact: training on unshifted data gives correlation **0.02**; on sync-verified data,
**0.46**. This is the largest single factor found in the dataset.

> Measured with a **three-axis** fit, not a single axis. A tilted phone splits vehicle yaw
> across two or three gyro axes, so a single-axis test mistakes *orientation* for *desync* —
> drive `S2` scores 0.005 on one axis and **0.929** using all three.

**No lag correction has been applied.** The values are recorded; the decision is open.

---

## Stage 2 — Enrichment (`enrich_dataset.py`)

All additive. No existing column was modified.

### 2.1 · `session`, `t_raw_s` — recording discontinuities

**Affected:** **7 drives** split into multiple sessions — `S2`, `S3b`, `S4`, `M`, `Y1`,
`Vta17`, `Vtb1`. 83 sessions across 72 drives.
**Why:** some files concatenate separate recordings. In `S3b` the phone's clock runs
*backwards*; `Vtb1` contains an **11-minute hole**. A window spanning such a break pairs
sensor data from one moment with a label from another — pure noise presented as truth.

**Threshold, and how it was chosen.** Sample intervals cluster at 100 ms (99.999th percentile
119 ms). Only **3 intervals out of 1,070,673** exceed 150 ms — they are 1.28 s, 1.37 s and
661 s — plus 8 points where time runs backwards. Since nothing falls between 0.12 s and
1.28 s, *any* threshold in that range gives identical segmentation. 0.5 s was taken from that
empty band. The number is read off the data, not argued from device behaviour.

> **Rule: no training window may cross a session boundary.**

### 2.2 · `speed_best`, `speed_src` — labels that survive GNSS dropouts

**Affected:** 0.01% of samples on average; most in `S3c` (0.4%). 4 drives have real dropouts.
**Why:** `speed_kmh` comes from GPS and freezes when the receiver loses lock, then snaps back.
Those snaps reach 15 km/h in 0.1 s — **4.2 g**, impossible for a car, so they are receiver
artifacts, not driving. `can_speed` is wheel-derived and immune. The two agree at r = 0.9993.

`speed_best` therefore uses GPS normally and substitutes CAN where the fix is frozen while
moving, or where an impossible jump occurs.

**CAN is offset-corrected first** (median −0.22 km/h) so switching source injects no false
speed change at the splice — an uncorrected splice would create a fake acceleration spike
exactly where the model is being taught what acceleration looks like.

> These stretches are **real GNSS outages with valid ground truth throughout** — precisely
> the scenario the benchmark measures. Small in volume, disproportionately valuable.

### 2.3 · `gnss_dropout`

**Affected:** 4 drives.
**Why:** marks where GPS lost lock while the vehicle was moving (position frozen ≥ 5 samples,
CAN speed > 3 km/h). Requiring *motion* matters: an earlier pass flagged 17 drives, but most
were frozen positions on a **stationary vehicle**, which is correct behaviour, not a fault.

### 2.4 · `gx_c`, `gy_c`, `gz_c` — bias-removed gyroscope

**Affected:** all 72 drives. Median bias 0.0005 rad/s; **worst 0.062 rad/s**.
**Why:** a gyroscope reads non-zero when perfectly still, and that offset integrates straight
into heading error. The median case costs ~1.7° per minute — tolerable. The worst drive costs
**214° per minute** — unusable uncorrected.

Bias is the **median** reading below 0.5 km/h, computed **per session** because it drifts with
temperature. Median rather than mean, since the mean is skewed by the phone being handled — an
earlier mean-based estimate reported 0.0047 rad/s, nearly 10× too high.

Raw `gx/gy/gz` are untouched. This is not data modification: the engine must estimate and
remove this bias at runtime regardless. Precomputing it just avoids repeating the work.

### 2.5 · `stationary`

**Affected:** 9.8% of samples on average.
**Why:** below 1 km/h for at least 2 s. Enables ZUPT — resetting velocity to exactly zero at
each stop, which also gives a free bias re-measurement. The 2-second minimum prevents
flickering at crawl speeds.

### 2.6 · `stuck`

**Affected:** 0.29% of samples on average; **20.4% in `Vtb1`**, under 1% everywhere else.
**Why:** flags samples inside a run of ≥ 5 identical consecutive readings — a sensor repeating
stale data rather than measuring. `Vtb1` includes 34.5 consecutive seconds of frozen gyro-X.
Integrating stale data produces confident, wrong motion.

### 2.7 · `split` — train / test / stress

**Affected:** 70 train, 1 test (`Y1`), 1 stress (`Vtb1`).
**Why:** two held-out drives serving different purposes, neither trained on.

`Y1` is driver D, **held out entirely** — normal realistic driving, so its number measures
generalisation to an unseen driver. This is the headline figure.

`Vtb1` is the worst data in the set and its driver (E) **remains in training** deliberately, so
its number isolates the effect of the *damage* rather than confounding it with an unfamiliar
driver. A robustness figure, never quoted as the headline.

---

## Considered and deliberately not done

### `|accel|` reads 10.10 m/s², not 9.81 — left alone

Looks like a 3% scale error and is not one. The magnitude of a noisy vector is always biased
upward: at this sensor's noise level the expected value is ~10.05, and the drives reading
10.2–10.4 are simply the faster, bumpier ones. **Do not "correct" this** — it would break the
scale to fix a non-problem.

### Damaged drives not deleted

`Vtb1` could be dropped. It is kept, because a phone with a stuck sensor and a receiver outage
is a real condition the system must survive rather than a condition to define away.

### Dead columns not removed

`gear` is constant in 48/72 drives, `steer_deg` in 12, `phone_gps_acc` in 10. Kept: they cost
almost nothing, and re-cleaning to recover a column later is far more expensive than carrying it.

### Sensor readings never modified

No smoothing, no outlier removal, no gap filling on `ax/ay/az/gx/gy/gz/mx/my/mz`. Vibration,
spikes and noise are the operating environment. A model trained on sanitised input will fail
on real input.

### `lag_s` measured but not applied

The offsets are recorded, not corrected. Applying them changes the phone↔label alignment on
most drives — a decision with real consequences that belongs to whoever trains the model.

---

## Where it ended up

```
72 drives · 29.7 h · 1,341 km · 1,070,741 samples · 43 columns · 102 MB
   train  70 drives  26.9 h  1241 km   drivers A, B, E
   test    1 drive    2.0 h    59 km   driver D
   stress  1 drive    0.9 h    42 km   driver E
```

Nothing from the original recordings was deleted. 298 rows were discarded by pair truncation
(0.03%), and no drive was dropped.

## Still open

1. **Sync.** Shift each drive by its `lag_s`, or keep only high-`sync_r` drives. Blocking:
   `Y1` has `sync_r = 0.068`, so the test set cannot be scored until this is settled.
2. **Whether `Vtb1` belongs in training at all** — currently `stress`, excluded.
