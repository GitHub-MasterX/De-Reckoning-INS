"""Phone · a road network cut to an area and written in the binary layout the Android app reads.

The network is the one step 4 / tn_roadnetwork.py built, cut to the segments whose midpoint lies inside a box. Drivable
directions are rebuilt for the cut exactly as core/roadnet_build.py numbers them (every forward direction, then every
backward one), so the app's filter walks the same graph Python's would on that area.

  --network england|tn        which built network to cut (default tn)
  --box S,W,N,E               the area in degrees (default: the whole network)
  --name NAME                 file name: data/osm/phone/NAME.roadnet.bin

File, little-endian:
  "RNW1", n_nodes i32, n_segments i32, n_edges i32, south west north east f64, name (i32 length + UTF-8)
  node_lat f64[n], node_lon f64[n]
  seg_u i32[m], seg_v i32[m], seg_len f64[m], seg_bearing f64[m], seg_class i8[m], seg_maxspeed f32[m] (NaN untagged),
  seg_fwd i8[m], seg_bwd i8[m], seg_edge_fwd i32[m], seg_edge_bwd i32[m]
  edge_to i32[e], edge_seg i32[e], edge_dir i8[e], edge_bearing f64[e]
  out_ptr i32[n + 1], out_edges i32[e]

Put it on the phone with:  adb push data/osm/phone/NAME.roadnet.bin /sdcard/Android/data/com.sih2026.nav.live/files/roadnet/
Run from the repo root:  .venv/bin/python3 round2/phone/export_roadnet.py --box 12.85,80.05,13.25,80.35 --name chennai"""
import sys
from pathlib import Path
import numpy as np

R2 = Path(__file__).resolve().parents[1]
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import roadnet

NETWORKS = {"england": roadnet.PATH, "tn": ROOT/"data/osm/road_network_tn.npz"}
OUT_DIR = ROOT/"data/osm/phone"


def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def cut(z, box):
    """The segments with their midpoint in box, renumbered, with their drivable directions rebuilt."""
    lat, lon = z["node_lat"], z["node_lon"]
    u, v = z["seg_u"], z["seg_v"]
    mid_lat, mid_lon = (lat[u] + lat[v])/2, (lon[u] + lon[v])/2
    if box is None:
        keep = np.ones(len(u), bool)
    else:
        s, w, n, e = box
        keep = (mid_lat >= s) & (mid_lat <= n) & (mid_lon >= w) & (mid_lon <= e)
    seg = np.flatnonzero(keep)
    nodes, inv = np.unique(np.r_[u[seg], v[seg]], return_inverse=True)
    su, sv = inv[:len(seg)], inv[len(seg):]
    fwd, bwd = z["seg_fwd"][seg], z["seg_bwd"][seg]
    bearing = z["seg_bearing"][seg]
    ef, eb = np.flatnonzero(fwd), np.flatnonzero(bwd)
    edge_from = np.r_[su[ef], sv[eb]]
    edge_fwd = np.full(len(seg), -1, np.int64)
    edge_fwd[ef] = np.arange(len(ef))
    edge_bwd = np.full(len(seg), -1, np.int64)
    edge_bwd[eb] = len(ef) + np.arange(len(eb))
    out_edges = np.argsort(edge_from, kind="stable")
    return dict(
        node_lat=lat[nodes], node_lon=lon[nodes], seg_u=su, seg_v=sv, seg_len=z["seg_len"][seg], seg_bearing=bearing,
        seg_class=z["seg_class"][seg], seg_maxspeed=z["seg_maxspeed"][seg], seg_fwd=fwd, seg_bwd=bwd,
        seg_edge_fwd=edge_fwd, seg_edge_bwd=edge_bwd,
        edge_to=np.r_[sv[ef], su[eb]], edge_seg=np.r_[ef, eb],
        edge_dir=np.r_[np.ones(len(ef), np.int8), -np.ones(len(eb), np.int8)],
        edge_bearing=roadnet.wrap(np.r_[bearing[ef], bearing[eb] + np.pi]),
        out_ptr=np.searchsorted(edge_from[out_edges], np.arange(len(nodes) + 1)), out_edges=out_edges)


def write(path, name, box, c):
    n, m, e = len(c["node_lat"]), len(c["seg_u"]), len(c["edge_to"])
    if box is None:
        box = (float(c["node_lat"].min()), float(c["node_lon"].min()), float(c["node_lat"].max()), float(c["node_lon"].max()))
    raw = name.encode()
    with open(path, "wb") as f:
        f.write(b"RNW1")
        f.write(np.array([n, m, e], "<i4").tobytes())
        f.write(np.array(box, "<f8").tobytes())
        f.write(np.array([len(raw)], "<i4").tobytes())
        f.write(raw)
        for key, dtype in (("node_lat", "<f8"), ("node_lon", "<f8"), ("seg_u", "<i4"), ("seg_v", "<i4"),
                           ("seg_len", "<f8"), ("seg_bearing", "<f8"), ("seg_class", "<i1"), ("seg_maxspeed", "<f4"),
                           ("seg_fwd", "<i1"), ("seg_bwd", "<i1"), ("seg_edge_fwd", "<i4"), ("seg_edge_bwd", "<i4"),
                           ("edge_to", "<i4"), ("edge_seg", "<i4"), ("edge_dir", "<i1"), ("edge_bearing", "<f8"),
                           ("out_ptr", "<i4"), ("out_edges", "<i4")):
            f.write(np.ascontiguousarray(c[key]).astype(dtype).tobytes())
    return n, m, e


if __name__ == "__main__":
    network = arg("--network", "tn")
    box_arg = arg("--box", None)
    box = tuple(float(x) for x in box_arg.split(",")) if box_arg else None
    name = arg("--name", network)
    z = np.load(NETWORKS[network])
    c = cut(z, box)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR/f"{name}.roadnet.bin"
    n, m, e = write(path, name, box, c)
    print(f"{name}: {c['seg_len'].sum()/1000:,.0f} km of road · {n:,} nodes · {m:,} segments · {e:,} drivable directions "
          f"-> {path.relative_to(ROOT)} ({path.stat().st_size/1e6:.1f} MB)")
