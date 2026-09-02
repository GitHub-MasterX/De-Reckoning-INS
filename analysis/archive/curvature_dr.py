"""
Dead reckoning with speed from MAP CURVATURE.

    omega = v * kappa   ->   v = omega / kappa

omega: gyroscope, our best channel (r=0.96).
kappa: road curvature, known from the map a priori - not a sensor, so no noise, no bias,
       and completely unaffected by GNSS being unavailable.

The accelerometer is not used at all. Nothing is integrated, so nothing accumulates:
every curve is an independent absolute speed fix.
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

DURS=[10,20,30,60,90]; GAINS=[0.0,0.05,0.1,0.2,0.4]
rng=np.random.default_rng(0)
agg={(d,g):[] for d in DURS for g in GAINS}; per=[]
for _,r in sel.iterrows():
    if r.driver not in ("B","D"): continue
    base=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=base[(base.session==r.session)&base.aligned_valid].reset_index(drop=True)
    if len(d)<8000: continue
    vi=d.veh_idx.to_numpy()
    yr=d.rate_yaw.to_numpy(); v=d.speed_best_al.to_numpy()/3.6
    lat=base.lat.to_numpy()[vi]; lon=base.lon.to_numpy()[vi]
    ok=np.isfinite(yr)&np.isfinite(v)&np.isfinite(lat)&np.isfinite(lon)
    yr,v,lat,lon=yr[ok],v[ok],lat[ok],lon[ok]
    if len(v)<8000: continue
    # curvature of the road, as a map would supply it
    x=(lon-lon.mean())*111320*np.cos(np.radians(lat.mean())); y=(lat-lat.mean())*110540
    dx,dy=np.gradient(smooth(x,0.2)),np.gradient(smooth(y,0.2))
    ds=np.hypot(dx,dy); th=np.unwrap(np.arctan2(dy,dx))
    kap=np.gradient(smooth(th,0.2))/np.maximum(ds,1e-3)
    om=np.abs(smooth(yr)); ka=np.abs(kap)
    usable=(ka>0.004)&(om>0.05)                    # radius < 250 m and actually turning
    vmeas=np.where(usable,om/np.maximum(ka,1e-6),np.nan)
    vmeas=np.where(np.isfinite(vmeas)&(vmeas<60),vmeas,np.nan)
    loc={}
    for dur in DURS:
        NW=int(dur*FS)
        starts=[s for s in range(0,len(v)-NW,20) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        if not starts: continue
        for s in rng.choice(starts,size=min(300,len(starts)),replace=False):
            dt=float(np.sum(v[s:s+NW])*DT)
            if dt<10: continue
            for g in GAINS:
                ve=v[s]; de=0.0
                for j in range(NW):
                    m=vmeas[s+j]
                    if g>0 and np.isfinite(m): ve=(1-g)*ve+g*m
                    de+=ve*DT
                agg[(dur,g)].append(abs(de-dt)/dt*100)
                loc.setdefault((dur,g),[]).append(abs(de-dt)/dt*100)
    if loc:
        per.append(dict(session=f"{r.drive}/s{int(r.session)}",
            **{f"{dur}s_g{g}":round(float(np.median(loc[(dur,g)])),1) for dur in DURS for g in (0.0,0.2) if (dur,g) in loc},
            pct_usable=round(100*float(np.mean(np.isfinite(vmeas))),1)))
print("DRIFT vs BLACKOUT LENGTH and CORRECTION GAIN   (gain 0 = coast, no correction)\n")
print(f"  {'duration':>9}" + "".join(f"{'g='+str(g):>10}" for g in GAINS) + f"{'best':>9}{'pass':>7}")
for dur in DURS:
    vals=[np.median(agg[(dur,g)]) if agg[(dur,g)] else np.nan for g in GAINS]
    b=np.nanmin(vals)
    print(f"  {dur:>7} s" + "".join(f"{v:>9.1f}%" for v in vals) + f"{b:>8.1f}%{'  YES' if b<10 else '   no':>7}")
print(f"\n  n at 60 s: {len(agg[(60,0.2)]):,}   BENCHMARK: under 10%\n")
print(pd.DataFrame(per).to_string(index=False))
