# Camera/model feasibility probe

This experiment lives on `codex/vision-camera`. The application itself remains
free of ML dependencies. `greenwave.vision_probe` imports them only when the
standalone probe is run. No detections are sent into live recommendations.

## Hardware and candidate

Host: Snapdragon X1E80100 ARM64, Adreno X1-85 GPU. Current Python 3.14.4 and
selected experiment wheels are AMD64, so this is an x64 CPU experiment on a
Windows ARM64 computer. Neither GPU nor NPU acceleration is claimed.

Candidate: YOLOv8 nano from
https://github.com/Syazvinski/Traffic-Light-Detection-Color-Classification
at commit `c2c5bfcad8bb6f168712426fa071022e3b8832cb`.
Weight SHA-256:
`6b7fc4adf8af46500d10666d7c5917b3a98a627353b8aa07bbe4155f04f172bb`.
Published classes: red, green, off, yellow. RED_YELLOW and pictograms are
missing. This is a candidate for feasibility testing, not a production model.

No explicit repository license was found for these weights. They remain local
evaluation assets outside Git; production redistribution is unresolved.
Ultralytics package licensing is documented at https://www.ultralytics.com/license.
KASTEL's larger models and state/pictogram taxonomy remain alternatives:
https://github.com/KASTEL-MobilityLab/traffic-light-detection.

The unannotated public example is KASTEL's `red-yellow.jpg`, pinned by commit
and SHA in the preparation script. The source repository is AGPL-3.0. This
single image is not an independent road-validation set. The other downloaded
example already contains prediction overlays and is not used as ground truth.

## Reproduction from the feature worktree

```powershell
python -m venv .venv-cv
.\.venv-cv\Scripts\python.exe -m pip install -r requirements-vision.txt
python tools/prepare_vision_probe.py
.\.venv-cv\Scripts\python.exe -m greenwave.vision_probe --weights data/derived/vision-probe/best_traffic_nano_yolo.pt --source data/derived/vision-probe/red-yellow.jpg --labels data/vision-probe-labels.json --repeat 10 --imgsz 640
```

Use a local film instead of the JPG with `--source C:/path/to/film.mp4
--max-frames 60`. Use `--source camera:0 --max-frames 60` for a chosen camera.
Camera testing is opt-in; the experiment does not automatically open the
Surface camera. No phone or running GreenWave server is needed.

Each run creates a new local output directory with a report, JSONL detections
and an annotated first image. It records source/model hashes, class names,
configuration, package versions, CPU threads, inference p50/p95, frame age and
sampled process RSS. Still-image repetitions measure performance, not recall.
Reported inference FPS excludes decoding, annotation and disk writes; it is
not measured end-to-end camera FPS. Large source videos are hashed in chunks.
The optional labels are manually estimated boxes for this public image only.
The comparison matches boxes by IoU before comparing state and reports misses,
unmatched predictions and matched false greens separately.

Bounding boxes use original-frame pixels. Low-score or tiny boxes become
UNKNOWN. The defaults (.5 state score, 12 px height, 4 px width) are provisional
experimental filters, not calibrated safety thresholds. Raw model score stays
available in every DTO; the annotation uses the filtered state.

## Time and current boundaries

Frame UTC/monotonic timestamps represent host dequeue/processing estimates.
Video PTS is retained separately. They are not original road-capture timestamps
and must not be fused with historic GPS as synchronized observations. The
clock uncertainty parameter is an assumption, not measured sensor latency.
Warmup is excluded from measured inference latency; the first source frame
is reused for warmup in this feasibility tool.

There is no tracker, state-change emitter, route association or phase learning
in this step. Detections have no track identity until a tracker is implemented.
State support gaps are explicit in the report. A nano model detecting a lamp
does not prove it can distinguish red-yellow, arrows, distant lights or night
conditions. Those need a suitable model and labeled validation data.

## Measured host results — 2026-09-26

