"""The problem statement gives TWO benchmarks, both 10% of distance:
     5 m over  50 m   -> at 60 km/h that is a 3-second blackout
   100 m over 1000 m  -> at 60 km/h that is a 60-second blackout
Drift grows with blackout length, so these are not equally hard. Where is the 10% line?"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0; DT=1/FS
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
DURS=[3,5,10,20,30,45,60,90]
rng=np.random.default_rng(0)
res={d:[] for d in DURS}; resd={d:[] for d in DURS}
for drv in ("B","D"):
    for _,r in sel[sel.driver==drv].iterrows():
        d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
        d=d[(d.session==r.session)&d.aligned_valid].reset_index(drop=True)
        v=d.speed_best_al.to_numpy()/3.6; v=v[np.isfinite(v)]
        if len(v)<2000: continue
        for dur in DURS:
            NW=int(dur*FS)
            starts=[s for s in range(0,len(v)-NW,20) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
            if not starts: continue
            for s in rng.choice(starts,size=min(500,len(starts)),replace=False):
                dt=float(np.sum(v[s:s+NW])*DT)
                if dt<10: continue
                de=v[s]*dur                        # coast
                res[dur].append(abs(de-dt)/dt*100)
                resd[dur].append(abs(de-dt))
print("COAST (hold the GNSS velocity) vs BLACKOUT DURATION")
print(f"  {'duration':>9}{'distance':>11}{'drift %':>10}{'drift m':>10}{'p90 %':>8}{'pass 10%':>10}")
for dur in DURS:
    if not res[dur]: continue
    x=np.array(res[dur]); m=np.array(resd[dur])
    dist=np.median([d for d in m/np.maximum(x,1e-9)*100])
    print(f"  {dur:>7} s{dist:>10.0f} m{np.median(x):>9.1f}%{np.median(m):>9.1f} m"
          f"{np.percentile(x,90):>7.1f}%{'  YES' if np.median(x)<10 else '   no':>10}")
print(f"\n  n per row: {len(res[60]):,} at 60 s")
print("\nPS benchmarks:")
print("   5 m over   50 m   -> ~3 s at 60 km/h")
print(" 100 m over 1000 m   -> ~60 s at 60 km/h")
