"""Four panels showing why 10 Hz destroys what 100 Hz and 248 Hz preserve."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path
OUT = Path("out/plots"); OUT.mkdir(parents=True, exist_ok=True)

SIG = "#15803d"; ALIAS = "#b91c1c"; VIB = "#b45309"
RATES = [(10, "#b91c1c"), (100, "#2563eb"), (248, "#15803d")]

fig = plt.figure(figsize=(16, 11.5))
gs = fig.add_gridspec(2, 2, hspace=.42, wspace=.22)

# ══════════ A · what each rate can represent ══════════
ax = fig.add_subplot(gs[0, 0])
ax.axvspan(0, 2, color=SIG, alpha=.28, label="vehicle acceleration  0–2 Hz  (what we want)")
ax.axvspan(3, 15, color=VIB, alpha=.20, label="wheel rotation  3–15 Hz  (20–100 km/h)")
ax.axvspan(10, 15, color=VIB, alpha=.32, label="wheel hop  10–15 Hz  [Gillespie]")
ax.axvspan(27, 100, color=VIB, alpha=.14, label="engine firing  27–100 Hz")
for fs, c in RATES:
    ax.axvline(fs/2, color=c, lw=2.6, ls="--")
    ax.text(fs/2, 0.045, f"{fs} Hz\nceiling {fs//2} Hz", color=c, ha="center",
            fontsize=9.5, weight="bold", transform=ax.get_xaxis_transform(),
            bbox=dict(fc="white", ec=c, lw=1.2, alpha=.92, boxstyle="round,pad=0.25"))
ax.set_xscale("log"); ax.set_xlim(0.3, 200); ax.set_ylim(0, 1)
ax.set_xlabel("frequency (Hz)", fontsize=11); ax.set_yticks([])
ax.set_title("A · What each rate can represent", fontsize=13, weight="bold", pad=12)
ax.legend(loc="upper right", fontsize=9, framealpha=.95)
ax.annotate("", xy=(2.6, .5), xytext=(40, .5),
            arrowprops=dict(arrowstyle="->", color=ALIAS, lw=2.6))
ax.text(9, .55, "folds down at 10 Hz", color=ALIAS, ha="center", fontsize=10, weight="bold")

# ══════════ B · true vs apparent frequency ══════════
ax = fig.add_subplot(gs[0, 1])
f = np.linspace(0, 40, 4000)
for fs, c in RATES:
    ax.plot(f, np.abs(f - fs*np.round(f/fs)), color=c, lw=2.4, label=f"sampled at {fs} Hz")
ax.plot(f, f, "k:", lw=1.4, alpha=.6, label="truth (no aliasing)")
ax.axhspan(0, 5, color=SIG, alpha=.10)
for v, kmh in [(2.9, 20), (4.4, 30), (7.3, 50), (8.8, 60), (14.6, 100)]:
    a = abs(v - 10*round(v/10))
    ax.plot([v], [a], "o", color=ALIAS, ms=8, zorder=5)
    ax.annotate(f"{kmh} km/h", (v, a), textcoords="offset points", xytext=(6, 7),
                fontsize=9, color=ALIAS, weight="bold")
ax.set_xlim(0, 40); ax.set_ylim(0, 20)
ax.set_xlabel("true vibration frequency (Hz)", fontsize=11)
ax.set_ylabel("frequency the recording reports (Hz)", fontsize=11)
ax.set_title("B · What the recording claims it saw", fontsize=13, weight="bold", pad=12)
ax.legend(fontsize=9.5, loc="upper left"); ax.grid(alpha=.25)

# ══════════ C · time domain, the same 2 seconds ══════════
ax = fig.add_subplot(gs[1, 0])
T = 2.0
t = np.linspace(0, T, 4000)
accel = 0.8*np.sin(2*np.pi*0.5*t)              # real vehicle acceleration, 0.5 Hz
vib   = 2.0*np.sin(2*np.pi*9.0*t)              # wheel vibration at 60 km/h, 9 Hz
sig   = accel + vib
ax.plot(t, sig, color="#94a3b8", lw=.9, label="what the phone actually feels  (0.5 Hz + 9 Hz)")
ax.plot(t, accel, color=SIG, lw=3, label="the signal we want  (0.5 Hz)")
for fs, c, mk in [(248, "#15803d", "."), (10, "#b91c1c", "o")]:
    ts = np.arange(0, T, 1/fs)
    ax.plot(ts, 0.8*np.sin(2*np.pi*0.5*ts) + 2.0*np.sin(2*np.pi*9.0*ts),
            mk, color=c, ms=4 if fs > 100 else 9, alpha=.85,
            label=f"sampled at {fs} Hz", zorder=4 if fs == 10 else 3)
t10 = np.arange(0, T, 0.1)
ax.plot(t10, 0.8*np.sin(2*np.pi*0.5*t10) + 2.0*np.sin(2*np.pi*1.0*t10),
        "--", color=ALIAS, lw=2.4, label="what 10 Hz reconstructs  (9 Hz → 1 Hz)")
ax.set_xlabel("time (s)", fontsize=11); ax.set_ylabel("acceleration (m/s²)", fontsize=11)
ax.set_title("C · The same two seconds, three ways", fontsize=13, weight="bold", pad=12)
ax.legend(fontsize=8.5, loc="upper right", ncol=1); ax.grid(alpha=.25); ax.set_ylim(-4, 5.2)

# ══════════ D · speed is unrecoverable at 10 Hz ══════════
ax = fig.add_subplot(gs[1, 1])
kmh = np.linspace(5, 110, 700)
f_true = (kmh/3.6)/1.9
ax.plot(kmh, f_true, color=SIG, lw=2.6, label="true wheel frequency")
for fs, c in [(248, "#15803d"), (100, "#2563eb"), (10, "#b91c1c")]:
    ax.plot(kmh, np.abs(f_true - fs*np.round(f_true/fs)), color=c, lw=2.6,
            ls="-" if fs == 10 else ":", label=f"reported at {fs} Hz")
ax.axvline(34, color=ALIAS, ls="--", lw=1.8)
ax.text(36, 8.6, "34 km/h — wheel rotation\ncrosses the 10 Hz ceiling",
        color=ALIAS, fontsize=9.5, weight="bold",
        bbox=dict(fc="white", ec=ALIAS, lw=1.2, alpha=.92, boxstyle="round,pad=0.3"))
for a, b in [(20, 50), (30, 40)]:
    fa = abs((a/3.6)/1.9 - 10*round((a/3.6)/1.9/10))
    fb = abs((b/3.6)/1.9 - 10*round((b/3.6)/1.9/10))
    ax.plot([a, b], [fa, fb], color=ALIAS, lw=1.4, ls=":")
    ax.plot([a, b], [fa, fb], "o", color=ALIAS, ms=8)
ax.text(22, 0.7, "20 and 50 km/h report\nthe SAME frequency", color=ALIAS,
        fontsize=9.5, weight="bold",
        bbox=dict(fc="white", ec=ALIAS, lw=1.2, alpha=.92, boxstyle="round,pad=0.3"))
ax.set_xlabel("vehicle speed (km/h)", fontsize=11)
ax.set_ylabel("wheel frequency reported (Hz)", fontsize=11)
ax.set_title("D · Reading speed off the vibration", fontsize=13, weight="bold", pad=12)
ax.legend(fontsize=9.5, loc="upper left"); ax.grid(alpha=.25); ax.set_ylim(0, 17)

for axx, cap in zip(fig.axes,
    ["everything right of a dashed line folds back on top of the signal",
     "at 10 Hz the line folds — the reported frequency is a lie",
     "at 248 Hz the 9 Hz is visible and removable; at 10 Hz it becomes a fake 1 Hz wave",
     "the curve folds back at 10 Hz, so one reading means two different speeds"]):
    axx.text(0.5, -0.155, cap, transform=axx.transAxes, ha="center", fontsize=10.5,
             style="italic", color="#374151")
fig.suptitle("Why a 10 Hz recording cannot support what 100 Hz and 248 Hz can",
             fontsize=16, weight="bold", y=.98)
fig.savefig(OUT/"05_sampling_rates.png", dpi=150, bbox_inches="tight")
print("wrote out/plots/05_sampling_rates.png")
