# Challenges Faced, and How Each Was Resolved

Every real obstacle encountered while building the final system, in the order it was encountered, including the
ones that were tried and rejected. Nothing here is smoothed over — a rejected idea is reported as rejected, with
the number that rejected it.

## 1 · The dataset itself was not clean

Before any model could be trained, the raw IO-VNBD dataset needed real cleaning work: two different column-naming
schemes across drives, case-mismatched file pairs, latin-1 encoding, a sensor log that assumed a perfect 10 Hz
clock when it was not always true. Time alignment between the phone's IMU and the vehicle's own GNSS/CAN truth
required a two-stage process — a coarse GPS-track match within ±10 minutes, then a fine gyro-vs-yaw match within
±30 seconds — because phone and vehicle clocks drift independently. 98.6% of rows aligned successfully; the
remainder were flagged and excluded rather than guessed at.

## 2 · Physics formulas for speed, tried first, all failed

Three closed-form physics approaches were tried before any learned model:

| Approach | Formula | Result |
|---|---|---|
| Integrate accelerometer readings | v = ∫a·dt | Worse than assuming speed never changes, at every window length from 5 s to 30 s |
| Turn-rate ÷ steering geometry | v = a_lateral ÷ ω | Accurate only on phones that could physically feel a corner — useless on 2 of 4 test phones |
| Map curvature | v = ω ÷ κ_road | Map curvature vs. real vehicle curvature: r = 0.22 — too weak to invert |

Why all three failed is explained mechanically, with the aliasing measurement behind it, in `MECHANISM.md`.

## 3 · The metric itself was misleading, and had to be fixed before anything else

The engine was originally scored only at the 1 km finish line of each blackout. This let an estimate wander far
off course mid-blackout and still score well if it happened to be close again by the end — watching the engine's
own replay screen exposed this directly. Switching to the error **averaged along the entire blackout** revealed
two problems invisible under the old metric:

- **42% of blackouts left the driven road** at some point, by 30 m or more.
- **Every blackout contained at least one 1-second jump** of the displayed position by tens of metres — the
  filter's internal belief was reasonable, but multiple road hypotheses could compete and the reported cursor
  could leap between them.

## 4 · Fixing the reporting layer, without touching the model underneath

Both problems above were failures of *display*, not of the filter's own belief. Two fixes, entirely in how belief
becomes an on-screen position:

- **Mode hysteresis** — the displayed position does not switch to a competing road hypothesis until that
  hypothesis has clearly been winning for several updates, not one instant.
- **A speed-limited cursor** — the displayed position cannot move faster than a real vehicle could, closing gaps
  quickly along the direction of travel but never sideways.

Result: cursor jumps fell from 71% of blackouts to 5%; blackouts leaving the road fell from 45% to 29%; and, as a
side effect of no longer chasing bad hypotheses, drift itself improved (7.0% → 5.9% median).

## 5 · The hunt for speed: eight further physics ideas, all rejected

With the reporting layer fixed, the remaining error was almost entirely speed error. Eight further approaches
were tried and measured on tuning drivers only, none adopted:

| Idea | Result |
|---|---|
| Decay speed toward the road's tagged limit | Limits are routinely exceeded; no improvement |
| Tighten the filter's own speed-limit penalty | Measurably worse |
| A learned "speed regresses to the mean" rule | Helped some blackouts, hurt others; net negative |
| Widen the filter's initial speed uncertainty | Badly worse — the map's turns are too sparse to recover the right hypothesis |
| Trend/derivative features for the speed signal | No measurable improvement |
| Deliberately exaggerate predictions to counter caution | Measurably worse — the model's caution is the statistically correct response |
| Native 248 Hz spectral features (own recordings) | Worse than coarse features — not enough data to fit a larger feature set |
| A learned arbiter choosing between held-speed and the model | Right only 54% of the time — no better than chance |

## 6 · The breakthrough

The insight that broke the deadlock, and the full mechanism behind it, is documented in `MECHANISM.md`: a
gradient-boosted tree model trained on four inputs that never require the destroyed part of the aliased signal.
Measured on drivers never used for training: **3.15 m/s** RMS error at 30 seconds ahead, against **6.09 m/s** for
simply holding the last known speed — and **2.47 m/s against 6.25 m/s** specifically when the vehicle was slow at
the moment of loss, which is where the engine had failed worst.

## 7 · Three stubborn clips, and what they revealed about tuning itself

Three real blackouts still missed the 10% target even in the finished engine. Each was diagnosed by substituting
the true value for one input at a time (speed, heading, road choice) to isolate the cause. Several targeted fixes
were tried and mostly rejected — a same-road-through-junction bonus helped the general case but made no
measurable difference on these specific clips (motorway-heavy, a different failure mode); a road-class-switch
penalty helped one case and broke another that legitimately needed that exact switch.

The finding that mattered more than any individual fix: **small setting changes move the aggregate result by a
fraction of a percentage point, while flipping individual blackouts across the pass/fail line roughly 5% of the
time.** One real blackout scored anywhere from 3.3% to 26.7% across four otherwise-reasonable configurations,
because that specific moment sits on a genuine coin-flip between two roads the map cannot disambiguate. This is
why every setting in this project was chosen using the aggregate result across hundreds of blackouts on tuning
drivers only, frozen, and applied exactly once, unmodified, to drivers never used for tuning.

## 8 · Validating outside the original dataset — India, a two-wheeler, a different sensor rate

Everything above was built on IO-VNBD — cars, mostly 10 Hz, England. To check it was not an artifact of that one
dataset, the full pipeline was re-run on the team's own recordings: a two-wheeler, phone hand-held, 248 Hz,
Tiruchirappalli, Tamil Nadu. Trained on one ride, tested on a separate ride over the same corridor.

Real differences found, each a genuine engineering challenge, not a restatement of the England result:

- **Tamil Nadu's map carries essentially no speed-limit tags** (0% of 111 blackouts start on a tagged road). The
  England-tuned gating rule ("hold on tagged fast roads") is inert here; the engine instead gates on the vehicle's
  own last-known speed, which needs no map tags at all — a genuinely different deployment rule per region.
- **Far fewer turns per kilometre** than the English routes (0.9/km on the main corridor vs. 3.5/km in town) — the
  map has fewer chances to correct position sideways. On this corridor, the map-free estimate actually scored
  better than the map-assisted one (8.7% vs. 10.1%) — sparse junctions plus parallel service roads is the map's
  worst case, in India as much as in England.
- **Speed breakers are visible at 248 Hz and invisible at 10 Hz** — 4 of 5 mapped bumps within 5 m of the route
  were detected directly in the raw stream, one peaking at 23 m/s² against a 4 m/s² background. A genuinely
  India-specific landmark opportunity, and a real point-landmark a parallel road cannot imitate.
- **Self-mapping *unofficial* bumps from repeated passes is not yet proven.** Jolts repeating between two rides
  looked like 2.7 per km until a control test (sliding one ride's detections 100–300 m along the same road) showed
  most matches were coincidence — the genuine excess rate is closer to 0.7 per km, and the strongest jolts do not
  repeat at all, because with the phone in a hand, most of what the accelerometer sees is the rider, not the road.
  Reported here honestly as an open question, not a working feature.

Despite harder conditions overall — no map tags, fewer turns, no working stop detector yet for a two-wheeler — the
learned speed model carried over directly, with the same shape of improvement seen in England, concentrated where
Indian traffic conditions are hardest for a held-speed approach: under 40 km/h, median error improved from
**27.5% to 14.7%**.
