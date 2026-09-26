"""Build local draft Radom routes from the two controlled GPS recordings.

The generated routes are for map-matching diagnostics only. They do not assert
road centreline, lane, stop-line, speed-limit, or phase verification.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'data' / 'runs'
ROUTES = ROOT / 'data' / 'routes'
EARTH_RADIUS_M = 6_371_008.8
SOURCES = (
    ('radom_limanowskiego_25_czerwca_draft',
     '7aa31a9922424dc4b2d6737581cc856d',
     'Radom: Limanowskiego/Maratońska → rondo 25 Czerwca/Prażmowskiego',
     'Od skrzyżowania Limanowskiego/Maratońska do ronda 25 Czerwca/Prażmowskiego.'),
    ('radom_25_czerwca_limanowskiego_draft',
     'fab1831c4aa2493abf6cc114cc342222',
     'Radom: rondo 25 Czerwca/Prażmowskiego → Limanowskiego/Maratońska',
     'Od ronda 25 Czerwca/Prażmowskiego do skrzyżowania Limanowskiego/Maratońska.'),
)


def _samples(run_id):
    run_dir = RUNS / run_id
    manifest = json.loads((run_dir / 'complete.json').read_text(encoding='utf-8'))
    for filename in ('metadata.json', 'raw.csv'):
        actual = hashlib.sha256((run_dir / filename).read_bytes()).hexdigest()
        if actual != manifest['sha256'][filename]:
            raise ValueError(f'{run_id}: {filename} fails source checksum')
    with (run_dir / 'raw.csv').open(encoding='utf-8', newline='') as source:
        rows = csv.DictReader(source)
        samples = []
        for row in rows:
            if row['event'] != 'EXTERNAL_TELEMETRY':
                continue
            try:
                lon, lat = float(row['longitude']), float(row['latitude'])
                accuracy = float(row['gps_accuracy'])
                speed = float(row['speed_mps'])
            except (ValueError, TypeError):
                continue
            if math.isfinite(lon) and math.isfinite(lat) and math.isfinite(accuracy) and accuracy <= 15:
                samples.append((lon, lat, speed))
    if len(samples) < 20:
        raise ValueError(f'{run_id}: too few accurate GPS samples')
    return samples


def _xy(point, origin):
    lon, lat = point
    return (EARTH_RADIUS_M * math.cos(math.radians(origin[1])) * math.radians(lon - origin[0]),
            EARTH_RADIUS_M * math.radians(lat - origin[1]))


def _distance_to_segment(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy
    t = 0 if length_sq == 0 else max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length_sq))
    return math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy)


def _simplify(points, tolerance_m):
    origin = points[0]
    projected = [_xy(point, origin) for point in points]
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        start, end = pending.pop()
        if end - start < 2:
            continue
        distance, index = max(
            (_distance_to_segment(projected[i], projected[start], projected[end]), i)
            for i in range(start + 1, end))
        if distance > tolerance_m:
            keep.add(index)
            pending.extend(((start, index), (index, end)))
    return [points[index] for index in sorted(keep)]


def build(spec):
    route_id, run_id, name, direction = spec
    samples = _samples(run_id)
    # Ignore stationary GPS wandering when constructing the route. Preserve the
    # first and last fixes as recording boundaries, not verified stop lines.
    moving = [sample[:2] for sample in samples if sample[2] >= 2.0]
    if len(moving) < 20:
        raise ValueError(f'{run_id}: too few moving samples')
    points = [samples[0][:2], *moving, samples[-1][:2]]
    smoothed = [
        (median(point[0] for point in points[max(0, i - 2):min(len(points), i + 3)]),
         median(point[1] for point in points[max(0, i - 2):min(len(points), i + 3)]))
        for i in range(len(points))
    ]
    smoothed[0], smoothed[-1] = points[0], points[-1]
    simplified = _simplify(smoothed, 7.0)
    coordinates = []
    for lon, lat in simplified:
        point = [round(lon, 7), round(lat, 7)]
        if not coordinates or coordinates[-1] != point:
            coordinates.append(point)
    if len(coordinates) < 2:
        raise ValueError(f'{run_id}: route collapsed')
    return {
        'schema_version': 1,
        'route_id': route_id,
        'geometry_version': 'gps-draft-2026-09-22-v1',
        'name': name,
        'direction_description': direction,
        'coordinates': coordinates,
        'source': {
            'kind': 'LOCAL_GPS_TRACE',
            'run_id': run_id,
            'obtained_on': '2026-09-22',
            'attribution': 'Prywatny pomiar GreenWave — Android Fused Location Provider',
            'notes': 'Mediana 5 punktów i uproszczenie 7 m; ślad nie jest osią jezdni ani geometrią pasa.'
        },
        'geometry_verification': {
            'status': 'DRAFT',
            'date': '2026-09-23',
            'notes': 'Do diagnostyki replay i map matchingu; wymaga porównania z podkładem ulic i sprawdzenia w terenie.'
        },
        'speed_sections': [],
        'stop_lines': []
    }


def main():
    ROUTES.mkdir(parents=True, exist_ok=True)
    for spec in SOURCES:
        route = build(spec)
        path = ROUTES / f'{route["route_id"]}.json'
        path.write_text(json.dumps(route, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'{path.name}: {len(route["coordinates"])} points')


if __name__ == '__main__':
    main()
