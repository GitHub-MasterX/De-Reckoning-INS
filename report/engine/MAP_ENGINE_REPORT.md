# Round 2 — map-aided dead reckoning: what was built, what it does, where it fails

PS 26168 (ISRO) · IO-VNBD · branch `round-2`, everything inside `round2/`. Round 1 is frozen at tag `round-1` and
untouched; `git diff round-1 --stat` lists only `round2/` paths.

---

## 1 · What round 2 set out to do

Round 1 cleared on roughly 10% drift at 1 km for driver E, measured as **distance travelled** error with no map.
Round 2 aimed to bring urban driving to about 10% and driver E clearly below it, using OpenStreetMap road structure
and the turns the gyroscope can feel.

Two things changed in what "drift" means, both recorded in `DECISIONS.md`:

- **2D position error** (the problem statement's "positional drift"), not distance travelled.
- **Grouped by driving condition** — slow (under 40 km/h), mixed (40–50), **50–70 km/h, the problem statement's own
  case**, and fast (70+) — because "driver E" was only ever standing in for a condition.

---

## 2 · What was built

| Step | What | Honesty rule |
|---|---|---|
| 1 | One fixed list of 4,265 blackouts, one scoring code | round 1's own numbers reproduced exactly through it |
| 2 | Gyro calibration from GNSS history before each blackout | no car sensors; beats round 1's CAN-assisted gyro (4.9° / 6.4° heading error at 1 km) |
| 3 | Map-free 2D dead reckoning | the baseline the map has to beat |
| 4 | OSM road network, 29,389 km around the routes | 99.5% of the true driving lies on it, 98.7% of positions connect |
| 5 | Road-constrained particle filter | sees only the last fix, the calibration and phone data |
| 6 | Tuning on drivers **A and B only** | rule fixed in advance; one refinement disclosed |
| 7 | One run on drivers **D and E** | nothing changed afterwards |
| 8 | Failure analysis and this report | — |

**The filter.** Each guess is a road, a position along it and a speed. Every 0.1 s a guess drives on and picks an exit
at junctions, favouring the one nearest the gyro's heading. Every 2 s the turning its roads produced is compared with
the gyro's turning, and guesses that disagree are resampled away. Within 100 m of a fix the engine reports plain dead
reckoning, because a fresh fix beats snapping to a road centreline.

---

## 3 · Results

### Per driver — 2D position error, median, no stops

| Distance | E (test) | B (tuning) | A (tuning) | D (test) |
|---|---|---|---|---|
| 50 m | 2.5 → 2.5% | 3.8 → 3.8% | 4.2 → 4.2% | 5.0 → 5.0% |
| 100 m | 3.5 → 3.5% | 5.2 → 5.2% | 6.0 → 5.9% | 6.8 → 6.8% |
| 200 m | 5.0 → **3.0%** | 8.6 → **5.9%** | 8.4 → **5.3%** | 11.5 → **6.7%** |
| 500 m | 7.7 → **6.2%** | 13.7 → **5.2%** | 11.4 → **5.3%** | 13.1 → **3.8%** |
| 1 km | 10.2 → **9.5%** | 15.4 → **5.0%** | 13.1 → **5.5%** | 15.2 → **3.0%** |

"no map → with map". **Every driver is under 10% at every distance.** In metres at 1 km: E 95.4, B 49.5, A 54.8,
D 30.5 against the 100 m target; at 50 m 1.2–2.5 m against the 5 m target.

### Per driving condition — test drivers D and E, 1 km

| Condition | No map | With map | Blackouts within 10% |
|---|---|---|---|
| slow, under 40 km/h | 26.2% | **6.6%** | 11% → 56% |
| mixed, 40–50 | 22.9% | **9.3%** | 18% → 53% |
| **50–70 km/h (the PS case)** | 19.8% | **5.7%** | 18% → 63% |
| fast, 70+ | 8.3% | **10.0%** | 60% → 50% |

### With stops allowed, 1 km

E 11.1 → 10.0%, B 18.5 → 7.8%, A 17.5 → 8.9%, D 18.2 → 6.2%.

### The map earns its keep where turns are

Distance from the last real turn to the 1 km mark, test drivers:

| Last turn | No map | With map |
|---|---|---|
| within 250 m | 17.7% | 5.0% |
| 250–500 m | 13.8% | 8.1% |
| 500–750 m | 11.7% | 9.5% |
| over 750 m | 8.2% | **11.2%** |

---

## 4 · Where it fails, and why

From `step8_failures.py`, which re-ran 400 blackouts — **the 200 worst plus 200 drawn at random**, so the shares below
describe the failures, not their frequency. The real frequency is that **49% of test blackouts end worse than with no
map** (31% for the tuning drivers), almost all of them on fast motorway.

| Cause | Share of failures | With map | No map | What happens |
|---|---|---|---|---|
| **Off the driven route** | 48% | 29.8% | 9.5% | the estimate ends a median 251 m from anywhere the car went — a wrong branch, slip road or parallel carriageway |
| **Straight road** | 29% | 23.4% | 6.9% | on the route but sliding along it: no turn inside the blackout, so nothing pins the guesses |
| **Along the road** | 23% | 40.5% | 17.0% | on the route but more than 50 m ahead or behind, although turns happened — a speed error the map could not catch |
| On the spot | 1% | 3.2% | 1.4% | on the route and within 50 m along it; these are ties, not failures |

Both tests are geometric. **Off the route** means the estimate ends more than 30 m from the track the car actually
drove; **along the road** measures how far back along that track it sits. Two earlier versions were wrong and were
replaced: the first compared OSM way ids, so a long curving way counted as "the same road" even where it led
elsewhere; the second split the error along and across the heading at the finish line, which called a 600 m lag
"sideways".

By condition, among the failures: fast motorway splits between leaving the route (48%) and sliding along a straight
(42%); the slower conditions fail by leaving the route (mixed 60%, slow 47%, 50–70 km/h 42%) or by speed error along
the route (slow 50%, 50–70 km/h 44%, mixed 33%). The fallback to dead reckoning never fired in the sample.

Where the filter wins: 33% of the improvements are straights (2.8% against 9.5%), **30% land essentially on the spot**
(1.5% against 15.7%), 23% are still off the route but far closer than before (6.8% against 15.8%), and 14% are
along-route corrections (7.6% against 26.4%). That is the sawtooth idea working: a turn re-anchors the position and
the error restarts near zero.

Pictures: `out/plots/r2_failures.png` (true track, map-free path, filter path, over the local roads).

---

## 5 · What these numbers are, and are not

- **They are medians.** At 1 km the share of individual blackouts inside 10% is E 52%, B 66%, A 65%, D 70%.
- **Per-driver figures mostly reflect what each driver drove.** E's 1 km blackouts are 74% fast motorway with a median
  of zero turns; D's are 47% slow and 40% mixed with three turns.
- **D is a single session** (83 blackouts at 1 km) — the least robust row in every table.
- **The map hurts on fast motorway**, where 58% of the test blackouts sit. That is why the pooled test figure moves
  only from 10.3% to 9.4% while every other condition improves several-fold.
- **50 m is unchanged by design**: below 100 m the engine reports dead reckoning, so the map neither helps nor hurts.

---

## 6 · Open for round 3

1. **Long straights.** A handover back to dead reckoning from the last map-corrected point (`straight_blend_m=300`)
   nearly halved the harm on A+B (25% → 13% of blackouts worse) at a worse median (4.9% → 6.2%). The tuning rule
   optimised the median, so it was not adopted. Settle it on A+B, then spend one more test run.
2. **Wrong-road lock-on.** The costly failure. Candidates: keep more hypotheses alive at junctions, a stricter prior
   for leaving a road class, and using the road's own bend shape rather than only accumulated turning.
3. **Driver E's phone reports about 54% of every real turn** — constant, and calibrated out from GNSS history, but
   worth understanding.
4. **Stops as landmarks** cannot help while the scored blackouts exclude stops; they need a benchmark that includes
   stop-and-go, which `DECISIONS.md` already defines.

---

## 7 · Reproducing this

From the repository root, with `data/clean/` and the England map in place:

```bash
.venv/bin/python3 round2/step1_evaluator.py          # the blackout list and scoring checks
.venv/bin/python3 round2/step2_calibration.py        # gyro calibration from GNSS history
.venv/bin/python3 round2/step3_deadreckoning.py      # the map-free baseline
.venv/bin/python3 round2/step4_roadnetwork.py        # the road network (~2 min scan)
.venv/bin/python3 round2/step6_tune.py --limit 120   # tuning on A and B, freezes out/pf_params.json
.venv/bin/python3 round2/step7_test.py               # the one frozen run on D and E
.venv/bin/python3 round2/run_round2_evaluation.py    # the results, per driver and per distance
.venv/bin/python3 round2/step8_failures.py           # why it fails, and the pictures
```

Round 1 still runs unchanged from the repository root: `python3 run_evaluation.py`.
