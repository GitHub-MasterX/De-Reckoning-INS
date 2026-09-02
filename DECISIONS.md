# Dead Reckoning Decisions — SIH 26168 (ISRO)

Everything settled so far. Immediate target is the **college internal hackathon**; SIH finale deferred.

- **Dataset:** IO-VNBD, 564 CSV, 2.06 GB
- **Device:** Samsung M17 5G
- **Updated:** 2026-08-28

Status markers: **[AGREED]** settled, build on it · **[REVISED]** changed after measurement · **[OPEN]** unresolved.

---

## Scope & strategy

- **[AGREED] Target is the college internal hackathon, not the SIH finale.** Deliverable is a working prototype. Live vehicle demo, tunnel footage, judge-in-car are parked.
- **[AGREED] No vehicle data collection needed yet.** IO-VNBD alone is enough to train and demonstrate. Removes cars, mounts and logging runs from the critical path.
- **[AGREED] Completing the statement as asked beats chasing novelty.** Novelty is framed as edge-case handling on top of a system that already meets spec.
- **[AGREED] Build for 10 Hz now.** The 5–124 Hz band the M17 captures has no labels to train against. Costs nothing to keep recording; usable the day we have our own labelled drives.
- **[AGREED] The Samsung M17 5G is the right build device.** Real ST LSM6DSV IMU, real gyro, magnetometer, multi-constellation GNSS. Compatible with IO-VNBD once its stream is resampled.

## The dataset

All figures measured from the CSVs directly, not taken from the paper.

- **[AGREED] Everything in IO-VNBD is 10 Hz.** Phone IMU and vehicle ECU both.
  - *Measured, 144 pairs:* phone dt = 0.100 s (144/144) · VBOX dt = 0.100 s (144/144)
- **[AGREED] Ground truth comes from the V- files, never the phone's own GPS.** Phone GPS updates roughly every nine seconds — at 60 km/h that is 150 m of unobserved motion between fixes. VBOX GPS runs at full 10 Hz.
  - *Measured:* phone GPS 9.0 s cadence in 124/144 files · VBOX GPS 0.1 s in 142/144
- **[AGREED] Odometry is the teacher, never the student.** Wheel speeds and CAN vehicle speed must never appear in the runtime input — the PS forbids OBD-II. They are the supervision **labels**, which the PS explicitly licenses ("models trained on vehicle kinematics"). Train on them; never ship them.
- **[AGREED] The labels are trustworthy.** CAN indicated speed and VBOX GPS velocity agree almost exactly, so neither is silently broken.
  - *Measured:* r = 0.9993 · bias = +0.26 km/h · 140/144 pairs usable
- **[AGREED] 144 synchronised phone/vehicle pairs, row-for-row aligned.** Direct join, no interpolation. The single most valuable asset — it is what makes supervised velocity learning possible at all.
- **[AGREED] Column headers differ between the two folders.** `GYROSCOPE Yaw/Pitch/Roll` in one, `GYROSCOPE X/Y/Z` in the other. Files are latin-1 encoded; V- filenames differ in case. The loader must handle all three or it silently drops half the dataset.
- **[AGREED] IO-VNBD's phone was mounted flat.** Convenient — matches our planned mounting. But it will not stress-test the alignment engine, so alignment must be validated separately.
  - *Measured:* accel Z mean = 9.85 m/s² · gravity ≈ [0, 0, 9.81]

## Sampling & rate

- **[REVISED] Reading speed off the vibration frequency does not work at 10 Hz.** This was the headline plan. At 10 Hz the ceiling is 5 Hz, and wheel rotation crosses that around 34 km/h — so 30 km/h and 40 km/h produce nearly identical readings.
  - *Measured:* dominant-frequency vs speed r = −0.054 (i.e. nothing)
