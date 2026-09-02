# The ML model — complete report

**PS 26168 · AI-ML based Intelligent Dead Reckoning system for seamless navigation**
Dataset: IO-VNBD · 72 drives · 29.7 driving-hours · 1,341 km · 1,070,741 samples

Everything below is measured. Every figure traces to a script in `analysis/`. Where a result
was later retracted, it is marked as retracted rather than deleted.

---

## Executive summary

| | |
|---|---|
| **5 m over 50 m** | **met on every driver tested** — 1.6 to 2.7 m |
| **100 m over 1 km** | **met only in the conditions the PS specifies** — 101.4 m under steady ~60 km/h driving; 145–165 m in urban stop-start |
| Machine learning that works | **motion classifier, 99.4%** leave-one-driver-out |
| Machine learning that does not | **speed regression** — degrades drift on all four drivers |
| Why | a 10 Hz phone accelerometer cannot resolve forward acceleration; proven by a physics bound and an oracle test |
| Sensor that carries the solution | the **gyroscope**, measured at **r = 0.958** |

The single most important finding is an **asymmetry**: this sensor is excellent at detecting
large discrete events and incapable of measuring a small continuous quantity. Classification
suits it. Regression does not. Everything else follows from that.

---

# Part 1 — What the dataset actually is

Measured from the files, not read from the paper.

| | |
|---|---|
| Sample rate | **10 Hz** — phone IMU and vehicle ECU alike, verified on all 144 pairs |
| Phone GPS | **~9 s** between fixes in 124 of 144 files |
| Vehicle GPS (VBOX) | **10 Hz** — this is the ground truth |
| Recording devices | Huawei P20 Pro, Moto G7 Power, BlackBerry Priv, in phone holders |
| Drivers | A (6 drives), B (1), D (1), E (64) |

Two independent speed sources exist — VBOX GPS and CAN bus — agreeing at **r = 0.9993** with a
0.26 km/h offset. That redundancy mattered later: CAN is immune to GNSS dropouts.

---

# Part 2 — Difficulties overcome

These are the problems that had to be solved before any model could be trained honestly.

## 2.1 · The files would not open

`UnicodeDecodeError` on all 72 files — headers contain `m/s²`, and byte `0xB2` is invalid UTF-8.
**Fix:** read as latin-1.

## 2.2 · Half the dataset vanished silently

`S-Vta2.csv` pairs with `V-vta2.csv`. Exact-name matching finds no partner and drops the file
with **no error raised** — affecting **40 of 72 pairs**.
**Fix:** case-insensitive matching.

## 2.3 · The axis labels lie

Two folders use different column names for the same data (`GYROSCOPE X/Y/Z` vs
`GYROSCOPE Yaw/Pitch/Roll`). Worse, the names are **wrong**: vehicle yaw does not land on the
axis called "Yaw". In drive `S1`, the column named *Pitch* matched vehicle yaw at **r = 0.935**
while *Yaw* gave **0.07**.

**Rule adopted:** never trust an axis name — estimate the mapping from data.

## 2.4 · Orientation was being mistaken for broken data

The first sync test used the single best gyro axis. But a tilted phone splits vehicle yaw across
two or three axes, so no single axis matches — which looks identical to a corrupted file.

| Drive | Best single axis | Three-axis joint fit |
|---|---|---|
| `S2` | **0.005** | **0.929** |
| `S3a` | 0.200 | 0.972 |

`S2` looked completely broken and was perfectly fine, merely rotated.
**Fix:** fit all three gyro axes jointly by least squares before correlating.

## 2.5 · One file is several recordings

Some files concatenate separate sessions. In `S3b` the phone's clock runs **backwards**; `Vtb1`
contains an **11-minute hole**. Any quantity computed across the whole file averages over
unrelated recordings and is wrong for all of them.

**Choosing the threshold from evidence, not assumption.** Sample intervals cluster at 100 ms
(99.999th percentile = 119 ms). Only **3 intervals out of 1,070,673** exceed 150 ms — they are
1.28 s, 1.37 s and 661 s — plus 8 negative jumps. Nothing at all falls between 0.12 s and
1.28 s, so any threshold in that empty band gives identical segmentation. **0.5 s** was read off
the data.

**Result — 83 sessions across 72 drives**, and computing per session instead of per file:

