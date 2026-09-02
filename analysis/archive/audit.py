"""Data quality audit of the CLEANED dataset. Reports only - changes nothing."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
CLEAN=Path("/home/masterx/sih/data/clean"); RAW=Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset/S-Dataset")
M=pd.read_csv("/home/masterx/sih/data/manifest.csv")
IMU=["ax","ay","az","gx","gy","gz"]; MAG=["mx","my","mz"]

def runs(a):
    a=np.asarray(a); 
    if len(a)<2: return np.array([len(a)])
    chg=np.flatnonzero(np.diff(a)!=0)
    return np.diff(np.concatenate(([-1],chg,[len(a)-1])))

# ============ A. TIMESTAMP INTEGRITY ============
print("="*78); print("A. TIMESTAMP INTEGRITY  (cleaned t_s assumes a perfect 10 Hz - is that true?)")
print("="*78)
bad_t=[]
for _,r in M.iterrows():
    f=RAW/f"S-{r.drive}.csv"
    if not f.exists(): continue
    hdr=pd.read_csv(f,encoding="latin-1",nrows=0); tc=[c for c in hdr.columns if "TIME SINCE START" in c]
    if not tc: continue
    t=pd.to_numeric(pd.read_csv(f,encoding="latin-1",usecols=tc)[tc[0]],errors="coerce").to_numpy()/1000.0
    t=t[np.isfinite(t)]
    if len(t)<10: continue
    span=t[-1]-t[0]; assumed=(r.n-1)/10.0; dt=np.diff(t)
    gaps=int((dt>0.25).sum()); worst=float(dt.max())
    if abs(span-assumed)>2.0 or gaps>0:
        bad_t.append((r.drive,round(span,1),round(assumed,1),round(span-assumed,1),gaps,round(worst,2)))
if bad_t:
    print(f"{'drive':<8}{'real span':>10}{'assumed':>10}{'diff s':>9}{'gaps>0.25s':>12}{'worst gap':>11}")
    for b in sorted(bad_t,key=lambda x:-abs(x[3]))[:20]: print(f"{b[0]:<8}{b[1]:>10}{b[2]:>10}{b[3]:>9}{b[4]:>12}{b[5]:>11}")
    print(f"\n  -> {len(bad_t)}/{len(M)} drives have timing that does NOT match a clean 10 Hz")
else: print("  all drives match a clean 10 Hz - t_s is safe")

# ============ B. STUCK / FROZEN VALUES ============
print("\n"+"="*78); print("B. STUCK VALUES  (sensor repeating the same reading = stale data)")
print("="*78)
stuck=[]
for _,r in M.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    worst_ch,worst_run,tot=None,0,0
    for c in IMU:
        R=runs(d[c].to_numpy()); mx=int(R.max()); tot+=int(R[R>=5].sum())
        if mx>worst_run: worst_run,worst_ch=mx,c
    head=max(int(runs(d[c].to_numpy()[:100])[0]) for c in IMU)
    if worst_run>=10 or head>=10: stuck.append((r.drive,worst_ch,worst_run,round(worst_run/10,1),tot,head))
if stuck:
    print(f"{'drive':<8}{'channel':>8}{'longest run':>13}{'= seconds':>11}{'samples in runs>=5':>20}{'frozen at start':>17}")
    for s in sorted(stuck,key=lambda x:-x[2])[:20]: print(f"{s[0]:<8}{s[1]:>8}{s[2]:>13}{s[3]:>11}{s[4]:>20}{s[5]:>17}")
    print(f"\n  -> {len(stuck)}/{len(M)} drives contain frozen stretches")
else: print("  no significant stuck values")

# ============ C. PHYSICAL SANITY ============
print("\n"+"="*78); print("C. PHYSICAL SANITY")
print("="*78)
rows=[]
for _,r in M.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    amag=np.linalg.norm(d[["ax","ay","az"]].to_numpy(),axis=1)
    still=d.speed_kmh.to_numpy()<0.5
    gbias=[float(np.nanmean(d[c].to_numpy()[still])) if still.sum()>50 else np.nan for c in ["gx","gy","gz"]]
    mmag=np.linalg.norm(d[MAG].to_numpy(),axis=1) if d[MAG].notna().any().any() else np.array([np.nan])
    rows.append(dict(drive=r.drive, a_med=round(float(np.nanmedian(amag)),2), a_max=round(float(np.nanmax(amag)),1),
        a_clip=round(100*float(np.mean(amag>39)),2),
        gbias=round(float(np.nanmax(np.abs(gbias))),4) if still.sum()>50 else np.nan,
        g_max=round(float(np.nanmax(np.abs(d[["gx","gy","gz"]].to_numpy()))),2),
        m_med=round(float(np.nanmedian(mmag)),1), m_nan=round(100*float(d[MAG].isna().all(axis=1).mean()),1)))
C=pd.DataFrame(rows)
print(f"  |accel| median across drives : {C.a_med.median():.2f} m/s2   (expect ~9.81)")
print(f"     drives outside 9.5-10.1   : {((C.a_med<9.5)|(C.a_med>10.1)).sum()}")
print(f"  |accel| max seen             : {C.a_max.max():.1f} m/s2   (LSM6-class parts clip near 39 = 4g)")
print(f"     drives with >0.1% near clip: {(C.a_clip>0.1).sum()}")
print(f"  gyro bias at standstill      : median {C.gbias.median():.4f} rad/s, worst {C.gbias.max():.4f}")
print(f"  |mag| median                 : {C.m_med.median():.1f} uT   (Earth field is 25-65)")
print(f"     drives with NO magnetometer: {(C.m_nan>99).sum()}")
if ((C.a_med<9.5)|(C.a_med>10.1)).any():
    print("\n  drives with odd |accel|:"); print(C[(C.a_med<9.5)|(C.a_med>10.1)][["drive","a_med","a_max"]].to_string(index=False))

# ============ D. GROUND TRUTH INTEGRITY ============
print("\n"+"="*78); print("D. GROUND TRUTH INTEGRITY  (speed / position glitches)")
print("="*78)
gt=[]
for _,r in M.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    v=d.speed_kmh.to_numpy(); dv=np.abs(np.diff(v))
    jump=int((dv>15).sum())                                  # >15 km/h in 0.1 s = impossible
    lat,lon=d.lat.to_numpy(),d.lon.to_numpy()
    step=np.hypot(np.diff(lat),np.diff(lon))*111000
    pjump=int((step>30).sum())                               # >30 m in 0.1 s = 1080 km/h
    frozen=int(runs(lat).max())
    if jump or pjump or frozen>50: gt.append((r.drive,jump,pjump,frozen,round(frozen/10,1)))
if gt:
    print(f"{'drive':<8}{'speed jumps':>13}{'pos jumps':>11}{'longest frozen pos':>20}{'= s':>7}")
    for g in sorted(gt,key=lambda x:-(x[1]+x[2]))[:20]: print(f"{g[0]:<8}{g[1]:>13}{g[2]:>11}{g[3]:>20}{g[4]:>7}")
    print(f"\n  -> {len(gt)}/{len(M)} drives have ground-truth glitches")
else: print("  ground truth is clean")

# ============ E. DEAD COLUMNS ============
print("\n"+"="*78); print("E. DEAD / CONSTANT COLUMNS")
print("="*78)
d0=pd.read_parquet(CLEAN/f"{M.drive.iloc[0]}.parquet"); dead={c:0 for c in d0.columns}
for _,r in M.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    for c in d.columns:
        s=d[c]
        if s.isna().all() or s.nunique(dropna=True)<=1: dead[c]+=1
for c,k in sorted(dead.items(),key=lambda x:-x[1]):
    if k: print(f"  {c:<15} dead or constant in {k}/{len(M)} drives")
if not any(dead.values()): print("  every column carries data in every drive")

# ============ F. DUPLICATE DRIVES ============
print("\n"+"="*78); print("F. DUPLICATE DRIVES")
print("="*78)
sig={}
for _,r in M.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    sig.setdefault(hash(d.ax.to_numpy()[:2000].tobytes()),[]).append(r.drive)
dups=[v for v in sig.values() if len(v)>1]
print(f"  {len(dups)} duplicate group(s): {dups}" if dups else "  all 72 drives are distinct")
