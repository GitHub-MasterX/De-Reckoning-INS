"""Tamil Nadu road network — built from the Tamil Nadu OSM file by the same rules as the England network (step 4), and
measured on what the particle filter relies on, next to England.

  1  build: every drivable road in the file -> data/osm/road_network_tn.npz (git-ignored; --reuse skips the scans)
  2  what the network contains, next to the England network
  3  what the filter uses: junctions to confirm turns at, roundabouts, one-way and speed-limit tags
  4  map faults that break the filter: roads that cross or touch with no junction node, dead ends drawn just short
     of another road, one-way traps, and roads that cannot be driven back from. Two roads already joined to each other
     within 25 m of road are never a fault, however close they come: short segments at sharp bends and merging
     lanes bring roads within centimetres of each other legitimately
  5  tagged landmarks — signals, stop and give-way signs, crossings, speed bumps, level crossings, tolls — which the
     filter does not use today
  6  the filter's own loader reads the file and finds the roads in it

The England rows are the network the round-2 results were measured on (data/osm/road_network.npz: the roads within
about 2.5 km of the IO-VNBD tracks), inside the rectangle the England landmark scan covered, so every column counts the
same area. That network is cut out around the tracks, and the cut ends roads artificially, which can only add to
England's one-way traps and cut-off share. City rows use approximate rectangles.
There are no Tamil Nadu drives yet, so nothing here says how close the mapped roads lie to where cars really drive:
step 4's track check measures that once there are recordings.

Outputs: round2/out/tn_roadnet_run.txt (console), tn_roadnet_regions.csv, tn_map_faults.csv; the landmark scan is cached
in data/osm/landmarks_tn.parquet.
Run from the repo root:  .venv/bin/python3 round2/tn_roadnetwork.py [--reuse]"""
import warnings; warnings.filterwarnings("ignore")
import sys, time, itertools, heapq
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT/"round2"
ROOT = R2.parent
sys.path.insert(0, str(ROOT))
from core import roadnet, roadnet_build

T0 = time.time()
PBF = ROOT/"data/osm/tamil_nadu-latest.osm.pbf"
PATH = ROOT/"data/osm/road_network_tn.npz"
TN_LANDMARKS = ROOT/"data/osm/landmarks_tn.parquet"
EN_LANDMARKS = ROOT/"data/osm/landmarks_iovnbd.parquet"      # analysis/osm_landmarks.py's scan of the England area
REUSE = "--reuse" in sys.argv
CITIES = {                     # (south, west, north, east): approximate rectangles
    "Chennai": (12.85, 80.05, 13.25, 80.35),
    "Coimbatore": (10.90, 76.85, 11.10, 77.10),
    "Madurai": (9.85, 78.05, 10.00, 78.20),
    "Tiruchirappalli": (10.70, 78.60, 10.90, 78.80),
    "Salem": (11.60, 78.08, 11.72, 78.22),
}
PIECE_M = 10.0      # roads are cut into pieces no longer than this for the geometry checks
TOUCH_M = 0.5       # two roads closer than this with no shared node cross or touch without a junction
NEAR_M = 5.0        # a dead end this close to another road it is not joined to was probably meant to join it
ON_ROAD_M = 15.0    # a tagged landmark this close to a public road is on it
JOINED_M = 25.0     # two roads already joined within this much road are not a fault, however close they come
TILE_M = 5000.0     # the geometry checks run tile by tile to bound memory
LEVEL = roadnet.BRIDGE | roadnet.TUNNEL
OFF_NETWORK = roadnet.PARKING | roadnet.RESTRICTED
MAIN = [roadnet.CLASS_CODE[c] for c in ("motorway", "trunk", "primary", "secondary", "tertiary")]
MOTOR = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "service",
         "living_street", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}
LANDMARKS = [("signals", "signals", ("highway=traffic_signals",)),
             ("stop_give_way", "stop/give way", ("highway=stop", "highway=give_way")),
             ("crossings", "crossings", ("highway=crossing",)),
             ("speed_bumps", "speed bumps", ("traffic_calming=",)),
             ("mini_roundabouts", "mini r'abouts", ("highway=mini_roundabout",)),
             ("level_crossings", "level crossings", ("railway=level_crossing",)),
             ("tolls", "toll booths", ("barrier=toll_booth",))]
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)
def head(t): print(f"\n{'='*112}\n{t}\n{'='*112}")