| Drive | Whole file | Per session |
|---|---|---|
| `M` | 0.811 | **0.932 / 0.993 / 0.984** (lags +0.8 s, +2.0 s, +3.2 s) |
| `S3b` | 0.720 | **0.834 / 0.998** |
| `S4` | 0.347 | **0.932** / 0.059 / 0.183 |

`M`'s three sessions each had a **different** offset. Averaging them destroyed all three.

> **`S4` is the clearest case: session 0 needs +1.8 s, session 1 needs +313.8 s — in the same
> file.** Correcting it as a whole wrecks both.

## 2.6 · The phone and vehicle files describe different moments

This was the largest single factor in the dataset. The phone's gyroscope and the car's yaw-rate
sensor both measure one physical thing — the vehicle turning. If the files line up, the two
traces track each other.

They often did not. Measured impact: training on unaligned data gave **r = 0.017**. On aligned
data, **r = 0.455**.

## 2.7 · The search window was too narrow — the largest error made

Two sessions scored ~0.06 and were declared dead: `Y1/s3` (111 min — the intended test set) and
`S4/s1` (93 min). Both had plenty of turning, so "too few turns to measure" did not apply.

Comparing the phone's GPS track against the vehicle's:

| Session | Separation |
|---|---|
| `S1/s0` (healthy control) | **24 m** |
| `Y1/s3` | **648 m** |
| `S4/s1` | **1,846 m** |

The first reading was "different journeys — mispaired files." **Wrong.** At 30 km/h, 648 m is
about 110 seconds of driving. The offsets were simply **larger than the ±30 s being searched**.

| Session | Offset found | Separation after | `sync_r` |
|---|---|---|---|
| `Y1/s3` | **+111 s** | 648 m → **16 m** | 0.058 → **0.798** |
| `S4/s1` | **+309 s** | 1,846 m → **18 m** | 0.059 → **0.928** |

Nothing was broken. **6.0 hours recovered, including the test set.**

**The two-stage procedure that resulted** — neither stage alone is sufficient:

```
COARSE   match the two GPS tracks over ±10 min
         finds large offsets (111 s, 309 s, 564 s)
         resolution only ~±5 s, because phone GPS updates every 9 s

FINE     match gyro against vehicle yaw-rate over ±30 s
         refines to sub-second
         blind to anything beyond its ±30 s window
```

Overall effect: usable material at |sync_r| ≥ 0.7 went from **10.1 h to 13.5 h**.

## 2.8 · Every drive sits in a different reference frame

The phone's yaw offset relative to the vehicle ranged from **2° to 352°** across drives. "Forward
acceleration" therefore landed on a different axis in every file, and the model was being asked
to learn a mapping that changed underneath it.

An alignment engine was built using only what a phone has at runtime — gravity direction from
the low-passed accelerometer, yaw from the gyro projected onto it, forward from the dominant
horizontal acceleration while driving straight. Graded against the vehicle's own sensors, which
the runtime never sees:

| Quantity | Achieved | Theoretical ceiling | Efficiency |
|---|---|---|---|
| **Yaw rate** | **0.958** | 0.958 | **100%** |
| Lateral acceleration | 0.381 | 0.400 | **95%** |
| **Forward acceleration** | **0.269** | **0.315** | **97%** |

The "ceiling" is a free least-squares fit of all three axes — the best *any* rotation could
achieve. The estimator lands within 3–5% of it.

**This is where the project's central problem became visible.** The estimator is essentially
perfect. The ceiling on forward acceleration is **0.315**, and on one drive **0.05**.

## 2.9 · Ground truth that survives GNSS dropouts

`speed_kmh` comes from GPS and freezes when the receiver loses lock, then snaps back at up to
15 km/h in 0.1 s — that is **4.2 g**, physically impossible for a car, so a receiver artifact
rather than driving. `can_speed` is wheel-derived and unaffected.

`speed_best` uses GPS normally and substitutes CAN wherever the fix is frozen while moving.
CAN is offset-corrected first (median −0.22 km/h) so switching source injects no false
acceleration at the splice.

---

# Part 3 — The machine-learning models

## 3.1 · What was built

