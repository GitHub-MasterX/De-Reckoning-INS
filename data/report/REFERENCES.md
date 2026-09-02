# References

Every entry below was checked against the source, not cited from memory. Each carries a note
on **why it is authoritative** — official vendor documentation, a peer-reviewed journal article,
or an indexed conference proceeding.

---

## 1 · Dataset — mandated by the problem statement

**[1]** U. Onyekpe, V. Palade, S. Kanarachos, and A. Szkolnik, "IO-VNBD: Inertial and Odometry
benchmark dataset for ground vehicle positioning," *Data in Brief*, vol. 35, art. no. 106885,
Feb. 2021.
DOI: [10.1016/j.dib.2021.106885](https://doi.org/10.1016/j.dib.2021.106885) · PMID: 33665271 ·
PMCID: PMC7907232
Open access: https://pmc.ncbi.nlm.nih.gov/articles/PMC7907232/

**[2]** IO-VNBD dataset repository — https://github.com/onyekpeu/IO-VNBD
*The repository named directly in the problem statement. Data distributed via Git LFS.*

**[3]** U. Onyekpe *et al.*, "IO-VNBD: Inertial and Odometry Benchmark Dataset for Ground Vehicle
Positioning," arXiv:2005.01701 [cs.RO], May 2020. https://arxiv.org/abs/2005.01701

> **Authority:** *Data in Brief* is a peer-reviewed Elsevier journal, indexed in Scopus and
> PubMed Central. The DOI and PMCID are verifiable identifiers. [2] is the repository the
> problem statement instructs teams to use.

---

## 2 · Android sensor documentation — official vendor source

**[4]** Google, "Motion sensors," *Android Developers*.
https://developer.android.com/develop/sensors-and-location/sensors/sensors_motion

Documents the constants this project uses and their units:

| Constant | Units | Notes |
|---|---|---|
| `TYPE_ACCELEROMETER` | m/s² | includes gravity |
| `TYPE_ACCELEROMETER_UNCALIBRATED` | m/s² | `values[0-2]` raw, `values[3-5]` estimated bias |
| `TYPE_GYROSCOPE` | rad/s | |
| `TYPE_GYROSCOPE_UNCALIBRATED` | rad/s | `values[0-2]` raw, `values[3-5]` estimated drift |

**[5]** Google, "Sensors overview," *Android Developers*.
https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview

Two statements from this page are load-bearing for the design and are quoted verbatim:

> "The delay that you specify is **only a suggested delay**. The Android system and other
> applications can alter this delay."

— which is why the engine resamples from **timestamps** rather than trusting a requested rate.

> "If your app targets Android 12 (API level 31) or higher, the system places a limit on the
> refresh rate of data from certain motion sensors… the sensor sampling rate is **limited to
> 200 Hz**… If your app needs to gather motion sensor data at a higher rate, you must declare
> the **`HIGH_SAMPLING_RATE_SENSORS`** permission… Otherwise… a `SecurityException` occurs."

> ⚠️ **Directly affects this project.** The Samsung M17 5G's LSM6DSV was measured at **248 Hz**.
> On Android 12+ that is capped to 200 Hz unless `HIGH_SAMPLING_RATE_SENSORS` is declared in the
> manifest. The permission must be added, or the high-rate path silently loses a quarter of its
> bandwidth.

> **Authority:** developer.android.com is Google's official platform documentation — the
> normative source for Android sensor behaviour.

---

## 3 · Sampling theory — why 10 Hz cannot represent the vibration

**[6]** C. E. Shannon, "Communication in the Presence of Noise," *Proceedings of the IRE*,
vol. 37, no. 1, pp. 10–21, Jan. 1949. DOI:
[10.1109/JRPROC.1949.232969](https://doi.org/10.1109/JRPROC.1949.232969)
Reprinted: *Proceedings of the IEEE*, vol. 86, no. 2, pp. 447–457, Feb. 1998.

*The Nyquist–Shannon sampling theorem. A signal sampled at f<sub>s</sub> can faithfully represent
content only below f<sub>s</sub>/2; content above that folds back (aliases) into the represented
band and is unrecoverable. At the dataset's 10 Hz this ceiling is **5 Hz**.*

> **Authority:** IEEE, the foundational citation for sampling theory.

---

## 4 · Vehicle vibration frequencies — why road and tyre content exceeds 5 Hz

This is the evidence that the contaminating vibration sits **above** the 5 Hz ceiling and
therefore aliases into the 0–2 Hz band where vehicle acceleration lives.

**[7]** T. D. Gillespie, *Fundamentals of Vehicle Dynamics*. Warrendale, PA: SAE International,
1992 (2nd ed. 2021). ISBN 978-1-56091-199-9.
https://www.sae.org/publications/books/content/r-114/

*The standard reference for automotive ride dynamics. Establishes the two-mass model: the
**sprung mass** (body) resonates near **1–1.5 Hz**, while the **unsprung mass** (wheel, tyre,
hub) resonates at the **wheel-hop frequency, typically 10–15 Hz**. Only the first is below the
5 Hz ceiling; wheel hop is above it and aliases.*

**[8]** J. Nyman and O. Sundström, "Wheel Induced Vibrations on Heavy Vehicles," M.Sc. thesis,
Chalmers University of Technology / KTH, 2013.
https://www.diva-portal.org/smash/get/diva2:753968/FULLTEXT01.pdf

*Measured confirmation: the first force-amplitude peak occurs at **14–15 Hz**, close to the
second harmonic of wheel rotation, and at highway speeds the wheel rotational frequency
coincides with the unsprung-mass natural frequency, amplifying vertical vibration.*

### Wheel rotational frequency — derived, not cited

For a tyre of circumference *C*, rotational frequency is **f = v / C**. With a typical passenger
circumference of ≈1.9 m:

| Speed | Wheel rotation | Above the 5 Hz ceiling? |
|---|---|---|
| 20 km/h | 2.9 Hz | no |
| 30 km/h | 4.4 Hz | no |
| **40 km/h** | **5.9 Hz** | **yes — aliases** |
| 60 km/h | 8.8 Hz | yes |
| 100 km/h | 14.6 Hz | yes |

**Wheel rotation crosses the 10 Hz Nyquist limit at roughly 34 km/h** — below normal road speed.
Combined with wheel hop at 10–15 Hz [7][8] and engine firing order (a four-cylinder at
800–3000 rpm fires at **27–100 Hz**), essentially all vibration energy the phone experiences
while driving lies above the ceiling and folds down onto the signal.

> **Authority:** [7] is the SAE reference text for vehicle dynamics; [8] is a supervised
> master's thesis with measured spectra, published in a university repository.

---

## 5 · Machine learning — the algorithm used

**[9]** F. Pedregosa *et al.*, "Scikit-learn: Machine Learning in Python," *Journal of Machine
Learning Research*, vol. 12, pp. 2825–2830, 2011.
https://www.jmlr.org/papers/v12/pedregosa11a.html

**[10]** scikit-learn developers, "`sklearn.ensemble.HistGradientBoostingClassifier`,"
*scikit-learn API reference*.
https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html

The class this project trains. The official documentation states verbatim:

> "This implementation is **inspired by LightGBM**."

and describes the histogram mechanism:

> "Before training, each feature of the input array `X` is **binned into integer-valued bins**,
> which allows for a much faster training stage."

**[11]** G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, "LightGBM: A
Highly Efficient Gradient Boosting Decision Tree," in *Advances in Neural Information Processing
Systems 30 (NIPS 2017)*, pp. 3149–3157.
https://proceedings.neurips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf

*The algorithm scikit-learn's implementation is based on — histogram-based binning with
gradient-based one-side sampling and exclusive feature bundling.*

**[12]** J. H. Friedman, "Greedy Function Approximation: A Gradient Boosting Machine," *The
Annals of Statistics*, vol. 29, no. 5, pp. 1189–1232, 2001. DOI:
[10.1214/aos/1013203451](https://doi.org/10.1214/aos/1013203451)

*The original formulation of gradient boosting, which every implementation above descends from.*

> **Authority:** [9] JMLR and [12] *Annals of Statistics* are peer-reviewed journals; [11] is
> NeurIPS, a top-tier indexed conference; [10] is the library's own normative API documentation.

---

## 6 · Method — supporting the approach

**[13]** U. Onyekpe, V. Palade, S. Kanarachos, and S.-R. G. Christopoulos, "A Quaternion Gated
Recurrent Unit Neural Network for Sensor Fusion," *Information*, vol. 12, no. 3, art. 117, 2021.
DOI: [10.3390/info12030117](https://doi.org/10.3390/info12030117)

**[14]** U. Onyekpe, V. Palade, and S. Kanarachos, "Learning to Localise Automated Vehicles in
Challenging Environments Using Inertial Navigation Systems (INS)," *Applied Sciences*, vol. 11,
no. 3, art. 1270, 2021. DOI: [10.3390/app11031270](https://doi.org/10.3390/app11031270)

*Work by the dataset's own authors, using IO-VNBD. Both learn the **error in an existing
odometry solution** rather than regressing velocity from raw inertial data — consistent with
this project's finding that direct velocity regression is not viable at 10 Hz.*

**[15]** OpenStreetMap contributors, OpenStreetMap. https://www.openstreetmap.org
Data © OpenStreetMap contributors, available under the Open Database Licence (ODbL).
Overpass API: https://overpass-api.de/

*The offline map database named as an example in the problem statement.*

---

## 7 · Standards and specifications referenced

**[16]** STMicroelectronics, *LSM6DSV — iNEMO inertial module: 6-axis IMU*, datasheet.
https://www.st.com/en/mems-and-sensors/lsm6dsv.html

*The IMU in the Samsung M17 5G used as the target device, identified via on-device sensor
enumeration. Datasheet output data rates confirm the ~240 Hz measured in practice.*

---

## Citation note

Numbers quoted in this project's reports come from measurements on the IO-VNBD data, made with
the scripts in `analysis/`, not from any reference above. The references establish that the
**mechanisms** invoked — Nyquist aliasing, wheel-hop and rotational vibration frequencies,
Android's sensor contract, and the boosting algorithm — are documented and independently
verifiable.
