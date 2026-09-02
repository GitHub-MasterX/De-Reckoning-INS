"""Baseline: can vehicle speed be regressed from 10 Hz phone IMU windows?
Held-out-DRIVE split (no window leakage). This is the go/no-go number for Model A."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.dummy import DummyRegressor

ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset")
FS, WIN, HOP = 10.0, 20, 5          # 2.0 s window, 0.5 s hop

def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()
def col(df,p):
    m=[c for c in df.columns if c.startswith(p)]; return m[0] if m else None

def featurize(sp, vp):
    S=pd.read_csv(sp,encoding="latin-1",low_memory=False); V=pd.read_csv(vp,encoding="latin-1",low_memory=False)
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); S,V=S.iloc[:n],V.iloc[:n]
    A=np.c_[num(S,col(S,"ACCELEROMETER X")),num(S,col(S,"ACCELEROMETER Y")),num(S,col(S,"ACCELEROMETER Z"))]
    gy=[c for c in S.columns if c.startswith("GYROSCOPE")]
    W=np.c_[num(S,gy[0]),num(S,gy[1]),num(S,gy[2])]
    y=num(V,"Velocity (km/hr)")                      # VBOX GPS velocity = ground truth
    X=np.c_[A,W]; ok=np.isfinite(X).all(1)&np.isfinite(y)
    X,y=X[ok],y[ok]
    if len(y)<WIN*4: return None,None
    idx=np.arange(0,len(y)-WIN,HOP)
    F=[]
    for i in idx:
        w=X[i:i+WIN]                                 # (20,6)
        amag=np.linalg.norm(w[:,:3],axis=1); wmag=np.linalg.norm(w[:,3:],axis=1)
        f=[]
        for c in range(6):
            s=w[:,c]; f += [s.mean(), s.std(), s.min(), s.max(), np.abs(np.diff(s)).mean()]
        f += [amag.mean(), amag.std(), wmag.mean(), wmag.std()]
        # crude spectral energy in 3 bands (all below Nyquist=5 Hz)
        for c in (0,1,2):
            sp_=np.abs(np.fft.rfft(w[:,c]-w[:,c].mean()))**2
            fr=np.fft.rfftfreq(WIN,1/FS)
            for lo,hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)):
                f.append(np.log(sp_[(fr>=lo)&(fr<hi)].sum()+1e-9))
        F.append(f)
    yv   = np.array([y[i:i+WIN].mean() for i in idx])
    ydv  = np.array([y[i+WIN-1]-y[i] for i in idx])          # speed CHANGE across the 2 s window
    return np.array(F), np.c_[yv, ydv]

Sd, Vd = ROOT/"S-Dataset", ROOT/"V-Dataset"
vmap = {p.name.lower(): p for p in Vd.iterdir()}
data=[]
for sp in sorted(Sd.iterdir()):
    vp = vmap.get(sp.name.replace("S-","V-",1).lower())
    if vp is None: continue
    try: F,y = featurize(sp,vp)
    except Exception as e:
        print(f"  ERR {sp.name}: {type(e).__name__}: {e}"); continue
    if F is None or len(y)<50 or np.nanmax(y[:,0])<5: continue
    data.append((sp.stem,F,y))
print(f"{len(data)} drives featurized, {sum(len(y) for _,_,y in data)} windows total")

names=[d[0] for d in data]
rng=np.random.default_rng(0); order=rng.permutation(len(data))
n_te=max(1,len(data)//4); te=set(order[:n_te]); tr=[i for i in range(len(data)) if i not in te]
Xtr=np.vstack([data[i][1] for i in tr]); ytr=np.concatenate([data[i][2] for i in tr])
Xte=np.vstack([data[i][1] for i in te]); yte=np.concatenate([data[i][2] for i in te])
YTR, YTE = ytr, yte
print(f"train {len(ytr)} windows / {len(tr)} drives  |  test {len(yte)} windows / {len(te)} drives (HELD-OUT DRIVES)")
print(f"test drives: {[names[i] for i in sorted(te)][:10]}")
print(f"speed range: train {ytr[:,0].min():.0f}-{ytr[:,0].max():.0f}, test {yte[:,0].min():.0f}-{yte[:,0].max():.0f} km/h\n")

mu,sd_=Xtr.mean(0),Xtr.std(0)+1e-9
Xtrn,Xten=(Xtr-mu)/sd_,(Xte-mu)/sd_
for ti,tname in [(0,"ABSOLUTE SPEED (km/h)"), (1,"SPEED CHANGE over 2 s window (km/h)")]:
    ytr_,yte_=YTR[:,ti],YTE[:,ti]
    print(f"\n--- target: {tname} ---   (test std = {yte_.std():.2f})")
    for nm, m in [("Dummy (predict mean)", DummyRegressor()),
                  ("Ridge (linear)", Ridge(alpha=1.0)),
                  ("HistGradientBoosting", HistGradientBoostingRegressor(max_iter=400, learning_rate=0.08, random_state=0))]:
        m.fit(Xtrn, ytr_); p=m.predict(Xten)
        mae=np.abs(p-yte_).mean(); rmse=np.sqrt(((p-yte_)**2).mean()); r=np.corrcoef(p,yte_)[0,1]
        print(f"  {nm:24s} MAE={mae:6.3f}  RMSE={rmse:6.3f}  r={r:+.3f}")
    if ti==1:
        m=HistGradientBoostingRegressor(max_iter=400,learning_rate=0.08,random_state=0).fit(Xtrn,ytr_)
        p=m.predict(Xten)
        # what does that dv error imply for distance drift over 60 s of blackout at 10% budget?
        err_per_win=np.abs(p-yte_).mean()          # km/h error per 2 s step
        n_win=30                                   # 60 s blackout
        v_err=err_per_win*np.sqrt(n_win)           # random-walk growth of velocity error
        d_err=v_err/3.6*60/2                       # mean velocity error x time (triangular)
        print(f"  => 60 s blackout at 60 km/h (1 km travelled):")
        print(f"     velocity error after 60 s ~ {v_err:.1f} km/h ; position drift ~ {d_err:.0f} m  (budget: 100 m)")
