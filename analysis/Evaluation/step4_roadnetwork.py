"""Round 2 · Step 4 — the drivable road network around the routes, from the England OSM file, checked against the
true tracks.

  1  scan the map and build   -> data/osm/road_network.npz (git-ignored; --reuse skips the scan if it exists)
  2  what the network contains
  3  true tracks against the network: on a road in an allowed direction, one-way conflicts, off the network
  4  can the network carry the true routes: consecutive matches connected along drivable directions
  4b why some consecutive matches are not connected
Region: every drivable way with a node within about 2.5 km of a track. Not a leak — a 1 km blackout cannot leave a
1.3 km circle around its start, and the start lies on the track.
Outputs: round2/out/step4_run.txt, roadnet_check.csv, roadnet_gaps.csv, roadnet_disconnected.csv.
Run from the repo root:  .venv/bin/python3 round2/step4_roadnetwork.py [--reuse]"""
import warnings; warnings.filterwarnings("ignore")
import sys, time, array, resource
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import sessions, roadnet
from core.Engine.geo import enu

T0 = time.time()
PBF = ROOT/"data/osm/england-latest.osm.pbf"
DX, DY = 0.02, 0.012           # map cells of about 1.4 km; kept with a 2-cell margin around the tracks
ORDER = ["E", "B", "A", "D"]
RADIUS, BEARING = 20.0, 30.0
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*104}\n{t}\n{'='*104}")


def parse_speed(s):
    """OSM maxspeed to km/h; NaN for 'national', 'none' and the like."""
    if not s:
        return np.nan
    s = s.strip().lower()
    try:
        if s.endswith("mph"):
            return float(s[:-3])*1.609344
        return float(s.replace("km/h", "").replace("kmh", ""))
    except ValueError:
        return np.nan


SESS = {}
for _, r in sessions.selected().iterrows():
    S = sessions.load(r.drive, r.driver, int(r.session))
    if S is not None:
        SESS[(S.drive, S.session)] = S
log(f"{len(SESS)} sessions loaded")

# ───────────────────────── 1 · scan and build ─────────────────────────
if "--reuse" in sys.argv and roadnet.PATH.exists():
    log(f"reusing {roadnet.PATH.relative_to(ROOT)} (build log: round2/out/step4_build_run.txt)")
