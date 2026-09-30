# Round 3 report — the learned speed model, in plain terms

This document explains the one thing round 3 added that round 2 did not have: a way to estimate the vehicle's speed
during a GNSS blackout, learned from data, after the physics-based approaches all failed. For the full numerical
results and the engine's other round-3 changes (the reporting layer, mode hysteresis, etc.), see `EXECUTION_LOG.md`
and `ENGINE_LAYERS.md`. This file is specifically about *why the physics failed* and *what the model does instead*.

---

## 1 · Why the physics-based approaches failed

Round 2 held the vehicle's speed at whatever the last GNSS fix reported, for the whole blackout. That is a crude
approach, so before building anything learned, several standard physics formulas were tried to replace it:

| Approach | Formula | Result |
|---|---|---|
| Integrate acceleration | `v = ∫a · dt` | **worse than doing nothing** at every time window from 5 s to 30 s |
| Turn-rate division | `v = lateral acceleration ÷ turn rate` | accurate only where the phone could physically feel a corner — useless on 2 of 4 test phones |
| Map curvature | `v = turn rate ÷ road curvature` | the map's curvature and the vehicle's actual curvature barely agreed (correlation 0.22) |

All three are **fixed, single-input equations** — one formula, applied identically regardless of the situation. The
common failure was **aliasing**: our accelerometer samples at 10 Hz (IO-VNBD) or 248 Hz (our own rides), but a
vehicle's wheel and engine vibration sit around 9–50 Hz. When a signal above half the sampling rate is measured, it
doesn't fade gently — it gets folded down and disguised as a completely different, wrong frequency, indistinguishable
from noise. This is not "a little bit of the signal is lost" — it is destructive. There is no way to recover it with a
cleverer formula, because the original information is genuinely gone. `round3_accel_bridge.py` confirmed this directly:
integrating acceleration was measured to be worse than assuming speed never changes, at every window length tested.

**The lesson from this failure decided the whole approach for what came next: stop trying to resolve the broken part
of the signal, and use other evidence instead that doesn't require resolving it.**

---

## 2 · From "gradient guessing" to "step matching" — how the replacement works

### The physics dial

Every one of the formulas above works like a **dial**: shake the sensor twice as hard, get exactly twice the speed,
smoothly, forever, with no exceptions. This is a strong assumption, and it is wrong in two ways at once — the sensor
data is noisy (so "twice as hard" is not reliably measurable), and the relationship itself is not actually linear once
you look at real data (a bumpy but slow road can vibrate as much as a smooth but fast one).

### The learned model's step switch

The replacement is a **gradient-boosted tree model** (the same family of model as round 1's stop classifier — not a
neural network; see the note in §5). Instead of one smooth formula, it learned a set of **thresholds**: "is this
feature above or below some cutoff," repeated and combined across several features. The result behaves like a
**multi-position switch**, not a dial: it separates readings into a handful of buckets and predicts roughly the same
value for anything inside a bucket, however far that value actually is from the bucket's edge.

This was measured directly by grouping real (not simulated) training rows into five buckets per feature and reading
off what the model actually predicts:

**Vertical vibration spread → predicted speed**

| Vibration level | Raw sensor range | Model predicts |
|---|---|---|
| Very low (stationary / idling) | 0.02 – 0.25 | **~8 km/h** |
| Low (just moving) | 0.25 – 0.38 | **~39 km/h** |
| Medium | 0.38 – 0.49 | **~49 km/h** |
| High | 0.49 – 0.65 | **~54 km/h** |
| Very high | 0.65 – **17.80** | **~53 km/h** |

The last bucket spans a raw range **27 times wider** than any other bucket (0.65 up to 17.80), and the predicted speed
barely changes (54 → 53 km/h). Once vibration is "high enough" to mean the vehicle is clearly moving fast, the model
stops caring exactly how much higher it climbs — a dial would keep predicting an ever-higher (and increasingly wrong)
speed for an ever-noisier reading; the switch just stays in its "fast" position.

**Jerk (sudden acceleration change) → predicted speed**

| Jerk level | Model predicts |
|---|---|
| Very low | ~8 km/h |
| Low | ~42 km/h |
| Medium | ~50 km/h |
| High | ~51 km/h |
| Very high | ~50 km/h |

Same shape: a steep climb across the first two steps, then a hard plateau.

**Map speed-limit tag → predicted speed** (the one feature that is *not* a noisy sensor, and behaves the most
gradient-like of the four)

| Tagged road limit | Model predicts |
|---|---|
| 2 – 13 (residential-ish) | ~30 km/h |
| 13 – 18 | ~42 km/h |
| 18 – 22 | ~60 km/h |
| 22 – 31 (dual carriageway / motorway) | ~71 km/h |

