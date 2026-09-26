from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from greenwave.observation_history import ObservationHistory
from greenwave.route_geometry import RouteRegistry
from greenwave.telemetry import RunLogger
from tests.test_map_matching import make_route


class ObservationHistoryTests(unittest.TestCase):
    def test_completeness_includes_empty_current_points_and_separates_old_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);routes_root=root/'routes';routes_root.mkdir()
            route=make_route(routes_root)
            logger=RunLogger(root/'runs');history=ObservationHistory(logger,RouteRegistry(routes_root))
            report=history.completeness(route.route_id)
            self.assertEqual(len(report['points']),1)
            self.assertEqual(report['points'][0]['status'],'NO_DATA')
            self.assertEqual(report['points'][0]['verification']['stop_line'],'DRAFT')
            self.make_run(root,route,'older-geometry');history.sync()
            report=history.completeness(route.route_id)
            self.assertEqual(len(report['points']),2)
            old=next(p for p in report['points'] if p['geometry_hash']=='older-geometry')
            self.assertIsNone(old['verification'])
            self.assertFalse(old['model_validated'])

    def make_run(self, root, route, geometry_hash=None):
        logger = RunLogger(root / 'runs')
        now = datetime(2026, 9, 26, tzinfo=timezone.utc)
        logger.start(dict(start_time=now))
        logger.append('RUN_START', timestamp=now, simulation_seconds=0, model_seconds=0)
        for sequence, seconds in enumerate((0, .5), 1):
            logger.append('ROUTE_OBSERVATION', timestamp=now+timedelta(seconds=seconds),
                simulation_seconds=0, model_seconds=seconds,
                payload=dict(observation_id=f'o{sequence}', route_id=route.route_id,
                    geometry_hash=geometry_hash or route.geometry_hash, geometry_version='v1',
                    stop_line_id='L1', state='GREEN', event_type='STATE_SEEN',
                    timestamp=(now+timedelta(seconds=seconds)).isoformat(), source='MANUAL_PASSENGER'))
        logger.finish('USER_STOP', timestamp=now+timedelta(seconds=1), simulation_seconds=0, model_seconds=1)
        return logger

    def test_reimport_restart_and_geometry_isolation_preserve_raw(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary);routes_root=root/'routes';routes_root.mkdir()
            route=make_route(routes_root)
            first=self.make_run(root,route)
            second=self.make_run(root,route,'older-geometry')
            raw=first._directory(first.run_id)/'raw.csv'
            before=hashlib.sha256(raw.read_bytes()).hexdigest()
            history=ObservationHistory(first,RouteRegistry(routes_root))
            self.assertEqual(history.sync()['observation_count'],4)
            self.assertEqual(history.sync()['observation_count'],4)
            points=ObservationHistory(first,RouteRegistry(routes_root)).read(route.route_id)['points']
            self.assertEqual(len(points),2)
            known=next(p for p in points if p['geometry_hash']==route.geometry_hash)
            old=next(p for p in points if p['geometry_hash']=='older-geometry')
            self.assertEqual(known['observations'][1]['classification'],'RAPID_DUPLICATE')
            self.assertEqual(known['observations'][0]['direction'],'FORWARD')
            self.assertIsNone(old['observations'][0]['direction'])
            self.assertEqual(history.read('different-route')['observation_count'],0)
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),before)
            # Corruption invalidates previously indexed evidence, not only new imports.
            raw.write_bytes(raw.read_bytes()+b'corrupt')
            result=history.sync()
            self.assertEqual(len(result['errors']),1)
            self.assertEqual(result['observation_count'],2)
            (second._directory(second.run_id)/'complete.json').unlink()
            self.assertEqual(history.sync()['observation_count'],0)

    def test_attestation_is_refreshed_without_changing_raw_seen_events(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);routes_root=root/'routes';routes_root.mkdir()
            route=make_route(routes_root);logger=self.make_run(root,route)
            history=ObservationHistory(logger,RouteRegistry(routes_root));history.sync()
            self.assertEqual(history.read()['points'][0]['observations'][0]['reviewed_type'],'STATE_SEEN')
            raw=logger._directory(logger.run_id)/'raw.csv'
            path=root/'derived'/'field-review'/logger.run_id/'attestation.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(run_id=logger.run_id,
                source_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                geometry_hash=route.geometry_hash,transition_states=['GREEN'])),encoding='utf-8')
            history.sync();event=history.read()['points'][0]['observations'][0]
            self.assertEqual(event['reviewed_type'],'STATE_START')
            self.assertEqual(event['raw_observation']['event_type'],'STATE_SEEN')
            path.unlink();history.sync()
            self.assertEqual(history.read()['points'][0]['observations'][0]['reviewed_type'],'STATE_SEEN')
