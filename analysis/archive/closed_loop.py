"""
HONEST version. The map stores curvature against DISTANCE ALONG THE ROAD - kappa(s) -
which is what OSM actually gives you: a static property of the road, no GNSS needed.

During a blackout the engine only knows its OWN estimate of how far it has travelled:

    s_hat  += v_hat * dt          our estimate of distance along the route
    kappa   = map_lookup(s_hat)   read the map at where we THINK we are
    v_meas  = omega / kappa       speed fix from the gyro
    v_hat  += g * (v_meas - v_hat)

Circular by construction: a bad position gives a bad curvature gives a worse speed.
Either it self-stabilises or it runs away. That is the experiment.

Also reported: the CHEATING version that looks up curvature at the TRUE position, to
show exactly how much the earlier numbers were flattered.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import signal
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0; DT=1/FS
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
sel=A[(A.sync_r.abs()>=0.70)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
def smooth(x,fc=0.5):
    return signal.sosfiltfilt(signal.butter(2,fc,btype="low",fs=FS,output="sos"),x)

KMIN,OMMIN,GAIN=0.004,0.05,0.06        # the configuration the sweep chose
DURS=[10,20,30,60,90]

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
    arc=np.concatenate(([0.0],np.cumsum(v[:-1])*DT))     # true distance along the route
    return v,np.abs(smooth(yr)),kap,arc

def fix_from(kappa,om):
    if kappa<=KMIN or om<=OMMIN: return None
    vm=om/kappa
    return vm if 0<vm<70 else None

rng=np.random.default_rng(0); agg={d:{"coast":[],"closed":[],"cheat":[]} for d in DURS}
for _,r in sel.iterrows():
    if r.driver not in ("B","D"): continue
    p=prep(r.drive,int(r.session))
    if p is None: continue
    v,om,kap,arc=p
    for dur in DURS:
        NW=int(dur*FS)
        starts=[s for s in range(0,len(v)-NW,20) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        if not starts: continue
        for s in rng.choice(starts,size=min(250,len(starts)),replace=False):
            dt=float(np.sum(v[s:s+NW])*DT)
            if dt<10: continue
            agg[dur]["coast"].append(abs(v[s]*dur-dt)/dt*100)
            # ---- CHEATING: curvature at the TRUE position ----
            ve=v[s]; de=0.0
            for j in range(NW):
                f=fix_from(kap[s+j],om[s+j])
                if f is not None: ve=(1-GAIN)*ve+GAIN*f
                de+=max(ve,0.0)*DT
            agg[dur]["cheat"].append(abs(de-dt)/dt*100)
            # ---- HONEST: curvature at our OWN estimated position ----
            ve=v[s]; de=0.0; s0=arc[s]
            seg=arc[s:s+NW]-s0
            for j in range(NW):
                idx=int(np.searchsorted(seg,de))            # where we THINK we are
                idx=min(max(idx,0),NW-1)
                f=fix_from(kap[s+idx],om[s+j])              # map at s_hat, gyro at now
                if f is not None: ve=(1-GAIN)*ve+GAIN*f
                de+=max(ve,0.0)*DT
            agg[dur]["closed"].append(abs(de-dt)/dt*100)
print("HONEST CLOSED LOOP vs the earlier (flawed) OPEN LOOP\n")
print(f"  {'duration':>9}{'metres':>9}{'coast':>9}{'honest':>10}{'cheating':>11}{'pass':>7}")
for d in DURS:
    if not agg[d]["closed"]: continue
    c=np.median(agg[d]["coast"]); h=np.median(agg[d]["closed"]); x=np.median(agg[d]["cheat"])
    print(f"  {d:>7} s{d*16.7:>8.0f}{c:>8.1f}%{h:>9.1f}%{x:>10.1f}%{'  YES' if h<10 else '   no':>7}")
print(f"\n  n at 60 s: {len(agg[60]['closed']):,}")
print(f"  at 60 s honest = {np.median(agg[60]['closed'])*10.02:.1f} m over 1002 m   [budget 100 m]")
