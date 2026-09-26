# Vision contracts v1

Implemented shared DTOs: `greenwave/vision_contracts.py`. They have no ML
dependencies and do not mutate GPS, raw runs, history or the prediction engine.

JSON envelopes have exactly `schema_version: 1`, `type` and `data`.
`decode_vision` validates nested DTOs, rejects unsupported versions and unknown
fields. Numeric values must be finite. Internal DTOs are frozen dataclasses;
bounding boxes and candidate lists use tuples. JSON represents them as arrays.

| DTO | Meaning |
| --- | --- |
| CameraFrameRef | Camera/session identity, ordered frame number, capture monotonic nanoseconds, timezone-aware UTC estimate, clock uncertainty, original width/height, optional media ref and PTS |
| VisionDetection | Frame, bbox in original pixels, state, pictogram, flashing status, model score and model SHA-256, optional tracker identity |
| VisionTrack | Track identity, first/latest detections from that track and camera/session, visibility |
| SignalAssociation | Track/session, assignment status and method, route/hash/line, direction/movement, optional display name and stop-line coordinates, candidates |
| VisionObservation | Current detection, association, seen/start distinction, optional previous-state evidence, continuity, review status/reviewer |

States: RED, YELLOW, GREEN, RED_YELLOW, OFF, UNKNOWN. No mapping of red-yellow
to green. Model scores are model outputs, not calibrated system probabilities.
The geographic coordinates belong to the stop line, not a measured lamp.
Names originate from assignment/map metadata, not from the image detector.

V1 allows CONFIRMED assignments only by MANUAL method with full directional
route identity. GPS and geometry produce proposals only. Review acceptance
requires confirmed assignment and reviewer identity. Even accepted observations
have `live_prediction_eligible=False`; these DTOs cannot enable recommendations.

STATE_START requires distinct ordered frames, distinct known active states,
the same track/camera/session and confirmed tracking continuity. Its timestamp
is the monotonic interval between the two capture frames, not inference finish
time. Clock uncertainty remains attached to each frame. First sightings and
recovery after lost tracking use STATE_SEEN. Evidence references are retained
when recording later review decisions; changing this DTO is not a raw-log edit.

`greenwave/vision_demos.py` supplies nine synthetic scenarios: no camera, good
detection, multiple lamps, unknown color, conflict, lost image, stale GPS,
wrong direction and phone disconnection. All are explicitly synthetic and
ineligible for live predictions. Locations and street names are examples.

Export JSON for frontend development with:

```powershell
python -m greenwave.vision_demos
```

This step implements contracts and mock data only. It does not install YOLO,
read a camera, compute tracking or assign real lamps. Next: benchmark candidate
models in an isolated environment, then build UI and capture against these DTOs.