# ───────────────────────── geometry helpers ─────────────────────────
def tile_groups(x, y, margin):
    """{tile: point indices} over TILE_M tiles; a point also joins each neighbouring tile it lies within `margin` of."""
    tx, ty = np.floor(x/TILE_M).astype(np.int64), np.floor(y/TILE_M).astype(np.int64)
    fx, fy = x - tx*TILE_M, y - ty*TILE_M
    near = {-1: (fx < margin, fy < margin), 1: (fx > TILE_M - margin, fy > TILE_M - margin)}
    idx, kx, ky = [np.arange(len(x))], [tx], [ty]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            m = np.flatnonzero((near[dx][0] if dx else True) & (near[dy][1] if dy else True))
            idx.append(m); kx.append(tx[m] + dx); ky.append(ty[m] + dy)
    idx, kx, ky = np.concatenate(idx), np.concatenate(kx), np.concatenate(ky)
    order = np.lexsort((ky, kx))
    idx, kx, ky = idx[order], kx[order], ky[order]
    cut = np.flatnonzero((np.diff(kx) != 0) | (np.diff(ky) != 0)) + 1
    return {(int(kx[s]), int(ky[s])): g for s, g in zip(np.r_[0, cut], np.split(idx, cut))}


def point_segment(px, py, ax, ay, bx, by):
    """Distance from points to segments (plane metres), and where along each segment the nearest point lies (0..1)."""
    dx, dy = bx - ax, by - ay
    l2 = dx*dx + dy*dy
    t = np.clip(((px - ax)*dx + (py - ay)*dy)/np.where(l2 > 0, l2, 1.0), 0.0, 1.0)
    return np.hypot(px - ax - t*dx, py - ay - t*dy), t


def load(path):
    """A network as plain arrays, plus node degrees and every road cut into pieces of at most PIECE_M, grouped by tile."""
    z = np.load(path)
    N = SimpleNamespace(**{k: z[k] for k in z.files})
    n, m = len(N.node_id), len(N.seg_u)
    N.nx, N.ny = roadnet.xy(N.node_lat, N.node_lon)
    N.mid_lat = (N.node_lat[N.seg_u] + N.node_lat[N.seg_v])/2
    N.mid_lon = (N.node_lon[N.seg_u] + N.node_lon[N.seg_v])/2
    N.usable = (N.seg_flags & OFF_NETWORK) == 0
    N.public = N.usable & (N.seg_class != roadnet.CLASS_CODE["service"])
    N.inc = np.bincount(np.r_[N.seg_u, N.seg_v], minlength=n)
    N.inc_public = np.bincount(np.r_[N.seg_u[N.public], N.seg_v[N.public]], minlength=n)
    N.out_deg = np.diff(N.out_ptr)
    N.in_deg = np.bincount(N.edge_to, minlength=n)
    x0, y0, x1, y1 = N.nx[N.seg_u], N.ny[N.seg_u], N.nx[N.seg_v], N.ny[N.seg_v]
    k = np.maximum(1, np.ceil(np.hypot(x1 - x0, y1 - y0)/PIECE_M)).astype(np.int64)
    s = np.repeat(np.arange(m), k)
    frac = (np.arange(k.sum()) - np.repeat(np.cumsum(k) - k, k) + 0.5)/np.repeat(k, k)
    N.piece_seg, N.px, N.py = s, x0[s] + frac*(x1[s] - x0[s]), y0[s] + frac*(y1[s] - y0[s])
    N.tiles = tile_groups(N.px, N.py, ON_ROAD_M + PIECE_M/2 + 0.01)
    ends = np.r_[N.seg_u, N.seg_v]
    order = np.argsort(ends, kind="stable")
    N.adj_ptr = np.searchsorted(ends[order], np.arange(n + 1))
    N.adj_node, N.adj_len = np.r_[N.seg_v, N.seg_u][order], np.r_[N.seg_len, N.seg_len][order]
    return N


def joined_within(N, starts, targets, limit=JOINED_M):
    """Is some target node reachable from some start node along roads, either direction, within `limit` metres?
    starts and targets map node -> metres already used to get from the place in question to that node."""
    best = dict(starts)
    heap = [(d, node) for node, d in starts.items()]
    heapq.heapify(heap)
    while heap:
        d, node = heapq.heappop(heap)
        if node in targets and d + targets[node] <= limit:
            return True
        if d > best.get(node, np.inf):
            continue
        for k in range(N.adj_ptr[node], N.adj_ptr[node + 1]):
            nd, other = d + float(N.adj_len[k]), int(N.adj_node[k])
            if nd <= limit and nd < best.get(other, np.inf):
                best[other] = nd
                heapq.heappush(heap, (nd, other))
    return False


