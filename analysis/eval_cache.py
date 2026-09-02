"""
Build one cache that everything downstream can run from: features, labels, true speed,
and the drive/session index each window came from — so blackouts can be simulated
without ever touching parquet again.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, time
from pathlib import Path
CLEAN = Path("data/clean"); M = Path("models"); FS, W, HOP = 10.0, 20, 5

def feats(a, g):
    am = np.linalg.norm(a, axis=1); gm = np.linalg.norm(g, axis=1)
    f = [am.mean(), am.std(), am.min(), am.max(), np.abs(np.diff(am)).mean(),
         gm.mean(), gm.std(), gm.max()]
    for c in range(3):
        f += [a[:,c].std(), np.abs(np.diff(a[:,c])).mean(), g[:,c].std()]
    for c in range(3):
        P = np.abs(np.fft.rfft(a[:,c] - a[:,c].mean()))**2
        fr = np.fft.rfftfreq(W, 1/FS)
        for lo, hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)):
            f.append(np.log(P[(fr>=lo)&(fr<hi)].sum() + 1e-9))
    return f

t0 = time.time()
A = pd.read_csv("data/alignment.csv")
sel = A[(A.sync_r.abs() >= 0.40) & A.sync_r.notna()]; sel = sel[sel.drive != "Vtb1"]
F, LAB, DRV, SESS, VEND, DV, MOV = [], [], [], [], [], [], []
sess_id = 0
for _, r in sel.iterrows():
    d = pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d = d[(d.session == r.session) & d.aligned_valid].reset_index(drop=True)
    if len(d) < 3000: continue
    a = d[["ax","ay","az"]].to_numpy(); g = d[["gx_c","gy_c","gz_c"]].to_numpy()
    v = d.speed_best_al.to_numpy()/3.6
    ok = np.isfinite(a).all(1) & np.isfinite(g).all(1) & np.isfinite(v)
    a, g, v = a[ok], g[ok], v[ok]
    if len(v) < 3000: continue
    for i in range(0, len(v)-W, HOP):
        seg = v[i:i+W]
        F.append(feats(a[i:i+W], g[i:i+W]))
        VEND.append(v[i+W-1])                                  # speed at window end, m/s
        DV.append(v[i+W-1] - v[i+W-1-HOP])                     # true Δv over one hop
        LAB.append(0 if seg.max()*3.6 < 1.0 else (1 if seg.min()*3.6 > 5.0 else -1))
        MOV.append(seg.min()*3.6 > 1.4)
        DRV.append(r.driver); SESS.append(sess_id)
    sess_id += 1
np.savez_compressed(M/"eval_cache.npz",
    X=np.array(F, np.float32), label=np.array(LAB, np.int8),
    driver=np.array(DRV), session=np.array(SESS, np.int16),
    v_end=np.array(VEND, np.float32), dv=np.array(DV, np.float32),
    moving=np.array(MOV, bool))
print(f"cached {len(F):,} windows from {sess_id} sessions in {time.time()-t0:.0f}s "
      f"({(M/'eval_cache.npz').stat().st_size/1e6:.0f} MB)")
