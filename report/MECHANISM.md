# Mechanism — How the Learned Speed Model Actually Works

This document covers the technical mechanism of Layer 2, the project's central innovation: why a gradient-boosted
tree model, trained on four specific inputs, succeeds where three closed-form physics formulas failed.

## Why gradient-boosted trees, and explicitly not a neural network

The model used here — and Layer 1's motion classifier — is a `HistGradientBoostingRegressor`/`Classifier`: several
hundred shallow decision trees, built sequentially, where each new tree is trained on the residual error left by
every tree before it. At each split, a tree asks a single yes/no threshold question on one input at a time, and
splits are nested, so a feature's effect changes depending on what has already been asked.

**There is no neural network anywhere in this pipeline** — no layers, no neurons, no backpropagation. This was a
deliberate choice, for two measured reasons: the true feature-to-speed relationships are step-shaped, not smooth
(§ below), so a model that is a step function by construction matches the actual shape of the data; and the
available training data (19–40 km of driving) is too small to fit a neural network's typical parameter count
without overfitting, whereas a shallow boosted-tree ensemble is well matched to a dataset this size.

## The physical reason a smooth formula cannot work: aliasing

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

## Three physics formulas, and exactly why each failed

| Approach | Formula | Measured result |
|---|---|---|
| Integrate accelerometer readings | v = ∫a·dt | Worse than assuming speed never changes, at every window from 5 s to 30 s |
| Turn-rate ÷ steering geometry | v = a_lateral ÷ ω | Accurate only on phones that could physically feel a corner — useless on 2 of 4 test phones |
| Map curvature | v = ω ÷ κ_road | Map curvature vs. real vehicle curvature: r = 0.22 — too weak to invert |

All three share the same shape: one input, a smooth proportional relationship, trusted equally everywhere. A
smooth formula multiplies the corrupted magnitude directly into its output — a single pothole jolt reading as
"very high speed" on the raw aliased signal directly corrupts the estimate.

## What survives aliasing, and why a step model exploits exactly that

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

## How the four inputs combine

The four inputs are combined jointly by the tree structure, not averaged or summed as independent correction
terms: `v̂ = f(vibration_bucket, jerk_bucket, road_class, v_last_fix)`, where map and last-known-speed context
change which vibration/jerk threshold actually gets applied, rather than being added on afterward. The trained
model is evaluated purely as a forward pass at inference time — a fixed sequence of threshold checks, no training
happens on-device.

## How the prediction enters the particle filter

The learned speed prediction becomes a per-tick target that every particle's velocity state drifts toward, rather
than replacing the filter's own weighting logic. Particles are still scored primarily by gyroscope-vs-road-bearing
agreement; the speed model only supplies how far each particle should advance along its current road segment on a
given tick. This keeps the map-matching mechanism intact while fixing only the along-track distance error a
held-speed assumption leaves behind.

## Why gating is necessary — measured, not assumed

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
