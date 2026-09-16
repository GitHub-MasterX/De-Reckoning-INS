"""Round 2 — results in one command, driver by driver, the way round 1's run_evaluation.py reported.

Reads what step 7 saved (out/test_errors.parquet: every scored blackout, with both the map-free baseline and the
frozen particle filter) and prints:
  1  per driver, per distance — 2D position error and the share inside the problem statement's 10%
  2  the same in metres, against the two PS targets (5 m over 50 m, 100 m over 1 km)
  3  per driving condition — the round-2 headline
  4  stop-and-go blackouts
  5  what each driver's blackouts are made of, so the per-driver numbers can be read properly
Writes out/round2_results.csv and out/plots/r2_drift_by_driver.png.
Nothing is re-run and nothing is retuned: A and B set the settings, D and E were tested once.

Run from the repo root:  .venv/bin/python3 round2/run_round2_evaluation.py"""
import warnings; warnings.filterwarnings("ignore")
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R2 = Path(__file__).resolve().parent
sys.path.insert(0, str(R2))
from core import context

ORDER = ["E", "B", "A", "D"]
ROLE = {"E": "test", "D": "test", "A": "tuning", "B": "tuning"}
CHECKS = (50, 100, 200, 500, 1000)
P = pd.read_parquet(R2/"out/test_errors.parquet")
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
def head(t): print(f"\n{'='*98}\n{t}\n{'='*98}")

print(f"round 2 · {P.row_start.nunique():,} blackouts · settings frozen on A+B: "
      + ", ".join(f"{k}={v}" for k, v in PARAMS.items()))
print("2D position error = distance between the estimate and the true position, as a share of the distance driven")

# ───────────────────────── 1 · per driver ─────────────────────────
head("1 · PER DRIVER — 2D position error, no stops (median · share within the PS 10%)")
rows = []
for D in ORDER:
    q = P[(P.driver == D) & (P.set == "moving")]
    print(f"\n  Driver {D} ({ROLE[D]} driver) — {q[q.checkpoint == 50].shape[0]:,} blackouts at 50 m, "
          f"{q[q.checkpoint == 1000].shape[0]:,} at 1 km")
    print(f"    {'distance':>10}{'blackouts':>11}{'no map':>10}{'with map':>11}{'no map':>12}{'with map':>11}")
    for c in CHECKS:
        s = q[q.checkpoint == c]
        if not len(s):
            continue
        row = dict(driver=D, role=ROLE[D], set="moving", distance_m=c, blackouts=len(s),
                   baseline_pct=s.base_pos.median(), filter_pct=s.pf_pos.median(),
                   baseline_pass=100*(s.base_pos <= 10).mean(), filter_pass=100*(s.pf_pos <= 10).mean())
        rows.append(row)
        print(f"    {c:>8} m{len(s):>11,}{row['baseline_pct']:>9.1f}%{row['filter_pct']:>10.1f}%"
              f"{row['baseline_pass']:>11.0f}%{row['filter_pass']:>10.0f}%")

# ───────────────────────── 2 · in metres ─────────────────────────
head("2 · THE SAME IN METRES — median error, against the problem statement's targets")
print(f"  {'driver':<8}" + "".join(f"{f'{c} m':>22}" for c in CHECKS))
print(f"  {'':<8}" + "".join(f"{'no map | with map':>22}" for _ in CHECKS))
for D in ORDER:
    cells = []
    for c in CHECKS:
        s = P[(P.driver == D) & (P.set == "moving") & (P.checkpoint == c)]
        cells.append(f"{s.base_pos.median()*c/100:.1f} m | {s.pf_pos.median()*c/100:.1f} m" if len(s) else "-")
    print(f"  {D:<8}" + "".join(f"{x:>22}" for x in cells))
print("\n  targets: under 5 m at 50 m, under 100 m at 1 km (both are the same 10% of distance)")

