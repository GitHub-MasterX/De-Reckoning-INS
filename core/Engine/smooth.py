"""A reported position that moves like a vehicle.

The particle filter believes several things at once — one guess per road it might be on. The position it reports is the
centre of whichever group of guesses is strongest at that moment, so when a different group takes over (at a junction,
after a resample, after a re-seed) the reported point moves across the gap between two roads in a single step. Measured
on round 2: every blackout contains at least one step of more than 20 m in one second, the worst of them 84 m in the
median blackout. A vehicle cannot do that, and on a screen it is the most obvious flaw there is.

This is a reporting layer, not a change to what the filter believes: the filter's own estimate is the target, and the
reported cursor chases it at a speed a vehicle could manage.

    limit = max(CATCH_UP x speed, speed + EXTRA_MS)      the ordinary allowance, m/s
    if the gap is large, the cursor is allowed gap / CLOSE_S instead, capped at MAX_FACTOR x speed (or speed +
    MAX_EXTRA_MS), so it closes a standing gap in about CLOSE_S seconds rather than trailing behind for the whole
    blackout

Both halves matter. Without the first the cursor teleports; without the second it lags — measured on the replay clips,
the plain speed limit left the cursor 169 m behind the vehicle where round 2 had been 83 m behind, because round 2 got
there by jumping 188 m in one step. The speed used is the engine's own held speed, never the truth.
"""
import numpy as np

CATCH_UP = 1.5               # the cursor may move this much faster than the vehicle is believed to be going
EXTRA_MS = 3.0               # plus this, so it can still close a gap when the vehicle is slow or stopped
CLOSE_S = 8.0                # a standing gap should be closed in about this long, so the cursor never trails for ever
MAX_FACTOR = 3.0             # but never faster than this multiple of the vehicle's speed
MAX_EXTRA_MS = 15.0          # or this much above it, whichever is the more generous


def smooth_track(t, east, north, speed, catch_up=CATCH_UP, extra_ms=EXTRA_MS, start=(0.0, 0.0),
                 close_s=CLOSE_S, max_factor=MAX_FACTOR, max_extra_ms=MAX_EXTRA_MS):
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
    hx, hy = 0.0, 0.0            # the direction the cursor is travelling, kept between steps
    prev_t = t[0] - (t[1] - t[0] if len(t) > 1 else 1.0)
    for k in range(len(t)):
        dt = max(float(t[k] - prev_t), 1e-6)
        prev_t = t[k]
        dx, dy = east[k] - cx, north[k] - cy
        gap = float(np.hypot(dx, dy))
        v = float(speed[k])
        allow = max(catch_up*v, v + extra_ms)                       # ordinary following
        if close_s > 0 and gap > 0:
            # Catching up is only safe in the direction the cursor is already travelling. A gap that lies ahead of
            # (or behind) the cursor is a place on the same road, so close it fast; a gap off to the side means the
            # filter has changed its mind about which road, and hurrying there is exactly the jump we are removing.
            if hx == 0.0 and hy == 0.0:
                hx, hy = dx/gap, dy/gap
            ahead = abs(dx*hx + dy*hy)
            ceiling = max(max_factor*v, v + max_extra_ms)
            allow = min(max(allow, ahead/close_s), ceiling)
        limit = allow*dt
        px, py = cx, cy
        if gap > limit and gap > 0:
            cx += dx*limit/gap
            cy += dy*limit/gap
        else:
            cx, cy = float(east[k]), float(north[k])
        step = float(np.hypot(cx - px, cy - py))
        if step > 0.5:                                             # remember where it is heading, ignoring jitter
            hx, hy = (cx - px)/step, (cy - py)/step
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

    def __init__(self, cluster_m, margin=1.6, hold=3, release_m=80.0, min_share=0.05):
        self.cluster_m = float(cluster_m)
        self.margin = float(margin)
        self.hold = int(hold)
        self.release_m = float(release_m)      # holding a mode this far from the filter's best guess helps nobody
        self.min_share = float(min_share)      # nor holding one the filter has all but abandoned
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
            far = float(np.hypot(self.anchor[0] - east[best], self.anchor[1] - north[best]))
            if w_keep <= 0 or w_keep < self.min_share or far > self.release_m:
                keep, self.streak = comp, 0                       # gone, abandoned, or left far behind
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