else:
    import osmium
    lat_all = np.concatenate([S.lat for S in SESS.values()])
    lon_all = np.concatenate([S.lon for S in SESS.values()])
    LON0, LAT0 = np.nanmin(lon_all) - 0.1, np.nanmin(lat_all) - 0.1
    LON1, LAT1 = np.nanmax(lon_all) + 0.1, np.nanmax(lat_all) + 0.1
    OCC = set()
    for S in SESS.values():
        ok = np.isfinite(S.lat) & np.isfinite(S.lon)
        for a, b in set(zip(((S.lon[ok] - LON0)//DX).astype(int).tolist(), ((S.lat[ok] - LAT0)//DY).astype(int).tolist())):
            for da in (-2, -1, 0, 1, 2):
                for db in (-2, -1, 0, 1, 2):
                    OCC.add((a + da, b + db))
    log(f"{len(OCC):,} map cells around the tracks")

    refs, lons, lats = array.array("q"), array.array("d"), array.array("d")
    W = dict(way=[], cls=[], flags=[], layer=[], speed=[], fwd=[], bwd=[], count=[])
    fp = (osmium.FileProcessor(str(PBF), osmium.osm.NODE | osmium.osm.WAY)
          .with_locations(storage="sparse_mem_array")
          .with_filter(osmium.filter.KeyFilter("highway")))
    seen = kept = bad = 0
    for o in fp:
        if not o.is_way():
            continue
        tags = o.tags
        hw = tags.get("highway")
        c = roadnet.CLASS_CODE.get(hw, -1)
        if c < 0 or tags.get("area") == "yes":
            continue
        seen += 1
        if seen % 1_000_000 == 0:
            log(f"  {seen:,} drivable ways seen, {kept:,} kept, {len(refs):,} node references")
        ns = o.nodes
        k = len(ns)
        if k < 2:
            continue
        try:
            n0 = ns[0]
            if not (LON0 - 0.3 < n0.lon < LON1 + 0.3 and LAT0 - 0.2 < n0.lat < LAT1 + 0.2):
                continue
            hit = False
            for q in list(range(0, k, 3)) + [k - 1]:
                nq = ns[q]
                if (int((nq.lon - LON0)//DX), int((nq.lat - LAT0)//DY)) in OCC:
                    hit = True
                    break
            if not hit:
                continue
            rr = [x.ref for x in ns]
            xx = [x.lon for x in ns]
            yy = [x.lat for x in ns]
        except Exception:
            bad += 1
            continue
        rb = tags.get("junction") in ("roundabout", "circular")
        ow = tags.get("oneway")
        implied = rb or hw == "motorway"
        if ow in ("yes", "true", "1"):
            fwd, bwd = True, False
        elif ow in ("-1", "reverse"):
            fwd, bwd = False, True
        elif ow in ("no", "false", "0", "reversible", "alternating"):
            fwd, bwd = True, True
        else:
            fwd, bwd = True, not implied
        flags = ((roadnet.ROUNDABOUT if rb else 0)
                 | (roadnet.BRIDGE if tags.get("bridge", "no") != "no" else 0)
                 | (roadnet.TUNNEL if tags.get("tunnel", "no") != "no" else 0)
                 | (roadnet.RESTRICTED if tags.get("access") in ("no", "private")
                    or tags.get("motor_vehicle") in ("no", "private") else 0)
                 | (roadnet.PARKING if tags.get("service") in ("parking_aisle", "driveway", "drive-through") else 0)
                 | (roadnet.IMPLIED_ONEWAY if implied and ow is None else 0))
        try:
            layer = int(float(tags.get("layer", "0")))
        except ValueError:
            layer = 0
        refs.extend(rr)
        lons.extend(xx)
        lats.extend(yy)
        W["way"].append(o.id); W["cls"].append(c); W["flags"].append(flags); W["layer"].append(max(-5, min(5, layer)))
        W["speed"].append(parse_speed(tags.get("maxspeed"))); W["fwd"].append(fwd); W["bwd"].append(bwd)
        W["count"].append(k)
        kept += 1
    log(f"scan done: {seen:,} drivable ways seen, {kept:,} kept, {len(refs):,} node references, {bad} with missing "
        f"locations; peak memory {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6:.1f} GB")

    R = np.frombuffer(refs, np.int64)
    LON = np.frombuffer(lons, np.float64)
    LAT = np.frombuffer(lats, np.float64)
    count = np.array(W["count"])
    way_of = np.repeat(np.arange(len(count)), count)
    node_id, first, inv = np.unique(R, return_index=True, return_inverse=True)
    node_lat, node_lon = LAT[first], LON[first]
    p = np.flatnonzero(way_of[:-1] == way_of[1:])
    u, v, w = inv[p], inv[p + 1], way_of[p]
    east, north = enu(node_lat[v], node_lon[v], node_lat[u], node_lon[u])
    seg_len = np.hypot(east, north)
    keep = (u != v) & (seg_len > 0.05)
    u, v, w, east, north, seg_len = u[keep], v[keep], w[keep], east[keep], north[keep], seg_len[keep]
    seg_bearing = np.arctan2(east, north)
    fwd = np.array(W["fwd"], bool)[w]
    bwd = np.array(W["bwd"], bool)[w]
    ef, eb = np.flatnonzero(fwd), np.flatnonzero(bwd)
    edge_from = np.r_[u[ef], v[eb]]
    seg_edge_fwd = np.full(len(u), -1, np.int64)
    seg_edge_fwd[ef] = np.arange(len(ef))
    seg_edge_bwd = np.full(len(u), -1, np.int64)
    seg_edge_bwd[eb] = len(ef) + np.arange(len(eb))
    out_edges = np.argsort(edge_from, kind="stable")
    np.savez_compressed(
        roadnet.PATH, node_id=node_id, node_lat=node_lat, node_lon=node_lon,
        seg_u=u.astype(np.int64), seg_v=v.astype(np.int64), seg_len=seg_len, seg_bearing=seg_bearing,
        seg_class=np.array(W["cls"], np.int8)[w], seg_flags=np.array(W["flags"], np.int16)[w],
        seg_layer=np.array(W["layer"], np.int8)[w], seg_maxspeed=np.array(W["speed"], np.float32)[w],
        seg_fwd=fwd, seg_bwd=bwd, seg_way=np.array(W["way"], np.int64)[w],
        seg_edge_fwd=seg_edge_fwd, seg_edge_bwd=seg_edge_bwd,
        edge_from=edge_from.astype(np.int64), edge_to=np.r_[v[ef], u[eb]].astype(np.int64),
        edge_seg=np.r_[ef, eb].astype(np.int64),
        edge_dir=np.r_[np.ones(len(ef), np.int8), -np.ones(len(eb), np.int8)],
        edge_bearing=roadnet.wrap(np.r_[seg_bearing[ef], seg_bearing[eb] + np.pi]),
        out_edges=out_edges.astype(np.int64),
        out_ptr=np.searchsorted(edge_from[out_edges], np.arange(len(node_id) + 1)).astype(np.int64))
    log(f"wrote {roadnet.PATH.relative_to(ROOT)} ({roadnet.PATH.stat().st_size/1e6:.0f} MB)")

net = roadnet.RoadNetwork()
log("network loaded and indexed")

# segments touching each node, ignoring direction — diagnosis of unconnected matches only
_ends = np.r_[net.seg_u, net.seg_v]
_order = np.argsort(_ends, kind="stable")
NODE_PTR = np.searchsorted(_ends[_order], np.arange(len(net.node_id) + 1))
NODE_SEG = np.r_[np.arange(len(net.seg_u)), np.arange(len(net.seg_u))][_order]


def reachable_any_direction(s_from, s_to, limit_m):
    """Segment s_to reachable from segment s_from within limit_m, ignoring one-way rules."""
    if s_from == s_to:
        return True
    best, stack = {}, [(int(net.seg_u[s_from]), 0.0), (int(net.seg_v[s_from]), 0.0)]
    while stack:
        node, d = stack.pop()
        for k in range(NODE_PTR[node], NODE_PTR[node + 1]):
            s = int(NODE_SEG[k])
            if s == s_to:
                return True
            other = int(net.seg_v[s]) if net.seg_u[s] == node else int(net.seg_u[s])
            nd = d + float(net.seg_len[s])
            if nd <= limit_m and nd < best.get(other, np.inf):
                best[other] = nd
                stack.append((other, nd))
    return False


# ───────────────────────── 2 · contents ─────────────────────────
head("2 · THE NETWORK")
km = net.seg_len.sum()/1000
oneway = net.seg_fwd != net.seg_bwd
print(f"  nodes {len(net.node_id):,} · segments {len(net.seg_u):,} · drivable directions {len(net.edge_from):,} · "
      f"{km:,.0f} km of road")
print(f"  one-way {100*net.seg_len[oneway].sum()/net.seg_len.sum():.0f}% of length · roundabouts "
      f"{net.seg_len[(net.seg_flags & roadnet.ROUNDABOUT) > 0].sum()/1000:,.0f} km · "
      f"private or no access {100*net.seg_len[(net.seg_flags & roadnet.RESTRICTED) > 0].sum()/net.seg_len.sum():.0f}% · "
      f"car-park aisles and driveways {100*net.seg_len[(net.seg_flags & roadnet.PARKING) > 0].sum()/net.seg_len.sum():.0f}% · "
      f"speed limit tagged {100*net.seg_len[np.isfinite(net.seg_maxspeed)].sum()/net.seg_len.sum():.0f}%")
print(f"\n  {'road class':<16}{'km':>9}{'share':>8}")
for code in np.argsort([-net.seg_len[net.seg_class == c].sum() for c in range(len(roadnet.CLASSES))]):
    L = net.seg_len[net.seg_class == code].sum()/1000
    if L > 0:
        print(f"  {roadnet.CLASSES[code]:<16}{L:>9,.0f}{100*L/km:>7.1f}%")

# ───────────────────────── 3 · tracks against the network ─────────────────────────
pts, gaps, trans = [], [], []
for (drive, session), S in SESS.items():
    idx = np.arange(0, len(S.t), 10)                                                    # one point per second
    idx = idx[(S.v[idx] > 3) & np.isfinite(S.lat[idx]) & np.isfinite(S.heading[idx]) & ~S.dropout[idx]]
    x, y = roadnet.xy(S.lat[idx], S.lon[idx])
    m = net.match(x, y, np.radians(S.heading[idx]), RADIUS, BEARING)
    cat = np.select([m["d_allowed"] <= RADIUS, m["d_aligned"] <= RADIUS, m["d_any"] <= RADIUS],
                    ["on_road", "oneway_conflict", "not_aligned"], "off_network")
    metres = S.v[idx]*np.r_[np.clip(np.diff(S.t[idx]), 0, 2), 1.0]
    pts.append(pd.DataFrame(dict(driver=S.driver, drive=drive, session=session, t=S.t[idx], lat=S.lat[idx],
                                 lon=S.lon[idx], metres=metres, cat=cat, d=m["d_allowed"],
                                 cls=np.where(m["seg"] >= 0, net.seg_class[np.maximum(m["seg"], 0)], -1))))
    # stretches of at least 10 s not on a road in an allowed direction
    bad = cat != "on_road"
    run_start = None
    for a in range(len(idx) + 1):
        cont = a < len(idx) and bad[a] and (run_start is None or idx[a] - idx[a - 1] == 10)
        if cont and run_start is None:
            run_start = a
        elif not cont and run_start is not None:
            if a - run_start >= 10:
                seg = slice(run_start, a)
                kinds, n_k = np.unique(cat[seg], return_counts=True)
                gaps.append(dict(driver=S.driver, drive=drive, session=session, t_start=round(float(S.t[idx[run_start]]), 1),
                                 seconds=int(a - run_start), metres=round(float(metres[seg].sum())),
                                 lat=round(float(S.lat[idx[run_start]]), 6), lon=round(float(S.lon[idx[run_start]]), 6),
                                 mostly=str(kinds[np.argmax(n_k)])))
            run_start = a if (a < len(idx) and bad[a]) else None
    # consecutive matched points on different directed edges: connected by drivable directions?
    e = np.where(m["seg"] >= 0, net.edge_of(np.maximum(m["seg"], 0), m["dir"]), -1)
    for a in range(len(idx) - 1):
        if e[a] < 0 or e[a + 1] < 0 or e[a] == e[a + 1] or idx[a + 1] - idx[a] != 10:
            continue
        limit = 2*max(S.v[idx[a]], S.v[idx[a + 1]]) + 50.0
        ok = net.reachable(int(e[a]), int(e[a + 1]), limit)
        rec = dict(driver=S.driver, connected=ok)
        if not ok:
            s1, s2 = int(net.edge_seg[e[a]]), int(net.edge_seg[e[a + 1]])
            ax_, ay_ = net.sx0[s1], net.sy0[s1]
            dx_, dy_ = net.sx1[s1] - ax_, net.sy1[s1] - ay_
            tt = np.clip(((x[a + 1] - ax_)*dx_ + (y[a + 1] - ay_)*dy_)/max(dx_*dx_ + dy_*dy_, 1e-9), 0.0, 1.0)
            rec.update(drive=drive, session=session, t=round(float(S.t[idx[a]]), 1),
                       lat=round(float(S.lat[idx[a]]), 6), lon=round(float(S.lon[idx[a]]), 6),
                       hop_m=float(np.hypot(x[a + 1] - ax_ - tt*dx_, y[a + 1] - ay_ - tt*dy_)),
                       any_direction=reachable_any_direction(s1, s2, limit),
                       longer_path=net.reachable(int(e[a]), int(e[a + 1]), 300.0),
                       level_change=bool(net.seg_layer[s1] != net.seg_layer[s2]),
                       class_from=roadnet.CLASSES[net.seg_class[s1]], class_to=roadnet.CLASSES[net.seg_class[s2]])
        trans.append(rec)
P = pd.concat(pts, ignore_index=True)
G = pd.DataFrame(gaps)
T = pd.DataFrame(trans)
log(f"{len(P):,} track points matched, {len(T):,} edge changes checked")

head(f"3 · TRUE TRACKS AGAINST THE NETWORK — one point per second while moving, shares of distance driven "
     f"(road within {RADIUS:g} m, direction within {BEARING:g}°)")
print("  on road       a road within 20 m, running within 30° of the car's direction, drivable that way")
print("  one-way       such a road exists, but its one-way tag forbids the car's direction")
print("  not aligned   a road within 20 m, but none running the car's way (mostly inside junctions and sharp turns)")
print("  off network   no mapped drivable road within 20 m\n")
rows = []
print(f"  {'driver':<8}{'km':>7}{'on road':>9}{'  within 10 m':>14}{'one-way':>9}{'not aligned':>13}{'off network':>13}"
      f"{'median offset':>15}")
for D in ORDER + ["all"]:
    q = P if D == "all" else P[P.driver == D]
    tot = q.metres.sum()
    share = {c: 100*q.metres[q.cat == c].sum()/tot for c in ("on_road", "oneway_conflict", "not_aligned", "off_network")}
    within10 = 100*q.metres[(q.cat == "on_road") & (q.d <= 10)].sum()/tot
    offset = q.d[q.cat == "on_road"].median()
    rows.append(dict(driver=D, km=tot/1000, within_10m=within10, median_offset_m=offset, **share))
    print(f"  {D:<8}{tot/1000:>7,.0f}{share['on_road']:>8.1f}%{within10:>13.1f}%{share['oneway_conflict']:>8.1f}%"
          f"{share['not_aligned']:>12.1f}%{share['off_network']:>12.1f}%{offset:>13.1f} m")
pd.DataFrame(rows).round(3).to_csv(ROOT/"outputs/Map_Diagnostics/roadnet_check.csv", index=False)

print(f"\n  road class under the car (share of on-road distance)")
print(f"  {'driver':<8}" + "".join(f"{roadnet.CLASSES[c][:13]:>14}" for c in (0, 1, 2, 3, 4, 6, 8, 9)) + f"{'other':>9}")
for D in ORDER:
    q = P[(P.driver == D) & (P.cat == "on_road")]
    tot = q.metres.sum()
    shares = [100*q.metres[q.cls == c].sum()/tot for c in (0, 1, 2, 3, 4, 6, 8, 9)]
    print(f"  {D:<8}" + "".join(f"{s:>13.1f}%" for s in shares) + f"{100 - sum(shares):>8.1f}%")

print(f"\n  stretches of at least 10 s not on an allowed road: per 100 km, and their share of distance")
for D in ORDER:
    g = G[G.driver == D] if len(G) else G
    dist_km = P.metres[P.driver == D].sum()/1000
    n = len(g)
    print(f"  {D:<8}{100*n/dist_km:>6.1f} per 100 km   {100*(g.metres.sum()/1000 if n else 0)/dist_km:>5.1f}% of distance"
          + (f"   mostly: " + ", ".join(f"{k} {v}" for k, v in g.mostly.value_counts().items()) if n else ""))
if len(G):
    G.sort_values("metres", ascending=False).to_csv(ROOT/"outputs/Map_Diagnostics/roadnet_gaps.csv", index=False)
    print("\n  longest ten (round2/out/Map_Diagnostics/roadnet_gaps.csv has all):")
    print(G.sort_values("metres", ascending=False).head(10).to_string(index=False))

# ───────────────────────── 4 · connectivity ─────────────────────────
head("4 · CAN THE NETWORK CARRY THE TRUE ROUTES — consecutive on-road points on different drivable directions, "
     "one second apart")
print("  connected = the second is reachable from the first along drivable directions within 2 s of driving + 50 m\n")
print(f"  {'driver':<8}{'changes':>9}{'connected':>11}{'not connected per 100 km':>26}")
for D in ORDER + ["all"]:
    q = T if D == "all" else T[T.driver == D]
    dist_km = (P.metres.sum() if D == "all" else P.metres[P.driver == D].sum())/1000
    print(f"  {D:<8}{len(q):>9,}{100*q.connected.mean():>10.1f}%{100*(~q.connected.astype(bool)).sum()/dist_km:>26.1f}")

head("4b · WHY SOME ARE NOT CONNECTED — first matching reason, in this order")
NC = T[~T.connected.astype(bool)].copy()
reasons = ["drivable, by a longer path under 300 m", "blocked only by a one-way rule",
           "different level (bridge or tunnel)", "hop to a parallel road within 15 m", "no link in the map"]
NC["reason"] = np.select(
    [NC.longer_path.astype(bool), NC.any_direction.astype(bool), NC.level_change.astype(bool), NC.hop_m <= 15],
    reasons[:4], reasons[4])
NC.to_csv(ROOT/"outputs/Map_Diagnostics/roadnet_disconnected.csv", index=False)
print(f"  {'reason':<38}" + "".join(f"{'driver ' + D:>11}" for D in ORDER) + f"{'all':>9}")
for rsn in reasons:
    cells = [f"{100*(NC[NC.driver == D].reason == rsn).mean():>10.0f}%" if (NC.driver == D).any() else f"{'-':>11}"
             for D in ORDER]
    print(f"  {rsn:<38}" + "".join(cells) + f"{100*(NC.reason == rsn).mean():>8.0f}%")
print(f"  {'not connected (count)':<38}" + "".join(f"{(NC.driver == D).sum():>11,}" for D in ORDER) + f"{len(NC):>9,}")
print(f"\n  median distance of the hop: {NC.hop_m.median():.1f} m")
print("\n  where they cluster (rounded to about 100 m; round2/out/Map_Diagnostics/roadnet_disconnected.csv has all):")
spots = (NC.assign(lat3=NC.lat.round(3), lon3=NC.lon.round(3))
           .groupby(["lat3", "lon3"]).agg(count=("reason", "size"), drivers=("driver", lambda s: "".join(sorted(set(s)))),
                                          main_reason=("reason", lambda s: s.value_counts().index[0]))
           .sort_values("count", ascending=False).head(8))
print(spots.to_string())
log("done")
