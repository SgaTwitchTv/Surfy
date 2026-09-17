# GreenWave (Surfy repository)

GreenWave is a local laboratory for developing a mobile application that helps
users catch a green wave. The project currently includes a map, traffic-light
observations, prediction and resynchronization, multi-signal route planning with
vehicle dynamics, a cost model for stops, braking, acceleration changes, travel
time and risk, an append-only raw trip logger, and diagnostic GPS reception from
a phone.

## Running the application

GreenWave requires Python 3.11 or newer and has no pip dependencies:

```powershell
python -m greenwave
```

The application opens in a browser at `http://127.0.0.1:8765`. The server binds
to the local computer only. Press Ctrl+C in the terminal to stop it. If the port
is already occupied, run `python -m greenwave --port 8766` or use `--port 0` to
select a free port automatically. The `--no-browser` option starts the server
without opening a browser. The map, styles and scripts are stored locally, so no
internet connection or map API key is required.

The legacy P02 Tkinter panel is available through:

```powershell
python -m greenwave --lab
```

This panel remains a historical M1/P02 tool. The current map and M2 features are
available in the browser interface. Tkinter requires a local Tcl/Tk installation.

## Quick M4 desktop test

Leave **Jedź według rekomendacji** (“Follow the recommendation”) enabled, set the
simulation rate to 5× or 10×, and click **Start**. The vehicle starts from rest,
accelerates within the model limits and follows the recommended target. The large
number is the target speed; the smaller number is the vehicle's current speed. M4
shows one target range, for example 34–34 km/h, validated against the complete
selected trajectory.

Disable automatic following to set a target speed manually with the slider. A
slider change does not cause an instantaneous speed jump. The simulated driver
also reacts to a non-green signal in this mode.

The **Plan korytarza — trajektoria i koszt** (“Corridor plan — trajectory and
cost”) section shows the plan for the upcoming signals, predicted stops, cost
components, alternatives and a comparison with the local-choice baseline. Below
it are the first command profile and the list of crossed stop lines. If no feasible
profile or valid prediction exists, GreenWave removes the target value and displays
the reason. An infeasible traffic-signal situation stops the simulation and requires
a new session without relocating the vehicle.

M2 observations and diagnostics can be tested as follows:

1. Keep **S1–S5 · dane syntetyczne** (“synthetic data”) selected, click **Start**,
   and then click **Pauza** (“Pause”).
2. Select S3 in the list or on the map. Choose **Właśnie zaczęła się faza** (“The
   phase has just started”) and **Zielone teraz** (“Green now”). The S3 prediction
   windows will change. Other signal models are not shifted automatically.
3. Open **Diagnostyka prognoz i modelu** (“Prediction and model diagnostics”) and
   compare the offset, correction and source.
4. Select S1 and report the start of a phase. The demo configuration contains
   explicit S1→S2–S5 relationships. Downstream predictions are corrected unless a
   newer direct observation of a signal takes precedence.
5. **Widzę ten kolor teraz** (“I see this colour now”) records the currently visible
   colour without inventing the start time of the phase. A contradiction with the
   model suspends its prediction until the next resynchronization.
6. The diagnostics panel can enable timing jitter and green extensions for a new
   session. The simulator's ground truth remains independent of the prediction.
7. Select the unverified Warsaw dataset. Its phases remain `UNKNOWN`, and position
   markers are disabled. **GREEN NOW** records an observation but does not invent a
   cycle.

The map supports panning, zooming and fitting the complete route. Probe position
and signal colours update during the simulation. By default, M4 analyses up to five
upcoming signals using test data. This stage is a research tool, not a road-driving
advisor.

M5 records a trip through the **Rozpocznij nagranie** (“Start recording”) button.
Files are written to `data/runs/<run_id>/`, and the recordings section can export a
completed run as a ZIP archive. Replay and seeking belong to M6.

In **Replay nagrania** (“Replay recording”), select a completed run, load it, choose
a playback rate from 1× to 10×, play or pause it, and seek with the slider. Replay is
independent of the current simulation.

The **Analiza przejazdu i jakości GPS** (“Trip and GPS quality analysis”) section
calculates metrics from a completed CSV file. Its report covers sample frequency
and gaps, GPS accuracy, speed availability and sources, and stop-to-motion
transitions. It distinguishes gaps produced by the phone's location provider from
additional transport delays. The source file remains unchanged, and analysis
rejects a run with an invalid hash or a broken record sequence.

A phone can connect over USB through `adb reverse`. The mobile page transmits raw
location measurements, while the server evaluates their quality, calculates a
fallback speed when needed and filters stationary GPS drift. See
[docs/phone-gps.md](docs/phone-gps.md) for the complete setup and controlled-recording
procedure. A native Android transmitter and projection onto a verified real-world
corridor are the next M8 stages.

## Data and interpretation

- `data/corridors/synthetic_s1_s5.json`: test phases, distances and speed limit.
- `data/corridors/zwirki_wigury.json`: unverified inventory with unknown values set
  to `null`.
- `data/prediction/`: horizon, uncertainty, validity and explicit relationship
  settings.
- `data/maps/warsaw.json`: a local OpenStreetMap geometry extract and road segment.
- `data/solver.json`: vehicle dynamics, minimum speed, margins and stabilization.
- `data/trajectory.json`: cost weights, horizon, signal count and M4 search width.

**The S1–S5 markers are placed experimentally along the available map segment.
They are not verified Warsaw stop-line locations.** The map covers a fragment of
the road rather than the complete Wawelska-to-airport route, and the demo position
is normalized onto that fragment. Map geometry does not automatically fill missing
corridor data. The map file contains its source, retrieval date and ODbL licence
metadata. © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).

The timing margin is not a calibrated confidence interval. `confidence` remains
`null` when there is no stated basis for it. When present, it is displayed only as
a decreasing model index, not as a probability. The default model expires after
240 seconds; a new phase-start observation can renew it.

UTC records when the local server processes an observation, while a monotonic clock
controls simulation speed. Operator reaction delay is unknown. For an unverified
corridor, model time means elapsed UTC time since the start of the session and is
independent of simulation pause state.

**Observation history is stored only in server memory.** Resetting the application
preserves earlier sessions; closing a browser tab does not remove the history, but
stopping the server does. Persistent logging belongs to M5. The UI displays the 100
most recent observations.

## Tests

```powershell
python -m unittest discover -s tests -v
node tests/mobile_flow.cjs
```

The Tkinter test may be skipped when Tcl/Tk is unavailable. HTTP tests require
access to local network sockets. To run the browser scenario:

```powershell
python -m greenwave --no-browser --port 8766
# In a second terminal; Playwright and Edge are required only for this test:
$env:GW_TEST_URL = 'http://127.0.0.1:8766'
node scripts/check_web.cjs
```

Playwright must be available as a Node module or specified through
`GW_PLAYWRIGHT_MODULE`. The scenario changes the active session, so run it against
a separate server. Screenshots are written to the Git-ignored
`artifacts/web-check` directory.

## Documentation

- Architecture: [docs/architecture.md](docs/architecture.md)
- M2 contract and acceptance criteria: [docs/m2.md](docs/m2.md)
- M3 profiles, constraints and tests: [docs/m3.md](docs/m3.md)
- P07/P08 search details and limitations: [docs/m4.md](docs/m4.md)
- L09 logger: [docs/m5.md](docs/m5.md)
- Replay: [docs/m6.md](docs/m6.md)
- M7 data analysis: [docs/m7.md](docs/m7.md)
