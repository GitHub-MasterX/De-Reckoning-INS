# Handoff — picking the work up somewhere else (state on 17 Sep 2026)

This file holds **only what is not already written down** in the other documents. Read those first, in this order:

| Document | What it already covers |
|---|---|
| `round2/PROJECT_SUMMARY.md` | both rounds end to end, results, what is open (§10), where things live (§11) |
| `round2/EXECUTION_LOG.md` | every step with numbers. **Entries 23–30 are the phone work**: TN map (23), engine on the phone (24), 248 Hz engine (25), rides 1–3 and tuning (26–28), the three segments (29), where the error comes from (30) |
| `round2/README.md` | layout of `round2/` and how to run the Python steps and exporters |
| `round2/DECISIONS.md`, `ROUND2_REPORT.md`, `MAP_LANDMARK_APPROACH.md` | round-2 design, evaluation rules, failure analysis |
| `round2/android/README.md` | the **replay** half of the app (IO-VNBD clips) and the build commands. Its caveat 4 ("the engine is not running on the phone") is **out of date**: it is now, see below |
| `round2/phone_data/README.md` | the real rides: the three segments, their files, results per segment (git-ignored folder, local only) |

---

## 1 · Things that will be lost if you only clone the repo

`git status` on branch `round-2` shows these as **untracked**. Nothing below is on GitHub, and branch `round-2`
and tag `round-1` have **never been pushed** (remote: `github.com/GitHub-MasterX/De-Reckoning-INS`, private).

| Path | Size | What | Must copy by hand? |
|---|---|---|---|
| `round2/android/` | 5.8 MB without `build/` | **the whole Android app: the replay app plus the live 248 Hz engine, all Kotlin, all tests.** The most valuable untracked thing | **yes** |
| `round2/phone_data/` | recordings | the only real dataset (3 segments + 6 raw recordings), git-ignored because they are location traces | **yes** — cannot be re-recorded, bike access has ended |
| `data/osm/` | ~0.4 GB | England + Tamil Nadu pbf, `road_network*.npz`, landmarks; `data/osm/phone/` the phone networks and test fixtures | can be rebuilt (commands in §6), but slow |
| `round2/phone_backup/` | 16 MB | the app as it was on the phone before any change (APK) + jadx decompile | nice to have |
| `round2/step9_export_replay.py`, `round2/out/replay/`, `round2/out/step9_run.txt` | small | exporter for the replay clips (documented in `android/README.md`) and its output | yes, if the replay app is kept |
| `round2/analysis/leak_check.py`, `round2/out/leak_check_run.txt` | small | proves no ground truth after a blackout starts reaches the engine (poisons it, re-runs, bit-identical) | yes |
| `round2/SIH.zip` | 1.1 GB | an older team project snapshot (Flutter / Gradle app, `MLModel/`, `SIH PPT.pptx`, dated 1 Sep) — not used by round 2 | only if wanted |

Undecided and left to you: whether to commit `round2/android/` (source only, no `build/`) and whether to push to GitHub.
The simplest safe move before switching: `tar czf sih_untracked.tgz round2/android --exclude=build round2/phone_data
round2/phone_backup round2/step9_export_replay.py round2/analysis/leak_check.py round2/out/replay data/osm/phone`.

---

## 2 · Environment on this laptop

- Python: `.venv/` at the repo root (`.venv/bin/python3`); run scripts from the repo root.
- No sudo, no Android Studio. Toolchain under `$HOME/tools`: `jdk17`, `gradle-8.4`, `jadx`; Android SDK in `~/Android/Sdk`.

```bash
export JAVA_HOME="$HOME/tools/jdk17"; export PATH="$JAVA_HOME/bin:$PATH"; export ANDROID_HOME="$HOME/Android/Sdk"
ADB=$ANDROID_HOME/platform-tools/adb
cd round2/android
~/tools/gradle-8.4/bin/gradle assembleDebug --no-daemon                     # build
$ADB install -r app/build/outputs/apk/debug/app-debug.apk                   # install (phone on USB debugging)
~/tools/gradle-8.4/bin/gradle testDebugUnitTest --no-daemon                 # every JVM test (fixtures must exist, §6)
```

