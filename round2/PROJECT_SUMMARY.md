# PS 26168 — Intelligent Dead Reckoning: the whole project so far

One document covering both rounds. Round-1 detail lives in `data/report/` on tag `round-1`; round-2 detail in
`round2/ROUND2_REPORT.md`, `DECISIONS.md`, `EXECUTION_LOG.md` and `MAP_LANDMARK_APPROACH.md`.

---

## 1 · The problem

A phone on a dashboard mount, no connection to the car. When GNSS drops — tunnel, underpass, urban canyon, multi-level
car park — the app must keep the vehicle icon moving from the phone's own sensors, then rejoin GNSS cleanly.

**The benchmark:** positional drift under **10% of the distance travelled** — the problem statement names under 5 m over
50 m, and under 100 m over 1 km at 60 km/h.

**The data:** IO-VNBD — 72 drives by four drivers (A, B, D, E) around Coventry and the Midlands. Phone IMU at 10 Hz;
the car's own GPS and CAN are the answer key and may never be an input.

---

## 2 · The dataset, as we use it

- **43 columns per drive**, documented in `data/report/COLUMNS.md`. Phone: accelerometer, gyroscope, magnetometer.
  Vehicle (grading only): GPS position, course and speed, CAN yaw rate and wheel speeds.
- **Cleaned per session**, not per file: each recording is aligned to the vehicle data by a two-stage lag search
  (coarse on the GPS track, fine on the gyro), and every drive keeps its original values — corrections were added as
  **new columns**, never overwritten.
- **28 sessions pass the alignment check** (`|sync_r| ≥ 0.40`, excluding the stress-test drive `Vtb1`): about
  **1,162 km** — E 731 km, A 271, B 105, D 55.
- **The hard constraint:** 10 Hz. Vibration above 5 Hz folds into the signal band, which is why the accelerometer can
  never be integrated twice here.

---

## 3 · Round 1 — what was built, and what it proved

| Piece | What it is |
|---|---|
| Cleaning and alignment engine | sessions, lag correction through `veh_idx`, validity flags |
| Motion classifier | 26 features over 2 s windows: **99.4% accuracy**, each driver scored by a model that never saw them |
| Blackout evaluator | `run_evaluation.py`: coasting, the ML speed model, and an oracle, over 50 m … 1500 m |

**Results (distance-travelled error, median):**

| Driver | 50 m | 1 km |
|---|---|---|
| E | 2.6% (1.3 m) | **10.2%** (101.8 m) |
| B | 3.2% (1.6 m) | 16.1% (161.1 m) |
| A | 5.2% (2.6 m) | 16.5% (164.9 m) |
| D | 5.3% (2.6 m) | 19.6% (196.0 m) |

**What round 1 established:**
- The 5 m over 50 m target is met by every driver.
- Coasting at the last known speed beats the trained speed regressor, whose bias compounds (E reached 43% at 1 km).
- The oracle (true speed changes) sits near 1%, which proves the evaluator itself is sound and the gap is the speed
  estimate, not the maths.
- **Retracted honestly:** a curvature method that looked excellent turned out to read the map at the *true* position;
  run honestly it diverged to 18.6%.

Round 1 was cleared on that ~10% result.

---

## 4 · Round 2 — the audit that came first

Before building anything, the round-1 claims were re-checked. Several did not survive:

| Claim | Outcome |
|---|---|
| "Error resets at every landmark" | Only position resets, not the speed error behind it |
| "Speed from two landmarks" (an extension) | Required, not optional — and one landmark suffices, since the last fix is an anchor |
| "85–95% of snaps are unambiguous" | Wrong: it ignored side roads. OSM offers a same-side turn every ~95 m in Coventry |
| Ceilings of 3.2–7.9% | Right numbers, wrong reasoning: computed on different blackouts, and reachable only with speed re-estimation |
| Stops at traffic signals as landmarks | Cannot help: the scored blackouts exclude stops, and only 27–48% of signal passes involve stopping |
| Motion-detected roundabouts (1.35/km) | Inflated: only 11–36% sit on a real roundabout |

Two further problems were found in how round 1 measured things: the headline number depended on how sessions were
weighted, and the metric was **distance travelled**, not **2D position** as the problem statement asks.

---

## 5 · Round 2 — how it was made honest

| Rule | Why |
|---|---|
| Round 1 frozen at tag `round-1`; all new work inside `round2/` | `git diff round-1 --stat` lists only `round2/` paths; the round-1 evaluation was re-run from the tag and reproduced every committed output byte for byte |
| Results grouped by **driving condition** (slow / mixed / **50–70 km/h** / fast), not by driver | "Driver E" was only ever standing in for a condition |
| **2D position error** as the metric | what the problem statement actually asks for |
| Tune on **A and B**, test once on **D and E** | the test set is spent once; nothing was changed afterwards |
| The engine sees only a sealed input | last GNSS fix, gyro calibration from *history*, phone data — never the true track |

---

## 6 · Round 2 — what was built, step by step

| Step | What | Result |
|---|---|---|
| 1 | Fixed list of 4,265 blackouts and one scoring code | reproduces round 1's own numbers exactly |
| 2 | Gyro calibration from GNSS history only | beats round 1's CAN-assisted gyro: 4.9° (A+B) and 6.4° (D+E) heading error at 1 km. Found that the phones under-report turning by a constant factor — driver E's by about half |
| 3 | Map-free 2D dead reckoning | the baseline: at 50–70 km/h, 19.8% at 1 km |
| 4 | OSM road network, 29,389 km around the routes | 99.5% of real driving lies on it, 98.7% of positions connect |
| 5 | Road-constrained particle filter | guesses of road, position and speed, weighed by the gyro's turning against the roads they drive |
| 6 | Tuning on A and B, then frozen | rule fixed in advance; one refinement disclosed |
| 7 | One run on D and E | see below |
| 8 | Failure analysis and report | why it loses, with pictures |

