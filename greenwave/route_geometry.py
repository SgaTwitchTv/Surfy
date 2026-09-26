"""Versioned, signal-independent route geometry for local map matching."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re


EARTH_RADIUS_M = 6_371_008.8
ROUTE_ID = re.compile(r'^[A-Za-z0-9._-]{1,80}$')
VERIFICATION_STATES = {'DRAFT', 'DESK_CHECKED', 'FIELD_CHECKED'}


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)


def _coordinate(value, name='coordinate'):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f'{name} must be [longitude, latitude]')
    longitude, latitude = _finite(value[0], f'{name} longitude'), _finite(value[1], f'{name} latitude')
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise ValueError(f'{name} is outside WGS84 bounds')
    return longitude, latitude


def _verification(value, name):
    if not isinstance(value, dict) or value.get('status') not in VERIFICATION_STATES:
        raise ValueError(f'{name}.status must be DRAFT, DESK_CHECKED or FIELD_CHECKED')
    return dict(value)


@dataclass(frozen=True)
class RouteProjection:
    segment_index: int
    s_m: float
    latitude: float
    longitude: float
    cross_track_m: float
    segment_heading_deg: float
    t: float


@dataclass(frozen=True)
class StopLine:
    stop_line_id: str
    signal_id: str | None
    segment_index: int
    coordinates: tuple[tuple[float, float], tuple[float, float]]
    direction: str
    movement: str | None
    source: dict
    verification: dict
    position_uncertainty_m: float
    s_m: float


@dataclass(frozen=True)
class RouteGeometry:
    route_id: str
    geometry_version: str
    name: str
    direction_description: str
    coordinates: tuple[tuple[float, float], ...]
    source: dict
    geometry_verification: dict
    speed_sections: tuple[dict, ...]
    stop_lines: tuple[StopLine, ...]
    geometry_hash: str
    origin_longitude: float
    origin_latitude: float
    xy: tuple[tuple[float, float], ...]
    cumulative_s_m: tuple[float, ...]

    @property
    def length_m(self):
        return self.cumulative_s_m[-1]

    @property
    def segment_count(self):
        return len(self.coordinates) - 1

    def to_xy(self, longitude, latitude):
        longitude, latitude = _coordinate((longitude, latitude))
        lat0 = math.radians(self.origin_latitude)
        return (EARTH_RADIUS_M * math.cos(lat0) * math.radians(longitude - self.origin_longitude),
                EARTH_RADIUS_M * math.radians(latitude - self.origin_latitude))

    def to_wgs84(self, x, y):
        latitude = self.origin_latitude + math.degrees(y / EARTH_RADIUS_M)
        longitude = self.origin_longitude + math.degrees(x / (EARTH_RADIUS_M * math.cos(math.radians(self.origin_latitude))))
        return longitude, latitude

    def project(self, longitude, latitude, *, max_distance_m=None):
        x, y = self.to_xy(longitude, latitude)
        results = []
        for index, ((ax, ay), (bx, by)) in enumerate(zip(self.xy, self.xy[1:])):
            dx, dy = bx - ax, by - ay
            length_squared = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length_squared))
            px, py = ax + t * dx, ay + t * dy
            distance = math.hypot(x - px, y - py)
            if max_distance_m is not None and distance > max_distance_m:
                continue
            projected_lon, projected_lat = self.to_wgs84(px, py)
            heading = (math.degrees(math.atan2(dx, dy)) + 360) % 360
            results.append(RouteProjection(
                segment_index=index,
                s_m=self.cumulative_s_m[index] + t * math.sqrt(length_squared),
                latitude=projected_lat, longitude=projected_lon,
                cross_track_m=distance, segment_heading_deg=heading, t=t))
        return tuple(sorted(results, key=lambda item: (item.cross_track_m, item.segment_index)))

    def public_dict(self):
        return dict(route_id=self.route_id, geometry_version=self.geometry_version,
                    name=self.name, direction_description=self.direction_description,
                    coordinates=self.coordinates, source=self.source,
                    geometry_verification=self.geometry_verification,
                    speed_sections=self.speed_sections,
                    stop_lines=[asdict(item) for item in self.stop_lines],
                    geometry_hash=self.geometry_hash, length_m=self.length_m,
                    segment_count=self.segment_count)


def _line_intersection_s(route, segment_index, line):
    """Return intersection/projection s and distance from line to route segment."""
    ax, ay = route.xy[segment_index]
    bx, by = route.xy[segment_index + 1]
    c = route.to_xy(*line[0]); d = route.to_xy(*line[1])
    rx, ry = bx - ax, by - ay
    sx, sy = d[0] - c[0], d[1] - c[1]
    cross = rx * sy - ry * sx
    if abs(cross) > 1e-9:
        qx, qy = c[0] - ax, c[1] - ay
        t = (qx * sy - qy * sx) / cross
        u = (qx * ry - qy * rx) / cross
        if 0 <= t <= 1 and 0 <= u <= 1:
            return route.cumulative_s_m[segment_index] + t * math.hypot(rx, ry), 0.0
    candidates = []
    for point in line:
        projection = min((p for p in route.project(*point) if p.segment_index == segment_index),
                         key=lambda p: p.cross_track_m)
        candidates.append(projection)
    best = min(candidates, key=lambda p: p.cross_track_m)
    return best.s_m, best.cross_track_m


def load_route(path):
    path = Path(path)
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or raw.get('schema_version') != 1:
        raise ValueError('Route schema_version must be 1')
    route_id = raw.get('route_id')
    if not isinstance(route_id, str) or not ROUTE_ID.fullmatch(route_id):
        raise ValueError('Invalid route_id')
    for name in ('geometry_version', 'name', 'direction_description'):
        if not isinstance(raw.get(name), str) or not raw[name].strip():
            raise ValueError(f'{name} must be a non-empty string')
    if not isinstance(raw.get('source'), dict) or not raw['source'].get('attribution'):
        raise ValueError('source with attribution is required')
    verification = _verification(raw.get('geometry_verification'), 'geometry_verification')
    values = raw.get('coordinates')
    if not isinstance(values, list) or len(values) < 2:
        raise ValueError('Route requires at least two coordinates')
    coordinates = tuple(_coordinate(value, f'coordinates[{index}]') for index, value in enumerate(values))
    if any(a == b for a, b in zip(coordinates, coordinates[1:])):
        raise ValueError('Consecutive route coordinates must be different')

    origin_longitude, origin_latitude = coordinates[0]
    lat0 = math.radians(origin_latitude)
    xy = tuple((EARTH_RADIUS_M * math.cos(lat0) * math.radians(lon - origin_longitude),
                EARTH_RADIUS_M * math.radians(lat - origin_latitude)) for lon, lat in coordinates)
    if max(math.hypot(x, y) for x, y in xy) > 30_000:
        raise ValueError('Route extent exceeds the supported 30 km local projection')
    cumulative = [0.0]
    for first, second in zip(xy, xy[1:]):
        length = math.dist(first, second)
        if length <= 0:
            raise ValueError('Route segment must have positive length')
        cumulative.append(cumulative[-1] + length)

    speed_sections = raw.get('speed_sections', [])
    if not isinstance(speed_sections, list):
        raise ValueError('speed_sections must be a list')
    normalized_sections = []
    for index, section in enumerate(speed_sections):
        if not isinstance(section, dict):
            raise ValueError(f'speed_sections[{index}] must be an object')
        start = _finite(section.get('start_s_m'), 'start_s_m')
        end = _finite(section.get('end_s_m'), 'end_s_m')
        limit = _finite(section.get('limit_mps'), 'limit_mps')
        if not 0 <= start < end <= cumulative[-1] or limit <= 0:
            raise ValueError(f'Invalid speed_sections[{index}] range or limit')
        if not isinstance(section.get('source'), dict):
            raise ValueError('Speed section requires source and verification')
        section_verification = _verification(section.get('verification'), f'speed_sections[{index}].verification')
        normalized_sections.append(dict(section, start_s_m=start, end_s_m=end, limit_mps=limit,
                                        verification=section_verification))
    normalized_sections.sort(key=lambda item: item['start_s_m'])
    if any(current['start_s_m'] < previous['end_s_m']
           for previous, current in zip(normalized_sections, normalized_sections[1:])):
        raise ValueError('speed_sections must not overlap')

    canonical = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    route = RouteGeometry(route_id, raw['geometry_version'], raw['name'], raw['direction_description'],
                          coordinates, dict(raw['source']), verification, tuple(normalized_sections), (),
                          hashlib.sha256(canonical.encode('utf-8')).hexdigest(), origin_longitude,
                          origin_latitude, xy, tuple(cumulative))
    stop_lines = []
    seen = set()
    for index, item in enumerate(raw.get('stop_lines', [])):
        if not isinstance(item, dict):
            raise ValueError(f'stop_lines[{index}] must be an object')
        stop_id = item.get('stop_line_id')
        if not isinstance(stop_id, str) or not ROUTE_ID.fullmatch(stop_id) or stop_id in seen:
            raise ValueError('Stop-line IDs must be unique valid identifiers')
        seen.add(stop_id)
        segment = item.get('segment_index')
        if isinstance(segment, bool) or not isinstance(segment, int) or not 0 <= segment < route.segment_count:
            raise ValueError(f'Invalid segment_index for {stop_id}')
        line_raw = item.get('coordinates')
        if not isinstance(line_raw, list) or len(line_raw) != 2:
            raise ValueError(f'{stop_id} requires two line coordinates')
        line = tuple(_coordinate(value, f'{stop_id} coordinate') for value in line_raw)
        uncertainty = _finite(item.get('position_uncertainty_m'), 'position_uncertainty_m')
        if uncertainty < 0:
            raise ValueError('position_uncertainty_m must be non-negative')
        signal_id = item.get('signal_id')
        if signal_id is not None and (not isinstance(signal_id, str) or not ROUTE_ID.fullmatch(signal_id)):
            raise ValueError(f'Invalid signal_id for {stop_id}')
        direction = item.get('direction', 'FORWARD')
        if direction not in ('FORWARD', 'REVERSE'):
            raise ValueError(f'Invalid direction for {stop_id}')
        movement = item.get('movement')
        if movement is not None and (not isinstance(movement, str) or not movement.strip()):
            raise ValueError(f'Invalid movement for {stop_id}')
        if not isinstance(item.get('source'), dict) or not item['source']:
            raise ValueError(f'{stop_id} requires a source')
        s_m, offset = _line_intersection_s(route, segment, line)
        tolerance = max(uncertainty, 5.0)
        if offset > tolerance:
            raise ValueError(f'{stop_id} is {offset:.1f} m from its assigned segment')
        stop_lines.append(StopLine(
            stop_id, signal_id, segment, line,
            direction, movement,
            dict(item.get('source') or {}), _verification(item.get('verification'), f'{stop_id}.verification'),
            uncertainty, s_m))
    return RouteGeometry(**{**route.__dict__, 'stop_lines': tuple(sorted(stop_lines, key=lambda line: line.s_m))})


class RouteRegistry:
    def __init__(self, root):
        self.root = Path(root)

    def list(self):
        if not self.root.exists():
            return []
        routes = []
        for path in sorted(self.root.glob('*.json')):
            try:
                route = load_route(path)
                routes.append(dict(route_id=route.route_id, geometry_version=route.geometry_version,
                                   name=route.name, direction_description=route.direction_description,
                                   geometry_verification=route.geometry_verification,
                                   geometry_hash=route.geometry_hash, length_m=route.length_m,
                                   stop_line_count=len(route.stop_lines), status='OK'))
            except (OSError, ValueError, json.JSONDecodeError) as error:
                routes.append(dict(route_id=path.stem, name=path.stem, status='DAMAGED', error=str(error)))
        return routes

    def load(self, route_id):
        if not isinstance(route_id, str) or not ROUTE_ID.fullmatch(route_id):
            raise ValueError('Invalid route ID')
        path = self.root / f'{route_id}.json'
        if path.resolve().parent != self.root.resolve() or not path.is_file():
            raise ValueError('Route not found')
        route = load_route(path)
        if route.route_id != route_id:
            raise ValueError('Route filename and route_id differ')
        return route

    def for_recording(self, run_id):
        """Find an explicitly sourced route; never infer from nearby GPS alone."""
        if not isinstance(run_id, str) or not re.fullmatch(r'[0-9a-f]{32}', run_id):
            return None
        for entry in self.list():
            if entry['status'] != 'OK':
                continue
            route = self.load(entry['route_id'])
            if route.source.get('run_id') == run_id:
                return route
        return None
