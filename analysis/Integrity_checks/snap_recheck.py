"""Audit of round2/MAP_LANDMARK_APPROACH.md §3.3 inside the evaluator's own protocol (run_evaluation.py,
tag round-1): 1 km blackouts, start speed > 4.2 m/s, speed never below 1.4 km/h,
error = |estimated - true distance|, median over blackouts (§14 of the doc).
Map = bends of the vehicle GPS course on the driven route, located by distance.
Causal: a bend with apex at sample b can only correct the estimate after b + 7.5 s (centred window).
Medians are shown two ways: every blackout (length-weighted) and <=200 random blackouts per session
(what run_evaluation.py does).
  --junctions   add OSM junction turn options along the route as competing candidates
                (needs data/osm/junction_passes.parquet from osm_junctions.py)"""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
from pathlib import Path
from scipy.ndimage import maximum_filter1d, uniform_filter1d
ROOT = Path(__file__).resolve().parents[2]
FS = 10.0; W = int(15*FS); HALF = W//2; TOL = int(5*FS); THR = 15.0
DIST, V_START, V_MOVE, EVERY, MIN_GAP = 1000.0, 4.2, 1.4/3.6, 20, 100
EVAL = {"E": 10.18, "B": 16.11, "A": 16.49, "D": 19.60}          # run_evaluation.py, coast @ 1 km
USE_J = "--junctions" in sys.argv
JP = pd.read_parquet(ROOT/"data/osm/junction_passes.parquet") if USE_J else None

def peaks(rate, v):
    h = np.cumsum(rate)/FS; d = np.zeros(len(h)); d[HALF:-HALF] = h[W:] - h[:-W]
    a = np.abs(d); vm = uniform_filter1d(v, size=W)
    idx = np.flatnonzero((a >= np.radians(THR)) & (a == maximum_filter1d(a, size=W)) & (vm > 2))
    keep = np.array([i for k, i in enumerate(idx) if k == 0 or i - idx[k-1] > HALF], int)
    return keep, np.degrees(d[keep])

def simulate(i, j, dist, v, dets, cpos, cang, gate_frac, reest):
    """Single-hypothesis matcher: at each detected turn, snap to the best candidate inside the gate.
    dets = (sample, net turn deg, map position of the real bend behind this detection or NaN)."""
    t0, p0, vh = i, dist[i], v[i]
    at, ap = [i], [dist[i]]
    st = np.zeros(4)                                # right bend, wrong candidate, false detection, n
    for a, g, tp in dets:
        est = p0 + vh*(a - t0)/FS
        gate = max(20.0, gate_frac*(est - p0))
        lo, hi = np.searchsorted(cpos, (est - gate, est + gate))
        best, bj = -1, np.inf
        for q in range(lo, hi):
            if cang[q]*g <= 0 or abs(cang[q] - g) > max(20.0, 0.4*abs(g)): continue
            J = (3*(cpos[q] - est)/gate)**2 + ((cang[q] - g)/15.0)**2
            if J < bj: best, bj = q, J
        if best < 0: continue
        pn = cpos[best]; st[3] += 1
        if np.isnan(tp): st[2] += 1
        elif abs(pn - tp) < 1e-6: st[0] += 1
        else: st[1] += 1
        if reest:
            k = [m for m in range(len(at)) if at[m] <= a - MIN_GAP]
            if k: vh = min(max((pn - ap[k[-1]])/((a - at[k[-1]])/FS), 1.0), 45.0)
        at.append(a); ap.append(pn); t0, p0 = a, pn
    return 100*abs(p0 + vh*(j - t0)/FS - dist[j])/(dist[j] - dist[i]), st

VARIANTS = [("phone turns · route map · gate 30% · speed re-estimated", 0.3, True, False),
            ("phone turns · route map · gate 50% · speed re-estimated", 0.5, True, False),
            ("phone turns · route map · gate 50% · speed kept", 0.5, False, False)]
if USE_J:
    VARIANTS += [("phone turns · + OSM junctions · gate 30% · re-estimated", 0.3, True, True),
                 ("phone turns · + OSM junctions · gate 50% · re-estimated", 0.5, True, True),
                 ("phone turns · + OSM junctions · gate 50% · speed kept", 0.5, False, True)]
