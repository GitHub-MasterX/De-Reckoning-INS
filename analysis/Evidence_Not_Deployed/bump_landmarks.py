"""Round 3 · Indian road furniture as landmarks — detected bumps, and the ones the map never knew about.

A speed breaker is the ideal dead-reckoning landmark: it is a *point*, it is violent enough to see in a 248 Hz
accelerometer, and unlike a bend it is not shared with the service road running alongside. India has them everywhere.
OpenStreetMap has 17 of them in the whole area of our rides.

So this does two things:

  1  detect     a bump detector on the raw accelerometer: the vertical axis, band-passed, against a rolling background
  2  self-map   the rides cover the same corridor twice, out and back. A bump found on both runs, at the same place, is
                a real landmark that nobody mapped — a "pseudo marker". Their density is what decides whether this is
                worth anything, and it is measured here rather than assumed.
  3  value      what an along-track fix at each landmark would be worth inside a blackout

Run from the repo root:  .venv/bin/python3 round2/bump_landmarks.py
Output: round2/out/bump_landmarks_run.txt
"""
import warnings; warnings.filterwarnings("ignore")
import gzip, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"analysis/Speed_Model"))
sys.path.insert(0, str(ROOT/"analysis/Reporting_Metrics"))
sys.path.insert(0, str(ROOT/"front-end/android/App_Export"))
from trichy_learned_speed import load_segment, blackouts, SEG, FLOOR_M
from core.Engine.geo import enu

T0 = time.time()
R = 6371000.0
MATCH_M = 20.0            # two detections this close are the same piece of road furniture
MIN_SPEED = 2.0
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*100}\n{t}\n{'='*100}")


def raw_stream(path):
    t, a = [], []
    with gzip.open(path, "rt") as f:
        for line in f:
            if line[0] == "A":
                p = line.split(",")
                t.append(int(p[1])); a.append((float(p[2]), float(p[3]), float(p[4])))
    return np.array(t)/1e9, np.array(a)


def detect_bumps(t, acc, min_gap_s=1.0):
    """Jolts: the force along gravity, high-passed, where the short-term energy leaps above its own background.

    Gravity is the slow part of the reading, so the vertical axis is found by smoothing the vector itself; what is
    left after removing the slow part is the shaking, and a bump is a burst of it.
    """
    n = len(t)
    if n < 1000:
        return np.zeros(0), np.zeros(0)
    fs = 1.0/np.median(np.diff(t))
    win = max(3, int(round(fs*0.4)))                      # 0.4 s: gravity and body motion
    ker = np.ones(win)/win
    slow = np.vstack([np.convolve(acc[:, k], ker, mode="same") for k in range(3)]).T
    up = slow/np.maximum(np.linalg.norm(slow, axis=1)[:, None], 1e-6)
    vert = np.einsum("ij,ij->i", acc, up)                 # the force along gravity, still with g in it
    jolt = vert - np.convolve(vert, ker, mode="same")     # remove the slow part: what is left is the jolt
    energy = np.convolve(jolt**2, np.ones(max(3, int(fs*0.15)))/max(3, int(fs*0.15)), mode="same")
    bg = pd.Series(energy).rolling(int(fs*20), min_periods=int(fs*2), center=True).median().to_numpy()
    score = energy/np.maximum(bg, 1e-6)
    peaks = []
    k = 0
    gap = int(fs*min_gap_s)
    while k < n:
        if score[k] > 12.0:                               # a burst an order of magnitude above the background
            j = k + int(np.argmax(score[k:k + gap]))
            peaks.append(j)
            k = j + gap
        else:
            k += 1
    idx = np.array(peaks, int)
    return t[idx] if len(idx) else np.zeros(0), score[idx] if len(idx) else np.zeros(0)


def positions(S, times):
    """Where the vehicle was at each detection, and how fast."""
    lat = np.interp(times, S["t"], S["lat"]); lon = np.interp(times, S["t"], S["lon"])
    v = np.interp(times, S["t"], S["v"]); dist = np.interp(times, S["t"], S["dist"])
    return lat, lon, v, dist


