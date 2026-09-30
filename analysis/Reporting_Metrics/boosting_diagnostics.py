"""Round 3 · diagnostics for the learned speed model's training mechanism.

Two things a professor is likely to ask for, made concrete rather than described:

  1. "Can you show the error going down as training progresses?"
     -> train_score_ / validation_score_, one value per boosting iteration (per tree added),
        recorded directly by sklearn when early_stopping + scoring="loss" are set.

  2. "Can you show what the model's prediction looks like at an intermediate stage,
     not just the final answer?"
     -> a manual staged-prediction reconstruction: sum the baseline plus the first k trees'
        contributions, for k = 1, 2, 3, ... n_iter_, for a handful of real held-out blackout rows.
        HistGradientBoostingRegressor doesn't expose staged_predict() (that's the older
        GradientBoostingRegressor API), so this walks its internal _predictors list directly.

This is NOT one of the deployed leave-one-session-out models used in the engine (learned_speed_model.py
trains one model per held-out session). It is the same architecture and same hyperparameters, trained
once on both tuning drivers (A, B) with a held-out validation slice, purely to make the training
mechanism visible. The deployed numbers (3.15 vs 6.09 m/s) come from learned_speed_model.py, not this file.

Run from the repo root:  .venv/bin/python3 round2/boosting_diagnostics.py
"""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"analysis/Speed_Model"))
sys.path.insert(0, str(ROOT/"analysis/Reporting_Metrics"))
from core import roadnet
from learned_speed_model import training_table
from accel_speed import TUNE

OUT = ROOT / "outputs" / "pptx_plots"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("Loading the same training table the deployed model uses (tuning drivers A + B)...")
    net = roadnet.RoadNetwork()
    D = training_table(net, TUNE)
    feats = [c for c in D.columns if c not in ("target", "group")]
    X = D[feats].to_numpy(float)
    y = D.target.to_numpy(float)
    print(f"{len(D):,} rows, {len(feats)} features: {feats}")

    # ---- 1. the real loss-vs-iteration curve --------------------------------------------------
    Xtr, Xval, ytr, yval = train_test_split(X, y, test_size=0.15, random_state=0)
    model = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.06, max_depth=6, l2_regularization=1.0,
        random_state=0, early_stopping=True, scoring="loss",
        validation_fraction=0.15, n_iter_no_change=300,  # never stop early — we want the full curve
    ).fit(Xtr, ytr)

    train_loss = -model.train_score_       # sklearn stores -loss for early-stopping's "higher is better"
    val_loss = -model.validation_score_
    iters = np.arange(len(train_loss))

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(iters, train_loss, label="training loss", color="#2e7d32")
    ax.plot(iters, val_loss, label="held-out validation loss", color="#c62828")
    ax.set_xlabel("Boosting iteration (trees added)")
    ax.set_ylabel("Squared-error loss")
    ax.set_title("Error reduction across training — same architecture as the deployed speed model")
    ax.legend()
    plt.tight_layout()
    fig.savefig(OUT / "boosting_loss_curve.png", dpi=150)
    print(f"saved {OUT/'boosting_loss_curve.png'}  "
          f"(loss {train_loss[0]:.2f} -> {train_loss[-1]:.2f} train, "
          f"{val_loss[0]:.2f} -> {val_loss[-1]:.2f} validation, {len(iters)} trees)")

    # ---- 2. staged prediction: watch the guess converge, tree by tree, for real rows ----------
    # HistGradientBoostingRegressor has no public staged_predict(); reconstruct it the supported way —
    # warm_start=True lets us re-fit the *same* model object with more trees each time, so calling
    # .predict() after each step is a real prediction from a model with exactly that many trees.
    n_show = 4
    rng = np.random.default_rng(0)
    rows = rng.choice(len(Xval), size=n_show, replace=False)
    Xshow = Xval[rows]

    checkpoints = [1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120, 180, 250, 300]
    ws_model = HistGradientBoostingRegressor(
        learning_rate=0.06, max_depth=6, l2_regularization=1.0, random_state=0,
        warm_start=True, max_iter=checkpoints[0],
    )
    staged = np.zeros((len(checkpoints), n_show))
    for i, k in enumerate(checkpoints):
        ws_model.max_iter = k
        ws_model.fit(Xtr, ytr)
        staged[i, :] = ws_model.predict(Xshow)
        print(f"  after {k:>3} trees: row1 pred {staged[i,0]*3.6:5.1f} km/h "
              f"(true {yval[rows[0]]*3.6:5.1f})")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i in range(n_show):
        ax.plot(checkpoints, staged[:, i]*3.6, marker="o", markersize=3,
                label=f"row {i+1} (true {yval[rows[i]]*3.6:.0f} km/h)")
        ax.axhline(yval[rows[i]]*3.6, color=ax.lines[-1].get_color(), linestyle=":", alpha=0.4)
    ax.set_xlabel("Boosting iteration (trees added so far)")
    ax.set_ylabel("Predicted speed (km/h)")
    ax.set_title("The model's own prediction, watched tree by tree (dotted = true speed)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(OUT / "boosting_staged_prediction.png", dpi=150)
    print(f"saved {OUT/'boosting_staged_prediction.png'}")

    # ---- 3. a tiny textual log of the numbers, for the write-up -------------------------------
    log_path = OUT / "boosting_diagnostics_log.txt"
    with open(log_path, "w") as f:
        f.write("Round 3 boosting diagnostics\n")
        f.write(f"Training rows: {len(D):,} (tuning drivers A + B only)\n")
        f.write(f"Trees fit: {len(iters)}\n")
        f.write(f"Training loss:   {train_loss[0]:.3f} -> {train_loss[-1]:.3f}\n")
        f.write(f"Validation loss: {val_loss[0]:.3f} -> {val_loss[-1]:.3f}\n")
        f.write("\nStaged prediction, 4 real held-out rows (km/h), by tree count:\n")
        f.write("  " + "".join(f"{f'@{k}t':>9}" for k in checkpoints) + "\n")
        for i in range(n_show):
            f.write(f"  row {i+1} (true {yval[rows[i]]*3.6:5.1f} km/h): "
                     + "".join(f"{staged[j,i]*3.6:9.1f}" for j in range(len(checkpoints))) + "\n")
    print(f"saved {log_path}")


if __name__ == "__main__":
    main()
