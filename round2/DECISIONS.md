# Round 2 — decisions

Settled before building. Each changes what the numbers mean, so any change gets a new dated entry
here with the reason — never a silent edit.

---

## 2026-09-16 · Step 0 — scoring rules

Proposed in the step-2 plan and accepted ("okay start step wise").

| # | Decision | Rule |
|---|---|---|
| 1 | **Weighting** | Every blackout in the fixed list counts. Headline = **session-weighted median** (each session's blackouts share one unit of weight). The every-blackout median is always shown next to it. |
| 2 | **Main metric** | **2D position error** at the checkpoint ÷ true distance travelled — the problem statement's "positional drift". Distance error (the round-1 metric) reported alongside. |
| 3 | **Blackout sets** | `moving` — round-1 rule: speed never below 1.4 km/h. `stopgo` — stops allowed; the checkpoint must be reached within 10 min. |
| 4 | **Split** | Tune on drivers **A and B** only. **D and E are test-only**, run once with frozen settings. |
| 5 | **Step-5 design** | **Road-constrained particle filter** (Hidden Markov Map Matching solved with many hypotheses). The event-based matcher from the audit stays as the comparison. |
| 6 | **Training** | No new model training in step 2. The trained motion classifier is reused unchanged. The matcher's few settings are tuned on A and B and frozen before D and E are touched. |

---

## 2026-09-16 · Step 1 — how blackouts are drawn

| Rule | Value | Why |
|---|---|---|
| Sessions | `data/alignment.csv`: \|sync_r\| ≥ 0.40, not `Vtb1`, ≥ 3,000 aligned rows | the same 28 sessions as round 1 and the audit |
| Start points | one every **250 m** of travelled distance | every kilometre counts equally whatever the speed; round 1 started every 2 s, which over-weights slow driving, and 2 s spacing makes near-duplicate blackouts |
| Start speed | above 4.2 m/s (15 km/h) | round-1 rule |
| History | at least **300 s** of session before the start | step 2 calibrates the gyro on GNSS before the blackout |
| Checkpoints | **50, 100, 200, 500, 1000 m** of true distance travelled | the PS benchmarks are 50 m and 1 km; each checkpoint is valid on its own, so a stop at 600 m does not remove the 50 m result |
| Clean data | inside the blackout: phone IMU present, vehicle position present, no vehicle GNSS dropout | a frozen truth position cannot grade anything |
| True distance | vehicle speed (`speed_best_al`) integrated over the phone clock (`t_raw_s`) | round-1 definition, with exact timing |
| True position | vehicle `lat`/`lon` through `veh_idx`, converted to metres with WGS84 radii at the start point | a 0.7% map-scale error would already be 7 m per km |
| Positions scored | estimate − truth, metres from the last fix before the blackout | |

The list is `round2/out/blackouts.parquet`, built by `round2/step1_evaluator.py` with `round2/core/`.
