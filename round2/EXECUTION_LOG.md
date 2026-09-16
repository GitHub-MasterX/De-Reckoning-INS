# Round 2 — execution log

Every run for round 2: what, why, how long, what came out, what went wrong. Oldest first.
Results are explained in `MAP_LANDMARK_APPROACH.md`; raw console output is in `out/`.

---

## 1 · Map download — 2026-09-15

- **What:** England OSM extract from Geofabrik into `data/osm/` (git-ignored): 1,693,829,796 bytes, data
  timestamp 2026-09-14T20:21:51Z, MD5 `948d45e796752dd0c47e65fbb229b73d` verified.
- **Why:** road geometry and landmarks for the whole dataset area. Decision: the whole England file, no cropping.
- **How:** run by hand with the progress-bar script, now `round2/get_osm_map.sh`.
- **Difficulties:** downloads started from a chat session died when the session ended; Geofabrik rebuilds
  the file daily, so a partial from an older build must not be resumed (the script compares Last-Modified);
  the URL redirects, so headers need `curl -sIL`.

## 2 · OSM reader check — 2026-09-15

- **What:** pyosmium 4.3.1 against a tiny synthetic `.pbf`.
- **Why:** before scanning 1.6 GB, confirm node locations survive when untagged nodes are filtered out
  before Python — otherwise every node would have to pass through Python.
- **Result:** locations survive; per-type filters (`enable_for`) work; `sparse_mem_array` storage is available.
- **Difficulties:** pyosmium has no `osmium.version`; read it with `importlib.metadata`.

## 3 · `analysis/osm_landmarks.py` — landmark tags along the routes

- **Why:** design-doc step 1 — which landmark types the drivers pass often enough to be worth using.
- **Run:** 91 s, peak 4.8 GB. 28 sessions, 1,162 km of track, 232,464 route points. 2,299,879 tagged objects
  reached Python; 198,339 landmarks in the dataset area; 15,649 roundabout ways merged into 4,656
  roundabouts; 4,550 passes; 0 ways with missing node locations.
- **Outputs:** `out/landmarks_along_routes.csv`, `out/osm_landmarks_run.txt`,
  `data/osm/landmarks_iovnbd.parquet`, `data/osm/landmark_passes.parquet`.
- **Result:** design doc §12.1.
- **Difficulties:** a roundabout is drawn as several ways — merged through shared nodes; a bridge or tunnel
  *crossing* the route must not count, so 60% of the structure has to run along the track; repeat passes
  separated at 200 m gaps. **Open:** D's bridge (2.11/km) and motorway-junction (0.67/km) counts look too
  high for Coventry.

## 4 · `analysis/landmark_usable.py` — which landmarks the car actually showed

- **Why:** a mapped landmark helps only if the sensors see it — a signal on green, or a roundabout driven
  straight through, gives nothing to detect.
- **Run:** not timed. Motion comes from the vehicle GPS course and speed, so this is a best case for the phone.
- **Output:** `out/landmark_usable_run.txt`; design doc §12.2.
- **Finding:** the earlier motion-signature roundabout counts were inflated — only 11–36% sit on a real roundabout.

## 5 · Audit — reading only, no runs

- `run_evaluation.py` (tag `round-1`): drift = |estimated − true distance| (line 125); at most 200 random
  blackouts per session (line 113); blackouts containing a stop are dropped (line 115).
- `analysis/eval_cache.py`: "moving" = speed above 1.4 km/h throughout each 2 s window.
- `analysis/align_frame.py` lines 48–51: the gyro yaw axis is fitted against the CAN yaw rate (IO-VNBD export quirk).
- Problem statement: the expected solution names "Unscented Kalman Filter + Hidden Markov Map Matching"
  and allows a downloaded OSM database.
- The §3 feasibility scripts had never been saved; they were recovered from the chat transcript to see how
  the ceilings and the "unambiguous" share were computed (windows every 20 s over all driving;
  competitors = bends on the driven route only).

## 6 · `analysis/osm_junctions.py` — junctions along the routes

