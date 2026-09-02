"""Speed-change prediction came out at r=0.017 - nothing learned.
Hypothesis: the phone's yaw offset differs per drive, so 'forward' lives in a
different mix of X/Y in every file. Test it."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset")
def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()
def col(df,p):
    m=[c for c in df.columns if c.startswith(p)]; return m[0] if m else None

vmap={p.name.lower():p for p in (ROOT/"V-Dataset").iterdir()}
print(f"{'drive':<12} {'best yaw':>9} {'r @best':>8} {'r rawX':>7} {'r rawY':>7} {'r |horiz|':>10}")
print("-"*60)
offsets=[]
for sp in sorted((ROOT/"S-Dataset").iterdir())[:14]:
    vp=vmap.get(sp.name.replace("S-","V-",1).lower())
    if vp is None: continue
    S=pd.read_csv(sp,encoding="latin-1",low_memory=False); V=pd.read_csv(vp,encoding="latin-1",low_memory=False)
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); S,V=S.iloc[:n],V.iloc[:n]
    ax=num(S,col(S,"ACCELEROMETER X")); ay=num(S,col(S,"ACCELEROMETER Y"))
    lon=num(V,"Indicated Longitudinal Acceleration (g)")*9.81
    spd=num(V,"Indicated Vehicle Speed (km/hr)")
    ok=np.isfinite(ax)&np.isfinite(ay)&np.isfinite(lon)&np.isfinite(spd)
    ax,ay,lon,spd=ax[ok],ay[ok],lon[ok],spd[ok]
    if len(spd)<3000 or np.nanmax(spd)<10: continue
    ax=ax-ax.mean(); ay=ay-ay.mean()          # strip static gravity leak
    # sweep yaw: which direction in the phone's flat plane is 'forward'?
    ths=np.linspace(0,2*np.pi,721)
    rs=np.array([np.corrcoef(ax*np.cos(t)+ay*np.sin(t), lon)[0,1] for t in ths])
    best=ths[np.argmax(rs)]
    horiz=np.sqrt(ax**2+ay**2)                 # yaw-invariant magnitude
    print(f"{sp.stem:<12} {np.degrees(best):>8.0f}° {rs.max():>8.3f} "
          f"{np.corrcoef(ax,lon)[0,1]:>7.3f} {np.corrcoef(ay,lon)[0,1]:>7.3f} "
          f"{np.corrcoef(horiz,np.abs(lon))[0,1]:>10.3f}")
    offsets.append(np.degrees(best))
o=np.array(offsets)
print("-"*60)
print(f"yaw offset across {len(o)} drives: min {o.min():.0f}deg  max {o.max():.0f}deg  spread {o.max()-o.min():.0f}deg")
print(f"  -> {'DIFFERENT per drive - alignment is the blocker' if o.max()-o.min()>40 else 'consistent - alignment is NOT the blocker'}")
