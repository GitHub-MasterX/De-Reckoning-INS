"""Two tests to close out the sync question.
A) The 2 dead sessions: do the phone's GPS track and the vehicle's GPS track describe
   the SAME journey? If not, the files are simply mispaired.
B) The 38 unverifiable sessions: verify with braking/acceleration instead of turning."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
FS=10.0
T=pd.read_csv("data/sessions_verdict.csv")

def haversine(la1,lo1,la2,lo2):
    R=6371000.0; p1,p2=np.radians(la1),np.radians(la2)
    dp,dl=np.radians(la2-la1),np.radians(lo2-lo1)
    a=np.sin(dp/2)**2+np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

print("="*74); print("A. THE TWO DEAD SESSIONS - are the files even from the same drive?")
print("="*74)
for drive,sess in [("Y1",3),("S4",1),("S1",0)]:      # S1 = healthy control
    d=pd.read_parquet(Path("data/clean")/f"{drive}.parquet"); d=d[d.session==sess]
    ok=np.isfinite(d.phone_lat)&np.isfinite(d.lat)&(d.phone_lat.abs()>1)&(d.lat.abs()>1)
    if ok.sum()<100: print(f"  {drive}/s{sess}: no usable GPS pair"); continue
    sep=haversine(d.phone_lat[ok].to_numpy(),d.phone_lon[ok].to_numpy(),
                  d.lat[ok].to_numpy(),d.lon[ok].to_numpy())
    tag="CONTROL (verified)" if drive=="S1" else "dead session"
    print(f"  {drive}/s{sess:<2} [{tag}]  phone-GPS vs vehicle-GPS separation:")
    print(f"       median {np.median(sep):>8.0f} m   p90 {np.percentile(sep,90):>8.0f} m   max {sep.max():>9.0f} m")

print("\n"+"="*74); print("B. THE UNVERIFIABLE SESSIONS - verify by braking instead of turning")
print("="*74)
def fit_lag(X,y,maxlag_s=30,decim=2):
    ok=np.isfinite(X).all(1)&np.isfinite(y)
    X,y=X[ok],y[ok]
    if len(y)<600 or np.std(y)<0.05: return np.nan,np.nan
    Xd,yd=X[::decim],y[::decim]; step=FS/decim
    ml=int(min(maxlag_s*step,len(yd)//4)); bl,br=0,0.0
    for L in range(-ml,ml+1):
        if L<0: x,t=Xd[-L:],yd[:len(yd)+L]
        elif L>0: x,t=Xd[:len(Xd)-L],yd[L:]
        else: x,t=Xd,yd
        if len(x)<60: continue
        A=np.c_[x,np.ones(len(x))]; c,*_=np.linalg.lstsq(A,t,rcond=None)
        r=np.corrcoef(A@c,t)[0,1]
        if np.isfinite(r) and abs(r)>abs(br): bl,br=L,r
    return bl/step,br

rows=[]
for _,r in T[T.verdict=="unverifiable"].iterrows():
    d=pd.read_parquet(Path("data/clean")/f"{r.drive}.parquet"); d=d[d.session==r.session]
    if len(d)<600: continue
    lag,rr=fit_lag(d[["ax","ay","az"]].to_numpy(), d.lon_acc.to_numpy())
    rows.append(dict(drive=r.drive,session=int(r.session),minutes=r.minutes,km=r.km,
                     v_mean=r.v_mean,yaw_r=r.sync_r,accel_r=round(rr,3) if np.isfinite(rr) else np.nan,
                     accel_lag=round(lag,2) if np.isfinite(lag) else np.nan))
U=pd.DataFrame(rows)
tested=U[U.accel_r.notna()]
print(f"tested {len(tested)}/{len(U)} unverifiable sessions using longitudinal acceleration\n")
for t in (0.7,0.5,0.3):
    s=tested[tested.accel_r.abs()>=t]
    print(f"  |accel_r| >= {t}: {len(s):>2} sessions, {s.minutes.sum()/60:>5.2f} h, {s.km.sum():>6.0f} km")
print()
print(tested.sort_values("minutes",ascending=False).head(14).to_string(index=False))
tested.to_csv("data/accel_sync.csv",index=False)
