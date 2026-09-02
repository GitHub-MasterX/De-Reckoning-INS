#!/usr/bin/env python3
"""
IDR — one-command evaluation.

    python run_evaluation.py

Loads the saved models, evaluates positional drift for every driver at the problem
statement's benchmark distances, scores the motion classifier, and writes every figure.
Nothing is retrained. Typical runtime: ~15 seconds.

Outputs -> out/
    drift_all_drivers.csv        drift by driver and distance
    classifier_scores.csv        classifier accuracy by held-out driver
    plots/01_drift_percent.png   drift vs distance, per driver
    plots/02_drift_metres.png    drift in metres, with the PS targets marked
    plots/03_benchmark_bars.png  both benchmarks against their budgets
    plots/04_classifier.png      classifier performance
"""
import os, sys
from pathlib import Path

def _bootstrap():
    """Run under the project venv even if invoked with a bare `python3`."""
    try:
        import numpy, sklearn, joblib, matplotlib, pandas   # noqa: F401
        return
    except ImportError:
        pass
    venv = Path(__file__).resolve().parent / ".venv" / "bin" / "python3"
    if venv.exists() and Path(sys.executable).resolve() != venv.resolve():
        os.execv(str(venv), [str(venv), *sys.argv])          # re-exec, keeps arguments
    sys.exit(
        "\nIDR — required packages are not available.\n"
        f"  interpreter : {sys.executable}\n"
        "  set up once : python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
        "  then run    : python3 run_evaluation.py\n"
    )
_bootstrap()

import warnings; warnings.filterwarnings("ignore")
import time, json
import numpy as np, pandas as pd, joblib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).parent
MODELS, OUT = ROOT/"models", ROOT/"out"
(OUT/"plots").mkdir(parents=True, exist_ok=True)
FS, HOP = 10.0, 5
STEP = HOP/FS
DISTS = [50, 100, 200, 500, 1000, 1500]
NAME = {"E": "steady highway — the PS scenario", "B": "urban / mixed traffic",
        "A": "urban / mixed traffic", "D": "dense urban, low speed"}
ORDER = ["E", "B", "D", "A"]

def banner(t): print(f"\n{'='*74}\n{t}\n{'='*74}")

t0 = time.time()
for f in ("eval_cache.npz", "motion_models.pkl", "metadata.json"):
    if not (MODELS/f).exists():
        sys.exit(f"missing models/{f} — run analysis/train_and_save.py and "
                 f"analysis/eval_cache.py first")
z = np.load(MODELS/"eval_cache.npz", allow_pickle=True)
X, lab, drv, sess = z["X"], z["label"], z["driver"], z["session"]
v_end, dv, moving = z["v_end"], z["dv"], z["moving"]
models = joblib.load(MODELS/"motion_models.pkl")
meta = json.loads((MODELS/"metadata.json").read_text())
print(f"loaded {X.shape[0]:,} windows x {X.shape[1]} features and "
      f"{len(models)} models in {time.time()-t0:.1f}s")

# ─────────────────────────── 1 · CLASSIFIER ───────────────────────────
banner("1 · MOTION CLASSIFIER — stationary vs moving, from IMU alone")
print(f"  {'held out':<10}{'n test':>10}{'accuracy':>11}{'recall':>10}{'precision':>12}")
crows, cms = [], {}
for D in ORDER:
    key = f"{D}_holdout"
    if key not in models: continue
    te = drv == D
    keep = te & (lab >= 0)
    p = models[key].predict(X[keep]); y = lab[keep]
    cm = confusion_matrix(y, p, labels=[0, 1]); cms[D] = cm
    acc = (p == y).mean()
    rec = cm[0,0]/max(cm[0].sum(), 1); pre = cm[0,0]/max(cm[:,0].sum(), 1)
    crows.append(dict(driver=D, n=int(keep.sum()), accuracy=round(acc,4),
                      stationary_recall=round(rec,4), stationary_precision=round(pre,4)))
    print(f"  {D:<10}{int(keep.sum()):>10,}{acc:>10.1%}{rec:>10.1%}{pre:>12.1%}")
C = pd.DataFrame(crows); C.to_csv(OUT/"classifier_scores.csv", index=False)
print(f"\n  mean accuracy {C.accuracy.mean():.1%}   "
      f"naive vibration threshold {meta['naive_threshold_accuracy']:.1%}   "
      f"gain +{100*(C.accuracy.mean()-meta['naive_threshold_accuracy']):.1f} points")