- **Why:** the "85–95% unambiguous" claim never included side roads. Measure how many competing turn
  options a matcher really faces.
- **Run:** 107 s, peak 4.6 GB. 3,933,596 drivable ways seen, 257,567 near the routes, 1,622,779 node
  references, 221,035 junction nodes nearby, 6,569 within 10 m of a track, 8,685 passes.
- **Outputs:** `data/osm/junction_passes.parquet`, `out/osm_junctions_run.txt`; design doc §13.
- **Difficulties:** OSM ways are not split at every junction, so arms are counted from interior nodes (2 arms)
  and way ends (1 arm); only ways near a route are read node by node (map-cell prefilter); nodes of one
  physical junction merged within 25 m; turn options measured against the direction of travel 5–30 m
  before the junction.

## 7 · `analysis/snap_recheck.py` — snapping under the evaluator's rules

- **Why:** the §3.3 ceilings used different blackouts and assumed speed error resets at a snap. Test them
  properly, then with phone-detected turns, then with OSM junctions as competing candidates.
- **Runs:** twice, not timed (about 1–2 min each): first without, then with `--junctions`. The first run's
  "snap more than 25 m off" measure was replaced by right bend / wrong candidate / false detection,
  because at motorway speed a correct bend with a 1 s timing error is already 28 m off.
- **Output:** `out/snap_recheck_run.txt` (the `--junctions` run); design doc §14–§15.
- **Difficulties:** the 10 Hz replication gave E 6.5% instead of 10.2%. Traced to the evaluator sampling at
  most 200 blackouts per session — with that sampling it gives 10.9%. The matcher keeps one hypothesis
  and works in 1-D along the true route, so its realistic rows are indicative, not final.

## 8 · Separating round 1 from round 2 — 2026-09-15

- **What:** annotated tag `round-1` on commit `02f408a`; branch `round-2`; all round-2 files moved into
  `round2/`. Scripts 3, 4, 6 and 7 ran before the move (from `analysis/` or a scratch folder); only
  their file paths changed.
- **Check:** `run_evaluation.py` re-run from the tag in a throwaway checkout — exit 0, every committed
  output identical (CSVs and plots). 1 km drift E 101.8 m, B 161.1 m, D 196.0 m, A 164.9 m, as submitted.

## 9 · Step 1 — round-2 evaluator (`step1_evaluator.py`, `core/`) — 2026-09-16

- **Why:** one fixed list of blackouts and one scoring code for every later step, checked before any method uses it.
- **Run:** a few seconds (28 sessions, 1,166 km). Output `out/step1_run.txt`; list `out/blackouts.parquet`,
  4,265 start points. Rules in `DECISIONS.md`: a start every 250 m, at least 300 s of history, checkpoints
  50–1000 m, `moving` and `stopgo` sets.
- **Valid 1 km blackouts:** moving — E 2,338 (11 sessions), B 183 (3), A 515 (6), D 83 (1);
  stopgo — E 2,641 (12), B 358 (3), A 968 (6), D 185 (1).
- **Checks:**
  - *Round-1 reproduction:* round-1's own blackouts through the same formula → all 24 numbers and all blackout
    counts identical.
  - *Ground truth:* vehicle path length and speed-integrated distance agree to +0.02 … +0.10% (median per driver).
  - *Scorer self-test:* coast distance placed on the true path gives 2D ÷ distance error of 0.992–1.000.
- **Reference — coast, distance error, moving set, every / session-weighted:** 1 km E 4.8 / 7.3%, B 14.8 / 16.0%,
  A 12.3 / 12.9%, D 19.3 / 19.3%; 50 m E 1.0 / 2.0%, B 2.8 / 2.7%, A 2.8 / 3.5%, D 3.4 / 3.4%.
- **Not comparable with round 1's 10.2 / 16.1 / 16.5 / 19.6%.** The rules changed (starts spaced by distance,
  history required, weighting) — not the method. Round-2 methods are compared with the round-2 baseline only.
