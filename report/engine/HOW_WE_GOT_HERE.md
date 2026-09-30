# How we got here — the road from round 1 to the merged engine

This is the story of the work in order, including the things that did not work, because most of the useful findings are
negative ones. The engineering detail of the finished engine is in `ENGINE_LAYERS.md`; every step with its raw numbers
is in `EXECUTION_LOG.md`.

---

## 1 · Round 1 — what we started with

The problem: a vehicle loses GNSS, and the phone's IMU has to carry the position until it returns. The benchmark is
about 10% of the distance travelled, at 1 km of blackout.

Round 1 built two things and learned one hard lesson.

- **A motion classifier** on accelerometer and gyroscope windows — is the vehicle moving or standing still? It reaches
  **99.0–99.6% accuracy** with 93% recall on stationary moments, on every driver. It is still in the engine today,
  unchanged and never retrained.
- **A speed regressor** on the same IMU — how fast is the vehicle going? It **lost to simply coasting on the last GNSS
  speed** and was dropped.

That second result set the shape of everything after it, though we did not understand why until round 3.

Round 1 cleared roughly 10% drift at 1 km for driver E, measured as distance-travelled error without a map.

## 2 · Round 2 — the map

If the IMU cannot supply speed, use structure instead: a vehicle is on a road, facing along it.

- Gyro calibration from GNSS history before each blackout — axis, scale and bias, fitted per phone. This matters more
  than it sounds: driver E's phone reports about **54% of every real turn**.
- An OpenStreetMap road network for England (29,389 km), and a **road-constrained particle filter**: 500 hypotheses
  carried along real roads, weighted by how well the gyro's turning matches the road's turning.
- Tuning on drivers A and B only; one run on D and E, with nothing changed afterwards.

Result: 2D error at 1 km in the 50–70 km/h case fell from **19.8% to 5.7%**, and every driver came under 10% on the
median. This is the round that made the approach work.

## 3 · The metric changes — and the numbers get honest

Watching replay clips on the phone, the rider noticed the cursor sitting far off the road for tens of seconds and
still scoring a few per cent. Round 2 scored the error **at a checkpoint** — where the estimate stood when the vehicle
had covered 1 km. That rewards an estimate that wanders and happens to be near the vehicle when the clock stops.

From that point the primary number became the **average error along the whole blackout**, with the end-point figure
reported second. The two correlate at only r = 0.76, and 13% of blackouts that "pass" at the end average 14% along the
way, reaching 36% at their worst.

Re-measured that way, round 2 sits at **7.0% median with 73% of blackouts under 10%** on the test drivers.

A second consequence: the app's demo clips had been chosen *by how they ended*, which is the worst possible sample for
a path metric — 12 of 12 passed at the end, 5 of 12 along the path. Clip selection was replaced by a rule fixed in
advance.

## 4 · Round 3, part one — what a reviewer actually sees

Measuring the whole path exposed two behaviours no checkpoint metric could show:

- **42% of blackouts leave the driven road** by more than 30 m, the worst of them by 104 m.
- **Every single blackout contains a teleport** — the reported position moving more than 20 m in one second, median
  worst step 84 m. The filter believes several roads at once and reports whichever group of guesses is strongest, so
  when the strongest changes, the cursor crosses the gap instantly.

Neither is a modelling error; both are reporting errors. The fix was a reporting layer: **mode hysteresis** (a rival
road must be clearly better for two updates before the cursor moves) and a **speed-limited cursor** (the reported
point chases the filter at a speed a vehicle could manage).

That first attempt removed the teleports and introduced a new problem — the cursor trailed 169 m behind where round 2
had trailed 83 m, because round 2 had been *using* its teleports to catch up. The answer was to make catch-up
**directional**: fast along the way the cursor is already travelling (a gap there is a place on the same road), slow
sideways (a gap there means the filter changed its mind, and hurrying is the jump we removed).

Result on the test drivers: path **7.0% → 5.9%**, blackouts under 10% **73% → 80%**, off-route **45% → 29%**,
teleports **71% → 5%**, worst step **84 m → 37 m**.

## 5 · The hunt for speed — eight ideas, seven dead

With the reporting fixed, everything left was speed. Position error splits into across-track (which road — the map
fixes it) and along-track (where on it), and along-track error is exactly the integral of the speed error.

Measured, on the tuning drivers, all of them properly and all of them negative:

| Idea | Outcome |
|---|---|
| Speed from map curvature (`v = turn rate ÷ curvature`) | 11–14 m/s RMS; map curvature matches the driven curvature at r = 0.22 |
| Accelerometer turn readings (`v = sideways force ÷ turn rate`) | 2.7–4.0 m/s RMS **where the phone can feel a corner** — but 24% of blackouts, 3 readings each |
| Integrating forward acceleration | worse than assuming no change, at every window from 5 s to 30 s |
| Vibration energy → speed, fitted per session | fits its own history at r = 0.78, transfers at 4.76 m/s against holding's 3.00 |
| Decaying toward the tagged speed limit | 10.9% → 11.2%; drivers exceed limits routinely |
| Tightening the filter's speed-limit penalty | 65% → 50% under 10% |
| Regression to the mean, learned (`v(60 s) = 0.59·v0 + 5.6`) | better RMS, worse benchmark — it helps rare big decelerations and hurts the common steady case |
| Widening the filter's own speed hypotheses | 65% → 38% under 10%; the map's turns are too sparse and too alike to select the right hypothesis back |

