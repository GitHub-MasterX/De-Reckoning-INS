# The final solution — what it is, and how we got here

One document, top to bottom: the problem, the finished engine, the numbers, and the path that led to each decision.
Deeper detail lives in the files linked at the end; this is the document to hand someone who wants the whole story in
one read.

---

## 1 · The problem

A vehicle's GNSS signal drops out — a tunnel, a built-up street, a jammer. The phone still has its accelerometer and
gyroscope. The task: estimate where the vehicle is while GNSS is gone, using only those sensors plus a road map,
and get back to within about 10% of the distance travelled by the time GNSS returns.

---

## 2 · The final solution, in one paragraph

The engine is four layers, each one fixing what the layer before it cannot:

1. A **motion classifier** decides moving vs. stationary, so the estimate freezes correctly at a stop (round 1).
2. A **learned speed model** predicts the vehicle's speed every second during the blackout, from the phone's
   vibration, the road under it, and the speed at the moment GNSS was lost — replacing the old approach of assuming
   the speed never changes (round 3).
3. A **road-constrained particle filter** carries hundreds of position hypotheses along the real road network,
   steered by the gyroscope and the learned speed, weighing each hypothesis by how well it matches what the sensors
   and the map both say (round 2).
4. A **reporting layer** turns the filter's internal, sometimes-conflicting beliefs into one steady, physically
   plausible position on screen, instead of a cursor that can jump between roads (round 3).

Full architecture and each layer's own constraints: `ENGINE_LAYERS.md`.

---

## 3 · The final numbers

Test drivers (never used to choose any setting), scored by the error averaged along the whole blackout — not just at
the finish line, which is the metric this project switched to after finding the old one misleading (§6.3):

| | Round 2 alone | **Final engine** |
|---|---|---|
| Path drift, median | 7.0% | **5.9%** (5.8% with the speed-model gate) |
| Blackouts meeting the 10% target | 73% | **80–82%** |
| Worst moment in a blackout, median | 16.3% | **13.0–13.1%** |
| Blackouts that leave the driven road | 45% | **~28–29%** |
| Cursor jumping between roads | 71% of blackouts | **5%** |
| Slow driving (under 40 km/h), path median | 10.6% | **8.2%** |

With the *true* speed (an oracle test, not achievable in deployment): the same engine scores **2.5–3%** — this is the
floor, and the gap between it and 5.9% is almost entirely the remaining speed uncertainty, not a flaw in the map
matching or the reporting.

**On our own recordings** (a two-wheeler, phone in hand, 248 Hz, Tamil Nadu, no speed-limit tags in the map at all):
45 of 111 real blackouts meet the 10% target, the engine beats the round-2 baseline on 85 of 111, and eight
consecutive kilometres of one ride average 6.5% (`TRICHY_REPORT.md`, local only — contains location data).

---

## 4 · How we got here

### 4.1 · Round 1 — the starting point

A motion classifier (accelerometer + gyroscope, gradient-boosted trees) reached 99%+ accuracy telling moving from
stationary. A speed *regressor* on the same sensors was also tried and **lost to simply holding the last known GNSS
speed** — this single result shaped everything that followed. Round 1 cleared ~10% drift on its best driver, using
held speed and no map.

### 4.2 · Round 2 — the map

If sensors can't measure speed directly, use the constraint that a vehicle drives on a road. A particle filter
carries many position hypotheses along a real OpenStreetMap network, scored by how well each one's turning matches
the gyroscope. Gyroscope calibration is fit per phone from GNSS history first — necessary, because one test phone's
gyroscope reported only ~54% of every real turn.

Result: 50–70 km/h driving went from 19.8% to 5.7% error; every driver's median came under 10%. This was the round
that made the whole approach viable.

### 4.3 · Fixing the metric before fixing anything else

Watching the engine's output on the app's replay screen exposed a problem: it was being scored *only at the 1 km
finish line*, which let an estimate wander far off course mid-blackout and still score well if it happened to be
close by the end. The project switched to scoring the **average error along the entire blackout**, and re-picked
which example clips to show accordingly (a rule fixed in advance, never "whichever clip looks best" — the earlier
approach was found to have quietly cherry-picked flattering examples).

Under the honest metric, round 2 scored 73% of test blackouts under 10% — a real number, but with two problems
visible only once you watched the whole path instead of just the ending:

