"""
STEP 2 - Physics baseline. No machine learning anywhere.

GNSS hands over a velocity at the moment of blackout. From there, integrate the aligned
forward acceleration:
        v(t) = v0 + INTEGRAL a_fwd dt
        d(t) =      INTEGRAL v dt
and measure how far the answer drifts from truth over 60 s.

Variants test how much of the error is a fixed accelerometer bias, a slowly-varying one
(road grade leaking gravity into the forward axis), or a scale error.

Reference points, same blackouts:
    COAST  - hold v0, integrate nothing   (this is what a model must beat: 14.1% / 17.0%)
    ORACLE - integrate the true speed     (proves the evaluator is honest)
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import signal
CLEAN=Path("/home/masterx/sih/data/clean"); FS=10.0; DUR=60.0
NW=int(DUR*FS); DT=1/FS
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")

def highpass(x,fc=0.01):
    sos=signal.butter(2,fc,btype="high",fs=FS,output="sos")
    return signal.sosfiltfilt(sos,x)

def run(drive,sess,rng):
    base=pd.read_parquet(CLEAN/f"{drive}.parquet")
    d=base[(base.session==sess)&base.aligned_valid].reset_index(drop=True)
    if len(d)<NW*3 or "acc_fwd" not in d.columns: return None
    a=d.acc_fwd.to_numpy(); v=d.speed_best_al.to_numpy()/3.6
    still=d.stationary.to_numpy()
    ok=np.isfinite(a)&np.isfinite(v)
    if ok.sum()<NW*3: return None
    a,v,still=a[ok],v[ok],still[ok]

    bias = float(np.mean(a[still])) if still.sum()>200 else float(np.mean(a))
    a_b  = a-bias                                   # fixed bias removed
    a_hp = highpass(a)                              # slow drift removed (grade, dive)
    dv_true=np.gradient(v)*FS
    g=np.isfinite(a_hp)&np.isfinite(dv_true)
    scale=float(np.dot(a_hp[g],dv_true[g])/max(np.dot(a_hp[g],a_hp[g]),1e-9))
    a_hs = a_hp*scale                               # scale calibrated too

    starts=[s for s in range(0,len(v)-NW,10) if v[s]>4.2 and (v[s:s+NW]>1.4).all()]
    if not starts: return None
    res={k:[] for k in ("coast","raw","bias","hp","hp_scale","oracle")}
    for s in rng.choice(starts,size=min(400,len(starts)),replace=False):
        d_true=float(np.sum(v[s:s+NW])*DT)
        if d_true<50: continue
        for key,acc in (("coast",None),("raw",a),("bias",a_b),("hp",a_hp),
                        ("hp_scale",a_hs),("oracle",dv_true)):
            ve=v[s]; de=0.0
            for k in range(NW):
                de+=ve*DT
                if acc is not None: ve+=acc[s+k]*DT
            res[key].append(abs(de-d_true)/d_true*100)
    return {k:np.array(x) for k,x in res.items() if x}, bias, scale

sel=A[(A.sync_r.abs()>=0.7)&A.sync_r.notna()]
rng=np.random.default_rng(0)
LAB={"coast":"COAST  hold v0, no integration","raw":"raw a_fwd integrated",
     "bias":"a_fwd - stationary bias","hp":"a_fwd high-passed (grade removed)",
     "hp_scale":"a_fwd high-passed + scale","oracle":"ORACLE true dv"}
for drv,name in (("B","driver B (M) - headline"),("D","driver D (Y1) - second holdout")):
    ss=sel[sel.driver==drv]
    if not len(ss): continue
    print(f"=== {name} ===")
    agg={k:[] for k in LAB}
    for _,r in ss.iterrows():
        out=run(r.drive,int(r.session),rng)
        if not out: continue
        res,bias,scale=out
        print(f"  {r.drive}/s{int(r.session)}  accel bias {bias:+.4f} m/s2, scale {scale:.3f}")
        for k in LAB:
            if k in res: agg[k].append(res[k])
    print(f"  {'strategy':<38}{'median':>9}{'p90':>9}")
    for k in LAB:
        if agg[k]:
            x=np.concatenate(agg[k])
            print(f"  {LAB[k]:<38}{np.median(x):>8.1f}%{np.percentile(x,90):>8.1f}%")
    print(f"  [benchmark: under 10%]\n")