CPU, four PyTorch threads, Python 3.14.4 AMD64, torch 2.9.1+cpu,
Ultralytics 8.3.199, OpenCV 4.11.0. Same public 3960x2475 image,
warmup excluded. These short runs are a feasibility smoke test, not sustained
camera throughput or a controlled independent accuracy benchmark.

| Input size | Measured frames | Inference p50 / p95 ms | Inference FPS | Sampled peak RSS MB | Per-frame filtered output |
| --- | --- | --- | --- | --- | --- |
| 640 | 10 | 57.2 / 96.2 | 15.6 | 404.8 | 1 UNKNOWN |
| 960 | 20 | 93.6 / 109.1 | 10.3 | 412.3 | 1 RED, 1 UNKNOWN |
| 1280 | 20 | 159.5 / 169.8 | 6.2 | 444.1 | 1 UNKNOWN |

Host processing-age p50/p95 was respectively 57.9/100.6, 94.3/109.9 and
160.1/170.6 ms. Sensor buffering and exposure delay are not included.
Increasing resolution did not reliably improve this candidate's detections.
Visual inspection at 960 confirms the overhead red lamp and an UNKNOWN box
around the red-yellow arrow; the other red lamp is missed. The coarse manual
labels and IoU=.5 comparison produce respectively 1/1/0 matched boxes across
640/960/1280, zero correctly scored matched states and zero matched false
greens. The overhead red at 960 falls below the geometric matching threshold.
Zero matched false greens here does not establish a false-green rate.

Local reports under `data/derived/vision-probe/`:
- `fea527b9463d45cf871beb22b6592eb1/report.json` — 640.
- `3a1f226f799b4e5bae919feaf2ffb15d/report.json` — 960.
- `89e225394e8a4ef591850edea33bc0ef/report.json` — 1280.
- `fed84ceaf3254b82a14ea3b27041d685/report.json` — video decoder smoke.

The video test uses a **synthetic repeated-still** MJPEG AVI, 15 frames at
1280x800 and nominal 5 FPS. All 15 frames were processed and EOF handled;
inference p50/p95 was 94.4/115.0 ms at input 960. This verifies file input,
frame progression and report creation, not moving-road performance or tracking.
No camera was opened. Actual USB-camera buffering, disconnects and day/night
road quality remain untested until suitable hardware/material is supplied.

## Decision and follow-up

Accept the CPU backend as a working experimental backend. Keep this weight
file as an evaluation candidate only: the example exposes misses, class gaps
and uncertain color results; its license is also unresolved.

| Approach | Current evidence | Decision |
| --- | --- | --- |
| Nano detector with built-in color classes | Executed above; four states, no arrows/red-yellow | Useful for runtime smoke; not selected for production |
| KASTEL state/pictogram model | Repository taxonomy includes red-yellow and pictograms; larger models, AGPL | Alternative to benchmark on labeled road clips |
| Detector plus crop classifier | Can separate lamp localization from richer state recognition; extra preprocessing/latency | Architectural alternative; not implemented or benchmarked in this step |

Before selecting a production model, evaluate independent day/night clips,
small lamps, red-yellow, arrows, reflections and car tail lamps; report misses,
UNKNOWN, false greens and latency separately. Hardware feasibility alone does
not satisfy that acceptance gate. UI can now develop against the shared DTOs;
actual tracking, synchronized capture and route association follow separately.

The CLI stores Ultralytics settings inside ignored experiment data, disables
automatic dependency installation and disables HUB/synchronization settings.
Weights, recordings, environment and generated reports remain outside Git.

Installation on this host repeatedly timed out on large PyPI downloads.
PyTorch was assembled from ranged official downloads and its official wheel
SHA-256 verified before installation. The inference runtime above is working;
the broader Ultralytics dependency installation is not yet complete (SciPy
and Polars). `pip check` therefore does not pass on this temporary environment.
The full reproduction command installs the declared package dependencies;
rerun it with a stable connection before treating the environment as complete
or using training/export/evaluation features beyond this standalone probe.
