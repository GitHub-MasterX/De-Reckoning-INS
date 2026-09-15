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
  66.7%) carry 43% of E's weight; at 1 km most of them have no valid blackout. Proposed fix, awaiting a decision:
  a session enters the session-weighted median only with at least 20 blackouts at that checkpoint.
