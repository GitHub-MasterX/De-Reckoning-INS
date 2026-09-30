# The engine, layer by layer — what each one does, what it cannot do, and how the next one covers it

Four layers estimate the position during a GNSS blackout. Each supplies exactly what the layer before it lacks, and
each has a constraint the next one is there to absorb. The story of how they came about is in `HOW_WE_GOT_HERE.md`;
the numbers behind every claim are in `EXECUTION_LOG.md`.

```
    IMU (10 Hz)        ─┐
                        ├─► 1. stop classifier ─► moving or standing still
    IMU + map + v0     ─┤
                        ├─► 2. learned speed   ─► how fast, second by second
    gyro + road network─┤
                        ├─► 3. particle filter ─► which road, and where along it
                        │
                        └─► 4. reporting layer ─► what the user is shown
```

---

## Layer 1 · The stop classifier — *is it moving?*

**What it does.** Round 1's gradient-boosted model reads 2-second windows of accelerometer and gyroscope and decides
moving or stationary. When it says stationary the position is frozen, so no drift accumulates at a red light.

**How well.** 99.0% accuracy on the tuning drivers, 99.6% on the test drivers; 93% of stationary moments recognised,
96.7–99.1% precision. It has never been retrained since round 1 and works on all four phones.

**Its constraint.** It answers a yes/no question. It says nothing about *how fast* when the answer is yes — and a
vehicle that slows from 75 to 20 km/h is "moving" the whole time, which is exactly the case that breaks everything
downstream.

**Who covers it.** Layer 2.

**Worth on its own:** on stop-and-go blackouts it takes the error from 21.4% to 17.6%.

---

## Layer 2 · The learned speed — *how fast?*

**What it does.** A gradient-boosted model predicts the vehicle's speed each second from three sources that are
individually useless and jointly informative:

| Input | What it contributes | Why it is not enough alone |
|---|---|---|
| **The shaking** — accelerometer and gyroscope energy over a 2 s window, in four bands to 5 Hz, plus jerk and per-axis spread | vibration grows with speed | confounded by road surface: a smooth road at speed looks like a rough road slowly |
| **The map under the car** — road class, tagged speed limit, how many distinct roads lie within 40 m | what this kind of road usually carries | cannot tell a traffic jam from free flow |
| **The last GNSS fix** — the speed it reported, and how long ago | where the vehicle started from | goes stale: the whole problem |

**How well.** Predicting the speed 30 s after a fix: **3.15 m/s RMS against 6.09 for holding that speed**. The map is
worth 0.4 m/s of that (IMU + last speed alone: 3.59). Where the vehicle was slow at the fix: **2.47 against 6.25**.
Trained on drivers A and B only, and it transfers to D and E, whose phones are measurably worse instruments.

**Its constraints, all three real.**

1. **It predicts typical behaviour, not intent.** A driver accelerating hard from a slow fix is invisible — the model
   answers with what that context usually carries. Both remaining failures in the demo set are this.
2. **Its errors are one-sided** (it shrinks toward the typical), so they integrate into lag instead of cancelling.
3. **It must not be used outside its training range.** Only 6% of its training samples are above 20 m/s, so on a
   motorway it extrapolates, while holding the last speed is nearly perfect there (1.85 m/s RMS). It is therefore
   **gated: hold on fast roads, use the model elsewhere.**

**Who covers it.** Layer 3 — the map constrains a wrong speed to at least stay on a real road, and turns re-anchor the
position along it.

**Worth on its own:** slow-driving blackouts go from 43% under the benchmark to 58%, path 12.0% → 8.2%.

---

## Layer 3 · The road-constrained particle filter — *which road, and where on it?*

**What it does.** 500 hypotheses are carried along the OpenStreetMap network from the last fix. Each moves at the
speed layer 2 supplies and turns by the gyro's calibrated turn rate; each is weighted by how well the road's own
turning matches the gyro's over 2-second windows, by how well its direction agrees with the heading, and by whether
its speed is plausible for that road. When the hypotheses disagree too much, they are resampled; when the map explains
nothing for several updates, the filter restarts itself on the road nearest the dead-reckoned position.

The gyro it trusts is calibrated per phone on GNSS history before the blackout — necessary, because driver E's phone
reports about 54% of every real turn.

