"""Build a drivable road network — the .npz layout core/roadnet.py reads — from an OSM file.

The same rules as the England build inside step4_roadnetwork.py. Step 4 keeps its own copy of the code so its
committed results stay untouched; analysis/roadnet_build_check.py rebuilds England with this module and compares
every array with the network the round-2 results were measured on.

`keep(nodes, count)` chooses the area: True keeps the way. None keeps every drivable way in the file."""
import array
import resource
import numpy as np

from . import roadnet
from .geo import enu


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


def build(pbf, out_path, keep=None, log=print):
    """Scan `pbf`, keep the drivable ways `keep` accepts, write the network to `out_path`. Returns scan counts."""
    import osmium
    refs, lons, lats = array.array("q"), array.array("d"), array.array("d")
    W = dict(way=[], cls=[], flags=[], layer=[], speed=[], fwd=[], bwd=[], count=[])
    fp = (osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY)
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
            if keep is not None and not keep(ns, k):
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
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6
    log(f"scan done: {seen:,} drivable ways seen, {kept:,} kept, {len(refs):,} node references, {bad} with missing "
        f"locations; peak memory {peak_gb:.1f} GB")

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
    keep_seg = (u != v) & (seg_len > 0.05)
    u, v, w, east, north, seg_len = u[keep_seg], v[keep_seg], w[keep_seg], east[keep_seg], north[keep_seg], seg_len[keep_seg]
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
        out_path, node_id=node_id, node_lat=node_lat, node_lon=node_lon,
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
    return dict(seen=seen, kept=kept, bad=bad, peak_gb=peak_gb)
