from datetime import datetime, timedelta, timezone
from dataclasses import replace
import json
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from greenwave.application import DATA, GreenWaveApplication
from greenwave.clocks import SimulationClock
from greenwave.events import ModelResynchronized, PredictionUpdated


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.seconds = 0
        self.utc = datetime(2026, 9, 11, tzinfo=timezone.utc)
        self.app = GreenWaveApplication(SimulationClock(lambda:self.seconds, lambda:self.utc+timedelta(seconds=self.seconds)))

    def test_position_and_clocks_at_rate_then_pause(self):
        self.app.control(running=True, rate=10, speed_kmh=36)
        self.seconds = 2
        self.app.control(running=False)
        self.seconds = 8
        snapshot = self.app.snapshot()
        self.assertEqual(snapshot['model_time'],20)
        self.assertGreater(snapshot['position']['road_position_m'],0)
        self.assertLess(snapshot['position']['road_position_m'],200)
        self.assertAlmostEqual(snapshot['position']['elapsed_seconds'],20)
        self.assertIn('00:00:08',snapshot['utc'])

    def test_map_observation_drives_predictions_and_typed_events(self):
        changed, updated = [], []
        self.app.bus.subscribe(changed.append,ModelResynchronized)
        self.app.bus.subscribe(updated.append,PredictionUpdated)
        self.app.observe('S3','GREEN','STATE_START')
        snapshot = self.app.snapshot()
        self.assertEqual(snapshot['signals'][2]['offset'],0)
        self.assertEqual(snapshot['signals'][3]['offset'],90)
        self.assertEqual(changed[0].signal_ids,('S3',))
        self.assertEqual(updated[0].model_version,1)
        self.assertEqual(snapshot['history_total'],1)

    def test_rejected_observation_has_no_side_effect(self):
        for point, state, kind in [('S9','GREEN','STATE_START'),('S1','BLUE','STATE_START'),('S1','GREEN','BOGUS')]:
            with self.assertRaises(ValueError):self.app.observe(point,state,kind)
        self.assertEqual(self.app.prediction.version,0)
        self.assertEqual(len(self.app.observations.history),0)

    def test_route_observation_is_scoped_and_recorded_without_changing_prediction(self):
        with tempfile.TemporaryDirectory() as root:
            app = GreenWaveApplication(runs_root=root)
            app.select_route('radom_limanowskiego_25_czerwca_draft')
            line = app.selected_route.stop_lines[0]
            with self.assertRaises(ValueError):
                app.observe_route(line.stop_line_id, 'RED', 'STATE_SEEN')
            app.set_view_mode('LIVE')
            with self.assertRaises(ValueError):
                app.observe_route('S1', 'RED', 'STATE_SEEN')
            app.recording('start')
            version = app.prediction.version
            event = app.observe_route(line.stop_line_id, 'RED', 'STATE_SEEN')
            self.assertEqual(event['route_id'], app.selected_route.route_id)
            self.assertEqual(event['line_verification'], line.verification['status'])
            self.assertEqual(app.prediction.version, version)
            run_id = app.logger.run_id
            app.recording('stop')
            with (Path(root) / run_id / 'raw.csv').open(encoding='utf-8', newline='') as source:
                rows = list(csv.DictReader(source))
            observations = [row for row in rows if row['event'] == 'ROUTE_OBSERVATION']
            self.assertEqual(len(observations), 1)
            self.assertEqual(json.loads(observations[0]['payload_json'])['stop_line_id'], line.stop_line_id)

    def test_fresh_phone_and_selected_route_start_field_recording_in_live_view(self):
        with tempfile.TemporaryDirectory() as root:
            app = GreenWaveApplication(runs_root=root)
            app.select_route('radom_25_czerwca_limanowskiego_draft')
            app.ingest_external_position(timestamp_seconds=self.utc.timestamp(),
                latitude=51.3938, longitude=21.1595, speed_mps=0, gps_accuracy_m=5,
                source='ANDROID_FUSED', device_id='phone', stream_id='field',
                sample_sequence=1, elapsed_realtime_nanos=1_000_000_000,
                sent_elapsed_realtime_nanos=1_100_000_000, is_mock=False)
            self.assertEqual(app.view_mode, 'SIMULATION')
            app.recording('start')
            self.assertEqual(app.view_mode, 'LIVE')
            with self.assertRaises(ValueError):
                app.observe('S2', 'GREEN', 'STATE_SEEN')
            route_event = app.observe_route(app.selected_route.stop_lines[0].stop_line_id,
                                            'GREEN', 'STATE_SEEN')
            app.recording('stop')
            metadata = json.loads((Path(root) / app.logger.run_id / 'metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['view_mode'], 'LIVE')
            self.assertEqual(route_event['route_id'], app.selected_route.route_id)

    def test_reset_keeps_history_and_discards_predictions(self):
        self.app.observe('S3','GREEN','STATE_START')
        old=self.app.session_id
        self.app.reset()
        snapshot=self.app.snapshot()
        self.assertNotEqual(old,snapshot['session_id'])
        self.assertEqual(snapshot['model_version'],0)
        self.assertEqual(snapshot['signals'][2]['offset'],60)
        self.assertEqual(snapshot['history_total'],1)
        old_event=replace(self.app.observations.history[0].observation,observation_id='old-event')
        self.app.observations.accept(old_event)
        self.assertEqual(self.app.prediction.version,0)

    def test_unknown_corridor_uses_utc_without_inventing_geometry(self):
        self.app.reset('zwirki_wigury')
        self.seconds=8
        self.app.observe('S1','GREEN','STATE_START')
        self.seconds=12
        snapshot=self.app.snapshot()
        self.assertFalse(snapshot['available'])
        self.assertEqual(snapshot['model_time'],12)
        self.assertEqual(snapshot['simulation_seconds'],0)
        self.assertEqual(snapshot['signals'][0]['observation_age_seconds'],4)
        self.assertTrue(all(s['distance_m'] is None and not s['windows'] for s in snapshot['signals']))
        with self.assertRaises(ValueError):self.app.control(running=True)

    def test_simulator_jitter_does_not_leak_into_prediction(self):
        normal=self.app.snapshot()
        self.app.reset(jitter=True)
        jitter=self.app.snapshot()
        for a,b in zip(normal['signals'],jitter['signals']):
            self.assertEqual(a['windows'],b['windows'])
            self.assertEqual(a['offset'],b['offset'])

    def test_end_of_route_stops_clock_without_instantly_stopping_vehicle(self):
        self.app.corridor=replace(self.app.corridor,signals=(self.app.corridor.signals[0],))
        self.app.control(running=True,rate=10,speed_kmh=50)
        self.seconds=100
        snapshot=self.app.snapshot()
        self.assertFalse(snapshot['running'])
        self.assertGreaterEqual(snapshot['position']['road_position_m'],300)
        self.assertLess(snapshot['position']['road_position_m'],302)
        self.assertGreater(snapshot['position']['speed_mps'],0)
        self.assertEqual(snapshot['recommendation']['status'],'COMPLETE')
        self.app.control(running=True)
        self.assertFalse(self.app.clock.running)

    def test_api_snapshot_is_finite_json(self):
        self.app.observe('S1','GREEN','STATE_START')
        json.dumps(self.app.snapshot(),allow_nan=False)

    def test_invalid_controls_do_not_partially_mutate(self):
        for invalid in (dict(rate=True),dict(speed_kmh=float('nan')),dict(running='yes'),dict(speed_kmh=80)):
            with self.assertRaises(ValueError):self.app.control(**invalid)
        self.assertFalse(self.app.clock.running)
        self.assertEqual(self.app.speed_kmh,36)

    def test_invalid_reset_config_preserves_active_session(self):
        session=self.app.session_id
        bad_relation=replace(self.app.prediction.relations[0],target_signal_id='S99')
        with patch('greenwave.application.load_prediction_config',return_value=(self.app.prediction.settings,(bad_relation,))):
            with self.assertRaises(ValueError):self.app.reset()
        self.assertEqual(self.app.session_id,session)
        self.assertEqual(self.app.prediction.session_id,session)

    def test_offline_map_has_sourced_geometry_and_demo_route(self):
        data=json.loads((DATA/'maps/warsaw.json').read_text(encoding='utf-8'))
        self.assertGreater(len(data['features']),100)
        self.assertGreater(len(data['demo_route']),10)
        self.assertGreater(data['demo_route'][0][1],data['demo_route'][-1][1])
        self.assertEqual(data['metadata']['marker_quality'],'PLACEHOLDER')
        self.assertIn('openstreetmap.org',data['metadata']['source_url'])
        chomiczowka=json.loads((DATA/'maps/chomiczowka.json').read_text(encoding='utf-8'))
        self.assertGreater(len(chomiczowka['features']),100)
        self.assertEqual(chomiczowka['metadata']['bbox'],[20.913,52.269,20.929,52.279])
        self.assertIn('openstreetmap.org',chomiczowka['metadata']['source_url'])

    def test_repeated_planning_does_not_restart_reaction_and_default_run_crosses_on_green(self):
        self.app.control(running=True)
        self.seconds=.5
        self.app.snapshot()
        self.assertEqual(self.app.recommendation.status,'READY')
        for time in range(1,161):
            self.seconds=time
            snapshot=self.app.snapshot()
            self.assertIsNone(snapshot['incident'])
            self.assertLessEqual(snapshot['position']['speed_mps'],50/3.6)
        self.assertEqual(len(snapshot['crossings']),5)
        self.assertTrue(all(c['state']=='GREEN' for c in snapshot['crossings']))
        self.assertEqual(snapshot['recommendation']['status'],'COMPLETE')

    def test_observation_immediately_invalidates_recommendation(self):
        self.assertEqual(self.app.recommendation.status,'READY')
        self.app.observe('S1','RED','STATE_SEEN')
        self.assertIsNone(self.app.recommendation.target_kmh)

    def test_motion_does_not_depend_on_polling_frequency(self):
        other=GreenWaveApplication(SimulationClock(lambda:self.seconds,lambda:self.utc+timedelta(seconds=self.seconds)))
        self.app.control(running=True)
        other.control(running=True)
        for time in range(1,101):
            self.seconds=time/10
            self.app.snapshot()
        other.snapshot()
        self.assertAlmostEqual(self.app.position.position,other.position.position)
        self.assertAlmostEqual(self.app.position.speed,other.position.speed)

    def test_live_mapping_does_not_mutate_simulation_or_unlock_draft_route(self):
        self.app.select_route('zwirki_wigury_draft')
        simulation_before=self.app.position.position
        common=dict(speed_mps=5,heading_deg=180,gps_accuracy_m=4,source='ANDROID_FUSED',
                    device_id='phone',stream_id='drive',is_mock=False,heading_accuracy_deg=5)
        self.app.ingest_external_position(timestamp_seconds=self.utc.timestamp(),
            latitude=52.21545,longitude=20.98821,sample_sequence=1,
            elapsed_realtime_nanos=1_000_000_000,sent_elapsed_realtime_nanos=1_100_000_000,**common)
        self.app.ingest_external_position(timestamp_seconds=self.utc.timestamp()+1,
            latitude=52.21530,longitude=20.98823,sample_sequence=2,
            elapsed_realtime_nanos=2_000_000_000,sent_elapsed_realtime_nanos=2_100_000_000,**common)
        mapping=self.app.mapping_snapshot()
        self.assertEqual(mapping['result']['status'],'MATCHED')
        self.assertFalse(mapping['recommendation_eligibility']['allowed'])
        self.assertIsNone(mapping['live_recommendation'])
        self.assertIn('GEOMETRY_NOT_FIELD_VERIFIED',
                      mapping['recommendation_eligibility']['reason_codes'])
        self.assertEqual(self.app.position.position,simulation_before)
