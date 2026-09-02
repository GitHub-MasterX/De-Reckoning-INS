"""Survey the IO-VNBD synchronised pairs: real sample rates, GPS behaviour, speed coverage."""
import warnings, sys
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

ROOT = Path("/home/masterx/sih/IO-VNBD/Synchronised V abd S datasets")

def clean(df):
    df.columns = [c.strip().replace("\xb2","2").replace("\xb0","deg") for c in df.columns]
    return df

def modal_run(a):
    """Modal run-length of repeated identical values."""
    a = np.asarray(a)
    if len(a) < 2: return len(a)
    chg = np.flatnonzero(np.diff(a) != 0)
    runs = np.diff(np.concatenate(([-1], chg, [len(a)-1])))
    if len(runs) == 0: return len(a)
    v, c = np.unique(runs, return_counts=True)
    return int(v[c.argmax()])

rows = []
def find_v(sp):
    """V- sibling: same dir (Categorised), or ../V-Dataset/ (Uncategorised)."""
    want = sp.name.replace("S-", "V-", 1).lower()
    for d in (sp.parent, sp.parent.parent / "V-Dataset"):
        if not d.is_dir(): continue
        for c in d.iterdir():
            if c.name.lower() == want: return c
    return None

errors = []
pairs = sorted(ROOT.rglob("S-*.csv"))
for sp in pairs:
    vp = find_v(sp)
    if vp is None:
        errors.append((sp.name, "no V- pair")); continue
    try:
        S = clean(pd.read_csv(sp, low_memory=False, encoding="latin-1"))
        V = clean(pd.read_csv(vp, low_memory=False, encoding="latin-1"))
    except Exception as e:
        errors.append((sp.name, str(e)[:60])); continue

    t = pd.to_numeric(S["TIME SINCE START (ms)"], errors="coerce").to_numpy()/1000.0
    dt = np.median(np.diff(t)) if len(t) > 1 else np.nan
    vt = pd.to_numeric(V["Time Since Start of Day (seconds)"], errors="coerce").to_numpy()
    vdt = np.median(np.diff(vt)) if len(vt) > 1 else np.nan

    lat = pd.to_numeric(S["GPS LATITUDE (degrees)"], errors="coerce").to_numpy()
    gps_hold = modal_run(lat)

    vlat = pd.to_numeric(V["Latitude (degrees)"], errors="coerce").to_numpy()
    vgps_hold = modal_run(vlat)

    spd = pd.to_numeric(V["Indicated Vehicle Speed (km/hr)"], errors="coerce").to_numpy()
    spd = spd[np.isfinite(spd)]
    dist_km = np.nansum(spd/3.6*dt)/1000.0 if len(spd) and np.isfinite(dt) else np.nan

    rows.append(dict(
        group=sp.parent.parent.name if sp.parent.parent != ROOT else sp.parent.name,
        name=sp.stem, n_S=len(S), n_V=len(V), aligned=(len(S)==len(V)),
        S_dt=round(dt,4), V_dt=round(vdt,4),
        S_hz=round(1/dt,2) if dt else np.nan, V_hz=round(1/vdt,2) if vdt else np.nan,
        phoneGPS_hold=gps_hold, phoneGPS_s=round(gps_hold*dt,1),
        vboxGPS_hold=vgps_hold, vboxGPS_s=round(vgps_hold*vdt,1),
        dur_min=round(len(S)*dt/60,1), dist_km=round(dist_km,2),
        v_max=round(np.nanmax(spd),1) if len(spd) else np.nan,
        v_mean=round(np.nanmean(spd),1) if len(spd) else np.nan,
        pct_moving=round(100*np.mean(spd>1),1) if len(spd) else np.nan,
    ))

df = pd.DataFrame(rows)
df.to_csv("/home/masterx/sih/out/survey.csv", index=False)
pd.set_option("display.width", 220, "display.max_columns", 40)

print(f"=== {len(df)} synchronised pairs parsed; {len(errors)} skipped ===")
for n, e in errors[:10]: print(f"    SKIP {n}: {e}")
print()
print("SAMPLE RATES (measured from timestamps):")
print(f"  phone dt: {df.S_dt.value_counts().head(3).to_dict()}   ->  {df.S_hz.median():.2f} Hz median")
print(f"  vbox  dt: {df.V_dt.value_counts().head(3).to_dict()}   ->  {df.V_hz.median():.2f} Hz median")
print(f"  row-aligned S/V pairs: {df.aligned.sum()}/{len(df)}")
print()
print("PHONE GPS update interval (seconds between distinct fixes):")
print(df.phoneGPS_s.value_counts().head(8).to_string())
print()
print("VBOX GPS update interval (seconds between distinct fixes):")
print(df.vboxGPS_s.value_counts().head(8).to_string())
print()
print("COVERAGE BY GROUP:")
g = df.groupby("group").agg(seqs=("name","count"), hours=("dur_min", lambda x: round(x.sum()/60,2)),
                            km=("dist_km","sum"), vmax=("v_max","max"), vmean=("v_mean","mean"),
                            pct_moving=("pct_moving","mean")).round(1)
print(g.to_string())
print(f"\nTOTAL: {df.dur_min.sum()/60:.1f} h, {df.dist_km.sum():.0f} km, max speed {df.v_max.max():.0f} km/h")
