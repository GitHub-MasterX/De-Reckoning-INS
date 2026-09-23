"""Round 3 · measurement 1 — can the map's own curvature give speed?

The idea. During a blackout the engine has no speed sensor it trusts, so it holds the last GNSS speed; on a road that
slows down or speeds up, that error accumulates along the road and the map cannot see it (a map fixes position across a
road, not along it). But whenever the road bends, geometry gives speed for free:

    turn rate (gyro, calibrated)  =  speed  x  curvature of the road being driven          omega = v * kappa
    so                               speed  =  turn rate / curvature                       v = omega / kappa

No accelerometer, no mount, no gravity: only the gyro we already calibrate, and the shape of the road in OSM.

What this script measures, honestly:
  * how often a usable reading exists (the road bends enough and the gyro is turning enough),
  * how accurate those readings are against the vehicle's true speed,
  * what holding the last reading (instead of the last GNSS speed) would do to the speed error over a blackout,
  * the distance error each would give if integrated blindly.

Upper bound, stated plainly: curvature is taken at the TRUE position, i.e. as if the filter always knew which road it
was on. Inside the particle filter each particle would use the road under itself, so the real gain is lower. This
number decides whether it is worth building, nothing more.

Only the tuning drivers (A, B) are used — the test drivers stay untouched (round2/DECISIONS.md).

Outputs: round2/out/round3_curve_speed.parquet, round2/out/round3_curve_speed_run.txt.
Run from the repo root:  .venv/bin/python3 round2/round3_curve_speed.py [--blackouts 200]
"""
import warnings; warnings.filterwarnings("ignore")
import argparse, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parent
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, calibration, engine_input, roadnet

T0 = time.time()
TUNE = ["A", "B"]
CHOICE = (R2/"out/calibration_choice.txt").read_text().strip()

# A reading is only taken when the road really bends and the gyro really turns: below these the ratio is noise.
KAPPA_MIN = 1/600.0          # rad/m — a 600 m radius bend, about 0.1 rad/s at 60 km/h
OMEGA_MIN = 0.015            # rad/s
WINDOWS_M = (60.0, 150.0)    # curvature measured over this much road, centred on the vehicle (two windows tried)
SMOOTH_S = 2.0               # the gyro is averaged over this before being compared with a road-length average
MATCH_RADIUS_M = 20.0
V_MIN, V_MAX = 2.0, 45.0     # m/s: readings outside this are dropped as nonsense

def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*112}\n{t}\n{'='*112}")


class Curvature:
    """Curvature of the road at a matched point, from the network's own geometry.

    OSM stores a road as a chain of straight segments (median 13 m). Walking that chain forward and backward from the
    vehicle for WINDOW_M/2 each way and dividing the total change of bearing by the distance walked gives the curvature
    of the road there, signed clockwise — the same sense as the gyro's calibrated turn rate. At a junction the walk
    follows the straightest continuation, which is what a vehicle driving on does.
    """

    def __init__(self, roads):
        self.r = roads

    def _forward(self, edge, limit_m):
        """Follow the road ahead of a directed edge for limit_m, taking the straightest continuation at junctions.

        Returns the bearing of the road where the walk stopped and how far it walked. The straightest continuation is
        what a vehicle driving along a road does; at a real junction (a turn of more than 60 degrees is the only way on)
        the walk stops, so a junction turn gives no curvature reading rather than a wrong one.
        """
        r = self.r
        e, walked = int(edge), 0.0
        bearing = float(r.edge_bearing[e])
        for _ in range(40):
            if walked >= limit_m:
                break
            node = int(r.edge_to[e])
            best, best_turn = -1, np.inf
            for k in range(r.out_ptr[node], r.out_ptr[node + 1]):
                f = int(r.out_edges[k])
                if f == int(r.edge_rev[e]):
                    continue                                   # not straight back the way we came
                turn = abs(roadnet.wrap(r.edge_bearing[f] - r.edge_bearing[e]))
                if turn < best_turn:
                    best, best_turn = f, turn
            if best < 0 or best_turn > np.radians(60):
                break                                          # a dead end or a real junction: stop here
            e = best
            walked += float(r.seg_len[r.edge_seg[e]])
            bearing = float(r.edge_bearing[e])
        return bearing, walked

    def _walk(self, edge, limit_m, forward):
        """The same walk backwards is the forward walk along the reverse edge, with the bearing turned around."""
        if forward:
            return self._forward(edge, limit_m)
        rev = int(self.r.edge_rev[int(edge)])
        if rev < 0:
            return float(self.r.edge_bearing[int(edge)]), 0.0
        b, walked = self._forward(rev, limit_m)
        return float(roadnet.wrap(b + np.pi)), walked

    def at(self, seg, dirn, window_m):
        """Signed curvature, rad/m, clockwise positive; NaN when the road cannot be followed far enough."""
        edge = int(self.r.edge_of(seg, dirn))
        if edge < 0:
            return np.nan
        b_ahead, d_ahead = self._walk(edge, window_m/2, forward=True)
        b_back, d_back = self._walk(edge, window_m/2, forward=False)
        span = d_ahead + d_back + float(self.r.seg_len[self.r.edge_seg[edge]])
        if d_ahead < window_m/4 or d_back < window_m/4 or span <= 0:
            return np.nan
        return float(roadnet.wrap(b_ahead - b_back))/span


