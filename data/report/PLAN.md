# Driver groups — status and decided tasks

After two-stage alignment (GPS coarse → gyro fine) across all 83 sessions.
**29.7 h total. 13.5 h verified, 13.5 h usable-noisy, 2.7 h marginal.**

---

## Summary

| Driver | Drives | Sessions | Total | Verified | Noisy | Lag range | **Role** |
|---|---|---|---|---|---|---|---|
| **A** | 6 (`S1` `S2` `S3a` `S3b` `S3c` `S4`) | 10 | 8.6 h / 275 km | **8.5 h** | 0 | −6.8 s → +313.8 s | **Primary training** |
| **B** | 1 (`M`) | 3 | 2.9 h / 105 km | **2.9 h** | 0 | +0.8 s → +3.2 s | **Test — headline number** |
| **D** | 1 (`Y1`) | 4 | 2.0 h / 59 km | **1.9 h** | 0 | +0.0 s → +115.6 s | **Test — second holdout** |
| **E** | 64 (`Vfa*` `Vta*` `Vtb*` `Vw*`) | 66 | 16.3 h / 902 km | 0.2 h | **13.5 h** | −60.4 s → +564.0 s | **Bulk training + stress** |

---

## Driver A — primary training data

**8.5 of 8.6 hours verified.** The cleanest large pool in the dataset, and six separate
drives rather than one long one, so it carries route variety.

| Task | Notes |
|---|---|
| Apply per-session lag before use | ranges to **+313.8 s** on `S4/s1` — not optional |
| Use as the main training set | |
| Do **not** hold any of it out | drivers B and D already cover evaluation |

> `S4` needs care: session 0 has a +1.8 s lag, session 1 needs **+313.8 s**. Correcting the
> file as a whole would wreck both. Per session, always.

---

## Driver B (`M`) — the test set

**All three sessions verified at 0.932 / 0.993 / 0.984**, zero stuck samples, small lags
(+0.8 s, +2.0 s, +3.2 s). The cleanest drive in the dataset, and driver B recorded nothing
else — so holding it out is a genuine unseen-driver test.

| Task | Notes |
|---|---|
| **Never train on it** | any leak invalidates the headline number |
| Evaluate the final model here | this is the figure that goes in the report |
| Recompute derived columns at eval time | don't read `gx_c`, `stationary` etc. from file — the real engine wouldn't have them |

2.9 h and 105 km is a solid holdout — larger than the `Y1` it replaced.

---

## Driver D (`Y1`) — second holdout

**Recovered.** It scored 0.058 and looked dead; the phone and vehicle files were **115.6 s**
apart, beyond the ±30 s originally searched. After correction: **0.798**, and the two GPS
tracks sit 16 m apart — as close as any healthy drive.

| Task | Notes |
|---|---|
| Apply the **+115.6 s** correction to session 3 | the whole recovery depends on it |
| Use as a second test set | two independent test drivers beat one |
| Report both B and D separately | never averaged — they are different drivers |

Its four sessions are lopsided: 0.5 min, 0.1 min, 5.1 min and **111.5 min**. Only session 3
matters.

---

## Driver E — bulk training, and the stress case

**16.3 h and 902 km — over half the dataset — but only 0.2 h verifies.** That sounds fatal
and isn't: the GPS tracks of these drives sit **20–38 m** from the vehicle tracks, the same
as healthy drives. They are correctly paired and correctly timed. The gyro correlation is
lower (~0.5) for reasons I could not pin down — not clock drift, not mount movement, not a
worse sensor, all three tested and ruled out.

| Task | Notes |
|---|---|
| Use for training | noisy labels train fine; more data still helps |
| **Never use for evaluation** | a noisy label makes a bad score uninterpretable |
| Try down-weighting vs. equal weight | measure it, don't assume |
| `Vtb1` → **stress test only** | 20.4% stuck samples, 34.5 s of frozen gyro-X, 661 s gap |

> **The rule: noisy data trains, clean data grades.**

---

## Standing rules

1. **Split by driver, never randomly.** Overlapping windows leak answers across a random split.
2. **Never cross a session boundary.** 83 sessions across 72 drives.
3. **Apply lag per session, never per file.** `S4` needs +1.8 s and +313.8 s in the same file.
4. **Noisy data trains, clean data grades.**

---

## Alignment procedure

Both stages are required — neither alone is sufficient.

```
COARSE   match the two GPS tracks over ±10 min
         finds large offsets (111 s, 309 s, 564 s)
         resolution only ~±5 s — phone GPS updates every 9 s

FINE     match gyro against vehicle yaw-rate over ±30 s
         refines to sub-second
         cannot see anything beyond its ±30 s window
```

Searching gyro alone misses a 300 s offset entirely and reports the session as broken.
That mistake cost 6 hours of data, including what was then the test set.

Final lags are in `data/alignment.csv` as `total_lag`.

---

## Next

1. Apply `total_lag` per session to the parquet files
2. Fix the evaluator's 4× overcount
3. Re-baseline the speed-change model on aligned data
