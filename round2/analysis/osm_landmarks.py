"""
Step 1 of round2/MAP_LANDMARK_APPROACH.md — which OSM landmark types lie along the IO-VNBD
routes, how often each driver passes them, and how many 1 km blackouts contain at least one.

One pass over england-latest.osm.pbf: node locations stay in memory (C++), and only
landmark-tagged objects reach Python. Everything inside the dataset area is cached so later
steps never re-read the 1.6 GB file.

Outputs
  data/osm/landmarks_iovnbd.parquet        every landmark in the dataset area (cache)
  data/osm/landmark_passes.parquet         every pass: session, landmark, type, along-track metre
  round2/out/landmarks_along_routes.csv    per driver x type: passes/km, unique, % of 1 km windows
"""
import warnings; warnings.filterwarnings("ignore")
import time, resource
import numpy as np, pandas as pd, osmium
from pathlib import Path
from scipy.spatial import cKDTree

ROOT   = Path(__file__).resolve().parents[2]
PBF    = ROOT/"data/osm/england-latest.osm.pbf"
CACHE  = ROOT/"data/osm/landmarks_iovnbd.parquet"
PASSES = ROOT/"data/osm/landmark_passes.parquet"
OUT    = ROOT/"round2/out/landmarks_along_routes.csv"
BUF, STEP, PARALLEL_FRAC, MARGIN, SPLIT = 15.0, 5.0, 0.6, 0.02, 200.0
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:5.0f}s]", *a, flush=True)
def xy(lon, lat):
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    return np.c_[lon*111320.0*np.cos(np.radians(lat)), lat*110540.0]
def densify(p):
    if len(p) < 2: return p, np.zeros(len(p))
    s = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))))
    k = np.r_[True, np.diff(s) > 0]; p, s = p[k], s[k]
    if len(p) < 2: return p, np.zeros(len(p))
    g = np.r_[np.arange(0, s[-1], STEP), s[-1]]
    return np.c_[np.interp(g, s, p[:,0]), np.interp(g, s, p[:,1])], g

# ───────────────────────── 1 · vehicle tracks (same sessions as §3.4) ─────────────────────────
A = pd.read_csv(ROOT/"data/alignment.csv")
sel = A[(A.sync_r.abs() >= 0.40) & A.sync_r.notna()]; sel = sel[sel.drive != "Vtb1"]
T_pts, T_trk, T_al, tracks = [], [], [], []
lo_min = la_min = 1e9; lo_max = la_max = -1e9
for _, r in sel.iterrows():
    base = pd.read_parquet(ROOT/f"data/clean/{r.drive}.parquet")
    d = base[(base.session == r.session) & base.aligned_valid]
    if len(d) < 3000: continue
    vi = d.veh_idx.to_numpy(); lat = base.lat.to_numpy()[vi]; lon = base.lon.to_numpy()[vi]
    ok = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) > 1); lat, lon = lat[ok], lon[ok]
    if len(lat) < 100: continue
    lo_min, lo_max = min(lo_min, lon.min()), max(lo_max, lon.max())
    la_min, la_max = min(la_min, lat.min()), max(la_max, lat.max())
    p = xy(lon, lat)
    brk = np.flatnonzero(np.hypot(*np.diff(p, axis=0).T) > 50) + 1        # GPS glitch
    off, tid = 0.0, len(tracks)
    for part in np.split(np.arange(len(p)), brk):
        if len(part) < 2: continue
        q, g = densify(p[part])
        if len(q) < 2: continue
        T_pts.append(q); T_al.append(g + off); T_trk.append(np.full(len(q), tid)); off += g[-1]
    tracks.append(dict(tid=tid, driver=r.driver, drive=r.drive, session=int(r.session), length=off))
P_all = np.vstack(T_pts); P_trk = np.concatenate(T_trk); P_al = np.concatenate(T_al)
tree = cKDTree(P_all)
TR = pd.DataFrame(tracks)
BB = (lo_min-MARGIN, la_min-MARGIN, lo_max+MARGIN, la_max+MARGIN)
log(f"{len(TR)} sessions, {TR.length.sum()/1000:.0f} km of track, {len(P_all):,} route points")
log(f"bbox lon {BB[0]:.3f}..{BB[2]:.3f}  lat {BB[1]:.3f}..{BB[3]:.3f}")

# ───────────────────────── 2 · scan the map once ─────────────────────────
HWY_NODE = {"traffic_signals","stop","give_way","crossing","mini_roundabout","turning_circle",
            "motorway_junction","speed_camera","milestone"}
BARRIER  = {"toll_booth","cattle_grid","lift_gate"}
MOTOR    = {"motorway","trunk","primary","secondary","tertiary","unclassified","residential","service",
            "living_street","motorway_link","trunk_link","primary_link","secondary_link","tertiary_link"}
def inbox(lon, lat): return BB[0] <= lon <= BB[2] and BB[1] <= lat <= BB[3]