def segment_xy(N, s):
    return N.nx[N.seg_u[s]], N.ny[N.seg_u[s]], N.nx[N.seg_v[s]], N.ny[N.seg_v[s]]


def segment_gap(N, a, b):
    """Shortest distance between segments a and b (plane metres), and where along a it falls (0..1)."""
    ax0, ay0, ax1, ay1 = segment_xy(N, a)
    bx0, by0, bx1, by1 = segment_xy(N, b)
    s1 = (ax1 - ax0)*(by0 - ay0) - (ay1 - ay0)*(bx0 - ax0)          # which side of a each end of b lies on
    s2 = (ax1 - ax0)*(by1 - ay0) - (ay1 - ay0)*(bx1 - ax0)
    s3 = (bx1 - bx0)*(ay0 - by0) - (by1 - by0)*(ax0 - bx0)          # which side of b each end of a lies on
    s4 = (bx1 - bx0)*(ay1 - by0) - (by1 - by0)*(ax1 - bx0)
    crossing = (s1*s2 < 0) & (s3*s4 < 0)
    d_a0, _ = point_segment(ax0, ay0, bx0, by0, bx1, by1)
    d_a1, _ = point_segment(ax1, ay1, bx0, by0, bx1, by1)
    d_b0, t_b0 = point_segment(bx0, by0, ax0, ay0, ax1, ay1)
    d_b1, t_b1 = point_segment(bx1, by1, ax0, ay0, ax1, ay1)
    D = np.c_[d_a0, d_a1, d_b0, d_b1]
    T = np.c_[np.zeros(len(a)), np.ones(len(a)), t_b0, t_b1]
    j, r = np.argmin(D, axis=1), np.arange(len(a))
    t_cross = s3/np.where(s3 != s4, s3 - s4, 1.0)
    return np.where(crossing, 0.0, D[r, j]), np.where(crossing, t_cross, T[r, j])


def near_pairs(N, x, y, r):
    """Every (point, segment) pair where the segment may lie within r (at most ON_ROAD_M) of the point."""
    P, S = [np.empty(0, np.int64)], [np.empty(0, np.int64)]
    for tile, group in tile_groups(x, y, 0.0).items():
        pieces = N.tiles.get(tile)
        if pieces is None:
            continue
        lists = cKDTree(np.c_[N.px[pieces], N.py[pieces]]).query_ball_point(np.c_[x[group], y[group]],
                                                                             r + PIECE_M/2 + 0.01)
        counts = np.fromiter((len(q) for q in lists), np.int64, len(group))
        P.append(np.repeat(group, counts))
        S.append(N.piece_seg[pieces[np.fromiter(itertools.chain.from_iterable(lists), np.int64, counts.sum())]])
    key = np.unique(np.concatenate(P)*len(N.seg_u) + np.concatenate(S))
    return key//len(N.seg_u), key % len(N.seg_u)


def places(lat, lon, r=10.0):
    """Labels such that points chained within r metres of each other share one: one label per place."""
    if not len(lat):
        return np.zeros(0, np.int64)
    x, y = roadnet.xy(lat, lon)
    p = cKDTree(np.c_[x, y]).query_pairs(r, output_type="ndarray")
    return connected_components(csr_matrix((np.ones(len(p)), (p[:, 0], p[:, 1])), shape=(len(x), len(x))),
                                directed=False)[1]


