"""The model has real signal (r 0.43-0.61) but too much bias. Coast has zero signal and
zero bias. The optimum is probably between them: v = v0 + alpha * sum(predictions).
alpha=0 is coast, alpha=1 is the model. Sweep it."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
CLEAN=Path("/home/masterx/sih/data/clean"); FS,WIN,HOP=10.0,20,5
STEP=HOP/FS; NW=int(60/STEP)
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
    d=pd.read_parquet(CLEAN/f"{drive}.parquet"); d=d[(d.session==sess)&d.aligned_valid].reset_index(drop=True)
    if len(d)<WIN*20 or not all(c in d.columns for c in COLS): return None
    X=d[COLS].to_numpy(); y=d.speed_best_al.to_numpy()/3.6; af=d.acc_fwd.to_numpy()
    ok=np.isfinite(X).all(1)&np.isfinite(y); X,y,af=X[ok],y[ok],af[ok]
    if len(y)<WIN*20: return None
    idx=np.arange(0,len(y)-WIN,HOP)
    return (np.array([feats(X[i:i+WIN]) for i in idx]),
            np.array([y[i+WIN-1]-y[i+WIN-1-HOP] for i in idx]),
            np.array([af[i+WIN-HOP:i+WIN].sum()/FS for i in idx]),
            np.array([y[i+WIN-1] for i in idx]))
sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
tr=[b for _,r in sel[sel.driver.isin(["A","E"])].iterrows() if (b:=build(r.drive,int(r.session)))]
Xtr=np.vstack([t[0] for t in tr]); dtr=np.concatenate([t[1] for t in tr])
mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
mdl=HistGradientBoostingRegressor(max_iter=500,learning_rate=0.06,random_state=0).fit((Xtr-mu)/sd,dtr)

# how much does speed actually change over 60 s? this bounds what coast can lose
net=[]
for F,dv,phys,v in tr:
    for s in range(0,len(v)-NW,50):
        if v[s]>4.2 and (v[s:s+NW]>1.4).all():
            net.append(abs(np.mean(v[s:s+NW])-v[s])/max(np.mean(v[s:s+NW]),1e-9)*100)
print(f"true |mean speed - start speed| over 60 s: median {np.median(net):.1f}% of mean speed")
print(f"  -> that IS coast's error. n={len(net):,}\n")

rng=np.random.default_rng(0)
ALPHAS=[0,0.1,0.2,0.3,0.4,0.5,0.7,1.0]
res={("model",a):[] for a in ALPHAS}; res.update({("phys",a):[] for a in ALPHAS})
for drv in ("B","D"):
    for _,r in sel[sel.driver==drv].iterrows():
        b=build(r.drive,int(r.session))
        if not b: continue
        F,dv,phys,v=b; p=mdl.predict((F-mu)/sd)
        starts=[s for s in range(0,len(v)-NW,10) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
        for s in (rng.choice(starts,size=min(300,len(starts)),replace=False) if starts else []):
            dt=float(np.sum(v[s:s+NW])*STEP)
            if dt<50: continue
            for src,pred in (("model",p),("phys",phys)):
                for a in ALPHAS:
                    ve=v[s]; de=0.0
                    for j in range(NW):
                        ve+=a*pred[s+j]; de+=max(ve,0.0)*STEP
                    res[(src,a)].append(abs(de-dt)/dt*100)
print("SHRINKAGE SWEEP   v = v0 + alpha * sum(predictions)")
print(f"  {'alpha':>7}{'model':>10}{'physics':>10}")
for a in ALPHAS:
    m=np.median(res[("model",a)]); q=np.median(res[("phys",a)])
    tag=" <- coast" if a==0 else ""
    print(f"  {a:>7.1f}{m:>9.1f}%{q:>9.1f}%{tag}")
bm=min(ALPHAS,key=lambda a: np.median(res[("model",a)]))
bp=min(ALPHAS,key=lambda a: np.median(res[("phys",a)]))
print(f"\n  best model alpha={bm} -> {np.median(res[('model',bm)]):.1f}%")
print(f"  best phys  alpha={bp} -> {np.median(res[('phys',bp)]):.1f}%")
print(f"  coast                 -> {np.median(res[('model',0)]):.1f}%     BENCHMARK: 10%")
