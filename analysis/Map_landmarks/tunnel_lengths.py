"""Road tunnel lengths in the dataset area (round2/DECISIONS.md, tunnel context).
Pieces of one tunnel that share a node are merged; twin bores stay separate.
Needs data/osm/landmarks_iovnbd.parquet from osm_landmarks.py (area = the IO-VNBD routes' bounding box)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.Engine.geo import enu

L = pd.read_parquet(ROOT/"data/osm/landmarks_iovnbd.parquet")
T = L[L.tag == "tunnel=yes"]
parent = {}
def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for refs in T.refs:
    for a in refs[1:]:
        parent[find(a)] = find(refs[0])
length = {}
for _, w in T.iterrows():
    lat, lon = np.asarray(w.lats), np.asarray(w.lons)
    e, n = enu(lat, lon, lat[0], lon[0])
    root = find(w.refs[0])
    length[root] = length.get(root, 0.0) + float(np.hypot(np.diff(e), np.diff(n)).sum())
x = np.array(sorted(length.values()))
print(f"road tunnels (tunnel=yes on motor roads), dataset area: {len(T)} ways -> {len(x)} tunnels")
print(f"  median {np.median(x):.0f} m   mean {x.mean():.0f} m   90th percentile {np.quantile(x, .9):.0f} m"
      f"   longest {x.max():.0f} m")
for t in (50, 100, 250, 500, 1000):
    print(f"  at least {t:>4} m: {100*(x >= t).mean():5.1f}%  ({(x >= t).sum()})")
