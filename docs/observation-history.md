# Shared signal observation history

The local SQLite index at `data/derived/observation-history.sqlite3` aggregates
`ROUTE_OBSERVATION` events from completed recordings. It is rebuildable from
raw logs and separate user attestations. Synthetic simulator observations
are not imported. Private data stays under the ignored `data/derived/` tree.

Open **Historia świateł ze wszystkich przejazdów** and click
**Importuj / odśwież nagrania** after recording a trip or adding an attestation.
**Pokaż historię** reads the persistent index without reimporting. The current
**Trasa GPS** selector filters the history; **Bez trasy** shows all routes.

Import validates completion, raw SHA-256 and sequence continuity before
indexing. Each run is replaced atomically, so repeat import does not multiply
events. Invalid, removed or no longer completed source runs are removed from
the index at the next sync; errors are reported to the UI. Active recordings
are not imported. Individual observations remain identified by run ID and
raw sequence, with original payload and provenance retained.

Histories are grouped by route ID, exact geometry hash and stop-line ID.
Direction and movement are taken only from the matching geometry. Missing
or old route geometry is retained separately with unknown direction rather
than assigned current route metadata. Existing user attestations apply only
when run ID, raw hash and geometry hash match. Reimport refreshes attestations
and duplicate classifications while preserving recorded observation types.

The history stores UTC timestamp, color, recorded and reviewed event type,
source run, GPS quality/position/speed, original matcher status, verification
metadata and duplicate classification. Quick and repeated same-color clicks
remain visible. They are not silently erased or interpreted as new cycles.

API: token-protected `GET /api/observation-history?route_id=...` and
token/session-protected `POST /api/observation-history/sync`.

## Completeness inventory

Click **Raport kompletności** to summarize indexed observations for the selected
route (or all routes). Import also refreshes this report. It includes every
current stop line, even without observations, and keeps archived geometry
separate. The token-protected API is
`GET /api/observation-history/completeness?route_id=...`.

Each point reports recordings with observations, colors, witnessed starts,
seen-only colors, duplicates, unresolved repeats, freshness and measured
transition intervals. Intervals never span separate recordings or seen-only
observations. Quick duplicates do not shift the first onset; unresolved
repeats break interval evidence. GREEN-to-RED is not a green duration because
yellow may intervene. RED-to-GREEN is the observed onset-to-onset interval,
not a reconstructed separate red-yellow phase. Click reaction delay remains
unknown. Recurrence of a color after other phases is reported explicitly as
possibly spanning skipped cycles, not proof of a complete single cycle.

Statuses describe evidence only: no data, partial data or repeated intervals.
Even repeated intervals do not validate a model. Missing transition pairs,
independent runs, recurrences and field verification of geometry, lines and
speed limits are listed separately. No required sample count or statistical
accuracy threshold is invented. Statistical phase learning and live
recommendations remain subsequent steps. The report does not change the live
prediction engine or mark route geometry field-verified.
