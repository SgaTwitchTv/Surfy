# Steps 7–8 — association, review and readiness for field testing

Scope: UV-09–10 implementation and UV-11 software validation tools, plus the
UV-12 field procedure. Road acceptance is still pending real labeled material.
This completes the experimental web UI; a standalone Android navigation/camera
application and final product styling are separate work.

## Start the combined UI/camera branch

```powershell
cd C:\Users\konra\source\repos\SgaTwitchTv\Surfy\.worktrees\vision-camera
python -m greenwave --no-browser --port 8767
```

Open `http://127.0.0.1:8767`. The main checkout is unchanged.
For the phone UI through USB:

```powershell
adb devices
adb reverse tcp:8767 tcp:8767
```

On the phone, open the same localhost URL in its browser. The native Android GPS
sender stays the source of location; configure its receiver port to match the
server and pair using that server's code. A browser GPS page is not substituted.
The camera remains connected to the computer. Web layouts are checked at 320/390
pixels and in landscape; actual Android background GPS/USB behavior still needs
hardware verification after switching between the sender and browser.

## First desktop test with a local dashcam film

1. Choose **Trasa GPS** matching the material, if one is available. A film from
   another city can test detection/tracking, but do not assign its lights to Warsaw.
2. Open **Laboratorium**, choose FILE, enter an absolute local video path and
   enable **YOLO + tracker**. Leave real-time playback enabled to inspect it,
   or disable it to analyze every decoded frame offline.
3. Start capture. Check frame/inference counters, boxes, state and lamp IDs.
4. Under **Przypisania lamp i przegląd CV**, choose the correct lamp and stop
   line/direction/movement, then **Przypisz lampę**. This is a human confirmation,
   not a GPS inference. Unknown pictograms do not prove vehicle relevance;
   recognized pedestrian/incompatible arrow classes are rejected.
5. Read the resulting label. File states are explicitly historical and are never
   shown as live road states on the navigation map. GPS proposals require a
   MATCHED forward position; they do not identify a lamp automatically.
6. Stop capture and refresh recordings. Select it and **Wczytaj zdarzenia CV**.
   A large import is bounded per request: refresh again while progress is pending.
7. Choose a stop line and enter the reviewer name. Confirm or reject a candidate.
   A repeated identical decision is idempotent; a changed decision appends a new
   record. Original model output is never edited.
8. **Odtwórz od zdarzenia** reopens the recording half a second before its PTS in
   the capture worker. It supports camera MJPEG AVI as well as readable movie
   formats and creates a separate replay capture. Stop an active capture first.
9. **Otwórz oryginalny film** uses native browser playback when the codec is
   supported (typically suitable MP4/WebM). If it is not, use worker playback.
   Byte-range requests are authenticated and bounded to 1 MiB per response,
   keeping media transfers bounded on the serialized local server.
10. **Eksport przeglądu** downloads the displayed review page (up to 200 CV events)
    with original evidence and separate decisions. All imported events/decisions
    remain stored in SQLite. Use **Starsze zdarzenia** for preceding pages.

## Camera, map and conflicts

Live manual associations are scoped to capture/segment/app session, route ID and
geometry hash. Missing/stale frames, changed geometry, session or tracker
continuity generation revoke them. Continuity generations also catch gaps that
occur between UI polls. Associations are not recovered automatically after restart.

Several lamps for one line produce a color only when their known states agree.
Disagreement produces CONFLICT; UNKNOWN/OFF prevents a confident grouped color.
Distinct lines remain independent. Nearby manual and CV observations with different
colors show a MANUAL/CV conflict (two-second comparison window, assumed one-second
host timestamp uncertainty). Neither source overwrites the other. This is a
diagnostic comparison, not calibrated synchronization.

The perspective navigation map displays current camera states only with fresh GPS,
MATCHED forward direction, a matching route/hash, fresh camera frame and recent
server response. Labels say they are camera observations with manual association.
This display never relaxes the backend's phase/geometry/limit gates or feeds CV
into recommendations. Historical movie/replay states are excluded.

## History and GPS provenance

