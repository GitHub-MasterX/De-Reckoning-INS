"""Which map landmarks the sensors can actually use (round2/MAP_LANDMARK_APPROACH.md §12.2).
1. Roundabouts: do motion-signature roundabouts sit on OSM roundabouts, and are OSM roundabout
   passes seen as turning signatures?
2. Stops: of traffic-signal passes, how many had a real stop? How many stops are explained by a
   mapped stop feature?
3. Realistic coverage: % of 1 km windows with a USABLE landmark (roundabout seen by motion, or a
   mapped stop feature where the vehicle actually stopped).
Motion comes from the vehicle GPS course and speed, so this is a best case for the phone.
Needs the outputs of osm_landmarks.py (data/osm/landmark_passes.parquet, landmarks_iovnbd.parquet)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy.spatial import cKDTree
from scipy.ndimage import maximum_filter1d, uniform_filter1d
ROOT = Path(__file__).resolve().parents[2]; FS = 10.0
PS = pd.read_parquet(ROOT/"data/osm/landmark_passes.parquet")
L  = pd.read_parquet(ROOT/"data/osm/landmarks_iovnbd.parquet")
def xy(lon, lat):
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    return np.c_[lon*111320.0*np.cos(np.radians(lat)), lat*110540.0]
def densify(p, step=5.0):
    if len(p) < 2: return p
    s = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(p, axis=0).T)))); k = np.r_[True, np.diff(s) > 0]
    p, s = p[k], s[k]
    if len(p) < 2: return p
    g = np.r_[np.arange(0, s[-1], step), s[-1]]
    return np.c_[np.interp(g, s, p[:,0]), np.interp(g, s, p[:,1])]
RB = cKDTree(np.vstack([densify(xy(w.lons, w.lats)) for _, w in L[L.tag=="junction=roundabout"].iterrows()]
                     + [xy(w.lons, w.lats) for _, w in L[L.tag=="highway=mini_roundabout"].iterrows()]))
STOP_TAGS = {"highway=traffic_signals","highway=give_way","highway=stop","railway=level_crossing",
             "barrier=lift_gate","barrier=toll_booth"}
def win(cum, W):
    h = W//2; out = np.zeros(len(cum)); out[h:-h] = cum[W:] - cum[:len(cum)-W]; return out
def nms(score, W, cand):
    idx = np.flatnonzero(cand & (score == maximum_filter1d(score, size=W)))
    return np.array([i for k, i in enumerate(idx) if k == 0 or i - idx[k-1] > W//2], int)
def coverage(length, alongs):
    if length < 1000: return 0, 0
    s = np.arange(0, length-1000, 100); a = np.sort(np.asarray(alongs, float))
    if not len(a): return len(s), 0
    i = np.searchsorted(a, s)
    return len(s), int(((i < len(a)) & (a[np.minimum(i, len(a)-1)] <= s+1000)).sum())

A = pd.read_csv(ROOT/"data/alignment.csv")
sel = A[(A.sync_r.abs() >= 0.40) & A.sync_r.notna()]; sel = sel[sel.drive != "Vtb1"]
Z = {D: dict(km=0.0, mot=0, mot25=0, mot50=0, spd_on=[], spd_off=[], osm_rb=0, osm_rb_seen=0,
             sig=0, sig_stop=0, stoptag=0, stoptag_stop=0, stops=0, stops_mapped=0,
             w_tot=0, w_use=0, w_osm=0) for D in "ABDE"}
for _, r in sel.iterrows():
    base = pd.read_parquet(ROOT/f"data/clean/{r.drive}.parquet")
    d = base[(base.session == r.session) & base.aligned_valid]
    if len(d) < 3000: continue
    vi = d.veh_idx.to_numpy()
    lat = base.lat.to_numpy()[vi]; lon = base.lon.to_numpy()[vi]
    hd = base.heading.to_numpy()[vi]; v = d.speed_best_al.to_numpy()/3.6
    ok = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) > 1)
    lat, lon, hd, v = lat[ok], lon[ok], hd[ok], v[ok]
    if len(lat) < 100: continue
    p = xy(lon, lat); stp = np.hypot(*np.diff(p, axis=0).T); stp[stp > 50] = 0.0
    along = np.concatenate(([0], np.cumsum(stp)))                 # identical construction to the scan
    vv = np.nan_to_num(v); hdf = pd.Series(hd).ffill().bfill().to_numpy()
    rate = np.gradient(np.unwrap(np.radians(hdf)))*FS; rate[vv < 2] = 0.0
    Ha = np.concatenate(([0], np.cumsum(np.abs(rate))/FS))[:len(vv)]
    tot = np.degrees(win(Ha, 250)); vmean = uniform_filter1d(vv, 250)*3.6
    ev = nms(tot, 250, (tot >= 150) & (vmean < 45))
    still = vv < 0.28; starts = np.flatnonzero(np.diff(still.astype(int)) == 1) + 1
    st = np.array([i for i in starts if still[i:i+30].all()], int)
    stop_al = along[st]
    z = Z[r.driver]; z["km"] += along[-1]/1000
    sp = PS[(PS.drive == r.drive) & (PS.session == r.session)]

    # 1 · roundabouts
    if len(ev):
        dist, _ = RB.query(p[ev]); z["mot"] += len(ev)
        z["mot25"] += int((dist <= 25).sum()); z["mot50"] += int((dist <= 50).sum())
        z["spd_on"] += list(vmean[ev][dist <= 50]); z["spd_off"] += list(vmean[ev][dist > 50])
    rb_al = sp[sp.tag.isin(["junction=roundabout","highway=mini_roundabout"])].along_m.to_numpy()
    seen = np.array([len(ev) > 0 and np.min(np.abs(along[ev] - a)) <= 150 for a in rb_al], bool)
    z["osm_rb"] += len(rb_al); z["osm_rb_seen"] += int(seen.sum())

    # 2 · stops at mapped stop features
    def stopped_at(a): return len(stop_al) > 0 and bool(((stop_al >= a-60) & (stop_al <= a+20)).any())
    sig_al = sp[sp.tag == "highway=traffic_signals"].along_m.to_numpy()
    st_al  = sp[sp.tag.isin(STOP_TAGS)].along_m.to_numpy()
    sig_hit = np.array([stopped_at(a) for a in sig_al], bool)
    st_hit  = np.array([stopped_at(a) for a in st_al], bool)
    z["sig"] += len(sig_al); z["sig_stop"] += int(sig_hit.sum())
    z["stoptag"] += len(st_al); z["stoptag_stop"] += int(st_hit.sum())
    z["stops"] += len(stop_al)
    z["stops_mapped"] += int(sum(((st_al >= s-20) & (st_al <= s+60)).any() for s in stop_al)) if len(st_al) else 0

    # 3 · realistic coverage
    usable = np.r_[rb_al[seen], st_al[st_hit]]
    strong_osm = sp[sp.tag.isin(STOP_TAGS | {"junction=roundabout","highway=mini_roundabout",
                                             "highway=turning_circle","barrier=cattle_grid"})
                    | sp.tag.str.startswith("traffic_calming=")].along_m.to_numpy()
    t_, u_ = coverage(along[-1], usable); _, o_ = coverage(along[-1], strong_osm)
    z["w_tot"] += t_; z["w_use"] += u_; z["w_osm"] += o_

pct = lambda a, b: 100*a/b if b else float("nan")
print("1 · ROUNDABOUTS — motion signature vs OpenStreetMap\n")
print(f"  {'driver':<7}{'motion events/km':>17}{'on an OSM roundabout (≤25 m / ≤50 m)':>40}"
      f"{'OSM roundabouts seen by motion':>33}{'speed: on / off OSM':>22}")
for D in "EBAD":
    z = Z[D]
    print(f"  {D:<7}{z['mot']/z['km']:>17.2f}{pct(z['mot25'],z['mot']):>31.0f}% / {pct(z['mot50'],z['mot']):>3.0f}%"
          f"{pct(z['osm_rb_seen'],z['osm_rb']):>32.0f}%"
          f"{np.median(z['spd_on']) if z['spd_on'] else float('nan'):>13.0f} / {np.median(z['spd_off']) if z['spd_off'] else float('nan'):.0f} km/h")
print("\n2 · STOPS — is a mapped stop feature an actual stop?\n")
print(f"  {'driver':<7}{'signal passes':>14}{'…with a stop':>14}{'all stop-tag passes w/ stop':>30}"
      f"{'stops/km':>10}{'stops explained by a mapped feature':>38}")
for D in "EBAD":
    z = Z[D]
    print(f"  {D:<7}{z['sig']:>14}{pct(z['sig_stop'],z['sig']):>13.0f}%{pct(z['stoptag_stop'],z['stoptag']):>29.0f}%"
          f"{z['stops']/z['km']:>10.2f}{pct(z['stops_mapped'],z['stops']):>37.0f}%")
print("\n3 · 1 km BLACKOUTS CONTAINING A LANDMARK\n")
print(f"  {'driver':<7}{'strong OSM landmark present':>30}{'USABLE (seen / actually stopped)':>36}")
for D in "EBAD":
    z = Z[D]
    print(f"  {D:<7}{pct(z['w_osm'],z['w_tot']):>29.0f}%{pct(z['w_use'],z['w_tot']):>35.0f}%")