- **Difficulty — session weighting is unstable for E.** E's session-weighted median is 9.8% at 500 m but 7.3% at
  1 km. At 500 m, six E sessions with fewer than 20 blackouts (38 blackouts in total; one is a single blackout at
  66.7%) carry 43% of E's weight; at 1 km most of them have no valid blackout. Resolved differently — see
  entry 11: results are now reported by driving condition.

## 10 · `analysis/tunnel_lengths.py` — how long real tunnels are — 2026-09-16

- **Why:** the proposal to size blackouts by the average tunnel length needed the real lengths.
- **Run:** a few seconds, from the OSM landmark cache (dataset area only). Output `out/tunnel_lengths_run.txt`.
- **Result:** 1,185 tunnel ways → 1,009 tunnels. Median 15 m, mean 56 m, 90th percentile 90 m. 13 are at least
  500 m long, 5 at least 1 km. The longest mapped value (4.9 km) was not checked.
- **Finding:** most mapped road tunnels are short underpasses, so tunnel length was not adopted as a blackout
  length; the 1 km checkpoint is longer than almost every real tunnel in the region.

## 11 · Step 1 re-run — results by driving condition — 2026-09-16

- **Why:** decision change in `DECISIONS.md` — group blackouts by average speed (slow under 40 km/h, mixed 40–50,
  ps_60 50–70, fast 70+), every blackout equal inside a group; add real-turn context from the landmark-spacing idea.
- **Run:** 3 s. The same 4,265 start points, now with context columns. Output `out/step1_run.txt`.
- **Moving 1 km blackouts per group, A+B | D+E:** slow 172 | 98 · mixed 144 | 177 · ps_60 214 | 407 · fast 168 | 1,739.
  A and B supply 214 blackouts at 50–70 km/h from 9 sessions — enough to tune on.
- **Coast, distance error, A+B | D+E:**
  - 1 km — slow 21.0 | 25.6% · mixed 14.1 | 18.3% · ps_60 14.0 | 14.5% · fast 4.5 | 3.5%
  - 50 m — slow 12.1 | 10.9% · mixed 2.9 | 4.1% · ps_60 1.6 | 2.3% · fast 0.6 | 0.7%
- **Landmark context at 1 km, all drivers:** median real turns — slow 4, mixed 3, ps_60 2, fast 0; blackouts with
  no turn — 1 / 3 / 13 / 70%; last turn to the 1 km mark — 117 / 194 / 270 / 1,001 m.
- **Findings:**
  1. The problem statement's own condition (50–70 km/h) drifts about 14% at 1 km by coasting. Round 1's low figure
     for E came mostly from fast motorway driving, which coasts at 3.5–4.5%.
  2. Slow driving fails even the 50 m benchmark by coasting (10.9–12.1%).
  3. 87% of 50–70 km/h blackouts contain a real turn, the last a median 270 m before the 1 km mark — room for landmark
     corrections exactly where they are needed. Fast blackouts rarely have one, but coast well already.

## 12 · Step 2, first run — 10 Hz rate calibration — 2026-09-16

- **Why:** replace round 1's car-assisted gyro (axis fitted to the CAN yaw rate, bias from stops found in the true
  speed) with a calibration fitted on GNSS history before each blackout.
- **Run:** 12 s. Output `out/step2_run_v1.txt`.
- **Result:** three rate-fit variants — last 300 s; axis from all history; axis and bias from all history. Median
  heading error at 1 km, A+B | D+E: 7.8 | 9.5°, 7.9 | 8.4°, 7.4 | 7.9°. No better than round 1's reference (6.0 | 9.1°).
- **Difficulty:** its "wrong sign" column (3–26%) was wrong — sign was judged by correlation over whole blackouts,
  including straight roads where only noise is left.

## 13 · Diagnosis — where the heading error comes from — 2026-09-16

- **Scripts:** `analysis/heading_error_sources.py`, `analysis/gyro_scale.py`, `analysis/gyro_columns.py`; output in
  `out/` under the same names. Seconds each.
