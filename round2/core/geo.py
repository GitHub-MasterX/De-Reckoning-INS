"""Local east/north metres around a reference point, from WGS84 radii of curvature.

Accurate to about a centimetre per kilometre at IO-VNBD latitudes. The common shortcut of
110,540 m per degree of latitude is 0.7% short at 52° N — 7 m per km, 7% of the 1 km budget."""
import numpy as np

A_WGS84 = 6378137.0
E2_WGS84 = 6.69437999014e-3


def enu(lat, lon, lat0, lon0):
    """East and north metres of (lat, lon) from (lat0, lon0)."""
    phi = np.radians(lat0)
    s2 = np.sin(phi)**2
    m = A_WGS84*(1 - E2_WGS84)/(1 - E2_WGS84*s2)**1.5     # north-south radius of curvature
    n = A_WGS84/np.sqrt(1 - E2_WGS84*s2)                  # east-west radius of curvature
    east = np.radians(np.asarray(lon, float) - lon0)*n*np.cos(phi)
    north = np.radians(np.asarray(lat, float) - lat0)*m
    return east, north
