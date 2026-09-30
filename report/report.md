# Intelligent Dead Reckoning for GNSS-Denied Navigation

**Smart India Hackathon 2026 · Problem Statement 26168 (ISRO)**

The master overview of the final system. Detailed reports live alongside this one:

| Report | Covers |
|---|---|
| `ARCHITECTURE.md` | The four-layer system, what each layer does, and why the split is exactly this |
| `MECHANISM.md` | How the learned speed model actually works — the physics, the aliasing, the trees |
| `CHALLENGES.md` | Every real obstacle faced, including the ones tried and rejected |

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

## References

- Groves, P. D. (2013). *Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems.* Artech House.
- Newson, P., & Krumm, J. (2009). *Hidden Markov Map Matching Through Noise and Sparseness.* ACM SIGSPATIAL GIS.
- Skog, I., & Händel, P. (2010). *Zero-Velocity Detection — An Algorithm Evaluation.* IEEE Trans. Biomedical Engineering.
- Gustafsson, F., et al. (2002). *Particle Filters for Positioning, Navigation, and Tracking.* IEEE Trans. Signal Processing.
- IO-VNBD — Inertial/Odometry Vehicle Navigation Benchmark Dataset (England, multiple drivers, car, 10 Hz IMU).
- Team's own recordings — Tiruchirappalli, Tamil Nadu, two-wheeler, hand-held phone, 248 Hz IMU, 1 Hz GNSS.
- OpenStreetMap contributors — road network data for England and Tamil Nadu, via the Overpass API.