**Road class (OSM highway type) → predicted speed** — the cleanest feature of all, because unlike a numeric tag there
is nothing to bin: this feature arrives already discrete (motorway, trunk, primary, …), so the model just looks it up
rather than searching for a threshold.

| OSM road class | Real average speed | Model predicts |
|---|---|---|
| motorway | 105.1 km/h | **105.0 km/h** |
| motorway_link (slip road) | 75.0 | **74.8** |
| trunk | 47.9 | **47.9** |
| primary | 43.4 | **43.8** |
| trunk_link | 27.8 | **27.5** |
| secondary | 36.4 | **36.3** |
| tertiary | 35.2 | **35.2** |
| tertiary_link | 27.5 | **26.4** |
| unclassified | 25.8 | **26.1** |
| residential | 19.8 | **20.0** |
| secondary_link | 17.8 | **17.5** |
| service (driveways, car parks) | 8.2 | **9.3** |

Every predicted value sits within about 1 km/h of the real average — this is the model's single most trustworthy
input, because unlike vibration or jerk it never passed through the accelerometer at all, so it carries none of the
sensor noise, aliasing, or averaging damage described in §3b. Notice also that the model was never told "a slip road
is different from an ordinary motorway or trunk road" — it discovered `motorway_link` (75 km/h) and `trunk_link`
(27.8 km/h) behave as their own, intermediate categories purely by being given the freedom to split on `road_class`
and let each branch specialize.

This is also the clearest illustration of *why the map and the IMU are combined rather than either used alone*:
`road_class` alone already predicts speed almost perfectly here — but only because it is certain which road the
vehicle is on. During an actual blackout the particle filter is not certain of that; it is weighing several road
hypotheses at once (§ ENGINE_LAYERS.md, layer 3). The IMU features are what keep the speed estimate useful precisely
when the map's own road identity is still uncertain.

**Last known GPS speed → predicted speed 30–90 s later**

| Speed at the fix | Model predicts later |
|---|---|
| 0 – 14 km/h | ~25 km/h |
| 14 – 32 | ~31 km/h |
| 32 – 45 | ~37 km/h |
| 45 – 59 | ~43 km/h |
| 59+ | ~66 km/h |

This last table also shows the model's built-in "regression to the mean": a very slow fix is predicted to speed up,
a very fast fix is predicted to (mostly) stay fast but with the gap to the average narrowing — matching what was
independently measured about how real driving actually evolves after a fix (entry 42, `EXECUTION_LOG.md`).

### Why steps beat a dial here

A dial trusts every reading equally, all the time — including a single violent pothole jolt, which a formula would
read as "very high speed" even though it is really a road defect, not velocity. A step model instead says: *past a
certain point, I stop trusting the exact magnitude of this one noisy signal, and lean on the other signals (the map,
the last known speed) to settle the actual number.* That is deliberately reduced sensitivity to any single unreliable
input — exactly the property you want when one sensor (the 10 Hz/248 Hz accelerometer) is known to have a
noise floor higher than the physics approaches could work around.

---

## 3 · The re-explanation of point 2 (why this is *not* "seeing more of the spectrum")

An earlier, tempting analogy was: *if a formula can only "see" two colors of a spectrum (say red and blue), maybe the
learned model can detect a faint leaked "buffer" beyond that boundary that the formula missed* — i.e., recovering a
little extra resolution from the same aliased frequency band.

**That is not what happened, and the distinction matters for how this is written up.**

Aliasing does not leave a faint, recoverable trace. When a 9 Hz wheel-rotation signal is sampled at 10 Hz, it is not
"slightly blurred" — it is **relabeled as an entirely different, wrong frequency**, and becomes statistically
indistinguishable from ordinary noise. There is no hidden buffer sitting there waiting to be detected by a smarter
algorithm; the original information is destroyed by the sampling process itself, permanently. This was confirmed
directly: integrating the aliased signal was worse than doing nothing at *every* tested time window, with no
combination of thresholds or smoothing able to recover it (`round3_accel_bridge.py`).

**What the model actually did was refuse to read that broken instrument at all, and cross-reference three different,
intact instruments instead:**

- **jerk** — a sudden *change* in acceleration is a time-domain event (a spike), not a frequency reading. It survives
  regardless of sample rate, because it doesn't depend on resolving a specific oscillation frequency.
- **vibration energy/spread** — a coarse statistic ("how much is this shaking overall"), not a precise frequency
  measurement.
- **the map and the last known fix** — external information that never went through the accelerometer at all.

So the corrected analogy is: **the formula insisted on reading a shattered instrument (the aliased frequency band).
The model put that instrument down and instead cross-referenced three other, unbroken instruments** that were sitting
next to it the whole time, unused, until they were combined and tested. It did not recover hidden spectral content —
that claim would not survive a Nyquist-theorem objection from a reviewer. It found a route around the broken
instrument entirely.

---

