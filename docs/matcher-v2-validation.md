# Local matcher v2 validation

The v1 matcher treated projections clamped to successive polyline endpoints
as independent route alternatives. A densely sampled straight road could
therefore become ambiguous solely because of its vertex spacing.

V2 removes an endpoint candidate only when the adjoining segment has a
strictly closer projection to the same fix. Interior projections and local
distance minima remain candidates, including separate branches of hairpins
and self-intersections. Freshness, GPS accuracy, acquisition, transition and
crossing thresholds remain unchanged. The algorithm version is
`m8-local-beam-v2`; source recordings and route verification are unchanged.

Regression coverage checks matching equivalence between coarse and dense
straight polylines, including approach to the start and stationary fixes.
Existing tests cover ambiguous parallel return segments, self-intersections,
corners, reverse travel, stale samples and impossible transitions.

Private recording `62373ee9441343539a359d81ada100c6` was replayed against the
same Arkadia route geometry before and after the change:

| Result | V1 | V2 |
| --- | ---: | ---: |
| MATCHED | 191 | 411 |
| UNCERTAIN | 183 | 6 |
| ACQUIRING | 47 | 4 |
| OFF_ROUTE | 74 | 74 |
| STALE | 31 | 31 |
| AMBIGUOUS_CANDIDATES reason | 177 | 0 |
| Confirmed crossing events | 0 | 5 |

All OFF_ROUTE samples in this replay precede acquisition at the route start
(approximately the first 78 seconds). Late samples remain excluded from live
matching. Five unconfirmed crossing events also remain: four interruptions
of forward-direction evidence and one crossing bracket longer than five
seconds. A confirmed algorithmic crossing is not field verification of the
draft stop-line coordinates or a validated traffic-signal phase model.

Derived reports are stored locally under `data/derived/`; private raw GPS
tracks are not included in this document.

Validation: `python -m unittest discover -s tests -q` — 173 tests passed,
one skipped.