def rows_for(S, C, bl):
    """One blackout: the engine's calibrated turn rate, and the truth used only for scoring."""
    i = int(bl.row_start)
    j = int(bl.end_1000)
    calib = calibration.engine_calibration(C, i, CHOICE)
    if calib is None:
        return None
    inp = engine_input.build(S, calib, i, j)
    k = slice(i, j + 1)
    return dict(t=inp.t, omega=inp.turn_rate(), v_true=S.v[k], lat=S.lat[k], lon=S.lon[k],
                heading=np.radians(S.heading[k]), speed0=float(S.v[i]))


def main(n_blackouts):
    head("Round 3 · can the map's curvature give speed?  (tuning drivers A and B only)")
    print(f"reading at |curvature| >= 1/{1/KAPPA_MIN:.0f} m and |turn rate| >= {OMEGA_MIN} rad/s, "
          f"curvature over {WINDOWS_M[0]:.0f} m and {WINDOWS_M[1]:.0f} m of road; "
          f"curvature taken at the TRUE position (an upper bound)")

    BL = pd.read_parquet(R2/"out/blackouts.parquet")
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()]
    rng = np.random.default_rng(3)
    take = rng.permutation(len(BL))[:n_blackouts]
    BL = BL.iloc[np.sort(take)]
    log(f"{len(BL)} blackouts from {BL.groupby(['drive','session']).ngroups} sessions")

    roads = roadnet.RoadNetwork()
    curve = Curvature(roads)
    log(f"road network: {len(roads.seg_len):,} segments")

    out = []
    S = C = None
    key = None
    for _, bl in BL.iterrows():
        k = (bl.drive, int(bl.session))
        if k != key:
            S = sessions.load(bl.drive, bl.driver, int(bl.session))
            C = calibration.Calibrator(S)
            key = k
            log(f"  {bl.drive} s{bl.session} ({bl.driver})")
        r = rows_for(S, C, bl)
        if r is None:
            continue
        x, y = roadnet.xy(r["lat"], r["lon"])
        m = roads.match(x, y, r["heading"], radius=MATCH_RADIUS_M)
        seg, dirn = m["seg"], m["dir"]
        kap = {w: np.full(len(x), np.nan) for w in WINDOWS_M}
        # curvature changes slowly: compute it every 10th row (1 s) and hold it between
        for p in range(0, len(x), 10):
            if seg[p] >= 0:
                for w in WINDOWS_M:
                    kap[w][p:p + 10] = curve.at(seg[p], dirn[p], w)
        kappa = kap[WINDOWS_M[0]]
        # the gyro averaged over SMOOTH_S, so it describes a stretch of road rather than an instant
        n_s = max(1, int(round(SMOOTH_S*10)))
        omega_s = pd.Series(r["omega"]).rolling(n_s, center=True, min_periods=1).mean().to_numpy()
        v_read = np.where(np.abs(kappa) >= KAPPA_MIN, r["omega"]/np.where(kappa == 0, np.nan, kappa), np.nan)
        ok = (np.abs(r["omega"]) >= OMEGA_MIN) & np.isfinite(v_read) & (v_read > V_MIN) & (v_read < V_MAX)
        v_read = np.where(ok, v_read, np.nan)
        out.append(pd.DataFrame(dict(
            drive=bl.drive, driver=bl.driver, session=int(bl.session), row_start=int(bl.row_start),
            band=bl.band_1000, t=r["t"] - r["t"][0], v_true=r["v_true"], v_held=r["speed0"],
            omega=r["omega"], omega_smooth=omega_s, kappa=kappa, kappa_long=kap[WINDOWS_M[1]],
            v_read=v_read, matched=seg >= 0)))
    D = pd.concat(out, ignore_index=True)
    D.to_parquet(R2/"out/round3_curve_speed.parquet")
    log(f"{len(D):,} rows over {D.groupby(['drive','session','row_start']).ngroups} blackouts")

    head("1 · how often is there a reading?")
    print(f"  rows matched to a road            {100*D.matched.mean():5.1f}%")
    print(f"  road bending enough               {100*(np.abs(D.kappa) >= KAPPA_MIN).mean():5.1f}%")
    print(f"  gyro turning enough               {100*(np.abs(D.omega) >= OMEGA_MIN).mean():5.1f}%")
    print(f"  usable speed reading              {100*D.v_read.notna().mean():5.1f}% of rows")
    per = D.groupby(["drive", "session", "row_start"]).v_read.apply(lambda s: s.notna().mean())
    print(f"  blackouts with at least one       {100*(per > 0).mean():5.1f}%   "
          f"(median {100*per.median():.0f}% of their rows, p90 {100*per.quantile(0.9):.0f}%)")
    gap = D.groupby(["drive", "session", "row_start"], group_keys=False).apply(
        lambda g: pd.Series(dict(gap_s=_longest_gap(g))))
    print(f"  longest stretch with no reading   median {gap.gap_s.median():4.1f} s, p90 {gap.gap_s.quantile(0.9):4.1f} s")

    head("2 · how good are the readings?")
    r = D[D.v_read.notna()]
    err = r.v_read - r.v_true
    print(f"  n = {len(r):,} readings")
    print(f"  error vs true speed: median {err.median():+5.2f} m/s, RMS {np.sqrt((err**2).mean()):5.2f} m/s, "
          f"p90 |error| {np.abs(err).quantile(0.9):5.2f} m/s")
    print(f"  the held GNSS speed on the same rows: RMS {np.sqrt(((r.v_held - r.v_true)**2).mean()):5.2f} m/s")
    print("\n  by speed band (RMS m/s):    reading   held GNSS speed   n")
    for b, g in r.groupby("band"):
        print(f"    {b:<9} {np.sqrt(((g.v_read - g.v_true)**2).mean()):19.2f} {np.sqrt(((g.v_held - g.v_true)**2).mean()):11.2f} {len(g):8,}")

    head("3 · what would it do to a whole blackout?")
    print("  'curve speed' = the last reading, held until the next one, starting from the GNSS speed at the blackout")
    rows = []
    for (drive, sess, start), g in D.groupby(["drive", "session", "row_start"]):
        v_curve = pd.Series(np.where(g.v_read.notna(), g.v_read, np.nan)).ffill().to_numpy()
        v_curve = np.where(np.isnan(v_curve), g.v_held.to_numpy(), v_curve)
        t, v_true = g.t.to_numpy(), g.v_true.to_numpy()
        rows.append(dict(band=g.band.iloc[0], readings=int(g.v_read.notna().sum()),
                         rms_held=float(np.sqrt(np.mean((g.v_held - v_true)**2))),
                         rms_curve=float(np.sqrt(np.mean((v_curve - v_true)**2))),
                         dist_held=float(np.trapezoid(g.v_held - v_true, t)),
                         dist_curve=float(np.trapezoid(v_curve - v_true, t)),
                         dist_true=float(np.trapezoid(v_true, t))))
    B = pd.DataFrame(rows)
    print(f"  blackouts: {len(B)}   with at least one reading: {(B.readings > 0).sum()}")
    print("\n  speed error over the blackout, RMS m/s (median over blackouts):")
    print(f"    held GNSS speed {B.rms_held.median():5.2f}      curve speed {B.rms_curve.median():5.2f}")
    print("\n  distance error after 1 km, |metres| (median over blackouts):")
    print(f"    held GNSS speed {B.dist_held.abs().median():5.0f}      curve speed {B.dist_curve.abs().median():5.0f}")
    print("\n  by band — RMS speed error (held / curve) and |distance error| after 1 km (held / curve):")
    print(f"    {'band':<9} {'n':>4}  {'rms held':>9} {'rms curve':>9}   {'dist held':>9} {'dist curve':>10}")
    for b, g in B.groupby("band"):
        print(f"    {b:<9} {len(g):4d}  {g.rms_held.median():9.2f} {g.rms_curve.median():9.2f}   "
              f"{g.dist_held.abs().median():9.0f} {g.dist_curve.abs().median():10.0f}")
    better = (B.dist_curve.abs() < B.dist_held.abs()).mean()
    print(f"\n  curve speed is closer on {100*better:.0f}% of blackouts")
    print("\n  Caveat: curvature came from the true position. In the filter each particle reads the road under itself,")
    print("  so a wrong road gives a wrong reading — the gain will be smaller, and the reading must be weighed, not trusted.")


