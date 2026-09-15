"""Round 2 · Step 1 — build the fixed blackout list and check the scoring before any method uses it.

  1  blackout list          -> round2/out/blackouts.parquet
  2  round-1 reproduction   round-1's own blackouts through the same formula must give round-1's numbers
  3  ground truth           vehicle path length against vehicle speed over the same stretch
  4  scorer self-test       a distance-only estimate placed on the true path
  5  reference              coast distance error under the round-2 rules

Rules: round2/DECISIONS.md.  Run from the repo root:  .venv/bin/python3 round2/step1_evaluator.py"""
import warnings; warnings.filterwarnings("ignore")
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, blackouts, scoring
from core.geo import enu

T0 = time.time()
ORDER = ["E", "B", "A", "D"]
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")

# ───────────────────────── 1 · blackout list ─────────────────────────
SESS, parts = {}, []
for _, r in sessions.selected().iterrows():
    S = sessions.load(r.drive, r.driver, int(r.session))
    if S is None:
        continue
    SESS[(S.drive, S.session)] = S
    parts.append(blackouts.build(S))
BL = pd.concat(parts, ignore_index=True)
(R2/"out").mkdir(exist_ok=True)
BL.to_parquet(R2/"out/blackouts.parquet", index=False)
log(f"{len(SESS)} sessions, {sum(S.dist[-1] for S in SESS.values())/1000:,.0f} km driven; "
    f"{len(BL):,} start points -> round2/out/blackouts.parquet")

head("1 · FIXED BLACKOUT LIST — valid blackouts (sessions contributing)")
print(f"  {'set':<8}{'checkpoint':>11}" + "".join(f"{'driver ' + D:>17}" for D in ORDER))
for sset in ("moving", "stopgo"):
    for c in blackouts.CHECKPOINTS:
        cells = []
        for D in ORDER:
            g = BL[(BL.driver == D) & BL[f"{sset}_{c}"]]
            cells.append(f"{len(g):,} ({g.groupby(['drive', 'session']).ngroups})")
        print(f"  {sset:<8}{c:>9} m" + "".join(f"{x:>17}" for x in cells))

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
ref = pd.read_csv(ROOT/"out/drift_all_drivers.csv")
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
head("5 · REFERENCE — coast (speed at blackout start held), DISTANCE error, round-2 rules, moving set")
print("  Distance only: heading is not modelled until step 3. Round-1 equivalents are in section 2.\n")
refrows = []
for c in blackouts.CHECKPOINTS:
    for b in BL[BL[f"moving_{c}"]].itertuples(index=False):
        S = SESS[(b.drive, b.session)]
        i, j = b.row_start, getattr(b, f"end_{c}")
        td = S.dist[j] - S.dist[i]
        refrows.append((b.driver, b.drive, b.session, c, 100*abs(S.v[i]*(S.t[j] - S.t[i]) - td)/td))
R = pd.DataFrame(refrows, columns=["driver", "drive", "session", "checkpoint", "err"])
print(f"  {'checkpoint':<12}" + "".join(f"{'driver ' + D:>26}" for D in ORDER))
print(f"  {'':<12}" + "".join(f"{'every / session-weighted':>26}" for D in ORDER))
for c in blackouts.CHECKPOINTS:
    cells = []
    for D in ORDER:
        q = R[(R.driver == D) & (R.checkpoint == c)]
        cells.append(f"{scoring.wmedian(q.err):.1f}% / {scoring.wmedian(q.err, scoring.session_weights(q)):.1f}%")
    print(f"  {c:>7} m    " + "".join(f"{x:>26}" for x in cells))

# ───────────────────────── 6 · sessions ─────────────────────────
head("6 · SESSIONS — valid moving blackouts and coast distance error, per session")
print("  In the session-weighted median every session carries equal weight, however few blackouts it has.\n")
print(f"  {'driver':<8}{'drive':<8}{'session':>8}{'km':>6}{'km/h':>6}"
      + "".join(f"{f'{c} m: n · median':>22}" for c in (50, 500, 1000)))
for D in ORDER:
    for (drive, session), _ in BL[BL.driver == D].groupby(["drive", "session"]):
        S = SESS[(drive, session)]
        cells = []
        for c in (50, 500, 1000):
            q = R[(R.drive == drive) & (R.session == session) & (R.checkpoint == c)]
            cells.append(f"{len(q):>5} · {q.err.median():5.1f}%" if len(q) else f"{0:>5} ·     -")
        print(f"  {D:<8}{drive:<8}{session:>8}{S.dist[-1]/1000:>6.0f}{3.6*S.v.mean():>6.0f}"
              + "".join(f"{x:>22}" for x in cells))
log("done")