- Phone: Samsung Galaxy M17 5G (SM-M176B), Android 16, LSM6DSV accelerometer + gyroscope at ~248 Hz.
- App on the phone: **"SIH Nav Live", `com.sih2026.nav.live`, versionCode 2 / `2.0.0-live`**, installed *next to* the
  original `com.sih2026.nav` (signed differently; its source was never on this machine — hence the decompile).
  The build on the phone is the **frozen** build of entry 27.
- Phone paths:
  - recordings: `/sdcard/Android/data/com.sih2026.nav.live/files/drives/drive_yyyyMMdd_HHmmss.csv.gz`
  - road networks: `/sdcard/Android/data/com.sih2026.nav.live/files/roadnet/*.roadnet.bin` (the app picks the one
    containing the last known location or first fix)

```bash
$ADB pull /sdcard/Android/data/com.sih2026.nav.live/files/drives/ round2/phone_data/raw/        # fetch rides
$ADB push data/osm/phone/tiruchirappalli.roadnet.bin /sdcard/Android/data/com.sih2026.nav.live/files/roadnet/
$ADB logcat -b crash -d                                                                          # crash logs
```

- Recording `151440` (walking/parked) was still running on the phone when last fetched; stop it in the app
  (notification → Stop) if it still is.

---

## 3 · The Android app — how it is put together

Root package `app/src/main/java/com/sih2026/nav/`. Replay parts are described in `android/README.md`; the live parts:

**Engine, pure Kotlin, no Android imports** (`live/engine/`) — so it runs in JVM tests on recordings exactly as on the phone:

