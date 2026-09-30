# System Architecture

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

## Inputs

- Accelerometer + gyroscope, phone MEMS IMU — 10 Hz (benchmark dataset) or 248 Hz (native, own recordings)
- GNSS fix, when available, roughly 1 Hz
- Offline OSM road graph, pre-built as a binary adjacency structure with R-tree spatial indexing

## GNSS available

The raw fix is shown directly as the position. In the background, each phone's own gyroscope axis alignment,
scale, and bias are fit by least-squares against this GNSS history continuously, so the correction is ready the
moment a blackout begins. This mattered directly: one test phone's gyroscope was found to report only ≈54% of
every real turn before this correction.

## GNSS lost — the four-layer dead-reckoning pipeline

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

## Output

A single (latitude, longitude, heading) estimate per tick, rendered on the Android app's map as a moving cursor,
with a live GNSS OK/LOST indicator and a re-centre control, in both live-sensor mode and offline-replay mode.

## Why this split, mechanically

The four layers correspond to the four distinct failure modes a GNSS blackout produces, and nothing more:

| Layer | Failure it corrects |
|---|---|
| 1 — Motion Classifier | Drift accumulating while the vehicle is not actually moving |
| 2 — Learned Speed Model | Distance travelled being wrong, because held speed does not track real speed changes |
| 3 — Particle Filter | Heading drift, and "which road" ambiguity that raw dead reckoning cannot resolve |
| 4 — Reporting Layer | The filter's own internal uncertainty being displayed as visible teleporting/jumping |

Each layer was added only after measuring that the layers before it, alone, left that specific failure mode
unaddressed — not as a design assumption. The measurements behind that sequencing are in `CHALLENGES.md`.
