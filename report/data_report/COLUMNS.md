# The 43 columns, and how they relate

Verified uniform across all 72 files — **one column layout, no exceptions.**

Format is `.parquet`, not CSV: it loads roughly 10× faster and preserves dtypes, which
matters at a million rows.

```python
import pandas as pd
d = pd.read_parquet("data/clean/S1.parquet")
```

---

## The one relationship that is the whole project

```
ax ay az gx gy gz        ──model──▶     speed_best
(what the phone feels)                (how fast the car is going)
```

Every other column exists to support, label, or check that single line.

---

## Group 1 — Phone sensors: the model's input

These are the **only** columns allowed at runtime. The problem statement forbids connecting
to the vehicle's computer, so everything in Group 2 exists solely to train and grade.

| Column | Unit | What it is |
|---|---|---|
| `ax` `ay` `az` | m/s² | Accelerometer. **Includes gravity** — at rest the three combine to ~9.81 |
| `gx` `gy` `gz` | rad/s | Gyroscope: how fast the phone is rotating |
| `gx_c` `gy_c` `gz_c` | rad/s | Same, with each session's resting offset subtracted |
| `mx` `my` `mz` | µT | Magnetometer. Points at magnetic north — badly distorted inside a steel car |

**Relationship inside the group:** `gx_c = gx − bias`, where bias is the gyro's reading while
the car was provably stopped. Use `gx_c` unless you are specifically studying bias.

---

## Group 2 — Vehicle sensors: the answers

### The label you predict

| Column | Unit | What it is |
|---|---|---|
| `speed_best` | km/h | **Train against this.** The true speed |
| `speed_src` | text | Which source it came from: `gps` / `can` / `gps_only` |
| `speed_kmh` | km/h | GPS speed, raw — freezes when the receiver loses lock |
| `can_speed` | km/h | Wheel-derived speed, raw — immune to GNSS |

Two independent measurements of one quantity, agreeing at r = 0.9993. `speed_best` normally
takes GPS and switches to CAN wherever GPS froze; `speed_src` records which happened at each
sample.

```
speed_kmh (GPS) ──┐
                  ├──▶ speed_best  ──▶ speed_src records the choice
can_speed (CAN) ──┘
```

### Where `can_speed` itself comes from

| Column | Unit | |
|---|---|---|
| `ws_fl` `ws_fr` `ws_rl` `ws_rr` | rad/s | The four wheels' rotation rates |

Wheel rate × tyre radius = road speed. These are the *upstream source* of `can_speed`.

> They are also exactly why the problem statement bans OBD-II — this is the feed you are
> forbidden to use, and the one you must replace.

### The reference signals that grade your intermediate steps

| Column | Unit | Phone equivalent |
|---|---|---|
| `yaw_rate` | rad/s | true turn rate ↔ `gx gy gz` |
| `lon_acc` | m/s² | true forward acceleration ↔ `ax ay az` |
| `lat_acc` | m/s² | true sideways acceleration ↔ `ax ay az` |

**This is the most important relationship in the dataset.** The phone and the car measure
*the same physical motion* from different orientations:

```
[gx gy gz]  ×  (unknown phone→vehicle rotation)  =  [roll_rate, pitch_rate, yaw_rate]
```

Solve that rotation and you have the alignment engine. It is also what `sync_r` measures — if
the two agree once rotated, the files are time-aligned; if they do not, something is broken.

### Position and context

| Column | Unit | |
|---|---|---|
| `lat` `lon` | degrees | true position — what your trajectory is finally scored against |
| `heading` | degrees | true direction of travel, 0 = north |
| `steer_deg` | degrees | steering wheel angle |
| `engine_rpm` | rev/min | engine speed |
| `brake` | 0/1 | brake pedal |
| `gear` | 1–5 | constant in 48/72 drives — mostly unusable |

Relationships worth knowing:

- `lat/lon` differentiated over time gives speed and heading — which is how `speed_kmh` and
  `heading` are produced. All three come from the same receiver, so **when one fails, all
  three fail together.**
- `steer_deg` and `yaw_rate` are linked by speed: the same wheel angle produces far more yaw
  at 80 km/h than at 10 km/h.
- `brake = 1` should coincide with `lon_acc` going negative. A useful sanity check.
- `engine_rpm` ÷ gear ratio would give speed — but `gear` is dead in two thirds of drives, so
  that path is closed.

