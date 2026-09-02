"""Does 10 Hz phone IMU carry any usable speed information in its spectrum?
Test on a long drive with wide speed variation."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import signal

S = pd.read_csv("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset/M (Driver B)/S-M.csv",
                encoding="latin-1", low_memory=False)
V = pd.read_csv("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset/M (Driver B)/V-M.csv",
                encoding="latin-1", low_memory=False)
S.columns=[c.strip() for c in S.columns]; V.columns=[c.strip() for c in V.columns]
n = min(len(S), len(V)); S, V = S.iloc[:n], V.iloc[:n]

az = pd.to_numeric(S[[c for c in S.columns if c.startswith("ACCELEROMETER Z")][0]], errors="coerce").to_numpy()
ax = pd.to_numeric(S[[c for c in S.columns if c.startswith("ACCELEROMETER X")][0]], errors="coerce").to_numpy()
ay = pd.to_numeric(S[[c for c in S.columns if c.startswith("ACCELEROMETER Y")][0]], errors="coerce").to_numpy()
gz = pd.to_numeric(S["GYROSCOPE Yaw (rad/s)"], errors="coerce").to_numpy()
spd = pd.to_numeric(V["Indicated Vehicle Speed (km/hr)"], errors="coerce").to_numpy()

ok = np.isfinite(az)&np.isfinite(ax)&np.isfinite(ay)&np.isfinite(spd)&np.isfinite(gz)
az,ax,ay,gz,spd = az[ok],ax[ok],ay[ok],gz[ok],spd[ok]
fs = 10.0
print(f"{len(spd)} samples @ {fs} Hz = {len(spd)/fs/60:.0f} min | speed {spd.min():.0f}-{spd.max():.0f} km/h\n")

# --- 1. Spectrogram vs speed: is there a spectral line that tracks speed? ---
nper = 128  # 12.8 s window
f, t, Sxx = signal.spectrogram(az - az.mean(), fs=fs, nperseg=nper, noverlap=nper//2)
# mean speed in each spectrogram window
idx = (t*fs).astype(int)
spd_w = np.array([spd[max(0,i-nper//2):i+nper//2].mean() for i in idx])
moving = spd_w > 5
print("=== Correlation of each frequency bin's power with vehicle speed ===")
print(f"{'freq (Hz)':>10} {'corr with speed':>16}")
for i, fi in enumerate(f):
    c = np.corrcoef(np.log(Sxx[i, moving]+1e-12), spd_w[moving])[0,1]
    print(f"{fi:>10.2f} {c:>16.3f}")

# --- 2. Peak-frequency tracking: does the dominant frequency move with speed? ---
peak_f = f[1:][np.argmax(Sxx[1:], axis=0)]
c_peak = np.corrcoef(peak_f[moving], spd_w[moving])[0,1]
print(f"\nDominant-frequency vs speed correlation: {c_peak:+.3f}   <-- the 'read speed off the FFT peak' idea")

# --- 3. What DOES correlate at 10 Hz? ---
def rms(v, w=20):
    return pd.Series(v).rolling(w, center=True).std().to_numpy()
feats = {
  "accel-Z RMS (vibration energy)": rms(az),
  "accel-X RMS":                    rms(ax),
  "accel-Y RMS":                    rms(ay),
  "|accel| RMS (3-axis)":           rms(np.sqrt(ax**2+ay**2+az**2)),
  "gyro-yaw |rate|":                np.abs(gz),
  "gyro-yaw RMS":                   rms(gz),
}
print("\n=== Simple 10 Hz features vs speed (moving only) ===")
m = spd > 5
for k, v in feats.items():
    good = m & np.isfinite(v)
    print(f"  {k:34s} corr = {np.corrcoef(v[good], spd[good])[0,1]:+.3f}")

# --- 4. The turn trick: v = a_lat / omega ---
lat_acc = ay  # dominant lateral axis TBD; check both
for name, a_l in (("accel-X as lateral", ax), ("accel-Y as lateral", ay)):
    turning = (np.abs(gz) > 0.08) & (spd > 15)
    v_est = np.abs(a_l[turning]) / np.abs(gz[turning]) * 3.6   # m/s -> km/h
    v_tru = spd[turning]
    keep = np.isfinite(v_est) & (v_est < 200)
    err = v_est[keep] - v_tru[keep]
    print(f"\n=== v = a_lat/omega using {name} ({turning.sum()} turning samples, {100*turning.mean():.1f}% of drive) ===")
    print(f"    corr={np.corrcoef(v_est[keep], v_tru[keep])[0,1]:+.3f}  median_err={np.median(err):+.1f} km/h  MAE={np.abs(err).mean():.1f} km/h")
