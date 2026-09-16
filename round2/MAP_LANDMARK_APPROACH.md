# Map-landmark positioning — round 2 approach

Using road structure from OpenStreetMap and turns detected by the gyroscope to correct dead-reckoning
drift during a GNSS blackout.

**Status (2026-09-15): design, feasibility measurements, map scans and an audit. Nothing is built yet.**
Branch `round-2`. Round 1 is frozen at tag `round-1` and untouched (`README.md`).

**The audit in one paragraph.** The core idea holds: with perfect snaps and speed re-estimated at each
snap, all four drivers reach **3–4%** drift at 1 km. With phone-detected turns, real OSM junctions
competing, and a matcher that keeps one guess at a time, urban drivers land around **8–10%** and
driver E around **9–10%**. Several earlier claims were wrong or incomplete; each is marked
**Corrected** where it appears and listed in §18.

Numbers marked *ceiling* assume perfect corrections and are upper bounds, not results.

---

## 1 · Goal

Round 1 was cleared on the ~10% result. For round 2:

| Driver | Profile | Drift at 1 km now (coast) | Target |
|---|---|---|---|
| **E** | steady highway — the PS scenario | **10.2%** | clearly **below 10%** |
| B | urban / mixed traffic | 16.1% | **~10%** |
| A | urban / mixed traffic | 16.5% | **~10%** |
| D | dense urban, low speed | 19.6% | **~10%** |

*Baseline from `run_evaluation.py` (tag `round-1`), leave-one-driver-out.*

> **Corrected — what these numbers are (§15).** Medians of *distance* error, over at most 200 random
> blackouts per session, counting only blackouts without a stop. Counting every blackout instead, the
> 10 Hz replication gives E **6.5%**; E's individual sessions range from 3.0% to 26.1%. D's figure
> comes from a single session.

> **Update 2026-09-16 — by driving condition (step 1, `out/step1_run.txt`).** Coasting, distance error at 1 km on
> the test drivers D and E: slow (under 40 km/h) 25.6%, mixed (40–50) 18.3%, **50–70 km/h — the problem statement's
> condition — 14.5%**, fast (70+) 3.5%. Round 1's "E ≈ 10%" came mostly from fast motorway driving. The real
> round-2 target is the 50–70 km/h group, where 87% of 1 km blackouts contain a real turn.

---

## 2 · The idea

Start from the last GNSS position. During the blackout, the **gyroscope detects each bend or
turn** the vehicle makes. The **OSM map knows where the bends are** on the road. Matching the
detected turn to the mapped bend resets the accumulated position error — a "cushion" that stops
error growing without limit.

Why the gyroscope: it is the reliable channel (yaw r = **0.958** against the vehicle's own
sensor), while forward acceleration caps at r = 0.315. Turns are measured by the good sensor.

### Why this is not the retracted curvature method

| | Retracted curvature method | This method |
|---|---|---|
| Loop | every sample: look up curvature at the *estimated* position → speed → move → look up again | the gyro **detects** the turn on its own; only then is the map searched near the estimate |
| Failure | position error → wrong curvature → wrong speed → worse position; **diverged to 18.6%** | position error cannot corrupt detection — "I just turned 40° left" is true wherever the engine thinks it is |
| Result | closed loop, self-reinforcing | the loop is broken; the search window tolerates the error |

> **Caveat (audit).** True for *detection*. *Association* can still chain errors: a wrong snap moves the
> next search window, which makes the next wrong snap likelier. Keeping several hypotheses (§7) is the guard.

### What it corrects

Road snapping normally only fixes **sideways** error. The 1 km benchmark measures **along-road**
error (how far along the road you are). Bends are distinctive points *along* the road, so
matching one fixes exactly the error the benchmark scores. Error becomes a sawtooth that resets
at every landmark; what counts at 1 km is only the distance travelled since the last snap.

> **Corrected.** A snap resets the *position* error, not the *speed* error that caused it. With perfect
> snaps, keeping the old speed gives 3.3–6.4%; re-estimating speed gives 3.0–4.0% (§14). The sawtooth
> only resets fully when speed is re-estimated too.

### Speed re-estimation — required (was: "extension")

After snapping at **two** landmarks, the map distance between them divided by the time taken
gives an **average speed with no accelerometer involved**. This corrects the cause of drift (a
wrong speed), not just the position, so error stays small between landmarks too.

> **Corrected.** One landmark is enough: the last GNSS fix is the first anchor, so average speed since
> the blackout began is available after the first snap (2.7–4.2% with perfect snaps, §14). But a wrong
> snap corrupts it — for D, 6.0% re-estimated against 4.4% with the old speed — so it must run inside
> a filter that rejects snaps inconsistent with the speed so far.

---

## 3 · Feasibility measurements

### 3.1 · A detection bug, found and fixed

The first pass reported phone-detected bends were only **7–12% genuine**, and claimed driver E
could reach **3.0%**. Both were wrong. **Retracted.**

Cause: the phone's `rate_yaw` and the rate derived from the GPS course use **opposite sign
conventions**, so every real left turn was compared against a right turn and rejected. Window
boundaries between the two detections were also not synchronised.

| Correlation on moving samples (median) | Driver E | Urban (A/B/D) |
|---|---|---|
| phone yaw vs GPS course | **−0.380** | **−0.742** |
| phone yaw vs CAN yaw rate | 0.444 | 0.908 |
| GPS course vs CAN yaw rate | −0.715 | −0.795 |

