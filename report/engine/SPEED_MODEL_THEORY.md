# Round 3 theory — the full walkthrough of how the learned speed model works

This is the single consolidated file for the "why does this work, in plain terms" conversation — separate from
`ROUND3_REPORT.md` (the technical writeup with the failure analysis and full numbers) and `ENGINE_LAYERS.md` (how the
four engine layers fit together). Cross-references are given where the deeper numbers live.

A standing correction, made once and applying throughout: **there is no neural network anywhere in this project.**
What's discussed below as "the learned speed model" is a **gradient-boosted decision tree ensemble**
(`HistGradientBoostingRegressor`) — the same model family as round 1's stop classifier. No layers, no neurons, no
backpropagation. If "ANN" appears anywhere in earlier notes or a slide, it should be corrected to "the learned speed
model" before presenting.

---

## 0 · The four relationships, grouped together

The four inputs walked through one at a time in this conversation, side by side. Each is explained in more depth
further down (§1 covers the first two, §3 the other two) — this section exists purely so all four sit in one place,
in the order they were worked through.

**1. Vertical vibration spread → predicted speed**

| Vibration level | Raw sensor range | Model predicts |
|---|---|---|
| Very low (stationary/idling) | 0.02 – 0.25 | ~8 km/h |
| Low (just moving) | 0.25 – 0.38 | ~39 km/h |
| Medium | 0.38 – 0.49 | ~49 km/h |
| High | 0.49 – 0.65 | ~54 km/h |
| Very high | 0.65 – 17.80 | ~53 km/h |

**2. Jerk (sudden acceleration change) → predicted speed**

| Jerk level | Model predicts |
|---|---|
| Very low | ~8 km/h |
| Low | ~42 km/h |
| Medium | ~50 km/h |
| High | ~51 km/h |
| Very high | ~50 km/h |

**3. Map speed-limit tag → predicted speed**

| Tagged road limit | Model predicts |
|---|---|
| 2 – 13 (residential-ish) | ~30 km/h |
| 13 – 18 | ~42 km/h |
| 18 – 22 | ~60 km/h |
| 22 – 31 (dual carriageway/motorway) | ~71 km/h |

**4. Last known GPS speed → predicted speed 30–90 s later**

| Speed at the fix | Model predicts later |
|---|---|
| 0 – 14 km/h | ~25 km/h |
| 14 – 32 | ~31 km/h |
| 32 – 45 | ~37 km/h |
| 45 – 59 | ~43 km/h |
| 59+ | ~66 km/h |

Reading across all four: the first two (raw sensor statistics) both show the steep-climb-then-plateau shape that
comes from sensor noise and aliasing damage (§2) — the model stops trusting the exact magnitude past a point. The
third (a clean map tag) is the closest to a straight line, because it never touched the accelerometer. The fourth
shows the model's own discovery of "regression to the mean" (§8) — extreme starting speeds are predicted to move back
toward a typical pace.

---

## 1 · Why the physics formulas failed, and what replaced them

Round 2 held the vehicle's speed at whatever the last GNSS fix reported, for the whole blackout. Before building
anything learned, three physics formulas were tried to do better:

| Approach | Formula | Result |
|---|---|---|
| Integrate acceleration | `v = ∫a · dt` | worse than doing nothing, at every time window from 5 s to 30 s |
| Turn-rate division | `v = lateral acceleration ÷ turn rate` | accurate only on phones that could physically feel a corner — useless on 2 of 4 test phones |
| Map curvature | `v = turn rate ÷ road curvature` | the map's curvature and the vehicle's actual curvature barely agreed (r = 0.22) |

All three are **fixed, single-input equations** — the same formula applied identically in every situation. The
learned model replaced this with a **gradient-boosted tree**: instead of one smooth formula, it learned a set of
**thresholds** ("is this feature above or below some cutoff"), combined across several inputs at once
(accelerometer, gyroscope, the map, and the last known GNSS speed).

**The shift, in one sentence:** from a *dial* (one input, smooth, proportional, trusted equally everywhere) to a
*multi-position switch* (several inputs, each sorted into a handful of buckets, combined jointly).

This was measured directly, not just claimed — real training rows were grouped into buckets per feature and the
model's actual predictions read off:

**Vertical vibration spread → predicted speed**

| Vibration level | Raw sensor range | Model predicts |
|---|---|---|
| Very low (stationary/idling) | 0.02 – 0.25 | ~8 km/h |
| Low (just moving) | 0.25 – 0.38 | ~39 km/h |
| Medium | 0.38 – 0.49 | ~49 km/h |
| High | 0.49 – 0.65 | ~54 km/h |
| Very high | 0.65 – 17.80 | ~53 km/h |