# ───────────────────────── the checks ─────────────────────────
def unjoined_crossings(N):
    """Two usable roads on the same level that cross, or come within TOUCH_M, with no node in common: a car can turn
    there, the network cannot."""
    m = len(N.seg_u)
    keys, gaps, ts = [np.empty(0, np.int64)], [np.empty(0)], [np.empty(0)]
    for group in N.tiles.values():
        if len(group) < 2:
            continue
        pairs = cKDTree(np.c_[N.px[group], N.py[group]]).query_pairs(PIECE_M + 0.01, output_type="ndarray")
        if not len(pairs):
            continue
        a, b = N.piece_seg[group[pairs[:, 0]]], N.piece_seg[group[pairs[:, 1]]]
        key = np.unique(np.minimum(a, b)*m + np.maximum(a, b))
        a, b = key//m, key % m
        shared = ((N.seg_u[a] == N.seg_u[b]) | (N.seg_u[a] == N.seg_v[b])
                  | (N.seg_v[a] == N.seg_u[b]) | (N.seg_v[a] == N.seg_v[b]))
        ok = ((a != b) & ~shared & N.usable[a] & N.usable[b] & (((N.seg_flags[a] | N.seg_flags[b]) & LEVEL) == 0)
              & (N.seg_layer[a] == N.seg_layer[b]))
        a, b, key = a[ok], b[ok], key[ok]
        gap, t = segment_gap(N, a, b)
        hit = gap <= TOUCH_M
        keys.append(key[hit]); gaps.append(gap[hit]); ts.append(t[hit])
    key, first = np.unique(np.concatenate(keys), return_index=True)
    a, b, gap, t = key//m, key % m, np.concatenate(gaps)[first], np.concatenate(ts)[first]
    ax0, ay0, ax1, ay1 = segment_xy(N, a)
    _, tb = point_segment(ax0 + t*(ax1 - ax0), ay0 + t*(ay1 - ay0), *segment_xy(N, b))
    la, lb = N.seg_len[a], N.seg_len[b]
    fault = np.array([not joined_within(N, {int(N.seg_u[i]): t[k]*la[k], int(N.seg_v[i]): (1 - t[k])*la[k]},
                                        {int(N.seg_u[j]): tb[k]*lb[k], int(N.seg_v[j]): (1 - tb[k])*lb[k]})
                      for k, (i, j) in enumerate(zip(a, b))], bool)
    a, b, gap, t = a[fault], b[fault], gap[fault], t[fault]
    lat = N.node_lat[N.seg_u[a]] + t*(N.node_lat[N.seg_v[a]] - N.node_lat[N.seg_u[a]])
    lon = N.node_lon[N.seg_u[a]] + t*(N.node_lon[N.seg_v[a]] - N.node_lon[N.seg_u[a]])
    return pd.DataFrame(dict(lat=lat, lon=lon, seg_a=a, seg_b=b, gap_m=gap, place=places(lat, lon)))


def short_dead_ends(N):
    """Dead ends that stop more than TOUCH_M but at most NEAR_M from a same-level road they are not joined to."""
    m = len(N.seg_u)
    own = np.full(len(N.node_id), -1, np.int64)
    own[N.seg_u] = np.arange(m)
    own[N.seg_v] = np.arange(m)
    dead = np.flatnonzero(N.inc == 1)
    dead = dead[N.usable[own[dead]]]
    pi, si = near_pairs(N, N.nx[dead], N.ny[dead], NEAR_M)
    node, so = dead[pi], own[dead[pi]]
    hang = np.where(N.seg_u[so] == node, N.seg_v[so], N.seg_u[so])          # the node the dead end hangs from
    ok = ((si != so) & (N.seg_way[si] != N.seg_way[so]) & (N.seg_u[si] != hang) & (N.seg_v[si] != hang)
          & N.usable[si] & (((N.seg_flags[si] | N.seg_flags[so]) & LEVEL) == 0) & (N.seg_layer[si] == N.seg_layer[so]))
    pi, si, node = pi[ok], si[ok], node[ok]
    gap, t = point_segment(N.nx[node], N.ny[node], *segment_xy(N, si))
    order = np.lexsort((gap, pi))
    first = order[np.r_[True, pi[order][1:] != pi[order][:-1]]] if len(order) else order
    hit = first[(gap[first] > TOUCH_M) & (gap[first] <= NEAR_M)]
    hit = hit[np.array([not joined_within(N, {int(node[h]): 0.0},
                                          {int(N.seg_u[si[h]]): t[h]*N.seg_len[si[h]],
                                           int(N.seg_v[si[h]]): (1 - t[h])*N.seg_len[si[h]]}) for h in hit], bool)]
    d = node[hit]
    return pd.DataFrame(dict(lat=N.node_lat[d], lon=N.node_lon[d], seg_a=own[d], seg_b=si[hit], gap_m=gap[hit]))


def main_parts(N):
    """Segments inside the largest strongly connected part (every road in it can be driven to and back from every other)
    and inside the largest weakly connected part (joined at all), largest by road length."""
    n = len(N.node_id)
    G = csr_matrix((np.ones(len(N.edge_from), np.float32), (N.edge_from, N.edge_to)), shape=(n, n))
    out = []
    for kind in ("strong", "weak"):
        lab = connected_components(G, directed=True, connection=kind)[1]
        a, b = lab[N.seg_u], lab[N.seg_v]
        big = int(np.argmax(np.bincount(a[a == b], weights=N.seg_len[a == b])))
        out.append((a == big) & (b == big))
    return out