| File | Role |
|---|---|
| `Geo.kt` | local ENU / plane projection, numpy-style angle wrap, haversine |
| `MotionModel.kt` | the round-1/2 stop classifier: walks the `deploy_all` HGB trees (`assets/live/motion_deploy_all.hgb`), features bit-identical to Python (numpy pairwise summation) |
| `Calibration.kt` | gyro calibration: `engine()` = round 2's window/rate fit (Python-identical); `vertical()` = 248 Hz fit of rotation about the tracked vertical |
| `DeadReckoning.kt` | heading + speed integration (`step`, `stepSpeed`, `stepWith` for analysis) |
| `RoadNetwork.kt` | RNW1 loader, 25 m sorted-grid nearest-road lookup (equivalent to Python's KD-tree) |
| `ParticleFilter.kt` | round 2's road-constrained PF, frozen `PfParams` (n 500, q_speed 0.4, sigma_turn 10, sigma_abs 15, dr_blend 100); optional `speedChange` so particles follow the 248 Hz speed estimate |
| `ImuStream.kt` | 248 Hz events → one 10 Hz row per 100 ms with **both** the sample at the tick (round 2 path) and the time-weighted mean (248 Hz path) |
| `TiltTracker.kt` | Mahony filter tracking "up" → horizontal acceleration (q1, q2), `verticalRate`, `tiltRate` |
| `MountCalibration.kt` | vehicle forward/right in the tilt-free frame from GPS history (sideways swing vs v × turn rate) |
| `SpeedEstimator.kt` | Kalman filter on [speed, forward bias]: acceleration propagation, turn readings v = a_right / r, ZUPT at stops |
| `LiveEngineCore.kt` | orchestrator: 30-min ring buffer, 1 Hz GPS interpolation, several blackouts at once, each running **round 2 unchanged** and **the 248 Hz engine** side by side, scored against the hidden GPS; `truth` hook runs oracle variants for analysis |

**Around it:** `live/sensor/LiveSensors.kt` (SENSOR_DELAY_FASTEST accel/gyro + uncalibrated + magnetometer, GPS at 1 s);
`live/record/DriveRecorder.kt` (gzip CSV on its own thread, flush every 2 s); `live/LiveRecordingService.kt`
(foreground service of type location + partial wake lock, so recording continues with the screen off; notification
with Stop); `domain/engine/LiveNavEngine.kt` (owned by `NavApp.liveEngine`; exposes `state`, `noMapState`,
`trueState`, `fullState` flows; writes the recording header); UI: `NavViewModel` (LIVE / REPLAY mode, blackout toggle),
`MainScreen` (permissions: fine location, notifications on API 33+), `LiveTelemetryOverlay` (ROUND 2 · 10 Hz, 248 Hz
ENGINE, DISTANCE (GPS), blackout button, mount/status lines, REC line), `MapViewContainer` (purple 248 Hz cursor and
trail). Manifest adds HIGH_SAMPLING_RATE_SENSORS, FOREGROUND_SERVICE(_LOCATION), WAKE_LOCK, POST_NOTIFICATIONS, `largeHeap`.

**Recording line format** (times = ns on `elapsedRealtimeNanos`): `A`/`G` accel/gyro, `a`/`g` uncalibrated (+bias),
`M` magnetometer, `L` GPS fix (t, utc ms, lat, lon, alt, acc, speed, speed acc, bearing, bearing acc, has speed, has
bearing), `B` blackout on/off, `E` engine row at 10 Hz with 13 fields:
`t, lat, lon, nomap_lat, nomap_lon, heading°, stationary, blackout, on_map, full_lat, full_lon, full_speed_kmh, full_on_map`
(`full_*` = 248 Hz engine). `#` lines = phone, sensors, settings. GPS keeps being recorded during a blackout (answer key).

**Tests** (`app/src/test/java/com/sih2026/nav/live/engine/`), JVM `-D` properties wired in `app/build.gradle.kts`:

| Test | Checks | Needs |
|---|---|---|
| `MotionModelTest`, `CalibrationTest`, `EngineTest`, `RoadNetworkTest`, `LiveEngineCoreTest` | port == Python (entry 24's numbers) | fixtures in `data/osm/phone/` + `test/resources/motion_fixture.bin` |
| `SyntheticDriveTest` (+ `SyntheticCar`) | 248 Hz engine on simulated car / handlebar / hand-wobble rides; recorder round trip | nothing |
| `DriveReplayTest` (+ `DriveReplay`) | scores a real recording: start every 250 m after 5 min history above 15 km/h, 1 km blackouts, checkpoints 50–1000 m, speed bands; writes `data/osm/phone/replay_results.csv` | `-Ddrive=<file or folder>` |
| `DriveDiagnoseTest` | calibrations every 2 min on a recording (why the mount fit fails, etc.) | `-Ddrive=` |
| `ErrorSourcesTest` | oracle attribution (true stops / speed / heading) and the hand-shake thirds of entry 30 | `-Ddrive=` |

```bash
gradle testDebugUnitTest --tests '*ErrorSourcesTest*' -Ddrive=../phone_data/segments/3_return.csv.gz
# tuning experiments, without editing code:
-DreadingRows= -DmaxTurnSpread= -DheldSpeedSigma= -DconfirmSeconds= -DverticalMinSpeed= -DmountRecentS= -DmountMinTurns=
```

---

## 4 · The 248 Hz engine's settings — frozen after ride 1

Chosen on segment 1 (outbound) only; segment 3 (return) was the test. **Do not retune on segment 3** — it stops being a test.

| Setting | Value | Where |
|---|---|---|
| gyro fit on rotation about tracked vertical, from speed | 2.5 m/s (was 5) | `Calibration.VERTICAL_MIN_SPEED` |
| vehicle-axes fit window / turning samples needed | 600 s / 12 (was 360 / 20) | `MountCalibration.RECENT_S`, `MIN_TURN_SAMPLES` |
| vehicle-axes fit trusted when | r ≥ 0.6 and sideways scale 0.6–1.5 | `MIN_FIT_R`, `MIN_SCALE`, `MAX_SCALE` |
| TiltTracker | TAU 30 s, KP = 1/30, KI = KP²/4; steady when \|‖a‖−g\| < 0.3 and \|ω_up\| < 0.05 | `TiltTracker` |
| turn reading length / max turn-rate spread | 20 rows (2 s) / 0.30 rad/s | `SpeedEstimator.Settings` |
| report the estimate only within | 20 s of a reading (corner, stop, start); else held GPS speed | `confirmSeconds` |
| held-speed anchor | off (0) | `heldSpeedSigma` |
| stop classifier | `deploy_all`, unchanged ("don't modify the ML model") | `MotionModel` |

Tried and **rejected** (details in entries 26–27): TiltTracker TAU 3 s (leans into accelerations) and TAU 60 s without
bias learning (9° drift); 1 s and 3 s turn readings; held-speed anchor (braking simulation back to 48%); gyro fit axis
left free (×2.2 scale error; pinned to vertical instead); phone-specific stop detector from vibration bands (39% stops
found at 2.3% false stops — net zero).

---

## 5 · Where things stand, and what to do next

**Result on the only test (return, frozen), median 2D drift at 1 km with the map, round 2 → 248 Hz:**
all 24.0% → 15.8%; 50–70 km/h 18.7% → **8.7%** (under the 10% goal); under 40 km/h 58.9% → 45.1%. One ride, overlapping
blackouts — indicative, not proof. IO-VNBD round-2 results (5.7% at 50–70 km/h on D+E) are unaffected.

**Diagnosis (entry 30):** speed is the main loss (true speed takes 15.8% → 7.2%, under 40 km/h 78% → 11%); heading
second (the hand roughly doubles–triples heading error); the engine's arithmetic is fine (1.5–1.9% with both inputs
true). The accelerometer speed almost never engages, because the vehicle-axes fit is rarely trusted with a hand-held
phone (return: only minutes 26–30). Stops found: 17% / 5% / 25% per segment.

**Answers already worked out in conversation (not elsewhere):**
- *"Is it all the 10 Hz accelerometer?"* For IO-VNBD, largely yes for speed: round 1's reports show aliasing (engine and
  road vibration folding onto 0–2 Hz), and accelerometer-, turn- and map-based speed all failed on it. That is why the
  phone records at 248 Hz. But on the phone rides the loss is no longer the sample rate — it is that a hand-held phone
  gives no stable vehicle frame, so the accelerometer cannot be turned into forward acceleration reliably.
