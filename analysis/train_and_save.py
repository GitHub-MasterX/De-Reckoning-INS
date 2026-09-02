"""
Train the motion classifier ONCE and save everything to models/.
After this, nothing needs retraining — analysis/load_model.py loads and scores in seconds.

Saves:
  models/motion_classifier.pkl   trained on ALL drivers  (the deployment model)
  models/motion_folds.pkl        the 4 leave-one-driver-out models (reproduces the 99.4% table)
  models/features_motion.npz     extracted features, so parquet is never re-read
  models/metadata.json           feature names, config, and the scores this run produced
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, joblib, json, time
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import confusion_matrix

CLEAN = Path("data/clean"); MODELS = Path("models"); MODELS.mkdir(exist_ok=True)
FS, W, HOP = 10.0, 20, 5

FEATURE_NAMES = (
    ["acc_mag_mean","acc_mag_std","acc_mag_min","acc_mag_max","acc_mag_absdiff",
     "gyr_mag_mean","gyr_mag_std","gyr_mag_max"]
    + [f"{s}_{ax}" for ax in "xyz" for s in ("acc_std","acc_absdiff","gyr_std")]
    + [f"band_{ax}_{b}" for ax in "xyz" for b in ("0.5-1.5Hz","1.5-3Hz","3-5Hz")]
)

def feats(a, g):
    """26 features from one 2-second window of accelerometer + gyroscope.
    This definition is the contract — any port must reproduce it exactly."""
    am = np.linalg.norm(a, axis=1); gm = np.linalg.norm(g, axis=1)
    f = [am.mean(), am.std(), am.min(), am.max(), np.abs(np.diff(am)).mean(),
         gm.mean(), gm.std(), gm.max()]
    for c in range(3):
        f += [a[:, c].std(), np.abs(np.diff(a[:, c])).mean(), g[:, c].std()]
    for c in range(3):
        P = np.abs(np.fft.rfft(a[:, c] - a[:, c].mean()))**2
        fr = np.fft.rfftfreq(W, 1/FS)
        for lo, hi in ((0.5, 1.5), (1.5, 3.0), (3.0, 5.0)):
            f.append(np.log(P[(fr >= lo) & (fr < hi)].sum() + 1e-9))
    return f

t0 = time.time()
A = pd.read_csv("data/alignment.csv")
sel = A[(A.sync_r.abs() >= 0.40) & A.sync_r.notna()]
sel = sel[sel.drive != "Vtb1"]                       # stress drive, never trained on

X, Y, D, RPM = [], [], [], []
for _, r in sel.iterrows():
    d = pd.read_parquet(CLEAN / f"{r.drive}.parquet")
    d = d[(d.session == r.session) & d.aligned_valid].reset_index(drop=True)
    if len(d) < 3000: continue
    a = d[["ax","ay","az"]].to_numpy(); g = d[["gx_c","gy_c","gz_c"]].to_numpy()
    v = d.speed_best_al.to_numpy(); rpm = d.engine_rpm.to_numpy()
    ok = np.isfinite(a).all(1) & np.isfinite(g).all(1) & np.isfinite(v)
    a, g, v, rpm = a[ok], g[ok], v[ok], rpm[ok]
    if len(v) < 3000: continue
    for i in range(0, len(v) - W, HOP):
        vm = v[i:i+W]
        if   vm.max() < 1.0: lab = 0        # stationary
        elif vm.min() > 5.0: lab = 1        # moving
        else: continue                      # ambiguous — excluded
        X.append(feats(a[i:i+W], g[i:i+W])); Y.append(lab); D.append(r.driver)
        RPM.append(float(np.nanmean(rpm[i:i+W])) if np.isfinite(rpm[i:i+W]).any() else np.nan)

X = np.array(X, dtype=np.float32); Y = np.array(Y, dtype=np.int8)
D = np.array(D); RPM = np.array(RPM, dtype=np.float32)
np.savez_compressed(MODELS/"features_motion.npz", X=X, Y=Y, D=D, RPM=RPM,
                    feature_names=np.array(FEATURE_NAMES))
t_feat = time.time() - t0
print(f"features: {X.shape[0]:,} windows x {X.shape[1]} features   ({t_feat:.0f}s)")
print(f"  stationary {int((Y==0).sum()):,} ({100*(Y==0).mean():.1f}%)   moving {int((Y==1).sum()):,}\n")

# ---- leave-one-driver-out, the honest validation ----
folds, scores = {}, {}
print("training leave-one-driver-out")
for h in ["A","B","D","E"]:
    tr, te = D != h, D == h
    if te.sum() < 200 or len(np.unique(Y[tr])) < 2: continue
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, random_state=0)
    m.fit(X[tr], Y[tr])
    p = m.predict(X[te]); yt = Y[te]
    cm = confusion_matrix(yt, p, labels=[0,1])
    idle = (yt == 0) & (RPM[te] > 400)
    scores[h] = dict(n_test=int(te.sum()), accuracy=float((p == yt).mean()),
                     stationary_recall=float(cm[0,0]/max(cm[0].sum(),1)),
                     stationary_precision=float(cm[0,0]/max(cm[:,0].sum(),1)),
                     idling_recall=float((p[idle] == 0).mean()) if idle.sum() > 30 else None)
    folds[h] = m
    print(f"  held out {h}: acc {scores[h]['accuracy']:.1%}  "
          f"stat-recall {scores[h]['stationary_recall']:.1%}")
joblib.dump(folds, MODELS/"motion_folds.pkl", compress=3)

# ---- deployment model: trained on everything ----
deploy = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, random_state=0)
deploy.fit(X, Y)
joblib.dump(deploy, MODELS/"motion_classifier.pkl", compress=3)

naive = (X[:, 1] > np.median(X[Y == 1, 1]) * 0.5).astype(int)
meta = dict(
    model="HistGradientBoostingClassifier", max_iter=300, learning_rate=0.08, random_state=0,
    window_seconds=W/FS, hop_seconds=HOP/FS, sample_rate_hz=FS,
    classes={"0": "stationary", "1": "moving"},
    input_channels=["ax","ay","az","gx_c","gy_c","gz_c"],
    n_features=X.shape[1], feature_names=FEATURE_NAMES,
    n_windows=int(X.shape[0]), n_stationary=int((Y==0).sum()), n_moving=int((Y==1).sum()),
    excluded_drives=["Vtb1"], sync_threshold=0.40,
    loo_scores=scores,
    mean_loo_accuracy=float(np.mean([s["accuracy"] for s in scores.values()])),
    naive_threshold_accuracy=float((naive == Y).mean()),
    feature_extraction_seconds=round(t_feat, 1),
)
(MODELS/"metadata.json").write_text(json.dumps(meta, indent=2))

print(f"\nmean LOO accuracy: {meta['mean_loo_accuracy']:.1%}  "
      f"(naive threshold {meta['naive_threshold_accuracy']:.1%})")
print(f"total {time.time()-t0:.0f}s")
for f in sorted(MODELS.iterdir()):
    print(f"  {f.name:28s} {f.stat().st_size/1024:8.1f} KB")