- **[AGREED] Windows are defined in seconds, never in samples.** Two seconds is two seconds — 20 samples at 10 Hz, 496 at 248 Hz, same event. Taking a fixed sample *count* from a faster stream silently changes what the window means. Defining windows in time removes the problem completely.
- **[AGREED] Downsampled 248 Hz is cleaner than native 10 Hz.** Each output sample is built from ~25 real measurements, so random noise partly cancels — roughly 5×. We are not degrading the phone; we are feeding the model better data than the dataset was recorded with. Bias does not average away — that stays the filter's job.
- **[AGREED] Low-pass at 4 Hz before decimating.** 5 Hz is the physical ceiling for 10 Hz output. 4 Hz leaves room for the filter's transition band, so nothing above 5 Hz survives to fold back down as a fake slow signal.
- **[AGREED] Drive resampling from timestamps, not from counting samples.** 248/10 = 24.8. Taking every 25th sample accrues 0.8% timing error permanently — 8 m per km. Interpolating at true 0.1 s boundaries from Android's nanosecond timestamps removes rate error and jitter together.
- **[AGREED] Linear interpolation is sufficient.** After the 4 Hz low-pass the signal is essentially straight between adjacent 248 Hz samples. Error ~0.1%, far below sensor noise. Splines buy nothing measurable.
- **[AGREED] Features over the full window, not a resampled raw sequence.** Mean, std, integral and band energy over a fixed two seconds are physical quantities — same number from 20 or 496 samples, just measured more precisely. Rate-agnostic by construction, uses every sample, and preserves short events resampling would delete (the mean washes out a bump; max and std do not).
- **[AGREED] Band-limit features to match training.** Training features come from 10 Hz data, which cannot contain sharp spikes. Computing `max` from the full 248 Hz stream at inference would produce values the model never saw. Low-pass first, even on the features path. High-frequency features are a separate set for later.

## Estimation engine

    any IMU → normalise rate/axes/units → 2 s window → features → model
            → Δvelocity → Kalman filter → map layer → position @ 10 Hz

- **[AGREED] A Kalman filter is the skeleton; ML supplies what it cannot compute.** The filter holds the estimate and tracks its own uncertainty. The model provides a velocity measurement and an honest per-moment trust level — that trust level is exactly what the PS means by "AI-based fusion."
- **[AGREED] Seamless GNSS handover is free.** The filter blends by relative uncertainty rather than replacing its estimate, so the icon slides to the corrected position instead of jumping. A required deliverable falls out of using the right tool — no special transition code.
- **[REVISED] The target is speed *change*, not absolute speed.** Absolute speed is not recoverable from 10 Hz IMU with simple features. The design never needed it: GNSS supplies velocity at the moment of blackout; the model only tracks how it changes from there.
  - *Measured, held-out drives:* absolute speed MAE 18.7 km/h (dummy baseline 26.5) — unusable
- **[REVISED] The turn trick is an auxiliary constraint, not a speed estimator.** speed = lateral force ÷ turn rate is real physics and needs no high sample rate — but it fires only during turns (~12% of a drive), and phone-grade sensors degrade it badly. Useful for bounding drift at corners; not a primary speed source.
  - *Measured:* perfect CAN sensors r = +0.83, MAE 3.9 km/h · phone sensors r = +0.41, MAE 14.2 km/h
- **[AGREED] Hard-code the laws, learn the patterns.** Code what is always true: NHC (no sideways/vertical motion), ZUPT (stationary = exactly zero, and a free bias re-measurement), gravity = 9.81. Learn what is empirical: pothole vs turn vs mount slip, and how much to trust each measurement. Never hard-code threshold lists — they break on the first different car.
- **[AGREED] The model need not run at 10 Hz.** The PS asks for 10 Hz *position output*, which the filter's predict step provides. The model can supply velocity measurements at 2 Hz and the filter fills in between. A heavier, more accurate model running less often is usually the right trade on a phone battery.
- **[AGREED] One input normaliser satisfies the "any IMU" requirement.** It absorbs the four things that vary between sensors — sample rate, axis convention, units, missing sensors — and emits one canonical stream. Everything downstream is identical whether the source is a phone, a FOG unit, or a Raspberry Pi. About a day of work.

## Map layer

- **[AGREED] The map feeds forward, not just backward.** Beyond snapping a drifted path onto a road, the map supplies expectations: if no junction exists within the current uncertainty ellipse, a yaw excursion *cannot* be a turn — it is a lane change or a mount slip. Ambiguity eliminated before the filter sees it. Above spec, and this is the edge-case novelty to claim.
- **[REVISED] The map fixes cross-track error only. It does nothing for along-track.** Map matching pins you laterally onto the road; it says nothing about how far *along* it you are — and along-track error is exactly what the 10% benchmark measures. In a straight 1 km tunnel, the literal benchmark scenario, the map contributes almost nothing: correctly on the road, possibly 200 m from where you think.
  - **Consequence: the velocity estimate carries the benchmark. Map work must not crowd out velocity work.**