rows, n_py, bad_ways = [], 0, 0
fp = (osmium.FileProcessor(str(PBF), osmium.osm.NODE | osmium.osm.WAY)
      .with_locations(storage="sparse_mem_array")
      .with_filter(osmium.filter.KeyFilter("highway","traffic_calming","railway","barrier").enable_for(osmium.osm.NODE))
      .with_filter(osmium.filter.KeyFilter("junction","tunnel","bridge","traffic_calming").enable_for(osmium.osm.WAY)))
log("scanning england-latest.osm.pbf ...")
for o in fp:
    n_py += 1
    if n_py % 1_000_000 == 0: log(f"  {n_py/1e6:.0f} M tagged objects reached Python, {len(rows):,} landmarks kept")
    tg = o.tags
    if o.is_node():
        lon, lat = o.location.lon, o.location.lat
        if not inbox(lon, lat): continue
        types = []
        h = tg.get("highway")
        if h in HWY_NODE: types.append(f"highway={h}")
        if tg.get("railway") == "level_crossing": types.append("railway=level_crossing")
        b = tg.get("barrier")
        if b in BARRIER: types.append(f"barrier={b}")
        tc = tg.get("traffic_calming")
        if tc and tc != "no": types.append(f"traffic_calming={tc}")
        for t in types:
            rows.append(("n", o.id, t, [lon], [lat], []))
    else:
        h = tg.get("highway")
        if h not in MOTOR: continue
        types = []
        if tg.get("junction") in ("roundabout", "circular"): types.append("junction=roundabout")
        if tg.get("tunnel") == "yes": types.append("tunnel=yes")
        if tg.get("bridge") in ("yes", "viaduct"): types.append("bridge=yes")
        tc = tg.get("traffic_calming")
        if tc and tc != "no": types.append(f"traffic_calming={tc}")
        if not types: continue
        lons, lats, refs = [], [], []
        for nd in o.nodes:
            if nd.location.valid(): lons.append(nd.lon); lats.append(nd.lat); refs.append(nd.ref)
        if len(lons) < len(o.nodes): bad_ways += 1
        if not lons or not any(inbox(a, b) for a, b in zip(lons, lats)): continue
        for t in types:
            rows.append(("w", o.id, t, lons, lats, refs))
L = pd.DataFrame(rows, columns=["osm_type","osm_id","tag","lons","lats","refs"])
L.to_parquet(CACHE, index=False)
log(f"scan done: {n_py:,} tagged objects reached Python; {len(L):,} landmarks in the dataset area; "
    f"ways with missing node locations: {bad_ways}")
log(f"peak memory {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2:.1f} GB")

# ───────────────────────── 3 · group roundabout ways into physical roundabouts ─────────────────────────
parent = {}
def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
rb = L[L.tag == "junction=roundabout"]
for refs in rb.refs:
    for a in refs[1:]: parent[find(a)] = find(refs[0])
features = []                                   # (uid, tag, is_way, points_xy)
for tag, grp in L.groupby("tag"):
    if tag == "junction=roundabout":
        g2 = {}
        for _, w in grp.iterrows(): g2.setdefault(find(w.refs[0]), []).append(w)
        for root, ws in g2.items():
            pts = np.vstack([densify(xy(w.lons, w.lats))[0] for w in ws])
            features.append((f"rb{root}", tag, True, pts))
    else:
        for _, w in grp.iterrows():
            pts = densify(xy(w.lons, w.lats))[0] if w.osm_type == "w" else xy(w.lons, w.lats)
            features.append((f"{w.osm_type}{w.osm_id}", tag, w.osm_type == "w", pts))
log(f"{len(features):,} physical landmark features ({rb.shape[0]:,} roundabout ways merged into "
    f"{sum(1 for f in features if f[1]=='junction=roundabout'):,} roundabouts)")

# ───────────────────────── 4 · match to the tracks ─────────────────────────
passes = []
for uid, tag, is_way, Pf in features:
    dmin, _ = tree.query(Pf, distance_upper_bound=BUF)
    hit = np.flatnonzero(np.isfinite(dmin))
    if not len(hit): continue
    nb = tree.query_ball_point(Pf[hit], r=BUF)
    wi = np.concatenate([np.full(len(n), hit[k]) for k, n in enumerate(nb)])
    rj = np.concatenate([np.asarray(n, int) for n in nb])
    tr, al = P_trk[rj], P_al[rj]
    for t in np.unique(tr):
        m = tr == t; o_ = np.argsort(al[m]); a = al[m][o_]; w = wi[m][o_]
        cuts = np.flatnonzero(np.diff(a) > SPLIT) + 1
        for ca, cw in zip(np.split(a, cuts), np.split(w, cuts)):
            if tag in ("tunnel=yes", "bridge=yes") and len(np.unique(cw))/len(Pf) < PARALLEL_FRAC:
                continue                                   # crossing over/under it, not driving on it
            passes.append((int(t), uid, tag, float(np.median(ca))))
