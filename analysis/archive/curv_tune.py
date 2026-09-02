"""The simple fixed-gain blend beat every Kalman variant, which means the measurement
error is SYSTEMATIC (the vehicle cuts corners; its path curvature is not the centreline's).
A small fixed gain is shrinkage against that bias. So: keep it simple, tune the filters."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import signal
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0; DT=1/FS
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
sel=A[(A.sync_r.abs()>=0.70)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
def smooth(x,fc=0.5):
    return signal.sosfiltfilt(signal.butter(2,fc,btype="low",fs=FS,output="sos"),x)
def prep(drive,sess):
    base=pd.read_parquet(CLEAN/f"{drive}.parquet")
    d=base[(base.session==sess)&base.aligned_valid].reset_index(drop=True)
    if len(d)<8000: return None
    vi=d.veh_idx.to_numpy()
    yr=d.rate_yaw.to_numpy(); v=d.speed_best_al.to_numpy()/3.6
    lat=base.lat.to_numpy()[vi]; lon=base.lon.to_numpy()[vi]
    ok=np.isfinite(yr)&np.isfinite(v)&np.isfinite(lat)&np.isfinite(lon)
    yr,v,lat,lon=yr[ok],v[ok],lat[ok],lon[ok]
    if len(v)<8000: return None
    x=(lon-lon.mean())*111320*np.cos(np.radians(lat.mean())); y=(lat-lat.mean())*110540
    dx,dy=np.gradient(smooth(x,0.2)),np.gradient(smooth(y,0.2))
    ds=np.hypot(dx,dy); th=np.unwrap(np.arctan2(dy,dx))
    kap=np.abs(np.gradient(smooth(th,0.2))/np.maximum(ds,1e-3))
    return v,np.abs(smooth(yr)),kap
data=[]
for _,r in sel.iterrows():
    if r.driver not in ("B","D"): continue
    p=prep(r.drive,int(r.session))
    if p: data.append((f"{r.drive}/s{int(r.session)}",)+p)
DURS=[10,20,30,60,90,120]; rng=np.random.default_rng(0)
# pre-draw the same blackouts for every configuration
BO={}
for nm,v,om,kap in data:
    for dur in DURS:
        NW=int(dur*FS)
        st=[s for s in range(0,len(v)-NW,20) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        if st: BO[(nm,dur)]=rng.choice(st,size=min(250,len(st)),replace=False)
best=None
print("sweeping filters and gain (60 s / 90 s medians)\n")
for kmin in (0.004,0.006,0.010):
    for ommin in (0.05,0.10,0.15,0.20):
        for g in (0.02,0.04,0.06,0.10):
            res={d:[] for d in DURS}
            for nm,v,om,kap in data:
                use=(kap>kmin)&(om>ommin)
                vm=np.where(use,om/np.maximum(kap,1e-6),np.nan)
                vm=np.where(np.isfinite(vm)&(vm<70),vm,np.nan)
                for dur in DURS:
                    if (nm,dur) not in BO: continue
                    NW=int(dur*FS)
                    for s in BO[(nm,dur)]:
                        dt=float(np.sum(v[s:s+NW])*DT)
                        if dt<10: continue
                        ve=v[s]; de=0.0
                        for j in range(NW):
                            m=vm[s+j]
                            if np.isfinite(m): ve=(1-g)*ve+g*m
                            de+=max(ve,0.0)*DT
                        res[dur].append(abs(de-dt)/dt*100)
            m60=np.median(res[60]); m90=np.median(res[90])
            score=max(m60,m90)
            if best is None or score<best[0]:
                best=(score,kmin,ommin,g,{d:np.array(res[d]) for d in DURS})
                print(f"  radius<{1/kmin:>4.0f}m  |w|>{ommin:.2f}  gain={g:.2f}  ->  60s {m60:5.1f}%  90s {m90:5.1f}%  *")
s,kmin,ommin,g,res=best
print(f"\nBEST:  radius < {1/kmin:.0f} m,  |omega| > {ommin} rad/s,  gain = {g}\n")
print(f"  {'duration':>9}{'distance':>11}{'coast':>9}{'curvature':>12}{'metres':>10}{'pass':>7}")
for d in DURS:
    if not len(res[d]): continue
    k=np.median(res[d])
    dist=d*16.7
    print(f"  {d:>7} s{dist:>9.0f} m{'':>9}{k:>11.1f}%{dist*k/100:>9.1f} m{'  YES' if k<10 else '   no':>7}")
print(f"\n  p90 at 60 s: {np.percentile(res[60],90):.1f}%   at 90 s: {np.percentile(res[90],90):.1f}%")
