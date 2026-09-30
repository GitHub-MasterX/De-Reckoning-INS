# Why the 1 km benchmark cannot be met from IO-VNBD

**Claim:** the *100 m over 1 km* benchmark is not reachable from this dataset, and the limit is
a property of the **data**, not of the method. The *5 m over 50 m* benchmark is met.

Everything below is measured, and every figure traces to a script in `analysis/`.

---

## The two benchmarks are not equally hard

The problem statement gives both as 10% of distance travelled, which makes them look
equivalent. They are not — drift grows with blackout duration, so they test different things.

| Benchmark | Duration at 60 km/h | What it tests |
|---|---|---|
| 5 m over 50 m | ~3 s | does the position keep moving sensibly? |
| 100 m over 1 km | ~60 s | can you track how the speed *changes*? |

Over three seconds a vehicle's speed barely changes, so holding the last known velocity is
nearly correct by construction. Over sixty seconds it slows for bends, accelerates, meets
traffic — and closing that gap needs a measurement the phone cannot make.

**Result:** *5 m over 50 m* is met at **2.6 m over 57 m**, using pure physics and no AI.
*100 m over 1 km* comes out at **~148 m**, against a 100 m budget.

---

## The information is present — the measurement is not

Feeding the evaluator the **true** speed changes gives **1.3% drift**. So the benchmark is
comfortably achievable *if* speed change can be measured. The evaluator is sound and the target
is not unreasonable.

The obstacle is measuring it.

### What the phone measures well, and what it does not

Both channels were rotated into the vehicle frame by an alignment engine operating within
**3–5% of the theoretical optimum** (the best any rotation could achieve):

| Quantity | Achieved | Ceiling | Efficiency |
|---|---|---|---|
| **Rotation** (yaw rate) | **0.958** | 0.958 | 100% |
| Lateral acceleration | 0.381 | 0.400 | 95% |
| **Forward acceleration** | **0.269** | **0.315** | 97% |

The estimator is essentially perfect. **The ceiling is the problem.** The gyroscope tracks the
vehicle's rotation almost exactly; the accelerometer explains about **10% of the variance** in
its forward acceleration — and on one drive, 0.05.

Speed change comes from forward acceleration. That is the channel that fails.

---

## Why it fails — three numbers

### 1. The accuracy required

100 m over 1 km at 60 km/h means knowing the mean speed to ~1.7 m/s, so the **mean
acceleration** over 60 s must be known to:

$$\bar{a} \text{ to } \frac{1.7}{60} = 0.028\ \text{m/s}^2$$

### 2. Random noise is not the problem

Sensor noise is ~0.5 m/s², and 60 s gives 600 samples:

$$\frac{0.5}{\sqrt{600}} = 0.020\ \text{m/s}^2 \quad ✓$$

Random error averages to just inside the budget. It is not what stops us.

### 3. Bias is — and the requirement is 0.16°

Bias does not average away. The dominant source is **gravity leaking into the forward axis**
when "horizontal" is estimated imperfectly. Gravity is 9.81 m/s², so the budget corresponds to:

$$\theta = \frac{0.028}{9.81} = 0.0029\ \text{rad} = \mathbf{0.16°}$$

**The phone's pitch relative to true horizontal must be known to 0.16 degrees, continuously,
while the vehicle noses down under braking, squats under acceleration, and the road grade
changes beneath it.** A 1° error injects 0.17 m/s² — six times the entire budget. A 2% gradient
injects 0.2 m/s².

That is the wall, and it is not a tuning problem.

---

## Why **10 Hz** specifically

The signal is not too fast to see. Vehicle acceleration is **0–2 Hz**, comfortably inside the
5 Hz limit of a 10 Hz recording.

What breaks is that road, tyre and engine vibration live at **10–100 Hz**, and sampling at
10 Hz **folds them down** into the 0–5 Hz band — on top of the signal.

```
at 248 Hz     0–2 Hz   vehicle acceleration
             10–100 Hz vibration                 separable: filter it out

at 10 Hz      0–5 Hz   acceleration + folded-down vibration, same band
                                                 NOT separable: the information
                                                 needed to tell them apart was
                                                 destroyed at sampling time
```

This is the difference between **noisy** and **contaminated**. Noisy data can be cleaned.
Contaminated data cannot — no filter recovers what aliasing has already merged.

It also explains why the gyroscope escapes: rotation is measured directly with roughly ten
times the signal-to-noise, and integrated once rather than twice.

---

## Every approach tried, and its result

60 s blackout, drift as % of distance. Coast = hold the GNSS velocity and integrate nothing.

| Approach | Drift | |
|---|---|---|
| **Coast** (no model, no integration) | **14.7%** | the baseline everything must beat |
| ML — absolute speed | MAE 18.7 km/h | unusable; dummy is 26.5 |
| ML — speed change, unaligned | r = 0.017 | nothing learned |
| ML — speed change, aligned | 20.8% | worse than coast |
| ML + online GNSS bias calibration | 26.2% | bias is not stationary; correction stale |
| Physics — integrate acceleration | 26.8% | fitted scale 0.18–0.42, should be 1.0 |
| Physics + stationary bias removal | 35.4% | at-rest bias ≠ in-motion bias |
| Turn regression `a_lat = vω + b` | r = 0.438 | bias absorbed by intercept; still too noisy |
| ZUPT | 24.9% | no stops inside a 60 s blackout at speed |
| Shrinkage sweep `v₀ + α·Σpred` | optimum **α = 0** | best use of every prediction is to ignore it |
| Map curvature `v = ω/κ` | **diverges** | needs the position it is trying to find |
| **Oracle** (true speed changes) | **1.3%** | the information would suffice |

Two independent families — learned and analytical — fail on the same channel. That is what
identifies the sensor rather than the method as the limit.

### On the curvature approach

`v = ω/κ` is sound physics and works well **as a measurement**: r = 0.824, MAE 4.8 km/h,
consistent across every session. It uses only the gyroscope and the map.

It cannot be used during a blackout, because reading curvature from the map requires knowing
where you are — which is the unknown. Closed-loop evaluation confirms it **diverges** (18.6% at
60 s, worse than coast).

The remaining honest form is *sequence matching* — aligning the observed yaw-rate pattern
against the map's profile of bends to recover distance travelled without a position fix. Not
attempted; not promised.

---

## What removes the bottleneck

Higher sample rate. At 248 Hz — the rate of the Samsung M17 5G intended for deployment —
vibration never folds into the signal band, so it can be filtered out, and the gravity estimate
that sets the 0.16° requirement is built from a far cleaner signal.

IO-VNBD physically cannot supply this: it was recorded at 10 Hz, and no processing recovers
information that was never sampled.

**Consequence:** models trained on IO-VNBD are limited to what its 10 Hz recording preserved.
Deployment on a 248 Hz device is not limited by the same wall — but demonstrating that requires
data recorded at that rate.

---

## Summary

| | |
|---|---|
| **5 m over 50 m** | **met** — 2.6 m over 57 m |
| **100 m over 1 km** | not met — ~148 m; requires 0.16° pitch knowledge, unattainable at 10 Hz |
| Rotation channel | **excellent** — r = 0.958, heading and turn detection are solved |
| Forward acceleration channel | ceiling r = 0.315 — the binding constraint |
| Path forward | 248 Hz recording, where the vibration and signal bands stay separate |
