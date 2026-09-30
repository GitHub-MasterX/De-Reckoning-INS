# The Tiruchirappalli rides — what our own data showed

*Local only: this file is git-ignored along with the rides it describes.*

Our own dataset, recorded to answer one question the IO-VNBD dataset could not: does the engine work on a modern
phone, on Indian roads, on the vehicle people actually ride?

---

## 1 · What was recorded

| | |
|---|---|
| Phone | Samsung Galaxy M17 5G (SM-M176B), Android 16, LSM6DSV IMU |
| Sampling | accelerometer and gyroscope at **248 Hz**, GNSS at 1 Hz, recorded continuously |
| Vehicle | two-wheeler, phone **hand-held or in a bag** — no mount |
| Where | Tiruchirappalli, the NH38 corridor and town streets |
| When | 17 September 2026, one trip |
| App | SIH Nav Live, our own build, logging every sensor event, every GNSS fix, and the engine's own output |

Three segments, 39 km in total:

| Segment | Route | Distance | Median speed |
|---|---|---|---|
| 1 · outbound | campus → Trichy town, NH38 | 18.9 km | 28 km/h |
| 2 · town | the ten-minute tuning ride | 2.6 km | 18 km/h |
| 3 · return | town → campus, same corridor | 18.3 km | 26 km/h |

The rides are stored in `round2/phone_data/` and are git-ignored, being location traces. They cannot be re-recorded.

## 2 · How it was evaluated

The same rule the IO-VNBD work uses: **a blackout starts every 250 m** once there are five minutes of history and the
vehicle is above 15 km/h, and **runs for 1 km**. Error is the **2D position error averaged along the whole blackout**,
as a percentage of the distance travelled, measured from 100 m in — never the error at the finish line.

That yields **111 blackouts** (54 outbound, 57 return; the town segment is too short for the rule).

**Nothing is scored by a model that saw it.** The learned speed model for the outbound ride is trained on the return
ride, and vice versa. The two rides are the same corridor in opposite directions, so this is a same-corridor test —
legitimate, and the deployment case for a commuter route, but not a claim about unseen roads.

## 3 · What the engine is

Four layers (full detail in `ENGINE_LAYERS.md`):

1. round 1's motion classifier — moving or stopped
2. the **learned speed** — predicts speed each second from the shaking, the Tamil Nadu map under the bike, and the
   speed at the last GNSS fix
3. round 2's road-constrained particle filter on the Tamil Nadu road network (350,308 km, built from the state's OSM)
4. round 3's reporting layer — mode hysteresis and a speed-limited cursor

## 4 · The result

**All 111 blackouts**, merged engine against round 2's held-speed engine:

| | under 10% | count | median |
|---|---|---|---|
| round 2 | 37% | 41 of 111 | 13.9% |
| **merged engine** | **41%** | **45 of 111** | **12.4%** |

**The merged engine is better on 85 of the 111 blackouts.**

By riding condition — the gain is entirely in slow, stop-start riding, which is where Indian traffic lives:

| Condition | n | round 2 under 10% | merged | median drift |
|---|---|---|---|---|
| **under 40 km/h** | 50 | 8 | **11** | **27.5% → 14.7%** |
| 40–50 | 6 | 1 | **4** | 14.0% → **8.0%** |
| 50–70 | 49 | 28 | 28 | 9.3% → 11.4% |
| 70+ | 6 | 4 | 4 | 7.1% → 8.2% |

**Is the error controlled even when it exceeds 10%?** On the return ride's 57 blackouts:

| | n | stayed on the driven road | worst sideways |
|---|---|---|---|
| under 10% | 27 | — | — |
| 10–20% | 12 | **92%** | 10 m |
| 20–40% | 8 | 50% | 30 m |
| over 40% | 10 | 10% | 352 m |

So **39 of 57 (68%) end with the cursor on the correct road**, whether or not they meet the benchmark. The remaining
sixth lose the road entirely.

### The eight-kilometre run

Eight consecutive, non-overlapping blackouts from the outbound ride, each reconstructed independently, scored by a
model trained on the return ride:

| Leg | Speed at the fix | Rode at | round 2 | **merged** |
|---|---|---|---|---|
| 1 | 68 km/h | 67 | 6.3% | **3.7%** |
| 2 | 72 | 62 | 5.3% | **2.2%** |
| 3 | 59 | 61 | 4.7% | **4.6%** |
| 4 | 69 | 57 | 6.0% | **4.9%** |
| 5 | 22 | 40 | 17.7% | **7.3%** |
| 6 | 27 | 31 | 28.0% | 13.8% |
| 7 | 42 | 23 | 7.4% | 7.5% |
| 8 | 21 | 23 | 18.5% | **7.9%** |

**8.0 km continuous, mean 6.5%, median 6.1%, seven of eight inside the benchmark.**

Leg 5 and Leg 7 are the evidence that this is not luck with favourable starts: both begin with the speed nearly 20 km/h
wrong (one accelerating, one decelerating) and both land under 8%, because the model *sees* the change. Leg 6 is the
failure and is kept in: GPS died at 27 km/h and the bike then swung 21 → 44 → 21 → 36 km/h within two minutes, which
no predictor of typical behaviour can follow.

## 5 · What is different about India, measured

- **No speed limits in the map.** Of the 111 blackouts, **0%** start on a road carrying a `maxspeed` tag. The gating
  rule developed on England ("hold the last speed on roads tagged 80 km/h or more") is inert here; gating on the
  **last known speed** works instead and is what the engine uses.
- **Almost nothing to anchor on.** NH38 offers **0.9 turns per km** against 3.5 in town. Road bends cannot substitute:
  the median bend on the route has a **1,578 m radius**, so an along-track error of 138 m shifts the road's bearing by
  only 5° — the gyro's own error over a kilometre.
- **The map can cost more than it gives here.** On the same blackouts, dead reckoning without the map scored **8.7%**
  and the full map-matched engine **10.1%**. Sparse junctions plus parallel service roads is the map's worst case, in
  England and in India alike.
- **Speed breakers are visible at 248 Hz and invisible at 10 Hz.** Of the mapped bumps lying within 5 m of the ridden
  line, **4 of 5 were detected** in the raw stream, one peaking at 23 m/s² against a 4 m/s² background. Binning to
  10 Hz averages them away entirely. They are point landmarks a parallel road cannot imitate — the one map element that
  attacks the along-track error a bend cannot.
- **Self-mapping those bumps is unproven.** Jolts repeating between the two runs looked like 2.7 per km until a control
  (sliding one run's detections 100–300 m along the same road) showed most were coincidence. The genuine excess is
  about **0.7 per km**, and the strongest jolts do not repeat at all — with the phone in a hand, most of what the
  accelerometer sees is the rider.

## 6 · Limitations, stated plainly

1. **No stop detection in this path.** The classifier finds 5–25% of a two-wheeler's stops (it was trained on cars), so
   it was switched off rather than trusted. On a bike in Indian traffic that is a constant cost, paid by every variant.
2. **One corridor, one day, one vehicle.** 39 km total, and the two rides share a route.
3. **Hand-held phone.** The turn-based speed readings and the bump landmarks both need a stable sensor frame.
4. **Blackouts overlap.** Starting every 250 m and running 1 km, consecutive blackouts share 75% of their road — 111
   samples, far fewer independent measurements. The eight-leg run above is the non-overlapping subset.
5. **The learned speed is trained on 19 km.** Features from the full 248 Hz spectrum were tried and did *worse* than
   coarse ones (3.55 vs 2.77 m/s), because there is not enough data to fit them.

## 7 · What this dataset proved, and what it did not

**Proved.** The engine runs live on a modern phone at 248 Hz, on a two-wheeler, on Indian roads, with the Tamil Nadu
map, and its learned speed carries from one ride to another: slow riding improves from **27.5% to 14.7%** median error,
and eight consecutive kilometres average **6.5%**. The whole pipeline — classifier, learned speed, particle filter,
reporting — was exercised end to end on data none of it was designed against.

**Not proved.** Generalisation to roads and vehicles outside this corridor; that the map helps on Indian highways (it
did not here); that self-mapped landmarks are real; and that the benchmark is met across the board — 45 of 111
blackouts meet it, and the failures are concentrated where the vehicle changes speed sharply just as GNSS is lost.