`data/derived/vision-capture/reviews.sqlite3` stores the independent event index,
append-only review decisions and assignment audit. Back it up with video artifacts;
reviewer decisions cannot be rebuilt from model output alone. New captures have a
compact `events.jsonl` alongside per-frame `vision.jsonl`; older captures import
from their per-frame journal. Duplicate imports do not duplicate observations.

If camera capture began during an active GPS recording, its manifest carries that
run ID. **Wczytaj powiązany GPS osobno** opens the existing GPS replay. It does not
invent a time alignment. For indexed passenger observations, first use
**Historia świateł ze wszystkich przejazdów → Importuj / odśwież nagrania**.
Matching run entries then appear beside CV review as a separate MANUAL source.
Unrelated/history-free films have no linked GPS. Accepted CV review remains outside
phase learning and does not increase confirmed phase-start counts in M8.

## Offline quality report

After obtaining a real local film, analyze it with every-frame mode and manually
label representative frames. Use capture frame IDs from `vision.jsonl`, original
image pixel coordinates and a real ground-truth lamp ID. Source video SHA-256 is
in the manifest. Example annotation schema:

```json
{
  "source_sha256": "replace-with-the-video-hash",
  "split": "ACCEPTANCE",
  "tuning_source_sha256": [],
  "frames": [{"frame_id": 10, "lamps": [{
    "lamp_id": "overhead-straight",
    "bbox_xyxy": [100, 40, 120, 90],
    "state": "RED",
    "stop_line_id": "optional-known-line"
  }]}],
  "transitions": [{
    "track_id": "capture-segment:lamp-1",
    "state": "GREEN",
    "interval_seconds": [5.1, 5.2]
  }]
}
```

```powershell
python -m greenwave.vision_validation --capture data/derived/vision-capture/CAPTURE_ID --labels C:/path/labels.json --output data/derived/validation/report.json
```

The report covers matched/missed lamps, state correctness, matched false GREEN,
unmatched green predictions, UNKNOWN, identity switches, assignment absence/error
where assignment data exists, transition interval error, inference p50/p95,
host processing age and sampled peak process memory. Sensor exposure/buffering
latency is not measured by host processing age.
Raw detector tracks are unassigned: do not interpret their missing line IDs as
validated association accuracy. Source hashes must match. Acceptance material
cannot reuse a video listed as tuning data. Split entire clips, not adjacent
frames. The report never automatically declares road quality accepted.

Day/night, reflections, tiny lamps, occlusions, red-yellow, arrows and multiple
intersections need separate real cases. The current candidate model still lacks
some states/pictograms; UI completeness does not resolve those model limitations.

## Verification commands

```powershell
python -m unittest discover -s tests -q
node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs
.venv-cv/Scripts/python.exe -m scripts.check_capture
.venv-cv/Scripts/python.exe -m scripts.check_tracking
```

Browser scripts use `GW_PLAYWRIGHT_MODULE` and a dedicated `GW_TEST_URL`.
`check_workbench.cjs` uses a 20-second repeated-still MJPEG clip at
`data/derived/workbench-smoke.avi`. It tests real inference, manual assignment,
historical isolation, durable review, export, event seek and phone layouts.
This technical clip is not a road-quality dataset.

## First field run (still to be performed)

1. On the computer, verify the chosen route/stop lines and start the server.
2. Connect/pair native phone GPS; verify FRESH, increasing samples and zero queue.
3. Check the browser UI on the phone and that the native sender continues sending.
4. Start GPS recording and note its run ID.
5. Mount the camera, start camera capture with YOLO, and check a fresh image.
   Starting it after GPS recording links the active run ID in its manifest.
6. Passenger assigns relevant lamp tracks and independently marks manual colors.
   After loss of continuity, reassign explicitly. CV operates as a diagnostic.
7. Include a stop, normal driving and another stop. Keep a record of disconnects,
   wrong assignments, false GREEN, missed lamps and bad timing.
8. Finish camera capture, then GPS recording. Note both IDs, route/direction and
   test start/end. Check both recordings complete and hashes available.
9. Review clips and passenger observations offline. Accept road performance only
   after those comparisons; prediction/learning work continues separately in M8.