res = {x: {} for x in "EBAD"}; cnt = {x: {} for x in "EBAD"}; sess_stats = {x: [] for x in "EBAD"}
def put(x, key, val): res[x].setdefault(key, []).append(val)

sel = pd.read_csv(ROOT/"data/test_outputs/alignment.csv")
sel = sel[(sel.sync_r.abs() >= 0.40) & sel.sync_r.notna() & (sel.drive != "Vtb1")]
n_sess = 0
for _, r in sel.iterrows():
    base = pd.read_parquet(ROOT/f"data/clean/{r.drive}.parquet",
                           columns=["session", "aligned_valid", "veh_idx", "rate_yaw", "speed_best_al", "heading"])
    d = base[(base.session == r.session) & base.aligned_valid].reset_index(drop=True)
    if len(d) < 3000: continue
    ph = d.rate_yaw.to_numpy(); v = d.speed_best_al.to_numpy()/3.6
    hd = base.heading.to_numpy()[d.veh_idx.to_numpy()]
    ok = np.isfinite(ph) & np.isfinite(v); rows = np.flatnonzero(ok)
    ph, v, hd = ph[ok], v[ok], hd[ok]
    if len(v) < 3000: continue
    n_sess += 1
    hv = np.isfinite(hd)
    gp = np.gradient(np.unwrap(np.radians(pd.Series(hd).ffill().bfill().to_numpy())))*FS
    gp[(v < 2) | ~hv] = 0.0
    m = (v > 5) & hv
    c = np.corrcoef(ph[m], gp[m])[0, 1] if m.sum() > 100 else 1.0
    ph = ph*(-1.0 if c < 0 else 1.0)
    dist = np.concatenate(([0.0], np.cumsum(v[:-1])/FS))
    ti, tang = peaks(gp, v); pi, pang = peaks(ph, v)
    tpos = dist[ti]; o = np.argsort(tpos)
    # which real bend (if any) is behind each phone detection: same sign, within ±5 s, one-to-one
    tp_pos = np.full(len(pi), np.nan); used = set()
    for q, (a, g) in enumerate(zip(pi, pang)):
        lo, hi = np.searchsorted(ti, (a - TOL, a + TOL + 1))
        cand = [k for k in range(lo, hi) if k not in used and tang[k]*g > 0]
        if cand:
            k = min(cand, key=lambda k: abs(ti[k] - a)); used.add(k); tp_pos[q] = tpos[k]
    c_route = (tpos[o], tang[o]); c_junc = c_route
    if USE_J:
        jp = JP[(JP.drive == r.drive) & (JP.session == r.session)]
        jpos, jang = [], []
        for row, opts in zip(jp.row.to_numpy(), jp.options):
            k = np.searchsorted(rows, row)
            if k >= len(rows) or rows[k] != row: continue
            for th in opts:
                if np.any((np.abs(tpos - dist[k]) < 30) & (np.sign(tang) == np.sign(th))): continue
                jpos.append(dist[k]); jang.append(float(th))
        allp = np.r_[tpos, jpos]; alla = np.r_[tang, jang]; o = np.argsort(allp)
        c_junc = (allp[o], alla[o])

    n = len(v); stopped = np.concatenate(([0], np.cumsum(v <= V_MOVE)))
    st = np.arange(0, n, EVERY); st = st[v[st] > V_START]
    en = np.searchsorted(dist, dist[st] + DIST)
    k = en < n; st, en = st[k], en[k]
    k = stopped[en + 1] - stopped[st] == 0; st, en = st[k], en[k]
    x = r.driver; first_coast = len(res[x].get("coast", []))
    for i, j in zip(st, en):
        true = dist[j] - dist[i]
        pct = lambda est: 100*abs(est - dist[j])/true
        put(x, "_sid", n_sess)
        put(x, "coast", pct(dist[i] + v[i]*(j - i)/FS))
        inside = ti[(ti >= i) & (ti <= j)]
        put(x, "doc", EVAL[x]*((dist[j] - dist[inside[-1]]) if len(inside) else true)/1000)
        use = ti[(ti > i) & (ti + HALF <= j)]
        put(x, "has", len(use) > 0)
        if len(use):
            bl = use[-1]; anc = np.r_[i, use]; prev = anc[anc <= bl - MIN_GAP]
            v2 = (dist[bl] - dist[prev[-1]])/((bl - prev[-1])/FS) if len(prev) else v[i]
            vs = (dist[bl] - dist[i])/((bl - i)/FS) if bl - i >= MIN_GAP else v[i]
            put(x, "p_keep", pct(dist[bl] + v[i]*(j - bl)/FS))
            put(x, "p_two", pct(dist[bl] + v2*(j - bl)/FS))
            put(x, "p_start", pct(dist[bl] + vs*(j - bl)/FS))
        else:
            for key in ("p_keep", "p_two", "p_start"): put(x, key, res[x]["coast"][-1])
        sel_d = (pi > i) & (pi + HALF <= j)
        dets = list(zip(pi[sel_d], pang[sel_d], tp_pos[sel_d]))
        for name, G, reest, withj in VARIANTS:
            cp, ca = c_junc if withj else c_route
            e, s_ = simulate(i, j, dist, v, dets, cp, ca, G, reest)
            put(x, name, e)
            cnt[x][name] = cnt[x].get(name, np.zeros(4)) + s_
    co = res[x].get("coast", [])[first_coast:]
    if co: sess_stats[x].append((len(co), float(np.median(co))))

