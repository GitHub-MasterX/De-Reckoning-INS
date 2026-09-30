# NavPulse — the Android app

Two modes: **Replay Dataset Clips** (baked recordings of real GNSS blackouts, England and Trichy) and **Live ML
Engine** (the phone's own live accelerometer, gyroscope, and GNSS, with the round-1 motion classifier running
on-device in real time).

Nothing in replay mode estimates anything live — every position it draws was produced offline by
`front-end/android/App_Export/export_replay.py` (England) and `trichy_clips.py`/`trichy_full.py` (Trichy) running
the full four-layer engine, and every drift figure on screen is the measured distance between the recorded
estimate and the recorded truth. Full mechanism: the repo-root `README.md`.

---

## What is on screen, in replay mode

| Element | What it is |
|---|---|
| **Green track** | the true position, from the vehicle's/rider's own GNSS — the answer key, never an engine input |
| **Cyan track** | the full engine's estimate: gyro-calibrated, learned speed, road-constrained particle filter, reporting layer |
| **Red dashed track** | the same engine *without* the map — the baseline the map has to beat |
| **GNSS OK / GNSS LOST** badge | live status; both tracks coincide during the lead-in, then separate at the blackout |
| **Drift readouts** | metres and % of distance driven, with and without the map, live during playback |

## Choosing a clip

The picker lists every bundled clip, split by group: **England** (IO-VNBD drivers A, B, D, E — A and B are
"tuning," settings were tuned on them; only D and E are "test," driven once with frozen settings) and **Trichy**
(the team's own Tamil Nadu recordings, 8 curated legs). Each row shows the clip's own measured drift %, colour-coded
green/amber/red against the 10% benchmark.

## Live ML Engine mode

Switches to the phone's own live sensors. The top bar shows the round-1 motion classifier's current state
(STATIONARY / MOVING) directly from on-device inference. The map centres on the phone's live GNSS position. A
re-centre control recentres both cursors without changing north-up/heading-up orientation.

## Building and installing

```bash
export JAVA_HOME="$HOME/tools/jdk17"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="$HOME/Android/Sdk"

cd front-end/android
unzip app/src/main/assets.zip -d app/src/main    # once — restores the replay clips + classifier asset
~/tools/gradle-8.4/bin/gradle assembleDebug --no-daemon
$ANDROID_HOME/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The phone needs USB debugging on (`adb devices` to confirm). Replay mode needs no location permission and no
sensors. Live mode needs sensor + location permissions, granted on first launch. Both need internet for OpenStreetMap
tiles.

## Regenerating the clips

```bash
.venv/bin/python3 front-end/android/App_Export/export_replay.py         # England
.venv/bin/python3 front-end/android/App_Export/trichy_clips.py          # Trichy
```

Writes into `App_Export/`'s own working `outputs/` area, then copies the winners into
`app/src/main/assets/England_test/`, `Trichy_test/`, and the shared `index.json` — then re-zip:
`cd app/src/main && zip -r assets.zip assets && rm -rf assets`.

## Honest caveats to keep in mind when demonstrating

1. **A clip is one blackout, not a median.** The headline figures in the reports are medians over hundreds of
   blackouts; individual clips can land anywhere within the measured spread — see `CHALLENGES.md` §7, the
   coin-flip finding.
2. **The map is known to cost more than it gives on some corridors** — the Trichy NH38 main road specifically
   (`CHALLENGES.md` §8) — sparse junctions plus parallel service roads is the map's worst case.
3. **The full four-layer engine is not running on-device in replay mode.** This app demonstrates what the engine
   produced offline; only the round-1 motion classifier runs on-device (in Live ML Engine mode).

## Layout

| Path | What |
|---|---|
| `app/src/main/java/.../domain/engine/ReplayNavEngine.kt` | plays a clip back at its recorded rate |
| `app/src/main/java/.../domain/engine/LiveNavEngine.kt` | live-sensor mode, on-device classifier |
| `app/src/main/java/.../data/model/ReplayClip.kt` | the clip format and its loader (England_test/Trichy_test split) |
| `app/src/main/java/.../ui/components/MapViewContainer.kt` | the map and its tracks |
| `app/src/main/java/.../ui/components/ClipPickerSheet.kt` | the driver/group and clip picker |
| `app/src/main/assets.zip` | the exported clips, their index, and the on-device classifier — unzip before building |
| `App_Export/` | every Python script that exports something for this app: replay clips, the classifier tree, road networks, engine test fixtures |
