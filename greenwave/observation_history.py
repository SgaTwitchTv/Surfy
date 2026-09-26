"""Rebuildable local SQLite index of immutable passenger observations."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from greenwave.analysis import RunAnalysis
from greenwave.observation_review import review_observations
from greenwave.observation_completeness import point_completeness


class ObservationHistory:
    def __init__(self, logger, routes, path=None):
        self.logger, self.routes = logger, routes
        self.path = Path(path) if path else logger.root.parent / 'derived' / 'observation-history.sqlite3'

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.execute('''CREATE TABLE IF NOT EXISTS observations (
            run_id TEXT NOT NULL, sequence INTEGER NOT NULL, route_id TEXT NOT NULL,
            geometry_hash TEXT NOT NULL, stop_line_id TEXT NOT NULL,
            timestamp TEXT NOT NULL, content TEXT NOT NULL,
            PRIMARY KEY(run_id, sequence))''')
        connection.execute('CREATE INDEX IF NOT EXISTS point_history ON observations(route_id, geometry_hash, stop_line_id, timestamp)')
        return connection

    def sync(self):
        imported_runs, errors = 0, []
        with closing(self._connect()) as db:
            completed = {d.name for d in self.logger.root.glob('*')
                         if d.is_dir() and (d / 'complete.json').exists()}
            with db:
                for (stored_run,) in db.execute('SELECT DISTINCT run_id FROM observations').fetchall():
                    if stored_run not in completed:
                        db.execute('DELETE FROM observations WHERE run_id=?', (stored_run,))
            for directory in sorted(self.logger.root.glob('*')):
                if not directory.is_dir() or not (directory / 'complete.json').exists():
                    continue
                run_id = directory.name
                try:
                    _, complete, rows = RunAnalysis(self.logger)._read(run_id)
                    raw_hash = complete['sha256']['raw.csv']
                    observations = [row for row in rows if row['event'] == 'ROUTE_OBSERVATION']
                    groups = {(r['payload'].get('route_id'), r['payload'].get('geometry_hash')) for r in observations}
                    entries = []
                    for route_id, geometry_hash in sorted(groups):
                        if not isinstance(route_id, str) or not isinstance(geometry_hash, str):
                            raise ValueError('Observation lacks route identity')
                        selected = [r for r in observations if (r['payload'].get('route_id'), r['payload'].get('geometry_hash')) == (route_id, geometry_hash)]
                        try:
                            route = self.routes.load(route_id)
                        except (ValueError, OSError):
                            route = None
                        exact = route is not None and route.geometry_hash == geometry_hash
                        # Unknown/old geometry stays separate; never attach current direction or movement.
                        review_route = route if exact else SimpleNamespace(route_id=route_id,
                            geometry_hash=geometry_hash, stop_lines=[SimpleNamespace(stop_line_id=key, s_m=0)
                                for key in sorted({r['payload']['stop_line_id'] for r in selected})])
                        attestation = None
                        path = self.logger.root.parent / 'derived' / 'field-review' / run_id / 'attestation.json'
                        if path.exists():
                            value = json.loads(path.read_text(encoding='utf-8'))
                            if (value.get('run_id') == run_id and value.get('source_raw_sha256') == raw_hash
                                    and value.get('geometry_hash') == geometry_hash):
                                attestation = value
                        empty_replay = SimpleNamespace(samples=[], match_history=[], detector=SimpleNamespace(events=[]))
                        review = review_observations(rows, empty_replay, review_route, attestation)
                        line_lookup = {line.stop_line_id: line for line in route.stop_lines} if exact else {}
                        for point in review['points']:
                            line = line_lookup.get(point['stop_line_id'])
                            for entry in point['observations']:
                                payload = next(r['payload'] for r in selected if r['sequence'] == entry['record_sequence'])
                                entry.update(run_id=run_id, source_raw_sha256=raw_hash, route_id=route_id,
                                    geometry_hash=geometry_hash, geometry_version=payload.get('geometry_version'),
                                    direction=None if line is None else line.direction,
                                    movement=None if line is None else line.movement,
                                    direction_description=None if not exact else route.direction_description,
                                    source=payload.get('source'), line_verification=payload.get('line_verification'),
                                    attestation=attestation, raw_observation=payload)
                                entry['timestamp'] = datetime.fromisoformat(entry['timestamp']).astimezone(timezone.utc).isoformat()
                                entries.append((run_id, entry['record_sequence'], route_id, geometry_hash,
                                    point['stop_line_id'], entry['timestamp'], json.dumps(entry, ensure_ascii=False, allow_nan=False)))
                    with db:
                        db.execute('DELETE FROM observations WHERE run_id=?', (run_id,))
                        db.executemany('INSERT INTO observations VALUES (?,?,?,?,?,?,?)', entries)
                    imported_runs += 1
                except (ValueError, OSError, KeyError, TypeError) as error:
                    # Invalid source data must not remain eligible through an old index.
                    with db:
                        db.execute('DELETE FROM observations WHERE run_id=?', (run_id,))
                    errors.append(dict(run_id=run_id, error=str(error)))
            return dict(imported_runs=imported_runs, observation_count=db.execute('SELECT COUNT(*) FROM observations').fetchone()[0], errors=errors)

    def read(self, route_id=None):
        with closing(self._connect()) as db:
            query = 'SELECT route_id, geometry_hash, stop_line_id, content FROM observations'
            args = ()
            if route_id:
                query += ' WHERE route_id=?'
                args = (route_id,)
            query += ' ORDER BY route_id, geometry_hash, stop_line_id, timestamp, run_id, sequence'
            points = {}
            for route, geometry, line, content in db.execute(query, args):
                key = (route, geometry, line)
                points.setdefault(key, dict(route_id=route, geometry_hash=geometry,
                    stop_line_id=line, observations=[]))['observations'].append(json.loads(content))
            return dict(points=list(points.values()),
                observation_count=sum(len(p['observations']) for p in points.values()),
                note='Local derived index; no automatic phase learning or live prediction.')

    def completeness(self, route_id=None):
        history = self.read(route_id)
        points = {(p['route_id'], p['geometry_hash'], p['stop_line_id']): p for p in history['points']}
        routes = [self.routes.load(route_id)] if route_id else [self.routes.load(r['route_id'])
            for r in self.routes.list() if r['status'] == 'OK']
        for route in routes:
            for line in route.stop_lines:
                key = (route.route_id, route.geometry_hash, line.stop_line_id)
                point = points.setdefault(key, dict(route_id=route.route_id, geometry_hash=route.geometry_hash,
                    stop_line_id=line.stop_line_id, observations=[]))
                point['verification'] = dict(geometry=route.geometry_verification['status'],
                    stop_line=line.verification['status'],
                    speed_limit=next((s['verification']['status'] for s in route.speed_sections
                        if s['start_s_m'] <= line.s_m <= s['end_s_m']), 'MISSING'),
                    direction=line.direction, movement=line.movement)
        result = []
        for key, point in sorted(points.items()):
            summary = point_completeness(point['observations'])
            verification = point.get('verification')
            if verification is None:
                summary['missing'].append('Geometria archiwalna lub nieznana; potrzebny osobny przegląd kierunku i linii.')
            else:
                for name, label in [('geometry','geometria trasy'), ('stop_line','linia zatrzymania'),
                                    ('speed_limit','ograniczenie prędkości')]:
                    if verification[name] != 'FIELD_CHECKED':
                        summary['missing'].append('Bez potwierdzenia terenowego: ' + label + '.')
            result.append(dict(route_id=key[0], geometry_hash=key[1], stop_line_id=key[2],
                               verification=verification, **summary))
        return dict(points=result, observation_count=history['observation_count'],
                    note='Inventory only. Repeated intervals do not establish model validity or enable live recommendations.')
