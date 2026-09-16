"""Does core/roadnet_build.py build exactly what step 4 built?

Rebuilds the England network with the shared module, using step 4's area rule (every drivable way with a node in a
map cell within two cells of a track), into a temporary file, and compares every array — values and types — with
data/osm/road_network.npz, the network the round-2 results were measured on. Nothing in data/ is written.

Output: round2/out/roadnet_build_check_run.txt.  Run from the repo root:
  .venv/bin/python3 round2/analysis/roadnet_build_check.py"""
import warnings; warnings.filterwarnings("ignore")
import sys, time, tempfile
from pathlib import Path
import numpy as np

R2 = Path(__file__).resolve().parents[1]
ROOT = R2.parent
sys.path.insert(0, str(R2))
from core import sessions, roadnet, roadnet_build

T0 = time.time()
PBF = ROOT/"data/osm/england-latest.osm.pbf"
DX, DY = 0.02, 0.012           # step 4's map cells
def log(m): print(f"[{time.time()-T0:5.0f}s] {m}", flush=True)


SESS = [S for S in (sessions.load(r.drive, r.driver, int(r.session)) for _, r in sessions.selected().iterrows())
        if S is not None]
lat_all = np.concatenate([S.lat for S in SESS])
lon_all = np.concatenate([S.lon for S in SESS])
LON0, LAT0 = np.nanmin(lon_all) - 0.1, np.nanmin(lat_all) - 0.1
LON1, LAT1 = np.nanmax(lon_all) + 0.1, np.nanmax(lat_all) + 0.1
OCC = set()
for S in SESS:
    ok = np.isfinite(S.lat) & np.isfinite(S.lon)
    for a, b in set(zip(((S.lon[ok] - LON0)//DX).astype(int).tolist(), ((S.lat[ok] - LAT0)//DY).astype(int).tolist())):
        for da in (-2, -1, 0, 1, 2):
            for db in (-2, -1, 0, 1, 2):
                OCC.add((a + da, b + db))
log(f"{len(SESS)} sessions, {len(OCC):,} map cells around the tracks")


def keep(ns, k):
    """Step 4's area rule, unchanged."""
    n0 = ns[0]
    if not (LON0 - 0.3 < n0.lon < LON1 + 0.3 and LAT0 - 0.2 < n0.lat < LAT1 + 0.2):
        return False
    for q in list(range(0, k, 3)) + [k - 1]:
        nq = ns[q]
        if (int((nq.lon - LON0)//DX), int((nq.lat - LAT0)//DY)) in OCC:
            return True
    return False


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp)/"road_network_rebuilt.npz"
    roadnet_build.build(PBF, out, keep=keep, log=log)
    old, new = np.load(roadnet.PATH), np.load(out)
    names = sorted(set(old.files) | set(new.files))
    differ = []
    for name in names:
        if name not in old.files or name not in new.files:
            differ.append(f"{name}: only in {'the rebuild' if name in new.files else 'step 4'}")
            continue
        a, b = old[name], new[name]
        same = (a.dtype == b.dtype and a.shape == b.shape
                and np.array_equal(a, b, equal_nan=a.dtype.kind == "f"))
        if not same:
            differ.append(f"{name}: step 4 {a.dtype}{a.shape} against rebuild {b.dtype}{b.shape}")

print(f"\n  {len(names)} arrays compared with {roadnet.PATH.relative_to(ROOT)}")
if differ:
    print("  DIFFERENCES — the shared build does not reproduce step 4:")
    for d in differ:
        print(f"    {d}")
else:
    print("  EVERY ARRAY IDENTICAL — values and types: the shared build reproduces step 4's England network exactly")
log("done")