def roundabouts(N):
    """One point per physical roundabout: roundabout segments joined into groups."""
    rb = (N.seg_flags & roadnet.ROUNDABOUT) > 0
    n = len(N.node_id)
    lab = connected_components(csr_matrix((np.ones(rb.sum()), (N.seg_u[rb], N.seg_v[rb])), shape=(n, n)),
                               directed=False)[1]
    nodes = np.unique(np.r_[N.seg_u[rb], N.seg_v[rb]])
    first = np.unique(lab[nodes], return_index=True)[1]
    return N.node_lat[nodes[first]], N.node_lon[nodes[first]]


def on_public_road(N, lat, lon):
    x, y = roadnet.xy(lat, lon)
    pi, si = near_pairs(N, x, y, ON_ROAD_M)
    pi, si = pi[N.public[si]], si[N.public[si]]
    gap, _ = point_segment(x[pi], y[pi], *segment_xy(N, si))
    out = np.zeros(len(x), bool)
    out[pi[gap <= ON_ROAD_M]] = True
    return out


def measure(label, N, landmarks):
    log(f"{label}: checking")
    N.cross = unjoined_crossings(N)
    N.short = short_dead_ends(N)
    N.trap = (N.in_deg > 0) & (N.out_deg == 0)                  # a guess can drive in and never out
    N.strong, N.weak = main_parts(N)
    N.rb_lat, N.rb_lon = roundabouts(N)
    L = landmarks.assign(on_road=on_public_road(N, landmarks.lat.to_numpy(), landmarks.lon.to_numpy()))
    log(f"{label}: {N.cross.place.nunique():,} crossings or touches without a node, {len(N.short):,} dead ends short of a road, "
        f"{N.trap.sum():,} one-way traps, {len(N.rb_lat):,} roundabouts, {L.on_road.sum():,} of {len(L):,} tagged "
        f"landmarks on a public road")
    return L


def region(label, N, box, L):
    def within(lat, lon):
        lat, lon = np.asarray(lat), np.asarray(lon)
        if box is None:
            return np.ones(len(lat), bool)
        s, w, n, e = box
        return (lat >= s) & (lat <= n) & (lon >= w) & (lon <= e)
    seg, node = within(N.mid_lat, N.mid_lon), within(N.node_lat, N.node_lon)
    km, pub = N.seg_len[seg].sum()/1000, N.seg_len[seg & N.public].sum()/1000
    def share(mask): return 100*N.seg_len[seg & mask].sum()/1000/km
    def per100(count): return 100*count/pub
    lm = L[within(L.lat, L.lon) & L.on_road.to_numpy()]
    row = dict(region=label, road_km=km, public_km=pub,
               junctions_per_km=(node & (N.inc_public >= 3)).sum()/pub,
               roundabouts_per_100km=per100(within(N.rb_lat, N.rb_lon).sum()),
               oneway_pct=share(N.seg_fwd != N.seg_bwd),
               speed_limit_pct=share(np.isfinite(N.seg_maxspeed)),
               bridge_pct=share((N.seg_flags & roadnet.BRIDGE) > 0),
               crossings_without_node_per_100km=per100(N.cross.place[within(N.cross.lat, N.cross.lon)
                                                                     & (N.cross.gap_m == 0)].nunique()),
               touching_without_node_per_100km=per100(N.cross.place[within(N.cross.lat, N.cross.lon)
                                                                    & (N.cross.gap_m > 0)].nunique()),
               short_dead_ends_per_100km=per100(within(N.short.lat, N.short.lon).sum()),
               oneway_traps_per_100km=per100((node & N.trap).sum()),
               cut_off_pct=share(~N.strong),
               islands_pct=share(~N.weak))
    for col, _, tags in LANDMARKS:
        row[f"{col}_per_100km"] = per100(lm.tag.map(lambda s: s.startswith(tags)).sum())
    return row


# ───────────────────────── 1 · build ─────────────────────────
if REUSE and PATH.exists():
    log(f"reusing {PATH.relative_to(ROOT)}")
else:
    log(f"scanning {PBF.relative_to(ROOT)}: every drivable way in the file is kept")
    roadnet_build.build(PBF, PATH, log=log)
    log(f"wrote {PATH.relative_to(ROOT)} ({PATH.stat().st_size/1e6:.0f} MB)")