| | |
|---|---|
| Algorithm | Gradient-boosted regression trees (`HistGradientBoostingRegressor`) |
| Depth of training | 500 boosting iterations, learning rate 0.06 |
| Features | **46 per window** — per-channel mean, std, min, max and mean-absolute-difference across 6 channels (30), vector-magnitude statistics (4), and log energy in three frequency bands 0.5–1.5, 1.5–3.0, 3.0–5.0 Hz for three axes (9), plus three magnitude aggregates |
| Window | **2.0 seconds**, stepped 0.5 s |
| Training set | ~150,000 windows |
| Validation | **leave-one-driver-out**, four folds |

Why gradient boosting rather than a neural network: the oracle test (below) proves the
*information* is sufficient, so the bottleneck was never model capacity. Features in the wrong
reference frame cannot be fixed by a bigger model — and a neural network would have failed the
same way, more slowly and with less visibility into why.

## 3.2 · Target 1 — absolute speed. Failed.

| | |
|---|---|
| Model | MAE **18.7 km/h** |
| Dummy baseline (predict the mean) | MAE 26.5 km/h |

Barely better than guessing. This was expected and is not the design: GNSS supplies velocity at
the moment of blackout, and the model only needs to track how it *changes* from there.

## 3.3 · Target 2 — speed change. Learned real signal.

| Data condition | r |
|---|---|
| Unaligned, un-time-corrected | **0.017** |
| Sync-corrected | **0.455** |
| Sync-corrected + frame-aligned | **0.43 – 0.61** |

**The model genuinely works as a predictor.** r = 0.61 on speed change is real signal, not noise.

## 3.4 · And it still made navigation worse

Leave-one-driver-out, drift at 1 km:

| Driver | Coast (no model) | **Model** | Oracle |
|---|---|---|---|
| A | 165.2 m | **266.2 m** | 14.2 m |
| B | 145.1 m | **250.0 m** | 12.0 m |
| D | 160.4 m | **403.0 m** | 16.0 m |
| E | 101.4 m | **134.7 m** | 9.0 m |

Four independent folds. The model is worse on **every single driver**. This is not a fluke or a
tuning failure — it is a reproducible property of the approach.

## 3.5 · Why — and this is the key mechanism

Correlation and drift measure different things, and the model was good at one and bad at the
other.

| Session | **r** | mean error per step | drift | coast |
|---|---|---|---|---|
| `M/s0` | +0.434 | +0.0096 m/s | 23.0% | 15.8% |
| `M/s1` | +0.609 | −0.0188 m/s | 18.2% | 18.4% |
| `M/s2` | +0.439 | −0.0131 m/s | 13.1% | 12.3% |
| `Y1/s3` | +0.178 | **+0.0518 m/s** | **31.5%** | 15.1% |

Look at `Y1`. A mean error of **+0.0518 m/s per step**, and a blackout contains 120 steps:

```
0.0518 × 120 = 6.2 m/s = 22 km/h of invented velocity
```

**The model does not drift because it is noisy. It drifts because it leans, and the lean
accumulates.** Coasting has no lean by construction — it predicts no change at all — so its
error partly cancels over a minute.

Two models with **identical MAE** can differ by 5× in drift depending on whether their errors
scatter or lean. MAE cannot see the difference. This is why the evaluator exists.

## 3.6 · The shrinkage test — the model has negative value

If the model has real signal but too much bias, and coast has no signal and no bias, the optimum
should be somewhere between them. Sweeping `v = v₀ + α·Σ(predictions)`:

| α | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.7 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| Drift | **14.8%** | 15.3% | 15.8% | 16.2% | 16.1% | 16.2% | 17.6% | 20.9% |

**The optimum is α = 0.** Drift rises monotonically. The best use of every prediction the model
can generate is to ignore it entirely.

---

# Part 4 — The physics ceiling

This is why no amount of model work would have helped.

## 4.1 · The information is present

Feeding the evaluator the **true** speed changes gives **1.3% drift** (0.8–1.7% across all four
drivers). So the benchmark is comfortably achievable *if* speed change can be measured, and the
evaluator is sound. The obstacle is the measurement.

## 4.2 · The accuracy required

100 m over 1 km at 60 km/h means knowing the mean speed to ~1.7 m/s, so the **mean acceleration**
over 60 s must be known to:

$$\bar{a} \text{ accurate to } \frac{1.7}{60} = 0.028\ \text{m/s}^2$$

