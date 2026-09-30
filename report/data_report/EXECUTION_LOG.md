# Execution log

Every script run, in order: **why** it was run, **what it resolved**, and **what it did not**.

Scripts live in `analysis/`. Numbers are as measured at the time of running; later entries
sometimes supersede earlier ones, and where that happens it is stated.

---

## Phase 1 — What is this dataset?

### `survey.py`
**Why:** the dataset paper claims 10 Hz; claims needed checking before anything was built on them.
**Resolved:** measured sample rates on all 144 pairs — phone and vehicle both exactly 0.1000 s.
Confirmed 10 Hz. Found phone GPS updates only every ~9 s in 124 of 144 files.
**Left open:** why phone GPS is so slow; whether pairs are actually time-aligned.

### `quality_check.py`
**Why:** needed to know whether the speed labels could be trusted at all.
**Resolved:** VBOX GPS and CAN speed agree at **r = 0.9993**, bias 0.26 km/h. Labels are sound.
140 of 144 pairs usable.
**Left open:** nothing on labels. Alignment still unverified.

### `spectrum_check.py`
**Why:** the project's original headline idea was reading speed off the vibration frequency.
**Resolved:** **killed that idea.** At 10 Hz the ceiling is 5 Hz, and wheel rotation crosses it
around 34 km/h. Dominant-frequency vs speed correlation: **−0.054**, i.e. nothing.
**Left open:** what *does* predict speed at 10 Hz.

---

## Phase 2 — First attempts, and the first failures

### `speed_baseline.py`
**Why:** establish whether speed is learnable from IMU features at all.
**Resolved:** absolute speed is **not** recoverable — MAE 18.7 km/h against a dummy of 26.5.
Confirmed the target must be speed *change*, not speed.
**Left open:** speed-change prediction scored **r = 0.017** — essentially zero. Unexplained at
the time.

### `alignment_check.py`
**Why:** to explain the r = 0.017.
**Resolved:** found the phone's yaw offset differs per drive (2° to 352°), so features in phone
frame mean different things in different files.
**Left open:** even at the best rotation, correlation with true longitudinal acceleration was
only 0.15–0.43. Not yet understood.

### `sync_check.py`
**Why:** to test whether phone and vehicle files describe the same moments.
**Resolved:** **they often do not.** Offsets of 1.3 s, 4.7 s, and some pairs with no agreement
at all. This explained the r = 0.017 — sensor readings paired with the wrong moment's answer.
**Left open:** used only the single best gyro axis, which cannot distinguish a *tilted phone*
from a *desynchronised file*.

### `sync_v2.py`
**Why:** fix the single-axis flaw above.
**Resolved:** fitting all three gyro axes jointly rescued drives that looked dead —
**`S2` went from 0.005 to 0.929.** Orientation had been masquerading as desync.
**Left open:** most of driver E still scored 0.4–0.6.

### `speed_synced.py`
**Why:** retrain on sync-verified data only.
**Resolved:** speed-change correlation went **0.017 → 0.455**. Alignment was confirmed as the
single largest factor in the dataset.
**Difficulty introduced:** first version contained a bug — the lag search initialised its best
score to **−9**, which no correlation can exceed, so the filter silently passed everything and
screened nothing. Results from that run were void.

### `blackout_eval.py`
**Why:** convert model accuracy into the number that matters — position drift.
**Resolved:** nothing usable.
**Difficulty introduced:** **the 4× overcount.** Each prediction covered 2.0 s while the
simulation stepped 0.5 s, so overlapping windows were summed and velocity accumulated four
times too fast. Reported 67.6% drift. **That number was meaningless** and was retracted.

---

## Phase 3 — Rebuilding the data properly

### `clean_dataset.py`
**Why:** four traps were making the dataset hard to load correctly — latin-1 encoding, two
column-naming schemes, case-mismatched filenames (40 of 72 pairs), unequal row counts.
**Resolved:** one canonical parquet per drive, uniform columns, SI units. 298 rows lost to
pair truncation (0.03%).
**Difficulty introduced then reversed:** first version discarded 17 short or stationary drives.
That was wrong — the stationary drives are the best available data for measuring sensor bias.
All 72 are now kept and flagged instead.