- **Sign is fine:** 0–0.6% wrong on blackouts with a true turn of at least 30°.
- **Timing is fine:** shifting the gyro ±2 s against the GPS does not reduce the error.
- **The phones under-report turning.** On turns of at least 60° the gyro reports 88% (A+B) and 58% (D+E) of the
  real turn, and round 1's reference does the same. Over 3, 10 and 30 s windows the share stays at 81–83% (A+B) and
  62–65% (D+E) — a constant scale, not filtering. Driver E's phone reports 49–59% in every one of its sessions.
- **Error grows with turning,** not time: A+B 2.3° (under 20° of turning in the blackout) to 18.7° (over 270°);
  D+E 4.8° to 28.5°.
- **10 Hz jitter** is 2.1 °/s (A+B) and 3.8 °/s (D+E). Fitting the axis on turning accumulated over 10 s windows
  raises the fit correlation from 0.18–0.96 to 0.89–1.00 per session.
- **E's raw gyro** has no flat, duplicated or stuck axis, but vibrates heavily: 14–29 °/s on Y, with Y and Z
  anti-correlated (−0.80 to −0.91) — a strong wobble. What causes the 55% scale is still unknown.

## 14 · Step 2, second run — window calibration — 2026-09-16

- **Why:** calibrate the scale, and fit the axis on accumulated turning instead of the jittery rate.
- **Run:** 7 s. Output `out/step2_run.txt`; `out/calibration.parquet`, `out/heading_errors.parquet`,
  `out/calibration_choice.txt`.
- **Fit:** correlation 0.997 (A+B) and 0.970 (D+E); scale median 1.05 (A+B) and 1.84 (D+E).
- **Heading error at 1 km, moving, A+B | D+E:** window 4.9 | 6.4° (90th percentile 16.2 | 17.6°); rate 7.4 | 7.9°;
  round 1's car-assisted reference 6.0 | 9.1°. At 200 m: window 2.1 | 3.1°. Wrong sign on real turns: 0.0 | 0.6%.
- **Chosen on A+B:** window (4.91° against 7.36° and 6.24°).
- **By condition, D+E at 1 km:** slow 8.9°, mixed 8.8°, 50–70 km/h 8.5°, fast 5.8° — reference 19.9 / 17.2 / 16.4 / 7.9°.
- **Result:** the honest calibration beats round 1's car-assisted gyro on both splits.
- **Still open:** 8.5° of heading error after 1 km at 50–70 km/h (driver E) would push an unmatched estimate sideways by
  tens of metres. Step 3 measures that; step 5's road matching is meant to remove it.

## 15 · Step 3 — map-free 2D dead reckoning — 2026-09-16

- **Why:** the honest 2D baseline — gyro heading plus held GNSS speed with ZUPT — that the map has to beat.
- **Run:** 13 s. 4,129 start points, 160,184 error records. Output `out/step3_run.txt`, `out/dr_errors.parquet`.
- **Classifier on honest input:** the raw gyro and round 1's truth-corrected gyro give the same result — accuracy 99.0%
  (A+B) and 99.6% (D+E), stationary recall 93%, precision 96.7% and 99.1%. Batch features identical to the contract.
- **2D position error, moving set, D+E (test) — median · share within 10%:**
  - 50 m: slow 13.0% · 40%, mixed 6.0% · 78%, **50–70 km/h 4.1% · 90%**, fast 1.9% · 100%
  - 1 km: slow 26.2% · 11%, mixed 22.9% · 18%, **50–70 km/h 19.8% · 18%**, fast 8.3% · 60%
- **A+B (tuning), 1 km:** slow 18.4%, mixed 16.8%, 50–70 km/h 14.1%, fast 7.3%.
- **Where the error comes from, 1 km, D+E:** at 50–70 km/h the engine's 19.8% splits into speed alone 14.2% and heading
  alone 8.5%. On fast motorways heading dominates (5.7% against 3.5% for speed) — driver E's vibrating phone.
- **ZUPT:** no cost on the moving set (13.8 vs 13.9% A+B, 10.3 vs 10.3% D+E); on stop-and-go it lowers A+B from 21.4% to 17.6%.
- **Per driver, 1 km, 2D | distance:** E 10.2 | 4.8%, B 15.4 | 14.8%, A 13.1 | 12.3%, D 15.2 | 19.4%. E's 2D 10.2% equals
  round 1's distance figure for E only by coincidence; they measure different things.