def _longest_gap(g):
    t = g.t.to_numpy()
    have = g.v_read.notna().to_numpy()
    idx = np.flatnonzero(have)
    if len(idx) == 0:
        return float(t[-1] - t[0])
    edges = np.r_[t[0], t[idx], t[-1]]
    return float(np.max(np.diff(edges)))


def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blackouts", type=int, default=200)
    a = ap.parse_args()
    main(a.blackouts)
    measurement2(a.blackouts)


# ---------------------------------------------------------------------------------------------------------------------
# Measurement 2 — speed from the shape of the bend, not from a pointwise ratio.
#
# Dividing turn rate by curvature at one instant fails (measurement 1): a vehicle's yaw includes lane weaving and
# corner cutting that a road centreline does not have, so the ratio is noise unless the bend is very tight.
# Accumulating removes most of that. Over a window of T seconds the gyro says the vehicle turned through an angle;
# the road ahead says how far you must drive to turn through that angle. That distance over T is a speed.
#
#     gyro over T seconds            ->  heading change  (weaving cancels out: it turns back)
#     road bearing profile ahead     ->  the distance that gives the same bearing change
#     speed                          =  that distance / T
#
# Still an upper bound: the profile starts at the true position, i.e. the particle is on the right road.

def bearing_profile(curve, seg, dirn, max_m=600.0):
    """Cumulative distance and road bearing ahead of a matched point, following the straightest continuation."""
    r = curve.r
    e = int(r.edge_of(seg, dirn))
    if e < 0:
        return None
    s, b = [0.0], [float(r.edge_bearing[e])]
    walked = 0.0
    for _ in range(200):
        node = int(r.edge_to[e])
        best, best_turn = -1, np.inf
        for k in range(r.out_ptr[node], r.out_ptr[node + 1]):
            f = int(r.out_edges[k])
            if f == int(r.edge_rev[e]):
                continue
            turn = abs(roadnet.wrap(r.edge_bearing[f] - r.edge_bearing[e]))
            if turn < best_turn:
                best, best_turn = f, turn
        if best < 0 or best_turn > np.radians(60):
            break
        e = best
        walked += float(r.seg_len[r.edge_seg[e]])
        s.append(walked)
        b.append(float(r.edge_bearing[e]))
        if walked >= max_m:
            break
    if len(s) < 3:
        return None
    s = np.array(s)
    b = np.unwrap(np.array(b))
    return s, b - b[0]