if REUSE and TN_LANDMARKS.exists():
    LT = pd.read_parquet(TN_LANDMARKS)
    log(f"reusing {TN_LANDMARKS.relative_to(ROOT)}")
else:
    import osmium
    rows = []
    fp = (osmium.FileProcessor(str(PBF), osmium.osm.NODE | osmium.osm.WAY)
          .with_locations(storage="sparse_mem_array")
          .with_filter(osmium.filter.KeyFilter("highway", "traffic_calming", "railway", "barrier")
                       .enable_for(osmium.osm.NODE))
          .with_filter(osmium.filter.KeyFilter("traffic_calming").enable_for(osmium.osm.WAY)))
    for o in fp:                                     # the same tags analysis/osm_landmarks.py collected for England
        tg = o.tags
        tc = tg.get("traffic_calming")
        types = [f"traffic_calming={tc}"] if tc and tc != "no" else []
        if o.is_node():
            if tg.get("highway") in ("traffic_signals", "stop", "give_way", "crossing", "mini_roundabout"):
                types.append(f"highway={tg.get('highway')}")
            if tg.get("railway") == "level_crossing":
                types.append("railway=level_crossing")
            if tg.get("barrier") == "toll_booth":
                types.append("barrier=toll_booth")
            lat, lon = o.location.lat, o.location.lon
        elif types and tg.get("highway") in MOTOR:
            try:
                lat, lon = o.nodes[0].lat, o.nodes[0].lon
            except Exception:
                continue
        else:
            continue
        rows += [(t, lat, lon) for t in types]
    LT = pd.DataFrame(rows, columns=["tag", "lat", "lon"])
    LT.to_parquet(TN_LANDMARKS, index=False)
    log(f"landmark scan: {len(LT):,} tagged landmarks -> {TN_LANDMARKS.relative_to(ROOT)}")

E = pd.read_parquet(EN_LANDMARKS)
E = E[(E.osm_type == "n") | E.tag.str.startswith("traffic_calming=")]
LE = pd.DataFrame(dict(tag=E.tag.to_numpy(), lat=[a[0] for a in E.lats], lon=[a[0] for a in E.lons]))
nodes_only = (E.osm_type == "n").to_numpy()
EN_BOX = (LE.lat[nodes_only].min(), LE.lon[nodes_only].min(), LE.lat[nodes_only].max(), LE.lon[nodes_only].max())

EN = load(roadnet.PATH)
TN = load(PATH)
log(f"networks loaded: England {len(EN.px):,} pieces in {len(EN.tiles):,} tiles, "
    f"Tamil Nadu {len(TN.px):,} pieces in {len(TN.tiles):,} tiles")
LE = measure("England", EN, LE)
LT = measure("Tamil Nadu", TN, LT)

# ───────────────────────── 2 · contents ─────────────────────────
head("2 · THE NETWORK — whole files: England's is the roads around the IO-VNBD routes, Tamil Nadu's the whole state")
for label, N in (("England", EN), ("Tamil Nadu", TN)):
    total = N.seg_len.sum()
    def pct(mask): return 100*N.seg_len[mask].sum()/total
    print(f"  {label:<11}{len(N.node_id):>10,} nodes · {len(N.seg_u):>10,} segments · {len(N.edge_from):>11,} drivable "
          f"directions · {total/1000:>8,.0f} km of road")
    print(f"  {'':<11}one-way {pct(N.seg_fwd != N.seg_bwd):.0f}% of length · roundabouts "
          f"{N.seg_len[(N.seg_flags & roadnet.ROUNDABOUT) > 0].sum()/1000:,.0f} km · private or no access "
          f"{pct((N.seg_flags & roadnet.RESTRICTED) > 0):.0f}% · car-park aisles and driveways "
          f"{pct((N.seg_flags & roadnet.PARKING) > 0):.0f}% · speed limit tagged {pct(np.isfinite(N.seg_maxspeed)):.0f}%")
print(f"\n  {'road class':<16}{'England km':>12}{'share':>8}{'Tamil Nadu km':>16}{'share':>8}")
for code in np.argsort([-TN.seg_len[TN.seg_class == c].sum() for c in range(len(roadnet.CLASSES))]):
    e, t = EN.seg_len[EN.seg_class == code].sum(), TN.seg_len[TN.seg_class == code].sum()
    if e > 0 or t > 0:
        print(f"  {roadnet.CLASSES[code]:<16}{e/1000:>12,.0f}{100*e/EN.seg_len.sum():>7.1f}%"
              f"{t/1000:>16,.0f}{100*t/TN.seg_len.sum():>7.1f}%")

