"""
Three training regimes, from the same cached features. No parquet reads, no retraining later.

  1. E-HOLDOUT     train A+B+D, test E        -> the PS scenario, fully unseen
  2. SECOND-HOLDOUT train A+B+E, test D       -> a second completely unseen driver
  3. WITHIN-DRIVER train first 75% of every session, test last 25%
                   (split by TIME with a 30 s buffer, so overlapping windows cannot leak)
  4. DEPLOY        train on everything        -> ship this; never quote its own score
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, joblib, json
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import confusion_matrix

M = Path("models")
z = np.load(M/"features_motion.npz", allow_pickle=True)
X, Y, D, RPM = z["X"], z["Y"], z["D"], z["RPM"]
meta = json.loads((M/"metadata.json").read_text())
HOP_S = meta["hop_seconds"]

# window index within each driver's stream, used for the time-based 75/25 split
order = np.arange(len(Y))
pos = np.zeros(len(Y))
for d in np.unique(D):
    m = D == d
    pos[m] = np.linspace(0, 1, m.sum())          # 0 = start of that driver, 1 = end

def score(m, Xte, yte, rpm_te, name):
    p = m.predict(Xte)
    cm = confusion_matrix(yte, p, labels=[0,1])
    idle = (yte == 0) & (rpm_te > 400)
    return dict(name=name, n=int(len(yte)),
        accuracy=float((p == yte).mean()),
        stat_recall=float(cm[0,0]/max(cm[0].sum(),1)),
        stat_prec=float(cm[0,0]/max(cm[:,0].sum(),1)),
        idling_recall=float((p[idle]==0).mean()) if idle.sum()>30 else None)

def fit(mask_tr):
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, random_state=0)
    m.fit(X[mask_tr], Y[mask_tr]); return m

results, models = [], {}

# ---- 1. E held out entirely ----
tr = D != "E"; te = D == "E"
m = fit(tr); models["E_holdout"] = m
r = score(m, X[te], Y[te], RPM[te], "1. E held out  (train A+B+D)")
r["train_windows"] = int(tr.sum()); results.append(r)

# ---- 2. a second driver held out entirely ----
tr = D != "D"; te = D == "D"
m = fit(tr); models["D_holdout"] = m
r = score(m, X[te], Y[te], RPM[te], "2. D held out  (train A+B+E)")
r["train_windows"] = int(tr.sum()); results.append(r)

# ---- 3. within-driver 75/25, split by time with a buffer ----
BUF = 0.02                                        # ~2% gap, well over one window length
tr = pos < (0.75 - BUF); te = pos >= 0.75
m = fit(tr); models["within_75_25"] = m
r = score(m, X[te], Y[te], RPM[te], "3. within-driver 75/25")
r["train_windows"] = int(tr.sum()); results.append(r)

# per-driver breakdown of the within split
per_driver = {}
for d in ["A","B","D","E"]:
    sub = te & (D == d)
    if sub.sum() > 200:
        per_driver[d] = score(models["within_75_25"], X[sub], Y[sub], RPM[sub], d)

# ---- 4. deployment ----
models["deploy_all"] = fit(np.ones(len(Y), bool))

joblib.dump(models, M/"motion_models.pkl", compress=3)

print(f"{'regime':<34}{'train':>11}{'test':>10}{'accuracy':>11}{'stat recall':>13}{'idling':>10}")
for r in results:
    ir = f"{r['idling_recall']:.1%}" if r['idling_recall'] is not None else "n/a"
    print(f"  {r['name']:<32}{r['train_windows']:>10,}{r['n']:>10,}"
          f"{r['accuracy']:>10.1%}{r['stat_recall']:>13.1%}{ir:>10}")

print(f"\nwithin-driver 75/25, broken out by driver:")
for d, r in per_driver.items():
    print(f"  driver {d}: n={r['n']:>7,}  acc {r['accuracy']:.1%}  stat-recall {r['stat_recall']:.1%}")

meta["splits"] = {r["name"]: {k: v for k, v in r.items() if k != "name"} for r in results}
meta["within_split_per_driver"] = per_driver
meta["note_on_deploy"] = ("deploy_all is trained on every driver. Ship it; never quote its "
                          "in-sample score. The honest figures are the held-out ones above.")
(M/"metadata.json").write_text(json.dumps(meta, indent=2))
print(f"\nsaved models/motion_models.pkl  ({(M/'motion_models.pkl').stat().st_size/1024:.0f} KB) "
      f"— keys: {', '.join(models)}")