- **Target for the map (step 5):** 50–70 km/h at 1 km on D+E, from 19.8% to below 10%.

## 16 · Step 4 — road network from OSM — 2026-09-16

- **Why:** the network the step-5 filter drives on, checked against where the cars really drove.
- **Build run:** 126 s, peak 4.9 GB. 3,933,596 drivable ways in England, 257,567 kept near the routes. Output
  `data/osm/road_network.npz` (git-ignored, 93 MB); log `out/step4_build_run.txt`.
- **Network:** 1,315,332 nodes, 1,365,205 segments, 2,549,969 drivable directions, 29,389 km of road — 32% service roads,
  29% residential; 13% of length one-way; 206 km of roundabouts; speed limit tagged on 31%.
- **Check runs:** `--reuse`, 4 s. Output `out/step4_run.txt`, `out/roadnet_check.csv`, `out/roadnet_gaps.csv`,
  `out/roadnet_disconnected.csv`.
- **True tracks on the network** (one point per second while moving, share of distance): on a road in an allowed
  direction 99.5% (E 99.8%, B 99.6%, A 98.8%, D 97.8%), within 10 m 98.7%, median offset 2.0 m; one-way conflicts
  0.1% (D 1.0%); off the network 0.1%.
- **Roads driven:** E 44% motorway and 31% trunk; B, A and D mostly trunk, secondary, tertiary and residential.
- **Stretches of 10 s or more off an allowed road:** 0–2.6 per 100 km. The longest are one-way conflicts in central
  Coventry (D 878 m, A up to 260 m) and 440 m off the map in Bradford (E).