Two things survived and were kept because they cost nothing where they do not apply: the turn readings given to the
filter as a measurement, and regression to the mean restricted to slow starts.

Along the way we found why the accelerometer keeps losing, and it is two separate walls:

- **Sampling rate.** At 10 Hz you see up to 5 Hz. Wheel rotation at 60 km/h is about 9 Hz; engine firing is 25–50 Hz.
  Both alias into the band where the vehicle's own acceleration lives.
- **The individual phones.** How much of real cornering force each driver's accelerometer registers: **B 0.80,
  A 0.42, D 0.12, E 0.06**. Gravity reads 9.86 m/s² on all four, so this is damping or filtering, not units. The two
  phones the competition scores us on are the two worst instruments in the set.

## 6 · Round 3, part two — the learned speed

The rider pushed back: why can a network not learn the velocity? Two experiments said no, and both were narrower than
the question:

- context without the IMU (698 blackout starts) — gradient boosting was **worse than holding** at every horizon;
- the IMU without the map (per-session linear fit) — **4.76 m/s against holding's 3.00**.

The full version is the one that worked. Given **the shaking** (a 2 s window of accelerometer and gyroscope energy
across four frequency bands), **the map under the car** (class, tagged limit, how built-up), and **the speed at the
last fix with how long ago it was**, a gradient-boosted model trained on 40,000 samples a second apart predicts the
speed 30 s later at **3.15 m/s RMS against 6.09 for holding** — and **2.47 against 6.25** when the car was slow at the
fix, which is where the engine fails.

It never measures speed. It recognises a context: this much shaking, on this kind of road, this built-up, this long
after a fix that read 8 m/s. Shaking alone is confounded by road surface; a map alone cannot tell a jam from free
flow; a stale speed alone goes stale. Together they carry real information.

Inside the engine, tuning drivers, leave-one-session-out so no blackout is scored by a model that saw its session:
under 10% **66% → 72%**, path 7.0% → 6.4%, off route 26% → 20%.

One run on the test drivers, model trained on A and B only:

| | under 10% | path median | worst moment |
|---|---|---|---|
| held speed | 80% | 5.9% | 13.1% |
| learned everywhere | 75% | 6.3% | 14.1% |
| learned below 72 km/h | **82%** | **5.8%** | **13.0%** |

By condition, held → gated: **slow 43% → 58%** (path 12.0% → **8.2%**), mixed 52% → 60%, **50–70 65% → 70%**,
fast 88% → 89%. The gate exists because only 6% of the model's training samples are above 20 m/s, so on a motorway it
extrapolates while holding is nearly perfect there.

## 7 · Should an arbiter choose between them?

If round 2 wins sometimes and the model wins usually, learn which to trust. Measured on 400 tuning blackouts:

| Strategy | under 10% | path median |
|---|---|---|
| always hold | 65% | 7.1% |
| **always use the model** | **70%** | **6.1%** |
| learned arbiter | 69% | 6.4% |
| hand-made rule (hold on fast roads) | 69% | 6.4% |
| **perfect chooser (oracle)** | **78%** | **5.1%** |

The headroom is real — a perfect chooser would gain eight more points — but the choice is **not predictable**: the
arbiter is right 54% of the time, a coin flip, with road class, density, limit, recent acceleration, gyro activity and
the model's own prediction all available to it. Which expert wins depends on what the driver does during the blackout,
which is the same unobservable we have been chasing since round 1. **Use the model everywhere; do not arbitrate.**

## 8 · Where it stands

Test drivers, 2,421 blackouts, error averaged along the whole blackout:

| | round 2 | merged engine |
|---|---|---|
| path drift, median | 7.0% | **5.8%** |
| blackouts under 10% | 73% | **82%** |
| worst moment, median | 16.3% | **13.0%** |
| leaves the road | 45% | ~28% |
| cursor teleports | 71% | **5%** |
| slow driving (under 40 km/h), path | 10.6% | **8.2%** |

And the honest remainder, in three named failure modes:

1. **Hard acceleration from a slow fix.** The model predicts what a context usually does and cannot see a driver
   flooring it. Its errors are one-sided, so they accumulate rather than cancel.
2. **Wrong-road lock-on.** On one test blackout the filter commits to a parallel road and **even perfect speed leaves
   21% error**. Speed cannot fix a road choice.
3. **What no one on board can observe.** The eight-point gap between our result and a perfect chooser is the driver's
   intention, and no sensor in this dataset measures it.

What would remove each: a wheel-speed or OBD feed for (1) — with true speed the same engine sits at 2.5–3%; junction
disambiguation for (2); and for (3), a 248 Hz IMU rigidly mounted, where the same geometric methods were three times
cleaner on our own recordings.
