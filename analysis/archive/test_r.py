"""Retrain (nothing was saved) and report BOTH r and drift on the test drivers,
alongside the physics baseline, so the two metrics can be compared directly."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
CLEAN=Path("/home/masterx/sih/data/clean"); FS,WIN,HOP=10.0,20,5
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")

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
    cols=["acc_fwd","acc_lat","acc_down","rate_roll","rate_pitch","rate_yaw"]
    if len(d)<WIN*10 or not all(c in d.columns for c in cols): return None
    X=d[cols].to_numpy(); y=d.speed_best_al.to_numpy()/3.6; af=d.acc_fwd.to_numpy()
    ok=np.isfinite(X).all(1)&np.isfinite(y)
    X,y,af=X[ok],y[ok],af[ok]
    if len(y)<WIN*10: return None
    idx=np.arange(0,len(y)-WIN,HOP)
    F=np.array([feats(X[i:i+WIN]) for i in idx])
    dv=np.array([y[i+WIN-1]-y[i+WIN-1-HOP] for i in idx])          # true Δv per 0.5 s, m/s
    phys=np.array([af[i+WIN-HOP:i+WIN].sum()/FS for i in idx])     # physics Δv over same span
    v=np.array([y[i+WIN-1] for i in idx])
    return F,dv,phys,v

sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]
sel=sel[sel.drive!="Vtb1"]
tr=[b for _,r in sel[sel.driver.isin(["A","E"])].iterrows() if (b:=build(r.drive,int(r.session)))]
Xtr=np.vstack([t[0] for t in tr]); dtr=np.concatenate([t[1] for t in tr])
mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
mdl=HistGradientBoostingRegressor(max_iter=500,learning_rate=0.06,random_state=0).fit((Xtr-mu)/sd,dtr)
print(f"retrained on {len(dtr):,} windows / {len(tr)} sessions (drivers A+E)\n")

rng=np.random.default_rng(0); NW=int(60*FS/HOP)
for drv,name in (("B","driver B (M)"),("D","driver D (Y1)")):
    print(f"=== {name} ===")
    for _,r in sel[sel.driver==drv].iterrows():
        b=build(r.drive,int(r.session))
        if not b: continue
        F,dv,phys,v=b
        p=mdl.predict((F-mu)/sd)
        rm=np.corrcoef(p,dv)[0,1]; rp=np.corrcoef(phys,dv)[0,1]
        bias_m=np.mean(p-dv); bias_p=np.mean(phys-dv)
        starts=[s for s in range(0,len(v)-NW,10) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        dr={k:[] for k in ("coast","model","phys")}
        for s in (rng.choice(starts,size=min(300,len(starts)),replace=False) if starts else []):
            dt=float(np.sum(v[s:s+NW])*(HOP/FS))
            if dt<50: continue
            for k,pred in (("coast",None),("model",p),("phys",phys)):
                ve=v[s]; de=0.0
                for j in range(NW):
                    de+=ve*(HOP/FS)
                    if pred is not None: ve+=pred[s+j]
                dr[k].append(abs(de-dt)/dt*100)
        print(f"  {r.drive}/s{int(r.session)}")
        print(f"     MODEL    r={rm:+.3f}  mean err={bias_m:+.5f} m/s per step  drift={np.median(dr['model']):.1f}%")
        print(f"     PHYSICS  r={rp:+.3f}  mean err={bias_p:+.5f} m/s per step  drift={np.median(dr['phys']):.1f}%")
        print(f"     COAST    r=  --                                     drift={np.median(dr['coast']):.1f}%")
    print()