- **Connectivity:** 98.7% of consecutive on-road points (1 s apart, on different drivable directions) connect within
  2 s of driving + 50 m. Of the 385 that do not: 29% are drivable by a longer path under 300 m, 47% are blocked only
  by a one-way rule, 14% change level on stacked roads (half of D's, on the Coventry ring road), 6% hop to a parallel
  road within 15 m, 4% cross a link missing from the map. Median hop 6.1 m.
- **Difficulty:** the first ordering of reasons tested the one-way rule before the longer path, so it over-counted
  one-way blocks (70%); reordered.
- **Carried into step 5:** one-way strong but not absolute, short hops to nearby roads allowed, hypotheses keep their
  level on stacked roads.

## 17 · Step 5 — the particle filter — 2026-09-16

- **Why:** the correction itself: guesses of road, position and speed, weighed by how the gyro's turning matches the
  roads they drive (`core/particle.py`, `step5_particlefilter.py`).
- **Speed:** about 0.06 s per blackout with 500 guesses — 0.08 ms per simulated second.
- **First smoke test (12 blackouts, 300 guesses):** 1 km 13.1% → 3.7%, but 50 m 4.4% → 9.6%. The start was scattered by
  up to 8 m around a fix that is actually good, so the scatter dominated at short range. Tightened the start spread
  (`sigma_pos0` 8 → 5 m, `sigma_off0` 4 → 1.5 m).
- **200 blackouts, 500 guesses:** 50 m 3.0% → 7.4%, 200 m 6.9% → 5.2%, 1 km 12.5% → 6.7%; 83 of 200 blackouts came out
  worse than no map at 1 km.
- **Where it helps and hurts** (1 km, by distance since the last real turn): within 250 m of a turn 12.5% → 3.7%;
  500–750 m 15.7% → 20.6%; over 750 m 8.6% → 12.2%. With no turn to pin it down, the guess cloud smears along the road
  and loses to plain coasting.
- **Difficulty:** after resampling, the guesses are reordered, and an anchor computed from the pre-resample weights
  would have paired weights with the wrong guesses. Fixed before tuning.

## 18 · Step 6 — tuning on A and B only — 2026-09-16

- **Rule, fixed in the script before any result:** lowest median 2D error at 1 km among settings whose 50 m median is
  within 1 point of the map-free baseline; ties to the smaller share made worse.
- **First sweep, 24 settings** (speed wander, speed pull, turn and heading tolerances): every setting sat at about 7.7%
  at 50 m against the baseline's 2.5%, so **no setting cleared the guard** and the script fell through to the best 1 km
  result. Disclosed rather than accepted: the cause is structural — a fresh fix beats snapping to a road centreline.
- **Fix:** a handover distance (`dr_blend_m`) — plain dead reckoning until that far from the fix, then the map.
- **Second sweep, 16 settings:** 12 cleared the guard. Best 1 km 4.9% with 50 m back to the baseline's 2.5%. Handovers
  of 100, 200 and 300 m tied on both ruled numbers, so the choice fell to row order; the tie-break now uses the 200 m
  median (5.8% at 100 m against 6.8% at 300 m). **Disclosed: the tie-break was refined after seeing the tie**, on
  checkpoints the rule had not ruled on.
- **Third sweep, 6 settings**, after adding a handover on long straights (coast on from the last map-corrected point):
  off → 1 km 4.90%, 25% of blackouts worse than no map; 300 m → 6.21%, 13% worse; 150 m → 6.78%, 14% worse. The
  pre-stated rule optimises the median, so **off** was frozen; the trade-off is recorded in `DECISIONS.md` for a later
  round, not quietly swapped in.
- **Frozen:** `q_speed=0.4`, `sigma_turn_deg=10`, `sigma_abs_deg=15`, `dr_blend_m=100`, `straight_blend_m=0`, 500
  guesses → `out/pf_params.json`; sweep table in `out/tuning.csv`, log in `out/step6_run.txt`.

## 19 · Step 7 — the frozen filter, run once on D and E — 2026-09-16

- **Why:** the single test of the frozen settings on drivers never used for tuning. Nothing was changed afterwards.
- **Run:** 191 s. 4,262 start points — 2,842 blackouts for D+E from 17 sessions, 1,358 for A+B. Seeded on a road 100% of
  the time, one failed re-seed. Output `out/step7_run.txt`, `out/test_errors.parquet`.
- **2D error at 1 km, D+E (test), baseline → filter, with the share within the PS 10%:**
  - slow (under 40 km/h) 26.2% → **6.6%** (11% → 56%)
  - mixed (40–50) 22.9% → **9.3%** (18% → 53%)
  - **50–70 km/h, the problem statement's condition: 19.8% → 5.7%** (18% → 63%)
  - fast (70+) 8.3% → **10.0%** (60% → 50%) — the only condition where the map hurts
- **At 50 m nothing changes** (2.6% median, 90% within 5 m): below 100 m from the fix the engine reports plain dead
  reckoning by design.
- **Pooled D+E at 1 km:** 10.3% → 9.4%, pass 48% → 53%. The pool is dominated by fast motorway blackouts (1,739 of 2,421),
  so it hides the gains in every other condition.
- **Per driver at 1 km, moving:** E 10.2 → 9.5%, B 15.4 → 5.0%, A 13.1 → 5.5%, D 15.2 → 3.0%.
  Stop-and-go: E 11.1 → 10.0%, B 18.5 → 7.8%, A 17.5 → 8.9%, D 18.2 → 6.2%.
- **By distance since the last real turn (D+E):** within 250 m 17.7 → 5.0%; 250–500 m 13.8 → 8.1%; 500–750 m 11.7 → 9.5%;
  over 750 m 8.2 → 11.2%. That last group holds 1,411 of 2,421 blackouts — mostly E's motorway driving — and is where
  the map loses.
- **Harm:** 49% of D+E blackouts end worse than no map (median 15.0% against 7.4%); A+B 31%.
- **Deliberately not acted on:** the straight-road handover (`straight_blend_m=300`) targets exactly the "over 750 m
  since a turn" case, and on A+B it nearly halved the harm (13% against 25%) for a worse median (6.2% against 4.9%).
  Changing it now would be tuning on the test set. It is the first candidate for round 3, to be settled on A+B and then
  tested once more — each further test of D+E weakens what the test means.
