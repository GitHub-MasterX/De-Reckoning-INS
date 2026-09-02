import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets")

def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()
def col(df,p):
    m=[c for c in df.columns if c.startswith(p)]; return m[0] if m else None

# ---- 1. Is GRAVITY really phone-frame, or a world-frame virtual sensor? ----
sp = ROOT/"Categorised IOVNB Dataset/M (Driver B)/S-M.csv"
S = pd.read_csv(sp, encoding="latin-1", low_memory=False); S.columns=[c.strip() for c in S.columns]
G = np.c_[num(S,col(S,"GRAVITY X")),num(S,col(S,"GRAVITY Y")),num(S,col(S,"GRAVITY Z"))]
A = np.c_[num(S,col(S,"ACCELEROMETER X")),num(S,col(S,"ACCELEROMETER Y")),num(S,col(S,"ACCELEROMETER Z"))]
print("=== GRAVITY column, per-axis mean / std / min / max ===")
for i,n in enumerate("XYZ"):
    g=G[:,i][np.isfinite(G[:,i])]
    print(f"  GRAVITY {n}: mean={g.mean():+.4f} std={g.std():.4f} min={g.min():+.3f} max={g.max():+.3f}")
print(f"  unique GRAVITY Z values: {len(np.unique(G[:,2][np.isfinite(G[:,2])]))}")
print("=== ACCELEROMETER, per-axis mean / std ===")
for i,n in enumerate("XYZ"):
    a=A[:,i][np.isfinite(A[:,i])]
    print(f"  ACCEL {n}: mean={a.mean():+.4f} std={a.std():.4f}")

# ---- 2. Label quality across all 144 pairs ----
def find_v(sp):
    want = sp.name.replace("S-","V-",1).lower()
    for d in (sp.parent, sp.parent.parent/"V-Dataset"):
        if d.is_dir():
            for c in d.iterdir():
                if c.name.lower()==want: return c
rows=[]
for spf in sorted(ROOT.rglob("S-*.csv")):
    vpf=find_v(spf)
    if vpf is None: continue
    try: V=pd.read_csv(vpf,encoding="latin-1",low_memory=False)
    except Exception: continue
    V.columns=[c.strip() for c in V.columns]
    can=num(V,"Indicated Vehicle Speed (km/hr)"); vbox=num(V,"Velocity (km/hr)")
    ok=np.isfinite(can)&np.isfinite(vbox)
    rows.append(dict(name=spf.stem, n=len(V),
        can_valid=100*np.isfinite(can).mean(), vbox_valid=100*np.isfinite(vbox).mean(),
        can_allzero=bool(np.nanmax(can)==0) if np.isfinite(can).any() else True,
        can_max=np.nanmax(can) if np.isfinite(can).any() else np.nan,
        vbox_max=np.nanmax(vbox) if np.isfinite(vbox).any() else np.nan,
        bias=np.nanmean(can[ok]-vbox[ok]) if ok.sum()>100 else np.nan,
        corr=np.corrcoef(can[ok],vbox[ok])[0,1] if ok.sum()>100 else np.nan))
Q=pd.DataFrame(rows); Q.to_csv("/home/masterx/sih/out/quality.csv",index=False)
print(f"\n=== LABEL QUALITY over {len(Q)} pairs ===")
print(f"  files where CAN speed is all-zero / unusable : {Q.can_allzero.sum()}")
print(f"  files where CAN speed valid <90% of rows     : {(Q.can_valid<90).sum()}")
print(f"  files where VBOX velocity valid <90% of rows : {(Q.vbox_valid<90).sum()}")
print(f"  median CAN-vs-VBOX correlation               : {Q["corr"].median():.4f}")
print(f"  median CAN-minus-VBOX bias                   : {Q["bias"].median():+.2f} km/h")
print(f"\n  usable pairs (CAN ok, VBOX ok, moving): {((~Q.can_allzero)&(Q.can_valid>90)&(Q.vbox_valid>90)&(Q.can_max>5)).sum()} / {len(Q)}")
print("\n  worst offenders:")
print(Q[Q.can_allzero|(Q.can_valid<90)][["name","n","can_valid","vbox_valid","can_max","vbox_max"]].head(12).to_string(index=False))
