"""Speed-change model + blackout evaluation, on lag-aligned data.

THE BUG THAT WAS FIXED: previously each prediction covered 2.0 s while the simulation
stepped 0.5 s, so overlapping windows were summed and velocity accumulated 4x too fast.
Now the target is the speed change over exactly one HOP, so consecutive predictions
tile time without overlap and summing them is correct.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.dummy import DummyRegressor

CLEAN=Path("/home/masterx/sih/data/clean")
FS, WIN, HOP = 10.0, 20, 5           # 2.0 s of context, target/step = 0.5 s
MIN_SYNC = 0.40                      # include "noisy" sessions in training
A=pd.read_csv("/home/masterx/sih/data/test_outputs/alignment.csv")

def feats(w):
    f=[]
    for c in range(6):
        s=w[:,c]; f+=[s.mean(),s.std(),s.min(),s.max(),np.abs(np.diff(s)).mean()]
    am=np.linalg.norm(w[:,:3],axis=1); wm=np.linalg.norm(w[:,3:],axis=1)
    f+=[am.mean(),am.std(),wm.mean(),wm.std()]
    for c in (0,1,2):
        P=np.abs(np.fft.rfft(w[:,c]-w[:,c].mean()))**2; fr=np.fft.rfftfreq(WIN,1/FS)
        for lo,hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)): f.append(np.log(P[(fr>=lo)&(fr<hi)].sum()+1e-9))
    return f

def build(drive, sess):
    d=pd.read_parquet(CLEAN/f"{drive}.parquet")
    d=d[(d.session==sess)&d.aligned_valid].reset_index(drop=True)
    if len(d)<WIN*10: return None
    X=d[["ax","ay","az","gx_c","gy_c","gz_c"]].to_numpy()
    y=d.speed_best_al.to_numpy()
    ok=np.isfinite(X).all(1)&np.isfinite(y)
    X,y=X[ok],y[ok]
    if len(y)<WIN*10: return None
    idx=np.arange(0,len(y)-WIN,HOP)
    F =np.array([feats(X[i:i+WIN]) for i in idx])
    dv=np.array([y[i+WIN-1]-y[i+WIN-1-HOP] for i in idx])   # <-- change over ONE HOP
    v =np.array([y[i+WIN-1] for i in idx])
    return F,dv,v

sel=A[(A.sync_r.abs()>=MIN_SYNC)&A.sync_r.notna()].copy()
sel=sel[~((sel.drive=="Vtb1"))]                              # stress drive, never trained on
train=sel[sel.driver.isin(["A","E"])]; testB=sel[sel.driver=="B"]; testD=sel[sel.driver=="D"]
print(f"train  {len(train)} sessions ({train.minutes.sum()/60:.1f} h) drivers A+E")
print(f"testB  {len(testB)} sessions ({testB.minutes.sum()/60:.1f} h) driver B = {list(testB.drive.unique())}")
print(f"testD  {len(testD)} sessions ({testD.minutes.sum()/60:.1f} h) driver D = {list(testD.drive.unique())}\n")

def gather(df):
    out=[]
    for _,r in df.iterrows():
        b=build(r.drive,int(r.session))
        if b: out.append((f"{r.drive}/s{int(r.session)}",)+b)
    return out
TR,TB,TD = gather(train), gather(testB), gather(testD)
Xtr=np.vstack([t[1] for t in TR]); dtr=np.concatenate([t[2] for t in TR])
print(f"{len(dtr):,} training windows from {len(TR)} sessions\n")
mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
dum=DummyRegressor().fit((Xtr-mu)/sd,dtr)
mdl=HistGradientBoostingRegressor(max_iter=500,learning_rate=0.06,random_state=0).fit((Xtr-mu)/sd,dtr)

rng=np.random.default_rng(0)
def blackout(sessions,name):
    """Four strategies, same blackouts, so the model's real contribution is visible."""
    print(f"=== {name} ===")
    acc={k:[] for k in ("coast","dummy","model","oracle")}
    NW=int(60*FS/HOP)
    for nm,F,dv,v in sessions:
        pm=mdl.predict((F-mu)/sd); pdm=dum.predict((F-mu)/sd)
        starts=[s for s in range(0,len(v)-NW,10) if v[s]>15 and (v[s:s+NW]>5).all()]
        if not starts: continue
        for s in rng.choice(starts,size=min(400,len(starts)),replace=False):
            dt=float(np.sum(v[s:s+NW]/3.6*(HOP/FS)))
            if dt<=50: continue
            for key,pred in (("coast",None),("dummy",pdm),("model",pm),("oracle",dv)):
                ve=v[s]; de=0.0
                for k in range(NW):
                    if pred is not None: ve+=pred[s+k]
                    de+=ve/3.6*(HOP/FS)
                acc[key].append(abs(de-dt)/dt*100)
    if not acc["model"]: print("  no usable windows\n"); return
    print(f"  {'strategy':<34}{'median':>9}{'p90':>9}")
    labels={"coast":"1. Coast - hold GNSS velocity (NO MODEL)",
            "dummy":"2. Dummy - add the training mean",
            "model":"3. Trained model",
            "oracle":"4. Oracle - the TRUE speed changes"}
    for k in ("coast","dummy","model","oracle"):
        a=np.array(acc[k]); print(f"  {labels[k]:<34}{np.median(a):>8.1f}%{np.percentile(a,90):>8.1f}%")
    c,m=np.median(acc["coast"]),np.median(acc["model"])
    print(f"  n={len(acc['model'])} blackouts   model vs coast: {c-m:+.1f} points "
          f"({100*(c-m)/c:+.0f}%)   [benchmark: under 10%]\n")
blackout(TB,"TEST - driver B (M), headline")
blackout(TD,"TEST - driver D (Y1), second holdout")
