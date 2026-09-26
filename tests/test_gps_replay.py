from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from greenwave.gps_replay import GPSReplaySession
from greenwave.mapping_analysis import MappingAnalysis, MappingAnalysisJobs
from greenwave.route_geometry import load_route
from greenwave.telemetry import RunLogger


class GPSReplayTests(unittest.TestCase):
    def make_run(self, root):
        logger = RunLogger(root)
        now = datetime(2026, 9, 18, tzinfo=timezone.utc)
        logger.start(dict(start_time=now, corridor_id='none'))
        logger.append('RUN_START', timestamp=now, simulation_seconds=0, model_seconds=0)
        for index in range(3):
            logger.append('EXTERNAL_TELEMETRY', timestamp=now + timedelta(seconds=index),
                simulation_seconds=0, model_seconds=index, source='ANDROID_FUSED',
                latitude=52 + index * .00001, longitude=21, speed_mps=1, gps_accuracy=4,
                payload=dict(phone_timestamp_seconds=100 + index, device_id='p', stream_id='s',
                    sample_sequence=index, elapsed_realtime_nanos=(10 + index) * 1_000_000_000,
                    sent_elapsed_realtime_nanos=(10 + index) * 1_000_000_000 + 100_000_000,
                    measurement_age_lower_bound_seconds=.1, freshness_status='FRESH',
                    usable_for_live=True, position_quality='GOOD', speed_source='DEVICE'))
        logger.finish('USER_STOP', timestamp=now + timedelta(seconds=3), simulation_seconds=0, model_seconds=3)
        return logger, logger.run_id

    def test_seek_and_continuous_replay_are_deterministic_and_source_is_immutable(self):
        with tempfile.TemporaryDirectory() as root:
            logger, run_id = self.make_run(root)
            raw = logger._directory(run_id) / 'raw.csv'
            before = hashlib.sha256(raw.read_bytes()).hexdigest()
            replay = GPSReplaySession(logger)
            replay.load(run_id)
            self.assertIsNotNone(replay.state()['bounds'])
            self.assertEqual(replay.state()['endpoints']['start']['latitude'], 52)
            self.assertAlmostEqual(replay.state()['endpoints']['end']['latitude'], 52.00002)
            end = replay.seek(replay.duration)
            self.assertEqual(end['cursor'], 3)
            replay.seek(0); replay.command('play'); replay.advance(replay.duration)
            self.assertEqual(replay.state()['cursor'], 3)
            self.assertEqual(replay.command('reset')['timeline_seconds'], 0)
            self.assertEqual(replay.state()['cursor'], 1)
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), before)

    def test_derived_analysis_is_separate_and_records_source_hash(self):
        with tempfile.TemporaryDirectory() as root:
            logger, run_id = self.make_run(Path(root) / 'runs')
            route_path = Path(root) / 'route.json'
            route_path.write_text(json.dumps(dict(schema_version=1, route_id='r', geometry_version='v1',
                name='R', direction_description='north', coordinates=[[21,52],[21,52.001]],
                source={'attribution':'test'}, geometry_verification={'status':'DRAFT'},
                speed_sections=[], stop_lines=[])), encoding='utf-8')
            route = load_route(route_path)
            raw = logger._directory(run_id) / 'raw.csv'
            before = hashlib.sha256(raw.read_bytes()).hexdigest()
            result = MappingAnalysis(logger, Path(root) / 'derived').analyze(run_id, route, write=True)
            self.assertEqual(result['source_raw_sha256'], before)
            self.assertTrue((Path(root) / 'derived' / run_id / result['analysis_id'] / 'manifest.json').exists())
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), before)
            self.assertIn('status_duration_seconds', result)
            self.assertIn('reason_counts', result)
            attestation_path = Path(root) / 'derived' / 'field-review' / run_id / 'attestation.json'
            attestation_path.parent.mkdir(parents=True)
            attestation = dict(run_id=run_id, source_raw_sha256='wrong',
                               geometry_hash=route.geometry_hash, transition_states=['RED', 'GREEN'])
            attestation_path.write_text(json.dumps(attestation), encoding='utf-8')
            analysis = MappingAnalysis(logger)
            self.assertIsNone(analysis.analyze(run_id, route)['observation_review']['attestation'])
            attestation['source_raw_sha256'] = before
            attestation_path.write_text(json.dumps(attestation), encoding='utf-8')
            self.assertEqual(analysis.analyze(run_id, route)['observation_review']['attestation'], attestation)
            attestation['geometry_hash'] = 'other'
            attestation_path.write_text(json.dumps(attestation), encoding='utf-8')
            self.assertIsNone(analysis.analyze(run_id, route)['observation_review']['attestation'])

    def test_mapping_report_separates_route_observations_from_synthetic_clicks(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            route_path = base / 'route.json'
            route_path.write_text(json.dumps(dict(schema_version=1, route_id='r',
                geometry_version='v1', name='R', direction_description='north',
                coordinates=[[21, 52], [21, 52.001]],
                source={'attribution': 'test'}, geometry_verification={'status': 'DRAFT'},
                speed_sections=[], stop_lines=[])), encoding='utf-8')
            route = load_route(route_path)
            logger = RunLogger(base / 'runs')
            now = datetime(2026, 9, 18, tzinfo=timezone.utc)
            logger.start(dict(start_time=now, corridor_id='synthetic'))
            logger.append('RUN_START', timestamp=now, simulation_seconds=0, model_seconds=0)
            logger.append('EXTERNAL_TELEMETRY', timestamp=now, simulation_seconds=0,
                model_seconds=0, source='ANDROID_FUSED', latitude=52, longitude=21,
                speed_mps=0, gps_accuracy=4,
                payload=dict(phone_timestamp_seconds=100, device_id='p', stream_id='s',
                    sample_sequence=1, elapsed_realtime_nanos=1_000_000_000,
                    sent_elapsed_realtime_nanos=1_100_000_000,
                    measurement_age_lower_bound_seconds=.1, freshness_status='FRESH',
                    usable_for_live=True, position_quality='GOOD', speed_source='DEVICE'))
            logger.append('ROUTE_OBSERVATION', timestamp=now + timedelta(seconds=1),
                simulation_seconds=0, model_seconds=1, source='MANUAL_PASSENGER',
                payload=dict(observation_id='o1', route_id='r', geometry_hash=route.geometry_hash,
                    stop_line_id='L1', state='RED', event_type='STATE_SEEN',
                    gps_freshness='FRESH', map_match_status='MATCHED'))
            logger.append('STATE_SEEN', timestamp=now + timedelta(seconds=2),
                simulation_seconds=0, model_seconds=2, source='MANUAL', signal_id='S2',
                payload=dict(observation={'signal_id': 'S2'}))
            logger.finish('USER_STOP', timestamp=now + timedelta(seconds=3),
                          simulation_seconds=0, model_seconds=3)
            report = MappingAnalysis(logger).analyze(logger.run_id, route)
            self.assertEqual(report['route_observation_count'], 1)
            self.assertEqual(report['synthetic_observation_count'], 1)
            self.assertTrue(report['route_observations'][0]['matches_analyzed_route'])
            self.assertEqual(report['route_observations'][0]['stop_line_id'], 'L1')

    def test_analysis_job_runs_off_request_thread_and_reports_completion(self):
        with tempfile.TemporaryDirectory() as root:
            logger, run_id = self.make_run(root)
            jobs = MappingAnalysisJobs(MappingAnalysis(logger, Path(root) / 'derived'))
            self.addCleanup(jobs.close)
            job = jobs.start(run_id, None, write=False)
            self.assertIn(job['status'], ('RUNNING', 'COMPLETED'))
            deadline = time.monotonic() + 2
            while job['status'] == 'RUNNING' and time.monotonic() < deadline:
                time.sleep(.01)
                job = jobs.status(job['job_id'])
            self.assertEqual(job['status'], 'COMPLETED')
            self.assertEqual(job['result']['sample_count'], 3)

    def test_elapsed_realtime_regression_is_an_explicit_boundary(self):
        with tempfile.TemporaryDirectory() as root:
            logger = RunLogger(root)
            now = datetime(2026, 9, 18, tzinfo=timezone.utc)
            logger.start(dict(start_time=now, corridor_id='none'))
            logger.append('RUN_START', timestamp=now, simulation_seconds=0, model_seconds=0)
            for index, elapsed in enumerate((10, 11, 9)):
                logger.append('EXTERNAL_TELEMETRY', timestamp=now + timedelta(seconds=index),
                    simulation_seconds=0, model_seconds=index, source='ANDROID_FUSED',
                    latitude=52 + index * .00001, longitude=21, speed_mps=1, gps_accuracy=4,
                    payload=dict(phone_timestamp_seconds=100 + index, device_id='p', stream_id='s',
                        sample_sequence=index, elapsed_realtime_nanos=elapsed * 1_000_000_000,
                        sent_elapsed_realtime_nanos=elapsed * 1_000_000_000 + 100_000_000,
                        measurement_age_lower_bound_seconds=.1, freshness_status='FRESH',
                        usable_for_live=True, position_quality='GOOD', speed_source='DEVICE'))
            logger.finish('USER_STOP', timestamp=now + timedelta(seconds=3), simulation_seconds=0,
                          model_seconds=3)
            replay = GPSReplaySession(logger)
            replay.load(logger.run_id)
            self.assertEqual(replay.samples[-1].timeline_source, 'RECEIPT_BOUNDARY')
