"""Lag is constant, yet windowed correlation only reaches ~0.6. If the phone SHIFTED in
its holder mid-drive, the phone->vehicle rotation changes and no single fit works.
Test: fit the rotation per 5-min window and see whether its direction moves."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
FS=10.0; WIN=int(5*60*FS); HOP=int(2*60*FS)

def axis_per_window(d):
    """For each window, the unit 3-vector mapping phone gyro -> vehicle yaw rate."""
    W=d[["gx","gy","gz"]].to_numpy(); y=d.yaw_rate.to_numpy()
    out=[]
    for s in range(0,len(d)-WIN,HOP):
        x,t=W[s:s+WIN],y[s:s+WIN]
        ok=np.isfinite(x).all(1)&np.isfinite(t)
        if ok.sum()<WIN*0.5 or np.std(t[ok])<1e-6: continue
        A=np.c_[x[ok],np.ones(ok.sum())]
        c,*_=np.linalg.lstsq(A,t[ok],rcond=None)
        v=c[:3]; n=np.linalg.norm(v)
        if n<1e-9: continue
        r=np.corrcoef(A@c,t[ok])[0,1]
        if abs(r)<0.5: continue
        out.append((s/FS/60, v/n, r))
    return out

cases=[("S1",0,"verified"),("S3c",0,"verified"),("M",2,"verified"),
       ("Vw4",0,"BROKEN"),("Vw2",0,"BROKEN"),("Vta29",0,"BROKEN"),
       ("Vta30",0,"BROKEN"),("Vta16",0,"BROKEN"),("Vtb1",1,"BROKEN")]
print(f"{'session':<12}{'verdict':<10}{'wins':>6}{'median r':>10}{'axis swing':>13}{'max step':>11}")
print("-"*64)
for drive,sess,verd in cases:
    f=Path("data/clean")/f"{drive}.parquet"
    if not f.exists(): continue
    d=pd.read_parquet(f); d=d[d.session==sess].reset_index(drop=True)
    o=axis_per_window(d)
    if len(o)<3:
        print(f"{drive+'/s'+str(sess):<12}{verd:<10}{len(o):>6}{'--':>10}{'--':>13}{'--':>11}"); continue
    V=np.array([x[1] for x in o]); R=np.array([x[2] for x in o])
    # angle of each window's axis from the drive's mean axis
    mean=V.mean(0); mean/=np.linalg.norm(mean)
    ang=np.degrees(np.arccos(np.clip(V@mean,-1,1)))
    step=np.degrees(np.arccos(np.clip(np.sum(V[1:]*V[:-1],axis=1),-1,1)))
    print(f"{drive+'/s'+str(sess):<12}{verd:<10}{len(o):>6}{np.median(R):>10.2f}"
          f"{ang.max():>11.1f}°{step.max():>10.1f}°")
print("\naxis swing = furthest any window's orientation sits from the drive average")
print("max step   = largest change between two consecutive windows (2 min apart)")
