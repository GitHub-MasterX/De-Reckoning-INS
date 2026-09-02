"""Is the S/V pairing actually time-aligned? Gyro-vs-CAN-yaw is the cleanest probe:
it needs no gravity removal and no yaw alignment if the phone is flat."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset")
def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()
def col(df,p):
    m=[c for c in df.columns if c.startswith(p)]; return m[0] if m else None

vmap={p.name.lower():p for p in (ROOT/"V-Dataset").iterdir()}
print(f"{'drive':<12} {'gyro r':>7} {'lag':>6} {'r@lag':>7} | {'accel r':>8} {'lag':>6} {'r@lag':>7}")
print("-"*66)
for sp in sorted((ROOT/"S-Dataset").iterdir())[:14]:
    vp=vmap.get(sp.name.replace("S-","V-",1).lower())
    if vp is None: continue
    S=pd.read_csv(sp,encoding="latin-1",low_memory=False); V=pd.read_csv(vp,encoding="latin-1",low_memory=False)
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); S,V=S.iloc[:n],V.iloc[:n]
    gy=[c for c in S.columns if c.startswith("GYROSCOPE")]
    W=np.c_[num(S,gy[0]),num(S,gy[1]),num(S,gy[2])]
    ax=num(S,col(S,"ACCELEROMETER X")); ay=num(S,col(S,"ACCELEROMETER Y"))
    yawcan=num(V,"Yaw Rate (deg/sec)")*np.pi/180
    lon=num(V,"Indicated Longitudinal Acceleration (g)")*9.81
    spd=num(V,"Indicated Vehicle Speed (km/hr)")
    ok=np.isfinite(W).all(1)&np.isfinite(yawcan)&np.isfinite(lon)&np.isfinite(spd)&np.isfinite(ax)&np.isfinite(ay)
    W,yawcan,lon,spd,ax,ay=W[ok],yawcan[ok],lon[ok],spd[ok],ax[ok],ay[ok]
    if len(spd)<3000 or np.nanmax(spd)<10: continue

    def lagscan(a,b,maxlag=50):
        a=(a-a.mean())/(a.std()+1e-12); b=(b-b.mean())/(b.std()+1e-12)
        rs=[]
        for L in range(-maxlag,maxlag+1):
            if L<0: x,y=a[-L:],b[:len(b)+L]
            elif L>0: x,y=a[:len(a)-L],b[L:]
            else: x,y=a,b
            rs.append(np.corrcoef(x,y)[0,1])
        rs=np.array(rs); i=np.argmax(np.abs(rs))
        return rs[maxlag], (i-maxlag)/10.0, rs[i]     # r at 0 lag, best lag in s, r there

    # gyro: pick the axis that best matches CAN yaw
    best_ax=np.argmax([abs(np.corrcoef(W[:,i],yawcan)[0,1]) for i in range(3)])
    g0,glag,gbest = lagscan(W[:,best_ax], yawcan)
    # accel: yaw-invariant horizontal magnitude vs |longitudinal|
    horiz=np.sqrt((ax-ax.mean())**2+(ay-ay.mean())**2)
    a0,alag,abest = lagscan(horiz, np.abs(lon))
    print(f"{sp.stem:<12} {g0:>7.3f} {glag:>5.1f}s {gbest:>7.3f} | {a0:>8.3f} {alag:>5.1f}s {abest:>7.3f}")
