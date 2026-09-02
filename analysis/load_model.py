"""
Load the saved model and reproduce the results — no retraining, no parquet reading.
This is what you run on the spot.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, joblib, json, time
from pathlib import Path
from sklearn.metrics import confusion_matrix

t0 = time.time()
M = Path("models")
models = joblib.load(M/"motion_models.pkl")        # every regime, one file
clf    = models["deploy_all"]                      # ship this; never quote its own score
folds  = {d: models[f"{d}_holdout"] for d in "ABDE" if f"{d}_holdout" in models}
meta  = json.loads((M/"metadata.json").read_text())
z     = np.load(M/"features_motion.npz", allow_pickle=True)
X, Y, D, RPM = z["X"], z["Y"], z["D"], z["RPM"]
t_load = time.time() - t0

print(f"loaded in {t_load:.2f} s   —   {X.shape[0]:,} windows x {X.shape[1]} features\n")
print("REPRODUCING THE LEAVE-ONE-DRIVER-OUT TABLE FROM DISK\n")
print(f"  {'held out':<10}{'n test':>9}{'accuracy':>11}{'stat recall':>13}{'stat prec':>11}{'idling recall':>15}")
accs = []
for h in ["A","B","D","E"]:
    if h not in folds: continue
    te = D == h
    p = folds[h].predict(X[te]); yt = Y[te]
    cm = confusion_matrix(yt, p, labels=[0,1])
    acc  = (p == yt).mean()
    rec  = cm[0,0]/max(cm[0].sum(),1)
    prec = cm[0,0]/max(cm[:,0].sum(),1)
    idle = (yt == 0) & (RPM[te] > 400)
    ir   = (p[idle] == 0).mean() if idle.sum() > 30 else float("nan")
    accs.append(acc)
    print(f"  {h:<10}{int(te.sum()):>9,}{acc:>10.1%}{rec:>13.1%}{prec:>11.1%}"
          + (f"{ir:>15.1%}" if np.isfinite(ir) else f"{'n/a':>15}"))

mean_acc = float(np.mean(accs))
print(f"\n  mean accuracy        : {mean_acc:.1%}")
print(f"  naive threshold      : {meta['naive_threshold_accuracy']:.1%}")
print(f"  gain from the model  : +{100*(mean_acc - meta['naive_threshold_accuracy']):.1f} points")

expected = meta["mean_loo_accuracy"]
match = abs(mean_acc - expected) < 1e-9
print(f"\n  metadata says {expected:.4%}, reloaded model gives {mean_acc:.4%}  "
      f"→ {'IDENTICAL' if match else 'MISMATCH'}")

print(f"\nDEPLOYMENT MODEL (trained on all drivers)")
p_all = clf.predict(X)
print(f"  in-sample accuracy   : {(p_all == Y).mean():.2%}   (not a validation number — "
      f"the honest figure is the {mean_acc:.1%} above)")
print(f"  predicts {X.shape[0]:,} windows in "
      f"{(lambda s: f'{s:.2f} s')(  __import__('timeit').timeit(lambda: clf.predict(X[:10000]), number=1) * X.shape[0]/10000 )}")
print(f"\ntotal wall time: {time.time()-t0:.2f} s")