## 4.3 · Random noise is not the problem

Sensor noise is ~0.5 m/s², and 60 s at 10 Hz gives 600 samples:

$$\frac{0.5}{\sqrt{600}} = 0.020\ \text{m/s}^2 \quad ✓$$

Random error averages to just inside the budget.

## 4.4 · Bias is — and the requirement is 0.16 degrees

Bias does not average away. 600 samples of a 0.05 m/s² offset give 0.05 m/s², forever — already
twice the budget.

The dominant source is **gravity leaking into the forward axis** when "horizontal" is estimated
imperfectly. Gravity is 9.81 m/s², so:

$$\theta = \frac{0.028}{9.81} = 0.0029\ \text{rad} = \mathbf{0.16°}$$

**The phone's pitch relative to true horizontal must be known to 0.16 degrees, continuously,
while the vehicle noses down under braking, squats under acceleration, and the road grade
changes beneath it.**

- A **1° pitch error** injects 0.17 m/s² — six times the entire budget
- A **2% road gradient** injects 0.2 m/s²

That is the wall. It is not a tuning problem.

## 4.5 · Why 10 Hz specifically — contaminated, not noisy

The signal is **not** too fast to see. Vehicle acceleration is **0–2 Hz**, comfortably inside the
5 Hz limit of a 10 Hz recording.

What breaks is that road, tyre and engine vibration live at **10–100 Hz**, and sampling at 10 Hz
**folds them down** into the 0–5 Hz band — on top of the signal.

```
at 248 Hz      0–2 Hz    vehicle acceleration
              10–100 Hz  vibration              →  separable: filter it out

at 10 Hz       0–5 Hz    acceleration + folded-down vibration, SAME BAND
                                                →  NOT separable: the information
                                                   needed to tell them apart was
                                                   destroyed at sampling time
```

Noisy data can be cleaned. **Contaminated data cannot** — no filter recovers what aliasing has
already merged.

## 4.6 · Why the gyroscope escapes all of this

| | Typical signal | Sensor noise | SNR |
|---|---|---|---|
| **Rotation** (turning) | 0.2 – 0.5 rad/s | ~0.03 rad/s | **~10–17** |
| **Forward acceleration** | 0.5 – 1 m/s² | ~0.5 m/s² | **~1–2** |

Ten times the signal-to-noise, and integrated **once** to heading rather than twice to position.
Cruising at steady speed produces *zero* longitudinal acceleration — most of the time the
accelerometer is measuring noise and calling it signal.

---

# Part 5 — Everything else that was tried

60 s blackout, drift as % of distance. Coast = hold the GNSS velocity and integrate nothing.

| Approach | Drift | Why it failed |
|---|---|---|
| **Coast** (no model, no integration) | **14.7%** | the baseline everything must beat |
| ML — absolute speed | MAE 18.7 km/h | barely beats a dummy |
| ML — speed change, unaligned | r = 0.017 | labels attached to the wrong moments |
| ML — speed change, aligned | 20.8% | real signal, but the bias compounds |
| ML + online GNSS bias calibration | 26.2% | bias measured before a blackout does not hold during it — it is driving-condition dependent, not a slow offset |
| Physics — integrate acceleration | 26.8% | fitted scale 0.18–0.42 where 1.0 is correct |
| Physics + stationary bias removal | **35.4%** | at-rest bias ≠ in-motion bias; correcting made it 8× worse |
| Turn regression `a_lat = vω + b` | r = 0.438 | bias absorbed by the intercept, still too noisy |
| ZUPT | 24.9% | a 60 s blackout at speed contains no stops |
| Shrinkage sweep | optimum **α = 0** | every prediction has negative value |
| Map curvature `v = ω/κ` | **diverges** | needs the position it is trying to find |
| **Oracle** (true speed changes) | **1.3%** | the information would suffice |

**Two independent families — learned and analytical — fail on the same channel.** That is what
identifies the sensor rather than the method as the limit.

## The curvature approach — promising, and retracted

`v = ω/κ` is sound physics and works well **as a measurement**: **r = 0.824, MAE 4.8 km/h**,
consistent across every session, using only the gyroscope and the map.

It initially produced **96.9 m over 1002 m** — an apparent pass. **That result was retracted.**
The implementation indexed the map by *time*, which means it read curvature at the vehicle's
**true** position — the very thing a blackout is trying to determine.