ORDER = "EBAD"
rng = np.random.default_rng(0)
balanced = {}
for x in ORDER:
    sid = np.array(res[x]["_sid"]); idx = []
    for s in np.unique(sid):
        w = np.flatnonzero(sid == s)
        idx.extend(rng.choice(w, size=min(200, len(w)), replace=False))
    balanced[x] = np.array(idx)
KEYS = [("coast", "coast (no map)"), ("doc", "§3.3 ceiling formula, on these blackouts"),
        ("p_keep", "perfect snaps · speed kept from blackout start"),
        ("p_two", "perfect snaps · speed from the last two anchors"),
        ("p_start", "perfect snaps · speed averaged since blackout start")] + [(nm, nm) for nm, *_ in VARIANTS]

print(f"{n_sess} sessions · 1 km blackouts, same rules as run_evaluation.py · bends >= {THR:.0f} deg\n")
print(f"  {'median drift at 1 km':<60}{'every blackout (length-weighted)':^44}{'<=200 per session (run_evaluation.py)':^44}")
print(f"  {'':<60}" + "".join(f"{'drv ' + x:>11}" for x in ORDER)*2)
print(f"  {'blackouts':<60}" + "".join(f"{len(res[x]['coast']):>11,}" for x in ORDER)
      + "".join(f"{len(balanced[x]):>11,}" for x in ORDER))
print(f"  {'coast - run_evaluation.py (reference)':<60}{'':<44}" + "".join(f"{EVAL[x]:>10.1f}%" for x in ORDER))
print(f"  {'blackouts with a usable real bend (causal)':<60}"
      + "".join(f"{100*np.mean(res[x]['has']):>10.0f}%" for x in ORDER)
      + "".join(f"{100*np.mean(np.array(res[x]['has'])[balanced[x]]):>10.0f}%" for x in ORDER))
for key, label in KEYS:
    print(f"  {label:<60}" + "".join(f"{np.median(res[x][key]):>10.1f}%" for x in ORDER)
          + "".join(f"{np.median(np.array(res[x][key])[balanced[x]]):>10.1f}%" for x in ORDER))

print(f"\n  {'snaps per blackout · right bend / wrong candidate / false detection':<60}")
for name, *_ in VARIANTS:
    print(f"  {name:<60}" + "".join(
        f"  {cnt[x][name][3]/len(res[x]['coast']):.2f} · {100*cnt[x][name][0]/max(cnt[x][name][3],1):.0f}/"
        f"{100*cnt[x][name][1]/max(cnt[x][name][3],1):.0f}/{100*cnt[x][name][2]/max(cnt[x][name][3],1):.0f}%"
        for x in ORDER))

print("\n  sessions: blackouts per session (min / median / max) · per-session median coast drift (min / median / max)")
for x in ORDER:
    s = np.array(sess_stats[x])
    print(f"  driver {x}: {len(s)} sessions · {s[:,0].min():.0f} / {np.median(s[:,0]):.0f} / {s[:,0].max():.0f} blackouts"
          f" · {s[:,1].min():.1f} / {np.median(s[:,1]):.1f} / {s[:,1].max():.1f} %")
