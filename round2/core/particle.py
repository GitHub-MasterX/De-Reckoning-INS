"""Road-constrained particle filter — the step-5 correction (round2/DECISIONS.md).

Each particle is one guess: which drivable direction of which road it is on, how far along it, and how fast.
  every 0.1 s   the guess drives on; at a junction it picks an exit, favouring the one closest to the gyro's
                current heading, and slightly favouring staying on a road of the same standing
  every 2 s     the turning its roads produced is compared with the gyro's turning over the same seconds, and its
                road's direction with the gyro's heading; guesses that disagree lose weight and are resampled away
  fallback      if every guess disagrees for several updates, the filter re-seeds around plain dead reckoning

The gyro, the last GNSS fix and the phone clock come from core/engine_input.py; nothing here sees the true track."""
import numpy as np

from . import deadreckoning, roadnet
from .geo import enu, inv_enu

FS = 10.0        # the data is 10 Hz (round2/core/sessions.py)

DEFAULTS = dict(
    n=500,                    # particles
    radius0=25.0,             # m, roads considered at the start fix
    bearing0_deg=60.0,        # a road must run within this of the start course
    sigma_pos0=5.0,           # m, how far the fix may be from the true road
    sigma_head0_deg=15.0,     # deg, how far the road may point from the course
    sigma_off0=1.5,           # m, spread along the road at the start — the fix itself is good, so keep it tight
    sigma_v0=0.04,            # share of the GNSS speed
    q_speed=0.5,              # m/s per sqrt(s), how fast the speed guess may wander
    speed_pull=0.0,           # 1/s, how strongly the speed guess is drawn back to the last GNSS speed (0 = free)
    v_min=0.5, v_max=45.0,    # m/s
    update_s=2.0,             # seconds between weight updates
    sigma_turn_deg=8.0,       # deg, road turning against gyro turning over one update
    sigma_abs_deg=25.0,       # deg, road direction against the gyro's heading
    sigma_choice_deg=45.0,    # deg, how strongly an exit must match the heading to be picked
    class_logprior=(0.0, 0.0, 0.0, 0.0, 0.0, -0.2, -0.4, -0.7, -1.2, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5),
    speed_limit_slack=1.25, sigma_limit=3.0,     # m/s over the tagged limit before it costs weight
    ess_frac=0.5,             # resample when the effective number of guesses falls below this share
    rough_off=2.0, rough_speed=0.3,              # jitter after resampling
    bad_deg=60.0, bad_updates=3,                 # when to decide the map explains nothing
    reseed_radius=30.0, cluster_m=40.0,
    dr_blend_m=0.0,           # m: report plain dead reckoning until this far from the fix, then hand over to the
                              # map over the next 100 m (0 = the map from the first metre). Right after a fix,
                              # dead reckoning beats snapping to a road centreline.
    info_turn_deg=8.0,        # a turn of at least this much in one update tells the map where the car is
    straight_blend_m=0.0)     # m: on a straight with no such turn, hand back from the map to dead reckoning
                              # reckoned from the last map-corrected point, over the following 150 m (0 = never)


def _seed(net, lat, lon, course, speed, n, p, rng, radius=None):
    """Particles on the drivable roads around one fix, or None if there is no road to sit on."""
    edges, dist, dpsi, along = net.candidates(lat, lon, course, radius or p["radius0"], p["bearing0_deg"])
    if not len(edges):
        return None
    w = np.exp(-(dist/p["sigma_pos0"])**2/2 - (dpsi/np.radians(p["sigma_head0_deg"]))**2/2)
    if not np.isfinite(w).any() or w.sum() <= 0:
        return None
    pick = rng.choice(len(edges), size=n, p=w/w.sum())
    edge = edges[pick].astype(np.int64)
    off = np.clip(along[pick] + rng.normal(0.0, p["sigma_off0"], n), 0.0, net.edge_len[edge])
    v = np.clip(speed*(1.0 + rng.normal(0.0, p["sigma_v0"], n)), p["v_min"], p["v_max"])
    return dict(edge=edge, off=off, v=v, logw=np.zeros(n), turn=np.zeros(n), dist=np.zeros(n))