The last bucket spans a raw range **27× wider** than any other, and the predicted speed barely moves (54 → 53 km/h).
Once vibration is "high enough," the model stops caring exactly how much higher it climbs — a dial would keep
predicting an ever-higher (and increasingly wrong) speed for an ever-noisier reading.

**Jerk (sudden acceleration change) → predicted speed:** same shape — 8 → 42 → 50 → 51 → 50 km/h across five buckets.
Steep climb, then a hard plateau.

**Why steps beat a dial:** a dial trusts every reading equally, including a single violent pothole jolt, which it
would misread as "very high speed." A step model says: *past a certain point, stop trusting the exact magnitude of
this one noisy signal, and lean on the other signals instead.* Deliberately reduced sensitivity to any one unreliable
input.

---

## 2 · The aliasing question — what the accelerometer can and cannot see, and the correction to the first answer

**The physical limit, in numbers.** A wheel spins at a frequency proportional to speed (≈2 m wheel circumference):

| Speed | Wheel rotation frequency |
|---|---|
| 20 km/h | 2.8 Hz |
| 36 km/h | **5.0 Hz** ← the danger line at 10 Hz sampling |
| 60 km/h | 8.3 Hz |
| 100 km/h | 13.9 Hz |

A sensor sampling at 10 Hz can only correctly measure signals up to half its rate — **5.0 Hz** (the Nyquist limit).
Above that speed, wheel vibration isn't just missed, it's **misread as a different, wrong frequency**, indistinguishable
from noise. This is destructive, not "a little blurry" — there is no way to recover it with a cleverer formula. Engine
vibration is worse: it aliases even at idle, because engine firing rate (25–70 Hz typically) is always far above 5 Hz.

At the phone's own 248 Hz sampling, the ceiling rises to 124 Hz — comfortably above wheel and most engine frequencies
— so this specific wall does not exist on our own recordings. But testing a model built on that finer detail
(`round3_native_248.py`) still lost to the coarser model, for an unrelated reason: not enough riding distance (~40 km)
to safely learn fine-grained patterns without overfitting one ride.

**The first-pass analogy, and its correction.** The first framing was: "the model detects a faint leaked buffer beyond
the boundary that the formula missed." **That is not accurate.** Aliasing doesn't leave a faint recoverable trace —
tested directly (`round3_accel_bridge.py`): integrating the aliased signal is worse than doing nothing at every window
length, with no threshold or smoothing recovering it.

**What actually happened, checked against a real recording.** The same 2-second window of our own ride (69 km/h) was
measured two ways: at its true 248 Hz rate, and after being averaged down to 10 Hz the way the pipeline actually
processes it:

| | True (248 Hz) | After binning to 10 Hz | What happened |
|---|---|---|---|
| Dominant vibration frequency | 5.49 Hz | 3.68 Hz | **33% wrong** — frequency identity destroyed |
| Vibration magnitude (std) | 1.445 m/s² | 0.583 m/s² | **60% smaller** — magnitude also degraded, not preserved |

This corrects an over-strong first claim that magnitude "survives mostly intact." It does not — the 10 Hz pipeline
doesn't point-sample, it **averages every 100 ms**, which is a genuine low-pass filter: it attenuates real energy
*before* aliasing even gets to relabel what's left. Two stacked effects, not one.

**Why the model still works despite this.** It never needed the *exact* magnitude — only that magnitude keeps
*climbing* with speed, even while uniformly squashed down. That's confirmed by the bucket table above: vibration
spread, computed the same damaged, 10 Hz-binned way, still climbed in lock-step with true speed across all five
buckets (8 → 39 → 49 → 54 → 53 km/h). Degraded in absolute value, but **monotonic** — which is all a step-threshold
model needs to sort a reading into the right bucket.

| | Frequency (which Hz) | Magnitude (exact value) | Magnitude (ordering across speeds) |
|---|---|---|---|
| Needed by the failed physics formulas | required | not used | not used |
| Survives 10 Hz binning? | ❌ 33% wrong | ❌ 60% degraded | ✅ still climbs with speed |
| What the model actually exploits | never asked | never relied on exactly | **this row** |

**Corrected one-line summary:** the coarse vibration signal is damaged too, just less catastrophically than the fine
one, and in a way that destroys the exact value while preserving the direction. A step model is the right tool for a
signal that is directionally reliable but numerically imprecise.

---

## 3 · The other four inputs, the same way — real relationships, not descriptions

**Map speed-limit tag → predicted speed** (a clean, non-sensor input — the most gradient-like of the group)