Fix: align sign per session from the measured correlation; detect bends deterministically
(net heading change over a centred 15 s window, non-maximum suppression, apex = window centre)
on both streams with the same algorithm.

> **Note (audit).** The sign comes from the GPS course and the yaw axis from a fit against the CAN yaw rate
> (`analysis/align_frame.py`, an IO-VNBD export quirk). A real phone gets the axis from gravity and the
> sign from GNSS before the blackout; round-2 code must do it that way (§15).

### 3.2 · Are phone-detected bends real? (corrected)

Truth = vehicle GPS course, lag-corrected through `veh_idx`. A detection counts as real if a
truth bend of the same direction lies within ±5 s.

| Group | Threshold | Precision | Recall | Apex position error |
|---|---|---|---|---|
| **E** | 10° | 70% | 62% | 7 m |
| **E** | 15° | 78% | 61% | 6 m |
| **E** | 20° | 83% | 60% | 5 m |
| **E** | 30° | 79% | 48% | 4 m |
| **Urban** | 10° | 87% | 84% | 3 m |
| **Urban** | 15° | 88% | 85% | 2 m |
| **Urban** | 20° | 90% | 85% | 2 m |
| **Urban** | 30° | 90% | 86% | 2 m |

Bends are located to within **2–7 m** (median). About **10–13%** of detections are false.

### 3.3 · Landmark density and ceilings (15° threshold)

| Driver | Real bends /km | False /km | Median gap | 1 km windows with **no** bend | Coast now | **Ceiling** | ~~Snaps unambiguous~~ |
|---|---|---|---|---|---|---|---|
| **E** | 0.8 | 0.2 | 376 m | **44%** | 10.2% | **7.9%** | ~~90%~~ |
| B | 2.7 | 0.3 | 258 m | 6% | 16.1% | **3.4%** | ~~95%~~ |
| A | 2.8 | 0.4 | 230 m | 7% | 16.5% | **3.2%** | ~~90%~~ |
| D | 3.4 | 0.4 | 227 m | 0% | 19.6% | **3.2%** | ~~90%~~ |

- **Ceiling** = drift at 1 km if every real bend gave a perfect along-road snap
  (drift rate × distance since the last snap).
- **Unambiguous** = share of snaps where the accumulated error was smaller than half the
  distance to the nearest competing same-direction bend, so the correct bend is the obvious one.

At 20° and 30° the ceilings rise (E 10.2%; urban 3.4–4.8%), so 15° is the better threshold.

> **Corrected.**
> - The ceilings were computed on windows every 20 s over *all* driving, not on the evaluator's
>   blackouts, and assumed the speed error resets at a snap. Recomputed properly (§14): 3.2 / 3.6 / 3.0 /
>   2.8% (E / B / A / D), reachable **only with speed re-estimation** (3.9 / 4.0 / 3.8 / 3.0% actual).
> - **"Snaps unambiguous" is wrong.** It compared only against other bends on the route actually driven —
>   side roads were never candidates. OSM offers a same-side turn about every 90–100 m in Coventry (§13);
>   with those competing, 16–28% of snaps go to the wrong feature (§14).

### 3.4 · Which landmarks each driver physically passes

Measured from the vehicle GPS course — motion signatures, no map needed.

| Driver | Roundabouts /km | Junction turns /km | Bends /km | Stops /km | 1 km blackouts with a **strong** landmark |
|---|---|---|---|---|---|
| **E** | 0.25 | 0.12 | 0.88 | 0.22 | **40%** |
| B | 0.93 | 0.32 | 1.46 | 0.60 | 79% |
| A | 1.35 | 0.45 | 1.02 | 0.58 | 85% |
| D | 1.52 | 0.40 | 1.43 | 0.67 | **92%** |

*Strong = roundabout (≥150° total rotation within 25 s under 45 km/h), junction turn (60–130°
net within 12 s), or stop (under 1 km/h for ≥3 s).*

> **Corrected — inflated.** Only 11–36% of these "roundabouts" lie on a real OSM roundabout; the rest are
> U-turns, turn pairs and car-park loops (§12.2). The strong-landmark shares are too high for the same reason.

### 3.5 · Verdict

- **Urban drivers A, B, D: excellent fit.** Ceilings of 3.2–3.4%, landmarks in 79–92% of
  kilometres. Reaching ~10% looks realistic even with imperfect snaps.
- **Driver E: this method alone will not get it well below 10%.** Ceiling 7.9% at best; 60% of
  kilometres contain no strong landmark. Highways don't bend, and the PS's own scenario — a
  tunnel — has no roundabouts, junctions or signals. E needs motorway-specific landmarks (§9).

> **Corrected verdict (§14).**
> - **Urban:** the physics works (3.0–4.0% with perfect snaps), but junction ambiguity is the real problem.
>   A single-guess matcher gives **8.2–10.1%** — around the target, not comfortably under it. Doing better
>   needs the multi-hypothesis matcher of §7.
> - **E:** confirmed, and stronger: 10.9% → **9.0–9.6%** realistic. A quarter of E's blackouts have no usable
>   bend and the phone catches 61% of E's bends. Map landmarks alone do not give "clearly below 10%".

---

## 4 · Roads in OSM are data, not colour

The colours on openstreetmap.org are only the rendered picture. The `.pbf` file holds geometry
and labels:

| Element | What it is |
|---|---|
| **node** | a single point with lat/lon |
| **way** | an ordered list of nodes — a road centreline |
| **tags** | labels on a way or node, e.g. `highway=primary`, `oneway=yes`, `maxspeed=40 mph` |
| **relation** | a group of ways, e.g. a route or junction |

Every road is a separate polyline that can be queried: nearest segment, its bearing, its
distance from the estimate.

---

## 5 · Gating: when to accept a map correction

```
map candidate inside the gate   →  accept the correction, snap
map candidate outside the gate  →  reject it, trust the engine's own coordinate
```

This also covers roads that exist but are missing from OSM: the vehicle must not be dragged
onto some other road far away.

### 5.1 · Why not a fixed threshold

The engine's uncertainty grows during a blackout. A fixed number of metres fails both ways:

- **early** — too loose: confident to ±5 m, yet it would snap to a road 40 m away
- **late** — too tight: drifted 70 m, the correct road is 70 m away, and the snap is refused

### 5.2 · The formula: a percentage of distance, shaped as an ellipse

Drift is roughly proportional to distance, so a percentage fits the physics. But the error is
**not a circle**: speed is poorly measured while heading is excellent, so uncertainty is a long
ellipse pointing along the direction of travel.

$$\sigma_{along} = \sqrt{\sigma_0^2 + (p \cdot \Delta d)^2}
\qquad
\sigma_{cross} = \sqrt{\sigma_0^2 + (\Delta d \cdot \beta \cdot \Delta t)^2}$$

| Symbol | Meaning | Value from our data |
|---|---|---|
| **p** | drift rate — the percentage | ~0.10 steady, 0.16–0.20 urban |
| **Δd, Δt** | distance and time **since the last snap** (resets at every landmark) | — |
| σ₀ | uncertainty right after a fix | ~5 m (GNSS accuracy / apex error 2–7 m) |
| β | gyroscope bias | median 0.0005 rad/s |

A candidate at along-road offset *a* and sideways offset *c* passes if

$$D^2 = \left(\frac{a}{\sigma_{along}}\right)^2 + \left(\frac{c}{\sigma_{cross}}\right)^2 < k^2
\qquad (k \approx 3)$$

**and** its bearing agrees with the vehicle heading:

$$|\text{road bearing} - \text{heading}| < \theta$$

In Kalman terms this is **Mahalanobis gating**. The heading check rejects parallel roads (a
service road beside a motorway) and crossing roads at junctions.

### 5.3 · The distance estimate has error — does that break the threshold?

No, it is second-order. If Δd is off by about p (say 15%), the threshold is off by p × p ≈
**2–4%**, and it resets to zero at every snap.

### 5.4 · Corrections from the audit

- **p is a median, not a standard deviation.** For a bell-shaped error, σ ≈ 1.48 × median, so a true 3σ gate
  is about 1.5× wider than 3 × p × Δd.
- **Drift % is not constant with distance.** Driver E is 2.6% at 50 m, 4.1% at 100 m, 6.7% at 200 m, 9.1% at
  500 m and 10.2% at 1 km (`out/drift_all_drivers.csv`, tag `round-1`). One percentage tuned at 1 km is
  about 4× too wide at 50 m, which lets wrong candidates in.
- **Use the filter's own uncertainty.** A Kalman filter on along-road position and speed grows its
  uncertainty the right way, shrinks it at every snap, and adjusts when speed is re-estimated. It still
  reads as "a percentage of distance", with the right shape.
- **Simulation (§14):** a gate at 30% of distance since the last snap did worse than 50% for urban drivers
  (10.7–10.8% against 7.6–8.3%): too tight rejects correct bends.
- **σ_cross, minor.** With a constant bias, heading error grows as β·Δt and sideways error as ½·v·β·Δt², so
  the formula is twice as cautious as needed. It leaves out the heading error at blackout start and
  gyro scale error during turns. Harmless for gating.

---

## 6 · The rotating drift circle — a turn exposes the error

**Concern raised:** the estimate is 25 m off; when the vehicle turns 25°, the cursor turns 25°
too — so doesn't the error just rotate along?

**Answer: the turn reveals the error.** Say you are truly at the bend apex and the estimate is
25 m behind on the straight. The gyro detects the turn when it *physically happens*:

```
gyro:  "the turn is happening right now"
map:   "the bend is 25 m ahead of where you think you are"
→      you are 25 m further along than estimated → correct by +25 m
```

After the snap, error drops to the bend-localisation error (**2–7 m**). The reverse case (estimate
ahead) corrects backwards.

**The rotation also helps geometrically.** After a turn of angle α, part of the old along-road
error becomes sideways relative to the new road, and snapping to the new road removes that part
even without matching the bend. Remaining along-road error = error × cos α:

| Turn | Error left from 25 m |
|---|---|
| 15° | 24.1 m |
| 25° | 22.7 m |
| 45° | 17.7 m |
| 60° | 12.5 m |
| **90°** | **0 m** |

Gentle bends need explicit apex matching. **A 90° junction turn removes along-road error almost
for free** — which makes crossroads the most valuable landmarks.

> **Caveat (audit).** Only if the snap picks the *right* new road. Along these routes OSM offers a
> same-side turn every ~90–100 m in Coventry and ~140 m on E's routes (§13); an along-road error beyond
> roughly half that spacing can select the wrong street.
>
> The detector's centred 15 s window also means a turn is confirmed 7.5 s after its apex. The correction
> is applied at the apex time and carried forward.

---

## 7 · Choosing between candidates — Hidden Markov Map Matching