def main():
    head("Round 3 · bumps as landmarks, and the ones nobody mapped")
    segs, det = {}, {}
    for n, fn in SEG.items():
        S = load_segment(ROOT/"data/phone_data/segments"/fn)
        t, acc = raw_stream(ROOT/"data/phone_data/segments"/fn)
        bt, sc = detect_bumps(t, acc)
        lat, lon, v, dist = positions(S, bt)
        keep = v > MIN_SPEED
        segs[n] = S
        det[n] = dict(t=bt[keep], score=sc[keep], lat=lat[keep], lon=lon[keep], v=v[keep], dist=dist[keep])
        km = S["dist"][-1]/1000
        log(f"segment {n}: {len(bt[keep])} jolts over {km:.1f} km while moving = {len(bt[keep])/km:.1f} per km")

    head("1 · do the same jolts appear on both runs of the same corridor?")
    A, B = det[1], det[3]
    k = np.cos(np.radians(segs[1]["lat"].mean()))
    ax, ay = np.radians(A["lon"])*R*k, np.radians(A["lat"])*R
    bx, by = np.radians(B["lon"])*R*k, np.radians(B["lat"])*R
    pairs = []
    for i in range(len(ax)):
        if len(bx) == 0:
            break
        d = np.hypot(bx - ax[i], by - ay[i])
        j = int(d.argmin())
        if d[j] <= MATCH_M:
            pairs.append((i, j, float(d[j])))
    print(f"  outbound jolts: {len(ax)}   return jolts: {len(bx)}")
    print(f"  jolts found at the same place on both runs (within {MATCH_M:.0f} m): {len(pairs)}")
    if pairs:
        dd = np.array([p[2] for p in pairs])
        km = min(segs[1]['dist'][-1], segs[3]['dist'][-1])/1000
        print(f"  they repeat to {np.median(dd):.0f} m (p90 {np.percentile(dd, 90):.0f} m)")
        print(f"  that is {len(pairs)/km:.2f} confirmed landmarks per km of corridor, from two passes")
        print(f"  for comparison, OpenStreetMap has 17 speed breakers in the whole area — about 0.5 per km")

    head("2 · what a landmark fix would be worth inside a blackout")
    S3 = segs[3]
    bl = blackouts(S3)
    lm_dist = np.array([S3["dist"][int(np.argmin(np.abs(S3["t"] - B["t"][j])))] for _, j, _ in pairs]) if pairs else np.zeros(0)
    rows = []
    for i, j in bl:
        d0, d1 = S3["dist"][i], S3["dist"][j]
        inside = ((lm_dist > d0 + FLOOR_M) & (lm_dist < d1)).sum()
        rows.append(dict(landmarks=int(inside), metres=float(d1 - d0)))
    P = pd.DataFrame(rows)
    print(f"  {len(P)} blackouts on the return ride")
    print(f"  blackouts containing at least one confirmed landmark: {100*(P.landmarks > 0).mean():.0f}%")
    print(f"  average landmarks per blackout: {P.landmarks.mean():.1f}")
    print(f"  with one landmark, the along-track error resets to the landmark's own spread (~{np.median([p[2] for p in pairs]) if pairs else 0:.0f} m),")
    print(f"  which for a 1 km blackout is about {100*(np.median([p[2] for p in pairs]) if pairs else 0)/1000:.1f}% error at that moment")
    head("3 · how good are the detections themselves?")
    for n in (1, 3):
        v = det[n]["v"]
        if len(v):
            print(f"  segment {n}: jolts detected at {3.6*np.median(v):.0f} km/h median speed, "
                  f"score {np.median(det[n]['score']):.0f}x background (p90 {np.percentile(det[n]['score'], 90):.0f}x)")


if __name__ == "__main__":
    main()
