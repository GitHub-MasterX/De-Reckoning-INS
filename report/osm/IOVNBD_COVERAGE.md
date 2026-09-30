# IO-VNBD geographic coverage

Measured from the vehicle GPS (`lat`, `lon`) of all 72 cleaned drives.
Bounds use the 0.1–99.9 percentile so single GPS glitches cannot stretch the box;
raw extremes differ by under 0.001°.

## All drives

| | South | North | West | East |
|---|---|---|---|---|
| **latitude** | **51.9468** | **53.7928** | | |
| **longitude** | | | **−2.2533** | **−0.6028** |

About **205 km north–south × 111 km east–west**, across the English Midlands up to West Yorkshire.

Ready-to-paste forms (with no margin added):

```
Overpass bbox   (S,W,N,E)          51.9468,-2.2533,53.7928,-0.6028
osmium extract  (minlon,minlat,maxlon,maxlat)   -2.2533,51.9468,-0.6028,53.7928
```

For map matching, add a margin so roads just outside a track are still present:

```
with ~5 km margin  (minlon,minlat,maxlon,maxlat)   -2.33,51.90,-0.53,53.84
```

## Per driver

| Driver | Latitude | Longitude | Where |
|---|---|---|---|
| **A** | 52.3627 → 52.5586 | −1.6034 → −1.2289 | Coventry and surroundings (68% within 15 km of the centre) |
| **B** | 52.3580 → 52.4791 | −1.5887 → −1.3787 | Coventry (100%) |
| **D** | 52.3948 → 52.4708 | −1.5456 → −1.4703 | Coventry (100%) |
| **E** | 51.9468 → 53.7928 | −2.2533 → −0.6028 | almost entirely **outside** Coventry — 63 of 64 drives |

Driver E clusters, read from the tracks (approximate place names):

- Derbyshire / Staffordshire — Burton, Ashbourne, Buxton (lat 52.8–53.3, lon −1.6 to −1.9)
- Worcester area (lat ~52.2, lon ~−2.2)
- Nuneaton / Hinckley (lat ~52.55, lon −1.46 to −1.54)
- East towards Milton Keynes (`Vw2`, `Vw3`, `Vw4` reach lon −0.6)
- North up the M1 corridor to Leeds (`Vfa02` reaches lat 53.79)

## Map source

`england-latest.osm.pbf` from Geofabrik, 1.6 GB, covering all of England, so every drive is
inside it. Covering the same area county by county would take about a dozen separate files.

- Download: https://download.geofabrik.de/europe/united-kingdom/england-latest.osm.pbf
- MD5 published at download time: `948d45e796752dd0c47e65fbb229b73d`
- Data © OpenStreetMap contributors, ODbL.

Neither the `.pbf` nor anything derived from it is committed to git (`data/osm/` is ignored).
