# ML track — initial tasks

**Owner:** BHAGYA
**Goal of this phase:** answer one question — *can we predict velocity change from 10 Hz IMU accurately enough to keep position drift under 10% of distance travelled?*

Everything here builds to that number. A trained model is not the deliverable; the drift percentage is.

---

## Already done — start from these, don't redo them

Scripts in `analysis/`, outputs in `out/`:

**Read `DECISIONS.md` first.** Several plausible-sounding approaches have already been tested and ruled out with measurements. Re-deriving them costs a week.

---

## T1 — Loader + reproduce the baseline

**Why first:** proves your environment, loader and split are correct before you build anything on top.

The dataset has four traps that will each cost you half a day:

1. Files are **latin-1** encoded, not UTF-8 (`m/s²` breaks `read_csv`)
2. Column names **differ between folders** — `GYROSCOPE Yaw/Pitch/Roll` in one, `GYROSCOPE X/Y/Z` in the other
3. V- filenames are **case-mismatched** — `S-Vta2.csv` pairs with `V-vta2.csv`
4. 4 of 144 pairs have **all-zero CAN speed** (stationary tests) — filter them out
5. And any other as per your analysis
**Ground truth is `Velocity (km/hr)` from the V- file.** Not the phone's GPS — that only updates every ~9 seconds in 124 of 144 files and is useless as truth.

**Done when:** reproduced absolute-speed MAE ≈ 18.7 km/h on held-out drives. That number is *bad on purpose* — it is the thing we are replacing. If you get a much better number, you have a leak (see below).

---

## T2 — Split discipline (read before T1, applies forever)

**Split by drive, never randomly.** This is the single easiest way to produce results that look excellent and mean nothing.

Windows overlap and adjacent 2-second windows are nearly identical. A random split puts window *n* in train and window *n+1* in test — the model has effectively seen the answer. You will get a beautiful number that collapses the moment it touches real data.

- Hold out **entire drives**, never individual windows
- Hold out at least one full drive from **each driver group** (S / M / Vf / Vta / Vtb / Vw / Y) so you are testing across drivers, not just across time
- Report the dummy baseline (predict the mean) alongside every result — if your model isn't clearly beating it, it has learned nothing

Any result that isn't from a held-out-drive split does not get reported to the team.

---

## T3 — The blackout evaluator ← build this before the model

Turns model output into the number the jury cares about.

```
1. Pick a held-out drive
2. Choose a random 60 s segment where the vehicle is moving
3. Take the true velocity at t=0 (this is what GNSS would have given
   at the moment of blackout)
4. From there, use ONLY the model's predicted velocity changes to
   track velocity forward, and integrate that to position
5. Compare against the true trajectory
6. Report: final position error, and that error as a % of distance travelled
```

Run it over many segments and report the **distribution**, not one lucky run — median, 90th percentile, worst case.

**Benchmark:** under 10% of distance travelled. At 60 km/h that's under 100 m over 1 km in 60 s.

**Done when:** you can hand any model to this and get back a drift percentage with error bars. Plot at least one true-vs-estimated trajectory — that plot is going in the report.

---

## T4 — The velocity-change model

Now build the thing, with T3 telling you whether it's working.

**Target:** change in velocity over each window. **Not** absolute speed — that has already been tested and fails (MAE 18.7 km/h, barely better than guessing).

**Input:** features computed over a fixed **2.0-second window**, defined in seconds, not sample count. Per axis (3 accel + 3 gyro): mean, std, min, max, mean absolute difference, plus energy in the 0.5–1.5, 1.5–3.0 and 3.0–5.0 Hz bands. Nothing above 5 Hz — it does not exist in this data.

**Model:** start with `HistGradientBoostingRegressor`. No architecture to design, no input-shape problems, rate-agnostic for free, and hard to beat on tabular features. Only move to a 1D CNN if trees plateau — and compare honestly against T3's drift number, not against MAE.

**Things worth trying, in order:**
1. Add ZUPT — detect stationary and force velocity to exactly zero. Cheap, and it stops drift accumulating during every traffic stop.
2. Add longer context — a 4 s or 6 s window alongside the 2 s one.
3. Predict *uncertainty* as well as Δv. The Kalman filter needs to know how much to trust each prediction, and this is what the problem statement means by "AI-based fusion." Quantile regression is the simple route.

---

## T5 — Interface contract (do early, ~half a day, unblocks integration)

Write down and freeze:

- Exact input feature list, in order
- Window length and hop, in **seconds**
- Expected input rate the features are computed at (10 Hz band-limited)
- Output: what it returns, in what units, and its uncertainty
- Model file format

Integration cannot start until this exists. Do it as soon as T4's shape is settled, even before accuracy is good.

---

## Not yours (yet)

- **Resampling / interpolation** — that's the runtime engine. You only specify what the model expects; the engine's job is to deliver it.
- **Map matching, Kalman filter, NHC** — different layer.
- **TFLite export and quantisation** — after accuracy is settled. Exporting a model that doesn't work yet is wasted effort.

---

## Sequence

```
T2 (read)  →  T1 (loader + reproduce)  →  T3 (evaluator)  →  T4 (model)
                                          T5 (contract, in parallel once T4 has shape)
```

The whole phase is trying to answer one question. If T3 comes back saying the drift is 40%, that is a **useful, project-changing result** delivered early — not a failure. Report it immediately rather than tuning quietly.
