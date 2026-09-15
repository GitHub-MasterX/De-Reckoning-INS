"""Map-free 2D dead reckoning — the step-3 baseline engine.

  heading   last GNSS course + turning from the calibrated gyro
  speed     last GNSS speed, held; zero while the motion classifier says stationary (ZUPT)
  position  speed × heading, integrated on the phone clock

Diagnostics may replace heading or speed with truth; that is for reporting only, never part of the engine."""
import numpy as np


def run(inp, stationary=None, heading=None, speed=None):
    """East and north (m from the start fix) and distance travelled, one value per row of the engine input.
    stationary: bool per row for ZUPT. heading (radians, clockwise from north) / speed (m/s): diagnostic overrides."""
    n = len(inp.t)
    dt = np.clip(np.diff(inp.t), 0.0, None)
    if heading is None:
        heading = inp.course0 + np.concatenate(([0.0], np.cumsum(inp.turn_rate()[:-1]*dt)))
    if speed is None:
        speed = np.full(n, inp.speed0)
        if stationary is not None:
            speed = np.where(stationary, 0.0, speed)
    step = speed[:-1]*dt
    east = np.concatenate(([0.0], np.cumsum(step*np.sin(heading[:-1]))))
    north = np.concatenate(([0.0], np.cumsum(step*np.cos(heading[:-1]))))
    dist = np.concatenate(([0.0], np.cumsum(step)))
    return east, north, dist
