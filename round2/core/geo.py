"""Local east/north metres around a reference point, from WGS84 radii of curvature.

Accurate to about a centimetre per kilometre at IO-VNBD latitudes. The common shortcut of
110,540 m per degree of latitude is 0.7% short at 52° N — 7 m per km, 7% of the 1 km budget."""
import numpy as np

A_WGS84 = 6378137.0
E2_WGS84 = 6.69437999014e-3


def _radii(lat0):
    phi = np.radians(lat0)
    s2 = np.sin(phi)**2
    return (A_WGS84*(1 - E2_WGS84)/(1 - E2_WGS84*s2)**1.5,      # north-south radius of curvature
            A_WGS84/np.sqrt(1 - E2_WGS84*s2),                   # east-west radius of curvature
            np.cos(phi))


def enu(lat, lon, lat0, lon0):
    """East and north metres of (lat, lon) from (lat0, lon0)."""
    m, n, cos_phi = _radii(lat0)
    return np.radians(np.asarray(lon, float) - lon0)*n*cos_phi, np.radians(np.asarray(lat, float) - lat0)*m


def inv_enu(east, north, lat0, lon0):
    """Latitude and longitude of a point given as east and north metres from (lat0, lon0)."""
    m, n, cos_phi = _radii(lat0)
    return lat0 + np.degrees(np.asarray(north, float)/m), lon0 + np.degrees(np.asarray(east, float)/(n*cos_phi))