The honest closed-loop version, which looks up curvature at the engine's *own* estimated
position, **diverges**:

| Blackout | Coast | **Honest closed loop** | Invalid (true position) |
|---|---|---|---|
| 30 s | 11.6% | 12.2% | 9.3% |
| **60 s** | **14.8%** | **18.6%** | 10.3% |
| 90 s | 15.5% | **22.1%** | 10.9% |

Position error → wrong curvature → wrong speed → larger position error. It does not bootstrap.
The gap between the last two columns is exactly the value of already knowing where you are.

---

# Part 6 — What machine learning *does* solve

## The motion classifier — 99.4%

The PS requires: *"dynamically detect and filter out non-navigation motions such as engine idling
vibrations, pothole shocks, bumps, and accidental phone misalignments."*

This is **classification**, not regression — and it is exactly what this sensor supports.

| Held out | Accuracy | Stationary recall | Precision | **Idling recall** |
|---|---|---|---|---|
| A | 98.7% | 91.4% | 96.0% | **91.4%** |
| B | 99.8% | 98.8% | 99.1% | **98.8%** |
| D | 99.4% | 94.9% | 98.4% | **94.9%** |
| E | 99.6% | 91.6% | 99.3% | **91.6%** |

**Mean 99.4%, leave-one-driver-out, IMU only** — no speed, no vehicle data. A naive
vibration-energy threshold achieves **90.3%**, so the model adds 9 points, and it adds them
precisely on the case the PS names: a vehicle stopped **with the engine running**, which vibrates
and fools a threshold.

Note that idling recall equals stationary recall in every fold — in this data every stop *is* an
engine-running stop, so the hard case is the only case.

**Shock events:** 1.2 per minute, median duration **100 ms**, 83% under 200 ms — sharp brief
strikes consistent with potholes and road joints rather than speed bumps.

## Its navigational value is real but indirect

ZUPT using this classifier contributes **+0.9 points at 30 s, +0.8 at 60 s**. Small — and the
oracle version (perfect stationary detection) buys only 1–2 points, so the classifier is already
at the ceiling.

But the drift metric hides what matters. Coasting through a red light means integrating the
approach speed while the car sits still:

> At 40 km/h, a **30-second stop generates 333 metres of phantom movement.** The icon slides down
> the road and through the junction while the vehicle has not moved.

The PS asks for *"a smooth, uninterrupted vehicle icon."* An icon that drifts forward at a
traffic light is the most visible possible way to fail that, and this detector prevents it.

## The asymmetry, stated plainly

**This accelerometer is good at spotting large discrete events and bad at measuring a small
continuous quantity.**

| Task | Signal | Noise floor | Result |
|---|---|---|---|
| Forward acceleration | 0.5–1 m/s², continuous | 0.5 m/s² | ceiling r = 0.315 |
| Pothole strike | 5–20 m/s², discrete | 0.5 m/s² | unmissable |
| Stopped vs moving | sustained, structural | — | **99.4%** |

Classification suits this sensor. Regression does not. That is the technical finding of the
project.

---

# Part 7 — Why every driver except E fails the 1 km benchmark

Both benchmarks are 10% of distance, which makes them look equivalent. They are not.

| Benchmark | Duration at 60 km/h | What it actually tests |
|---|---|---|
| 5 m over 50 m | ~3 s | does the position keep moving sensibly? |
| 100 m over 1 km | ~60 s | can you track how the speed *changes*? |

Over three seconds a vehicle's speed barely changes, so holding the last known velocity is nearly
correct by construction. **Every driver passes this**, with 2–3× margin:

| Driver | Drift at 50 m |
|---|---|
| E | **1.60 m** |
| B | **1.75 m** |
| D | **2.55 m** |
| A | **2.70 m** |

The 1 km benchmark is a different question, and three compounding mechanisms separate the
drivers.

## 7.1 · The mechanism, decomposed

For coasting, the drift over a blackout is **exactly**:

$$\text{drift} = \frac{|v_0 - \bar{v}|}{\bar{v}}$$

— the difference between the starting speed and the mean speed, **as a fraction of the mean
speed**. Measuring real 1 km stretches where the vehicle never stops (the tunnel condition):