# ───────────────────────── 3 · per condition ─────────────────────────
head("3 · PER DRIVING CONDITION — the round-2 headline, test drivers D and E")
print(f"  {'group':<8}{'km/h':>8}{'distance':>11}{'blackouts':>11}{'no map':>10}{'with map':>11}{'within 10%':>24}")
for lo, hi, name in context.BANDS:
    for c in CHECKS:
        s = P[(P.set == "moving") & (P.band == name) & (P.checkpoint == c) & P.driver.isin(["D", "E"])]
        if not len(s):
            continue
        label = f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"
        rows.append(dict(driver="D+E", role="test", set=f"moving·{name}", distance_m=c, blackouts=len(s),
                         baseline_pct=s.base_pos.median(), filter_pct=s.pf_pos.median(),
                         baseline_pass=100*(s.base_pos <= 10).mean(), filter_pass=100*(s.pf_pos <= 10).mean()))
        print(f"  {name:<8}{label:>8}{c:>9} m{len(s):>11,}{s.base_pos.median():>9.1f}%{s.pf_pos.median():>10.1f}%"
              f"{100*(s.base_pos <= 10).mean():>14.0f}% → {100*(s.pf_pos <= 10).mean():>3.0f}%")

# ───────────────────────── 4 · stop-and-go ─────────────────────────
head("4 · STOP-AND-GO BLACKOUTS — stops allowed inside the blackout")
print(f"  {'driver':<8}" + "".join(f"{f'{c} m':>20}" for c in CHECKS))
for D in ORDER:
    cells = []
    for c in CHECKS:
        s = P[(P.driver == D) & (P.set == "stopgo") & (P.checkpoint == c)]
        if len(s):
            rows.append(dict(driver=D, role=ROLE[D], set="stopgo", distance_m=c, blackouts=len(s),
                             baseline_pct=s.base_pos.median(), filter_pct=s.pf_pos.median(),
                             baseline_pass=100*(s.base_pos <= 10).mean(), filter_pass=100*(s.pf_pos <= 10).mean()))
        cells.append(f"{s.base_pos.median():.1f}% | {s.pf_pos.median():.1f}%" if len(s) else "-")
    print(f"  {D:<8}" + "".join(f"{x:>20}" for x in cells))

# ───────────────────────── 5 · what each driver drove ─────────────────────────
head("5 · WHAT EACH DRIVER'S 1 km BLACKOUTS ARE MADE OF — share by driving condition")
print(f"  {'driver':<8}" + "".join(f"{name:>12}" for _, _, name in context.BANDS) + f"{'turns in 1 km':>16}")
for D in ORDER:
    s = P[(P.driver == D) & (P.set == "moving") & (P.checkpoint == 1000)]
    print(f"  {D:<8}" + "".join(f"{100*(s.band == name).mean():>11.0f}%" for _, _, name in context.BANDS)
          + f"{s.turns.median():>16.0f}")

pd.DataFrame(rows).round(2).to_csv(R2/"out/round2_results.csv", index=False)

# ───────────────────────── plot ─────────────────────────
(R2/"out/plots").mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
for ax, D in zip(axes.ravel(), ORDER):
    q = P[(P.driver == D) & (P.set == "moving")]
    d = [c for c in CHECKS if len(q[q.checkpoint == c])]
    ax.plot(d, [q[q.checkpoint == c].base_pos.median() for c in d], "o-", color="#1f4e79", lw=2, label="no map")
    ax.plot(d, [q[q.checkpoint == c].pf_pos.median() for c in d], "o-", color="#15803d", lw=2, label="with map")
    ax.axhline(10, color="#dc2626", ls="--", lw=1.6, label="10% benchmark")
    ax.set_title(f"Driver {D} — {ROLE[D]} driver", fontsize=12, weight="bold")
    ax.set_xlabel("blackout distance (m)"); ax.set_ylabel("2D position error (% of distance)")
    ax.set_ylim(0, 30); ax.grid(alpha=.25); ax.legend(fontsize=9, loc="upper left")
fig.suptitle("Round 2 — 2D position drift with and without the map, per driver", fontsize=13.5, weight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.965])
fig.savefig(R2/"out/plots/r2_drift_by_driver.png", dpi=150)
print("\nwrote round2/out/round2_results.csv and round2/out/plots/r2_drift_by_driver.png")