def _advance(net, st, psi_now, p, rng, max_rounds=8):
    """Move particles past the ends of their roads, choosing an exit at each junction."""
    sig = np.radians(p["sigma_choice_deg"])
    prior = np.asarray(p["class_logprior"], float)
    k_max = 6
    edge, off, logw, turn = st["edge"], st["off"], st["logw"], st["turn"]
    for _ in range(max_rounds):
        ii = np.flatnonzero((off >= net.edge_len[edge]) & np.isfinite(logw))
        if not len(ii):
            return
        off[ii] -= net.edge_len[edge[ii]]
        node = net.edge_to[edge[ii]]
        base, end = net.out_ptr[node], net.out_ptr[node + 1]
        deg = end - base
        cols = np.minimum(base[:, None] + np.arange(k_max)[None, :], np.maximum(end - 1, base)[:, None])
        cand = net.out_edges[cols]
        valid = (np.arange(k_max)[None, :] < deg[:, None])
        lp = (-(roadnet.wrap(net.edge_bearing[cand] - psi_now)**2)/(2*sig**2)
              + prior[net.seg_class[net.edge_seg[cand]]])
        allow = valid & (cand != net.edge_rev[edge[ii]][:, None])       # no U-turns unless there is nowhere else
        solo = ~allow.any(axis=1)
        allow[solo] = valid[solo]
        lp = np.where(allow, lp, -np.inf)
        pick = np.argmax(lp + rng.gumbel(size=lp.shape), axis=1)
        rows = np.arange(len(ii))
        dead = (deg == 0) | ~np.isfinite(lp[rows, pick])
        old_bearing = net.edge_bearing[edge[ii]]
        live = ~dead
        chosen = cand[rows, pick]
        edge[ii[live]] = chosen[live]
        turn[ii[live]] += roadnet.wrap(net.edge_bearing[chosen[live]] - old_bearing[live])
        if dead.any():
            logw[ii[dead]] = -np.inf
            off[ii[dead]] = 0.0


def _weights(logw):
    if not np.isfinite(logw).any():
        return None
    w = np.exp(logw - np.max(logw[np.isfinite(logw)]))
    w[~np.isfinite(logw)] = 0.0
    s = w.sum()
    return w/s if s > 0 else None


def _estimate(net, st, w, lat0, lon0, cluster_m):
    """Weighted centre of the strongest group of guesses: east, north (m from the fix) and distance travelled."""
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
    near = np.hypot(east - east[best], north - north[best]) <= cluster_m
    ww = w[near]
    if ww.sum() <= 0:
        near = np.zeros(len(w), bool)
        near[best] = True
        ww = np.ones(1)
    ww = ww/ww.sum()
    return float(ww @ east[near]), float(ww @ north[near]), float(ww @ st["dist"][near])


