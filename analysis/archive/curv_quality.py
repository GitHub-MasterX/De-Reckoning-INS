"""The simple pointwise estimator worked (10.0% at 60 s). Where is its error?
If sharp curves give much better speed fixes than gentle ones, filtering on curvature
should buy more than any amount of filter architecture."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import signal
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
sel=A[(A.sync_r.abs()>=0.70)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
def smooth(x,fc=0.5):
    return signal.sosfiltfilt(signal.butter(2,fc,btype="low",fs=FS,output="sos"),x)
K,V,W,OM=[],[],[],[]
for _,r in sel.iterrows():
    base=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=base[(base.session==r.session)&base.aligned_valid].reset_index(drop=True)
    if len(d)<8000: continue
    vi=d.veh_idx.to_numpy()
    yr=d.rate_yaw.to_numpy(); v=d.speed_best_al.to_numpy()/3.6
    lat=base.lat.to_numpy()[vi]; lon=base.lon.to_numpy()[vi]
    ok=np.isfinite(yr)&np.isfinite(v)&np.isfinite(lat)&np.isfinite(lon)
    yr,v,lat,lon=yr[ok],v[ok],lat[ok],lon[ok]
    if len(v)<8000: continue
    x=(lon-lon.mean())*111320*np.cos(np.radians(lat.mean())); y=(lat-lat.mean())*110540
    dx,dy=np.gradient(smooth(x,0.2)),np.gradient(smooth(y,0.2))
    ds=np.hypot(dx,dy); th=np.unwrap(np.arctan2(dy,dx))
    kap=np.abs(np.gradient(smooth(th,0.2))/np.maximum(ds,1e-3))
    om=np.abs(smooth(yr))
    m=(kap>0.001)&(om>0.02)&(v>3)
    K.append(kap[m]); V.append(v[m]); OM.append(om[m])
K=np.concatenate(K); V=np.concatenate(V); OM=np.concatenate(OM)
est=OM/np.maximum(K,1e-6); good=np.isfinite(est)&(est<70)
K,V,est,OM=K[good],V[good],est[good],OM[good]
print(f"{len(K):,} candidate samples\n")
print("SPEED-FIX QUALITY vs CURVATURE   (kappa = 1/radius)")
print(f"  {'radius':>14}{'kappa':>11}{'samples':>10}{'% of drive':>12}{'MAE km/h':>11}{'r':>8}")
edges=[0.001,0.002,0.004,0.008,0.015,0.03,0.06,1.0]
tot=len(K)
for lo,hi in zip(edges[:-1],edges[1:]):
    m=(K>=lo)&(K<hi)
    if m.sum()<200: continue
    e=est[m]; t=V[m]
    print(f"  {1/hi:>6.0f}-{1/lo:>6.0f} m{lo:>11.3f}{m.sum():>10,}{100*m.sum()/tot:>11.1f}%"
          f"{np.abs(e-t).mean()*3.6:>10.1f}{np.corrcoef(e,t)[0,1]:>8.3f}")
print("\nalso filter on yaw rate (a fix needs the car to actually be turning):")
for omin in (0.02,0.05,0.10,0.15,0.20):
    m=(OM>omin)&(K>0.004)
    if m.sum()<200: continue
    print(f"  |omega| > {omin:.2f} rad/s & radius < 250 m : {m.sum():>7,} samples "
          f"({100*m.sum()/tot:>4.1f}%)  MAE {np.abs(est[m]-V[m]).mean()*3.6:>5.1f} km/h  r={np.corrcoef(est[m],V[m])[0,1]:.3f}")
