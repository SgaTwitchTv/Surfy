# Step 6 — experimental detection and lamp tracking (UV-07–08)

Start GreenWave from `.worktrees/vision-camera`:

```powershell
python -m greenwave --no-browser --port 8767
```

Open `http://127.0.0.1:8767` → **Laboratorium**. Choose FILE and a local video
path, or CAMERA and a device index. Check **YOLO + tracker (eksperyment)**,
then **Uruchom podgląd i zapis**. The local candidate weights and `.venv-cv`
from the earlier feasibility probe are required. Missing weights/dependencies
produce an error; no model downloads happen at capture startup.

For complete movie analysis, uncheck real-time playback. This processes every
decoded frame with a bounded, blocking queue; media PTS drives tracking even
when processing faster/slower than playback. Camera/real-time mode keeps a
single latest frame, dropping old queued frames rather than accumulating delay.
The original recorded image is never annotated; only JPEG preview copies are.

Each visible box shows a session-local lamp ID, filtered state and `unassigned`.
The status panel exposes frame/inference counters, current tracks and candidate
events. UNKNOWN is displayed while a state change lacks sufficient evidence.
No location/name is invented: route association is the next stage.

## Algorithm and evidence

The CPU adapter reuses the pinned nano YOLO candidate documented in
`vision-probe.md`. Its joint detection/state classes are red, green, yellow and
off. It does not establish red-yellow combinations, arrows, pedestrian heads
or flashing; pictogram/flashing remain UNKNOWN when unsupported. Tiny or
low-scoring boxes become UNKNOWN. These provisional thresholds are not validated
road accuracy. Overlap suppression is class-agnostic to reduce duplicate boxes.
Bounding boxes come from Ultralytics `boxes.xyxy` in original-image coordinates:
https://docs.ultralytics.com/modes/predict/#boxes .

The conservative tracker uses mutual unambiguous IoU matching, without matching
by color (a change of color must preserve identity). IoU below .25 or competing
matches within .15 do not reuse the identity. IDs expire after 1.5 seconds.
No motion predictor or appearance embedding is used; rapid motion/crossings may
produce new IDs. This is deliberate uncertainty, not guaranteed identity.

A new state needs at least three detections spanning .15 seconds. A short color
flash produces no transition. Missing detections, UNKNOWN/OFF, a gap over .5 s,
reversed/repeated media time or changed capture segment clear continuity.
First confirmation emits STATE_SEEN. A continuous confirmed change emits a
pending STATE_START candidate with last-old/first-new frame evidence and a
tracking-clock interval, not inference completion time. Temporal confirmation
does not prove the model's color was correct. Flashing is not classified and
requires labeled clips before choosing a suitable policy.

`vision.jsonl` stores per-frame detections, tracks, pending observations, clocks
and inference duration. Manifest records model hash/classes/version/thresholds,
analysis mode, counts and artifact hashes. `DRAINING` means decoding has ended
but analysis has not; `ENDED` is only published after finalization. All
observations remain unassigned/PENDING and in this independent vision journal.
Existing manual history, raw GPS, phase estimates and speed recommendations
receive no automatic CV events. Historical GPS synchronization remains unverified.
Replay buttons currently replay video without automatically enabling analysis;
to reanalyze, select FILE and the recorded video artifact and check YOLO.

## Tests and road acceptance still required

```powershell
python -m unittest discover -s tests -q
.venv-cv/Scripts/python.exe -m scripts.check_capture
.venv-cv/Scripts/python.exe -m scripts.check_tracking
```

Tracker tests cover multiple lamps, ambiguity, transient colors, unknown/off,
missing detections, gaps, new segments and reversed clocks. The integration smoke
uses the earlier repeated-still clip: real YOLO processes all 15 frames, produces
stable tracks and first-seen evidence, with no invented transition. This proves
integration, not road accuracy. `scripts/check_tracking.cjs` checks real inference,
preview and track data in Edge against a dedicated server using Playwright.

Next acceptance material: a locally available dashcam video with readable lights
and observed changes. Keep separate clips for tuning and evaluation. Manually
label boxes/identities/colors and transition intervals, then measure missed lamps,
false GREEN, switches, timing error and UNKNOWN. Day/night, tiny lights, reflections,
occlusions, arrows and red-yellow require separate cases. Unsupported states can
require another model. The implementation is ready for these tests; road quality
and physical-camera operation are not yet accepted.