"Compare the expected position with the predicted one and use whichever fits best" is **Hidden
Markov Map Matching**. The problem statement's expected solution names it — verified in the text:
*"A framework (e.g., AI-ML framework or Unscented Kalman Filter + Hidden Markov Map Matching) that binds
the calculated position to known road networks and geometric paths during a dropout."*

When a turn is detected, every mapped bend or junction inside the ellipse is a candidate. Score:

$$J = D^2 + \left(\frac{\Delta\psi_{gyro} - \Delta\psi_{map}}{\sigma_{turn}}\right)^2$$

Lowest J wins. Distance says *where* it could be; turn angle says *which* feature it is — the
gyro reads a turn to within a few degrees, so a 25° bend cannot be confused with a 90° junction.
~~Measured: **85–95%** of snaps have only one candidate in the window.~~ For ties, keep both
hypotheses until the next landmark decides.

> **Corrected.** The 85–95% figure ignored side roads (§3.3). The turn angle separates a bend from a junction,
> but not one ~90° junction from the next, and urban junctions are mostly ~90°. What the matcher still needs:
> 1. **A "no mapped feature" option** — 3–11% of snaps in the simulation came from false detections, and
>    unmapped roads exist. Without it, every false detection snaps to something.
> 2. **Several hypotheses alive at once**, decided by later turns — not only for exact ties.
> 3. **Distance measured along the road network** from the last snap, not in a straight line.
>
> The simulation's 8–10% urban result (§14) is what a matcher *without* these gets.

---

## 8 · Landmark catalogue

### 8.1 · Ranked by usefulness

| Landmark | Detected by | Expected strength | Measured on these routes (§12–§14) |
|---|---|---|---|
| **Roundabouts** | gyro — long continuous turn | **excellent**; UK roads are full of them | 0.27/km E, 0.58–0.97/km urban; the car showed ≥150° of turning at only 40–60% of them (driving straight over turns less) |
| **Junction turns (~90°)** | gyro | **excellent** — geometry alone removes along-road error | real, but a same-side turn option every ~90–100 m urban → ambiguity is the main error source |
| **Bends** | gyro | good, needs apex matching | 73–100% of scored blackouts contain one (evaluator weighting) |
| **Stops at signals / stop lines** | the 99.4% stationary classifier + OSM node | ~~good~~ **cannot move the current benchmark** | `run_evaluation.py` drops blackouts containing a stop; only 27–48% of signal passes involve a stop |
| **Speed bumps, level crossings** | accelerometer shock + OSM tag | ~~good~~ **too sparse here** | 0.03–0.25 traffic-calming passes/km; level crossings ≈0 |
| **School / hospital zones** | slowing down | **weak** — the slowdown is gradual and depends on the driver; usable only as a **speed limit**, not a position fix | not measured |

Speed bumps near schools are the better way to use the school-zone idea: a bump is a sharp event
at a known point.

### 8.2 · What a map usually contains (worldwide, taginfo)

| Key | Objects | Relevance |
|---|---|---|
| `building` | 708 M | none for positioning |
| `highway` | 301 M | **roads and road points — the core** |
| `addr:*` | ~600 M combined | none |
| `name` | 116 M | app UI |
| `natural` | 94 M | none |
| `surface` | 81 M | vibration texture change |
| `landuse` | 52 M | speed context |
| `power`, `waterway` | 52 M, 40 M | none |
| `amenity` | 35 M | speed context |
| `barrier` | 34 M | stops and jolts |
| `oneway` 26 M · `maxspeed` 23 M · `lanes` 20 M · `layer` 16 M · `lit` 15 M | | road attributes |

### 8.3 · Road-relevant elements, grouped by how the phone senses them

**A · Road geometry — constrains position all the time**

| Tag | Use |
|---|---|
| `highway=motorway, trunk, primary, secondary, tertiary, unclassified, residential, service, living_street` | centrelines to snap onto |
| `highway=*_link` | slip roads |
| `oneway` | rules out wrong-direction candidates |
| `lanes`, `turn:lanes`, `width` | snap tolerance |
| `layer`, `bridge`, `tunnel` | stacked roads — don't snap to the road under a flyover |
| `access` | ignore roads cars can't use |

**B · Detected by the gyroscope (turning signatures)**

| Tag | Count | Signature |
|---|---|---|
| `junction=roundabout` | 1.0 M | long continuous turn |
| `highway=mini_roundabout` | — | short loop |
| shared nodes between ways | — | ~90° junction turn |
| `highway=turning_circle` | 2.6 M | U-turn |
| `highway=motorway_junction` + `motorway_link` | 239 k | heading split, only if the exit is taken |
| `junction=cloverleaf`, `trumpet`, `diamond`, `spui`, `jughandle` | — | motorway interchange loops, up to ~270° |

**C · Detected by the stationary classifier (stops)**

| Tag | Count | Why the vehicle stops |
|---|---|---|
| `highway=crossing` | 13.5 M | pedestrian crossing (sometimes) |
| `highway=stop` | 2.5 M | stop sign |
| `highway=traffic_signals` | 2.0 M | red light |
| `highway=give_way` | 1.7 M | yield |
| `railway=level_crossing` | 1.0 M | barrier down |
| `barrier=lift_gate` | 584 k | gate |
| `barrier=toll_booth` | 64 k | toll |

**D · Detected by the accelerometer (jolts)**