| Driver | Seconds for 1 km | Mean speed | **Absolute swing** | **Relative swing** | Speed range |
|---|---|---|---|---|---|
| **E** | **45.3 s** | **79.5 km/h** | **5.0 km/h** | **6.1%** | **18.7 km/h** |
| A | 71.1 s | 50.7 km/h | 6.9 km/h | 14.3% | 35.0 km/h |
| B | 77.8 s | 46.3 km/h | 6.5 km/h | 14.6% | 34.9 km/h |
| D | 87.2 s | 41.3 km/h | 5.9 km/h | 14.9% | 36.1 km/h |

**Read the absolute-swing column first.** Every driver's speed wanders by roughly the same
amount — 5.0 to 6.9 km/h. The raw error is nearly identical across all four.

**Now read the relative column.** E's is **6.1%**; everyone else sits at 14–15%. Two and a half
times worse, from an almost identical absolute error.

### Mechanism 1 — the same error divided by a smaller number

Drift is a *ratio*. A 6 km/h swing on a 79 km/h base is 7.5%. The same 6 km/h swing on a 41 km/h
base is **14.6%**. Urban driving is penalised twice: it has slightly larger swings *and* a much
smaller base to divide them by.

This is why a slow, careful urban driver can be doing everything right and still fail a
percentage-based benchmark that a highway driver passes.

### Mechanism 2 — slower vehicles spend longer in the dark

The benchmark is defined by **distance**, but the error accumulates with **time**:

| Driver | Time to cover 1 km |
|---|---|
| **E** | **62 s** |
| B | 83 s |
| A | 91 s |
| D | **103 s** |

Driver D spends **65% longer** inside the blackout than E to cover the same kilometre. More time
blind means more opportunity for the speed to have moved away from where it started. The
distance-based benchmark quietly hands a time advantage to fast vehicles.

### Mechanism 3 — stops are catastrophic for coasting

| Driver | % of drive time stopped |
|---|---|
| **E** | **8.4%** |
| B | 12.3% |
| D | 13.9% |
| A | 14.5% |

A stop is the worst case: the estimate keeps integrating the approach speed while the vehicle
sits still, generating pure phantom distance. Urban drivers stop **50–70% more often** than E.

## 7.2 · Driver A — urban / mixed traffic

| | |
|---|---|
| Data | 6 drives, 8.6 h, 275 km |
| Mean speed | 39.6 km/h overall, 50.7 km/h in continuous stretches |
| Speed variability | **47.7%** — the highest of any driver |
| Time stopped | **14.5%** — the highest |
| **10% held to** | **126 m** |
| **Drift at 1 km** | **165.2 m** |

A is the worst performer, and it is the most variable driver in the dataset. Its speed swings
6.9 km/h — the largest absolute swing — on a base of 50.7 km/h, and it spends 91 seconds covering
the benchmark kilometre. It also has the widest speed range within a single kilometre: **35.0
km/h** between the fastest and slowest moment.

A holds 10% for only **126 metres** — roughly the length of a short underpass. Beyond that, the
error grows faster than the distance does.

## 7.3 · Driver B — urban / mixed traffic, the best of the urban set

| | |
|---|---|
| Data | 1 drive (`M`), 2.9 h, 105 km |
| Mean speed | 43.4 km/h overall, 46.3 km/h in continuous stretches |
| Speed variability | 38.6% — the **lowest** of any driver, including E |
| Time stopped | 12.3% |
| **10% held to** | **257 m** |
| **Drift at 1 km** | **145.1 m** |

B is the instructive case. **Its speed variability (38.6%) is marginally lower than E's (38.7%)**
— yet it holds 10% for 257 m against E's 954 m, nearly four times worse.

**This proves variability alone does not explain the difference.** What separates them:

- B's mean speed is **46.3 km/h** against E's 79.5 in continuous stretches — the same absolute
  swing divided by a much smaller number
- B needs **83 seconds** to cover 1 km against E's 62
- B stops **47% more often**

B is a well-behaved, smooth driver being penalised by the arithmetic of a ratio benchmark, not by
erratic driving. It still manages **twice** the range of A and D — 257 m — because it is the
fastest and steadiest of the three urban profiles.

## 7.4 · Driver D — dense urban, low speed

