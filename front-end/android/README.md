# The replay app — watching the estimate drift away from the truth

An Android app that replays real GNSS blackouts from IO-VNBD with **two cursors on the map**: where the car
actually was, and where the round-2 engine thought it was.

Nothing in the app estimates anything. Every position it draws was produced offline by
`round2/step9_export_replay.py` running the frozen particle filter, and every drift figure on screen is the
measured distance between the two cursors. A clip's headline numbers match `ROUND2_REPORT.md` because they come
from the same code path — the exporter prints both side by side when it runs.

---

## What is on screen

| Element | What it is |
|---|---|
| **Green disc** | the true position, from the vehicle's own GNSS — the answer key, never an engine input |
| **Cyan arrow** | the estimate: gyro calibrated from pre-blackout GNSS history, held speed, road-constrained particle filter |
| **Red dashed trail** | the same engine *without* the map — the baseline the map has to beat |
| **Amber circle** | radius = the measured error, so it passes through the true position |
| **GNSS OK / GNSS LOST** | the lead-in has GNSS, so all three coincide; at the blackout they separate |
| **Drift readouts** | metres and % of distance driven, with and without the map, live |

The camera keeps both cursors in view and zooms out as they separate — the point is watching them come apart.

## Choosing a drive

The picker lists every bundled clip by driver. **Driver A and B are labelled "tuning"**: the filter's settings
were tuned on them. Only **D and E are "test"** — driven once with frozen settings, so only they are evidence of
how the engine behaves on driving it has never seen (`round2/DECISIONS.md`).

Each row shows the clip's own measured outcome, for example `55% → 1.8%`: what the engine would have scored
without the map, and what it scored with it.

## Building and installing

No sudo, no Android Studio. The toolchain lives under `$HOME`:

```bash
export JAVA_HOME="$HOME/tools/jdk17"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="$HOME/Android/Sdk"

cd round2/android
~/tools/gradle-8.4/bin/gradle assembleDebug --no-daemon    # APK in app/build/outputs/apk/debug/
$ANDROID_HOME/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

`./gradlew` also works, but only once it has fetched its own copy of Gradle — on a slow link its 10 s download
timeout trips before that finishes, which is why the command above uses the already-installed distribution.

The phone needs USB debugging on; check it is seen with `adb devices`. The app needs **no location permission
and no sensors** — it replays recorded data. It does need the internet, for OpenStreetMap tiles.

## Regenerating the clips

```bash
.venv/bin/python3 round2/step9_export_replay.py --per-driver 3 --hz 10
```

Writes to `round2/out/replay/` and copies into `app/src/main/assets/replay/`. Clips are chosen per driver as the
urban blackouts where the map helps most **and** the estimate still finishes inside the 10% benchmark — ranking
on improvement alone picks the blackouts with the worst baselines, which the filter also loses (A/S2 improves
119% → 44% and still ends 437 m from the car).

## Honest caveats to keep in mind when demonstrating

1. **These clips are urban.** The map is known to *hurt* on fast motorway, where 58% of the test blackouts sit
   (`ROUND2_REPORT.md` §5). A replay of one would show two cursors sitting on each other for a kilometre and then
   the map-aided one doing slightly worse.
2. **A clip is one blackout, not a median.** The headline figures in the report are medians over thousands of
   blackouts; at 1 km only about half to two-thirds of individual blackouts land inside 10%.
3. **Driver D is a single session** — the least robust row in every table.
4. **The engine is not running on the phone.** This app demonstrates what the engine produced, not an on-device
   implementation; the edge port is still open work (`PROJECT_SUMMARY.md` §10).

## Layout

| Path | What |
|---|---|
| `app/src/main/java/.../domain/engine/ReplayNavEngine.kt` | plays a clip back at its recorded rate, exposing the estimate, the truth and the map-free track |
| `app/src/main/java/.../data/model/ReplayClip.kt` | the clip format and its loader |
| `app/src/main/java/.../ui/components/MapViewContainer.kt` | the map, both cursors, the three trails |
| `app/src/main/java/.../ui/components/TelemetryOverlay.kt` | the measured readouts and playback controls |
| `app/src/main/java/.../ui/components/ClipPickerSheet.kt` | the driver and clip picker |
| `app/src/main/assets/replay/` | the exported clips and their index |
