"""
STEP 1 - Alignment engine: rotate every drive from the PHONE's frame into the VEHICLE's.

DATASET QUIRK, handled first: AndroSensor exports gyroscope axes under a different
convention from the accelerometer (gravity sits on accel Z, but vehicle yaw appears on
gyro Y). A real Android app does not have this - TYPE_GYROSCOPE and TYPE_ACCELEROMETER
share the device frame - so this correction is specific to IO-VNBD.

  down    = gravity direction, from the low-passed accelerometer
  yawaxis = gyro direction carrying rotation about the vertical
            (here: calibrated against CAN, because of the quirk above)
  forward = dominant horizontal acceleration while driving straight,
            sign resolved by speed change
  lateral = down x forward

Labels are read through veh_idx so they are lag-corrected.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import signal
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0

def unit(v):
    return v/max(float(np.linalg.norm(v)),1e-12)
def lowpass(X,fc=0.02):
    sos=signal.butter(2,fc,btype="low",fs=FS,output="sos")
    return signal.sosfiltfilt(sos,X,axis=0)

rows=[]
for f in sorted(CLEAN.glob("*.parquet")):
    base=pd.read_parquet(f); drive=f.stem; n=len(base)
    acc_v=np.full((n,3),np.nan); gyr_v=np.full((n,3),np.nan)
    yaw_all=base.yaw_rate.to_numpy(); lon_all=base.lon_acc.to_numpy(); lat_all=base.lat_acc.to_numpy()
    for s in np.unique(base.session.to_numpy()):
        m=np.flatnonzero((base.session.to_numpy()==s)&base.aligned_valid.to_numpy())
        if len(m)<2000: continue
        sub=base.iloc[m]; vi=sub.veh_idx.to_numpy()
        A=sub[["ax","ay","az"]].to_numpy(); G=sub[["gx_c","gy_c","gz_c"]].to_numpy()
        can_yaw=yaw_all[vi]; can_lon=lon_all[vi]; can_lat=lat_all[vi]
        v=sub.speed_best_al.to_numpy()/3.6
        good=np.isfinite(A).all(1)&np.isfinite(G).all(1)&np.isfinite(can_yaw)&np.isfinite(v)
        if good.sum()<2000: continue

        # --- down: gravity is the only sustained acceleration ---
        Ad=lowpass(A); down=unit(Ad[good].mean(0))

        # --- gyro vertical axis (dataset quirk: calibrate against CAN) ---
        M=np.c_[G[good],np.ones(good.sum())]
        c,*_=np.linalg.lstsq(M,can_yaw[good],rcond=None)
        yawaxis=unit(c[:3]); yaw_est=G@yawaxis

        # --- horizontal acceleration ---
        H=A-np.outer(A@down,down)

        # --- forward: dominant horizontal direction while going straight ---
        straight=good&(np.abs(yaw_est)<0.05)
        if straight.sum()<500: continue
        Hs=H[straight]-H[straight].mean(0)
        P=np.eye(3)-np.outer(down,down)
        w,V=np.linalg.eigh(P@(Hs.T@Hs/len(Hs))@P.T)
        fwd=unit(V[:,int(np.argmax(w))]); fwd=unit(fwd-down*(fwd@down))
        dv=np.gradient(np.nan_to_num(v,nan=float(np.nanmean(v))))*FS
        sel=straight&np.isfinite(dv)
        if sel.sum()>500 and np.corrcoef(H[sel]@fwd,dv[sel])[0,1]<0: fwd=-fwd
        lat=unit(np.cross(down,fwd))

        R=np.vstack([fwd,lat,down])
        acc_v[m]=A@R.T
        gyr_v[m]=np.c_[G@np.cross(lat,down), G@np.cross(down,fwd), yaw_est]

        def cc(a,b,mask=good):
            g=mask&np.isfinite(a)&np.isfinite(b)
            return float(np.corrcoef(a[g],b[g])[0,1]) if g.sum()>500 and np.std(b[g])>1e-9 else np.nan
        rows.append(dict(drive=drive,session=int(s),n=int(good.sum()),
            r_yaw_raw=max(abs(cc(G[:,i],can_yaw)) for i in range(3)),
            r_yaw_aligned=abs(cc(yaw_est,can_yaw)),
            r_lon_raw=max(abs(cc(A[:,i],can_lon)) for i in range(3)),
            r_lon_aligned=abs(cc(acc_v[m][:,0],can_lon)),
            r_lat_raw=max(abs(cc(A[:,i],can_lat)) for i in range(3)),
            r_lat_aligned=abs(cc(acc_v[m][:,1],can_lat))))
    for i,cn in enumerate(["acc_fwd","acc_lat","acc_down"]): base[cn]=acc_v[:,i]
    for i,cn in enumerate(["rate_roll","rate_pitch","rate_yaw"]): base[cn]=gyr_v[:,i]
    base.to_parquet(f,index=False)

V=pd.DataFrame(rows); V.to_csv("/home/masterx/sih/data/test_outputs/frame_validation.csv",index=False)
big=V[V.n>6000]
print(f"{len(V)} sessions aligned, {len(big)} over 10 minutes\n")
print("AGREEMENT WITH THE VEHICLE'S OWN SENSORS   (median over sessions >10 min)")
print(f"{'quantity':<24}{'best raw axis':>15}{'aligned':>10}{'gain':>9}")
for lab,a,b in [("yaw rate","r_yaw_raw","r_yaw_aligned"),
                ("forward accel","r_lon_raw","r_lon_aligned"),
                ("lateral accel","r_lat_raw","r_lat_aligned")]:
    ra,rb=big[a].median(),big[b].median()
    print(f"  {lab:<22}{ra:>15.3f}{rb:>10.3f}{rb-ra:>+9.3f}")
print("\nlargest sessions:")
print(big.nlargest(10,"n")[["drive","session","n","r_yaw_aligned","r_lon_aligned","r_lat_aligned"]].round(3).to_string(index=False))