### `audit.py`
**Why:** check the cleaned data for anything still broken.
**Resolved:** found time discontinuities in 7 drives, stuck sensor values in `Vtb1`, gyro bias,
GPS glitches. Also established that `|accel|` reading 10.10 instead of 9.81 is **correct** —
the magnitude of a noisy vector is biased upward — so nobody "fixes" it later.
**Difficulty introduced:** counted 17 drives with ground-truth glitches without requiring the
vehicle to be *moving*. Most were stationary vehicles, which is correct behaviour. The real
count is 4.

### `gap_dist.py`
**Why:** to choose a session-break threshold with evidence rather than by guess.
**Resolved:** the distribution is sharply bimodal — only 3 intervals out of 1,070,673 exceed
150 ms (1.28 s, 1.37 s, 661 s), and nothing at all falls between 0.12 s and 1.28 s. Any
threshold in that empty band gives identical results, so 0.5 s was taken from it.
**Left open:** nothing. This one is settled.

### `enrich_dataset.py`
**Why:** add the derived quantities the modelling would need, without touching originals.
**Resolved:** `session`, `speed_best` (falls back to CAN during GNSS dropouts, offset-corrected
so the splice injects no false acceleration), bias-removed gyro, `stationary`, `stuck`.
**Difficulty introduced:** gyro bias first estimated with the **mean**, giving 0.0047 rad/s —
about 10× too high, skewed by the phone being handled. Median gives 0.0005 rad/s.

### `per_session.py`
**Why:** everything was being computed per *file*, but a file can contain several unrelated
recordings.
**Resolved:** large gains. **`M` went from 0.811 to 0.932 / 0.993 / 0.984** across its three
sessions, each with a different lag (+0.8 s, +2.0 s, +3.2 s) — averaging them had destroyed all
three. `S4` needs +1.8 s on one session and +313.8 s on another, in the same file.
**Left open:** `Y1` and `S4/s1` still scored ~0.06 and looked dead.

---

## Phase 4 — Why were some sessions dead?

Four hypotheses, tested in order. Three were wrong.

### `why_flat.py`
**Why:** understand the near-zero speed-change correlation.
**Resolved:** confirmed the per-drive yaw offset spread (2°–352°).
**Left open:** even at the best angle, correlation stayed at 0.04–0.43.

### `drift_check.py`
**Hypothesis:** the phone's and the VBOX's clocks run at different rates, so no single shift
can work — `L(t) = L₀ + εt`.
**Result: ✗ rejected.** The phone's true sample interval is 0.10000 s, ε ≈ 0 ppm. **The lag is
constant within a session**, so a single per-session shift is the complete correction.

### `mount_stability.py`
**Hypothesis:** the phone shifted in its holder mid-drive, so one rotation cannot fit.
**Result: ✗ rejected.** `S3c` swings **28.9°** and still scores 0.95, while `Vw4` swings only
10.4° and scores 0.57. Orientation stability does not explain it.

### `device_check.py`
**Hypothesis:** the dataset used three different phones; driver E had a worse one.
**Result: ✗ rejected.** Driver E's gyro is *quieter* than driver A's (0.029 vs 0.046) and the
ADC quantisation step is identical (0.0001) — same chip family.

### `final_verdicts.py`
**Why:** two remaining ideas — verify low-turn drives using braking instead of turning, and
check whether the dead sessions were mispaired files.
**Resolved (partly):** the accelerometer-based sync test **largely failed** — only 2 of 18
sessions reached r ≥ 0.7. Phone longitudinal acceleration is contaminated by pitch and gravity,
making it a much weaker alignment signal than rotation. One useful result: on `Vfa02` it put the
lag at +8.8 s against the gyro's +8.5 s, and two independent methods agreeing is stronger
evidence than either correlation alone.
**Also found:** dead sessions sit 648 m and 1,846 m from the vehicle's GPS track, against 24 m
for a healthy control.
**Difficulty introduced:** that was first read as "different journeys, mispaired files." Wrong.

### `gps_align.py`
**Why:** 648 m at 30 km/h is about 110 seconds of driving — which suggested the offset was
simply **larger than the ±30 s being searched**.
**Resolved: the largest error in the analysis, corrected.** Searching ±10 minutes:

| Session | Offset | Separation | `sync_r` |
|---|---|---|---|
| `Y1/s3` | **+111 s** | 648 m → **16 m** | 0.058 → **0.798** |
| `S4/s1` | **+309 s** | 1,846 m → **18 m** | 0.059 → **0.928** |

Nothing was broken. **6.0 hours recovered, including the intended test set.**

---

## Phase 5 — Applying it

### `align_all.py`
**Why:** run the two-stage alignment across all 83 sessions.
**Resolved:** usable material at r ≥ 0.7 went from 10.1 h to **13.5 h**; at r ≥ 0.5, 13.2 h to
16.6 h. Neither stage alone is sufficient — the gyro test cannot see a 309 s offset, and GPS
cannot resolve below ~5 s because phone GPS only updates every 9 s.
**Left open:** driver E still correlates ~0.5 for reasons never identified.

### `add_alignment.py`
**Why:** apply the lags without destroying the originals.
**Resolved:** added `veh_idx` (which vehicle row each phone row corresponds to),
`aligned_valid`, `speed_best_al`, `lag_applied_s`. **98.6% of rows aligned**; 1.4% lost at
session edges. Every original column byte-identical.

### `evaluate.py`
**Why:** re-run with the 4× bug fixed, and finally measure against sensible baselines.
**Resolved — the most important result so far:**

| Strategy | Driver B | Driver D |
|---|---|---|
| Coast — hold GNSS velocity, **no model** | **14.1%** | **17.0%** |
| Dummy — add the training mean | 14.1% | 17.0% |
| Trained model | **24.3%** | 23.3% |
| Oracle — the true speed changes | **1.3%** | 1.6% |

The oracle at 1.3% **proves the evaluator is now correct**. And the trained model is **worse
than doing nothing** — its errors are biased, and a small consistent lean compounds over 120
steps. Coasting has no lean by construction.
**Consequence:** the real target is 14.1% → under 10%, and every future model reports against
coast. No model that cannot beat 14.1% ships.

### `align_frame.py`
**Why:** step 1 of the plan — rotate every drive into the vehicle's frame so "forward" means
the same thing everywhere.
**Difficulty found first:** an initial version graded against the vehicle row at the *same
index* instead of the lag-corrected `veh_idx`, and made everything look worse.
**Second difficulty found — a genuine dataset quirk:** the accelerometer and gyroscope columns
use **different axis conventions**. Gravity sits on accel Z, so rotation about the vertical
should appear on gyro Z — it appears on gyro **Y** (0.948, 0.995, 0.958 across three drives,
against −0.36 for gyro Z). Projecting gyro onto the accel-derived "down" gives −0.34 instead of
+0.95. This is an AndroSensor export artifact; a real Android app does not have it, because
`TYPE_GYROSCOPE` and `TYPE_ACCELEROMETER` share the device frame.

**Resolved, on 9 well-synced sessions (11.1 h):**

| Quantity | Achieved | Theoretical ceiling | Efficiency |
|---|---|---|---|
| Yaw rate | **0.958** | 0.958 | **100%** |
| Forward accel | 0.269 | 0.315 | **97%** |
| Lateral accel | 0.381 | 0.400 | **95%** |

The estimator lands within 3–5% of the best any rotation could achieve. Alignment is done.

**What it did NOT resolve — and this is the real obstacle:**
the *ceiling itself* for forward acceleration is only **0.32**, and on `S3c` just **0.05**.
Phone accelerometer noise at 10 Hz is ~1.25 m/s² per axis while real driving acceleration is
0.5–1 m/s² — the signal sits under the vibration. **Rotation is measured almost perfectly;
forward acceleration barely at all.** Speed, not heading, is the problem.

New columns: `acc_fwd`, `acc_lat`, `acc_down`, `rate_roll`, `rate_pitch`, `rate_yaw`.

---

## Phase 6 — The plan, step by step

### `physics_baseline.py` — STEP 2
**Why:** before adding any ML, find out what pure physics achieves. Integrate the aligned
forward acceleration from the GNSS velocity at blackout and measure the drift.

**Result — physics does not beat doing nothing:**

| Strategy | Driver B | Driver D |
|---|---|---|
| **COAST** — hold v0, integrate nothing | **14.7%** | **16.1%** |
| raw `acc_fwd` integrated | 29.8% | 19.6% |
| `acc_fwd` − stationary bias | **127.6%** | 19.3% |
| `acc_fwd` high-passed (grade removed) | 18.7% | 18.2% |
| `acc_fwd` high-passed + scale calibrated | 15.2% | 16.0% |
| **ORACLE** — true speed changes | **0.2%** | **0.3%** |

