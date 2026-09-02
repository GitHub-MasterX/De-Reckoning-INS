"""Is the lag in 'broken' sessions constant, or drifting?
If the phone's true sample rate differs from the VBOX's 10.000 Hz, row-by-row pairing
walks apart linearly:   j = a + b*i   with b = phone_rate_ratio.
Test 1: measure the phone's true sample interval from its own clock.
Test 2: slide a window through the session and see whether the best lag moves."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
FS=10.0
T=pd.read_csv("data/sessions_verdict.csv")
broken=T[(T.verdict=="BROKEN")&(T.minutes>15)].sort_values("minutes",ascending=False)

def best_lag(W,yaw,maxlag_s=40,decim=2):
    ok=np.isfinite(W).all(1)&np.isfinite(yaw)
    W,yaw=W[ok],yaw[ok]
    if len(yaw)<600 or np.std(yaw)<1e-6: return np.nan,np.nan
    Wd,yd=W[::decim],yaw[::decim]; step=FS/decim
    ml=int(min(maxlag_s*step,len(yd)//4)); bl,br=0,0.0
    for L in range(-ml,ml+1):
        if L<0: x,y=Wd[-L:],yd[:len(yd)+L]
        elif L>0: x,y=Wd[:len(Wd)-L],yd[L:]
        else: x,y=Wd,yd
        if len(x)<60: continue
        A=np.c_[x,np.ones(len(x))]; c,*_=np.linalg.lstsq(A,y,rcond=None)
        r=np.corrcoef(A@c,y)[0,1]
        if np.isfinite(r) and abs(r)>abs(br): bl,br=L,r
    return bl/step,br

print(f"{'session':<14}{'mins':>6}{'phone dt':>10}{'ppm':>9}{'predicted drift':>17}{'measured slope':>16}{'win r':>8}")
print("-"*82)
for _,r in broken.iterrows():
    d=pd.read_parquet(Path("data/clean")/f"{r.drive}.parquet"); d=d[d.session==r.session].reset_index(drop=True)
    t=d.t_raw_s.to_numpy()
    dtm=float(np.median(np.diff(t))) if np.isfinite(t).sum()>100 else np.nan
    # robust rate: least-squares slope of t vs index
    ok=np.isfinite(t); idx=np.arange(len(t))[ok]
    slope=np.polyfit(idx,t[ok],1)[0] if ok.sum()>1000 else np.nan
    ppm=(slope-0.1)/0.1*1e6 if np.isfinite(slope) else np.nan
    pred=(slope-0.1)*len(d) if np.isfinite(slope) else np.nan     # seconds of drift over session

    # sliding-window lag
    W=d[["gx","gy","gz"]].to_numpy(); yaw=d.yaw_rate.to_numpy()
    win=int(5*60*FS); hop=int(2*60*FS); pts=[]
    for s in range(0,len(d)-win,hop):
        L,rr=best_lag(W[s:s+win],yaw[s:s+win])
        if np.isfinite(L) and abs(rr)>0.55: pts.append((s/FS,L,rr))
    if len(pts)>=4:
        ts=np.array([p[0] for p in pts]); ls=np.array([p[1] for p in pts]); rs=np.array([p[2] for p in pts])
        m,c0=np.polyfit(ts,ls,1)
        print(f"{r.drive+'/s'+str(int(r.session)):<14}{r.minutes:>6.0f}{slope:>10.5f}{ppm:>9.0f}"
              f"{pred:>15.1f}s{m*ts[-1]:>14.1f}s{np.median(rs):>8.2f}   "
              f"[{len(pts)} windows, L0={c0:+.1f}s]")
    else:
        print(f"{r.drive+'/s'+str(int(r.session)):<14}{r.minutes:>6.0f}{slope:>10.5f}{ppm:>9.0f}"
              f"{pred:>15.1f}s{'--':>15}{'--':>8}   [{len(pts)} usable windows]")