# ─────────────────────────── 2 · DRIFT ───────────────────────────
banner("2 · POSITIONAL DRIFT — GNSS blackout, each driver unseen by its model")
rng = np.random.default_rng(0); rows = []
for D in ORDER:
    clf = models[f"{D}_holdout"]
    reg = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06,
                                        random_state=0).fit(X[drv != D], dv[drv != D])
    te = drv == D
    stat = clf.predict(X[te]) == 0
    pdv = reg.predict(X[te])
    v_, dv_, s_, m_ = v_end[te], dv[te], sess[te], moving[te]
    acc = {k: {d: [] for d in DISTS} for k in ("coast","zupt","model","oracle")}
    for s in np.unique(s_):
        m = s_ == s
        v, dvt, ps, pd_, mv = v_[m], dv_[m], stat[m], pdv[m], m_[m]
        cum = np.concatenate(([0], np.cumsum(v)*STEP))
        for dist in DISTS:
            st = [i for i in range(0, len(v)-6, 4) if v[i] > 4.2]
            if not st: continue
            for i in rng.choice(st, size=min(200, len(st)), replace=False):
                j = np.searchsorted(cum, cum[i]+dist)
                if j >= len(v) or not mv[i:j].all(): continue
                dt = float(np.sum(v[i:j])*STEP)
                if dt < dist*0.5: continue
                for key in acc:
                    ve, de = v[i], 0.0
                    for k in range(i, j):
                        if key == "model":  ve += pd_[k]
                        if key == "oracle": ve += dvt[k]
                        if key == "zupt" and ps[k]: ve = 0.0
                        de += max(ve, 0.0)*STEP
                    acc[key][dist].append(abs(de-dt)/dt*100)
    for dist in DISTS:
        if not acc["coast"][dist]: continue
        rows.append(dict(driver=D, dist_m=dist, n=len(acc["coast"][dist]),
                         **{k: round(float(np.median(acc[k][dist])),2) for k in acc}))
T = pd.DataFrame(rows); T.to_csv(OUT/"drift_all_drivers.csv", index=False)

for D in ORDER:
    s = T[T.driver == D]
    if not len(s): continue
    print(f"\n  Driver {D} — {NAME[D]}")
    print(f"    {'distance':>10}{'coast':>9}{'+ZUPT':>9}{'model':>9}{'oracle':>9}{'best (m)':>11}")
    for _, r in s.iterrows():
        best = min(r.coast, r.zupt)
        tag = "  ✓ PASS" if best < 10 else ""
        print(f"    {int(r.dist_m):>8} m{r.coast:>8.1f}%{r.zupt:>8.1f}%{r.model:>8.1f}%"
              f"{r.oracle:>8.1f}%{r.dist_m*best/100:>10.1f}{tag}")

# ─────────────────────────── 3 · BENCHMARKS ───────────────────────────
banner("3 · PROBLEM STATEMENT BENCHMARKS")
print(f"  {'driver':<8}{'condition':<36}{'5 m / 50 m':>16}{'100 m / 1 km':>18}")
bench = []
for D in ORDER:
    s = T[T.driver == D].sort_values("dist_m")
    if not len(s): continue
    d50  = np.interp(50,   s.dist_m, s.coast)*0.5
    d1k  = np.interp(1000, s.dist_m, s.coast)*10
    bench.append(dict(driver=D, m50=d50, m1k=d1k))
    print(f"  {D:<8}{NAME[D]:<36}{d50:>10.1f} m {'PASS' if d50<5 else 'fail':<5}"
          f"{d1k:>12.1f} m {'PASS' if d1k<100 else 'fail':<5}")
B = pd.DataFrame(bench)
print(f"\n  5 m / 50 m benchmark: {int((B.m50<5).sum())}/{len(B)} drivers PASS")
best = B.loc[B.m1k.idxmin()]
print(f"  100 m / 1 km best: driver {best.driver} at {best.m1k:.1f} m "
      f"({'PASS' if best.m1k<100 else f'misses by {best.m1k-100:.1f} m'})")

# ─────────────────────────── 4 · FIGURES ───────────────────────────
banner("4 · FIGURES")
CLR = {"coast": "#1f4e79", "zupt": "#7c3aed", "model": "#c2410c", "oracle": "#15803d"}
LBL = {"coast": "coast (no AI)", "zupt": "coast + ZUPT (AI classifier)",
       "model": "ML speed model", "oracle": "oracle (true Δv)"}

fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
for ax, D in zip(axes.ravel(), ORDER):
    s = T[T.driver == D].sort_values("dist_m")
    for k in ("coast","zupt","model","oracle"):
        ax.plot(s.dist_m, s[k], "o-", color=CLR[k], lw=2, ms=5, label=LBL[k])
    ax.axhline(10, color="#dc2626", ls="--", lw=1.6, label="10% benchmark")
    ax.set_xlabel("blackout distance (m)"); ax.set_ylabel("drift (% of distance)")
    ax.set_title(f"Driver {D} — {NAME[D]}", fontsize=11.5, weight="bold")
    ax.set_ylim(0, 45); ax.grid(alpha=.25); ax.legend(fontsize=8, loc="upper left")
fig.suptitle("Positional drift vs blackout distance — each driver unseen by its model",
             fontsize=13.5, weight="bold")