- *"Does the trained model work on the M17?"* The only trained model is the stop classifier (`deploy_all`); it runs
  unchanged on the tick samples but was trained on IO-VNBD phones in cars and finds only 5–25% of stops on a two-wheeler.
  Everything else (calibration, dead reckoning, PF) is physics fitted from each phone's own GPS history, so it carries over.
- *TN map:* junctions/connectivity as good as England's, but tagged landmarks, roundabouts and speed limits 10–100× rarer.
  The route (NH38) has 0.9 turns/km — few corners for the map or turn readings to lock onto.

**Next steps, in the order they would pay off:**
1. **Speed without a trusted mount** (offered, not started): use the recorded segments; ideas — speed readings
   from turns that don't need forward/right axes (|a_horizontal| ÷ |turn rate| in the tilt-free frame), vibration
   spectrum ↔ speed (wheel/engine frequency) learned per ride from GPS, looser mount trust with the estimate gated by
   its own sigma. Tune on segment 1, test once on segment 3.
2. **Stops for a two-wheeler** — needed in town (true stops alone: 44.7% → 12.1% at 200 m on segment 2).
3. **Heading under hand motion** — down-weight or hold turn rate when `tiltRate` is high.
4. Update `round2/android/README.md` caveat 4 and `PROJECT_SUMMARY.md` §10 item 5 (the app and on-device engine now exist).
5. Decide: commit `round2/android/` source; push `round-1` tag and `round-2` branch.

**Working rules to keep** (the user's): don't modify the ML model; round 1 frozen, everything under `round2/`;
.md not .html; ask yes/no before changing data; honest numbers, synthetic results labelled as synthetic; never commit
location recordings.