def shape_speed(prof, dpsi, t_window, v_lo=2.0, v_hi=45.0, tol=np.radians(3)):
    """The speed whose distance over t_window turns the road through dpsi; NaN when the answer is not unique."""
    s, db = prof
    lo, hi = v_lo*t_window, v_hi*t_window
    m = (s >= lo) & (s <= hi)
    if m.sum() < 3 or s[-1] < lo:
        return np.nan, np.nan
    ss, bb = s[m], db[m]
    err = np.abs(bb - dpsi)
    j = int(err.argmin())
    if err[j] > tol:
        return np.nan, np.nan
    good = ss[err <= max(tol, err[j]*2)]          # how wide the set of distances that fit is: the ambiguity
    return float(ss[j]/t_window), float((good.max() - good.min())/t_window)


def measurement2(n_blackouts, t_window=10.0, min_turn_deg=8.0):
    head(f"Round 3 · measurement 2 — speed from the shape of the bend ({t_window:.0f} s windows, "
         f"at least {min_turn_deg:.0f} deg of turning)")
    BL = pd.read_parquet(R2/"out/blackouts.parquet")
    BL = BL[BL.driver.isin(TUNE) & BL.moving_1000 & BL.end_1000.notna()]
    rng = np.random.default_rng(3)
    BL = BL.iloc[np.sort(rng.permutation(len(BL))[:n_blackouts])]
    roads = roadnet.RoadNetwork()
    curve = Curvature(roads)
    rows, S, C, key = [], None, None, None
    for _, bl in BL.iterrows():
        k = (bl.drive, int(bl.session))
        if k != key:
            S, C, key = sessions.load(bl.drive, bl.driver, int(bl.session)), None, k
            C = calibration.Calibrator(S)
            log(f"  {bl.drive} s{bl.session} ({bl.driver})")
        r = rows_for(S, C, bl)
        if r is None:
            continue
        x, y = roadnet.xy(r["lat"], r["lon"])
        m = roads.match(x, y, r["heading"], radius=MATCH_RADIUS_M)
        seg, dirn = m["seg"], m["dir"]
        t, omega, v_true = r["t"] - r["t"][0], r["omega"], r["v_true"]
        w = int(t_window*10)
        for p in range(0, len(t) - w, 20):                      # a window every 2 s
            if seg[p] < 0:
                continue
            dpsi = float(np.trapezoid(omega[p:p + w], t[p:p + w]))
            if abs(dpsi) < np.radians(min_turn_deg):
                continue
            prof = bearing_profile(curve, seg[p], dirn[p])
            if prof is None:
                continue
            v, spread = shape_speed(prof, dpsi, t_window)
            if not np.isfinite(v):
                continue
            rows.append(dict(band=bl.band_1000, v_shape=v, spread=spread, v_held=float(r["speed0"]),
                             v_true=float(v_true[p:p + w].mean())))
    R = pd.DataFrame(rows)
    if R.empty:
        print("  no windows produced a reading")
        return
    R.to_parquet(R2/"out/round3_shape_speed.parquet")
    e, eh = R.v_shape - R.v_true, R.v_held - R.v_true
    print(f"  {len(R)} readings over {n_blackouts} blackouts")
    print(f"  shape speed vs true: median {e.median():+5.2f} m/s, RMS {np.sqrt((e**2).mean()):5.2f}, "
          f"within 3 m/s {100*(e.abs() < 3).mean():3.0f}%")
    print(f"  held GNSS speed on the same windows: RMS {np.sqrt((eh**2).mean()):5.2f}, "
          f"within 3 m/s {100*(eh.abs() < 3).mean():3.0f}%")
    print("\n  keeping only the unambiguous readings (the distances that fit span less than X m/s):")
    for lim in (10.0, 5.0, 2.0):
        q = R[R.spread <= lim]
        if len(q) < 10:
            continue
        eq, ehq = q.v_shape - q.v_true, q.v_held - q.v_true
        print(f"    spread <= {lim:4.1f} m/s   n={len(q):5d} ({100*len(q)/len(R):3.0f}%)   "
              f"shape RMS {np.sqrt((eq**2).mean()):5.2f}   held RMS {np.sqrt((ehq**2).mean()):5.2f}   "
              f"shape within 3 m/s {100*(eq.abs() < 3).mean():3.0f}%")
    print("\n  by band (RMS m/s, shape / held):")
    for b, g in R.groupby("band"):
        print(f"    {b:<9} n={len(g):5d}   {np.sqrt(((g.v_shape - g.v_true)**2).mean()):5.2f} / "
              f"{np.sqrt(((g.v_held - g.v_true)**2).mean()):5.2f}")


if __name__ == "__main__":
    _cli()
