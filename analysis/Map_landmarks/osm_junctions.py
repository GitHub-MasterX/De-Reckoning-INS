"""Road junctions along the IO-VNBD routes: how many competing turn candidates a map matcher faces
(round2/MAP_LANDMARK_APPROACH.md §13).
Junction = OSM node where drivable ways meet with >= 3 arms. Every pass keeps its turn options:
arm angle relative to the incoming direction of travel (+ = right, - = left), with straight-on and
the road just driven excluded.
Output: data/osm/junction_passes.parquet (feeds snap_recheck.py --junctions)."""
import warnings; warnings.filterwarnings("ignore")
import time, math, array, resource, numpy as np, pandas as pd, osmium
from pathlib import Path
from scipy.spatial import cKDTree
ROOT = Path(__file__).resolve().parents[2]
PBF = ROOT/"data/osm/england-latest.osm.pbf"
OUT = ROOT/"data/osm/junction_passes.parquet"
BUF, ARM_LEN, DX, DY, KX, KY = 10.0, 15.0, 0.02, 0.012, 111320.0, 110540.0
CLS = {**dict.fromkeys(("motorway", "trunk", "primary", "secondary", "tertiary", "motorway_link",
                        "trunk_link", "primary_link", "secondary_link", "tertiary_link"), 0),
       **dict.fromkeys(("unclassified", "residential", "living_street", "road"), 1), "service": 2}
T0 = time.time()
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def xy(lon, lat):
    lon = np.asarray(lon, float); lat = np.asarray(lat, float)
    return np.c_[lon*KX*np.cos(np.radians(lat)), lat*KY]

# ── routes (same session selection and track construction as osm_landmarks.py) ──
sel = pd.read_csv(ROOT/"data/test_outputs/alignment.csv")
sel = sel[(sel.sync_r.abs() >= 0.40) & sel.sync_r.notna() & (sel.drive != "Vtb1")]
TR = []
for _, r in sel.iterrows():
    base = pd.read_parquet(ROOT/f"data/clean/{r.drive}.parquet",
                           columns=["session", "aligned_valid", "veh_idx", "lat", "lon"])
    d = base[(base.session == r.session) & base.aligned_valid].reset_index(drop=True)
    if len(d) < 3000: continue
    vi = d.veh_idx.to_numpy(); lat = base.lat.to_numpy()[vi]; lon = base.lon.to_numpy()[vi]
    ok = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) > 1)
    if ok.sum() < 100: continue
    p = xy(lon[ok], lat[ok]); stp = np.hypot(*np.diff(p, axis=0).T); stp[stp > 50] = 0.0
    TR.append(dict(drive=r.drive, driver=r.driver, session=int(r.session), rows=np.flatnonzero(ok),
                   p=p, along=np.concatenate(([0.0], np.cumsum(stp))), lon=lon[ok], lat=lat[ok]))
