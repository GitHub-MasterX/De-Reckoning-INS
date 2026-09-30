"""Round-2 shared code: session loading, geodesy, the fixed blackout list, scoring.

Split into two subpackages: Foundation/ (data + scoring, no engine mechanism) and Engine/ (the actual
dead-reckoning/particle-filter/reporting mechanism, plus geo.py since 3 of the 8 Engine modules need it
against Foundation/scoring.py's 1). Re-exported flat here so `from core import sessions` etc. (used
throughout round2/ and round3_*.py) keeps working unchanged regardless of which subpackage a module lives in.
"""
from .Foundation import sessions, blackouts, context, engine_input, scoring
from .Engine import calibration, motion, deadreckoning, roadnet, roadnet_build, particle, smooth, geo
