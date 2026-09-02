"""The 'dead' sessions show phone-GPS and vehicle-GPS hundreds of metres apart.
That is either a mispairing, OR a time offset far larger than the +/-30 s I searched.
At 30 km/h, 648 m of separation is ~78 s of offset - outside my search window.
Align the two GPS TRACKS directly, over +/-10 minutes."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
FS=10.0
def hav(la1,lo1,la2,lo2):
    R=6371000.0; p1,p2=np.radians(la1),np.radians(la2)
    dp,dl=np.radians(la2-la1),np.radians(lo2-lo1)
    a=np.sin(dp/2)**2+np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def track_align(d, maxlag_s=600, step_s=1.0):
    pl,po=d.phone_lat.to_numpy(),d.phone_lon.to_numpy()
    vl,vo=d.lat.to_numpy(),d.lon.to_numpy()
    ok=np.isfinite(pl)&np.isfinite(po)&np.isfinite(vl)&np.isfinite(vo)&(np.abs(pl)>1)&(np.abs(vl)>1)
    if ok.sum()<500: return None
    pl,po,vl,vo=pl[ok],po[ok],vl[ok],vo[ok]
    best=(0,1e12)
    for Ls in np.arange(-maxlag_s,maxlag_s+step_s,step_s):
        L=int(round(Ls*FS))
        if L<0: a=(pl[-L:],po[-L:]); b=(vl[:len(vl)+L],vo[:len(vo)+L])
        elif L>0: a=(pl[:len(pl)-L],po[:len(po)-L]); b=(vl[L:],vo[L:])
        else: a,b=(pl,po),(vl,vo)
        if len(a[0])<500: continue
        m=float(np.median(hav(a[0],a[1],b[0],b[1])))
        if m<best[1]: best=(float(Ls),m)
    return best

T=pd.read_csv("data/sessions_verdict.csv")
cases=[("S1",0,"control: verified"),("S3c",0,"control: verified"),
       ("Y1",3,"DEAD"),("S4",1,"DEAD"),
       ("Vw4",0,"noisy"),("Vw2",0,"noisy"),("Vta29",0,"noisy"),("Vfa02",0,"unverifiable")]
print(f"{'session':<12}{'status':<20}{'sep @ lag0':>12}{'best lag':>11}{'sep @ best':>12}")
print("-"*70)
for drive,sess,tag in cases:
    f=Path("data/clean")/f"{drive}.parquet"
    if not f.exists(): continue
    d=pd.read_parquet(f); d=d[d.session==sess]
    r=track_align(d)
    if r is None: print(f"{drive+'/s'+str(sess):<12}{tag:<20}{'no GPS pair':>12}"); continue
    lag,sep=r
    ok=np.isfinite(d.phone_lat)&np.isfinite(d.lat)&(d.phone_lat.abs()>1)&(d.lat.abs()>1)
    sep0=float(np.median(hav(d.phone_lat[ok].to_numpy(),d.phone_lon[ok].to_numpy(),
                             d.lat[ok].to_numpy(),d.lon[ok].to_numpy())))
    print(f"{drive+'/s'+str(sess):<12}{tag:<20}{sep0:>10.0f} m{lag:>+10.0f}s{sep:>10.0f} m")