KM = {D: sum(t["along"][-1] for t in TR if t["driver"] == D)/1000 for D in "EBAD"}
LON0 = min(t["lon"].min() for t in TR) - 0.1; LAT0 = min(t["lat"].min() for t in TR) - 0.1
LON1 = max(t["lon"].max() for t in TR) + 0.1; LAT1 = max(t["lat"].max() for t in TR) + 0.1
OCC = set()                                   # map cells within ~2.5 km of any track
for t in TR:
    cells = set(zip(((t["lon"] - LON0)//DX).astype(int).tolist(), ((t["lat"] - LAT0)//DY).astype(int).tolist()))
    for a, b in cells:
        for da in (-2, -1, 0, 1, 2):
            for db in (-2, -1, 0, 1, 2):
                OCC.add((a + da, b + db))
log(f"{len(TR)} sessions, {sum(KM.values()):.0f} km of track, {len(OCC):,} map cells kept")

# ── scan: every drivable way near a route, node by node ──
refs, lons, lats = array.array("q"), array.array("d"), array.array("d")
flag, cls_, rab = array.array("b"), array.array("b"), array.array("b")
fp = (osmium.FileProcessor(str(PBF), osmium.osm.NODE | osmium.osm.WAY)
      .with_locations(storage="sparse_mem_array")
      .with_filter(osmium.filter.KeyFilter("highway")))
seen = kept = bad = 0
for o in fp:
    if not o.is_way(): continue
    c = CLS.get(o.tags.get("highway"), -1)
    if c < 0 or o.tags.get("area") == "yes": continue
    seen += 1
    if seen % 500000 == 0:
        log(f"  {seen:,} drivable ways seen, {kept:,} near the routes, {len(refs):,} node refs")
    ns = o.nodes; k = len(ns)
    if k < 2: continue
    try:
        n0 = ns[0]
        if not (LON0 - 0.3 < n0.lon < LON1 + 0.3 and LAT0 - 0.2 < n0.lat < LAT1 + 0.2): continue
        hit = False
        for q in list(range(0, k, 3)) + [k - 1]:
            nq = ns[q]
            if (int((nq.lon - LON0)//DX), int((nq.lat - LAT0)//DY)) in OCC:
                hit = True; break
        if not hit: continue
        rr = [x.ref for x in ns]; xx = [x.lon for x in ns]; yy = [x.lat for x in ns]
    except Exception:
        bad += 1; continue
    f = [0]*k; f[0] = 1; f[-1] = 2
    refs.extend(rr); lons.extend(xx); lats.extend(yy); flag.extend(f)
    cls_.extend([c]*k); rab.extend([1 if o.tags.get("junction") in ("roundabout", "circular") else 0]*k)
    kept += 1
log(f"scan done: {seen:,} drivable ways, {kept:,} near the routes, {len(refs):,} node refs, "
    f"{bad} with missing locations; peak memory {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6:.1f} GB")

# ── junction nodes = >= 3 arms (way interior node = 2 arms, way end = 1) ──
R = np.frombuffer(refs, np.int64); LON = np.frombuffer(lons, np.float64); LAT = np.frombuffer(lats, np.float64)
F = np.frombuffer(flag, np.int8); C = np.frombuffer(cls_, np.int8); RB = np.frombuffer(rab, np.int8)
arms = np.where(F == 0, 2, 1).astype(np.int32)
order = np.argsort(R, kind="stable")
_, first, cnt = np.unique(R[order], return_index=True, return_counts=True)
tot = np.add.reduceat(arms[order], first)
nsv = np.add.reduceat(np.where(C[order] <= 1, arms[order], 0), first)
jidx = np.flatnonzero(tot >= 3)
occ0 = order[first[jidx]]
JXY = xy(LON[occ0], LAT[occ0])
dd, _ = cKDTree(np.vstack([t["p"] for t in TR])).query(JXY, distance_upper_bound=BUF)
near = np.flatnonzero(np.isfinite(dd))
JU, JN = jidx[near], JXY[near]
log(f"{len(jidx):,} junction nodes in the kept cells; {len(near):,} within {BUF:.0f} m of a track")

def arm_bearing(k, step):
    """Compass bearing from junction occurrence k to a point ~15 m along its way."""
    q, acc, stop = k, 0.0, (2 if step == 1 else 1)
    while not (F[q] & stop):
        q2 = q + step
        acc += math.hypot((LON[q2] - LON[q])*KX*math.cos(math.radians(LAT[q])), (LAT[q2] - LAT[q])*KY)
        q = q2
        if acc >= ARM_LEN: break
    if q == k: return None
    return math.degrees(math.atan2((LON[q] - LON[k])*KX*math.cos(math.radians(LAT[k])), (LAT[q] - LAT[k])*KY))

BEAR, RBJ = [], []
for uu in JU:
    occ = order[first[uu]:first[uu] + cnt[uu]]
    b = [arm_bearing(int(k), s) for k in occ for s in (1, -1)]
    BEAR.append([x for x in b if x is not None]); RBJ.append(bool(RB[occ].any()))

# ── passes: where each track goes through a junction, and which turns were possible there ──
out = []
for t in TR:
    AL, P_ = t["along"], t["p"]
    for n, lst in enumerate(cKDTree(P_).query_ball_point(JN, r=BUF)):
        if not lst: continue
        lst = np.sort(np.asarray(lst, int))
        for grp in np.split(lst, np.flatnonzero(np.diff(AL[lst]) > 100) + 1):
            k = int(grp[np.argmin(np.hypot(*(P_[grp] - JN[n]).T))])
            a = AL[k]; k0 = np.searchsorted(AL, a - 30.0); k1 = np.searchsorted(AL, a - 5.0)
            if k1 <= k0 or k1 >= len(AL): continue
            dx, dy = P_[k1] - P_[k0]
            if math.hypot(dx, dy) < 10: continue
            hin = math.degrees(math.atan2(dx, dy))
            opts = [round(rel, 1) for rel in (((b - hin + 180.0) % 360.0) - 180.0 for b in BEAR[n])
                    if 30.0 < abs(rel) < 150.0]
            out.append(dict(drive=t["drive"], driver=t["driver"], session=t["session"], row=int(t["rows"][k]),
                            along_m=float(a), tot_arms=int(tot[JU[n]]), ns_arms=int(nsv[JU[n]]),
                            roundabout=RBJ[n], options=opts,
                            n_left=sum(x < 0 for x in opts), n_right=sum(x > 0 for x in opts)))
P = pd.DataFrame(out)
P.to_parquet(OUT, index=False)
log(f"{len(P):,} junction passes written to {OUT.relative_to(ROOT)}")

def clusters(q):
    n, gaps = 0, []
    for _, s in q.groupby(["drive", "session"]):
        a = np.sort(s.along_m.to_numpy()); a = a[np.r_[True, np.diff(a) > 25]]
        n += len(a); gaps += np.diff(a).tolist()
    return n, (float(np.median(gaps)) if gaps else float("nan"))

print(f"\nJUNCTIONS ON THE DRIVEN ROUTES   (OSM nodes within {BUF:.0f} m of the track, merged within 25 m)\n")
print(f"  {'driver':<8}{'km':>6}{'junctions/km (median gap)':>28}{'excl. service roads':>21}"
      f"{'with a LEFT turn option':>26}{'with a RIGHT turn option':>27}")
for D in "EBAD":
    q = P[P.driver == D]; km = KM[D]
    na, ga = clusters(q); nn, gn = clusters(q[q.ns_arms >= 3])
    nl, gl = clusters(q[q.n_left > 0]); nr, gr = clusters(q[q.n_right > 0])
    print(f"  {D:<8}{km:>6.0f}{na/km:>15.1f} /km ({ga:>4.0f} m){nn/km:>10.1f} /km ({gn:>4.0f} m)"
          f"{nl/km:>12.1f} /km, every {gl:>4.0f} m{nr/km:>12.1f} /km, every {gr:>4.0f} m")
