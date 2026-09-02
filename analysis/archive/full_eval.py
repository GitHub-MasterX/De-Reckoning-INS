"""
Everything, evaluated the same way. 60 s GNSS blackout, drift as % of distance travelled.

Strategies, cumulative where sensible:
  coast          hold the GNSS velocity, integrate nothing
  phys           integrate aligned forward acceleration
  model          ML prediction of speed change
  *_cal          + bias measured from the 60 s BEFORE the blackout, while GNSS was up
                 (this is the online self-calibration idea - deployable, not cheating)
  turn           v = |a_lat| / |yaw rate|, a DIRECT speed measurement during corners,
                 no integration at all
  fused          model_cal, corrected toward the turn measurement whenever cornering
  fused_zupt     + velocity forced to zero when the vehicle is detected stationary
  oracle         the true speed changes
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
CLEAN=Path("/home/masterx/sih/data/clean"); FS,WIN,HOP=10.0,20,5
STEP=HOP/FS                       # 0.5 s per step
NW=int(60/STEP)                   # 120 steps = 60 s
CAL=int(60/STEP)                  # calibrate on the preceding 60 s
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
COLS=["acc_fwd","acc_lat","acc_down","rate_roll","rate_pitch","rate_yaw"]

def feats(w):
    f=[]
    for c in range(w.shape[1]):
        s=w[:,c]; f+=[s.mean(),s.std(),s.min(),s.max(),np.abs(np.diff(s)).mean()]
    am=np.linalg.norm(w[:,:3],axis=1); wm=np.linalg.norm(w[:,3:6],axis=1)
    f+=[am.mean(),am.std(),wm.mean(),wm.std()]
    for c in (0,1,2):
        P=np.abs(np.fft.rfft(w[:,c]-w[:,c].mean()))**2; fr=np.fft.rfftfreq(WIN,1/FS)
        for lo,hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)): f.append(np.log(P[(fr>=lo)&(fr<hi)].sum()+1e-9))
    return f

def build(drive,sess):
    d=pd.read_parquet(CLEAN/f"{drive}.parquet")
    d=d[(d.session==sess)&d.aligned_valid].reset_index(drop=True)
    if len(d)<WIN*20 or not all(c in d.columns for c in COLS): return None
    X=d[COLS].to_numpy(); y=d.speed_best_al.to_numpy()/3.6
    af=d.acc_fwd.to_numpy(); al=d.acc_lat.to_numpy(); yr=d.rate_yaw.to_numpy()
    st=d.stationary.to_numpy()
    ok=np.isfinite(X).all(1)&np.isfinite(y)
    X,y,af,al,yr,st=X[ok],y[ok],af[ok],al[ok],yr[ok],st[ok]
    if len(y)<WIN*20: return None
    idx=np.arange(0,len(y)-WIN,HOP)
    F   =np.array([feats(X[i:i+WIN]) for i in idx])
    dv  =np.array([y[i+WIN-1]-y[i+WIN-1-HOP] for i in idx])
    phys=np.array([af[i+WIN-HOP:i+WIN].sum()/FS for i in idx])
    lat =np.array([al[i+WIN-HOP:i+WIN].mean() for i in idx])
    yaw =np.array([yr[i+WIN-HOP:i+WIN].mean() for i in idx])
    stat=np.array([st[i+WIN-HOP:i+WIN].all() for i in idx])
    v   =np.array([y[i+WIN-1] for i in idx])
    return F,dv,phys,lat,yaw,stat,v

sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
tr=[b for _,r in sel[sel.driver.isin(["A","E"])].iterrows() if (b:=build(r.drive,int(r.session)))]
Xtr=np.vstack([t[0] for t in tr]); dtr=np.concatenate([t[1] for t in tr])
mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
mdl=HistGradientBoostingRegressor(max_iter=500,learning_rate=0.06,random_state=0).fit((Xtr-mu)/sd,dtr)
print(f"trained on {len(dtr):,} windows / {len(tr)} sessions\n")

# how good is the turn-based speed measurement on its own?
tv,tt=[],[]
for F,dv,phys,lat,yaw,stat,v in tr:
    m=(np.abs(yaw)>0.12)&(v>4)
    if m.sum()>100: tv.append(np.abs(lat[m]/yaw[m])); tt.append(v[m])
tv,tt=np.concatenate(tv),np.concatenate(tt); k=np.isfinite(tv)&(tv<60)
print(f"turn-based speed v=|a_lat|/|yaw|: r={np.corrcoef(tv[k],tt[k])[0,1]:+.3f}, "
      f"MAE={np.abs(tv[k]-tt[k]).mean()*3.6:.1f} km/h over {k.sum():,} cornering samples\n")

KEYS=["coast","phys","phys_cal","model","model_cal","turn","fused","fused_zupt","oracle"]
rng=np.random.default_rng(0); agg={k:[] for k in KEYS}; per=[]
for drv in ("B","D"):
    for _,r in sel[sel.driver==drv].iterrows():
        b=build(r.drive,int(r.session))
        if not b: continue
        F,dv,phys,lat,yaw,stat,v=b
        p=mdl.predict((F-mu)/sd)
        starts=[s for s in range(CAL,len(v)-NW,10) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        if not starts: continue
        loc={k:[] for k in KEYS}
        for s in rng.choice(starts,size=min(300,len(starts)),replace=False):
            dt=float(np.sum(v[s:s+NW])*STEP)
            if dt<50: continue
            c=slice(s-CAL,s)
            bm=float(np.mean(p[c]-dv[c])); bp=float(np.mean(phys[c]-dv[c]))
            for key in KEYS:
                ve=v[s]; de=0.0
                for j in range(NW):
                    i=s+j
                    if   key=="coast":     inc=0.0
                    elif key=="phys":      inc=phys[i]
                    elif key=="phys_cal":  inc=phys[i]-bp
                    elif key=="model":     inc=p[i]
                    elif key=="model_cal": inc=p[i]-bm
                    elif key=="oracle":    inc=dv[i]
                    else:                  inc=p[i]-bm
                    ve+=inc
                    if key in ("turn","fused","fused_zupt") and abs(yaw[i])>0.12:
                        vt=abs(lat[i]/yaw[i])
                        if np.isfinite(vt) and 0<vt<60:
                            ve=(1-0.25)*ve+0.25*vt if key!="turn" else (1-0.5)*ve+0.5*vt
                    if key=="fused_zupt" and stat[i]: ve=0.0
                    de+=max(ve,0.0)*STEP
                loc[key].append(abs(de-dt)/dt*100)
        for k in KEYS: agg[k]+=loc[k]
        per.append(dict(session=f"{r.drive}/s{int(r.session)}",driver=drv,n=len(loc['coast']),
                        **{k:round(float(np.median(loc[k])),1) for k in KEYS}))

print("="*64); print("OVERALL DEVIATION  (all test blackouts, drivers B and D)"); print("="*64)
print(f"  {'strategy':<24}{'median':>9}{'p90':>9}{'vs coast':>11}")
base=np.median(agg["coast"])
for k in KEYS:
    x=np.array(agg[k]); m=np.median(x)
    print(f"  {k:<24}{m:>8.1f}%{np.percentile(x,90):>8.1f}%{base-m:>+10.1f}")
print(f"\n  n={len(agg['coast'])} blackouts    BENCHMARK: under 10%\n")
print("BREAKDOWN BY SESSION")
print(pd.DataFrame(per)[["session","driver","n"]+KEYS].to_string(index=False))
