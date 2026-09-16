"""Round 2 · Step 8 — why the filter fails when it fails, and pictures of it.

Takes the 1 km blackouts from step 7, re-runs the frozen filter on a sample of them while recording the whole path,
and sorts the outcomes into causes:
  fallback        the map explained nothing, so the engine re-seeded or fell back to dead reckoning
  off the route   the estimate ends more than 30 m from anywhere the car actually drove — a wrong road or branch
  straight road   no real turn inside the blackout — nothing for the gyro to match
  along the road  on the driven route, but the wrong place along it: a speed error the map could not catch
  sideways        on the driven route, offset across it

The route test is geometric on purpose: comparing OSM way ids instead would call a long curving way "the same road"
even where it leads somewhere else.

Draws a few cases: the true track, the map-free path and the filter's path, over the local roads.
Outputs: round2/out/step8_run.txt, out/failure_cases.csv, out/plots/r2_failures.png.
Run from the repo root:  .venv/bin/python3 round2/step8_failures.py [--sample N]"""
import warnings; warnings.filterwarnings("ignore")
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, deadreckoning, engine_input, motion, particle, roadnet, scoring
from core.geo import enu, inv_enu

T0 = time.time()
OFF_ROUTE_M = 30.0
def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
SAMPLE = arg("--sample", 400)
PARAMS = json.loads((R2/"out/pf_params.json").read_text())
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")

E = pd.read_parquet(R2/"out/test_errors.parquet")
E = E[(E.set == "moving") & (E.checkpoint == 1000)].copy()
E["delta"] = E.pf_pos - E.base_pos
BL = pd.read_parquet(R2/"out/blackouts.parquet").set_index(["drive", "session", "row_start"])
net = roadnet.RoadNetwork()

