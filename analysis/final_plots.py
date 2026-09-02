"""Per-driver figure: drift against blackout distance, with the vehicle's speed profile
on the same axes so the cause of the drift is visible, not just its size."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
CLEAN=Path("/home/masterx/sih/data/clean"); OUT=Path("/home/masterx/sih/out"); FS=10.0
A=pd.read_csv("/home/masterx/sih/data/alignment.csv")
sel=A[(A.sync_r.abs()>=0.40)&A.sync_r.notna()]; sel=sel[sel.drive!="Vtb1"]
T=pd.read_csv(OUT/"per_driver_drift.csv")
COND={"A":"urban / mixed traffic","B":"urban / mixed traffic",
      "D":"dense urban, low speed","E":"steady highway  —  the PS scenario"}
DURS=sorted(T.dur_s.unique()); rng=np.random.default_rng(0)

# speed statistics per driver per blackout length
sp={}
for _,r in sel.iterrows():
    d=pd.read_parquet(CLEAN/f"{r.drive}.parquet")
    d=d[(d.session==r.session)&d.aligned_valid]
    v=d.speed_best_al.to_numpy(); v=v[np.isfinite(v)]
    if len(v)<3000: continue
    for dur in DURS:
        NW=int(dur*FS)
        st=[s for s in range(0,len(v)-NW,50) if v[s]>15 and (v[s:s+NW]>5).all()]
        if not st: continue
        for s in rng.choice(st,size=min(200,len(st)),replace=False):
            seg=v[s:s+NW]
            sp.setdefault((r.driver,dur),[]).append((seg.mean(),abs(seg.mean()-seg[0])))
stats={k:(np.median([a for a,_ in x]),np.median([b for _,b in x])) for k,x in sp.items()}

fig,axes=plt.subplots(2,2,figsize=(14,9.5))
for ax,drv in zip(axes.ravel(),["E","B","A","D"]):
    s=T[T.driver==drv].sort_values("dist_m")
    if not len(s): ax.axis("off"); continue
    x=s.dist_m.to_numpy(); c=s.coast.to_numpy()
    ax.plot(x,c,"o-",color="#1f4e79",lw=2.4,ms=6,label="drift  (coast, no AI)",zorder=4)
    ax.axhline(10,color="#dc2626",ls="--",lw=1.6,label="10% benchmark",zorder=3)
    # where 10% is crossed
    cr=None
    for i in range(len(x)-1):
        if c[i]<10<=c[i+1]:
            f=(10-c[i])/(c[i+1]-c[i]); cr=x[i]+f*(x[i+1]-x[i]); break
    if cr:
        ax.axvline(cr,color="#059669",ls=":",lw=2,zorder=3)
        ax.annotate(f"10% held to\n{cr:.0f} m",xy=(cr,10),xytext=(cr+90,3.5),fontsize=10,
                    weight="bold",color="#059669",
                    arrowprops=dict(arrowstyle="->",color="#059669",lw=1.4))
    ax.set_xlabel("distance travelled during GNSS blackout  (m)",fontsize=10)
    ax.set_ylabel("positional drift  (% of distance)",fontsize=10,color="#1f4e79")
    ax.tick_params(axis="y",labelcolor="#1f4e79")
    ax.set_ylim(0,26); ax.set_xlim(0,2400); ax.grid(alpha=.22)
    # speed on the right axis - the cause of the drift
    ax2=ax.twinx()
    xs=[x[list(s.dur_s).index(d)] for d in DURS if (drv,d) in stats and d in list(s.dur_s)]
    mv=[stats[(drv,d)][0] for d in DURS if (drv,d) in stats and d in list(s.dur_s)]
    sw=[stats[(drv,d)][1] for d in DURS if (drv,d) in stats and d in list(s.dur_s)]
    ax2.plot(xs,mv,"s--",color="#b45309",lw=1.8,ms=5,alpha=.9,label="mean speed")
    ax2.plot(xs,sw,"^--",color="#7c3aed",lw=1.8,ms=5,alpha=.9,label="speed swing from start")
    ax2.set_ylabel("speed  (km/h)",fontsize=10,color="#b45309")
    ax2.tick_params(axis="y",labelcolor="#b45309"); ax2.set_ylim(0,90)
    h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels()
    ax.legend(h1+h2,l1+l2,fontsize=8.5,loc="upper left",framealpha=.93)
    mean_v=stats.get((drv,60),(0,0))[0]
    ax.set_title(f"Driver {drv}   —   {COND[drv]}\n{mean_v:.0f} km/h average during blackouts",
                 fontsize=11.5,weight="bold",pad=9)
fig.suptitle("GNSS-blackout drift vs distance, by driving condition   —   leave-one-driver-out",
             fontsize=14,weight="bold")
fig.tight_layout(rect=[0,0,1,0.965])
fig.savefig(OUT/"plots/drift_by_condition.png",dpi=150)
print("wrote out/plots/drift_by_condition.png\n")
print(f"{'driver':<8}{'condition':<34}{'10% held to':>13}{'@1km drift':>12}")
for drv in ["E","B","A","D"]:
    s=T[T.driver==drv].sort_values("dist_m")
    x=s.dist_m.to_numpy(); c=s.coast.to_numpy(); cr=np.nan
    for i in range(len(x)-1):
        if c[i]<10<=c[i+1]:
            f=(10-c[i])/(c[i+1]-c[i]); cr=x[i]+f*(x[i+1]-x[i]); break
    print(f"{drv:<8}{COND[drv]:<34}{cr:>10.0f} m{np.interp(1000,x,c)*10:>10.1f} m")
