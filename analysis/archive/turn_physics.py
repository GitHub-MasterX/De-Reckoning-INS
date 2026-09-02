"""
Two speed estimators that avoid integrating longitudinal acceleration.

  A) LATERAL REGRESSION      a_lat = v*omega + b, fitted over a window.
     Slope = speed. Intercept absorbs gravity leak / sensor bias / road banking,
     so the speed estimate is immune to exactly the bias that kills integration.

  B) MAP CURVATURE           omega = v*kappa  ->  v = omega/kappa
     kappa comes from the road geometry, which the map knows a priori with no
     sensor error. Uses only the gyroscope, our best channel (r = 0.96).
     Curvature here is derived from the vehicle's own track = what OSM would supply.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import signal
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
sel=A[(A.sync_r.abs()>=0.70)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]

def smooth(x,fc=0.5):
    sos=signal.butter(2,fc,btype="low",fs=FS,output="sos")
    return signal.sosfiltfilt(sos,x)

rows=[]
for _,r in sel.iterrows():
    base=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=base[(base.session==r.session)&base.aligned_valid].reset_index(drop=True)
    if len(d)<6000 or "acc_lat" not in d.columns: continue
    vi=d.veh_idx.to_numpy()
    al=d.acc_lat.to_numpy(); yr=d.rate_yaw.to_numpy(); v=d.speed_best_al.to_numpy()/3.6
    # vehicle position must be read through veh_idx, or it is offset from the gyro
    lat=base.lat.to_numpy()[vi]; lon=base.lon.to_numpy()[vi]
    ok=np.isfinite(al)&np.isfinite(yr)&np.isfinite(v)
    if ok.sum()<6000: continue
    al,yr,v,lat,lon=al[ok],yr[ok],v[ok],lat[ok],lon[ok]
    als,yrs=smooth(al),smooth(yr)

    # ---- A) lateral regression over sliding windows ----
    W=int(6*FS); H=int(1*FS)
    est_a,tru_a,ptw=[],[],[]
    for s in range(0,len(v)-W,H):
        w_om=yrs[s:s+W]; w_al=als[s:s+W]
        if np.std(w_om)<0.03 or v[s:s+W].min()<3: continue
        X=np.c_[w_om,np.ones(W)]
        c,*_=np.linalg.lstsq(X,w_al,rcond=None)
        if 0<c[0]<60:
            est_a.append(c[0]); tru_a.append(float(np.mean(v[s:s+W])))
            m=np.abs(w_om)>0.12
            if m.sum()>10: ptw.append(float(np.median(np.abs(w_al[m]/w_om[m]))))
    # ---- B) curvature from the track: kappa = dtheta/ds ----
    x=(lon-lon.mean())*111320*np.cos(np.radians(lat.mean())); y=(lat-lat.mean())*110540
    dx,dy=np.gradient(smooth(x,0.2)),np.gradient(smooth(y,0.2))
    ds=np.hypot(dx,dy); th=np.unwrap(np.arctan2(dy,dx))
    kap=np.gradient(smooth(th,0.2))/np.maximum(ds,1e-3)
    est_b,tru_b=[],[]
    for s in range(0,len(v)-W,H):
        k=np.abs(kap[s:s+W]); om=np.abs(yrs[s:s+W])
        m=(k>0.004)&(om>0.05)                       # radius under 250 m, actually turning
        if m.sum()<20 or v[s:s+W].min()<3: continue
        ve=float(np.median(om[m]/k[m]))
        if 0<ve<60: est_b.append(ve); tru_b.append(float(np.mean(v[s:s+W])))
    def stat(e,t):
        if len(e)<20: return (np.nan,np.nan,0)
        e,t=np.array(e),np.array(t)
        return (float(np.corrcoef(e,t)[0,1]), float(np.abs(e-t).mean()*3.6), len(e))
    ra,ma,na=stat(est_a,tru_a); rb,mb,nb=stat(est_b,tru_b)
    rp,mp,_=stat(ptw,tru_a[:len(ptw)]) if len(ptw)>20 else (np.nan,np.nan,0)
    rows.append(dict(session=f"{r.drive}/s{int(r.session)}",driver=r.driver,
        reg_r=ra,reg_mae=ma,reg_n=na, ptw_r=rp,ptw_mae=mp, map_r=rb,map_mae=mb,map_n=nb))
R=pd.DataFrame(rows)
print("SPEED FROM TURNS - three estimators, same windows\n")
print(f"{'':<14}{'r':>8}{'MAE km/h':>11}{'windows':>10}")
for lab,rc,mc,nc in [("A) regression","reg_r","reg_mae","reg_n"),
                     ("   pointwise ratio","ptw_r","ptw_mae","reg_n"),
                     ("B) map curvature","map_r","map_mae","map_n")]:
    print(f"  {lab:<20}{R[rc].median():>6.3f}{R[mc].median():>10.1f}{int(R[nc].sum()):>10}")
print("\nper session:")
print(R.round(3).to_string(index=False))
