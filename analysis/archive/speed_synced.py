"""Re-run the speed-change model, but first screen and time-correct every S/V pair.
Gyro-vs-CAN-yaw cross-correlation gives both the sync quality and the lag."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.dummy import DummyRegressor
ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset")
FS, WIN, HOP, MAXLAG = 10.0, 20, 5, 300      # +/- 30 s lag search
def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()
def col(df,p):
    m=[c for c in df.columns if c.startswith(p)]; return m[0] if m else None

def best_lag(a, b, maxlag=MAXLAG):
    a=(a-a.mean())/(a.std()+1e-12); b=(b-b.mean())/(b.std()+1e-12)
    best=(0,0.0)
    for L in range(-maxlag, maxlag+1, 2):
        if L<0: x,y=a[-L:],b[:len(b)+L]
        elif L>0: x,y=a[:len(a)-L],b[L:]
        else: x,y=a,b
        if len(x)<500: continue
        r=np.corrcoef(x,y)[0,1]
        if abs(r)>abs(best[1]): best=(L,r)
    return best

vmap={p.name.lower():p for p in (ROOT/"V-Dataset").iterdir()}
rows, kept = [], []
for sp in sorted((ROOT/"S-Dataset").iterdir()):
    vp=vmap.get(sp.name.replace("S-","V-",1).lower())
    if vp is None: continue
    try:
        S=pd.read_csv(sp,encoding="latin-1",low_memory=False); V=pd.read_csv(vp,encoding="latin-1",low_memory=False)
    except Exception: continue
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); S,V=S.iloc[:n].reset_index(drop=True),V.iloc[:n].reset_index(drop=True)
    gy=[c for c in S.columns if c.startswith("GYROSCOPE")]
    W=np.c_[num(S,gy[0]),num(S,gy[1]),num(S,gy[2])]
    A=np.c_[num(S,col(S,"ACCELEROMETER X")),num(S,col(S,"ACCELEROMETER Y")),num(S,col(S,"ACCELEROMETER Z"))]
    yawcan=num(V,"Yaw Rate (deg/sec)")*np.pi/180
    y=num(V,"Velocity (km/hr)")
    ok=np.isfinite(W).all(1)&np.isfinite(A).all(1)&np.isfinite(yawcan)&np.isfinite(y)
    W,A,yawcan,y=W[ok],A[ok],yawcan[ok],y[ok]
    if len(y)<3000 or np.nanmax(y)<10: continue
    bi=np.argmax([abs(np.corrcoef(W[:,i],yawcan)[0,1]) for i in range(3)])
    L,r = best_lag(W[:,bi], yawcan)
    rows.append((sp.stem, L/10.0, r, len(y)))
    if abs(r) < 0.70: continue
    if L>0:   Wc,Ac,yc = W[:len(W)-L], A[:len(A)-L], y[L:]
    elif L<0: Wc,Ac,yc = W[-L:], A[-L:], y[:len(y)+L]
    else:     Wc,Ac,yc = W,A,y
    kept.append((sp.stem, np.c_[Ac,Wc], yc))

D=pd.DataFrame(rows, columns=["drive","lag_s","r","n"])
D.to_csv("/home/masterx/sih/out/sync.csv", index=False)
print(f"=== SYNC SCREEN over {len(D)} drives ===")
print(f"  |r| >= 0.90 (excellent) : {(D.r.abs()>=0.90).sum()}")
print(f"  |r| >= 0.70 (usable)    : {(D.r.abs()>=0.70).sum()}")
print(f"  |r| <  0.70 (discarded) : {(D.r.abs()<0.70).sum()}")
print(f"  lag = 0 s               : {(D.lag_s==0).sum()}   |lag| > 1 s: {(D.lag_s.abs()>1).sum()}")
print(f"  median |lag| among usable: {D[D.r.abs()>=0.70].lag_s.abs().median():.1f} s")
print(f"  -> kept {len(kept)} drives for training\n")

def featurize(X, y):
    idx=np.arange(0,len(y)-WIN,HOP); F=[]
    for i in idx:
        w=X[i:i+WIN]; f=[]
        for c in range(6):
            s=w[:,c]; f += [s.mean(), s.std(), s.min(), s.max(), np.abs(np.diff(s)).mean()]
        am=np.linalg.norm(w[:,:3],axis=1); wm=np.linalg.norm(w[:,3:],axis=1)
        f += [am.mean(), am.std(), wm.mean(), wm.std()]
        for c in (0,1,2):
            P=np.abs(np.fft.rfft(w[:,c]-w[:,c].mean()))**2; fr=np.fft.rfftfreq(WIN,1/FS)
            for lo,hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)):
                f.append(np.log(P[(fr>=lo)&(fr<hi)].sum()+1e-9))
        F.append(f)
    return np.array(F), np.array([y[i+WIN-1]-y[i] for i in idx]), np.array([y[i:i+WIN].mean() for i in idx])

data=[(nm,)+featurize(X,y) for nm,X,y in kept]
rng=np.random.default_rng(0); order=rng.permutation(len(data)); n_te=max(1,len(data)//4)
te=set(order[:n_te]); tr=[i for i in range(len(data)) if i not in te]
Xtr=np.vstack([data[i][1] for i in tr]); dtr=np.concatenate([data[i][2] for i in tr])
Xte=np.vstack([data[i][1] for i in te]); dte=np.concatenate([data[i][2] for i in te])
print(f"train {len(dtr)} windows / {len(tr)} drives | test {len(dte)} windows / {len(te)} HELD-OUT drives")
mu,sd=Xtr.mean(0),Xtr.std(0)+1e-9
print(f"\n--- target: SPEED CHANGE over 2 s (test std {dte.std():.2f}) ---")
for nm,m in [("Dummy",DummyRegressor()),("HistGradientBoosting",HistGradientBoostingRegressor(max_iter=400,learning_rate=0.08,random_state=0))]:
    m.fit((Xtr-mu)/sd,dtr); p=m.predict((Xte-mu)/sd)
    print(f"  {nm:22s} MAE={np.abs(p-dte).mean():6.3f}  RMSE={np.sqrt(((p-dte)**2).mean()):6.3f}  r={np.corrcoef(p,dte)[0,1]:+.3f}")
