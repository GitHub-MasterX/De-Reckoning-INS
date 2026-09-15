"""The drivable road network around the IO-VNBD routes, for map matching.

Built by round2/step4_roadnetwork.py from the England OSM file into data/osm/road_network.npz (git-ignored).
  nodes     OSM nodes of every kept way            node_id, node_lat, node_lon
  segments  consecutive node pairs of a way        seg_u, seg_v, seg_len (m), seg_bearing (rad, u→v, clockwise from
            (undirected geometry)                  north), seg_class, seg_flags, seg_layer, seg_maxspeed (km/h, NaN if
                                                   untagged), seg_fwd / seg_bwd (drivable u→v / v→u), seg_way,
                                                   seg_edge_fwd / seg_edge_bwd (edge id, -1 if not drivable that way)
  edges     drivable directions of segments        edge_from, edge_to, edge_seg, edge_dir (+1 / -1), edge_bearing;
                                                   the edges leaving node n are out_edges[out_ptr[n]:out_ptr[n + 1]]"""
import itertools
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT/"data/osm/road_network.npz"
CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
           "service", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link", "road")
CLASS_CODE = {name: k for k, name in enumerate(CLASSES)}
ROUNDABOUT, BRIDGE, TUNNEL, RESTRICTED, PARKING, IMPLIED_ONEWAY = 1, 2, 4, 8, 16, 32
SAMPLE_M = 25.0               # spatial-index points along segments

_A, _E2 = 6378137.0, 6.69437999014e-3
_PHI0 = np.radians(52.5)
_M0 = _A*(1 - _E2)/(1 - _E2*np.sin(_PHI0)**2)**1.5
_N0 = _A/np.sqrt(1 - _E2*np.sin(_PHI0)**2)


def xy(lat, lon):
    """Plane metres for nearest-road queries — accurate over tens of metres anywhere in the dataset area."""
    lat = np.asarray(lat, float)
    return np.radians(np.asarray(lon, float))*_N0*np.cos(np.radians(lat)), np.radians(lat)*_M0


def wrap(a):
    """Angle to [-pi, pi)."""
    return (np.asarray(a) + np.pi) % (2*np.pi) - np.pi


class RoadNetwork:
    def __init__(self, path=PATH):
        z = np.load(path)
        for key in z.files:
            setattr(self, key, z[key])
        self.sx0, self.sy0 = xy(self.node_lat[self.seg_u], self.node_lon[self.seg_u])
        self.sx1, self.sy1 = xy(self.node_lat[self.seg_v], self.node_lon[self.seg_v])
        k = np.maximum(1, np.ceil(self.seg_len/SAMPLE_M)).astype(np.int64)
        seg = np.repeat(np.arange(len(k)), k)
        frac = (np.arange(k.sum()) - np.repeat(np.cumsum(k) - k, k) + 0.5)/np.repeat(k, k)
        self.sample_seg = seg
        self.tree = cKDTree(np.c_[self.sx0[seg] + frac*(self.sx1[seg] - self.sx0[seg]),
                                  self.sy0[seg] + frac*(self.sy1[seg] - self.sy0[seg])])

    def edge_of(self, seg, dirn):
        """Directed edge id of segment `seg` driven in direction `dirn` (+1 u→v, -1 v→u); -1 if not drivable."""
        return np.where(np.asarray(dirn) > 0, self.seg_edge_fwd[seg], self.seg_edge_bwd[seg])

    def match(self, x, y, heading, radius=20.0, max_bearing_deg=30.0):
        """For points (plane metres) moving along `heading` (rad): distance to the nearest segment at all
        (d_any), to the nearest whose line agrees with the heading either way (d_aligned), and to the nearest
        that may also be driven that way (d_allowed), plus that segment and direction (seg, dir). inf / -1 if
        nothing within `radius`."""
        x, y, heading = np.asarray(x, float), np.asarray(y, float), np.asarray(heading, float)
        n = len(x)
        lists = self.tree.query_ball_point(np.c_[x, y], r=radius + SAMPLE_M/2 + 1.0)
        counts = np.fromiter((len(q) for q in lists), np.int64, n)
        out = dict(d_any=np.full(n, np.inf), d_aligned=np.full(n, np.inf), d_allowed=np.full(n, np.inf),
                   seg=np.full(n, -1, np.int64), dir=np.zeros(n, np.int8))
        if counts.sum() == 0:
            return out
        pi = np.repeat(np.arange(n), counts)
        si = self.sample_seg[np.fromiter(itertools.chain.from_iterable(lists), np.int64, counts.sum())]
        key = np.unique(pi*len(self.seg_u) + si)
        pi, si = key//len(self.seg_u), key % len(self.seg_u)
        ax, ay, dx, dy = self.sx0[si], self.sy0[si], self.sx1[si] - self.sx0[si], self.sy1[si] - self.sy0[si]
        l2 = dx*dx + dy*dy
        t = np.clip(((x[pi] - ax)*dx + (y[pi] - ay)*dy)/np.where(l2 > 0, l2, 1.0), 0.0, 1.0)
        dist = np.hypot(x[pi] - (ax + t*dx), y[pi] - (ay + t*dy))
        tol = np.radians(max_bearing_deg)
        ok_f = np.abs(wrap(heading[pi] - self.seg_bearing[si])) <= tol
        ok_b = np.abs(wrap(heading[pi] - self.seg_bearing[si] - np.pi)) <= tol
        allowed = (ok_f & self.seg_fwd[si]) | (ok_b & self.seg_bwd[si])
        near = dist <= radius
        for name, mask in (("d_any", near), ("d_aligned", near & (ok_f | ok_b)), ("d_allowed", near & allowed)):
            np.minimum.at(out[name], pi, np.where(mask, dist, np.inf))
        d_ok = np.where(near & allowed, dist, np.inf)
        order = np.lexsort((d_ok, pi))
        first = order[np.r_[True, pi[order][1:] != pi[order][:-1]]]
        good = first[np.isfinite(d_ok[first])]
        out["seg"][pi[good]] = si[good]
        out["dir"][pi[good]] = np.where(ok_f[good] & self.seg_fwd[si[good]], 1, -1)
        return out

    def reachable(self, e_from, e_to, limit_m):
        """Can directed edge e_to be reached from the end of e_from within limit_m of further driving?"""
        if e_from == e_to:
            return True
        best, stack = {}, [(int(e_from), 0.0)]
        while stack:
            e, d = stack.pop()
            v = self.edge_to[e]
            for k in range(self.out_ptr[v], self.out_ptr[v + 1]):
                f = int(self.out_edges[k])
                if f == e_to:
                    return True
                nd = d + float(self.seg_len[self.edge_seg[f]])
                if nd <= limit_m and nd < best.get(f, np.inf):
                    best[f] = nd
                    stack.append((f, nd))
        return False