- **42% of blackouts left the driven road** at some point, by 30 m or more.
- **Every blackout contained at least one 1-second jump of the displayed position by tens of metres** — the filter
  believes multiple roads are possible, and the reported cursor could leap between them.

### 4.4 · Round 3, part one — a reporting layer that behaves like a vehicle

Neither problem above was a modelling failure — the filter's internal belief was fine; how it was *displayed* was
not. Two fixes, purely in how the filter's belief becomes an on-screen position, changing nothing about what the
filter itself believes:

- **Mode hysteresis** — the position doesn't switch to a competing road hypothesis until that hypothesis has clearly
  been winning for a little while, not just for one instant.
- **A speed-limited cursor** — the displayed position can't move faster than a real vehicle could, closing gaps
  quickly along the direction of travel but never sideways, so a road-hypothesis change shows up as motion, not a
  teleport.

Cursor jumps fell from 71% of blackouts to 5%; blackouts leaving the road fell from 45% to 29%; and, as a side
effect of no longer chasing bad hypotheses, the drift itself improved too (7.0% → 5.9% median).

### 4.5 · The hunt for speed — eight physics ideas, all of them failed

With the reporting fixed, what remained was almost entirely speed error — the filter fixes *which road*, never *how
far along it*, and "how far along it" is exactly what speed error corrupts. Eight physics-based ways to measure or
predict speed were tried and measured on the tuning drivers only:

| Idea | Result |
|---|---|
| Integrate accelerometer readings into speed | worse than assuming speed never changes, at every time window tried |
| Speed from turn-rate ÷ steering geometry | accurate only on phones that could physically feel a corner — 2 of 4 phones couldn't |
| Speed from the map's road curvature | the map's curvature barely matched the vehicle's actual path (correlation 0.22) |
| Decay speed toward the road's tagged limit | limits are routinely exceeded; no improvement |
| Tighten the filter's own speed-limit penalty | measurably worse |
| A learned "speed regresses to the mean" rule | helped on some blackouts, hurt on others; net negative |
| Widen the filter's initial speed uncertainty | badly worse — the map's turns are too sparse to pick the right hypothesis back out |

The reason all eight failed is physical, not a tuning shortfall: the accelerometer samples at 10 Hz (this project's
main dataset) or 248 Hz (our own phone), while wheel and engine vibration sit at frequencies that **alias** at normal
driving speeds — the sensor doesn't just miss that information, it misreads it as a different, wrong signal, and no
formula can undo that afterward. This was confirmed directly, not assumed: integrating the signal was tested and
found worse than doing nothing at every window length.

### 4.6 · Round 3, part two — the learned speed model

The insight that broke the deadlock: a model doesn't need to resolve the destroyed frequency information. A
gradient-boosted tree model (same family as round 1's classifier — **not a neural network**; this project does not
use one anywhere) was trained on four kinds of evidence, none of which require reading the broken part of the signal:

- **coarse vibration energy** — not which exact frequency, just how much shaking overall (this survives aliasing
  well enough to still climb reliably with speed, even though its exact magnitude is degraded — verified against a
  real recording, not assumed: `ROUND3_THEORY.md` §2)
- **sudden jerk** — a time-domain spike, unrelated to frequency at all
- **the road map** — class, tagged limit, how built-up the area is; entirely independent of the sensor
- **the speed at the moment GNSS was lost**, and how long ago that was

Trained on one set of drivers, tested on a different set never used for training: it predicts speed 30 seconds
ahead at **3.15 m/s error, against 6.09 m/s for simply holding the last speed** — and **2.47 m/s against 6.25 m/s**
specifically when the vehicle was slow at the moment of loss, which is where the engine had failed worst.

Full mechanism — the physics failures explained in depth, every feature relationship shown with real numbers, why a
tree-based "step" model beats a smooth formula, how the model's output feeds into the particle filter, why it needs
to be switched off on fast roads (it was trained mostly on slower driving and would otherwise guess blindly there),
and why one individual test clip's score can't be trusted the way a result averaged over hundreds can:
`ROUND3_THEORY.md` and `ROUND3_REPORT.md`.

### 4.7 · What was tried and rejected for the three still-hardest cases

Three real blackouts still miss the 10% target even in the finished engine. Each was diagnosed by substituting the
true value for one input at a time to isolate the cause, and several targeted fixes were tried:

- A rule keeping the filter on the same physical road through a junction — genuinely helped the general case, made
  no measurable difference on the test set (motorway-heavy, where the failure mode is different).