| Tag | Count |
|---|---|
| `traffic_calming=bump` | 479 k |
| `traffic_calming=hump` | 423 k |
| `traffic_calming=table` | 324 k |
| `traffic_calming=island`, `cushion`, `rumble_strip`, `choker`, `chicane`, `dip`, `mini_bumps` | 115 k down to 7 k |
| `railway=level_crossing` | 1.0 M |
| `barrier=cattle_grid` | 96 k |
| `bridge=yes` endpoints (expansion joints) | plausible, **untested** |
| `surface` changes (asphalt → sett / cobblestone) | weak at 10 Hz, better at 248 Hz |

**E · Speed priors — bound speed, not position**

`maxspeed`, road class defaults, `living_street`, `amenity=school`, `amenity=hospital`,
`landuse=residential/retail`, `highway=speed_camera`

**F · Not sensed — app UI only**

`name`, `ref` ("now on M1, junction 21"), `highway=milestone` (243 k, a distance marker useful
for validation), `highway=street_lamp` (6.5 M), `highway=bus_stop` (4.2 M — buses stop, cars
don't), buildings, shops, nature, water, power.

---

## 9 · Options for driver E (highway)

| Option | How | Caveat | Audit |
|---|---|---|---|
| **`highway=motorway_junction`** | the node sits "as the last point before the splay at which it is still possible to make a smooth turn" (OSM wiki) — a precise along-road fix | only if the vehicle **takes** the exit | **Corrected:** the node itself is not sensed — the slip road peels off at a few degrees, below the 15° detector. The usable landmark is the slip-road bend after it, already counted as a bend. 0.13 passes/km for E |
| **`tunnel=yes`** | the map knows the tunnel's start and length; if GNSS drops at the portal, the vehicle cannot be past the exit while GNSS is still missing | a **bound**, not a fix — but it is exactly the PS scenario | GNSS returns at the exit, ending the blackout anyway; 0.01 tunnels/km on E's routes |
| **Interchange loops** (`cloverleaf`, `trumpet`) | ~270° continuous turn, very strong gyro signature | only on interchange routes | untested |
| **Bridge expansion joints** | known-position jolt on motorways | **untested** | 0.66 bridges/km on E's routes, but a joint jolt sits mostly above 5 Hz — the round-1 aliasing problem at 10 Hz |
| **`barrier=toll_booth`** | a guaranteed stop on a highway at a mapped point | few tolls in the UK dataset, but **Indian national highways are full of toll plazas** — the PS's real deployment | none on these routes; a stop, so excluded by the current benchmark |

> **Realistic E result (§14):** 10.9% → 9.0–9.6%. None of the options above changes that on this dataset.

---

## 10 · Warning: more landmark types is not automatically better

Every extra landmark type adds a chance of snapping to the wrong feature, especially types that
are rare or poorly tagged. OSM tagging completeness varies by area — especially bumps and
crossings. Plan: once the map is loaded, count each tag along the IO-VNBD routes and rank by
**density × detection reliability**; use only the types that pay for their false-match risk.

> **Done (§12).** Ranking on these routes: **turns** (junction turns, roundabouts, bends) first. **Stops** only
> matter if the benchmark includes stop-and-go blackouts. **Jolts** are too sparse. **Highway features** are
> either not sensed (motorway junction nodes) or untested (bridge joints).

---

## 11 · Map data

**Coverage of all 72 drives** (0.1–99.9 percentile): latitude **51.9468 → 53.7928**, longitude
**−2.2533 → −0.6028** — about 205 × 111 km across the English Midlands to Leeds.

| Driver | Latitude | Longitude | Area |
|---|---|---|---|
| A | 52.3627 → 52.5586 | −1.6034 → −1.2289 | Coventry |
| B | 52.3580 → 52.4791 | −1.5887 → −1.3787 | Coventry |
| D | 52.3948 → 52.4708 | −1.5456 → −1.4703 | Coventry |
| E | 51.9468 → 53.7928 | −2.2533 → −0.6028 | Derbyshire, Staffordshire, Worcester, M1 to Leeds |

**Source:** Geofabrik `england-latest.osm.pbf`, covering every drive. Decision: use the whole file,
**no cropping**. Downloaded 2026-09-15: 1,693,829,796 bytes, data timestamp 2026-09-14T20:21:51Z, MD5
`948d45e796752dd0c47e65fbb229b73d` verified. Stored in `data/osm/` (git-ignored); fetch with
`round2/get_osm_map.sh`. Coordinate details: `data/osm/IOVNBD_COVERAGE.md`. Data © OpenStreetMap
contributors, ODbL.

---

## 12 · Step 1 result — OSM landmarks along the routes

28 sessions, 1,162 km of vehicle track (E 731 km, B 105, A 271, D 55). A landmark counts as passed when the
track comes within 15 m; bridges and tunnels only when 60% of the structure runs along the track.
Source: `analysis/osm_landmarks.py`, output `out/osm_landmarks_run.txt`.

### 12.1 · Passes per km, and % of 1 km windows containing one

*Windows here start every 100 m over all driving — not the evaluator's blackouts.*

| Type | E | B | A | D |
|---|---|---|---|---|
| `junction=roundabout` | 0.26 · 20% | 0.56 · 43% | 0.42 · 31% | 0.78 · 51% |
| `highway=mini_roundabout` | 0.01 · 1% | 0.13 · 8% | 0.13 · 9% | 0.16 · 7% |
| `highway=turning_circle` | 0.00 · 0% | 0.02 · 2% | 0.03 · 3% | 0.04 · 4% |
| **any turn landmark** | **0.27 · 21%** | **0.71 · 52%** | **0.58 · 41%** | **0.97 · 56%** |
| `highway=traffic_signals` | 0.36 · 10% | 1.37 · 39% | 1.30 · 37% | 1.46 · 47% |
| `highway=give_way` | 0.17 · 6% | 0.11 · 10% | 0.25 · 13% | 0.14 · 11% |
| `highway=stop`, `railway=level_crossing`, `barrier=lift_gate`, `barrier=toll_booth` | ≤0.01 | ≤0.01 | ≤0.01 | ≤0.02 each |
| **any stop landmark** | **0.54 · 14%** | **1.50 · 47%** | **1.57 · 43%** | **1.66 · 55%** |
| `traffic_calming=*` | 0.03 · 2% | 0.25 · 5% | 0.19 · 9% | 0.09 · 7% |
| `barrier=cattle_grid` | 0.02 · 1% | 0 | 0 | 0 |
| `highway=motorway_junction` | 0.13 · 12% | 0.21 · 11% | 0.20 · 11% | 0.67 · 21% |
| `tunnel=yes` | 0.01 · 1% | 0.08 · 2% | 0.01 · 1% | 0.11 · 4% |
| `bridge=yes` | 0.66 · 33% | 0.89 · 38% | 0.70 · 24% | 2.11 · 41% |
| `highway=crossing` | 0.63 · 14% | 1.94 · 47% | 3.24 · 61% | 2.76 · 69% |
| `highway=speed_camera` | 0.04 · 4% | 0.08 · 6% | 0.10 · 8% | 0.09 · 4% |
| **any turn / stop / jolt** | **0.86 · 30%** | **2.46 · 73%** | **2.35 · 64%** | **2.72 · 81%** |
| **… + highway features** | **1.65 · 55%** | **3.63 · 84%** | **3.26 · 72%** | **5.61 · 86%** |

Traffic calming, all drivers: bump 29, hump 28, island 17, table 16, choker 6, chicane 5, rumble strip 3,
cushion 2. No toll booths or milestones on these routes. **Open:** D's bridge (2.11/km) and motorway
junction (0.67/km) counts look too high for Coventry — not yet investigated.

### 12.2 · Which of them the car actually showed

Motion from the vehicle GPS course and speed — a best case for the phone. Source: `analysis/landmark_usable.py`.

| | E | B | A | D |
|---|---|---|---|---|
| motion "roundabouts" (≥150° in 25 s) per km | 0.25 | 0.93 | 1.35 | 1.52 |
| …of which on a real OSM roundabout (≤25 m) | 32% | 26% | 11% | 18% |
| OSM roundabouts where the car turned ≥150° | 40% | 47% | 60% | 58% |
| traffic-signal passes with a stop | 29% | 31% | 27% | 48% |
| stops explained by a mapped stop feature | 38% | 43% | 38% | 51% |
| 1 km windows with a usable roundabout or stop | 11% | 40% | 38% | 54% |

A red light is a landmark, a green light is not; over half of all stops are queues or unmapped junctions,
which would give wrong fixes if matched to the nearest signal.

---

## 13 · Junction density along the routes

Every OSM node where drivable ways meet with at least three arms, within 10 m of the track, nodes of one
junction merged within 25 m. A *turn option* is an arm 30–150° left or right of the direction of travel.
Source: `analysis/osm_junctions.py`, output `out/osm_junctions_run.txt`.

| Driver | Junctions /km (median gap) | Excluding service roads | Same-side turn option on the **left** | …on the **right** |
|---|---|---|---|---|
| **E** | 2.9 (104 m) | 2.0 (126 m) | every **142 m** | every **140 m** |
| B | 8.7 (73 m) | 6.1 (93 m) | every **96 m** | every **100 m** |
| A | 9.0 (70 m) | 6.4 (90 m) | every **95 m** | every **95 m** |
| D | 11.3 (66 m) | 8.0 (87 m) | every **101 m** | every **86 m** |

A detected urban left turn has a competing left turn roughly every 100 m. With along-road uncertainty of
tens of metres, two or three candidates often sit inside the gate.

---

## 14 · Audit — snapping simulated under the evaluator's rules

**Protocol** (`analysis/snap_recheck.py`, output `out/snap_recheck_run.txt`): the same blackouts as
`run_evaluation.py` — 1 km, start speed above 4.2 m/s, never below 1.4 km/h, error = |estimated −
true distance|, coast = speed at blackout start. Map bends = bends in the vehicle GPS course, located by
distance (15° detector). A bend can correct the estimate only 7.5 s after its apex. Speed re-estimation
uses the latest anchor at least 10 s back, clamped to 1–45 m/s.

### 14.1 · Median drift at 1 km

| | E | B | A | D |
|---|---|---|---|---|
| blackouts (≤200 per session, as the evaluator) | 2,335 | 600 | 1,261 | 200 |
| sessions with scored blackouts | 15 | 3 | 7 | **1** |
| blackouts with a usable real bend | 73% | 90% | 88% | 100% |
| coast — `run_evaluation.py` | 10.2% | 16.1% | 16.5% | 19.6% |
| coast — this replication | 10.9% | 15.3% | 17.1% | 15.9% |
| §3.3 ceiling formula, on these blackouts | 3.2% | 3.6% | 3.0% | 2.8% |
| perfect snaps · speed kept | 5.4% | 6.4% | 5.6% | 3.3% |
| perfect snaps · speed from the last two anchors | **3.9%** | **4.0%** | **3.8%** | **3.0%** |
| perfect snaps · speed averaged since blackout start | 4.2% | 3.8% | 3.7% | 2.7% |
| phone turns · route bends only · gate 50% · re-estimated | 9.1% | 8.3% | 7.6% | 6.0% |
| phone turns · route bends only · gate 50% · speed kept | 9.1% | 9.5% | 8.2% | 4.4% |
| phone turns · route bends only · gate 30% · re-estimated | 9.3% | 10.8% | 10.7% | 7.2% |
| phone turns · **+ OSM junctions** · gate 50% · re-estimated | **9.6%** | **9.2%** | **10.1%** | **8.2%** |
| phone turns · + OSM junctions · gate 50% · speed kept | 9.0% | 10.7% | 11.4% | 6.7% |
| phone turns · + OSM junctions · gate 30% · re-estimated | 9.6% | 11.7% | 12.7% | 8.9% |

*The replication differs a little from `run_evaluation.py` because the per-session blackouts are drawn at
random; D moves most because it is one session.*

The same with **every blackout counted** (14,962 / 2,057 / 4,926 / 1,103): coast 6.5 / 14.7 / 16.6 / 16.4%;
perfect snaps + speed re-estimated 3.9 / 3.7 / 4.1 / 3.1%; phone turns + OSM junctions (gate 50%,
re-estimated) 6.3 / 10.1 / 10.5 / 9.2%.

### 14.2 · What the snaps did

Gate 50%, speed re-estimated. Shares of snaps.

| | E | B | A | D |
|---|---|---|---|---|
| snaps per blackout, route bends only | 0.39 | 1.87 | 1.94 | 2.76 |
| right bend / wrong candidate / false detection | 77 / 12 / 10% | 92 / 5 / 4% | 90 / 6 / 3% | 88 / 7 / 4% |
| snaps per blackout, + OSM junctions | 0.46 | 1.86 | 2.07 | 2.99 |
| right bend / wrong candidate / false detection | 61 / 28 / 11% | 79 / 16 / 4% | 72 / 22 / 6% | 71 / 25 / 4% |

### 14.3 · What this shows

1. **The physics works.** Perfect snaps plus speed re-estimation: 3.0–4.0% for every driver.
2. **Speed re-estimation is required.** Keeping the old speed after a perfect snap: 3.3–6.4%.
3. **Ambiguity is the main loss.** Adding real junctions raises wrong-candidate snaps from 5–12% to 16–28% and
   urban drift to 8.2–10.1%.
4. **Raw speed re-estimation is fragile.** With wrong snaps it can hurt (D: 8.2% re-estimated, 6.7% kept).
5. **E gains little.** 10.9% → 9.0–9.6%: few usable bends, 61% recall, and a wrong snap on a motorway is costly.

### 14.4 · Limits of this simulation

- **1-D along the true route.** A wrong snap shifts the along-road position, but the car never goes down a wrong
  street, and heading drift is ignored. Optimistic.
- **Map bends come from the vehicle GPS course**, which is cleaner than OSM polylines. Optimistic.
- **One hypothesis at a time**, with no recovery when later turns disagree. Pessimistic.
- **Sign calibration uses the GPS course** of the whole session. Slightly optimistic.

---

## 15 · Evaluator problems that affect every round-2 number

All in `run_evaluation.py` at tag `round-1` (unchanged; round-1 results stand as submitted).

1. **Weighting (line 113).** At most 200 random blackouts per session, so a short drive counts as much as a long
   one. E's sessions range from **3.0% to 26.1%** (median session 13.1%). Counting every blackout gives E
   **6.5%**, sampling per session ~10–11%. Random draws also move D by several points.
   *Recommendation:* a deterministic version — every blackout, each session weighted equally — fixed before
   any round-2 comparison, and never switched to whichever looks better.
2. **Sample size.** D's 1 km figure comes from **one session**, B's from three, A's from seven, E's from fifteen.
   An improvement for D is one drive improving.
3. **Stops excluded (line 115).** Blackouts containing a stop are dropped, so ZUPT and stop landmarks cannot
   show a benefit, and stop-and-go urban driving is not scored.
4. **Distance, not position (line 125).** The score is distance-travelled error. The problem statement asks for
   *positional* drift, and map matching's real failures — wrong street, parallel road — only exist in 2D.
5. **Calibration uses ground truth.** Yaw axis fitted to the CAN yaw rate (`analysis/align_frame.py` lines 48–51);
   turn sign from the GPS course. A phone gets both from gravity and pre-blackout GNSS.

---

## 16 · What is still unproven

1. **2D behaviour** — wrong streets, parallel roads, heading drift (the simulation is 1-D).
2. **Real OSM bend geometry** instead of the GPS-course bends.
3. **How much a multi-hypothesis matcher recovers** of the gap between ~9–10% and the 3–4% ceiling.
4. **Detection without GPS-based calibration** — sign from gravity and pre-blackout GNSS.
5. **Generalisation** — D is one session, B three.
6. **D's suspicious bridge and motorway-junction counts** (§12.1).
7. **Bridge-joint and interchange-loop landmarks.**
8. **Stop landmarks** under a stop-and-go benchmark.
9. **Newson & Krumm (2009)** — to verify before citing.

---

## 17 · Next steps

**Done:** landmark tag counts (§12), usable landmarks (§12.2), junction density (§13), snap audit (§14).

**Decisions — taken 2026-09-16, recorded in `DECISIONS.md`:** results reported by driving condition (average
speed: slow, mixed, 50–70 km/h, fast), every blackout equal inside a group, with real-turn context from the
landmark-spacing idea; 2D position error as the main metric, distance error alongside; a
`moving` and a `stopgo` blackout set; tune on A and B, test once on D and E; step 5 built as a
road-constrained particle filter; no new model training.

**Then build, in this order:**
1. **Round-2 evaluator** — **done 2026-09-16** (`step1_evaluator.py`): fixed blackout list, driving-condition
   groups, round-1 numbers reproduced exactly.
2. **Honest start state and gyro calibration** — **done 2026-09-16** (`step2_calibration.py`): calibration from
   GNSS history only, axis + scale + bias on 10 s windows; median heading error at 1 km 4.9° (A+B) and 6.4°
   (D+E), better than round 1's car-assisted gyro.
3. **2D dead reckoning without the map** — **done 2026-09-16** (`step3_deadreckoning.py`): at 50–70 km/h on D+E the
   2D error is 4.1% at 50 m and 19.8% at 1 km (speed alone 14.2%, heading alone 8.5%) — the number the map must bring
   below 10%.
4. **Road network from OSM** — **done 2026-09-16** (`step4_roadnetwork.py`): 29,389 km of drivable road around the
   routes; 99.5% of the true driving lies on a mapped road in an allowed direction (median offset 2 m), and 98.7% of
   consecutive positions connect through it.
5. **Map matcher** — **done 2026-09-16** (`core/particle.py`, `step5_particlefilter.py`): road-constrained particle
   filter — guesses of road, position and speed, weighed by the gyro's turning against the roads they drive, with a
   fallback to plain dead reckoning.
6. **Tune on A and B only, and freeze** — **done 2026-09-16** (`step6_tune.py`): on the tuning subset 50 m 2.5%
   (baseline 2.5%), 200 m 5.8% (6.8%), 1 km 4.9% (14.3%), with 25% of blackouts worse than no map.
7. **Test once on D and E** — **done 2026-09-16** (`step7_test.py`): at 1 km on the test drivers, the frozen filter cuts
   the 2D error from 19.8% to **5.7%** in the problem statement's 50–70 km/h condition (18% → 63% of blackouts within
   10%), from 26.2% to 6.6% in slow driving and from 22.9% to 9.3% in mixed. On fast motorways it is worse than no map
   (8.3% → 10.0%), which is where 58% of the test blackouts sit, so the pooled figure moves only 10.3% → 9.4%. At 50 m
   nothing changes: below 100 m the engine reports plain dead reckoning by design.