fig.tight_layout(rect=[0,0,1,0.965]); fig.savefig(OUT/"plots/01_drift_percent.png", dpi=150)
plt.close(fig); print("  01_drift_percent.png")

fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
for ax, D in zip(axes.ravel(), ORDER):
    s = T[T.driver == D].sort_values("dist_m")
    for k in ("coast","model","oracle"):
        ax.plot(s.dist_m, s.dist_m*s[k]/100, "o-", color=CLR[k], lw=2, ms=5, label=LBL[k])
    xs = np.array([0, 1600]); ax.plot(xs, xs*0.10, "--", color="#dc2626", lw=1.6, label="10% budget")
    ax.scatter([50,1000], [5,100], color="#dc2626", s=60, marker="s", zorder=5, label="PS targets")
    ax.set_xlabel("blackout distance (m)"); ax.set_ylabel("drift (metres)")
    ax.set_title(f"Driver {D} — {NAME[D]}", fontsize=11.5, weight="bold")
    ax.set_ylim(0, 320); ax.set_xlim(0, 1600); ax.grid(alpha=.25); ax.legend(fontsize=8, loc="upper left")
fig.suptitle("Positional drift in metres, against the two problem-statement targets",
             fontsize=13.5, weight="bold")
fig.tight_layout(rect=[0,0,1,0.965]); fig.savefig(OUT/"plots/02_drift_metres.png", dpi=150)
plt.close(fig); print("  02_drift_metres.png")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.6))
x = np.arange(len(B))
c1 = ["#15803d" if v < 5 else "#c2410c" for v in B.m50]
a1.bar(x, B.m50, color=c1, width=.55)
a1.axhline(5, color="#dc2626", ls="--", lw=2, label="5 m budget")
for i, v in enumerate(B.m50): a1.text(i, v+.12, f"{v:.1f} m", ha="center", fontsize=10, weight="bold")
a1.set_xticks(x); a1.set_xticklabels([f"Driver {d}" for d in B.driver])
a1.set_ylabel("drift (m)"); a1.set_title("Benchmark 1 — 5 m over 50 m", fontsize=12, weight="bold")
a1.set_ylim(0, 6.5); a1.legend(); a1.grid(axis="y", alpha=.25)
c2 = ["#15803d" if v < 100 else "#c2410c" for v in B.m1k]
a2.bar(x, B.m1k, color=c2, width=.55)
a2.axhline(100, color="#dc2626", ls="--", lw=2, label="100 m budget")
for i, v in enumerate(B.m1k): a2.text(i, v+3, f"{v:.0f} m", ha="center", fontsize=10, weight="bold")
a2.set_xticks(x); a2.set_xticklabels([f"Driver {d}" for d in B.driver])
a2.set_ylabel("drift (m)"); a2.set_title("Benchmark 2 — 100 m over 1 km", fontsize=12, weight="bold")
a2.set_ylim(0, 220); a2.legend(); a2.grid(axis="y", alpha=.25)
fig.suptitle("Both benchmarks, all drivers   (green = pass)", fontsize=13.5, weight="bold")
fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig(OUT/"plots/03_benchmark_bars.png", dpi=150)
plt.close(fig); print("  03_benchmark_bars.png")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2))
a1.bar(np.arange(len(C)), C.accuracy*100, color="#15803d", width=.55)
a1.axhline(meta["naive_threshold_accuracy"]*100, color="#c2410c", ls="--", lw=2,
           label=f"naive threshold {meta['naive_threshold_accuracy']:.1%}")
for i, v in enumerate(C.accuracy): a1.text(i, v*100+.15, f"{v:.1%}", ha="center", fontsize=10, weight="bold")
a1.set_xticks(np.arange(len(C))); a1.set_xticklabels([f"held out {d}" for d in C.driver])
a1.set_ylim(85, 101); a1.set_ylabel("accuracy (%)"); a1.legend(fontsize=9); a1.grid(axis="y", alpha=.25)
a1.set_title("Motion classifier — leave-one-driver-out", fontsize=12, weight="bold")
tot = sum(cms.values())
a2.imshow(tot/tot.sum(axis=1, keepdims=True), cmap="Greens", vmin=0, vmax=1)
for i in range(2):
    for j in range(2):
        a2.text(j, i, f"{tot[i,j]:,}\n{tot[i,j]/tot[i].sum():.1%}", ha="center", va="center",
                fontsize=12, weight="bold", color="white" if i == j else "#333")
a2.set_xticks([0,1]); a2.set_xticklabels(["predicted\nstationary","predicted\nmoving"])
a2.set_yticks([0,1]); a2.set_yticklabels(["actually\nstationary","actually\nmoving"])
a2.set_title("Confusion matrix — all held-out folds pooled", fontsize=12, weight="bold")
fig.tight_layout(); fig.savefig(OUT/"plots/04_classifier.png", dpi=150)
plt.close(fig); print("  04_classifier.png")

banner(f"DONE in {time.time()-t0:.0f}s   —   results in out/")