def run(inp, net, stationary, record_rows, params=None, rng=None):
    """Run the filter over one blackout. Returns the estimate at each row in `record_rows` (east, north metres from
    the start fix, and distance travelled), plus diagnostics."""
    p = dict(DEFAULTS)
    p.update(params or {})
    rng = rng if rng is not None else np.random.default_rng(0)
    n = int(p["n"])
    t = inp.t
    rows = len(t)
    dt = np.clip(np.diff(t), 0.0, None)
    psi = inp.course0 + np.concatenate(([0.0], np.cumsum(inp.turn_rate()[:-1]*dt)))     # gyro heading per row
    dr_e, dr_n, dr_d = deadreckoning.run(inp, stationary=stationary)                    # the fallback
    upd = max(1, int(round(p["update_s"]*FS)))
    record = {int(r): None for r in record_rows}
    out = dict(east=[], north=[], dist=[], rows=[], ess=[], on_map=[], reseeds=0, reseed_failed=0,
               fallback_rows=0, seeded=True)

    st = _seed(net, inp.lat0, inp.lon0, inp.course0, inp.speed0, n, p, rng)
    if st is None:                                                    # no road at the fix: plain dead reckoning
        out["seeded"] = False
        for r in sorted(record):
            out["rows"].append(r); out["east"].append(dr_e[r]); out["north"].append(dr_n[r])
            out["dist"].append(dr_d[r]); out["ess"].append(np.nan); out["on_map"].append(False)
        out["fallback_rows"] = rows
        return out

    bad, psi_prev = 0, psi[0]
    anchor = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)          # last map-corrected point: filter east/north/dist, DR east/north/dist
    for k in range(rows - 1):
        if stationary[k]:
            step = np.zeros(n)
        else:
            st["v"] += (p["speed_pull"]*(inp.speed0 - st["v"])*dt[k]
                        + rng.normal(0.0, p["q_speed"]*np.sqrt(max(dt[k], 1e-6)), n))
            np.clip(st["v"], p["v_min"], p["v_max"], out=st["v"])
            step = st["v"]*dt[k]
        st["off"] += step
        st["dist"] += step
        _advance(net, st, psi[k], p, rng)

        if (k + 1) % upd == 0:
            psi_at_prev_update = psi_prev
            mism = roadnet.wrap(st["turn"] - (psi[k + 1] - psi_prev))
            st["logw"] += -(mism**2)/(2*np.radians(p["sigma_turn_deg"])**2)
            st["logw"] += -(roadnet.wrap(net.edge_bearing[st["edge"]] - psi[k + 1])**2
                            )/(2*np.radians(p["sigma_abs_deg"])**2)
            limit = net.seg_maxspeed[net.edge_seg[st["edge"]]]/3.6
            excess = np.where(np.isfinite(limit), np.maximum(0.0, st["v"] - p["speed_limit_slack"]*limit), 0.0)
            st["logw"] += -(excess**2)/(2*p["sigma_limit"]**2)
            st["turn"][:] = 0.0
            psi_prev = psi[k + 1]

            w = _weights(st["logw"])
            if w is None:
                bad = p["bad_updates"]
            else:
                alive = np.isfinite(st["logw"])
                bad = bad + 1 if np.degrees(np.abs(mism[alive]).min()) > p["bad_deg"] else 0
                ess = 1.0/np.sum(w**2)
                if ess < p["ess_frac"]*n:
                    idx = np.searchsorted(np.cumsum(w), (rng.random() + np.arange(n))/n)
                    for key in ("edge", "off", "v", "dist"):
                        st[key] = st[key][idx]
                    st["turn"] = st["turn"][idx]
                    st["off"] = np.clip(st["off"] + rng.normal(0.0, p["rough_off"], n), 0.0, net.edge_len[st["edge"]])
                    st["v"] = np.clip(st["v"] + rng.normal(0.0, p["rough_speed"], n), p["v_min"], p["v_max"])
                    st["logw"] = np.zeros(n)
                    w = np.full(n, 1.0/n)                # the guesses were reordered: the old weights no longer match
                else:
                    st["logw"] = np.log(np.maximum(w, 1e-300))
            if (p["straight_blend_m"] > 0 and w is not None
                    and abs(np.degrees(psi[k + 1] - psi_at_prev_update)) >= p["info_turn_deg"]):
                fe, fn, fd = _estimate(net, st, w, inp.lat0, inp.lon0, p["cluster_m"])
                anchor = (fe, fn, fd, dr_e[k + 1], dr_n[k + 1], dr_d[k + 1])     # the map just told us where we are
            if bad >= p["bad_updates"]:                              # the map explains nothing: start again on it
                lat_dr, lon_dr = inv_enu(dr_e[k + 1], dr_n[k + 1], inp.lat0, inp.lon0)
                fresh = _seed(net, float(lat_dr), float(lon_dr), psi[k + 1], float(np.median(st["v"])), n, p, rng,
                              radius=p["reseed_radius"])
                if fresh is None:
                    out["reseed_failed"] += 1
                else:
                    fresh["dist"] = np.full(n, float(np.median(st["dist"])))
                    st = fresh
                    out["reseeds"] += 1
                bad = 0
                psi_prev = psi[k + 1]

        if (k + 1) in record:
            w = _weights(st["logw"])
            if w is None:
                east, north, dist_est, on_map = dr_e[k + 1], dr_n[k + 1], dr_d[k + 1], False
                out["fallback_rows"] += 1
            else:
                east, north, dist_est = _estimate(net, st, w, inp.lat0, inp.lon0, p["cluster_m"])
                on_map = True
                if p["straight_blend_m"] > 0:            # long straight: coast on from the last map-corrected point
                    since = dr_d[k + 1] - anchor[5]
                    back = float(np.clip((since - p["straight_blend_m"])/150.0, 0.0, 1.0))
                    if back > 0:
                        east = (1 - back)*east + back*(anchor[0] + dr_e[k + 1] - anchor[3])
                        north = (1 - back)*north + back*(anchor[1] + dr_n[k + 1] - anchor[4])
                        dist_est = (1 - back)*dist_est + back*(anchor[2] + dr_d[k + 1] - anchor[5])
                        on_map = back < 0.5
                if p["dr_blend_m"] > 0:                  # hand over from the fresh fix to the map
                    share = float(np.clip((dr_d[k + 1] - p["dr_blend_m"])/100.0, 0.0, 1.0))
                    east = share*east + (1 - share)*dr_e[k + 1]
                    north = share*north + (1 - share)*dr_n[k + 1]
                    dist_est = share*dist_est + (1 - share)*dr_d[k + 1]
                    on_map = on_map and share > 0.5
            out["rows"].append(k + 1); out["east"].append(east); out["north"].append(north)
            out["dist"].append(dist_est); out["on_map"].append(on_map)
            out["ess"].append(float(1.0/np.sum(w**2)) if w is not None else np.nan)
    return out
