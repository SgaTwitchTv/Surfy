# Step 5 — camera/video capture and replay

Implemented on `codex/vision-camera`, including the step-4 UI. No inference,
color classification, tracking, assignment to stop lines, or solver input yet.

## Run

From the repository's `.worktrees/vision-camera` directory:

```powershell
python -m greenwave --no-browser --port 8767
```

Open `http://127.0.0.1:8767`, then **Laboratorium**.
The server automatically uses this worktree's `.venv-cv/Scripts/python.exe`
for capture. If OpenCV is installed elsewhere:

```powershell
python -m greenwave --no-browser --port 8767 --vision-python C:\path\to\python.exe
```

1. Choose `FILE` and enter the absolute local movie path, or choose `CAMERA`
   and enter a camera index (usually 0; try 1 for an additional USB camera).
2. Click **Uruchom podgląd i zapis**. Camera permission in Windows must allow desktop apps.
3. Expect `RUNNING`, increasing frame count, current dimensions, frame age and image.
   Requested resolution/FPS may differ from what the camera delivers; frame DTOs
   and the manifest contain actual dimensions. Recorded camera FPS is the reported
   nominal value, falling back to the requested FPS.
4. Switching tabs keeps capture running. Click **Zatrzymaj zapis** to finish files.
5. Refresh recordings; replay a complete recording's segment with its button.
6. For a physical USB-camera test, disconnect it while recording. Expect
   `RECONNECTING` and disappearance of the image. Reconnect; expect `RUNNING`
   with a new segment. Stop and check the recording is complete.

Phone/GPS is not needed for this first camera test. No camera starts automatically.
Avoid selecting an existing user server's port. A movie must be readable by the
computer, not a phone-local path or remote URL.

## Storage and timing

Ignored local directory: `data/derived/vision-capture/<capture UUID>/`.
It contains configuration, worker log, manifest, separate original video artifacts,
`frames.jsonl`, and up to 32 bounded preview JPEGs. Camera recordings use MJPEG AVI;
file input is copied before decoding. Completed artifacts carry SHA-256 hashes;
replay verifies the copied bytes in its worker and creates a separate capture UUID.
Files are retained until the user removes them; capture needs sufficient disk space.

Each frame records a global ID, segment-specific session, encoded frame index,
dimensions, host monotonic timestamp, UTC and media PTS. Host timestamps are taken
after `read()`: they are **not calibrated sensor exposure timestamps**. The one-second
uncertainty is an assumption, not a measured accuracy. Camera PTS is nominal encoded
frame time; actual spacing must be read from the journal. File PTS is the decoder's
reported value, with unavailable values marked explicitly. Replay generates new
host clocks; original capture timing remains in the original frame journal.
No automatic synchronization or fusion with historical GPS is performed.

The optional current run ID links the recording to an active GPS log; it does not
prove temporal synchronization. Raw GPS logs and observation events stay unchanged.

OpenCV runs in a separate process. Its preview queue holds one image and replaces
old frames; the preview is JPEG-encoded at most 10 Hz. Every successfully read frame
is recorded in the frame journal regardless of preview drops. Reconnects close the
old video segment and create a new one, so a future tracker must reset across them.
Frames older than two seconds are not shown as fresh. Capture status and video
access require the local application token; control also requires the app session.

Stopping signals the worker. A blocked capture gets terminated after three seconds
and remains incomplete. Normal finalization may need longer to hash large files.
Closing the server uses a bounded shutdown and can leave an incomplete recording;
finish capture explicitly before closing the server.

## Validation

```powershell
python -m unittest discover -s tests -q
node --test tests/driver_ui.cjs
.venv-cv/Scripts/python.exe -m scripts.check_capture
```

The decoder smoke test makes its own local synthetic movie and checks frame count,
frame IDs, hashes, bounded preview storage, stop, replay and checksum rejection.
Unit tests mock a camera disconnect/reconnect, asserting independent segment clocks
and preserved frame references. A physical camera and Windows device unplug behavior
still need manual validation.

For browser checks, point `GW_PLAYWRIGHT_MODULE` at an installed Playwright module,
start the dedicated test server, and set `GW_TEST_URL` to its address. The script
`scripts/check_capture.cjs` expects a six-second MJPEG test clip at
`data/derived/vision-capture-smoke.avi`; it starts only file playback. Existing
`check_driver_ui.cjs` and `check_web.cjs` cover UI/navigation regressions.
