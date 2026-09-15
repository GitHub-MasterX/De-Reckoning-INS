"""Scoring for every round-2 method: 2D position error and distance error, as % of true distance travelled.
Results are reported per driving-condition group, every blackout counting equally (round2/DECISIONS.md)."""
import numpy as np
from .geo import enu


def truth_at(S, i, j):
    """True displacement (east, north metres from the start fix) and true distance, start row i to row j."""
    east, north = enu(S.lat[j], S.lon[j], S.lat[i], S.lon[i])
    return float(east), float(north), float(S.dist[j] - S.dist[i])


def errors(S, i, j, est_east, est_north, est_dist):
    """(2D position error %, distance error %) of an estimate made at row j of a blackout that began at row i.
    Estimated east/north are metres from the last fix before the blackout."""
    east, north, dist = truth_at(S, i, j)
    return 100*np.hypot(est_east - east, est_north - north)/dist, 100*abs(est_dist - dist)/dist
