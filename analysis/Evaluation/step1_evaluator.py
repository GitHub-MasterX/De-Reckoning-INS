"""Round 2 · Step 1 — build the fixed blackout list and check the scoring before any method uses it.

  1  blackout list          -> round2/out/Pipeline_Data/blackouts.parquet; counts per driver and per driving condition
  2  round-1 reproduction   round-1's own blackouts through the same formula must give round-1's numbers
  3  ground truth           vehicle path length against vehicle speed over the same stretch
  4  scorer self-test       a distance-only estimate placed on the true path
  5  reference              coast distance error by driving condition and by driver, plus landmark context
  6  sessions               per session: blackouts, coast error, the route's spacing between real turns

Rules: round2/DECISIONS.md.  Run from the repo root:  .venv/bin/python3 round2/step1_evaluator.py"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, blackouts, context, scoring
from core.Engine.geo import enu

T0 = time.time()
ORDER = ["E", "B", "A", "D"]
TUNE, TEST = ["A", "B"], ["D", "E"]
GROUPS = [name for _, _, name in context.BANDS]
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")
def nsess(g): return g.groupby(["drive", "session"]).ngroups
def band_label(lo, hi): return f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}"

# ───────────────────────── 1 · blackout list ─────────────────────────
SESS, parts = {}, []
for _, r in sessions.selected().iterrows():
    S = sessions.load(r.drive, r.driver, int(r.session))
    if S is None:
        continue
    SESS[(S.drive, S.session)] = S
    parts.append(blackouts.build(S))
BL = pd.concat(parts, ignore_index=True)
(ROOT/"outputs").mkdir(exist_ok=True)
BL.to_parquet(ROOT/"outputs/Pipeline_Data/blackouts.parquet", index=False)
log(f"{len(SESS)} sessions, {sum(S.dist[-1] for S in SESS.values())/1000:,.0f} km driven; "
    f"{len(BL):,} start points -> round2/out/Pipeline_Data/blackouts.parquet")

head("1 · FIXED BLACKOUT LIST — valid blackouts (sessions contributing)")
print(f"  {'set':<8}{'checkpoint':>11}" + "".join(f"{'driver ' + D:>17}" for D in ORDER))
for sset in ("moving", "stopgo"):
    for c in blackouts.CHECKPOINTS:
        cells = []
        for D in ORDER:
            g = BL[(BL.driver == D) & BL[f"{sset}_{c}"]]
            cells.append(f"{len(g):,} ({nsess(g)})")
        print(f"  {sset:<8}{c:>9} m" + "".join(f"{x:>17}" for x in cells))

head("1b · DRIVING CONDITIONS — valid blackouts per group:  tuning A+B  |  test D+E   (sessions)")
print(f"  {'group':<7}{'km/h':>7}" + "".join(f"{lab:>30}" for lab in ("moving 50 m", "moving 1000 m", "stopgo 1000 m")))
for lo, hi, name in context.BANDS:
    cells = []
    for sset, c in (("moving", 50), ("moving", 1000), ("stopgo", 1000)):
        g = BL[BL[f"{sset}_{c}"] & (BL[f"band_{c}"] == name)]
        a, b = g[g.driver.isin(TUNE)], g[g.driver.isin(TEST)]
        cells.append(f"{len(a):,} ({nsess(a)})  |  {len(b):,} ({nsess(b)})")
    print(f"  {name:<7}{band_label(lo, hi):>7}" + "".join(f"{x:>30}" for x in cells))

# ───────────────────────── 2 · round-1 reproduction ─────────────────────────
head("2 · ROUND-1 REPRODUCTION — round-1's blackouts (eval_cache.npz, same random draws), same formula")
z = np.load(ROOT/"models/eval_cache.npz", allow_pickle=True)
drv, sess, v_end, moving = z["driver"], z["session"], z["v_end"], z["moving"]
STEP, DISTS = 0.5, [50, 100, 200, 500, 1000, 1500]
rng = np.random.default_rng(0)
rec = {}
for D in ["E", "B", "D", "A"]:                        # run_evaluation.py's order: the random draws depend on it
    te = drv == D
    v_, s_, m_ = v_end[te], sess[te], moving[te]
    for s in np.unique(s_):
        v, mv = v_[s_ == s], m_[s_ == s]
        cum = np.concatenate(([0], np.cumsum(v)*STEP))
        for dist in DISTS:
            st = [i for i in range(0, len(v)-6, 4) if v[i] > 4.2]
            if not st:
                continue
            for i in rng.choice(st, size=min(200, len(st)), replace=False):
                j = np.searchsorted(cum, cum[i]+dist)
                if j >= len(v) or not mv[i:j].all():
                    continue
                dt = float(np.sum(v[i:j])*STEP)
                if dt < dist*0.5:
                    continue
                ve, de = v[i], 0.0
                for k in range(i, j):
                    de += max(ve, 0.0)*STEP
                rec.setdefault((D, dist), []).append(abs(de-dt)/dt*100)
ref = pd.read_csv(ROOT/"outputs/Results/drift_all_drivers.csv")
worst, n_bad = 0.0, 0
print(f"  {'driver':<8}{'distance':>10}{'round 1 (committed)':>22}{'reproduced':>13}{'blackouts':>11}")
for _, row in ref.iterrows():
    vals = rec[(row.driver, int(row.dist_m))]
    mine = round(float(np.median(vals)), 2)
    worst = max(worst, abs(mine - row.coast)); n_bad += len(vals) != row.n
    if int(row.dist_m) in (50, 1000):
        print(f"  {row.driver:<8}{int(row.dist_m):>8} m{row.coast:>21.2f}%{mine:>12.2f}%{len(vals):>11,}")
print(f"\n  all {len(ref)} rows (4 drivers x 6 distances): largest difference {worst:.2f} points, "
      f"{n_bad} blackout-count mismatches  ->  {'IDENTICAL' if worst == 0 and n_bad == 0 else 'MISMATCH'}")

# ───────────────────────── 3 · ground truth ─────────────────────────
head("3 · GROUND TRUTH — vehicle path length (positions) vs vehicle distance (speed), 1 km moving blackouts")
gt = []
for b in BL[BL.moving_1000].itertuples(index=False):
    S = SESS[(b.drive, b.session)]
    i, j = b.row_start, b.end_1000
    e, n = enu(S.lat[i:j+1], S.lon[i:j+1], S.lat[i], S.lon[i])
    gt.append((b.driver, np.hypot(np.diff(e), np.diff(n)).sum()/(S.dist[j] - S.dist[i])))
gt = pd.DataFrame(gt, columns=["driver", "ratio"])
print(f"  {'driver':<8}{'blackouts':>10}{'(path - speed distance) / speed distance':>44}")
print(f"  {'':<18}{'median':>16}{'5th percentile':>16}{'95th percentile':>17}")
for D in ORDER:
    q = gt[gt.driver == D].ratio
    print(f"  {D:<8}{len(q):>10,}{100*(q.median()-1):>+15.2f}%{100*(q.quantile(.05)-1):>+15.2f}%"
          f"{100*(q.quantile(.95)-1):>+16.2f}%")

# ───────────────────────── 4 · scorer self-test ─────────────────────────
head("4 · SCORER SELF-TEST — coast distance placed on the true path (heading perfect by construction)")
stt = []
for b in BL[BL.moving_1000].itertuples(index=False):
    S = SESS[(b.drive, b.session)]
    i, j = b.row_start, b.end_1000
    est_dist = S.v[i]*(S.t[j] - S.t[i])
    k = min(int(np.searchsorted(S.dist, S.dist[i] + est_dist + 50)), len(S.t) - 1)
    e, n = enu(S.lat[i:k+1], S.lon[i:k+1], S.lat[i], S.lon[i])
    along = S.dist[i:k+1] - S.dist[i]
    p2d, p1d = scoring.errors(S, i, j, np.interp(est_dist, along, e), np.interp(est_dist, along, n), est_dist)
    stt.append((b.driver, p2d, p1d))
stt = pd.DataFrame(stt, columns=["driver", "pos", "dist"])
print(f"  {'driver':<8}{'distance error':>16}{'2D position error':>20}{'2D / distance (median)':>25}")
for D in ORDER:
    q = stt[stt.driver == D]
    print(f"  {D:<8}{q.dist.median():>15.2f}%{q.pos.median():>19.2f}%"
          f"{(q.pos/q.dist.where(q.dist > 0)).median():>24.3f}")
print("\n  On the true path the 2D error can only be the distance error, shortened where the road bends")
print("  (a chord is shorter than its arc) and scaled by the path/speed ratio of section 3.")

# ───────────────────────── 5 · reference ─────────────────────────
head("5 · REFERENCE — coast (speed at blackout start held), DISTANCE error, moving set")
print("  Distance only: heading is not modelled until step 3. Every blackout counts equally inside a group.")
refrows = []
for c in blackouts.CHECKPOINTS:
    for b in BL[BL[f"moving_{c}"]].itertuples(index=False):
        S = SESS[(b.drive, b.session)]
        i, j = b.row_start, getattr(b, f"end_{c}")
        td = S.dist[j] - S.dist[i]
        refrows.append((b.driver, b.drive, b.session, c, getattr(b, f"band_{c}"), getattr(b, f"turns_{c}"),
                        getattr(b, f"since_turn_m_{c}"), 100*abs(S.v[i]*(S.t[j] - S.t[i]) - td)/td))
R = pd.DataFrame(refrows, columns=["driver", "drive", "session", "checkpoint", "band", "turns", "since", "err"])

print("\n  5a · by driving condition — median drift (blackouts)")
print(f"  {'group':<7}{'km/h':>7}{'checkpoint':>12}{'A+B (tuning)':>22}{'D+E (test)':>22}")
for lo, hi, name in context.BANDS:
    for c in (50, 1000):
        cells = []
        for who in (TUNE, TEST):
            q = R[(R.band == name) & (R.checkpoint == c) & R.driver.isin(who)]
            cells.append(f"{q.err.median():.1f}% ({len(q):,})" if len(q) else "-")
        print(f"  {name:<7}{band_label(lo, hi):>7}{c:>10} m" + "".join(f"{x:>22}" for x in cells))

print("\n  5b · by driver — median drift, every blackout equal")
print(f"  {'checkpoint':<12}" + "".join(f"{'driver ' + D:>12}" for D in ORDER))
for c in blackouts.CHECKPOINTS:
    print(f"  {c:>7} m   " + "".join(f"{R[(R.driver == D) & (R.checkpoint == c)].err.median():>11.1f}%" for D in ORDER))

print("\n  5c · landmark context at 1 km — real turns >= 15° in the vehicle GPS course (reporting only), all drivers")
q1 = R[R.checkpoint == 1000]
print(f"  {'':<48}" + "".join(f"{nm:>10}" for nm in GROUPS))
for label, fn in (("blackouts", lambda x: f"{len(x):,}"),
                  ("median real turns inside the 1 km", lambda x: f"{x.turns.median():.0f}"),
                  ("share with no turn at all", lambda x: f"{100*(x.turns == 0).mean():.0f}%"),
                  ("median distance, last turn -> 1 km mark", lambda x: f"{x.since.median():.0f} m")):
    print(f"  {label:<48}" + "".join(f"{(fn(q1[q1.band == nm]) if (q1.band == nm).any() else '-'):>10}"
                                      for nm in GROUPS))
print("  With no turn, the distance counts from where GPS was lost. From step 5, drift is broken down by it.")

# ───────────────────────── 6 · sessions ─────────────────────────
head("6 · SESSIONS — moving blackouts and coast distance error; the route's median gap between real turns")
print(f"  {'driver':<8}{'drive':<8}{'session':>8}{'km':>6}{'km/h':>6}{'turn gap':>10}"
      + "".join(f"{f'{c} m: n · median':>22}" for c in (50, 500, 1000)))
for D in ORDER:
    for (drive, session), _ in BL[BL.driver == D].groupby(["drive", "session"]):
        S = SESS[(drive, session)]
        tt = context.real_turns(S)
        gap = f"{np.median(np.diff(S.dist[tt])):.0f} m" if len(tt) > 1 else "-"
        cells = []
        for c in (50, 500, 1000):
            q = R[(R.drive == drive) & (R.session == session) & (R.checkpoint == c)]
            cells.append(f"{len(q):>5} · {q.err.median():5.1f}%" if len(q) else f"{0:>5} ·     -")
        print(f"  {D:<8}{drive:<8}{session:>8}{S.dist[-1]/1000:>6.0f}{3.6*S.v.mean():>6.0f}{gap:>10}"
              + "".join(f"{x:>22}" for x in cells))
log("done")
