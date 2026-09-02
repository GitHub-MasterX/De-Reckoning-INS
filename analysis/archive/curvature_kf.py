"""
Curvature speed, done properly.

  1. REGRESSION not ratio:  fit omega = v*kappa over a window; the slope is the speed.
     Averages over the whole curve instead of dividing point by point.
  2. HONEST UNCERTAINTY:    the regression's own standard error says how much to trust it.
     A sharp curve gives a tight estimate, a gentle one a loose estimate.
  3. KALMAN UPDATE:         velocity carries an uncertainty that grows while coasting and
     shrinks at each curve, so the gain is computed rather than guessed.
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

WIN=int(4*FS)            # 4 s regression window
Q=0.35**2                # velocity process noise per second (m/s)^2 - how fast speed can drift
DURS=[10,20,30,60,90,120]

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
    kap=np.gradient(smooth(th,0.2))/np.maximum(ds,1e-3)
    om=smooth(yr)
    # regression v and its standard error, per window
    n=len(v); vm=np.full(n,np.nan); vs=np.full(n,np.nan)
    for s in range(0,n-WIN,5):
        k=kap[s:s+WIN]; o=om[s:s+WIN]
        sk=np.std(k)
        if sk<0.002: continue                      # too straight to measure anything
        kc=k-k.mean(); oc=o-o.mean()
        den=float(kc@kc)
        if den<1e-9: continue
        slope=float(kc@oc/den)
        if not (0<slope<60): continue
        resid=oc-slope*kc
        se=float(np.sqrt((resid@resid)/max(len(k)-2,1)/den))   # standard error of the slope
        j=s+WIN-1
        vm[j]=slope; vs[j]=max(se,0.3)
    return v,vm,vs

rng=np.random.default_rng(0); agg={d:{"coast":[],"kf":[]} for d in DURS}; per=[]
for _,r in sel.iterrows():
    if r.driver not in ("B","D"): continue
    p=prep(r.drive,int(r.session))
    if p is None: continue
    v,vm,vs=p; loc={}
    for dur in DURS:
        NW=int(dur*FS)
        starts=[s for s in range(0,len(v)-NW,20) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        if not starts: continue
        for s in rng.choice(starts,size=min(300,len(starts)),replace=False):
            dt=float(np.sum(v[s:s+NW])*DT)
            if dt<10: continue
            agg[dur]["coast"].append(abs(v[s]*dur-dt)/dt*100)
            ve=v[s]; P=1.0; de=0.0
            for j in range(NW):
                i=s+j
                P+=Q*DT                                   # uncertainty grows while coasting
                if np.isfinite(vm[i]):
                    R=vs[i]**2
                    K=P/(P+R)                             # gain computed, not guessed
                    ve+=K*(vm[i]-ve); P*=(1-K)
                de+=max(ve,0.0)*DT
            agg[dur]["kf"].append(abs(de-dt)/dt*100)
            loc.setdefault(dur,[]).append(abs(de-dt)/dt*100)
    if loc: per.append(dict(session=f"{r.drive}/s{int(r.session)}",
        **{f"{d}s":round(float(np.median(loc[d])),1) for d in DURS if d in loc}))
print("KALMAN + REGRESSION CURVATURE SPEED\n")
print(f"  {'duration':>9}{'coast':>10}{'this':>10}{'gain':>9}{'pass':>7}")
for d in DURS:
    if not agg[d]["kf"]: continue
    c=np.median(agg[d]["coast"]); k=np.median(agg[d]["kf"])
    print(f"  {d:>7} s{c:>9.1f}%{k:>9.1f}%{c-k:>+8.1f}{'  YES' if k<10 else '   no':>7}")
print(f"\n  n at 60 s: {len(agg[60]['kf']):,}    BENCHMARK: under 10%\n")
print(pd.DataFrame(per).to_string(index=False))
