# Intelligent Dead Reckoning for GNSS-Denied Navigation

**Smart India Hackathon 2026 · Problem Statement 26168 (ISRO)**

## Contents

- [Executive Summary](#executive-summary)
- [The Problem, Precisely](#the-problem-precisely)
- [System Architecture](#system-architecture)
- [Mechanism — How the Learned Speed Model Actually Works](#mechanism--how-the-learned-speed-model-actually-works)
- [Challenges Faced, and How Each Was Resolved](#challenges-faced-and-how-each-was-resolved)
- [Results](#results)
- [Honest Limitations](#honest-limitations)
- [References](#references)

---

## Executive Summary

A vehicle's GNSS signal is lost — a tunnel, a dense urban street, a jammed corridor. The phone still has its
accelerometer and gyroscope. The task: keep the vehicle's position tracked using only those sensors and an offline
road map, and return to within roughly 10% of the distance travelled by the time GNSS comes back.

The final system is four layers, each fixing exactly what the layer before it could not — a motion classifier, a
learned speed model, a road-constrained particle filter, and a reporting layer. Full detail in `ARCHITECTURE.md`
and `MECHANISM.md`.

On drivers never used to tune any setting: median path drift **5.9%** of distance travelled, **80–82%** of
blackouts meet the 10% benchmark, cursor teleporting fell from 71% of blackouts to **5%**. On the team's own
recordings — a two-wheeler, hand-held phone, real Tamil Nadu roads, no speed-limit tags in the map at all — 45 of
111 real blackouts meet the same 10% target, and the engine beats a simpler baseline on 85 of 111.

Every number in this report is measured, not estimated, and every failure encountered along the way is reported
alongside the successes — including the ones that are still open. See `CHALLENGES.md` for the full record.

---

---

## The Problem, Precisely

The problem statement specifies **100 m of drift over 1 km at 60 km/h in a tunnel**. More generally: given an
accelerometer and gyroscope sampling continuously, a road map, and the vehicle's last known GNSS fix, produce a
position estimate for the duration of a GNSS blackout that stays close to the true path — without ever seeing
ground truth during the blackout itself.

Why this is hard, physically:

- **The pitch wall.** A phone accelerometer cannot separate gravity from real acceleration below a small tilt
  error. At 60 km/h, a 100 m budget over 1 km demands accelerometer error under 0.028 m/s². A tilt error as small
  as 0.16° already produces a phantom acceleration of ≈0.027 m/s² — at the edge of the entire budget before any
  real vehicle motion is measured. Confirmed by direct static test.
- **Aliasing.** Sampling at 10 Hz sets a Nyquist limit of 5 Hz. Above ≈36 km/h, the sensor does not just lose
  resolution — it misreads the true vibration frequency as a wrong one. Full measurement in `MECHANISM.md`.
- **No CAN bus or OBD access** on a consumer smartphone — every estimate must come from the IMU and the map alone.

---

---

## System Architecture


The final engine is four layers, each fixing exactly what the layer before it could not. Everything branches on
one condition at every sensor tick: is a GNSS fix available right now.

```
Phone sensors (continuous)              GNSS fix, when available
Accelerometer + Gyroscope                        │
  10 Hz (benchmark) / 248 Hz (native)             │
            │                          ┌──────────┴──────────┐
            │                          │  GNSS available?     │
            │                          └─────┬───────────┬────┘
            │                         YES     │           │  NO — blackout
            │              ┌──────────────────┘           └───────────────────┐
            │              ▼                                                  ▼
            │   Raw fix shown directly                     ┌───────────────────────────────┐
            │   Per-phone gyro calibration                 │ Layer 1 — Motion Classifier    │
            │   fit continuously from GNSS history          │ 99.4% held-out accuracy        │
            │                                               │ triggers zero-velocity update  │
            │                                               └───────────────┬───────────────┘
            │                                                               │ if moving
            │                                                               ▼
            │                                               ┌───────────────────────────────┐
            │                                               │ Layer 2 — Learned Speed Model  │
            │                                               │ vibration + jerk + road class  │
            │                                               │ + last-known speed              │
            │                                               └───────────────┬───────────────┘
            │                                                               │ predicted speed
            │                                                               ▼
            │                                               ┌───────────────────────────────┐
            │                                               │ Layer 3 — Particle Filter      │
            │                                               │ 500 hypotheses on the road graph│
            │                                               └───────────────┬───────────────┘
            │                                                               │ particle cluster
            │                                                               ▼
            │                                               ┌───────────────────────────────┐
            │                                               │ Layer 4 — Reporting Layer      │
            │                                               │ mode hysteresis + speed-limited │
            │                                               │ cursor                          │
            │                                               └───────────────┬───────────────┘
            │                                                               │
            └───────────────────────────────┬──────────────────────────────┘
                                             ▼
                              Android UI — one position per tick
```

### Inputs

- Accelerometer + gyroscope, phone MEMS IMU — 10 Hz (benchmark dataset) or 248 Hz (native, own recordings)
- GNSS fix, when available, roughly 1 Hz
- Offline OSM road graph, pre-built as a binary adjacency structure with R-tree spatial indexing

### GNSS available

The raw fix is shown directly as the position. In the background, each phone's own gyroscope axis alignment,
scale, and bias are fit by least-squares against this GNSS history continuously, so the correction is ready the
moment a blackout begins. This mattered directly: one test phone's gyroscope was found to report only ≈54% of
every real turn before this correction.

### GNSS lost — the four-layer dead-reckoning pipeline

**Layer 1 — Motion Classifier.** A gradient-boosted decision tree (26 features over 20-sample windows, hop 5),
trained leave-one-driver-out, 99.4% held-out accuracy against a 90.3% naive-threshold baseline. Decides
stationary vs. moving each tick; when stationary, a zero-velocity update (ZUPT) freezes the estimate so drift does
not accumulate while parked or idling.

**Layer 2 — Learned Speed Model.** When moving, a second gradient-boosted model predicts the current speed from
four inputs: vibration spread and jerk from the raw IMU stream, the OSM road class under the current best-guess
position, and the speed at the moment the GNSS fix was lost together with how long ago that was. Gated: on roads
tagged 60 km/h or faster, held last-known speed is used instead, since it is already close to optimal there. Full
mechanism in `MECHANISM.md`.

**Layer 3 — Road-Constrained Particle Filter.** 500 position hypotheses ("particles") are carried along the road
graph, each weighted by how well its turning matches the gyroscope, its road class, and any speed-limit penalty,
driven forward using the speed from Layer 2, and resampled every tick.

**Layer 4 — Reporting Layer.** Mode hysteresis selects which particle cluster to report, resisting rapid
unjustified flips between competing road hypotheses; a speed-limited, direction-aware cursor caps how fast the
displayed position can visibly "catch up," so a change of belief shows as motion rather than a teleport.

### Output

A single (latitude, longitude, heading) estimate per tick, rendered on the Android app's map as a moving cursor,
with a live GNSS OK/LOST indicator and a re-centre control, in both live-sensor mode and offline-replay mode.

### Why this split, mechanically

The four layers correspond to the four distinct failure modes a GNSS blackout produces, and nothing more:

| Layer | Failure it corrects |
|---|---|
| 1 — Motion Classifier | Drift accumulating while the vehicle is not actually moving |
| 2 — Learned Speed Model | Distance travelled being wrong, because held speed does not track real speed changes |
| 3 — Particle Filter | Heading drift, and "which road" ambiguity that raw dead reckoning cannot resolve |
| 4 — Reporting Layer | The filter's own internal uncertainty being displayed as visible teleporting/jumping |

Each layer was added only after measuring that the layers before it, alone, left that specific failure mode
unaddressed — not as a design assumption. The measurements behind that sequencing are in `CHALLENGES.md`.


---

## Mechanism — How the Learned Speed Model Actually Works


This document covers the technical mechanism of Layer 2, the project's central innovation: why a gradient-boosted
tree model, trained on four specific inputs, succeeds where three closed-form physics formulas failed.

### Why gradient-boosted trees, and explicitly not a neural network

The model used here — and Layer 1's motion classifier — is a `HistGradientBoostingRegressor`/`Classifier`: several
hundred shallow decision trees, built sequentially, where each new tree is trained on the residual error left by
every tree before it. At each split, a tree asks a single yes/no threshold question on one input at a time, and
splits are nested, so a feature's effect changes depending on what has already been asked.

**There is no neural network anywhere in this pipeline** — no layers, no neurons, no backpropagation. This was a
deliberate choice, for two measured reasons: the true feature-to-speed relationships are step-shaped, not smooth
(§ below), so a model that is a step function by construction matches the actual shape of the data; and the
available training data (19–40 km of driving) is too small to fit a neural network's typical parameter count
without overfitting, whereas a shallow boosted-tree ensemble is well matched to a dataset this size.

### The physical reason a smooth formula cannot work: aliasing

Sampling at 10 Hz sets the Nyquist limit at 5 Hz. Wheel rotation frequency is proportional to speed divided by
wheel circumference, and it crosses 5 Hz at ≈36 km/h. Above that speed, the true vibration frequency is not merely
degraded — it is folded back (aliased) onto a different, incorrect frequency, a mathematically exact consequence
of the sampling theorem, not an approximation.

Measured directly on a real 69 km/h recording window:

| Quantity | True (248 Hz) | 10 Hz-binned | Error |
|---|---|---|---|
| Frequency | 5.49 Hz | 3.68 Hz | 33% wrong |
| Magnitude (std) | 1.445 m/s² | 0.583 m/s² | 60% lost |

The 10 Hz pipeline additionally mean-bins every 100 ms, an extra low-pass-filter attenuation stacked on top of the
aliasing itself.

### Three physics formulas, and exactly why each failed

| Approach | Formula | Measured result |
|---|---|---|
| Integrate accelerometer readings | v = ∫a·dt | Worse than assuming speed never changes, at every window from 5 s to 30 s |
| Turn-rate ÷ steering geometry | v = a_lateral ÷ ω | Accurate only on phones that could physically feel a corner — useless on 2 of 4 test phones |
| Map curvature | v = ω ÷ κ_road | Map curvature vs. real vehicle curvature: r = 0.22 — too weak to invert |

All three share the same shape: one input, a smooth proportional relationship, trusted equally everywhere. A
smooth formula multiplies the corrupted magnitude directly into its output — a single pothole jolt reading as
"very high speed" on the raw aliased signal directly corrupts the estimate.

### What survives aliasing, and why a step model exploits exactly that

Although the exact aliased magnitude is wrong, it still **climbs monotonically** with true speed — corrupted in
value, but directionally intact. A decision tree only asks whether a value is above or below a learned threshold,
so it can use a monotonic-but-corrupted signal without being misled by its magnitude.

Measured directly, by grouping real training rows into buckets per feature and reading the model's actual
predictions:

**Vertical vibration spread → predicted speed**

| Vibration level | Raw sensor range | Model predicts |
|---|---|---|
| Very low (idle) | 0.02 – 0.25 | ~8 km/h |
| Low (just moving) | 0.25 – 0.38 | ~39 km/h |
| Medium | 0.38 – 0.49 | ~49 km/h |
| High | 0.49 – 0.65 | ~54 km/h |
| Very high | 0.65 – 17.80 | ~53 km/h *(plateau)* |

**Jerk (sudden acceleration change) → predicted speed**

| Jerk level | Model predicts |
|---|---|
| Very low | ~8 km/h |
| Low | ~42 km/h |
| Medium | ~50 km/h |
| High | ~51 km/h |
| Very high | ~50 km/h *(plateau)* |

**Map speed-limit tag → predicted speed**

| Tagged road limit (km/h) | Model predicts |
|---|---|
| 2 – 13 (residential-ish) | ~30 km/h |
| 13 – 18 | ~42 km/h |
| 18 – 22 | ~60 km/h |
| 22 – 31 (dual carriageway/motorway) | ~71 km/h |

**Last known GPS speed → predicted speed 30–90 s later**

| Speed at the fix | Model predicts later |
|---|---|
| 0 – 14 km/h | ~25 km/h |
| 14 – 32 | ~31 km/h |
| 32 – 45 | ~37 km/h |
| 45 – 59 | ~43 km/h |
| 59+ | ~66 km/h |

Reading across all four: the first two (raw sensor statistics) both show the steep-climb-then-plateau shape that
is the direct signature of aliasing damage — the model stops trusting the exact magnitude past a point. The third
(a clean map tag) is closest to a straight line, because it never touched the accelerometer. The fourth shows the
model's own discovered "regression to the mean": v(60 s) ≈ 0.59 × v₀ + 5.6 — extreme starting speeds are predicted
to move back toward a typical pace. This relationship was never hand-coded; it emerged from the training data's
own structure.

### How the four inputs combine

The four inputs are combined jointly by the tree structure, not averaged or summed as independent correction
terms: `v̂ = f(vibration_bucket, jerk_bucket, road_class, v_last_fix)`, where map and last-known-speed context
change which vibration/jerk threshold actually gets applied, rather than being added on afterward. The trained
model is evaluated purely as a forward pass at inference time — a fixed sequence of threshold checks, no training
happens on-device.

### How the prediction enters the particle filter

The learned speed prediction becomes a per-tick target that every particle's velocity state drifts toward, rather
than replacing the filter's own weighting logic. Particles are still scored primarily by gyroscope-vs-road-bearing
agreement; the speed model only supplies how far each particle should advance along its current road segment on a
given tick. This keeps the map-matching mechanism intact while fixing only the along-track distance error a
held-speed assumption leaves behind.

### Why gating is necessary — measured, not assumed

On roads tagged 60 km/h or faster, held last-known speed is already close to optimal, and only ≈6% of the training
data covers that speed range — the model has too little evidence there to be trusted over the simpler baseline.
The engine therefore gates: hold last-known speed on fast, tagged roads; use the learned model everywhere else.

An oracle test of a perfect chooser between the two methods tops out at 78% of blackouts under 10%, only 8 points
above simply always using the learned model (70%). That residual 8-point gap was shown to be fundamentally
unpredictable in advance from any information available at the moment GNSS is lost — not a limitation of the
gating logic itself, but a genuine ceiling on how well driver intent can be anticipated.

On the team's own Tamil Nadu recordings, this England-tuned gate never fires (0% of local roads carry a
`maxspeed` tag), so gating was re-derived on the vehicle's own last-known-speed threshold instead — a genuinely
different deployment rule per region, not a portability failure.


---

## Challenges Faced, and How Each Was Resolved


Every real obstacle encountered while building the final system, in the order it was encountered, including the
ones that were tried and rejected. Nothing here is smoothed over — a rejected idea is reported as rejected, with
the number that rejected it.

### 1 · The dataset itself was not clean

Before any model could be trained, the raw IO-VNBD dataset needed real cleaning work: two different column-naming
schemes across drives, case-mismatched file pairs, latin-1 encoding, a sensor log that assumed a perfect 10 Hz
clock when it was not always true. Time alignment between the phone's IMU and the vehicle's own GNSS/CAN truth
required a two-stage process — a coarse GPS-track match within ±10 minutes, then a fine gyro-vs-yaw match within
±30 seconds — because phone and vehicle clocks drift independently. 98.6% of rows aligned successfully; the
remainder were flagged and excluded rather than guessed at.

### 2 · Physics formulas for speed, tried first, all failed

Three closed-form physics approaches were tried before any learned model:

| Approach | Formula | Result |
|---|---|---|
| Integrate accelerometer readings | v = ∫a·dt | Worse than assuming speed never changes, at every window length from 5 s to 30 s |
| Turn-rate ÷ steering geometry | v = a_lateral ÷ ω | Accurate only on phones that could physically feel a corner — useless on 2 of 4 test phones |
| Map curvature | v = ω ÷ κ_road | Map curvature vs. real vehicle curvature: r = 0.22 — too weak to invert |

Why all three failed is explained mechanically, with the aliasing measurement behind it, in `MECHANISM.md`.

### 3 · The metric itself was misleading, and had to be fixed before anything else

The engine was originally scored only at the 1 km finish line of each blackout. This let an estimate wander far
off course mid-blackout and still score well if it happened to be close again by the end — watching the engine's
own replay screen exposed this directly. Switching to the error **averaged along the entire blackout** revealed
two problems invisible under the old metric:

- **42% of blackouts left the driven road** at some point, by 30 m or more.
- **Every blackout contained at least one 1-second jump** of the displayed position by tens of metres — the
  filter's internal belief was reasonable, but multiple road hypotheses could compete and the reported cursor
  could leap between them.

### 4 · Fixing the reporting layer, without touching the model underneath

Both problems above were failures of *display*, not of the filter's own belief. Two fixes, entirely in how belief
becomes an on-screen position:

- **Mode hysteresis** — the displayed position does not switch to a competing road hypothesis until that
  hypothesis has clearly been winning for several updates, not one instant.
- **A speed-limited cursor** — the displayed position cannot move faster than a real vehicle could, closing gaps
  quickly along the direction of travel but never sideways.

Result: cursor jumps fell from 71% of blackouts to 5%; blackouts leaving the road fell from 45% to 29%; and, as a
side effect of no longer chasing bad hypotheses, drift itself improved (7.0% → 5.9% median).

### 5 · The hunt for speed: eight further physics ideas, all rejected

With the reporting layer fixed, the remaining error was almost entirely speed error. Eight further approaches
were tried and measured on tuning drivers only, none adopted:

| Idea | Result |
|---|---|
| Decay speed toward the road's tagged limit | Limits are routinely exceeded; no improvement |
| Tighten the filter's own speed-limit penalty | Measurably worse |
| A learned "speed regresses to the mean" rule | Helped some blackouts, hurt others; net negative |
| Widen the filter's initial speed uncertainty | Badly worse — the map's turns are too sparse to recover the right hypothesis |
| Trend/derivative features for the speed signal | No measurable improvement |
| Deliberately exaggerate predictions to counter caution | Measurably worse — the model's caution is the statistically correct response |
| Native 248 Hz spectral features (own recordings) | Worse than coarse features — not enough data to fit a larger feature set |
| A learned arbiter choosing between held-speed and the model | Right only 54% of the time — no better than chance |

### 6 · The breakthrough

The insight that broke the deadlock, and the full mechanism behind it, is documented in `MECHANISM.md`: a
gradient-boosted tree model trained on four inputs that never require the destroyed part of the aliased signal.
Measured on drivers never used for training: **3.15 m/s** RMS error at 30 seconds ahead, against **6.09 m/s** for
simply holding the last known speed — and **2.47 m/s against 6.25 m/s** specifically when the vehicle was slow at
the moment of loss, which is where the engine had failed worst.

### 7 · Three stubborn clips, and what they revealed about tuning itself

Three real blackouts still missed the 10% target even in the finished engine. Each was diagnosed by substituting
the true value for one input at a time (speed, heading, road choice) to isolate the cause. Several targeted fixes
were tried and mostly rejected — a same-road-through-junction bonus helped the general case but made no
measurable difference on these specific clips (motorway-heavy, a different failure mode); a road-class-switch
penalty helped one case and broke another that legitimately needed that exact switch.

The finding that mattered more than any individual fix: **small setting changes move the aggregate result by a
fraction of a percentage point, while flipping individual blackouts across the pass/fail line roughly 5% of the
time.** One real blackout scored anywhere from 3.3% to 26.7% across four otherwise-reasonable configurations,
because that specific moment sits on a genuine coin-flip between two roads the map cannot disambiguate. This is
why every setting in this project was chosen using the aggregate result across hundreds of blackouts on tuning
drivers only, frozen, and applied exactly once, unmodified, to drivers never used for tuning.

### 8 · Validating outside the original dataset — India, a two-wheeler, a different sensor rate

Everything above was built on IO-VNBD — cars, mostly 10 Hz, England. To check it was not an artifact of that one
dataset, the full pipeline was re-run on the team's own recordings: a two-wheeler, phone hand-held, 248 Hz,
Tiruchirappalli, Tamil Nadu. Trained on one ride, tested on a separate ride over the same corridor.

Real differences found, each a genuine engineering challenge, not a restatement of the England result:

- **Tamil Nadu's map carries essentially no speed-limit tags** (0% of 111 blackouts start on a tagged road). The
  England-tuned gating rule ("hold on tagged fast roads") is inert here; the engine instead gates on the vehicle's
  own last-known speed, which needs no map tags at all — a genuinely different deployment rule per region.
- **Far fewer turns per kilometre** than the English routes (0.9/km on the main corridor vs. 3.5/km in town) — the
  map has fewer chances to correct position sideways. On this corridor, the map-free estimate actually scored
  better than the map-assisted one (8.7% vs. 10.1%) — sparse junctions plus parallel service roads is the map's
  worst case, in India as much as in England.
- **Speed breakers are visible at 248 Hz and invisible at 10 Hz** — 4 of 5 mapped bumps within 5 m of the route
  were detected directly in the raw stream, one peaking at 23 m/s² against a 4 m/s² background. A genuinely
  India-specific landmark opportunity, and a real point-landmark a parallel road cannot imitate.
- **Self-mapping *unofficial* bumps from repeated passes is not yet proven.** Jolts repeating between two rides
  looked like 2.7 per km until a control test (sliding one ride's detections 100–300 m along the same road) showed
  most matches were coincidence — the genuine excess rate is closer to 0.7 per km, and the strongest jolts do not
  repeat at all, because with the phone in a hand, most of what the accelerometer sees is the rider, not the road.
  Reported here honestly as an open question, not a working feature.

Despite harder conditions overall — no map tags, fewer turns, no working stop detector yet for a two-wheeler — the
learned speed model carried over directly, with the same shape of improvement seen in England, concentrated where
Indian traffic conditions are hardest for a held-speed approach: under 40 km/h, median error improved from
**27.5% to 14.7%**.


---

## Results

**Test drivers (England, never used to tune any setting), scored by error averaged along the whole blackout:**

| Metric | Predecessor engine | Final engine |
|---|---|---|
| Path drift, median | 7.0% | **5.9%** (5.8% with the speed-model gate) |
| Blackouts meeting the 10% target | 73% | **80–82%** |
| Worst moment in a blackout, median | 16.3% | **13.0–13.1%** |
| Blackouts that leave the driven road | 45% | **~28–29%** |
| Cursor jumping between roads | 71% of blackouts | **5%** |
| Slow driving (under 40 km/h), path median | 10.6% | **8.2%** |
| Speed prediction error (RMS) | 6.09 m/s | **3.15 m/s** |

With the *true* speed substituted (an oracle test, not achievable in deployment), the same engine scores 2.5–3% —
this is the theoretical floor, and the gap between it and 5.9% is almost entirely residual speed uncertainty, not
a mapping flaw.

**On the team's own India recordings (two-wheeler, hand-held phone, 248 Hz, no map speed-limit tags):**

45 of 111 real blackouts meet the 10% target; the engine beats the simpler held-speed baseline on 85 of 111. Eight
consecutive, non-overlapping kilometres from one ride — scored by a model trained only on a separate ride over the
same corridor — average **6.5%**, with seven of eight legs under the benchmark.

---

---

## Honest Limitations

- **The remaining error is a speed problem, not a mapping problem.** With true speed, the engine scores 2.5–3%;
  the 5.9% actually achieved is almost entirely residual speed-prediction uncertainty.
- **Two distinct, named failure modes remain:** a vehicle accelerating hard immediately after GNSS is lost, and
  the filter occasionally locking onto the wrong parallel road at a sparse junction.
- **The gap between the achieved result and a theoretical perfect chooser between the engine's own internal
  methods is about eight percentage points**, and this gap was shown to be fundamentally unpredictable in advance
  — not a limitation of modelling effort. See `MECHANISM.md` §"Why gating is necessary."
- **Self-mapped, unofficial road landmarks are a promising but unproven idea**, not a working feature.
- **No working stop detector exists yet for a two-wheeler specifically** — the motion classifier was trained on
  car data.
- **India validation covers one corridor, recorded on one day, with a hand-held phone** — a real, useful,
  out-of-dataset validation, but not yet a claim of generalisation beyond that corridor.

---

---

## References

- Groves, P. D. (2013). *Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems.* Artech House.
- Newson, P., & Krumm, J. (2009). *Hidden Markov Map Matching Through Noise and Sparseness.* ACM SIGSPATIAL GIS.
- Skog, I., & Händel, P. (2010). *Zero-Velocity Detection — An Algorithm Evaluation.* IEEE Trans. Biomedical Engineering.
- Gustafsson, F., et al. (2002). *Particle Filters for Positioning, Navigation, and Tracking.* IEEE Trans. Signal Processing.
- IO-VNBD — Inertial/Odometry Vehicle Navigation Benchmark Dataset (England, multiple drivers, car, 10 Hz IMU).
- Team's own recordings — Tiruchirappalli, Tamil Nadu, two-wheeler, hand-held phone, 248 Hz IMU, 1 Hz GNSS.
- OpenStreetMap contributors — road network data for England and Tamil Nadu, via the Overpass API.