**What it resolved:** the question "can integrating the accelerometer help?" is answered —
**no.** The best variant lands at 15.2% and 16.0% against coast's 14.7% and 16.1%. Dead even
at best, worse everywhere else. Oracle at 0.2% confirms the evaluator is honest.

**Why, and it is not fixable by tuning.** The fitted scale factors are the tell: **0.179,
0.260, 0.417, and −0.034**. If `acc_fwd` measured true forward acceleration, the optimal scale
would be ≈1.0. A least-squares fit shrinking it to a fifth means it is mostly noise — and on
`Y1` the fit returns −0.03, i.e. "ignore this signal entirely." This matches the alignment
ceiling of 0.32 exactly.

**One instructive failure:** subtracting the stationary bias made things **eight times worse**
(127.6%). The accelerometer's bias while parked (+0.21 to +0.67 m/s²) is not its bias while
driving — vibration rectification and imperfect levelling of the forward axis change it. A
correction measured at rest must not be applied naively in motion.

**What it did NOT resolve:** where speed can come from at all. Longitudinal acceleration is
ruled out. Remaining candidates: lateral acceleration during turns (larger signal, 2–4 m/s²
against 0.5–1 m/s² for straight-line acceleration, so much better signal-to-noise), and ZUPT.

### `full_eval.py` — every strategy, one protocol
**Why:** try everything available and get a single comparable deviation figure.
**Result — nothing beats coasting:**

| Strategy | Median drift | vs coast |
|---|---|---|
| **coast** — hold v0, integrate nothing | **14.7%** | — |
| model (ML speed change) | 20.8% | −6.2 |
| fused (model + turn correction) | 24.1% | −9.4 |
| fused + ZUPT | 24.9% | −10.3 |
| turn-based `v = a_lat/ω` | 26.0% | −11.4 |
| model + online bias calibration | 26.2% | −11.6 |
| physics (integrate `acc_fwd`) | 26.8% | −12.2 |
| physics + bias calibration | 35.4% | −20.7 |
| **oracle** — true speed changes | **1.3%** | +13.4 |

**What failed and why:**
- **Online bias calibration made things worse** (26.2% vs 20.8%). Bias measured over the 60 s
  before a blackout does not hold *during* it — the bias is driving-condition dependent, not a
  slowly-varying offset you can measure and hold.
- **Turn-based speed is too noisy**: `r = 0.289`, MAE **14.8 km/h** over 8,784 cornering
  samples. A ratio estimator divides by yaw rate, which amplifies noise, and road banking adds
  a systematic error.
- **ZUPT changed nothing** — a 60 s blackout at speed contains no stops to anchor to.

### `shrink.py` — is there a bias/variance optimum?
**Why:** the model has real signal (r 0.43–0.61) but too much bias; coast has no signal and no
bias. Sweep `v = v0 + α·Σ(predictions)`.
**Result: the optimum is α = 0.** Drift rises monotonically with α — 14.8%, 15.3%, 15.8%, 16.2%
… 20.9%. The best use of every prediction we can generate is **to ignore it**.

### `duration_sweep.py` — where is the 10% line?
**Why:** the problem statement gives two benchmarks and they are not equally hard.

| Blackout | Distance | Coast drift | Metres | Passes 10%? |
|---|---|---|---|---|
| 3 s | 34 m | 2.9% | **1.0 m** | **YES** |
| 5 s | 57 m | 4.7% | **2.6 m** | **YES** |
| 10 s | 117 m | 6.7% | 7.7 m | **YES** |
| 20 s | 234 m | 10.0% | 22.8 m | borderline |
| 60 s | 706 m | 14.5% | 97.2 m | no |
| 90 s | 1050 m | 14.5% | **149.9 m** | no |

**This is the most useful result of the whole analysis.** The PS's short benchmark — *5 m over
50 m* — is already met by **coasting alone, with no AI at all** (2.6 m over 57 m). The long
benchmark — *100 m over 1 km* — is missed: 150 m against 100 m allowed, so roughly a **33%
improvement** is needed, not a rebuild.

