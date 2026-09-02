"""Previous screen picked the single best gyro axis. If a phone sits tilted, vehicle
yaw splits across two axes and NO single axis matches - which looks identical to a
sync failure. Fit all 3 axes jointly instead, so orientation can't masquerade as lag."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset")
def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()

def fit_r(W, y):
    """Best achievable correlation using any linear mix of the 3 gyro axes."""
    A=np.c_[W, np.ones(len(W))]
    coef,*_=np.linalg.lstsq(A, y, rcond=None)
    return np.corrcoef(A@coef, y)[0,1]

vmap={p.name.lower():p for p in (ROOT/"V-Dataset").iterdir()}
rows=[]
for sp in sorted((ROOT/"S-Dataset").iterdir()):
    vp=vmap.get(sp.name.replace("S-","V-",1).lower())
    if vp is None: continue
    try:
        S=pd.read_csv(sp,encoding="latin-1",low_memory=False); V=pd.read_csv(vp,encoding="latin-1",low_memory=False)
    except Exception: continue
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); S,V=S.iloc[:n],V.iloc[:n]
    gy=[c for c in S.columns if c.startswith("GYROSCOPE")]
    W=np.c_[num(S,gy[0]),num(S,gy[1]),num(S,gy[2])]
    yawcan=num(V,"Yaw Rate (deg/sec)")*np.pi/180
    spd=num(V,"Velocity (km/hr)")
    ok=np.isfinite(W).all(1)&np.isfinite(yawcan)&np.isfinite(spd)
    W,yawcan,spd=W[ok],yawcan[ok],spd[ok]
    if len(spd)<3000 or np.nanmax(spd)<10: continue
    Wd, yd = W[::5], yawcan[::5]                       # 2 Hz is ample for turn dynamics
    best=(0,0.0)
    for L in range(-60,61):                            # +/-30 s at 0.5 s steps
        if L<0: x,y=Wd[-L:],yd[:len(yd)+L]
        elif L>0: x,y=Wd[:len(Wd)-L],yd[L:]
        else: x,y=Wd,yd
        if len(x)<300: continue
        r=fit_r(x,y)
        if abs(r)>abs(best[1]): best=(L,r)
    single=max(abs(np.corrcoef(W[:,i],yawcan)[0,1]) for i in range(3))
    rows.append(dict(drive=sp.stem, lag_s=best[0]*0.5, r_3axis=round(best[1],3),
                     r_bestsingle=round(single,3), n=len(spd)))
D=pd.DataFrame(rows).sort_values("r_3axis",key=abs,ascending=False)
D.to_csv("/home/masterx/sih/out/sync_v2.csv",index=False)
print(D.to_string(index=False))
print(f"\n=== {len(D)} drives ===")
for t in (0.95,0.90,0.80,0.70):
    print(f"  |r| >= {t}: {(D.r_3axis.abs()>=t).sum():>3}   (single-axis screen gave {(D.r_bestsingle.abs()>=t).sum()})")
print(f"  drives rescued by 3-axis fit (single<0.7, 3axis>=0.9): {((D.r_bestsingle.abs()<0.7)&(D.r_3axis.abs()>=0.9)).sum()}")