- **[AGREED] Guard against circularity.** The prior depends on where you think you are; if position is wrong the map confidently reinforces the error. Apply only at high map-matching confidence, weight by positional uncertainty, never let the map be the sole heading source. OSM centrelines are coarse — spline-fit before differentiating for curvature.
- **[REVISED] The edge case is unmapped roads, not off-roading.** Roads that physically exist but are absent from OSM — village roads, new construction, private roads — are common in India and directly on-theme. Also the easier problem: the vehicle behaves normally, so every kinematic constraint still holds. Only the map is wrong.
- **[AGREED] Detect it as an HMM state, not a distance threshold.** A fixed "if error > x" threshold fails both ways, because at any single instant drift and genuine departure look identical. What separates them is persistence and heading agreement over a window. Adding "unmapped road" as a candidate state with low transition probability makes it fall out of the same machinery that picks road segments — self-calibrating, and a better answer when a judge asks how the threshold was chosen.

## Mounting & vehicle physics

- **[AGREED] Flat in the console holder. Not the passenger seat.** Console is rigid, low in the vehicle, and matches IO-VNBD's mounting. A phone loose on a seat is not rigidly coupled to the car — it slides, and sliding is motion the phone measures that the car never made. It also prevents the alignment engine from ever converging.
- **[AGREED] Stated assumption: phone and vehicle are one rigid body.** Legitimate to declare rather than solve. Put it on the assumptions slide.
- **[REVISED] Flat mounting does not solve road grade or brake dive.** Those tilt the entire car and the phone tilts with it. Flat mounting removes the *static* mounting tilt — one unknown fewer — but dynamic pitch remains, so live pitch estimation is still load-bearing. On a 5% slope gravity leaks ~0.5 m/s² into the forward axis, indistinguishable from real acceleration. Bigger threat than potholes.
- **[REVISED] Vibration is the accelerometer's job; the gyroscope measures rotation.** A pothole gives a sharp vertical *acceleration* spike — the main signature — and the gyro sees the body rocking afterward. Both register it; they register different halves.
- **[REVISED] Noise floor is the limit, not sensitivity.** Both sensors resolve far finer than needed. Lane changes (0.5–1.5 m/s²), turns (2–4 m/s²) and potholes (5–20 m/s²) all clear the noise comfortably. Detection was never the problem — interpretation is.
- **[AGREED] Engine vibration is invisible at 10 Hz, and that's fine.** Runs at 27–100 Hz depending on revs, is oscillatory, averages to ~zero when integrated, so it does not cause drift. Its one real use: engine running + vehicle not moving = apply ZUPT.
- **[AGREED] Gyro for heading; magnetometer only for initialisation and slow correction. Clamp mount, not magnetic.** A car is a steel box full of speakers, motors and wiring — magnetometer heading inside one is off by tens of degrees and varies with cabin position. Magnetic phone mounts are the worst single offender and trivially avoidable. A ₹200 decision removes an entire error source.
- **[AGREED] Mount compliance matters; lane reflectors are a bonus cue.** A rubbery holder resonates around 10–30 Hz and filters what reaches the phone — two phones in different mounts in the same car see measurably different signals. Rigid is better. Separately: you only strike lane reflectors when crossing a lane, which is a lane-change signal fully independent of the gyro. Visible at 248 Hz, invisible at 10 Hz — a later-model asset.

## Still open

- **[OPEN] The speed-change test has not been run.** This is the number that decides whether the approach clears the 10% drift benchmark. Absolute speed already failed; whether Δvelocity succeeds is the open question, and everything downstream depends on the answer.
- **[OPEN] Pros and cons of the resampling approach.** Requested, not yet held.
- **[OPEN] Redmi Note 8 Pro gyroscope unverified.** Needs an AIDA64 check to confirm real hardware rather than a synthesised sensor — the Oppo A59 5G already failed this with an `oem-pseudo-gyro`.
- **[OPEN] No model has been trained yet.** Everything so far is dataset characterisation and baselines. First real model, first trajectory plot, and first drift number are all still ahead.

---

## Environment

- IO-VNBD cloned with Git LFS (`~/.local/bin/git-lfs`, installed without sudo)
- Python 3.12 virtualenv at `.venv` — numpy, pandas, scipy, matplotlib, scikit-learn
- Analysis scripts in `analysis/`, survey outputs in `out/`
- System Python is 3.14, which has no PyTorch wheels — hence the 3.12 environment
