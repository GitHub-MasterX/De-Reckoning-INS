"""
Does the classifier improve navigation?

The earlier ZUPT test was invalid: blackouts were sampled requiring the vehicle to be
moving throughout, so there were no stops to anchor to and ZUPT could not possibly help.
Real urban blackouts contain traffic lights. Sample them realistically.

  coast        hold the GNSS velocity
  zupt_pred    + force velocity to zero when the CLASSIFIER says stationary
  zupt_true    + using the true stationary flag (upper bound on what ZUPT can give)
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0; DT=1/FS; W=20; HOP=5
A=pd.read_csv("/home/masterx/sih/data/test_outputs/alignment.csv")
sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
def feats(a,g):
    am=np.linalg.norm(a,axis=1); gm=np.linalg.norm(g,axis=1)
    f=[am.mean(),am.std(),am.min(),am.max(),np.abs(np.diff(am)).mean(),gm.mean(),gm.std(),gm.max()]
    for c in range(3): f+=[a[:,c].std(),np.abs(np.diff(a[:,c])).mean(),g[:,c].std()]
    for c in range(3):
        P=np.abs(np.fft.rfft(a[:,c]-a[:,c].mean()))**2; fr=np.fft.rfftfreq(W,1/FS)
        for lo,hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)): f.append(np.log(P[(fr>=lo)&(fr<hi)].sum()+1e-9))
    return f
cache={}
for _,r in sel.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=d[(d.session==r.session)&d.aligned_valid].reset_index(drop=True)
    if len(d)<3000: continue
    a=d[["ax","ay","az"]].to_numpy(); g=d[["gx_c","gy_c","gz_c"]].to_numpy()
    v=d.speed_best_al.to_numpy()/3.6
    ok=np.isfinite(a).all(1)&np.isfinite(g).all(1)&np.isfinite(v)
    a,g,v=a[ok],g[ok],v[ok]
    if len(v)<3000: continue
    idx=np.arange(0,len(v)-W,HOP)
    F=np.array([feats(a[i:i+W],g[i:i+W]) for i in idx])
    lab=np.array([1 if v[i:i+W].min()>1.4 else (0 if v[i:i+W].max()<0.28 else -1) for i in idx])
    cache[(r.drive,int(r.session))]=(r.driver,F,lab,np.array([v[i+W-1] for i in idx]))
print(f"{len(cache)} sessions\n")
DURS=[30,60,90]; rng=np.random.default_rng(0); out=[]
for held in ["A","B","D","E"]:
    tr=[x for x in cache.values() if x[0]!=held]; te=[x for x in cache.values() if x[0]==held]
    if not te: continue
    Xt=np.vstack([t[1][t[2]>=0] for t in tr]); Yt=np.concatenate([t[2][t[2]>=0] for t in tr])
    clf=HistGradientBoostingClassifier(max_iter=250,learning_rate=0.08,random_state=0).fit(Xt,Yt)
    res={k:{d:[] for d in DURS} for k in ("coast","zupt_pred","zupt_true")}
    for _,F,lab,v in te:
        pred=clf.predict(F)                       # 1 = moving, 0 = stationary
        for dur in DURS:
            NW=int(dur/(HOP/FS))
            st=[s for s in range(0,len(v)-NW,10) if v[s]>4.2]      # stops ALLOWED inside
            if not st: continue
            for s in rng.choice(st,size=min(250,len(st)),replace=False):
                dt=float(np.sum(v[s:s+NW])*(HOP/FS))
                if dt<20: continue
                for key in ("coast","zupt_pred","zupt_true"):
                    ve=v[s]; de=0.0
                    for j in range(NW):
                        i=s+j
                        if key=="zupt_pred" and pred[i]==0: ve=0.0
                        if key=="zupt_true" and lab[i]==0:  ve=0.0
                        de+=max(ve,0.0)*(HOP/FS)
                    res[key][dur].append(abs(de-dt)/dt*100)
    for dur in DURS:
        if not res["coast"][dur]: continue
        out.append(dict(driver=held,dur=dur,n=len(res["coast"][dur]),
            coast=round(float(np.median(res["coast"][dur])),1),
            zupt=round(float(np.median(res["zupt_pred"][dur])),1),
            zupt_true=round(float(np.median(res["zupt_true"][dur])),1)))
T=pd.DataFrame(out)
print("DRIFT WITH REALISTIC BLACKOUTS (stops allowed inside)\n")
print(f"  {'driver':<8}{'dur':>5}{'coast':>9}{'+ZUPT (AI)':>13}{'gain':>8}{'+ZUPT (true)':>15}")
for _,r in T.iterrows():
    print(f"  {r.driver:<8}{r.dur:>4}s{r.coast:>8.1f}%{r.zupt:>12.1f}%{r.coast-r.zupt:>+7.1f}{r.zupt_true:>14.1f}%")
print("\nPOOLED")
for dur in DURS:
    s=T[T.dur==dur]
    if len(s): print(f"  {dur:>3}s   coast {s.coast.mean():5.1f}%   +ZUPT {s.zupt.mean():5.1f}%   gain {s.coast.mean()-s.zupt.mean():+.1f}")
