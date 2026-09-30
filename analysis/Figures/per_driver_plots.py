"""
Leave-one-driver-out: train on three drivers, test on the fourth, rotate.
Plot drift against distance travelled, model vs coast vs oracle, per driver.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
CLEAN=Path("/home/masterx/sih/data/clean"); OUT=Path("/home/masterx/sih/out")
FS,WIN,HOP=10.0,20,5; STEP=HOP/FS
A=pd.read_csv("/home/masterx/sih/data/test_outputs/alignment.csv")
COLS=["acc_fwd","acc_lat","acc_down","rate_roll","rate_pitch","rate_yaw"]
DURS=[5,10,20,30,45,60,90,120]

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
    if len(d)<WIN*30 or not all(c in d.columns for c in COLS): return None
    X=d[COLS].to_numpy(); y=d.speed_best_al.to_numpy()/3.6
    ok=np.isfinite(X).all(1)&np.isfinite(y); X,y=X[ok],y[ok]
    if len(y)<WIN*30: return None
    idx=np.arange(0,len(y)-WIN,HOP)
    return (np.array([feats(X[i:i+WIN]) for i in idx]),
            np.array([y[i+WIN-1]-y[i+WIN-1-HOP] for i in idx]),
            np.array([y[i+WIN-1] for i in idx]))

sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
cache={}
for _,r in sel.iterrows():
    b=build(r.drive,int(r.session))
    if b: cache[(r.drive,int(r.session))]=(r.driver,)+b
print(f"{len(cache)} sessions cached\n")

rng=np.random.default_rng(0); results={}
for held in ["A","B","D","E"]:
    tr=[v for v in cache.values() if v[0]!=held]
    te=[v for v in cache.values() if v[0]==held]
    if not te or not tr: continue
    Xtr=np.vstack([t[1] for t in tr]); dtr=np.concatenate([t[2] for t in tr])
    mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
    m=HistGradientBoostingRegressor(max_iter=400,learning_rate=0.06,random_state=0).fit((Xtr-mu)/sd,dtr)
    curves={k:{d:[] for d in DURS} for k in ("coast","model","oracle")}
    dists={d:[] for d in DURS}
    for _,F,dv,v in te:
        p=m.predict((F-mu)/sd)
        for dur in DURS:
            NW=int(dur/STEP)
            st=[s for s in range(0,len(v)-NW,10) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
            if not st: continue
            for s in rng.choice(st,size=min(200,len(st)),replace=False):
                dt=float(np.sum(v[s:s+NW])*STEP)
                if dt<20: continue
                dists[dur].append(dt)
                for key,pred in (("coast",None),("model",p),("oracle",dv)):
                    ve=v[s]; de=0.0
                    for j in range(NW):
                        if pred is not None: ve+=pred[s+j]
                        de+=max(ve,0.0)*STEP
                    curves[key][dur].append(abs(de-dt)/dt*100)
    results[held]=(curves,dists,len(te),sum(len(t[2]) for t in te))
    print(f"  driver {held}: {len(te)} sessions, trained on {len(dtr):,} windows")

C={"coast":"#6b7280","model":"#c2410c","oracle":"#15803d"}
for metric in ("pct","metres"):
    fig,axes=plt.subplots(2,2,figsize=(13,9.5))
    for ax,drv in zip(axes.ravel(),["A","B","D","E"]):
        if drv not in results: ax.axis("off"); continue
        curves,dists,ns,nw=results[drv]
        for key in ("coast","model","oracle"):
            xs,ys,lo,hi=[],[],[],[]
            for d in DURS:
                if not curves[key][d]: continue
                dd=np.median(dists[d]); v=np.array(curves[key][d])
                xs.append(dd)
                if metric=="pct": ys.append(np.median(v)); lo.append(np.percentile(v,25)); hi.append(np.percentile(v,75))
                else: ys.append(np.median(v)*dd/100); lo.append(np.percentile(v,25)*dd/100); hi.append(np.percentile(v,75)*dd/100)
            ax.plot(xs,ys,"o-",color=C[key],label=key,lw=2,ms=5)
            ax.fill_between(xs,lo,hi,color=C[key],alpha=0.12)
        if metric=="pct":
            ax.axhline(10,color="#dc2626",ls="--",lw=1.5,label="benchmark 10%")
            ax.set_ylabel("drift  (% of distance)"); ax.set_ylim(0,40)
        else:
            xs=np.array([50,2500]); ax.plot(xs,xs*0.10,"--",color="#dc2626",lw=1.5,label="benchmark 10%")
            ax.scatter([50,1000],[5,100],color="#dc2626",zorder=5,s=45,marker="s",label="PS targets")
            ax.set_ylabel("drift  (metres)"); ax.set_ylim(0,320)
        ax.set_xlabel("distance travelled during blackout  (m)")
        ax.set_title(f"Driver {drv}   —   {ns} sessions, {nw:,} windows",fontsize=11,weight="bold")
        ax.grid(alpha=.25); ax.legend(fontsize=8.5,loc="upper left"); ax.set_xlim(0,2200)
    fig.suptitle("Dead-reckoning drift vs blackout distance — leave-one-driver-out"
                 + ("   (percentage)" if metric=="pct" else "   (metres)"),fontsize=13,weight="bold")
    fig.tight_layout()
    fig.savefig(OUT/f"plots/drift_{metric}.png",dpi=150)
    print(f"  wrote outputs/plots/drift_{metric}.png")

rows=[]
for drv,(curves,dists,ns,nw) in results.items():
    for d in DURS:
        if not curves["coast"][d]: continue
        rows.append(dict(driver=drv,dur_s=d,dist_m=round(np.median(dists[d])),
            coast=round(np.median(curves["coast"][d]),1),
            model=round(np.median(curves["model"][d]),1),
            oracle=round(np.median(curves["oracle"][d]),1),
            coast_m=round(np.median(curves["coast"][d])*np.median(dists[d])/100,1),
            n=len(curves["coast"][d])))
T=pd.DataFrame(rows); T.to_csv(OUT/"Results/per_driver_drift.csv",index=False)
print("\n"+T.to_string(index=False))