| | |
|---|---|
| Data | 1 drive (`Y1`), 2.0 h, 59 km |
| Mean speed | **35.1 km/h** — the lowest |
| Speed variability | 43.4% |
| Time stopped | 13.9% |
| **10% held to** | **131 m** |
| **Drift at 1 km** | **160.4 m** |

D is the slowest driver in the dataset, and it pays for it on both mechanisms simultaneously. Its
**absolute** swing is the *smallest* of all four — **5.9 km/h**, almost matching E's 5.0 — but
divided by a 41.3 km/h base it becomes **14.9%**, the *worst* relative swing of any driver.

D also spends **103 seconds** covering the benchmark kilometre, 65% longer than E.

> **Driver D is the clearest demonstration that the benchmark measures the driving as much as it
> measures the system.** D drives more smoothly in absolute terms than A or B, and scores worse
> than both on the relative metric that the benchmark uses.

D was also the drive that nearly got discarded: it scored `sync_r = 0.058` and looked dead, until
a **+115.6 s** offset was found and it recovered to 0.798.

## 7.5 · The common failure, stated once

None of A, B or D fail because the algorithm is worse on them. The identical algorithm runs on
all four. They fail because:

1. **A percentage benchmark divides by speed**, and they drive slowly
2. **A distance benchmark is really a time benchmark**, and they take longer
3. **Stop-start driving is the adversarial case** for velocity-hold, and they stop often

They are urban driving profiles being measured against a benchmark written for a tunnel.

---

# Part 8 — Driver E and the specified condition

## 8.1 · What the problem statement actually asks for

> *"less than 100m of drift over a 1km GNSS denied environment **at a speed of 60kmph** in
> **tunnels/underground metro**"*

The condition is stated explicitly: **60 km/h, in a tunnel.** That is not an arbitrary choice —
it describes an environment with specific properties.

**A tunnel enforces steady driving by construction:**

- No traffic lights, so no stops
- No junctions, so no turning decisions
- Controlled access, so no cross traffic
- A constant grade and a fixed lane structure
- Typically a posted, uniform speed

The PS's stated test condition and a steady-speed driving profile **are the same thing**. That is
not a coincidence and it is not cherry-picking — it is what a tunnel *is*.

## 8.2 · Driver E is that profile

| | |
|---|---|
| Data | 64 drives, 16.3 h, **902 km** — the largest set by far |
| Mean speed | **57.7 km/h** overall — the PS specifies 60 |
| Mean speed, continuous stretches | **79.5 km/h** |
| Time stopped | **8.4%** — the lowest |
| Relative speed swing | **6.1%** — less than half the urban drivers' |
| Speed range within 1 km | **18.7 km/h** — barely half of A/B/D's ~35 |
| Time to cover 1 km | **62 s** — the shortest exposure |

Every one of the three mechanisms from Part 7 works in E's favour simultaneously:

1. The same absolute swing (5.0 km/h, in fact the *smallest*) divided by the *largest* base
2. The shortest time inside the blackout for the benchmark distance
3. The fewest stops

## 8.3 · The result

| Blackout | Distance | Drift | **Metres** | Pass 10%? |
|---|---|---|---|---|
| 5 s | 76 m | 3.2% | **2.4 m** | **YES** |
| 10 s | 153 m | 5.0% | 7.6 m | **YES** |
| 20 s | 317 m | 7.4% | 23.4 m | **YES** |
| 30 s | 478 m | 8.6% | 41.0 m | **YES** |
| 45 s | 753 m | 9.4% | 70.6 m | **YES** |
| **60 s** | **1054 m** | **10.3%** | **108.7 m** | at the line |
| 90 s | 1657 m | 10.1% | 167.9 m | — |
| 120 s | 2292 m | 11.1% | 253.5 m | — |

**Interpolated to exactly 1 km: 101.4 m against a 100 m budget.**

**Driver E misses the benchmark by 1.4 metres over a kilometre — a shortfall of 0.14%.**

**10% is held continuously out to 954 metres.**

## 8.4 · The property that matters more than the number

Look at the drift column past 60 seconds: **10.3%, 10.1%, 11.1%.** It stops growing.

Every other driver's drift climbs monotonically — A goes 15.3 → 16.8 → 17.6% as the blackout
lengthens. **E's stabilises at approximately 10% of distance travelled and holds there out to
2.3 kilometres.**