---

## Group 3 — Derived flags

| Column | Type | Derived from | Meaning |
|---|---|---|---|
| `stationary` | bool | `speed_best` | stopped for ≥ 2 s |
| `gnss_dropout` | bool | `lat`/`lon` + `can_speed` | GPS lost lock while moving |
| `stuck` | bool | the six IMU channels | sensor repeating a stale value |
| `session` | int | `t_raw_s` | recording-session id |

**The chain that matters:**

```
speed_best ──▶ stationary ──▶ gyro bias measured here ──▶ gx_c gy_c gz_c
```

A gyroscope's resting offset can only be measured while the car is provably stopped — so
`stationary` is what makes `gx_c` possible at all.

And the other one:

```
lat/lon frozen  +  car moving  ──▶ gnss_dropout ──▶ speed_src switches to "can"
```

---

## Group 4 — Time

| Column | Unit | |
|---|---|---|
| `t_s` | s | nominal, `row_index / 10` |
| `t_raw_s` | s | the phone's actual clock |
| `session` | int | increments at each break |

These agree on 65 of 72 drives. Where they disagree, **`t_raw_s` is right and `t_s` is a lie**
— the file contains multiple recordings stitched together. `session` marks the seams.

> **Rule: no training window may cross a session boundary.**

---

## Group 5 — Reference only, do not build on these

| Column | Why not |
|---|---|
| `phone_lat` `phone_lon` `phone_speed` `phone_gps_acc` | The phone's own GPS — updates roughly **every 9 seconds**. Useless as truth; kept only for comparison |
| `grav_x` `grav_y` `grav_z` | Android's *computed* gravity estimate, not a real sensor. A vendor black box that differs between phones — a model leaning on it will not transfer |

---

## The whole thing in one picture

```
      PHONE                                          VEHICLE
   ax ay az                                       lon_acc, lat_acc
   gx gy gz    ◀── same motion, rotated ──▶       yaw_rate
   mx my mz                                       heading

        │                                              │
        │ model                                        │ (labels + grading)
        ▼                                              ▼
    speed_best  ◀────────── trained against ──── speed_kmh / can_speed
        │                                              ▲
        │ integrate                                    │
        ▼                                        ws_fl/fr/rl/rr
    your trajectory  ◀──── scored against ────  lat / lon
```

---

## Full column list, in file order

| # | Column | Type | Group |
|---|---|---|---|
| 1 | `t_s` | float64 | time |
| 2–4 | `ax` `ay` `az` | float64 | phone — input |
| 5–7 | `gx` `gy` `gz` | float64 | phone — input |
| 8–10 | `mx` `my` `mz` | float64 | phone — input |
| 11 | `speed_kmh` | float64 | vehicle — label source |
| 12–13 | `lat` `lon` | float64 | vehicle — ground truth position |
| 14 | `can_speed` | float64 | vehicle — label source |
| 15 | `yaw_rate` | float64 | vehicle — reference |
| 16–17 | `lon_acc` `lat_acc` | float64 | vehicle — reference |
| 18 | `heading` | float64 | vehicle — ground truth |
| 19–22 | `ws_fl` `ws_fr` `ws_rl` `ws_rr` | float64 | vehicle — never an input |
| 23 | `steer_deg` | float64 | vehicle — context |
| 24 | `engine_rpm` | float64 | vehicle — context |
| 25 | `brake` | float64 | vehicle — context |
| 26 | `gear` | float64 | vehicle — mostly dead |
| 27–29 | `grav_x` `grav_y` `grav_z` | float64 | reference only |
| 30–33 | `phone_lat` `phone_lon` `phone_speed` `phone_gps_acc` | float64 | reference only |
| 34 | `t_raw_s` | float64 | time |
| 35 | `session` | int16 | derived |
| 36 | `speed_best` | float64 | **the label** |
| 37 | `speed_src` | str | derived |
| 38 | `gnss_dropout` | bool | derived |
| 39–41 | `gx_c` `gy_c` `gz_c` | float64 | phone — input, bias removed |
| 42 | `stationary` | bool | derived |
| 43 | `stuck` | bool | derived |

---

**See also:** `README.md` (what the data is) · `CHANGELOG.md` (how it got this way)
