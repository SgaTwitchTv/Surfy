# M8 field validation

The software and offline checks can be completed at the computer. Two physical
facts still require observation: whether the selected route follows the intended
carriageway, and where each stop line lies for the chosen movement. Keep every
route, speed section and stop line at `DRAFT` or `DESK_CHECKED` until that evidence
exists.

## Stationary phone check

1. Build and install the current debug APK from
   `android/GreenWaveSensor/app/build/outputs/apk/debug/app-debug.apk`.
2. Start GreenWave with `python -m greenwave --no-browser`. In another PowerShell
   run `adb devices` and confirm `device`, then run
   `adb reverse tcp:8765 tcp:8765`.
3. Pair the Android app with `http://localhost:8765`, start its foreground sensor
   service, and open the desktop UI at `http://127.0.0.1:8765`.
4. Select **Telefon na żywo** and initially leave **Trasa GPS** at **Bez trasy**.
   Confirm that sequence numbers grow, accuracy and speed are visible, the receipt
   age stays low, and freshness is `FRESH`.
5. Disconnect USB for more than five seconds. The desktop must show `STALE`; it
   must not retain a current matched position or target speed.
6. Reconnect, repeat `adb reverse tcp:8765 tcp:8765`, and allow the queue to drain.
   Buffered samples remain historical/stale. A new stream or fresh samples must
   reacquire mapping rather than continuing the old crossing state.
7. Record the run ID and export it. Replay it offline, seek to the same instant
   twice, and verify identical position and mapping status.

## Arkadia pilot fixed for the first drive

Use route `arkadia_maczka_okopowa_v1`, geometry
`osm-osrm-desk-2026-09-19-v1`:

- start: the lights at the left-turn area from Reymonta into Maczka,
  `52.268550, 20.932530`;
- direction: east/south-east along Generała Stanisława Maczka, through Rondo
  Ofiar Zbrodni Katyńskiej, then along Powązkowska;
- end: the straight-ahead lights at Powązkowska/Okopowa,
  `52.253278, 20.981089`, by the McDonald's/Arkadia area;
- length: approximately 3.76 km;
- the first route version does not continue to Rondo ONZ.

The route geometry and the OSM `maxspeed=50` inventory are `DESK_CHECKED`. The
speed limit must still be compared with signs. These ten candidate lines are
`DRAFT` and must be checked in this order:

1. `SL01_MACZKA_PEDESTRIAN` — crossing on Maczka before Rudnickiego;
2. `SL02_MACZKA_RUDNICKIEGO` — Maczka/Rudnickiego;
3. `SL03_RONDO_KATYNSKIE_ENTRY` — entry to Rondo Ofiar Zbrodni Katyńskiej;
4. `SL04_RONDO_KATYNSKIE_EXIT` — exit from the roundabout into Powązkowska;
5. `SL05_POWAZKOWSKA_CEMETERY` — crossing on Powązkowska by the cemetery;
6. `SL06_POWAZKOWSKA_KRASINSKIEGO` — Krasińskiego/Ficowskiego area;
7. `SL07_POWAZKOWSKA_RYDYGIERA` — Powązkowska/Rydygiera;
8. `SL08_POWAZKOWSKA_DUCHNICKA` — Powązkowska/Duchnicka;
9. `SL09_POWAZKOWSKA_TATARSKA` — Powązkowska/Tatarska;
10. `SL10_POWAZKOWSKA_OKOPOWA` — final Powązkowska/Okopowa line.

The start coordinate is the recording boundary. It is not counted as a crossing
event because the route has no accepted sample before that line. During the drive,
the passenger must confirm whether every candidate controls the intended
straight-ahead carriageway and note missing, duplicated or displaced lines.

Create a new geometry version when any ordered route coordinate, stop line or
speed section changes. Do not overwrite the evidence attached to an earlier run.

## Controlled road validation

This is a mapping test. The driver follows traffic law and does not follow a speed
recommendation from GreenWave. A passenger operates and observes the application.

1. Mount the phone with an open view of the sky, connect USB, confirm fresh samples,
   select the exact route and direction, and start a new recording.
2. Remain stationary for 30–60 seconds before the route. Note the run ID, route ID,
   geometry version and geometry hash.
3. Drive the prepared route once normally. The passenger checks that direction is
   `FORWARD`, distance to the next line generally decreases, uncertain geometry is
   shown as `UNCERTAIN`, and leaving the route removes accepted `s`.
4. At each inventoried line, the passenger notes the stop-line ID and actual pass
   time. In **Telefon na żywo**, the passenger may select that route point and use
   GREEN/YELLOW/RED to record a manual `ROUTE_OBSERVATION`; the default
   **Widzę ten kolor teraz** records a colour currently visible, while
   **Właśnie zaczęła się faza** is reserved for an actually observed change.
   These clicks do not create verified phase data or update the simulation
   prediction. Confirm the run metadata says `view_mode=LIVE`; synthetic S1–S5
   clicks are unrelated to Arkadia and must not be counted as road observations.
5. Do not interact with the UI as the driver. Do not perform an artificial exit,
   U-turn or other manoeuvre solely for the test.
6. Remain stationary for 30–60 seconds after the route and stop recording.
7. Back at the computer, replay the complete run, generate the mapping report and
   compare it with passenger notes. Check match loss/recovery, direction changes,
   gaps, confirmed and unconfirmed crossings, and source-file hash preservation.

Record the result as `PASS`, `FAIL` or `INCONCLUSIVE`. A pass applies only to this
route version, direction, tested device and observed conditions. Promote geometry,
stop lines or limits to `FIELD_CHECKED` only when the corresponding evidence was
actually observed. Verified phase data remains a separate requirement before live
speed recommendations can be enabled.
