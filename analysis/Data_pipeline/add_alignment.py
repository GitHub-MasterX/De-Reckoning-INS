"""Add alignment as NEW columns. Nothing existing is touched or shifted.

  veh_idx        for phone row i, which vehicle row it actually corresponds to
  aligned_valid  False where that row would fall outside the session
  speed_best_al  the label, pre-aligned (convenience; veh_idx does the general case)
  lag_applied_s  the offset used, for reference

Any vehicle column can be aligned on demand:
    lab = d.speed_best.to_numpy()[d.veh_idx.to_numpy()]
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0
A=pd.read_csv("/home/masterx/sih/data/test_outputs/alignment.csv")
lag={(r.drive,int(r.session)): (r.total_lag if np.isfinite(r.total_lag) else 0.0) for _,r in A.iterrows()}

tot_valid=tot_rows=0; rows=[]
for f in sorted(CLEAN.glob("*.parquet")):
    d=pd.read_parquet(f); drive=f.stem; n=len(d)
    sid=d.session.to_numpy()
    veh=np.full(n,-1,dtype=np.int32); ok=np.zeros(n,bool); lag_col=np.zeros(n)
    for s in np.unique(sid):
        m=np.flatnonzero(sid==s); s0,s1=m[0],m[-1]+1
        L=int(round(lag.get((drive,int(s)),0.0)*FS))
        tgt=m+L
        inside=(tgt>=s0)&(tgt<s1)                 # must stay inside the SAME session
        veh[m[inside]]=tgt[inside]; ok[m[inside]]=True
        lag_col[m]=L/FS
    d["veh_idx"]=veh
    d["aligned_valid"]=ok
    d["lag_applied_s"]=lag_col
    sb=d.speed_best.to_numpy()
    al=np.full(n,np.nan); al[ok]=sb[veh[ok]]
    d["speed_best_al"]=al
    d.to_parquet(f,index=False)
    tot_valid+=int(ok.sum()); tot_rows+=n
    rows.append(dict(drive=drive,n=n,valid=int(ok.sum()),
                     pct=round(100*ok.mean(),1),
                     max_lag=round(float(np.abs(lag_col).max()),1)))
R=pd.DataFrame(rows)
print(f"{tot_valid:,} of {tot_rows:,} rows aligned ({100*tot_valid/tot_rows:.1f}%)")
print(f"rows lost to shifting past a session edge: {tot_rows-tot_valid:,}\n")
print("largest shifts applied:")
print(R.nlargest(8,"max_lag")[["drive","n","valid","pct","max_lag"]].to_string(index=False))
print("\nworst coverage after shifting:")
print(R.nsmallest(6,"pct")[["drive","n","valid","pct","max_lag"]].to_string(index=False))
d=pd.read_parquet(CLEAN/"S1.parquet")
print(f"\ncolumns now: {len(d.columns)}  (added veh_idx, aligned_valid, lag_applied_s, speed_best_al)")
print("original columns untouched - spot check S1 speed_best:",
      f"mean {d.speed_best.mean():.4f}, n={d.speed_best.notna().sum()}")