| Tagged road limit | Model predicts |
|---|---|
| 2 – 13 (residential-ish) | ~30 km/h |
| 13 – 18 | ~42 km/h |
| 18 – 22 | ~60 km/h |
| 22 – 31 (dual carriageway/motorway) | ~71 km/h |

**Road class (OSM highway type) → predicted speed** — arrives already discrete, so there's nothing to bin; the model
just looks it up:

| OSM road class | Real average speed | Model predicts |
|---|---|---|
| motorway | 105.1 km/h | 105.0 km/h |
| motorway_link (slip road) | 75.0 | 74.8 |
| trunk | 47.9 | 47.9 |
| primary | 43.4 | 43.8 |
| trunk_link | 27.8 | 27.5 |
| secondary | 36.4 | 36.3 |
| tertiary | 35.2 | 35.2 |
| unclassified | 25.8 | 26.1 |
| residential | 19.8 | 20.0 |
| service | 8.2 | 9.3 |

Every value is within ~1 km/h of the real average — the model's single most trustworthy input, because it never
passed through the accelerometer and carries none of §2's sensor damage. It also discovered on its own that a
motorway *slip road* behaves like its own intermediate category (75 km/h), without being told that distinction exists
— just by being allowed to split on this feature and let each branch specialize.

**Last known GPS speed → predicted speed 30–90 s later**

| Speed at the fix | Model predicts later |
|---|---|
| 0 – 14 km/h | ~25 km/h |
| 14 – 32 | ~31 km/h |
| 32 – 45 | ~37 km/h |
| 45 – 59 | ~43 km/h |
| 59+ | ~66 km/h |

This table also shows "regression to the mean" happening on its own — expanded in §8 below.

**Why combine these rather than use the best one alone.** `road_class` alone predicts speed almost perfectly *if* you
already know which road the vehicle is on. During an actual blackout the filter doesn't know that with certainty — it
is weighing several road hypotheses at once (layer 3, `ENGINE_LAYERS.md`). The IMU features are what keep the speed
estimate useful precisely when the map's own road identity is still uncertain.

---

## 4 · Why gradient-boosted trees, not a neural network or a straight-line regression

- **Data size.** Training data is tens of thousands of rows from a few dozen kilometres of driving — small by deep
  learning standards. A neural network needs far more data to avoid memorizing noise; boosted trees regularize well
  at this size, which is also why round 1's classifier used the same family successfully.
- **Feature types.** Inputs mix a continuous sensor statistic, a categorical map tag, and a discrete road class —
  trees handle this natively (no need to normalize or one-hot-encode by hand), where a neural net would need explicit
  feature engineering to do the same.
- **Interpretability.** Every claim in §1–3 came directly out of inspecting the trained model — feature importances,
  and grouping real predictions by real feature value. A tree ensemble is one of the few model types where you can
  read off "here is the literal relationship it learned" this directly; a neural net's weights don't decompose this
  cleanly.
- **Matches the actual relationship shape.** §1–3 showed the true underlying relationships are step-like, not smooth
  — trees *are* step functions by construction, so there's no mismatch between model architecture and the shape of
  the pattern actually present in the data.

---

## 5 · How the model combines features jointly, not by voting

A tree doesn't average "vibration says X, the map says Y" into a blended answer. It asks **nested** questions: *if
vibration is high, AND the map says residential, THEN predict this — but if vibration is high AND the map says
motorway, predict something else entirely.* Each split can depend on the outcome of an earlier split, which is how
the model encodes that a feature's meaning changes depending on context — exactly what §3's `road_class` example
showed (the same "high vibration" reading means something very different on a motorway than on a residential road).
A gradient-boosted ensemble is hundreds of these trees stacked, each one correcting the residual errors of the trees
before it, which is what lets it capture interactions between many features at once rather than just one at a time.

---

## 6 · How the model's output actually plugs into round 2's particle filter

The model produces one number per second: a predicted speed. That number doesn't replace the filter's own logic — it
becomes what each of the filter's hypotheses ("particles") is told to drift by. In code, `core/particle.py` gained an
optional `speed_target=` argument: when set, every particle's speed is nudged to track the model's predicted speed
over time, in addition to (not instead of) the filter's existing checks — how well a hypothesis's turning matches the
gyro, how well its direction matches the heading, whether its speed is plausible for the road it's on. With
`speed_target` left unset, the code reproduces round 2 exactly (checked: 199 checkpoints, zero differ) — this is a
genuinely additive change, not a replacement of the filter's own reasoning.

Why route it this way rather than, say, directly overriding the reported position: a wrong speed prediction on its
own can only mislead the filter's *drift*, and the filter's other checks (map matching, gyro agreement) can still
override it if the terrain disagrees. If the model's prediction were instead used to move the reported cursor
directly, a bad prediction would show up on screen immediately with nothing to catch it.

