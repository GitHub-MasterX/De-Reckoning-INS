"""Generate a MULTI-PAGE draw.io file. Five tabs, each readable on its own."""
from xml.sax.saxutils import escape

C = {"raw":("#eeeeee","#666666"), "data":("#dae8fc","#6c8ebf"), "sync":("#e1d5e7","#9673a6"),
     "align":("#d5e8d4","#82b366"), "feat":("#ffe6cc","#d79b00"), "ok":("#d5e8d4","#2d7d32"),
     "fail":("#f8cecc","#b85450"), "run":("#fff2cc","#d6b656"), "app":("#ffe6cc","#d79b00"),
     "res":("#e8f0fe","#4d7fb3"), "note":("#fffbe6","#c9a227"), "hdr":("#37474f","#263238")}

class Page:
    def __init__(self, name):
        self.name, self.cells, self.n = name, [], 0
    def _id(self, p="n"):
        self.n += 1; return f"{self.name[:3]}{p}{self.n}"
    def box(self, x, y, w, h, title, sub="", kind="data", fs=14, dashed=False):
        fill, stroke = C[kind]
        lbl = f"<b>{title}</b>"
        if sub: lbl += f"<br><font style='font-size:11px;color:#444'>{sub}</font>"
        i = self._id()
        st = (f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
              f"fontSize={fs};verticalAlign=middle;align=center;spacingTop=2;strokeWidth=2;"
              + ("dashed=1;" if dashed else ""))
        self.cells.append(f'<mxCell id="{i}" value="{escape(lbl)}" style="{escape(st)}" vertex="1" '
                          f'parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i
    def text(self, x, y, w, h, body, kind="note", fs=13, align="left"):
        fill, stroke = C[kind]
        i = self._id("t")
        st = (f"rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
              f"fontSize={fs};verticalAlign=top;align={align};spacingLeft=12;spacingTop=8;")
        self.cells.append(f'<mxCell id="{i}" value="{escape(body)}" style="{escape(st)}" vertex="1" '
                          f'parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i
    def title(self, x, y, w, txt, sub=""):
        lbl = f"<b>{txt}</b>" + (f"<br><font style='font-size:13px;color:#cfd8dc'>{sub}</font>" if sub else "")
        i = self._id("h")
        st = ("rounded=0;whiteSpace=wrap;html=1;fillColor=#37474f;strokeColor=none;fontColor=#ffffff;"
              "fontSize=19;verticalAlign=middle;align=left;spacingLeft=22;")
        self.cells.append(f'<mxCell id="{i}" value="{escape(lbl)}" style="{escape(st)}" vertex="1" '
                          f'parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="56" as="geometry"/></mxCell>')
    def arrow(self, s, t, lbl="", down=False, dashed=False):
        i = self._id("e")
        ports = ("exitX=0.5;exitY=1;entryX=0.5;entryY=0;" if down
                 else "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
        st = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#546e7a;strokeWidth=2.5;"
              "endArrow=blockThin;endFill=1;fontSize=11;labelBackgroundColor=#ffffff;"
              + ports + ("dashed=1;" if dashed else ""))
        self.cells.append(f'<mxCell id="{i}" value="{escape(lbl)}" style="{escape(st)}" edge="1" '
                          f'parent="1" source="{s}" target="{t}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    def xml(self):
        return (f'  <diagram name="{escape(self.name)}" id="{self.name.replace(" ","_")}">\n'
                '    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" '
                'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" '
                'pageHeight="1000" math="0" shadow="0">\n      <root>\n'
                '        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n        '
                + "\n        ".join(self.cells) + '\n      </root>\n    </mxGraphModel>\n  </diagram>')

pages = []
W, H, GAP = 230, 96, 76
def col(k, x0=70): return x0 + k*(W+GAP)

# ══════════════════ PAGE 1 — OVERVIEW ══════════════════
p = Page("1 · Overview"); pages.append(p)
p.title(60, 40, 1480, "Intelligent Dead Reckoning — system overview",
        "GNSS-denied navigation from a dashboard-mounted smartphone · SIH PS 26168")
y = 170
a = p.box(col(0), y, W, H, "IO-VNBD", "72 drives · 1,341 km", "raw")
b = p.box(col(1), y, W, H, "Clean &amp; align", "sync, sessions, frame", "data")
c = p.box(col(2), y, W, H, "Features", "26 per 2 s window", "feat")
d = p.box(col(3), y, W, H, "Train", "leave-one-driver-out", "feat")
e = p.box(col(4), y, W, H, "Models", "classifier + regressor", "ok")
for s, t in zip([a,b,c,d],[b,c,d,e]): p.arrow(s, t)
y2 = 360
f = p.box(col(0), y2, W, H, "Phone sensors", "IMU + GNSS", "run")
g = p.box(col(1), y2, W, H, "Engine", "normalise · align · fuse", "run")
h = p.box(col(2), y2, W, H, "Map layer", "OSM · NHC", "run")
i2 = p.box(col(3), y2, W, H, "Position", "10 Hz", "run")
j = p.box(col(4), y2, W, H, "App", "Kotlin · Compose", "app")
for s, t in zip([f,g,h,i2],[g,h,i2,j]): p.arrow(s, t)
p.arrow(e, g, "trained model", down=True)
p.text(70, 520, 700, 250,
    "WHAT SHIPS\n\n"
    "✓  Motion classifier — 99.4% leave-one-driver-out\n"
    "✓  Alignment engine — 97–100% of theoretical optimum\n"
    "✓  Kalman fusion, map matching, NHC\n\n"
    "✗  Speed regressor — measured, degrades drift, NOT deployed", "ok")
p.text(810, 520, 740, 250,
    "BENCHMARKS\n\n"
    "5 m over 50 m        1.3 – 2.6 m      PASS on all 4 drivers\n"
    "100 m over 1 km      102 m            driver E, misses by 1.8 m\n"
    "                     161 – 196 m      urban drivers\n\n"
    "Driver E is the problem statement's stated condition:\n"
    "steady ~60 km/h, tunnel-like.", "res")

# ══════════════════ PAGE 2 — DATA PIPELINE ══════════════════
p = Page("2 · Data pipeline"); pages.append(p)
p.title(60, 40, 1480, "Data pipeline", "raw CSV → analysis-ready · analysis/*.py, run in order")
y = 170
n1 = p.box(col(0), y, W, H, "1 · Ingest", "latin-1 · pairing · truncation", "data")
n2 = p.box(col(1), y, W, H, "2 · Enrich", "speed_best · gyro bias", "data")
n3 = p.box(col(2), y, W, H, "3 · Sessions", "83 across 72 drives", "sync")
n4 = p.box(col(3), y, W, H, "4 · Sync", "two-stage alignment", "sync")
n5 = p.box(col(4), y, W, H, "5 · Vehicle frame", "phone → car axes", "align")
for s, t in zip([n1,n2,n3,n4],[n2,n3,n4,n5]): p.arrow(s, t)
p.text(70, 340, 460, 210,
    "THE FOUR INGEST TRAPS\n\n"
    "•  latin-1 encoding — all 72 files\n"
    "•  case-mismatched filenames — 40 of 72\n"
    "•  two column-naming schemes\n"
    "•  unequal row counts — 9 pairs", "note")
p.text(570, 340, 460, 210,
    "SESSION SPLIT\n\n"
    "One file can hold several recordings.\n"
    "Only 3 gaps of 1,070,673 exceed 150 ms.\n"
    "Nothing falls in 0.12–1.28 s, so the\n"
    "0.5 s threshold is read off the data.", "note")
p.text(1070, 340, 470, 210,
    "TWO-STAGE SYNC\n\n"
    "COARSE  GPS tracks, ±10 min\n"
    "        finds +111 s, +309 s offsets\n"
    "FINE    gyro vs yaw-rate, ±30 s\n"
    "        refines to sub-second\n\n"
    "Recovered 6 h, including the test set.", "note")
p.text(70, 590, 1470, 130,
    "OUTPUT   ·   data/clean/*.parquet — 72 drives, 29.7 h, 1,341 km, 1,070,741 samples at 10 Hz, 49 columns\n"
    "             every original column preserved byte-identical; all corrections added as NEW columns", "res")

# ══════════════════ PAGE 3 — MODEL TRAINING ══════════════════
p = Page("3 · Model training"); pages.append(p)
p.title(60, 40, 1480, "Model training", "offline · scikit-learn · leave-one-driver-out")
y = 170
m1 = p.box(col(0), y, W, H, "26 features", "2.0 s window, 0.5 s hop", "feat")
m2 = p.box(col(1), y, W, H, "Split", "hold out a whole driver", "feat")
m3 = p.box(col(2), y, W, H+40, "Motion classifier", "stationary vs moving<br>IMU only", "ok")
m4 = p.box(col(3), y, W, H+40, "✓ 99.4%", "naive threshold 90.3%<br>DEPLOYED", "ok")
p.arrow(m1, m2); p.arrow(m2, m3); p.arrow(m3, m4)
y3 = 330
m5 = p.box(col(2), y3, W, H+40, "Speed regressor", "predicts Δv<br>r = 0.43–0.61", "fail", dashed=True)
m6 = p.box(col(3), y3, W, H+40, "✗ worse than coast", "drift 43% vs 10%<br>NOT DEPLOYED", "fail", dashed=True)
p.arrow(m2, m5); p.arrow(m5, m6)
p.text(70, 490, 720, 240,
    "WHY THE REGRESSOR FAILS\n\n"
    "Its errors LEAN rather than scatter.\n"
    "A blackout stacks ~2,000 predictions, so a\n"
    "0.05 m/s bias compounds into 22 km/h.\n\n"
    "Correlation cannot see this — two models with\n"
    "identical MAE differ 5× in drift.\n"
    "Shrinkage sweep: best weight is ZERO.", "fail")
p.text(830, 490, 710, 240,
    "WHY THE CLASSIFIER WORKS\n\n"
    "A stopped vehicle is a large, sustained,\n"
    "structural signature — not a small quantity\n"
    "buried in noise.\n\n"
    "Held out E entirely (trained urban-only):\n"
    "still 99.6% on 84,291 unseen highway windows.", "ok")

# ══════════════════ PAGE 4 — RUNTIME ENGINE ══════════════════
p = Page("4 · Runtime engine"); pages.append(p)
p.title(60, 40, 1480, "On-device runtime", "portable core · phone, Raspberry Pi, or FOG IMU")
y = 190
r = []
for k, (t, s, kind) in enumerate([
        ("Sensors", "accel · gyro · mag · GNSS", "run"),
        ("Normalise", "any rate → 10 Hz", "run"),
        ("Align", "phone → vehicle frame", "align"),
        ("Classify", "ZUPT · shock reject", "ok"),
        ("Fuse", "Kalman, GNSS+INS", "run")]):
    r.append(p.box(col(k), y, W, H, t, s, kind))
for a_, b_ in zip(r[:-1], r[1:]): p.arrow(a_, b_)
y4 = 380
r2 = []
for k, (t, s, kind) in enumerate([
        ("Map layer", "OSM · HMM · NHC", "run"),
        ("Blackout handler", "seamless switch", "run"),
        ("Position out", "10 Hz phone / 200 Hz edge", "run")]):
    r2.append(p.box(col(k+1), y4, W, H, t, s, kind))
p.arrow(r[4], r2[0], "", down=True)
p.arrow(r2[0], r2[1]); p.arrow(r2[1], r2[2])
p.text(70, 540, 700, 200,
    "SAMPLE-RATE HANDLING\n\n"
    "Phone samples at 248 Hz; the model expects 10 Hz.\n\n"
    "low-pass 4 Hz  →  interpolate on timestamps  →  10 Hz\n\n"
    "Filter BEFORE decimating, or vibration folds\n"
    "into the signal band and cannot be removed.", "note")
p.text(810, 540, 730, 200,
    "WHAT THE CLASSIFIER DOES HERE\n\n"
    "It detects vehicle STATE, not position.\n\n"
    "stationary  →  force velocity to zero (ZUPT)\n"
    "moving      →  coast + Kalman + map\n\n"
    "Prevents 333 m of phantom motion per 30 s stop.", "ok")

# ══════════════════ PAGE 5 — RESULTS ══════════════════
p = Page("5 · Results"); pages.append(p)
p.title(60, 40, 1480, "Results", "leave-one-driver-out · each driver unseen by the model that scored it")
p.text(70, 130, 1470, 250,
    "POSITIONAL DRIFT (%)                50 m     100 m     200 m     500 m    1000 m\n"
    "───────────────────────────────────────────────────────────────────────────────\n"
    "Driver E   steady highway            2.6       4.1       6.7       9.1      10.2\n"
    "Driver B   urban / mixed             3.2       5.2       7.9      11.1      16.1\n"
    "Driver A   urban / mixed             5.2       8.5      11.7      13.4      16.5\n"
    "Driver D   dense urban               5.3       9.6      10.9      18.2      19.6\n"
    "───────────────────────────────────────────────────────────────────────────────\n"
    "benchmark                          under 10% of distance travelled", "res")
p.text(70, 410, 700, 290,
    "WHY ONLY DRIVER E MEETS 1 km\n\n"
    "drift  =  | v₀ − v̄ |  ⁄  v̄\n\n"
    "1 · Every driver's speed wanders by a SIMILAR\n"
    "    absolute amount (5.0–6.9 km/h) — but E\n"
    "    divides it by 79.5 km/h, others by 41–51.\n"
    "    relative swing:  E 6.1%   vs   A/B/D 14–15%\n\n"
    "2 · A distance benchmark is a TIME benchmark.\n"
    "    1 km takes E 62 s, driver D 103 s.\n\n"
    "3 · Stops break velocity-hold. E stops 8.4%\n"
    "    of the time, urban drivers 12–15%.", "note")
p.text(810, 410, 730, 290,
    "PHYSICAL LIMIT AT 10 Hz\n\n"
    "required accuracy   0.028 m/s² on mean accel\n"
    "random noise        0.020 m/s²      ✓ fine\n"
    "bias                does NOT average out\n\n"
    "gravity leak sets the wall:\n"
    "     θ  =  0.028 / 9.81  =  0.16°  of pitch\n\n"
    "ALIASING — signal 0–2 Hz, vibration 10–100 Hz\n"
    "folds into 0–5 Hz. Contaminated, not noisy:\n"
    "no filter can separate them. 248 Hz can.", "fail")

xml = ('<mxfile host="app.diagrams.net" agent="claude" version="24.0.0">\n'
       + "\n".join(pg.xml() for pg in pages) + "\n</mxfile>\n")
open("outputs/plots/IDR_architecture.drawio", "w").write(xml)
print(f"wrote outputs/plots/IDR_architecture.drawio — {len(pages)} pages, {len(xml):,} bytes")
for pg in pages: print(f"    {pg.name:<24} {len(pg.cells):>2} elements")
