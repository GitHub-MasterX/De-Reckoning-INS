"""THE number: simulate a 60 s GNSS blackout and measure position drift as % of
distance travelled. Uses only sync-verified, lag-corrected drives."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset")
FS, WIN, HOP = 10.0, 20, 5
def num(df,c): return pd.to_numeric(df[c],errors="coerce").to_numpy()
def col(df,p):
    m=[c for c in df.columns if c.startswith(p)]; return m[0] if m else None

SY = pd.read_csv("/home/masterx/sih/out/sync_v2.csv")
good = SY[SY.r_3axis.abs()>=0.70]
print(f"Using {len(good)} sync-verified drives (|r|>=0.70):")
print(good[["drive","lag_s","r_3axis","n"]].to_string(index=False), "\n")

vmap={p.name.lower():p for p in (ROOT/"V-Dataset").iterdir()}
drives=[]
for _,row in good.iterrows():
    sp=ROOT/"S-Dataset"/f"{row.drive}.csv"; vp=vmap.get(row.drive.replace("S-","V-",1).lower()+".csv")
    if vp is None or not sp.exists(): continue
    S=pd.read_csv(sp,encoding="latin-1",low_memory=False); V=pd.read_csv(vp,encoding="latin-1",low_memory=False)
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); S,V=S.iloc[:n],V.iloc[:n]
    gy=[c for c in S.columns if c.startswith("GYROSCOPE")]
    X=np.c_[num(S,col(S,"ACCELEROMETER X")),num(S,col(S,"ACCELEROMETER Y")),num(S,col(S,"ACCELEROMETER Z")),
            num(S,gy[0]),num(S,gy[1]),num(S,gy[2])]
    y=num(V,"Velocity (km/hr)")
    ok=np.isfinite(X).all(1)&np.isfinite(y); X,y=X[ok],y[ok]
    L=int(round(row.lag_s*FS))
    if L>0:   X,y = X[:len(X)-L], y[L:]
    elif L<0: X,y = X[-L:], y[:len(y)+L]
    drives.append((row.drive,X,y))

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

prep=[]
for nm,X,y in drives:
    idx=np.arange(0,len(y)-WIN,HOP)
    F=np.array([feats(X[i:i+WIN]) for i in idx])
    dv=np.array([y[i+WIN-1]-y[i] for i in idx])
    v =np.array([y[i+WIN-1]     for i in idx])
    prep.append((nm,F,dv,v,idx))

rng=np.random.default_rng(0); results=[]
for h in range(len(prep)):                                     # leave-one-drive-out
    tr=[i for i in range(len(prep)) if i!=h]
    Xtr=np.vstack([prep[i][1] for i in tr]); dtr=np.concatenate([prep[i][2] for i in tr])
    mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
    m=HistGradientBoostingRegressor(max_iter=400,learning_rate=0.08,random_state=0).fit((Xtr-mu)/sd,dtr)
    nm,F,dv,v,idx=prep[h]; pred=m.predict((F-mu)/sd)
    mae=np.abs(pred-dv).mean()

    # --- blackout simulation: 60 s = 120 windows at 0.5 s hop ---
    NW=120; drifts=[]
    starts=[s for s in range(0,len(v)-NW,20) if v[s]>15 and (v[s:s+NW]>5).all()]
    for s in rng.choice(starts, size=min(400,len(starts)), replace=False) if starts else []:
        v_est=v[s]; d_est=0.0
        for k in range(NW):
            v_est += pred[s+k]                                 # only the model, no GNSS
            d_est += v_est/3.6*HOP/FS
        d_true=np.sum(v[s:s+NW]/3.6*HOP/FS)
        if d_true>50: drifts.append(abs(d_est-d_true)/d_true*100)
    drifts=np.array(drifts)
    if len(drifts):
        results.append((nm,mae,len(drifts),np.median(drifts),np.percentile(drifts,90),drifts.max()))
        print(f"  held-out {nm:<8} MAE={mae:.2f} km/h | {len(drifts):>3} blackouts | "
              f"drift median {np.median(drifts):>6.1f}%  p90 {np.percentile(drifts,90):>6.1f}%  worst {drifts.max():>6.1f}%")

if results:
    R=pd.DataFrame(results,columns=["drive","mae","n","median","p90","worst"])
    print(f"\n{'='*70}\nACROSS ALL HELD-OUT DRIVES   (benchmark: under 10%)")
    print(f"  median drift : {R['median'].median():.1f}%")
    print(f"  p90 drift    : {R['p90'].median():.1f}%")
    print(f"  folds passing 10% on median: {(R['median']<10).sum()}/{len(R)}")
