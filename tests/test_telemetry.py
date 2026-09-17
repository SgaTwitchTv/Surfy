import csv, json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path

from greenwave.application import GreenWaveApplication
from greenwave.telemetry import RunLogger


class TelemetryTests(unittest.TestCase):
    def test_append_only_run_manifest_and_export(self):
        with tempfile.TemporaryDirectory() as root:
            logger=RunLogger(root)
            logger.start(dict(start_time=datetime.now(timezone.utc),session_id='s',corridor_id='c',direction='N',timebase='SIMULATION'))
            run_id=logger.run_id
            self.assertTrue(logger.append('TELEMETRY',timestamp=datetime.now(timezone.utc),simulation_seconds=0,model_seconds=0,source='TEST',speed_mps=1))
            logger.finish('USER_STOP',timestamp=datetime.now(timezone.utc),simulation_seconds=1,model_seconds=1)
            directory=Path(root)/run_id
            self.assertTrue((directory/'complete.json').exists())
            with (directory/'raw.csv').open(encoding='utf-8') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual([row['sequence'] for row in rows],['1','2'])
            manifest=json.loads((directory/'complete.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['records'],2)
            self.assertEqual(logger.list_runs()[0]['status'],'COMPLETED')
            self.assertEqual(logger.list_runs()[0]['external_samples'],0)
            exported=logger.export(run_id)
            self.assertGreater(len(exported),100)
            with self.assertRaises(ValueError):logger.export('../'+run_id)

    def test_active_export_is_refused_and_interrupted_is_explicit(self):
        with tempfile.TemporaryDirectory() as root:
            logger=RunLogger(root); logger.start(dict(start_time='now',session_id='s',corridor_id='c',direction='N',timebase='SIMULATION'))
            with self.assertRaises(ValueError):logger.export(logger.run_id)
            run_id=logger.run_id; logger.stream.close(); logger.active=False
            self.assertEqual(logger.list_runs()[0]['status'],'UNFINISHED')
            self.assertIn('run_id',logger.status())

    def test_application_recording_captures_observations_and_route_completion(self):
        with tempfile.TemporaryDirectory() as root:
            app=GreenWaveApplication(runs_root=root)
            app.recording('start'); run_id=app.logger.run_id
            app.observe('S1','GREEN','STATE_START')
            app.control(running=True)
            app.clock.set_running(False)
            app.clock._elapsed=20
            app.snapshot()
            self.assertTrue(app.logger.active)
            app.recording('stop')
            self.assertFalse(app.logger.active)
            run=app.logger.list_runs()[0]
            self.assertEqual(run['run_id'],run_id); self.assertEqual(run['status'],'COMPLETED')
            text=(Path(root)/run_id/'raw.csv').read_text(encoding='utf-8')
            self.assertIn('GREEN_START',text); self.assertIn('RUN_END',text); self.assertIn('TELEMETRY',text)

    def test_reset_closes_old_recording_and_starts_new_session(self):
        with tempfile.TemporaryDirectory() as root:
            app=GreenWaveApplication(runs_root=root); old=app.session_id
            app.recording('start'); app.reset()
            runs=app.logger.list_runs(); self.assertEqual(len(runs),1); self.assertEqual(runs[0]['reason'],'RESET')
            self.assertNotEqual(old,app.session_id)

    def test_phone_timestamp_is_preserved_without_replacing_session_time(self):
        with tempfile.TemporaryDirectory() as root:
            app=GreenWaveApplication(runs_root=root); app.recording('start'); run_id=app.logger.run_id
            phone_time=1_789_000_000.25
            app.ingest_external_position(timestamp_seconds=phone_time,latitude=52.2,longitude=20.9,
                                         speed_mps=2,gps_accuracy_m=8,source='WEB_GEOLOCATION')
            app.recording('stop')
            with (Path(root)/run_id/'raw.csv').open(encoding='utf-8') as stream:
                row=next(item for item in csv.DictReader(stream) if item['event']=='EXTERNAL_TELEMETRY')
            self.assertLess(float(row['model_seconds']),phone_time)
            self.assertEqual(json.loads(row['payload_json'])['phone_timestamp_seconds'],phone_time)


if __name__=='__main__':unittest.main()