worst = E.nlargest(SAMPLE//2, "delta")
rest = E.drop(worst.index)
mix = pd.concat([worst, rest.sample(min(SAMPLE - len(worst), len(rest)), random_state=0)])
mix = mix.sort_values(["drive", "session", "row_start"])
log(f"{len(E):,} blackouts at 1 km · re-running {len(mix):,} of them (the {len(worst)} worst, plus a random sample)")

rows, paths, cache = [], {}, {}
for b in mix.itertuples(index=False):
    key = (b.drive, b.session)
    if key not in cache:
        S = sessions.load(b.drive, b.driver, int(b.session))
        cache = {key: (S, calibration.Calibrator(S), motion.stationary_rows(S, b.driver)[0])}
    S, C, stat = cache[key]
    i = int(b.row_start)
    j = int(BL.loc[(b.drive, b.session, i), "end_1000"])
    cal = calibration.engine_calibration(C, i, CHOICE)
    if cal is None:
        continue
    inp = engine_input.build(S, cal, i, j)
    rec = list(range(10, j - i + 1, 10))
    res = particle.run(inp, net, stat[i:j+1], rec, params=PARAMS, rng=np.random.default_rng(i))
    dre, drn, _ = deadreckoning.run(inp, stationary=stat[i:j+1])
    k = res["rows"].index(j - i) if (j - i) in res["rows"] else len(res["rows"]) - 1
    est_e, est_n = res["east"][k], res["north"][k]
    te, tn, _ = scoring.truth_at(S, i, j)
    track_e, track_n = enu(S.lat[i:j+1], S.lon[i:j+1], S.lat[i], S.lon[i])
    gap = np.hypot(track_e - est_e, track_n - est_n)
    nearest = int(np.argmin(gap))
    off_route = float(gap[nearest])                       # how far the estimate is from the track the car drove
    arc = np.r_[0.0, np.cumsum(np.hypot(np.diff(track_e), np.diff(track_n)))]
    lag = float(arc[-1] - arc[nearest])                   # how far back along that track the estimate sits
    fallback = (not res["on_map"][k]) or res["reseeds"] > 0 or not res["seeded"]
    if fallback:
        cause = "fallback"
    elif off_route > OFF_ROUTE_M:
        cause = "off the route"
    elif b.turns == 0:
        cause = "straight road"
    elif abs(lag) > 50.0:                                 # on the route, but well behind or ahead of the car
        cause = "along the road"
    else:
        cause = "sideways"
    rows.append(dict(driver=b.driver, drive=b.drive, session=int(b.session), row_start=i, band=b.band,
                     turns=int(b.turns), since_turn_m=float(b.since_turn_m), base_pos=b.base_pos, pf_pos=b.pf_pos,
                     delta=b.delta, cause=cause, off_route_m=off_route, lag_m=lag,
                     reseeds=res["reseeds"], on_map=res["on_map"][k]))
    paths[(b.drive, b.session, i)] = dict(S=S, i=i, j=j, pf=(res["east"], res["north"]), dr=(dre, drn),
                                          driver=b.driver, band=b.band, cause=cause)
F = pd.DataFrame(rows)
F.to_csv(R2/"out/failure_cases.csv", index=False)
log(f"{len(F):,} blackouts classified")

head("1 · WHY THE FILTER LOSES — blackouts where it ended worse than no map (1 km, no stops)")
w = F[F.delta > 0]
better = F[F.delta <= 0]
print(f"  re-ran {len(F):,} blackouts — the worst by margin plus a random sample, so these shares describe the")
print(f"  failures, not how often they happen. {len(w):,} ended worse than no map, {len(better):,} as good or better.\n")
print(f"  {'cause':<16}{'worse':>8}{'share':>8}{'median error':>15}{'no-map error':>15}{'median turns':>14}"
      f"{'since last turn':>17}{'off route':>12}")
for cause, q in w.groupby("cause"):
    print(f"  {cause:<16}{len(q):>8,}{100*len(q)/len(w):>7.0f}%{q.pf_pos.median():>14.1f}%{q.base_pos.median():>14.1f}%"
          f"{q.turns.median():>14.0f}{q.since_turn_m.median():>15.0f} m{q.off_route_m.median():>10.0f} m")
print(f"\n  for contrast, the blackouts it improved:")
print(f"  {'cause':<16}{'count':>8}{'share':>8}{'median error':>15}{'no-map error':>15}{'median turns':>14}"
      f"{'since last turn':>17}{'off route':>12}")
for cause, q in better.groupby("cause"):
    print(f"  {cause:<16}{len(q):>8,}{100*len(q)/len(better):>7.0f}%{q.pf_pos.median():>14.1f}%"
          f"{q.base_pos.median():>14.1f}%{q.turns.median():>14.0f}{q.since_turn_m.median():>15.0f} m"
          f"{q.off_route_m.median():>10.0f} m")

head("2 · BY DRIVING CONDITION — share of the re-run blackouts that ended worse, and why")
causes = sorted(F.cause.unique())
print(f"  {'group':<8}{'re-run':>8}{'worse':>8}" + "".join(f"{c:>16}" for c in causes))
for band, q in F.groupby("band"):
    bad = q[q.delta > 0]
    print(f"  {band:<8}{len(q):>8,}{100*len(bad)/max(len(q), 1):>7.0f}%"
          + "".join(f"{100*(bad.cause == c).mean() if len(bad) else 0:>15.0f}%" for c in causes))

# ───────────────────────── pictures ─────────────────────────
pick = []
for cause in ("off the route", "straight road", "along the road", "fallback", "sideways"):
    q = F[(F.cause == cause) & (F.delta > 0)].nlargest(1, "delta")
    if len(q):
        pick.append(q.iloc[0])
best = F.nsmallest(1, "delta")
if len(best):
    pick.append(best.iloc[0])
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
for ax, row in zip(axes.ravel(), pick):
    P = paths[(row.drive, row.session, int(row.row_start))]
    S, i, j = P["S"], P["i"], P["j"]
    te, tn = enu(S.lat[i:j+1], S.lon[i:j+1], S.lat[i], S.lon[i])
    x, y = roadnet.xy(S.lat[i:j+1:20], S.lon[i:j+1:20])
    segs = np.unique(net.sample_seg[np.fromiter(
        (m for lst in net.tree.query_ball_point(np.c_[x, y], r=200.0) for m in lst), np.int64)])
    for s in segs:
        e0, n0 = enu(net.node_lat[net.seg_u[s]], net.node_lon[net.seg_u[s]], S.lat[i], S.lon[i])
        e1, n1 = enu(net.node_lat[net.seg_v[s]], net.node_lon[net.seg_v[s]], S.lat[i], S.lon[i])
        ax.plot([e0, e1], [n0, n1], color="#cbd5e1", lw=1, zorder=1)
    ax.plot(te, tn, color="#111827", lw=2.5, label="true track", zorder=4)
    ax.plot(P["dr"][0], P["dr"][1], color="#1f4e79", lw=1.8, ls="--", label="no map", zorder=3)
    ax.plot(P["pf"][0], P["pf"][1], color="#15803d", lw=1.8, label="with map", zorder=3)
    ax.scatter([te[-1]], [tn[-1]], color="#111827", s=45, zorder=5)
    ax.scatter([P["pf"][0][-1]], [P["pf"][1][-1]], color="#15803d", s=45, zorder=5)
    verdict = "the map won" if row.delta <= 0 else "the map lost"
    ax.set_title(f"{row.cause} — {verdict}\ndriver {row.driver}, {row.band}: no map {row.base_pos:.1f}% · "
                 f"with map {row.pf_pos:.1f}%", fontsize=10.5, weight="bold")
    ax.set_aspect("equal"); ax.grid(alpha=.2); ax.legend(fontsize=8, loc="best")
    ax.set_xlabel("east (m)"); ax.set_ylabel("north (m)")
for ax in axes.ravel()[len(pick):]:
    ax.axis("off")
fig.suptitle("Round 2 — where the map helps and where it hurts, 1 km blackouts", fontsize=13.5, weight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(R2/"out/plots/r2_failures.png", dpi=150)
print(f"\n  drew {len(pick)} cases -> round2/out/plots/r2_failures.png")
log("done")