---

## 7 · Why the model needed "gating" between fast and slow roads

The training data is almost entirely slow-to-moderate driving (only ~6% of samples are above 20 m/s / 72 km/h) — the
model has very little experience with sustained motorway speeds. Past the edge of what it has seen, a model doesn't
know it's guessing; it extrapolates silently, and that extrapolation is unreliable specifically in the one regime
(steady motorway cruising) where the *simple* fallback — holding the last GNSS speed — is already nearly perfect,
because speed genuinely doesn't change much there.

So the engine gates: on fast/tagged roads, use the held GNSS speed (cheap, and already close to correct there); below
that, use the learned model, where it has real training density and the held-speed fallback is worst. This is a
**mixture-of-experts** decision made from a measured boundary (the model's own training-data coverage), not an
arbitrary cutoff — and it costs nothing extra, since "hold the speed" was already the baseline being improved on.

---

## 8 · Why "regression to the mean" appeared on its own

Re-reading the last-known-speed table in §3: a fix at 0–14 km/h is predicted to become ~25 km/h later (speeds up); a
fix at 59+ km/h is predicted to become ~66 km/h (stays high, but the *gap* to the overall average shrinks more at the
low end). The model was never told "driving regresses to a typical pace" — it discovered this purely because, in the
training data, that is what actually happens: a vehicle recorded going very slowly (idling in traffic, at a light) is
statistically more likely to be about to speed up than to keep crawling forever, and a vehicle going very fast is more
likely to ease off than to keep accelerating without bound. The tree simply reproduces whatever correlation is
actually present between "how fast right now" and "how fast a while later" in real driving — regression to the mean
is a property of the data, and the model exposes it rather than invents it.

This matters directly for the engine: it's *why* holding the last GNSS speed forever (round 2's approach) is
systematically biased, and why a model that learns this correction, even roughly, beats it.

---

## 9 · Why the attempted bias-fixes made the model worse, not better (entry 46)

Two fixes were tried on the model's known weakness — it under-predicts hard acceleration (it never sees a driver
"flooring it," because that's rare in training data, so it always regresses toward the typical case):

- **Trend features** (giving the model the change in vibration over the last 5 seconds, not just its current level):
  71% of blackouts under the 10% benchmark, against 72% without the trend features — essentially no gain.
- **Prediction expansion** (deliberately pushing predictions further from their own average, to counteract the
  model's cautious shrinkage): made things measurably *worse* — 67% and 66% under the benchmark at two different
  expansion strengths, against 72% unmodified.

**Why expansion backfires.** The model's shrinkage toward a typical value isn't a bug to be undone — it's the
correct, calibrated response to genuine uncertainty. Most of the time, the "cautious middle" guess actually is closer
to the truth than a bold extreme one would be; only rarely is the vehicle actually flooring it. Expanding predictions
away from the mean makes the model *bolder* uniformly, which helps on the rare hard-acceleration blackouts but adds
new error to the much larger number of ordinary ones — the arithmetic doesn't favor the trade. This is the same
principle as §8: the model's shrinkage reflects a real property of the data (most driving is unremarkable), and
fighting that property costs more than it buys back.

---

## 10 · Why one clip's score is unstable but the overall average is trustworthy

Across 500 tuning blackouts, a small change to the filter's settings moves the **median of the whole distribution**
by about 0.3 percentage points — a small, stable, repeatable shift. But the **same change flips 5% of individual
blackouts** across the 10%-benchmark line, in either direction. One specific clip (driver A's off-road case) scored
6.6%, 3.3%, 8.0%, or 26.7% depending on exactly which combination of settings was used — not because any one
combination was secretly "correct," but because that particular blackout sits at a genuine decision boundary where
the filter is nearly evenly torn between two roads, and *any* small nudge decides it differently.

**The consequence:** an individual clip cannot be reliably "tuned" to look good — doing so is measuring which way a
coin toss landed, not measuring a real improvement, and the apparent fix will not survive being re-tested on a
different dataset or even a different random seed. What *can* be trusted is the **distribution** — the median and the
share-under-10% across hundreds of blackouts — because that number is an average over many independent decision
boundaries, and individual coin-flips cancel out in aggregate even though no single one of them is predictable.

This is also why every setting in this project was chosen on the tuning drivers (A, B) using the distribution-wide
numbers, then run **once**, unmodified, on the test drivers (D, E) — never tuned to make a specific test-set clip look
better, because that clip's score is exactly the kind of unstable, coin-flip-sensitive number this section describes.
