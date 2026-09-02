"""What do sample gaps actually look like across all 72 drives?
The empirical distribution should tell us where to put the session-break threshold."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
RAW=Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset/S-Dataset")
M=pd.read_csv("/home/masterx/sih/data/manifest.csv")
alldt=[]; per=[]
for _,r in M.iterrows():
    f=RAW/f"S-{r.drive}.csv"
    if not f.exists(): continue
    hdr=pd.read_csv(f,encoding="latin-1",nrows=0); tc=[c for c in hdr.columns if "TIME SINCE START" in c]
    if not tc: continue
    t=pd.to_numeric(pd.read_csv(f,encoding="latin-1",usecols=tc)[tc[0]],errors="coerce").to_numpy()/1000.0
    t=t[np.isfinite(t)]
    if len(t)<10: continue
    dt=np.diff(t); alldt.append(dt)
    pos=dt[dt>0]
    per.append(dict(drive=r.drive, n=len(dt), neg=int((dt<0).sum()),
                    p999=round(float(np.percentile(pos,99.9)),3),
                    mx=round(float(pos.max()),2), over1=int((pos>1).sum()), over5=int((pos>5).sum())))
A=np.concatenate(alldt); P=A[A>0]
print(f"Total inter-sample intervals across all drives: {len(A):,}")
print(f"  negative (time ran backwards): {int((A<0).sum())}  <- session restarts\n")
print("Distribution of POSITIVE gaps (seconds):")
for q in [50,90,99,99.9,99.99,99.999,100]:
    print(f"  {q:>8}th pct : {np.percentile(P,q):.4f}")
print(f"\nCounts above thresholds:")
for th in [0.15,0.2,0.3,0.5,1,2,3,5,10,30,60]:
    n=int((P>th).sum()); print(f"  > {th:>5} s : {n:>7}   ({100*n/len(P):.6f}%)")
print("\nEvery gap above 0.5 s anywhere in the dataset:")
big=np.sort(P[P>0.5])[::-1]
print("  " + ", ".join(f"{g:.2f}s" for g in big[:40]))
print(f"\n  -> {len(big)} gaps exceed 0.5 s in total, across {len(per)} drives")
D=pd.DataFrame(per)
print("\nDrives with any gap over 1 s, or with time running backwards:")
print(D[(D.over1>0)|(D.neg>0)].to_string(index=False))