PS = pd.DataFrame(passes, columns=["tid","uid","tag","along_m"]).merge(TR[["tid","driver","drive","session"]], on="tid")
PS.to_parquet(PASSES, index=False)
log(f"{len(PS):,} landmark passes matched")

# ───────────────────────── 5 · statistics ─────────────────────────
def group(tag):
    if tag.startswith("traffic_calming="): return "traffic_calming=*"
    return tag
PS["type"] = PS.tag.map(group)
GROUPS = {
  "TURN  (gyro)":           ["junction=roundabout","highway=mini_roundabout","highway=turning_circle"],
  "STOP  (classifier)":     ["highway=traffic_signals","highway=stop","highway=give_way",
                             "railway=level_crossing","barrier=toll_booth","barrier=lift_gate"],
  "JOLT  (accelerometer)":  ["traffic_calming=*","barrier=cattle_grid"],
  "HIGHWAY":                ["highway=motorway_junction","tunnel=yes","bridge=yes"],
  "OTHER":                  ["highway=crossing","highway=speed_camera","highway=milestone"],
}
DRIVERS = ["E","B","A","D"]
km = TR.groupby("driver").length.sum()/1000

def coverage(tids, alongs_by_tid):
    tot = hit = 0
    for t in tids:
        Lm = TR.loc[TR.tid == t, "length"].iloc[0]
        if Lm < 1000: continue
        s = np.arange(0, Lm-1000, 100); a = alongs_by_tid.get(t, np.array([]))
        tot += len(s)
        if len(a):
            i = np.searchsorted(a, s)
            hit += int(((i < len(a)) & (a[np.minimum(i, len(a)-1)] <= s+1000)).sum())
    return 100*hit/tot if tot else float("nan")

recs = []
def stat(label, tags):
    sub = PS[PS.type.isin(tags)]
    r = {"type": label}
    for D in DRIVERS:
        s = sub[sub.driver == D]; tids = TR[TR.driver == D].tid
        al = {t: np.sort(g.along_m.to_numpy()) for t, g in s.groupby("tid")}
        r[f"{D}_per_km"] = len(s)/km.get(D, np.nan)
        r[f"{D}_unique"] = s.uid.nunique()
        r[f"{D}_pct_1km"] = coverage(tids, al)
    recs.append(r); return r

print("\n" + "="*104)
print("OSM LANDMARKS ALONG THE IO-VNBD ROUTES   ·   passes per km driven  |  % of 1 km blackouts containing one")
print("="*104)
print(f"  {'':<28}" + "".join(f"{'driver '+D:>19}" for D in DRIVERS))
print(f"  {'km of track':<28}" + "".join(f"{km.get(D,0):>19.0f}" for D in DRIVERS))
for gname, tags in GROUPS.items():
    print(f"\n  {gname}")
    for t in tags:
        r = stat(t, [t])
        print(f"    {t:<26}" + "".join(f"{r[D+'_per_km']:>9.2f}/km {r[D+'_pct_1km']:>4.0f}%" for D in DRIVERS))
    r = stat(f"ANY {gname.split()[0]}", tags)
    print(f"    {'→ any of the above':<26}" + "".join(f"{r[D+'_per_km']:>9.2f}/km {r[D+'_pct_1km']:>4.0f}%" for D in DRIVERS))

strong = GROUPS["TURN  (gyro)"] + GROUPS["STOP  (classifier)"] + GROUPS["JOLT  (accelerometer)"]
r = stat("ANY STRONG (turn/stop/jolt)", strong)
print(f"\n  {'ANY STRONG (turn/stop/jolt)':<30}" + "".join(f"{r[D+'_per_km']:>7.2f}/km {r[D+'_pct_1km']:>4.0f}%" for D in DRIVERS))
r = stat("ANY STRONG + HIGHWAY", strong + GROUPS["HIGHWAY"])
print(f"  {'ANY STRONG + HIGHWAY':<30}" + "".join(f"{r[D+'_per_km']:>7.2f}/km {r[D+'_pct_1km']:>4.0f}%" for D in DRIVERS))

print("\n  traffic_calming breakdown (all drivers): " +
      ", ".join(f"{k.split('=')[1]} {v}" for k, v in PS[PS.type=='traffic_calming=*'].tag.value_counts().items()))

print("\n  CROSS-CHECK against motion signatures from the vehicle GPS course (MAP_LANDMARK_APPROACH.md §3.4)")
gyro_rb = {"E": 0.25, "B": 0.93, "A": 1.35, "D": 1.52}
for D in DRIVERS:
    osm = len(PS[(PS.driver==D) & PS.type.isin(["junction=roundabout","highway=mini_roundabout"])])/km[D]
    print(f"    driver {D}: roundabouts OSM {osm:.2f}/km   vs   detected from motion {gyro_rb[D]:.2f}/km")

pd.DataFrame(recs).to_csv(OUT, index=False)
log(f"wrote {OUT.relative_to(ROOT)}, {PASSES.relative_to(ROOT)}, {CACHE.relative_to(ROOT)}")