R = pd.DataFrame([region("England (routes)", EN, EN_BOX, LE), region("Tamil Nadu", TN, None, LT)]
                 + [region(c, TN, box, LT) for c, box in CITIES.items()])
R.round(3).to_csv(ROOT/"outputs/Map_Diagnostics/tn_roadnet_regions.csv", index=False)

# ───────────────────────── 3 · what the filter uses ─────────────────────────
head("3 · WHAT THE FILTER USES — public roads are every class but service roads, without car parks or private roads")
print("  junctions     nodes where three or more public-road segments meet, per km: each is a place a turn can pin the car to")
print("  roundabouts   physical roundabouts per 100 km")
print("  one-way       share of road length drivable one way only; the filter never lets a guess drive against it")
print("  speed limit   share of road length with a maxspeed tag; the filter's speed-limit weight needs one")
print("  bridges       share of road length on a bridge or flyover\n")
print(f"  {'region':<18}{'road km':>10}{'public km':>11}{'junctions':>11}{'roundabouts':>13}{'one-way':>10}"
      f"{'speed limit':>13}{'bridges':>10}")
print(f"  {'':<18}{'':>10}{'':>11}{'per km':>11}{'per 100 km':>13}{'% length':>10}{'% length':>13}{'% length':>10}")
for r in R.itertuples(index=False):
    print(f"  {r.region:<18}{r.road_km:>10,.0f}{r.public_km:>11,.0f}{r.junctions_per_km:>11.2f}"
          f"{r.roundabouts_per_100km:>13.1f}{r.oneway_pct:>9.1f}%{r.speed_limit_pct:>12.1f}%{r.bridge_pct:>9.1f}%")
en_all = EN.seg_len.sum()/1000
print(f"\n  England rows cover the {R.road_km[0]:,.0f} km of its {en_all:,.0f} km network inside the England landmark "
      f"scan's rectangle.")

# ───────────────────────── 4 · faults ─────────────────────────
head("4 · MAP FAULTS THAT BREAK THE FILTER — per 100 km of public road")
print("  crossing, no node    places where two roads on the same level cross with no shared node: a missing junction —")
print("                       the car can turn there and the network cannot — or a flyover with no bridge tag")
print("  touching, no node    places where two roads come within 0.5 m with no shared node: a junction drawn unjoined")
print("  dead end short       dead ends 0.5–5 m from another road they are not joined to: usually a junction drawn short")
print("  one-way trap         nodes a guess can drive into but not out of: every guess that enters dies")
print("  cut off              share of road length outside the largest part where every road can be driven to and back")
print("  islands              share of road length not joined to the largest part at all\n")
print(f"  {'region':<18}{'crossing, no node':>19}{'touching, no node':>19}{'dead end short':>16}{'one-way trap':>14}"
      f"{'cut off':>10}{'islands':>10}")
print(f"  {'':<18}{'per 100 km':>19}{'per 100 km':>19}{'per 100 km':>16}{'per 100 km':>14}{'% length':>10}{'% length':>10}")
for r in R.itertuples(index=False):
    print(f"  {r.region:<18}{r.crossings_without_node_per_100km:>19.1f}{r.touching_without_node_per_100km:>19.1f}"
          f"{r.short_dead_ends_per_100km:>16.1f}"
          f"{r.oneway_traps_per_100km:>14.1f}{r.cut_off_pct:>9.1f}%{r.islands_pct:>9.1f}%")

C = TN.cross.drop_duplicates("place")
C = C[np.isin(TN.seg_class[C.seg_a], MAIN) & np.isin(TN.seg_class[C.seg_b], MAIN)]
print(f"\n  across Tamil Nadu, {len(C):,} of the {TN.cross.place.nunique():,} places crossing or touching without a node "
      f"are between two main roads (motorway to tertiary)" + (":" if len(C) else ""))
for r in C.sample(min(5, len(C)), random_state=0).itertuples(index=False):
    print(f"    {'crossing' if r.gap_m == 0 else f'{r.gap_m:.2f} m apart':<14}{roadnet.CLASSES[TN.seg_class[r.seg_a]]} way "
          f"{TN.seg_way[r.seg_a]} × {roadnet.CLASSES[TN.seg_class[r.seg_b]]} way {TN.seg_way[r.seg_b]}   "
          f"https://www.openstreetmap.org/#map=19/{r.lat:.6f}/{r.lon:.6f}")