- A penalty for the filter switching to a smaller class of road — helped one case, badly broke another that
  legitimately needed to make that exact switch.
- Giving the model the *trend* of the vibration, not just its current level — no measurable improvement.
- Deliberately exaggerating the model's predictions to counter its natural caution — made things measurably worse;
  the model's caution turns out to be the statistically correct response to how rarely extreme driving actually
  happens in the data.

The finding that mattered more than any one fix: small setting changes move the *overall* result by a fraction of a
percentage point, while flipping **individual** blackouts across the pass/fail line 5% of the time — one real
blackout scored anywhere from 3.3% to 26.7% across otherwise-reasonable setting choices, because that specific
moment sits on a genuine coin-flip between two roads. This is why every setting in this project was chosen using
the aggregate result across hundreds of blackouts, never a single clip's score, and applied exactly once,
unmodified, to the drivers never used for tuning.

### 4.8 · Validating outside the original dataset

Everything above was built and tuned on IO-VNBD — cars, mostly 10 Hz sensors, England. To check it wasn't an
artifact of that one dataset, the whole pipeline (classifier → learned speed → map filter → reporting) was re-run
on our own recordings: a two-wheeler, phone hand-held, 248 Hz, Tiruchirappalli. Trained on one ride, tested on a
separate ride over the same corridor.

Findings that differ from England, and why:

- **Tamil Nadu's map carries essentially no speed-limit tags** — the England-tuned rule ("trust the held speed on
  fast tagged roads") never fires there; the engine instead gates on the vehicle's own last known speed, which needs
  no map tags at all.
- **The route has far fewer turns per kilometre** than the English test routes, so the map gets fewer chances to
  correct position sideways — on this corridor, the map-free estimate actually beat the map-assisted one.
- **Speed-breaker road bumps are detectable in the 248 Hz stream** (4 of 5 mapped ones found) and are invisible at
  10 Hz — a genuinely India-specific landmark opportunity. An attempt to also self-map *unmapped* bumps from
  repeated passes looked promising until a proper control test showed most of the apparent matches were
  coincidence; this is flagged as unproven, not claimed as working.

Despite the harder conditions (no map tags, fewer turns, no working stop detector for a two-wheeler yet), the
learned speed model carried over directly and produced the same shape of improvement as in England, concentrated in
slow, stop-start riding — exactly where Indian traffic conditions are worst for the old held-speed approach.

---

## 5 · Honest limits of the final solution

- **The remaining error is a speed problem, not a mapping problem.** With true speed, the same engine scores
  2.5–3%; the 5.9% actually achieved is almost entirely the residual uncertainty in predicted speed.
- **Two named failure modes remain distinct from each other:** a vehicle accelerating hard right after GNSS is lost
  (the model, trained mostly on typical driving, under-predicts this), and the filter occasionally locking onto the
  wrong parallel road at a junction (which no amount of correct speed can fix by itself — even a perfect speed input
  leaves ~21% error on that specific failure shape).
- **The gap between the achieved result and a theoretically perfect chooser between the engine's own methods is
  about eight percentage points** — and that gap was shown to be fundamentally unpredictable in advance from any
  information available at the moment GNSS is lost, not a limitation of the modelling effort.
- **Self-mapped, unofficial road landmarks are a promising but unproven idea**, not a working feature.
- **No working stop detector exists yet for a two-wheeler** — the current classifier was trained on car data.

---

## 6 · Where everything lives

| Topic | File |
|---|---|
| This document | `FINAL_SOLUTION.md` |
| Full numbered history of every step, with every measurement | `EXECUTION_LOG.md` |
| The four-layer architecture in depth, per-layer constraints | `ENGINE_LAYERS.md` |
| Round 2's design and evaluation rules | `ROUND2_REPORT.md`, `MAP_LANDMARK_APPROACH.md`, `DECISIONS.md` |
| The learned speed model's mechanism, in full technical detail | `ROUND3_REPORT.md` |
| The learned speed model explained in plain terms, worked examples, all ten "why" questions | `ROUND3_THEORY.md` |
| The narrative version of round 3 (written before the speed model existed) | `HOW_WE_GOT_HERE.md` |
| Results on our own recordings — local only, contains location data | `TRICHY_REPORT.md` |
| Project overview and status | `PROJECT_SUMMARY.md`, `README.md` |
| How to pick this work back up on another machine | `HANDOFF.md` |
