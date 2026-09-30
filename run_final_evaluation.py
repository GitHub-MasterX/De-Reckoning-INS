#!/usr/bin/env python3
"""Final model — one command, the real evaluation.

Runs the two scripts that actually produce every headline number in the project's README:

  1. analysis/Speed_Model/learned_speed_model.py --stage test
     The learned speed model, scored on drivers D and E (never used to tune anything).
     Produces the 3.15 vs 6.09 m/s speed-error numbers.

  2. analysis/Reporting_Metrics/reporting_layer.py --stage test
     The full merged engine — classifier, learned speed, road-constrained particle filter,
     and the reporting layer (mode hysteresis + speed-limited cursor) — on the same test
     drivers. Produces the 5.9% median / 80-82% under 10% numbers.

Both are run fresh, not read from a cache, so what this script prints is a live reproduction,
not a claim. A summary transcript is also written to outputs/Results/final_evaluation_summary.txt.

This replaces run_evaluation.py, which only ever evaluated round 1's motion classifier in
isolation — it never ran the particle filter, the map, the learned speed model, or the
reporting layer, so it was never actually the final model's evaluation.

Usage:
    .venv/bin/python3 run_final_evaluation.py               # full test set (2,421 blackouts)
    .venv/bin/python3 run_final_evaluation.py --limit 300    # a quick subset, for a fast check
"""
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def arg(flag, default):
    return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default


def banner(title):
    print(f"\n{'=' * 100}\n{title}\n{'=' * 100}")


def run(script, extra_args, log_lines):
    """Run one evaluation script as a real subprocess, streaming its output live."""
    cmd = [PY, str(script), "--stage", "test"] + extra_args
    banner(f"Running: {' '.join(str(c) for c in cmd)}")
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print(line, end="")
        log_lines.append(line)
    proc.wait()
    if proc.returncode != 0:
        print(f"\n  FAILED (exit {proc.returncode}): {script}")
        sys.exit(proc.returncode)


def main():
    t0 = time.time()
    limit = arg("--limit", 0)
    extra = ["--limit", str(limit)] if limit else []
    log = []

    banner("FINAL MODEL EVALUATION — classifier + learned speed model + particle filter + reporting layer")
    print("Both stages run fresh against drivers D and E — never used to tune any setting.")

    run(ROOT / "analysis/Speed_Model/learned_speed_model.py", extra, log)
    run(ROOT / "analysis/Reporting_Metrics/reporting_layer.py", extra, log)

    # ---- pull the real numbers back out of what was just written, and print one clean summary ----
    speed = pd.read_parquet(ROOT / "outputs/Results/learned_speed_model_test.parquet")
    engine = pd.read_parquet(ROOT / "outputs/Results/reporting_layer_test.parquet")
    final = engine[engine.variant == "round 3 (chosen)"]
    predecessor = engine[engine.variant == "round 2 (as published)"]

    banner("FINAL SUMMARY — the numbers that appear in README.md")
    summary_lines = [
        f"{'Metric':<42}{'Predecessor engine':>22}{'Final engine':>18}",
        f"{'Path drift, median':<42}{predecessor.path.median():>21.1f}%{final.path.median():>17.1f}%",
        f"{'Blackouts meeting the 10% target':<42}{100*(predecessor.path < 10).mean():>21.0f}%{100*(final.path < 10).mean():>17.0f}%",
        f"{'Worst moment, median':<42}{predecessor.worst.median():>21.1f}%{final.worst.median():>17.1f}%",
        f"{'Blackouts that leave the driven road':<42}{100*predecessor.off.mean():>21.0f}%{100*final.off.mean():>17.0f}%",
        f"{'Cursor jumping between roads':<42}{100*(predecessor.jumps > 0).mean():>20.0f}%{100*(final.jumps > 0).mean():>17.0f}%",
        f"{'Slow driving (<40 km/h), path median':<42}{predecessor[predecessor.band=='slow'].path.median():>21.1f}%{final[final.band=='slow'].path.median():>17.1f}%",
        f"{'Speed prediction error (RMS)':<42}{speed.rms_held.median():>20.2f}m/s{speed.rms_model.median():>16.2f}m/s",
    ]
    for line in summary_lines:
        print(line)
        log.append(line + "\n")

    elapsed = time.time() - t0
    footer = f"\nDONE in {elapsed:.0f}s — {len(final)} test blackouts, drivers D and E, settings frozen from A and B."
    print(footer)
    log.append(footer + "\n")

    out_path = ROOT / "outputs/Results/final_evaluation_summary.txt"
    out_path.write_text("".join(log))
    print(f"Transcript written to {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