**What it buys.** On the same blackouts, error without the map against with it: 24.6% → 13.2%, 47.6% → 36.1%,
49.8% → 16.6%. Roughly half.

**Its constraints.**

1. **A map fixes position across a road, never along it.** It cannot tell how far you have travelled — that is
   entirely layer 2's job, which is why speed dominates the remaining error.
2. **Junctions are ambiguous.** Arriving at a fork slightly out of position, two branches can fit the observed turn
   equally well. Once it commits to the wrong one, it is wrong until it re-seeds — and on one test blackout **even
   perfect speed leaves 21% error** for this reason.
3. **Its guesses must contain the truth.** The seeding spread is deliberately tight (4% of the GNSS speed); widening
   it to cover large speed errors makes results much worse (65% → 38% under the benchmark), because the map's turns
   are too sparse to select the right hypothesis back.
4. **It believes several things at once**, and the one it reports can change abruptly.

**Who covers it.** Layer 4 covers (4). Nothing yet covers (2) — that is the next round's work.

---

## Layer 4 · The reporting layer — *what does the user see?*

**What it does.** It never changes what the filter believes; it changes what is displayed.

- **Mode hysteresis.** The group of guesses that had the cursor keeps it until a rival is clearly better (1.3×) for
  two updates running, or until the filter abandons it (weight under 5%, or left more than 80 m behind).
- **A speed-limited cursor.** The reported point chases the filter at a speed a vehicle could manage
  (1.5 × its believed speed, or speed + 3 m/s). A standing gap is closed in about 6 s, capped at 3× the vehicle's
  speed, and **only along the direction the cursor is already travelling** — a gap ahead is a place on the same road,
  a gap sideways means the filter changed its mind about the road, and hurrying there is the jump being removed.

**What it buys.** Teleports fall from **71% of blackouts to 5%** and the worst single step from **84 m to 37 m**;
blackouts leaving the road fall from 45% to 29%; and because the cursor stops chasing bad hypotheses, the drift falls
too (7.0% → 5.9%).

**Its constraint.** It lags: the cursor sits about 18 m further back than round 2's, which earned its 2 m by jumping.
On a vehicle accelerating hard, that lag costs real accuracy — one demo clip is worse for this reason alone.

**Who covers it.** Nobody. It is a deliberate trade: a credible cursor that is slightly behind, instead of an
incredible one that is occasionally ahead.

---

## How the layers cover for each other

| Failure | The layer that would suffer | The layer that absorbs it |
|---|---|---|
| Drift while standing at a light | dead reckoning integrates noise | **1** freezes the position |
| Vehicle changes speed after the fix | **1** only knows it is moving | **2** predicts the new speed from context |
| The predicted speed is wrong | **2** accumulates along-track error | **3** keeps it on a real road, and a turn re-anchors it |
| The map's roads are ambiguous | **3** may hold several, or the wrong one | **4** refuses to show a rival until it is convincing |
| The filter changes its mind | **3** reports a jump across two roads | **4** makes the cursor travel there like a vehicle |
| The model is outside its training range | **2** extrapolates on motorway | the gate hands the job back to the held GNSS speed |

**And what nothing covers, stated plainly.** A driver accelerating hard from a slow fix; a wrong branch taken at an
ambiguous junction; and the eight-point gap between this engine and a perfect chooser between its own experts, which
is the driver's intention. The first needs a wheel-speed or OBD feed — with true speed the same engine scores 2.5–3%.
The second needs junction disambiguation. The third needs a sensor nobody in this dataset has.

---

## Where each layer lives

| Layer | Code |
|---|---|
| 1 · stop classifier | `core/motion.py`, model from round 1 (`deploy_all`); Kotlin: `live/engine/MotionModel.kt` |
| 2 · learned speed | `round3_learned_speed.py` (training and use), features from `round3_vibration_speed.py`, map features from `map_feats` |
| 3 · particle filter | `core/particle.py` (`speed_target=` and `speed_obs=` are round 3's additions; with both unset it reproduces round 2 exactly), road network in `core/roadnet.py` |
| 4 · reporting layer | `core/smooth.py` — `ModeTracker` and `smooth_track`; settings in `out/round3_report_choice.json` |
| evaluation | `round3_path_metric.py`, `round3_excursions.py`, `round3_report_fix.py`, `round3_arbiter.py` |
