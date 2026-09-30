"""
AI motion classifier - the PS capability we had not attempted.

  "dynamically detect and filter out non-navigation motions such as engine idling
   vibrations, pothole shocks, bumps, and accidental phone misalignments"

Classification suits this sensor far better than regression does. Forward acceleration is
a small continuous quantity buried in noise; a stopped-but-idling vehicle and a pothole
strike are large discrete events.

  1. STATIONARY vs MOVING, from IMU only. The hard case is a stopped vehicle with the
     engine running: it vibrates, so naive energy thresholds call it motion.
  2. SHOCK detection (potholes, bumps). No ground truth exists in IO-VNBD, so these are
     characterised rather than scored.

Labels come from vehicle speed and engine RPM. Held out BY DRIVER.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import confusion_matrix
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0; W=20; HOP=5
A=pd.read_csv("/home/masterx/sih/data/test_outputs/alignment.csv")
sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]

def feats(a,g):
    """IMU-only descriptors. No speed, no vehicle data."""
    am=np.linalg.norm(a,axis=1); gm=np.linalg.norm(g,axis=1)
    f=[am.mean(),am.std(),am.min(),am.max(),np.abs(np.diff(am)).mean(),
       gm.mean(),gm.std(),gm.max()]
    for c in range(3):
        f+=[a[:,c].std(),np.abs(np.diff(a[:,c])).mean(),g[:,c].std()]
    for c in range(3):
        P=np.abs(np.fft.rfft(a[:,c]-a[:,c].mean()))**2; fr=np.fft.rfftfreq(W,1/FS)
        for lo,hi in ((0.5,1.5),(1.5,3.0),(3.0,5.0)): f.append(np.log(P[(fr>=lo)&(fr<hi)].sum()+1e-9))
    return f

X,Y,D,RPM=[],[],[],[]
for _,r in sel.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=d[(d.session==r.session)&d.aligned_valid].reset_index(drop=True)
    if len(d)<3000: continue
    a=d[["ax","ay","az"]].to_numpy(); g=d[["gx_c","gy_c","gz_c"]].to_numpy()
    v=d.speed_best_al.to_numpy(); rpm=d.engine_rpm.to_numpy()
    ok=np.isfinite(a).all(1)&np.isfinite(g).all(1)&np.isfinite(v)
    a,g,v,rpm=a[ok],g[ok],v[ok],rpm[ok]
    if len(v)<3000: continue
    for i in range(0,len(v)-W,HOP):
        vm=v[i:i+W]
        if vm.max()<1.0:   lab=0                      # stationary
        elif vm.min()>5.0: lab=1                      # moving
        else: continue                                # ambiguous - skip
        X.append(feats(a[i:i+W],g[i:i+W])); Y.append(lab); D.append(r.driver)
        RPM.append(float(np.nanmean(rpm[i:i+W])) if np.isfinite(rpm[i:i+W]).any() else np.nan)
X=np.array(X); Y=np.array(Y); D=np.array(D); RPM=np.array(RPM)
print(f"{len(Y):,} windows   stationary {np.sum(Y==0):,} ({100*np.mean(Y==0):.1f}%)   moving {np.sum(Y==1):,}\n")

print("STATIONARY vs MOVING - leave-one-driver-out, IMU only\n")
print(f"  {'held out':<10}{'n test':>9}{'accuracy':>11}{'stat recall':>13}{'stat prec':>11}{'idling recall':>15}")
accs=[]
for h in ["A","B","D","E"]:
    tr=D!=h; te=D==h
    if te.sum()<200 or len(np.unique(Y[tr]))<2: continue
    m=HistGradientBoostingClassifier(max_iter=300,learning_rate=0.08,random_state=0).fit(X[tr],Y[tr])
    p=m.predict(X[te]); yt=Y[te]
    cm=confusion_matrix(yt,p,labels=[0,1])
    acc=(p==yt).mean()
    rec=cm[0,0]/max(cm[0].sum(),1); prec=cm[0,0]/max(cm[:,0].sum(),1)
    idle=(yt==0)&(RPM[te]>400)                       # stopped WITH the engine running
    ir=(p[idle]==0).mean() if idle.sum()>30 else np.nan
    accs.append(acc)
    print(f"  {h:<10}{te.sum():>9,}{acc:>10.1%}{rec:>13.1%}{prec:>11.1%}"
          + (f"{ir:>15.1%}" if np.isfinite(ir) else f"{'n/a':>15}"))
print(f"\n  mean accuracy across drivers: {np.mean(accs):.1%}")

# naive baseline: threshold on vibration energy alone
thr=np.median(X[Y==1,1])*0.5
naive=(X[:,1]>thr).astype(int)
print(f"  naive energy threshold gives : {(naive==Y).mean():.1%}   <- what the model has to beat")

print("\n\nSHOCK EVENTS (potholes / bumps) - characterised, no ground truth available\n")
tot=cnt=0; durs=[]
for _,r in sel.head(12).iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=d[(d.session==r.session)&d.aligned_valid]
    if len(d)<3000 or "acc_down" not in d.columns: continue
    ad=d.acc_down.to_numpy(); v=d.speed_best_al.to_numpy()
    ok=np.isfinite(ad)&np.isfinite(v); ad,v=ad[ok],v[ok]
    hp=ad-pd.Series(ad).rolling(21,center=True,min_periods=1).mean().to_numpy()
    s=np.std(hp); ev=np.abs(hp)>5*s
    lab=np.diff(np.concatenate(([0],ev.astype(int))))
    st=np.flatnonzero(lab==1); en=np.flatnonzero(lab==-1)
    n=min(len(st),len(en))
    if n: durs+=list((en[:n]-st[:n])/FS)
    cnt+=n; tot+=len(v)/FS/60
print(f"  {cnt:,} shock events over {tot:.0f} minutes = {cnt/max(tot,1):.1f} per minute")
if durs:
    dd=np.array(durs)
    print(f"  duration: median {np.median(dd)*1000:.0f} ms, 90th pct {np.percentile(dd,90)*1000:.0f} ms")
    print(f"  under 200 ms (pothole-like): {100*np.mean(dd<0.2):.0f}%   over 400 ms (bump-like): {100*np.mean(dd>0.4):.0f}%")
