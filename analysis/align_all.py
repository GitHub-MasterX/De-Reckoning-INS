"""Two-stage alignment across every session.
  COARSE: match the two GPS tracks over +/-10 min   (finds large offsets, ~+/-5 s resolution)
  FINE:   match gyro against yaw-rate over +/-30 s  (refines to sub-second)
Neither alone is enough: gyro can't see a 300 s offset, GPS can't resolve below ~5 s."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
FS=10.0
def hav(la1,lo1,la2,lo2):
    R=6371000.0; p1,p2=np.radians(la1),np.radians(la2)
    dp,dl=np.radians(la2-la1),np.radians(lo2-lo1)
    return 2*R*np.arcsin(np.sqrt(np.sin(dp/2)**2+np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2))

def coarse(d, maxlag_s=600, dec=10):
    pl,po=d.phone_lat.to_numpy(),d.phone_lon.to_numpy()
    vl,vo=d.lat.to_numpy(),d.lon.to_numpy()
    ok=np.isfinite(pl)&np.isfinite(po)&np.isfinite(vl)&np.isfinite(vo)&(np.abs(pl)>1)&(np.abs(vl)>1)
    if ok.sum()<1000: return np.nan,np.nan
    pl,po,vl,vo=pl[ok][::dec],po[ok][::dec],vl[ok][::dec],vo[ok][::dec]
    step=FS/dec; ml=int(min(maxlag_s*step,len(pl)//3))
    bl,bs=0,1e12
    for L in range(-ml,ml+1):
        if L<0: a1,a2,b1,b2=pl[-L:],po[-L:],vl[:len(vl)+L],vo[:len(vo)+L]
        elif L>0: a1,a2,b1,b2=pl[:len(pl)-L],po[:len(po)-L],vl[L:],vo[L:]
        else: a1,a2,b1,b2=pl,po,vl,vo
        if len(a1)<100: continue
        m=float(np.median(hav(a1,a2,b1,b2)))
        if m<bs: bl,bs=L,m
    return bl/step, bs

def fine(W,y,maxlag_s=30,dec=2):
    ok=np.isfinite(W).all(1)&np.isfinite(y); W,y=W[ok],y[ok]
    if len(y)<600 or np.std(y)<1e-6: return np.nan,np.nan
    Wd,yd=W[::dec],y[::dec]; step=FS/dec
    ml=int(min(maxlag_s*step,len(yd)//4)); bl,br=0,0.0
    for L in range(-ml,ml+1):
        if L<0: x,t=Wd[-L:],yd[:len(yd)+L]
        elif L>0: x,t=Wd[:len(Wd)-L],yd[L:]
        else: x,t=Wd,yd
        if len(x)<60: continue
        A=np.c_[x,np.ones(len(x))]; c,*_=np.linalg.lstsq(A,t,rcond=None)
        r=np.corrcoef(A@c,t)[0,1]
        if np.isfinite(r) and abs(r)>abs(br): bl,br=L,r
    return bl/step,br

def shift(arr_phone, arr_veh, L):
    Ls=int(round(L*FS))
    if Ls>0:  return arr_phone[:len(arr_phone)-Ls], arr_veh[Ls:]
    if Ls<0:  return arr_phone[-Ls:], arr_veh[:len(arr_veh)+Ls]
    return arr_phone, arr_veh

S=pd.read_csv("data/sessions.csv"); out=[]
for _,r in S.iterrows():
    d=pd.read_parquet(Path("data/clean")/f"{r.drive}.parquet"); d=d[d.session==r.session].reset_index(drop=True)
    c_lag,c_sep = coarse(d)
    W=d[["gx","gy","gz"]].to_numpy(); y=d.yaw_rate.to_numpy()
    if np.isfinite(c_lag) and abs(c_lag)>=1:
        Wc,yc = shift(W,y,c_lag)
    else:
        c_lag = 0.0 if np.isfinite(c_lag) else np.nan; Wc,yc = W,y
    f_lag,f_r = fine(Wc,yc)
    total = (c_lag if np.isfinite(c_lag) else 0.0) + (f_lag if np.isfinite(f_lag) else 0.0)
    out.append(dict(drive=r.drive,driver=r.driver,session=int(r.session),minutes=r.minutes,km=r.km,
        v_mean=r.v_mean, old_sync_r=r.sync_r, coarse_lag=round(c_lag,1) if np.isfinite(c_lag) else np.nan,
        gps_sep_m=round(c_sep,0) if np.isfinite(c_sep) else np.nan,
        fine_lag=round(f_lag,1) if np.isfinite(f_lag) else np.nan,
        total_lag=round(total,1), sync_r=round(f_r,3) if np.isfinite(f_r) else np.nan))
A=pd.DataFrame(out); A.to_csv("data/alignment.csv",index=False)
old=S.sync_r.abs(); new=A.sync_r.abs()
print("SYNC QUALITY, before vs after two-stage alignment\n")
for t in (0.9,0.8,0.7,0.5):
    ob=(old>=t).sum(); nb=(new>=t).sum()
    oh=S[old>=t].minutes.sum()/60; nh=A[new>=t].minutes.sum()/60
    print(f"  |sync_r| >= {t}: {ob:>2} -> {nb:>2} sessions   {oh:>5.1f} h -> {nh:>5.1f} h")
print(f"\n  untestable: {S.sync_r.isna().sum()} -> {A.sync_r.isna().sum()}")
print(f"\nsessions needing a coarse shift larger than 30 s (invisible to the old search):")
big=A[A.coarse_lag.abs()>30].sort_values("minutes",ascending=False)
print(big[["drive","driver","session","minutes","old_sync_r","coarse_lag","total_lag","sync_r","gps_sep_m"]].to_string(index=False))
print(f"\n  -> {big.minutes.sum()/60:.1f} h recovered by widening the search")
print("\nUSABLE HOURS BY DRIVER (|sync_r| >= 0.7 after alignment):")
g=A[new>=0.7].groupby("driver").agg(sessions=("drive","count"),hours=("minutes",lambda x:round(x.sum()/60,2)),km=("km","sum"))
tot=A.groupby("driver").agg(all_h=("minutes",lambda x:round(x.sum()/60,2)))
print(g.join(tot,how="right").fillna(0).to_string())