8. **Failure analysis and write-up.**

---

## 18 · Corrections log

| Earlier claim | Where | Status | Evidence |
|---|---|---|---|
| Phone bends only 7–12% genuine; E could reach 3.0% | §3.1 | **Retracted** (sign bug) | §3.1 |
| Error resets at every snap | §2 | **Corrected** — only position resets | speed kept 3.3–6.4%, re-estimated 3.0–4.0% (§14) |
| Speed from two landmarks is an extension | §2 | **Corrected** — required; one landmark suffices; needs outlier rejection | §14.3 |
| Ceilings 7.9 / 3.4 / 3.2 / 3.2% | §3.3 | **Corrected** — different blackouts; only with speed re-estimation | 3.2 / 3.6 / 3.0 / 2.8% recomputed (§14) |
| Snaps unambiguous 90–95% | §3.3, §7 | **Wrong** — side roads never considered | turn option every ~90–100 m; 16–28% wrong candidates (§13–§14) |
| Strong landmark in 79–92% of km | §3.4 | **Wrong** — roundabout signatures inflated | 11–36% on a real roundabout (§12.2) |
| Urban drivers: excellent fit | §3.5 | **Corrected** — ~8–10% with a single-guess matcher | §14 |
| Percentage gate with p = 0.10–0.20 | §5 | **Corrected** — p is a median; drift % grows with distance | §5.4 |
| Stops at signals: good landmark | §8.1 | **Wrong for the current benchmark** | stops excluded; 27–48% of signal passes stop (§12.2, §15) |
| Speed bumps, level crossings: good | §8.1 | **Wrong on these routes** — too sparse | 0.03–0.25/km (§12.1) |
| Motorway junction node: precise fix | §9 | **Wrong** — not sensed | slip road diverges below the 15° detector |
| E baseline 10.2% as "steady highway" | §1 | **Corrected** — depends on weighting; sessions 3.0–26.1% | §15 |

---

## Sources verified during this discussion

- Problem statement PS 26168, "Expected Solution" and "Performance Benchmark" sections (text as provided for SIH 2026)
- taginfo — live OSM tag statistics: https://taginfo.openstreetmap.org
- OSM wiki, Map features: https://wiki.openstreetmap.org/wiki/Map_features
- OSM wiki, `traffic_calming=*`: https://wiki.openstreetmap.org/wiki/Key:traffic_calming
- OSM wiki, `highway=motorway_junction`: https://wiki.openstreetmap.org/wiki/Tag:highway%3Dmotorway_junction
- Geofabrik England extract: https://download.geofabrik.de/europe/united-kingdom/england.html

**To verify before citing:** P. Newson and J. Krumm, "Hidden Markov Map Matching Through Noise
and Sparseness," *ACM SIGSPATIAL GIS*, 2009 — the standard reference for §7.
