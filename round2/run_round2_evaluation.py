"""Round 2 — results in one command, driver by driver, the way round 1's run_evaluation.py reported.

Reads what step 7 saved (out/test_errors.parquet: every scored blackout, with both the map-free baseline and the
frozen particle filter) and prints:
  1  per driver, per distance — 2D drift, the share inside the 10% benchmark, and a PASS/fail verdict
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
BUDGET = 10.0            # the problem statement's benchmark: 10% of the distance driven
P = pd.read_parquet(R2/"out/test_errors.parquet")
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")
def verdict(pct): return "✓ PASS" if pct < BUDGET else "fail"

print(f"round 2 · {P.row_start.nunique():,} blackouts · settings frozen on A+B: "
      + ", ".join(f"{k}={v}" for k, v in PARAMS.items()))
print("""
  What the numbers mean
    2D drift      distance between the estimate and the true position at the checkpoint, as a share of the
                  distance driven since GPS was lost. Lower is better; the benchmark is under 10%.
    no map        the step-3 engine: gyro heading + the last GPS speed held + stop detection, no map at all.
                  (Round 1's "coast" is not the same thing — it scored distance travelled, not 2D position.)
    with map      the same engine with the road-constrained particle filter on top.
    within 10%    the share of individual blackouts that met the benchmark, not just the median one.
    PASS          the median with the map is under 10% of the distance driven.""")

# ───────────────────────── 1 · per driver ─────────────────────────
head("1 · PER DRIVER — no stops inside the blackout")
rows = []
for D in ORDER:
    q = P[(P.driver == D) & (P.set == "moving")]
    print(f"\n  Driver {D} ({ROLE[D]} driver) — {q[q.checkpoint == 50].shape[0]:,} blackouts at 50 m, "
          f"{q[q.checkpoint == 1000].shape[0]:,} at 1 km")
    print(f"    {'':>10}{'':>11}{'2D drift (median)':>23}{'within 10%':>22}{'verdict':>12}")
    print(f"    {'distance':>10}{'blackouts':>11}{'no map':>12}{'with map':>11}{'no map':>11}{'with map':>11}"
          f"{'(with map)':>12}")
    for c in CHECKS:
        s = q[q.checkpoint == c]
        if not len(s):
            continue
        row = dict(driver=D, role=ROLE[D], set="moving", distance_m=c, blackouts=len(s),
                   baseline_pct=s.base_pos.median(), filter_pct=s.pf_pos.median(),
                   baseline_pass=100*(s.base_pos <= BUDGET).mean(), filter_pass=100*(s.pf_pos <= BUDGET).mean())
        row["verdict"] = verdict(row["filter_pct"])
        rows.append(row)
        print(f"    {c:>8} m{len(s):>11,}{row['baseline_pct']:>11.1f}%{row['filter_pct']:>10.1f}%"
              f"{row['baseline_pass']:>10.0f}%{row['filter_pass']:>10.0f}%{row['verdict']:>12}")

# ───────────────────────── 2 · in metres ─────────────────────────
head("2 · THE SAME IN METRES — median error against the problem statement's targets")
print(f"  {'driver':<8}" + "".join(f"{f'{c} m':>24}" for c in CHECKS))
print(f"  {'':<8}" + "".join(f"{'no map | with map':>24}" for _ in CHECKS))
for D in ORDER:
    cells = []
    for c in CHECKS:
        s = P[(P.driver == D) & (P.set == "moving") & (P.checkpoint == c)]
        if not len(s):
            cells.append("-")
            continue
        metres = s.pf_pos.median()*c/100
        cells.append(f"{s.base_pos.median()*c/100:.1f} | {metres:.1f} m  {'✓' if metres < c*BUDGET/100 else '✗'}")
    print(f"  {D:<8}" + "".join(f"{x:>24}" for x in cells))
print(f"\n  budget at each distance (10%): " + " · ".join(f"{c} m → {c*BUDGET/100:.0f} m" for c in CHECKS))
print("  the two named PS targets are under 5 m over 50 m, and under 100 m over 1 km")

# ───────────────────────── 3 · per condition ─────────────────────────
head("3 · PER DRIVING CONDITION — test drivers D and E, no stops")
print(f"  {'group':<8}{'km/h':>8}{'distance':>11}{'blackouts':>11}{'2D drift: no map':>19}{'with map':>11}"
      f"{'within 10%':>22}{'verdict':>10}")
for lo, hi, name in context.BANDS:
    for c in CHECKS:
        s = P[(P.set == "moving") & (P.band == name) & (P.checkpoint == c) & P.driver.isin(["D", "E"])]
        if not len(s):
            continue
        label = f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"
        pf = s.pf_pos.median()
        rows.append(dict(driver="D+E", role="test", set=f"moving·{name}", distance_m=c, blackouts=len(s),
                         baseline_pct=s.base_pos.median(), filter_pct=pf,
                         baseline_pass=100*(s.base_pos <= BUDGET).mean(), filter_pass=100*(s.pf_pos <= BUDGET).mean(),
                         verdict=verdict(pf)))
        print(f"  {name:<8}{label:>8}{c:>9} m{len(s):>11,}{s.base_pos.median():>18.1f}%{pf:>10.2f}%"
              f"{100*(s.base_pos <= BUDGET).mean():>14.0f}% → {100*(s.pf_pos <= BUDGET).mean():>3.0f}%"
              f"{verdict(pf):>10}")
print("\n  the with-map column carries two decimals because the verdict is decided on the unrounded value, here and in")
print("  the stop-and-go table below: a cell printed as 10.00% with a tick was just under the budget, one with a")
print("  cross was just over")

# ───────────────────────── 4 · stop-and-go ─────────────────────────
head("4 · STOP-AND-GO BLACKOUTS — stops allowed inside the blackout (2D drift: no map | with map)")
print(f"  {'driver':<8}" + "".join(f"{f'{c} m':>23}" for c in CHECKS))
for D in ORDER:
    cells = []
    for c in CHECKS:
        s = P[(P.driver == D) & (P.set == "stopgo") & (P.checkpoint == c)]
        if not len(s):
            cells.append("-")
            continue
        pf = s.pf_pos.median()
        rows.append(dict(driver=D, role=ROLE[D], set="stopgo", distance_m=c, blackouts=len(s),
                         baseline_pct=s.base_pos.median(), filter_pct=pf,
                         baseline_pass=100*(s.base_pos <= BUDGET).mean(), filter_pass=100*(s.pf_pos <= BUDGET).mean(),
                         verdict=verdict(pf)))
        cells.append(f"{s.base_pos.median():.1f}% | {pf:.2f}%  {'✓' if pf < BUDGET else '✗'}")
    print(f"  {D:<8}" + "".join(f"{x:>22}" for x in cells))

# ───────────────────────── 5 · what each driver drove ─────────────────────────
head("5 · WHAT EACH DRIVER'S 1 km BLACKOUTS ARE MADE OF — share by driving condition")
print(f"  {'driver':<8}" + "".join(f"{name:>12}" for _, _, name in context.BANDS) + f"{'turns in 1 km':>16}")
for D in ORDER:
    s = P[(P.driver == D) & (P.set == "moving") & (P.checkpoint == 1000)]
    print(f"  {D:<8}" + "".join(f"{100*(s.band == name).mean():>11.0f}%" for _, _, name in context.BANDS)
          + f"{s.turns.median():>16.0f}")
print("\n  a driver's figures mostly reflect this mix: E is nearly all fast motorway with no turns to match,")
print("  D is mostly slow and mixed driving with three turns in a kilometre")

# ───────────────────────── 6 · side by side with round 1 ─────────────────────────
head("6 · SIDE BY SIDE WITH ROUND 1 — progress read on round 1's own metric")
R1 = pd.read_csv(R2.parent/"out/drift_all_drivers.csv")
print("  Every number in this file is DRIFT — how far the estimate ends from the truth, as a share of the distance")
print("  driven. The column names are ENGINES, meaning whose drift it is:")
print("    coast     round 1's engine: hold the last GPS speed and keep going (no heading, no map)")
print("    no map    round 2's engine without the map: gyro heading + held GPS speed + stop detection")
print("    with map  the same engine with the particle filter on the road network")
print("    floor     round 1's oracle: the true speed fed in, so only the maths and the 10 Hz sampling remain —")
print("              what any engine would score if the speed estimate were perfect\n")
print("  Round 1 scored DISTANCE TRAVELLED drift. Round 2 scores 2D POSITION drift and records distance drift too, so")
print("  the first four columns compare like with like. Two things differ and should be said aloud when this is shown:")
print("    · the blackout sets are not the same — round 1 started one every 2 s and sampled at most 200 per session,")
print("      round 2 starts one every 250 m and requires 5 minutes of history before each")
print("    · round 1's engine had no heading at all; 2D position was never scored")
print("  The controlled comparison — identical blackouts, same metric — is 'no map' against 'with map'.\n")
print(f"  {'':<8}{'':>10}{'round 1':>12}{'round 2':>12}{'round 2':>12}{'round 1':>10}{'round 2':>15}")
print(f"  {'driver':<8}{'distance':>10}{'coast':>12}{'no map':>12}{'with map':>12}{'floor':>10}{'with map, 2D':>15}")
print(f"  {'':<8}{'':>10}{'distance':>12}{'distance':>12}{'distance':>12}{'distance':>10}{'position':>15}")
for D in ORDER:
    for c in (50, 1000):
        r1 = R1[(R1.driver == D) & (R1.dist_m == c)]
        s = P[(P.driver == D) & (P.set == "moving") & (P.checkpoint == c)]
        if not len(s) or not len(r1):
            continue
        rows.append(dict(driver=D, role=ROLE[D], set="round1_vs_round2", distance_m=c, blackouts=len(s),
                         baseline_pct=s.base_dist.median(), filter_pct=s.pf_dist.median(),
                         baseline_pass=float(r1.coast.iloc[0]), filter_pass=s.pf_pos.median(),
                         verdict=verdict(s.pf_dist.median())))
        print(f"  {D:<8}{c:>8} m{float(r1.coast.iloc[0]):>11.1f}%{s.base_dist.median():>11.1f}%"
              f"{s.pf_dist.median():>11.1f}%{float(r1.oracle.iloc[0]):>9.1f}%{s.pf_pos.median():>14.1f}%")

pd.DataFrame(rows).round(2).to_csv(R2/"out/round2_results.csv", index=False)

# ───────────────────────── plot ─────────────────────────
(R2/"out/plots").mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
for ax, D in zip(axes.ravel(), ORDER):
    q = P[(P.driver == D) & (P.set == "moving")]
    d = [c for c in CHECKS if len(q[q.checkpoint == c])]
    ax.plot(d, [q[q.checkpoint == c].base_pos.median() for c in d], "o-", color="#1f4e79", lw=2, label="no map")
    ax.plot(d, [q[q.checkpoint == c].pf_pos.median() for c in d], "o-", color="#15803d", lw=2, label="with map")
    ax.axhline(BUDGET, color="#dc2626", ls="--", lw=1.6, label="10% benchmark")
    ax.set_title(f"Driver {D} — {ROLE[D]} driver", fontsize=12, weight="bold")
    ax.set_xlabel("blackout distance (m)"); ax.set_ylabel("2D drift (% of distance)")
    ax.set_ylim(0, 30); ax.grid(alpha=.25); ax.legend(fontsize=9, loc="upper left")
fig.suptitle("Round 2 — 2D position drift with and without the map, per driver", fontsize=13.5, weight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.965])
fig.savefig(R2/"out/plots/r2_drift_by_driver.png", dpi=150)
print("\nwrote round2/out/round2_results.csv and round2/out/plots/r2_drift_by_driver.png")
