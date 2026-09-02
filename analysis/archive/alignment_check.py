"""Which phone axis is which? Test alignment against CAN ground truth."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path

def load(stem):
    base = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset")
    sp = next(base.rglob(f"S-{stem}.csv")); vp = next(base.rglob(f"V-{stem}.csv"))
    S = pd.read_csv(sp, encoding="latin-1", low_memory=False)
    V = pd.read_csv(vp, encoding="latin-1", low_memory=False)
    S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
    n=min(len(S),len(V)); return S.iloc[:n].reset_index(drop=True), V.iloc[:n].reset_index(drop=True)

def num(df,c): return pd.to_numeric(df[c], errors="coerce").to_numpy()
def col(df,p): return [c for c in df.columns if c.startswith(p)][0]

for stem in ["M", "S1", "Vw1"]:
    try: S,V = load(stem)
    except StopIteration: continue
    A = np.c_[num(S,col(S,"ACCELEROMETER X")), num(S,col(S,"ACCELEROMETER Y")), num(S,col(S,"ACCELEROMETER Z"))]
    G = np.c_[num(S,col(S,"GRAVITY X")), num(S,col(S,"GRAVITY Y")), num(S,col(S,"GRAVITY Z"))]
    W = np.c_[num(S,"GYROSCOPE Yaw (rad/s)"), num(S,"GYROSCOPE Pitch (rad/s)"), num(S,"GYROSCOPE Roll (rad/s)")]
    yaw_can = num(V,"Yaw Rate (deg/sec)")*np.pi/180          # rad/s
    lon_can = num(V,"Indicated Longitudinal Acceleration (g)")*9.81
    lat_can = num(V,"Indicated Lateral Acceleration (g)")*9.81
    spd     = num(V,"Indicated Vehicle Speed (km/hr)")

    ok = np.isfinite(A).all(1)&np.isfinite(G).all(1)&np.isfinite(W).all(1)&np.isfinite(yaw_can)&np.isfinite(spd)
    A,G,W,yaw_can,lon_can,lat_can,spd = A[ok],G[ok],W[ok],yaw_can[ok],lon_can[ok],lat_can[ok],spd[ok]
    if len(spd)<1000: continue

    print(f"\n{'='*72}\n{stem}:  {len(spd)} samples ({len(spd)/600:.0f} min), speed {spd.min():.0f}-{spd.max():.0f} km/h")
    print(f"  |ACCELEROMETER| mean = {np.linalg.norm(A,axis=1).mean():.2f} m/s2   "
          f"|GRAVITY| mean = {np.linalg.norm(G,axis=1).mean():.2f}   -> accel {'INCLUDES' if np.linalg.norm(A,axis=1).mean()>5 else 'EXCLUDES'} gravity")
    print(f"  mean gravity vector (phone frame): [{G[:,0].mean():+.2f} {G[:,1].mean():+.2f} {G[:,2].mean():+.2f}]  "
          f"-> phone 'down' axis = {'XYZ'[np.argmax(np.abs(G.mean(0)))]}")

    print("  gyro axis vs CAN yaw-rate correlation:")
    for i,nm in enumerate(["GYRO 'Yaw'  (phone X)","GYRO 'Pitch'(phone Y)","GYRO 'Roll' (phone Z)"]):
        print(f"     {nm}: {np.corrcoef(W[:,i], yaw_can)[0,1]:+.3f}")
    best = np.argmax(np.abs([np.corrcoef(W[:,i],yaw_can)[0,1] for i in range(3)]))
    print(f"     -> vehicle YAW maps to gyro column {best} ('{['Yaw','Pitch','Roll'][best]}')")

    L = A - G   # linear acceleration, gravity removed
    print("  linear-accel axis vs CAN longitudinal / lateral:")
    for i,nm in enumerate("XYZ"):
        print(f"     lin-{nm}:  lon {np.corrcoef(L[:,i],lon_can)[0,1]:+.3f}   lat {np.corrcoef(L[:,i],lat_can)[0,1]:+.3f}")
    fwd = np.argmax(np.abs([np.corrcoef(L[:,i],lon_can)[0,1] for i in range(3)]))
    lft = np.argmax(np.abs([np.corrcoef(L[:,i],lat_can)[0,1] for i in range(3)]))
    print(f"     -> forward = lin-{'XYZ'[fwd]}, lateral = lin-{'XYZ'[lft]}")

    # v = a_lat / omega, now with gravity removed + correct axes + sign
    s_l = np.sign(np.corrcoef(L[:,lft],lat_can)[0,1]); s_w = np.sign(np.corrcoef(W[:,best],yaw_can)[0,1])
    a_lat = s_l*L[:,lft]; om = s_w*W[:,best]
    turning = (np.abs(om)>0.15)&(spd>20)
    v_est = np.abs(a_lat[turning]/om[turning])*3.6
    v_tru = spd[turning]; keep = np.isfinite(v_est)&(v_est<200)
    print(f"  v = a_lat/omega  [aligned, gravity removed]  n={turning.sum()} ({100*turning.mean():.1f}% of drive)")
    print(f"     corr={np.corrcoef(v_est[keep],v_tru[keep])[0,1]:+.3f}  MAE={np.abs(v_est[keep]-v_tru[keep]).mean():.1f} km/h")
    # CAN-only sanity: does the trick work at all with perfect sensors?
    t2 = (np.abs(yaw_can)>0.15)&(spd>20)
    ve = np.abs(lat_can[t2]/yaw_can[t2])*3.6; vt = spd[t2]; k2=np.isfinite(ve)&(ve<200)
    print(f"     SANITY using CAN lat-accel + CAN yaw-rate: corr={np.corrcoef(ve[k2],vt[k2])[0,1]:+.3f}  MAE={np.abs(ve[k2]-vt[k2]).mean():.1f} km/h")
