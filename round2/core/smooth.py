"""A reported position that moves like a vehicle.

The particle filter believes several things at once — one guess per road it might be on. The position it reports is the
centre of whichever group of guesses is strongest at that moment, so when a different group takes over (at a junction,
after a resample, after a re-seed) the reported point moves across the gap between two roads in a single step. Measured
on round 2: every blackout contains at least one step of more than 20 m in one second, the worst of them 84 m in the
median blackout. A vehicle cannot do that, and on a screen it is the most obvious flaw there is.

This is a reporting layer, not a change to what the filter believes: the filter's own estimate is the target, and the
reported cursor chases it at a speed a vehicle could manage.

    limit = max(CATCH_UP x speed, speed + EXTRA_MS)      how fast the cursor may travel, m/s
    the cursor moves toward the filter's estimate, never further than limit x dt in one step

So a brief wrong-road excursion is mostly absorbed (the cursor leans towards it and comes back), and a real correction
still arrives, a few seconds later, as motion instead of a teleport. The speed used is the engine's own held speed, not
the truth.
"""
import numpy as np

CATCH_UP = 1.5               # the cursor may move this much faster than the vehicle is believed to be going
EXTRA_MS = 3.0               # plus this, so it can still close a gap when the vehicle is slow or stopped


def smooth_track(t, east, north, speed, catch_up=CATCH_UP, extra_ms=EXTRA_MS, start=(0.0, 0.0)):
    """Follow the filter's estimates (east, north, metres) with a cursor that never exceeds a vehicle's speed.

    t        the time of each estimate, s
    speed    the engine's believed speed at each estimate, m/s (the held GNSS speed; never the truth)
    start    where the cursor begins — the last fix, i.e. the origin of the east/north frame
    Returns the reported east and north.
    """
    t = np.asarray(t, float)
    east = np.asarray(east, float)
    north = np.asarray(north, float)
    speed = np.broadcast_to(np.asarray(speed, float), east.shape)
    out_e = np.empty_like(east)
    out_n = np.empty_like(north)
    cx, cy = float(start[0]), float(start[1])
    prev_t = t[0] - (t[1] - t[0] if len(t) > 1 else 1.0)
    for k in range(len(t)):
        dt = max(float(t[k] - prev_t), 1e-6)
        prev_t = t[k]
        dx, dy = east[k] - cx, north[k] - cy
        gap = float(np.hypot(dx, dy))
        limit = max(catch_up*float(speed[k]), float(speed[k]) + extra_ms)*dt
        if gap > limit and gap > 0:
            cx += dx*limit/gap
            cy += dy*limit/gap
        else:
            cx, cy = float(east[k]), float(north[k])
        out_e[k], out_n[k] = cx, cy
    return out_e, out_n


class ModeTracker:
    """Which group of guesses gets reported, with hysteresis — the filter-side half of the fix.

    The filter believes several roads at once. Round 2 reports whichever group is strongest at this instant, so a
    competitor that edges ahead for a single update pulls the reported position onto another road and then gives it
    back. This keeps reporting the group it reported last time, and hands over only when a competitor has been clearly
    better (MARGIN times the weight) for HOLD updates in a row — or when the group being reported dies altogether.

    It changes nothing the filter believes and consumes no random numbers: same particles, same weights, same
    resampling. Only the choice of which mode is shown.
    """

    def __init__(self, cluster_m, margin=1.6, hold=3):
        self.cluster_m = float(cluster_m)
        self.margin = float(margin)
        self.hold = int(hold)
        self.anchor = None          # (east, north) of the mode being reported
        self.streak = 0
        self.switches = 0

    def __call__(self, net, st, w, lat0, lon0, p):
        from .geo import enu
        edge = st["edge"]
        seg = net.edge_seg[edge]
        f = np.clip(st["off"]/np.maximum(net.edge_len[edge], 1e-6), 0.0, 1.0)
        fwd = net.edge_dir[edge] > 0
        a = np.where(fwd, net.seg_u[seg], net.seg_v[seg])
        b = np.where(fwd, net.seg_v[seg], net.seg_u[seg])
        lat = net.node_lat[a] + f*(net.node_lat[b] - net.node_lat[a])
        lon = net.node_lon[a] + f*(net.node_lon[b] - net.node_lon[a])
        east, north = enu(lat, lon, lat0, lon0)

        best = int(np.argmax(w))
        comp = np.hypot(east - east[best], north - north[best]) <= self.cluster_m      # the strongest group now
        w_comp = float(w[comp].sum())

        if self.anchor is None:
            keep = comp
        else:
            keep = np.hypot(east - self.anchor[0], north - self.anchor[1]) <= self.cluster_m
            w_keep = float(w[keep].sum())
            if w_keep <= 0:
                keep, self.streak = comp, 0                       # the mode we were reporting is gone
                self.switches += 1
            elif not keep[best] and w_comp > self.margin*w_keep:      # the rival is a different mode, not our own
                self.streak += 1
                if self.streak >= self.hold:
                    keep, self.streak = comp, 0                   # a rival has been clearly better long enough
                    self.switches += 1
            else:
                self.streak = 0

        ww = w[keep]
        if ww.sum() <= 0:
            keep = np.zeros(len(w), bool)
            keep[best] = True
            ww = np.ones(1)
        ww = ww/ww.sum()
        e, n, d = float(ww @ east[keep]), float(ww @ north[keep]), float(ww @ st["dist"][keep])
        self.anchor = (e, n)
        return e, n, d