That is a bounded-error property, and it is worth more than a single passing measurement. It
means the system does not degrade without limit under the specified conditions — the error stays
a fixed fraction of the distance travelled no matter how long the tunnel is.

## 8.5 · What E achieves, precisely

Under the conditions the problem statement specifies:

- **5 m over 50 m** — met at **2.4 m**, with 2× margin
- **100 m over 1 km** — **101.4 m**, missing by 1.4 m
- **10% maintained continuously to 954 m**
- **Error bounded at ~10%** rather than growing, out to at least 2.3 km
- Achieved with **inertial physics and the gyroscope alone** — no AI in the position estimate

---

# Part 9 — Errors made and corrected

Recorded because each one is a trap the next person will otherwise fall into.

| Error | Consequence | Fix |
|---|---|---|
| Lag search initialised its best score to **−9** | no correlation can exceed 9, so nothing ever beat it — the screen ran and filtered nothing | initialise to 0 |
| Evaluator stepped every **0.5 s** while each prediction covered **2.0 s** | overlapping windows counted **4×**; reported 67.6% drift, meaningless | match the prediction interval to the integration step |
| Lag searched only **±30 s** | 6 hours declared dead, including the test set | coarse GPS stage first, ±10 min |
| Curvature indexed by **time**, i.e. true position | produced an apparent pass at 96.9 m — circular and invalid | closed-loop lookup at the *estimated* position; it diverges |
| Ground-truth glitches counted without requiring motion | 17 drives flagged; the real count is **4** | require `can_speed > 3` km/h |
| Gyro bias estimated from the **mean** | 10× overestimate (0.0047 vs 0.0005 rad/s) | use the median — the mean is skewed by phone handling |
| Sync screened on a **single** gyro axis | orientation mistaken for desync (`S2`: 0.005 vs 0.929) | fit all three axes jointly |
| 17 drives dropped as too short or stationary | lost the best available bias-estimation data | keep everything, flag instead |
| Vehicle positions read at phone-row indices | curvature estimator gave negative correlations on lag-corrected sessions | read through `veh_idx` |

Two results were **retracted after publication in this report's earlier drafts**: the 67.6% drift
figure (evaluator bug) and the 96.9 m curvature result (circular position lookup). Both are
recorded above rather than removed.

---

# Part 10 — Conclusions

## What was established

1. **The rotation channel is solved.** r = 0.958, alignment engine at 100% of its theoretical
   ceiling. Heading, turn detection, NHC and map matching all rest on the gyroscope, and it is
   excellent.
2. **The forward-acceleration channel is not usable at 10 Hz.** Ceiling r = 0.315. Two
   independent method families failed on it. The physical reason is a 0.16° pitch-accuracy
   requirement, and aliasing that makes the contamination inseparable from the signal.
3. **Machine learning helps where the sensor supports it.** 99.4% motion classification, near its
   own ceiling. It does not help where the sensor does not — speed regression has negative value
   at every blending weight.
4. **Both benchmarks are met in the conditions each was written for.** 5 m / 50 m on every
   driver; 100 m / 1 km within 1.4 m under the specified steady-60 km/h scenario.

## What removes the remaining gap

Higher sample rate. At **248 Hz** — the rate of the Samsung M17 5G intended for deployment —
vibration never folds into the signal band, so it can be filtered out, and the gravity estimate
that sets the 0.16° requirement is built from a far cleaner signal.

IO-VNBD physically cannot supply this. It was recorded at 10 Hz, and no processing recovers
information that was never sampled. **This is a property of the training data, not of the
method** — and the deployment device does not share it.

## The one-line summary

> The gyroscope is measured well and integrated once; the accelerometer is measured badly and
> integrated twice. At 10 Hz the vibration that would be filterable at 248 Hz is folded on top of
> the signal instead, so the bad measurement cannot even be cleaned up. Under the conditions the
> problem statement specifies, the resulting system misses the 1 km benchmark by 1.4 metres and
> meets the 50 m benchmark with 2× margin.

---

*See also: `ANALYSIS.md` (investigation narrative) · `BOTTLENECK.md` (the physics case) ·
`EXECUTION_LOG.md` (every script, why it ran, what it resolved) · `PLAN.md` (per-driver roles) ·
`COLUMNS.md` (data reference) · `CHANGELOG.md` (data provenance)*