## 3b · A real measured example, and a correction to the claim above

The first draft of §3 said vibration energy "survives" aliasing "mostly intact." That was checked directly against a
real recording and turned out to be **too strong a claim** — the honest, measured result is more nuanced, and more
interesting, than "one feature is untouched and the rest are destroyed."

**The test.** Our own ride was recorded at 248 Hz. The same physical window of driving can therefore be measured two
ways: at its true rate, and after being averaged down to 10 Hz the same way the round-2/round-3 pipeline processes it.
One real 2-second window, vehicle at 69 km/h, was compared both ways:

| | **True (248 Hz)** | **After binning to 10 Hz** | What happened |
|---|---|---|---|
| Dominant vibration frequency | 5.49 Hz | **3.68 Hz** | **33% wrong** — the frequency identity is destroyed, as §2–3 predicted |
| Vibration magnitude (std) | 1.445 m/s² | **0.583 m/s²** | **60% smaller** — the exact energy is *also* degraded, not preserved |

**The correction.** The 10 Hz pipeline does not sample a single instant every 100 ms — it **averages every 100 ms into
one value**. Averaging is a genuine low-pass filter: it doesn't only mislabel high-frequency wiggles, it **smooths
them away**, discarding real energy before aliasing even has a chance to relabel what's left. So there are two
separate, stacked effects, not one:

1. **Aliasing** — folds whatever high-frequency content survives into a false, misleading frequency.
2. **Averaging/binning** — additionally *attenuates* that content before aliasing gets to it.

So vibration magnitude is not an "unbroken instrument" the way the map or the last known fix are — it takes damage
too. The earlier framing overstated how clean it stayed.

**Why the model still works despite this.** The model never needed the *exact* magnitude — only that the magnitude
keeps climbing when the vehicle goes faster, even if it is uniformly squashed down by binning. That is a much weaker
requirement than "measure the true value," and it is exactly what survives. This was already visible in §2's bucket
table, re-read with this in mind: vibration spread computed the same attenuated, 10 Hz-binned way still climbed in
lock-step with true speed across all five buckets (8 → 39 → 49 → 54 → 53 km/h) — degraded in absolute terms, but
**monotonic**, which is all a step-threshold model needs to sort readings into the right bucket.

| | Frequency (which Hz) | Magnitude (exact value) | Magnitude (ordering across speeds) |
|---|---|---|---|
| Needed by the failed physics formulas | ✅ required | not used | not used |
| Survives 10 Hz binning? | ❌ measured 33% wrong | ❌ measured 60% degraded | ✅ **still climbs with speed** (§2's bucket table) |
| What the model actually exploits | never asked | never relied on exactly | **this row — the thing that both aliasing and averaging fail to destroy** |

**The corrected one-line summary:** it is not that the model found an untouched signal sitting next to a broken one.
The coarse vibration signal is damaged too — just less catastrophically, and in a way that destroys the *exact value*
while preserving the *direction* (more shake still reliably means more speed). A step-shaped model, sorting readings
into a handful of buckets rather than trusting a precise number, is exactly the right tool for a signal that is
directionally reliable but numerically imprecise — which is now the better-supported reason, backed by a real
measurement, for why the relationships in §2 came out as staircases rather than straight lines.

---

## 4 · Summary comparison

| | Physics formulas (tried and failed) | The learned model (what replaced them) |
|---|---|---|
| Mathematical form | one continuous equation, same everywhere | hundreds of nested if/else threshold rules, summed |
| Relationship shape | straight line / proportional | steps: steep rise, then flat plateau, per feature |
| Inputs used | accelerometer alone | accelerometer *and* gyroscope *and* map *and* last known speed, combined |
| Sensitivity to noise | trusts every reading equally — a single spike swings the answer | desensitized past a threshold — a spike does not move the prediction once "in the plateau" |
| What failed | tried to resolve an aliased, destroyed frequency band | never attempts to resolve that band; uses jerk, coarse energy, and external map/GNSS data instead |
| Result | worse than doing nothing, at every configuration tested | beats holding the last speed: 3.15 m/s RMS vs 6.09 m/s (30 s out); 2.47 vs 6.25 m/s when the vehicle was slow at the fix |

---

## 5 · One correction carried over from earlier in this project

This model is **not a neural network** ("ANN"). It is a gradient-boosted decision tree ensemble
(`HistGradientBoostingRegressor`), the same model family used for round 1's stop classifier. No layers, no neurons, no
backpropagation — its "learning" is literally a sequence of threshold splits, which is also why it is directly
readable and auditable (§2's tables came straight out of it, with no black box in between). If this report or a slide
built from it refers to an "ANN," that phrasing should be corrected to "the learned speed model" or "the
gradient-boosted speed model" before presentation, to avoid a factual challenge about network architecture that the
project would not be able to answer.