**The filter in one paragraph.** Each guess is a road, a position along it and a speed. Every 0.1 s it drives on and
picks an exit at junctions, favouring the one nearest the gyro's heading. Every 2 s the turning its roads produced is
compared with the gyro's turning, and guesses that disagree are resampled away. Within 100 m of a fix the engine
reports plain dead reckoning, because a fresh fix beats snapping to a road centreline.

---

## 7 · Where it stands — the numbers

**Per driver, 2D drift, no stops** (no map → with map; every cell passes the 10% benchmark):

| Distance | E (test) | B (tuning) | A (tuning) | D (test) |
|---|---|---|---|---|
| 50 m | 2.5 → 2.5% | 3.8 → 3.8% | 4.2 → 4.2% | 5.0 → 5.0% |
| 200 m | 5.0 → 3.0% | 8.6 → 5.9% | 8.4 → 5.3% | 11.5 → 6.7% |
| 500 m | 7.7 → 6.2% | 13.7 → 5.2% | 11.4 → 5.3% | 13.1 → 3.8% |
| 1 km | 10.2 → **9.5%** | 15.4 → **5.0%** | 13.1 → **5.5%** | 15.2 → **3.0%** |

In metres at 1 km: E 95.4, B 49.5, A 54.8, D 30.5 — all inside the 100 m target.

**Per driving condition at 1 km, test drivers D and E:**

| Condition | No map | With map | Within 10% |
|---|---|---|---|
| slow, under 40 km/h | 26.2% | 6.6% | 11% → 56% |
| mixed, 40–50 | 22.9% | 9.3% | 18% → 53% |
| **50–70 km/h (the PS case)** | 19.8% | **5.7%** | 18% → 63% |
| fast, 70+ | 8.3% | 10.03% | 60% → 50% — the one condition the map makes worse |

**Where the map earns its keep:** within 250 m of a real turn, 1 km drift falls from 17.7% to 5.0%. Over 750 m since the
last turn it rises from 8.2% to 11.2% — nothing pins the guesses along a straight road.

---

## 8 · What fails, and why

Of the blackouts where the map loses (sample weighted towards failures, so these are shares of failures, not rates —
the rates are 49% of test blackouts and 31% of tuning ones):

| Cause | Share | With map | No map |
|---|---|---|---|
| Ends off the driven route (median 251 m away) | 48% | 29.8% | 9.5% |
| Slides along a straight with no turn to match | 29% | 23.4% | 6.9% |
| Speed error along the right route | 23% | 40.5% | 17.0% |

Where it wins, a third of the gains land essentially on the spot (1.5% against 15.7%). Pictures:
`out/plots/r2_failures.png`.

---

## 9 · Honest caveats to carry into any presentation

1. **All headline figures are medians.** At 1 km the share of individual blackouts inside 10% is 52% (E), 66% (B),
   65% (A), 70% (D).
2. **Per-driver numbers mostly reflect what each driver drove** — E's kilometres are 74% fast motorway with no turns;
   D's are 47% slow with three turns.
3. **D is a single session** (83 blackouts at 1 km), the least robust row anywhere.
4. **Round-1 and round-2 numbers are not comparable**: round 1 scored distance travelled, round 2 scores 2D position.
5. **Slow driving still fails at short range** (13.0% at 50 m) and **fast motorway fails at 1 km** (10.03%).
6. **No AI was added in round 2.** The map matcher is an algorithm; the only trained model is round 1's motion
   classifier, reused unchanged. The problem statement lists "UKF + Hidden Markov Map Matching" as an acceptable
   framework, so this is within spec.

---

## 10 · What is open

1. **Long straights** — a handover back to dead reckoning from the last map-corrected point halved the harm on A+B but
   worsened the median, so the pre-stated tuning rule rejected it. First candidate for round 3.
2. **Wrong-road lock-on** — the expensive failure: more hypotheses at junctions, stricter priors for leaving a road
   class, matching the road's bend shape rather than only accumulated turning.
3. **Stop-and-go landmarks** — traffic signals can only help once a stop-and-go benchmark is scored.
4. **Driver E's phone reports about 54% of every real turn** — calibrated out, but not explained.
5. **The Android app and the edge engine** are not built; the work so far is the engine's logic, proven offline.
6. **Nothing is pushed to GitHub** — tag `round-1` and branch `round-2` exist only on this machine.

---

## 11 · Where everything lives

| Path | What |
|---|---|
| tag `round-1` | round 1 exactly as submitted: `run_evaluation.py`, `idr/`, `models/`, `analysis/`, `data/report/` |
| `round2/README.md` | layout and how to run every step |
| `round2/PROJECT_SUMMARY.md` | this document |
| `round2/ROUND2_REPORT.md` | round 2 in detail |
| `round2/DECISIONS.md` | every settled rule, dated, with the reason |
| `round2/EXECUTION_LOG.md` | every run: why, how long, what came out, what went wrong |
| `round2/MAP_LANDMARK_APPROACH.md` | the design and the audit that corrected it |
| `round2/out/` | results, logs and plots |

**Reproducing the headlines:**

```bash
python3 run_evaluation.py                            # round 1, unchanged
.venv/bin/python3 round2/run_round2_evaluation.py    # round 2, per driver and per distance
```