trap = np.flatnonzero(TN.trap)
into = np.full(len(TN.node_id), -1, np.int64)
into[TN.edge_to] = np.arange(len(TN.edge_to))
F = pd.concat([
    pd.DataFrame(dict(kind=np.where(C0.gap_m == 0, "crossing without a junction node", "touching without a junction node"), lat=C0.lat, lon=C0.lon, seg_a=C0.seg_a, seg_b=C0.seg_b,
                      gap_m=C0.gap_m)) for C0 in [TN.cross.drop_duplicates("place")]] + [
    pd.DataFrame(dict(kind="dead end short of a road", lat=TN.short.lat, lon=TN.short.lon, seg_a=TN.short.seg_a,
                      seg_b=TN.short.seg_b, gap_m=TN.short.gap_m)),
    pd.DataFrame(dict(kind="one-way trap", lat=TN.node_lat[trap], lon=TN.node_lon[trap],
                      seg_a=TN.edge_seg[into[trap]], seg_b=-1, gap_m=np.nan))], ignore_index=True)
F["city"] = ""
for c, (s, w, n, e) in CITIES.items():
    F.loc[F.lat.between(s, n) & F.lon.between(w, e), "city"] = c
for side in ("a", "b"):
    seg = F[f"seg_{side}"].to_numpy()
    F[f"way_{side}"] = np.where(seg >= 0, TN.seg_way[np.maximum(seg, 0)], -1)
    F[f"class_{side}"] = np.where(seg >= 0, np.array(roadnet.CLASSES)[TN.seg_class[np.maximum(seg, 0)]], "")
F["link"] = [f"https://www.openstreetmap.org/#map=19/{a:.6f}/{b:.6f}" for a, b in zip(F.lat, F.lon)]
F.drop(columns=["seg_a", "seg_b"]).round({"lat": 7, "lon": 7, "gap_m": 2}).to_csv(ROOT/"outputs/Map_Diagnostics/tn_map_faults.csv", index=False)
print(f"\n  every Tamil Nadu fault, with its OSM ways and a map link: round2/out/Map_Diagnostics/tn_map_faults.csv ({len(F):,} rows)")

# ───────────────────────── 5 · tagged landmarks ─────────────────────────
head("5 · TAGGED LANDMARKS — per 100 km of public road, on or within 15 m of one; the filter does not use these today")
print(f"  {'region':<18}" + "".join(f"{label:>16}" for _, label, _ in LANDMARKS))
for r in R.itertuples(index=False):
    print(f"  {r.region:<18}" + "".join(f"{getattr(r, col + '_per_100km'):>16.1f}" for col, _, _ in LANDMARKS))

# ───────────────────────── 6 · the loader ─────────────────────────
head("6 · THE FILTER'S LOADER — core/roadnet.RoadNetwork on the Tamil Nadu file")
del EN, TN, LE, LT


def rss_gb():
    with open("/proc/self/status") as f:
        return next(int(line.split()[1]) for line in f if line.startswith("VmRSS"))/1e6


before, t0 = rss_gb(), time.time()
net = roadnet.RoadNetwork(PATH)
print(f"  loads in {time.time() - t0:.0f} s and holds {rss_gb() - before:.1f} GB "
      f"({len(net.sample_seg):,} points in the nearest-road index)")
public = ((net.seg_flags & OFF_NETWORK) == 0) & (net.seg_class != roadnet.CLASS_CODE["service"]) & (net.seg_len > 20)
rng = np.random.default_rng(0)
found = 0
for sid in rng.choice(np.flatnonzero(public), 200, replace=False):
    lat = (net.node_lat[net.seg_u[sid]] + net.node_lat[net.seg_v[sid]])/2
    lon = (net.node_lon[net.seg_u[sid]] + net.node_lon[net.seg_v[sid]])/2
    heading = float(net.seg_bearing[sid]) + (0.0 if net.seg_fwd[sid] else np.pi)
    edges = net.candidates(lat, lon, heading, radius=5.0, max_bearing_deg=10.0)[0]
    found += bool(np.isin(sid, net.edge_seg[edges]))
print(f"  {found}/200 random public road segments found by the filter's own nearest-road search at their midpoints, "
      f"driving their allowed way")
log("done")
