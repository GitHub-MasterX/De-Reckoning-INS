"""Phone · the stationary classifier, exported for the Android app exactly as trained — nothing is refitted.

The model is round 1's `deploy_all` HistGradientBoostingClassifier (models/motion_models.pkl, trained on all four
drivers). Its trees are written to a small binary file the app reads, and a fixture of real IO-VNBD windows is
written with scikit-learn's own features and decisions, so the app's unit tests check the Kotlin port against them.

  model    round2/android/app/src/main/assets/live/motion_deploy_all.hgb
  fixture  round2/android/app/src/test/resources/motion_fixture.bin

Model file, little-endian:  "HGB1", n_features i32, n_trees i32, baseline f64, then per tree n_nodes i32 and per node
feature i32, threshold f64, left i32, right i32, is_leaf i8, missing_go_to_left i8, value f64.
A window is stationary when the summed raw score is <= 0 (predict_proba <= 0.5 picks class 0, "stationary").

Fixture file, little-endian:  "MFX1", n i32, then per window acc 20x3 f64, gyr 20x3 f64, features 26 f32, raw f64,
stationary i8.

Run from the repo root:  .venv/bin/python3 round2/phone/export_motion_model.py"""
import sys
import struct
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
R2 = ROOT/"round2"
sys.path.insert(0, str(R2))
sys.path.insert(0, str(ROOT))
from core import motion, sessions

APP = ROOT/"front-end/android/app/src"
MODEL_OUT = APP/"main/assets/live/motion_deploy_all.hgb"
FIXTURE_OUT = APP/"test/resources/motion_fixture.bin"
PER_SESSION = 250            # windows drawn from each fixture session
rng = np.random.default_rng(0)

clf = motion.models()["deploy_all"]
trees = [p[0].nodes for p in clf._predictors]
assert all(len(p) == 1 for p in clf._predictors), "binary model: one tree per iteration"
assert not any(t["is_categorical"].any() for t in trees)
baseline = float(clf._baseline_prediction.ravel()[0])


def raw_score(X):
    """The exported trees walked by hand, as the app walks them."""
    out = np.full(len(X), baseline)
    for nodes in trees:
        for r, x in enumerate(X):
            k = 0
            while not nodes["is_leaf"][k]:
                v = float(x[nodes["feature_idx"][k]])
                go_left = bool(nodes["missing_go_to_left"][k]) if np.isnan(v) else v <= nodes["num_threshold"][k]
                k = int(nodes["left"][k] if go_left else nodes["right"][k])
            out[r] += float(nodes["value"][k])
    return out


MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(MODEL_OUT, "wb") as f:
    f.write(b"HGB1")
    f.write(struct.pack("<iid", clf.n_features_in_, len(trees), baseline))
    for nodes in trees:
        f.write(struct.pack("<i", len(nodes)))
        for n in nodes:
            f.write(struct.pack("<idiibbd", int(n["feature_idx"]), float(n["num_threshold"]), int(n["left"]),
                                int(n["right"]), int(n["is_leaf"]), int(n["missing_go_to_left"]), float(n["value"])))
print(f"model: {len(trees)} trees, {sum(len(t) for t in trees):,} nodes, baseline {baseline:.6f} -> "
      f"{MODEL_OUT.relative_to(ROOT)} ({MODEL_OUT.stat().st_size/1e3:.0f} kB)")

# fixture: real windows from one session of each driver, half of them from stops where there are any
acc_w, gyr_w = [], []
for _, r in sessions.selected().drop_duplicates("driver").iterrows():
    S = sessions.load(r.drive, r.driver, int(r.session))
    starts = motion.window_starts(len(S.t))
    stopped = starts[S.v[starts + 10] < 0.3]
    moving = starts[S.v[starts + 10] >= 0.3]
    pick = np.r_[rng.choice(stopped, min(len(stopped), PER_SESSION//2), replace=False),
                 rng.choice(moving, PER_SESSION - min(len(stopped), PER_SESSION//2), replace=False)]
    idx = pick[:, None] + np.arange(motion.WINDOW_SAMPLES)[None, :]
    acc_w.append(S.acc[idx]); gyr_w.append(S.gyr[idx])
    print(f"  {r.driver} {r.drive} s{int(r.session)}: {len(pick)} windows ({min(len(stopped), PER_SESSION//2)} at stops)")
acc_w, gyr_w = np.concatenate(acc_w), np.concatenate(gyr_w)
starts = np.arange(len(acc_w))*motion.WINDOW_SAMPLES                  # the windows laid end to end
features = motion.features_batch(acc_w.reshape(-1, 3), gyr_w.reshape(-1, 3), starts)
raw = clf._raw_predict(features).ravel()
stationary = clf.predict(features) == 0

hand = raw_score(features)
assert np.array_equal(stationary, hand <= 0), "hand-walked trees disagree with predict()"
print(f"fixture: {len(features)} windows, {stationary.sum()} stationary; hand-walked raw score against "
      f"scikit-learn: largest gap {np.max(np.abs(hand - raw)):.2e}, decisions identical")

FIXTURE_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(FIXTURE_OUT, "wb") as f:
    f.write(b"MFX1")
    f.write(struct.pack("<i", len(features)))
    for k in range(len(features)):
        f.write(acc_w[k].astype("<f8").tobytes())
        f.write(gyr_w[k].astype("<f8").tobytes())
        f.write(features[k].astype("<f4").tobytes())
        f.write(struct.pack("<db", float(raw[k]), int(stationary[k])))
print(f"-> {FIXTURE_OUT.relative_to(ROOT)} ({FIXTURE_OUT.stat().st_size/1e6:.1f} MB)")
