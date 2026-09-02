"""Not clock drift, not mount movement. IO-VNBD used THREE different phones
(Huawei P20 Pro, Moto G7 Power, BlackBerry Priv). A noisier gyro would explain a
permanently low correlation. Fingerprint each driver's device from its noise floor."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
S=pd.read_csv("data/sessions_verdict.csv"); rows=[]
for _,r in S.iterrows():
    d=pd.read_parquet(Path("data/clean")/f"{r.drive}.parquet"); d=d[d.session==r.session]
    st=d.stationary.to_numpy()
    if st.sum()<300: continue
    g=d[["gx","gy","gz"]].to_numpy()[st]; a=d[["ax","ay","az"]].to_numpy()[st]
    ok=np.isfinite(g).all(1)&np.isfinite(a).all(1); g,a=g[ok],a[ok]
    if len(g)<300: continue
    rows.append(dict(drive=r.drive,driver=r.driver,session=r.session,verdict=r.verdict,
        minutes=r.minutes, n_still=int(len(g)),
        gyro_noise=float(np.median(np.std(g,axis=0))),
        accel_noise=float(np.median(np.std(a,axis=0))),
        gyro_res=float(np.median([np.min(np.diff(np.unique(g[:,i]))) for i in range(3)])),
        accel_res=float(np.median([np.min(np.diff(np.unique(a[:,i]))) for i in range(3)]))))
D=pd.DataFrame(rows)
print("SENSOR NOISE FLOOR AT STANDSTILL, by driver\n")
print(D.groupby("driver").agg(sessions=("drive","count"),
    gyro_noise=("gyro_noise","median"), accel_noise=("accel_noise","median"),
    gyro_res=("gyro_res","median"), accel_res=("accel_res","median")).to_string())
print("\n  gyro_noise/accel_noise = std of readings while parked (lower = better sensor)")
print("  *_res = smallest step between distinct values = the ADC quantisation step\n")
print("Quantisation step is a hardware fingerprint - identical values mean the same chip:")
for drv in sorted(D.driver.unique()):
    sub=D[D.driver==drv]
    print(f"  driver {drv}: gyro_res values seen -> {sorted(set(np.round(sub.gyro_res,7)))[:4]}")
print("\nBy sync verdict:")
print(D.groupby("verdict").agg(sessions=("drive","count"),
    gyro_noise=("gyro_noise","median"), accel_noise=("accel_noise","median")).to_string())
