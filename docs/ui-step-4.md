# Step 4 — navigation UI and laboratory

Implemented on `codex/ui-desktop`. The main checkout and Android sensor are
unchanged. This is the responsive web frontend: no new APK is needed for UI.

## Screens

- **UI**: vehicle-following, heading-oriented perspective over the existing
  offline OSM geometry; stop-line icons and labels; segmented curved speedometer,
  recommended speed band and large acceleration/hold/deceleration cue.
- **Nawigacja**: the existing flat map, signal selection and manual observations.
- **Laboratorium**: phone/matcher diagnostics, history, recording analysis and
  nine synthetic vision-contract scenarios. The preview shows synthetic boxes,
  never claims that a real camera or tracker is connected.

Session/source controls remain shared, under **Sesja i źródło danych**. Selecting
a screen never resets the run, starts/stops a recording or changes driving mode.
This is a 2.5D rendering of the existing map, not Google Maps or 3D buildings.
Street data, routes and points are not replaced with a schematic fixture.

## Recommendations and sources

The display consumes the existing backend recommendation. Live instructions
require the backend eligibility gate, a fresh usable sample, finite speed,
known verified limit and a valid READY recommendation within that limit.
GPS replay never produces live instructions. A missing/stale HTTP stream
withdraws speed and instructions after 1.5 seconds, independently of GPS gating.
That UI timeout is a provisional display policy, not a GNSS freshness criterion.

Red speed zones lie outside the returned band, green inside it. A point target
has a green marker instead of an invented wider band. The scale follows the
limit and is not an authorization to exceed it. Near-edge cues use provisional
0.8 km/h entry and 1.5 km/h release margins; narrow bands use smaller deadbands.
Backend braking/coasting/stopping takes precedence over acceleration cues.
Changing session, mode, route geometry or speed band resets cue hysteresis.

Simulation is prominently identified as synthetic. In live/replay, lamp state
is UNKNOWN: previous manual clicks are labeled as history, not current phases.
Stop-line geometry alone does not identify an individual lamp. Camera/API live
state adapters and automatic association remain later steps. Their mock data
never enters the solver or observation logger. Missing GPS shows route geometry
without a vehicle marker; stale position is explicitly diagnostic.

The passenger buttons reuse the existing observation endpoints and selection.
STATE_SEEN versus STATE_START remains explicit. Screen changes do not silently
change this event type or select a new line while recording.

## Run

From the main repository directory:

```powershell
Set-Location .worktrees/ui-desktop
python -m greenwave --no-browser --port 8766
```

Open `http://127.0.0.1:8766/`. Port 8766 separates the prototype from an existing
8765 measurement server. This checkout has its own local recordings directory;
private main-checkout recordings have not been copied or modified.
For normal USB tests, use the chosen server port and pair the Android sender
with that server; the earlier server's pairing token is not interchangeable.

## Verification

- Python suite: 195 tests, OK, one environment-dependent test skipped.
- `node --test tests/driver_ui.cjs`: six tests covering invalid inputs, stale
  eligibility, limit boundaries, hysteresis, braking priority and projection.
- `scripts/check_driver_ui.cjs`: Edge browser, light/dark, 1360/390/320 px,
  observations, nine vision scenarios, replay/live gating and interrupted HTTP.
- `scripts/check_web.cjs`: existing navigation/control/history/solver regression.

Browser checks require Playwright plus Edge, and **a dedicated synthetic test
server**, because they change simulated observations. Set `GW_TEST_URL` to its
address and `GW_PLAYWRIGHT_MODULE` if Playwright is installed outside this repo.
Screenshots are local under ignored `artifacts/driver-ui` and `artifacts/web-check`.
No external map requests occur. Actual phone service lifecycle, USB camera,
day/night recognition and a moving-road acceptance test remain separate checks.
