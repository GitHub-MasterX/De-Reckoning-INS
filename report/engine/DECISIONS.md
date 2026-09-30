# Round 2 — decisions

Settled before building. Each changes what the numbers mean, so any change gets a new dated entry
here with the reason — never a silent edit.

---

## 2026-09-16 · Step 0 — scoring rules

Proposed in the step-2 plan and accepted ("okay start step wise").

| # | Decision | Rule |
|---|---|---|
| 1 | ~~**Weighting**~~ | ~~Every blackout in the fixed list counts. Headline = session-weighted median (each session's blackouts share one unit of weight). The every-blackout median is always shown next to it.~~ **Replaced the same day — see "Change to decision 1" below.** |
| 2 | **Main metric** | **2D position error** at the checkpoint ÷ true distance travelled — the problem statement's "positional drift". Distance error (the round-1 metric) reported alongside. |
| 3 | **Blackout sets** | `moving` — round-1 rule: speed never below 1.4 km/h. `stopgo` — stops allowed; the checkpoint must be reached within 10 min. |
| 4 | **Split** | Tune on drivers **A and B** only. **D and E are test-only**, run once with frozen settings. |
| 5 | **Step-5 design** | **Road-constrained particle filter** (Hidden Markov Map Matching solved with many hypotheses). The event-based matcher from the audit stays as the comparison. |
| 6 | **Training** | No new model training in step 2. The trained motion classifier is reused unchanged. The matcher's few settings are tuned on A and B and frozen before D and E are touched. |

---

## 2026-09-16 · Step 1 — how blackouts are drawn

| Rule | Value | Why |
|---|---|---|
| Sessions | `data/alignment.csv`: \|sync_r\| ≥ 0.40, not `Vtb1`, ≥ 3,000 aligned rows | the same 28 sessions as round 1 and the audit |
| Start points | one every **250 m** of travelled distance | every kilometre counts equally whatever the speed; round 1 started every 2 s, which over-weights slow driving, and 2 s spacing makes near-duplicate blackouts |
| Start speed | above 4.2 m/s (15 km/h) | round-1 rule |
| History | at least **300 s** of session before the start | step 2 calibrates the gyro on GNSS before the blackout |
| Checkpoints | **50, 100, 200, 500, 1000 m** of true distance travelled | the PS benchmarks are 50 m and 1 km; each checkpoint is valid on its own, so a stop at 600 m does not remove the 50 m result |
| Clean data | inside the blackout: phone IMU present, vehicle position present, no vehicle GNSS dropout | a frozen truth position cannot grade anything |
| True distance | vehicle speed (`speed_best_al`) integrated over the phone clock (`t_raw_s`) | round-1 definition, with exact timing |
| True position | vehicle `lat`/`lon` through `veh_idx`, converted to metres with WGS84 radii at the start point | a 0.7% map-scale error would already be 7 m per km |
| Positions scored | estimate − truth, metres from the last fix before the blackout | |
| Context columns | per checkpoint: average speed, driving-condition group, real turns inside, distance since the last turn — from ground truth, **for reporting only, never an engine input** | see "Change to decision 1" |

The list is `round2/out/blackouts.parquet`, built by `round2/step1_evaluator.py` with `round2/core/`.

---

## 2026-09-16 · Change to decision 1 — report by driving condition, not by session

Accepted: "okay go with option 3 then, along with any pros that are helpful from the other idea".

**Why.** Sessions run from 3 km to 214 km. Weighting every session equally let a session with one blackout
count as much as one with 772 — driver E read 9.8% at 500 m but 7.3% at 1 km for that reason alone.
Counting every blackout instead lets E's four long motorway drives decide E's number (88% of its 1 km
blackouts). "Driver E" was only ever standing in for a driving condition.

| Rule | Value |
|---|---|
| **Groups** | average speed over the blackout (true distance ÷ elapsed time), per checkpoint: **slow** under 40 km/h · **mixed** 40–50 · **ps_60** 50–70, the problem statement's "1 km at 60 km/h" · **fast** 70 and over |
| **Inside a group** | every blackout counts equally (plain median); blackouts and sessions shown |
| **Headline** | each group on the test drivers D and E; the tuning drivers A and B shown separately |
| **Per driver** | still reported, every blackout equal, for transparency |

**Taken from the landmark-spacing idea**

| Rule | Value |
|---|---|
| **Landmark context** | every blackout carries its real turns (at least 15° in the vehicle GPS course): turns inside it, and the distance from the last turn — or from where GPS was lost — to each checkpoint. Reporting only, never an engine input. |
| **Why** | the spacing of landmarks is what should decide drift once corrections exist, so from step 5 every group's drift is broken down by that distance |
| **Route spacing** | each session's median gap between real turns is reported |

**Not adopted, and why**

| Idea | Reason |
|---|---|
| Blackouts spaced by each route's landmark gap | counts would still grow with route length (214 km ÷ 376 m ≈ 570 against 3 km ÷ 376 m ≈ 8), and the test set would depend on the method's own signal |
| Blackout length as multiples of tunnel length | mapped road tunnels in the dataset area are mostly underpasses: median 15 m, mean 56 m |

**Tunnel context, kept for the write-up.** Of 1,009 mapped road tunnels in the dataset area, 13 are at least
500 m long and 5 at least 1 km (`analysis/tunnel_lengths.py`). The 1 km checkpoint is longer than almost
every real tunnel in the region, which makes it a demanding test.

---

## 2026-09-16 · Step 2 — start state and gyro calibration

| Rule | Value | Why |
|---|---|---|
| **Start state** | the last GNSS fix at the blackout start row: position, course, speed | what a phone has when GNSS drops |
| **Engine input** | `core/engine_input.py` packs the start state, the calibration and the phone data from the start onward — nothing else | later steps cannot read the vehicle track |
| **Calibration data** | GNSS course and phone gyro from **before** the start only | fitted while GNSS still worked |
| **Turn-rate model** | turn = scale × (gyro · axis) − bias | the phones under-report turning by a constant factor: driver E's phone reports about 54% of it (scale 1.84), A and B about 95% |
| **Method** | **window fit** — axis, scale and bias fitted on turning accumulated over 10 s windows of all history (`Calibrator.at_windows`) | chosen on A+B only: median heading error at 1 km 4.9°, against 7.4° for the 10 Hz rate fit and 6.2° with a recent-bias median |
| **Fallback** | the 10 Hz rate fit, scale 1, when history holds fewer than 3 turning windows | an engine uses what it has; 2% of A+B starts, none of D+E |
| **Sign check** | wrong sign counted only on blackouts whose true turn is at least 30° | on straight roads only noise is left; the first run's 3–26% "wrong sign" was that artefact |

---

## 2026-09-16 · Step 3 — map-free 2D baseline

| Rule | Value | Why |
|---|---|---|
| **Engine** | heading = last GNSS course + calibrated gyro turning; speed = last GNSS speed, held, and zero while the motion classifier says stationary; position integrated on the phone clock (`core/deadreckoning.py`) | the simplest honest engine — the number the map has to beat |
| **Stationary detection** | round-1 motion classifier, each driver scored by the model trained without them (`{driver}_holdout`), fed the raw phone gyro | round 1 removed gyro bias using stops found in the true speed; dropping that changed nothing (accuracy 99.0% A+B, 99.6% D+E either way) |
| **Feature contract** | `core/motion.py` computes the 26 features in batch | checked identical to `idr/features.py` |
| **ZUPT always on** | also on the moving set | the engine cannot know whether a blackout will contain stops; on the moving set it cost nothing |
| **Diagnostics** | the engine's speed with the true heading, and the true speed with the engine's heading — reporting only | splits the 2D error into its speed and heading parts |

---

## 2026-09-16 · Step 4 — road network

| Rule | Value | Why |
|---|---|---|
| **Region** | every drivable OSM way with a node within about 2.5 km of a track (map cells of about 1.4 km, 2-cell margin) | a 1 km blackout cannot leave a 1.3 km circle around its start, and the start lies on the track — no leak |
| **Road classes** | motorway, trunk, primary, secondary, tertiary, unclassified, residential, living street, service, every `_link`, `road`; `area=yes` excluded | everything a car can drive, car parks included |
| **One-way** | `oneway=yes`, `-1`, `no` as tagged; implied one-way on `highway=motorway` and roundabouts | OSM convention |
| **Kept for later** | roundabout, bridge, tunnel, layer, private access, car-park aisle, speed limit (tagged on 31% of length) | attributes the filter may use |
| **Stored** | `data/osm/road_network.npz` (git-ignored, 93 MB): nodes, segments, drivable directions, the directions leaving each node; loaded by `core/roadnet.py` | |
| **Carried into step 5, to be tuned** | one-way as a strong rule with a small escape chance, not absolute; hypotheses may hop to a road within about 15 m; hypotheses keep their level where roads are stacked | the checks found real one-way conflicts (0.1% of distance, clustered in central Coventry), unconnected hops on the stacked Coventry ring road, and a few links missing from the map |

---

## 2026-09-16 · Step 5 — the particle filter

| Rule | Value | Why |
|---|---|---|
| **A guess** | which drivable direction of which road, how far along it, how fast (`core/particle.py`) | the road network carries the position, so only along-road position and speed are free |
| **Moving** | every 0.1 s a guess drives on; its speed wanders (`q_speed`); at a junction it takes an exit, favouring the one nearest the gyro's heading (`sigma_choice_deg`) and slightly favouring roads of the same standing | the exit choice is a prior on driver behaviour, not a measurement |
| **Weighing** | every 2 s: the turning the guess's roads produced against the gyro's turning (`sigma_turn_deg`), the road's direction against the gyro's heading (`sigma_abs_deg`), and a penalty for exceeding a tagged speed limit | this is the turn-matching idea, applied continuously, gentle bends included |
| **Resampling** | when the effective number of guesses falls below half, with a little jitter added | standard particle filter |
| **Fallback** | if every guess disagrees for three updates, re-seed around plain dead reckoning; if no road is near the fix at all, report plain dead reckoning | covers car parks, unmapped roads and wrong lock-ons |
| **Handover from the fix** (`dr_blend_m`) | report plain dead reckoning until 100 m from the fix, then hand over to the map over the next 100 m | right after a fix, dead reckoning beats snapping to a road centreline: every setting without this sat at 7.7% at 50 m against the baseline's 2.5% |
| **Output** | the weighted centre of the strongest group of guesses | a plain mean would sit between two rival roads |

---

## 2026-09-16 · Step 6 — tuning, on A and B only

**Rule, fixed before any result was seen:** the lowest median 2D error at 1 km, among settings whose 50 m median is
within 1 point of the map-free baseline; ties to the smaller share of blackouts made worse.
**Refined once, disclosed:** several settings tied on both ruled numbers, leaving the choice to row order, so the
200 m median now breaks such ties (`EXECUTION_LOG.md` entry 18).

| | |
|---|---|
| **Frozen settings** | `q_speed=0.4`, `sigma_turn_deg=10`, `sigma_abs_deg=15`, `dr_blend_m=100`, `straight_blend_m=0`, 500 guesses — `out/pf_params.json` |
| **On the tuning subset** | 50 m 2.5% (baseline 2.5%) · 200 m 5.8% (6.8%) · 1 km 4.9% (14.3%) · worse than no map at 1 km: 25% of blackouts |
| **Disclosed trade-off** | handing back to dead reckoning on long straights (`straight_blend_m=300`) gives a worse median at 1 km (6.2%) but nearly halves the harm (13% of blackouts worse). The pre-stated rule optimises the median, so it was not chosen; worth revisiting if reliability matters more than the median |
| **Test set** | D and E are read once, in step 7, with these settings; no tuning after that |