## Phase 7 — The breakthrough: speed without the accelerometer

### `turn_physics.py`
**Why:** every method so far integrated longitudinal acceleration, and all of them inherit the
same wall — hitting the benchmark that way requires knowing the phone's pitch relative to true
horizontal to **0.16°**, continuously, through brake dive and road grade. Two estimators avoid
integration entirely.

**A) Lateral regression.** `a_lat = v·ω + b` fitted over a window: the **slope is the speed**
and the **intercept absorbs the bias**. Gravity leak, sensor offset and road banking all land
in `b`, leaving the speed estimate immune to them.

**B) Map curvature.** `ω = v·κ` → `v = ω/κ`. The gyroscope supplies `ω` at r = 0.96; the map
supplies `κ` with no sensor error at all. **The accelerometer is not used.**

| Estimator | r | MAE |
|---|---|---|
| pointwise `a_lat/ω` (the earlier, wrong form) | 0.032 | 15.8 km/h |
| A) lateral regression | 0.438 | 12.4 km/h |
| **B) map curvature** | **0.824** | **4.8 km/h** |

Regression beats pointwise division by **13×** in correlation, confirming that the bias
absorption works exactly as the algebra predicts. But map curvature beats everything, and does
so consistently — every session lands between **0.804 and 0.893**.

**Difficulty found and fixed mid-run:** the first version read vehicle positions at phone-row
indices instead of through `veh_idx`. Sessions with large lag corrections (`S4/s1` +313.8 s,
`Y1/s3` +115.6 s) produced negative correlations. With the lag applied, they match every other
session. Same class of mistake as the ±30 s search window — trusting an index instead of the
correction that was already measured.

### `curvature_dr.py` — dead reckoning with curvature-corrected speed
**Why:** turn the estimator into a full blackout result.

| Blackout | Coast | **With curvature correction** | Passes 10%? |
|---|---|---|---|
| 10 s | 6.8% | **6.8%** | **YES** |
| 20 s | 10.2% | **8.8%** | **YES** |
| 30 s | 12.4% | **9.8%** | **YES** |
| 60 s | 14.7% | **10.0%** | at the line |
| 90 s | 15.1% | **11.4%** | no |

**Result: 14.7% → 10.0% at 60 s, and everything up to 30 s now passes.** The best correction
gain is low (0.05) — the measurement is trusted gently rather than taken whole.

**What this did NOT resolve:**
- Curvature here is derived from the vehicle's own GPS track. **Real OSM centrelines are
  coarser polylines** and will give a noisier `κ`. This must be re-validated against actual OSM
  geometry before the number can be claimed.
- Only **18–28%** of samples are usable — the method needs the road to bend. A long straight
  tunnel supplies nothing, and that is the literal benchmark scenario.
- `M/s0` got **worse** with correction (16.0% → 19.3% at gain 0.2). Gain tuning is not yet
  robust across sessions.

### `closed_loop.py` — the honest test of the curvature method
**Why:** the earlier curvature results indexed the map by **time**, which means they read
curvature at the vehicle's *true* position. During a blackout that position is the unknown
being solved for, so those results were circular and invalid.

The honest form stores curvature against distance along the road — `κ(s)`, exactly what OSM
supplies — and looks it up at the engine's **own** estimate of how far it has travelled.

| Blackout | Coast | **Honest** | Invalid (true position) |
|---|---|---|---|
| 10 s | 7.0% | 7.5% | 7.3% |
| 30 s | 11.6% | 12.2% | 9.3% |
| **60 s** | **14.8%** | **18.6%** | 10.3% |
| 90 s | 15.5% | **22.1%** | 10.9% |

**Result: it diverges.** Position error → wrong curvature → wrong speed → larger position
error. It does not bootstrap. At 60 s the honest loop gives **186.8 m over 1002 m** against a
100 m budget, and is worse than doing nothing.

The gap between the two right-hand columns (18.6% vs 10.3%) is exactly the value of already
knowing where you are — which is the whole problem.

**Every curvature result reported before this is retracted.** `v = ω/κ` remains sound physics
(r = 0.824, MAE 4.8 km/h as a *measurement*), but it cannot be used without a position fix that
a blacked-out phone does not have.

**Legitimate best remains coast: 14.8% at 60 s.**
