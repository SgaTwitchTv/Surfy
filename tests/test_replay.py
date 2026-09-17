import csv, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path

from greenwave.telemetry import RunLogger
from greenwave.replay import ReplaySession, ReplayPositionProvider


class ReplayTests(unittest.TestCase):
    def make_run(self, root):
        log=RunLogger(root); now=datetime.now(timezone.utc)
        log.start(dict(start_time=now,session_id='s',corridor_id='c',direction='N',timebase='SIMULATION'))
        for i,event in enumerate(('RUN_START','TELEMETRY','GREEN_START','TELEMETRY','RUN_END')):
            log.append(event,timestamp=now,simulation_seconds=i,model_seconds=i,source='TEST',current_corridor_position=i*10,speed_mps=i,target_speed_mps=5)
        log.finish('USER_STOP',timestamp=now,simulation_seconds=5,model_seconds=5)
        return log,log.run_id

    def test_load_seek_pause_rate_and_deterministic_events(self):
        with tempfile.TemporaryDirectory() as root:
            logger,run_id=self.make_run(root); replay=ReplaySession(logger)
            state=replay.load(run_id); self.assertEqual(state['model_seconds'],0);self.assertFalse(state['running'])
            replay.command('play'); replay.advance(1); self.assertEqual(replay.time,1)
            replay.command('rate',5); replay.advance(1); self.assertEqual(replay.time,5);self.assertFalse(replay.running)
            replay.seek(2); self.assertEqual(replay.state()['event'],'GREEN_START');self.assertEqual(len(replay.events(2)),3)
            replay.command('play');replay.advance(0);self.assertTrue(replay.running);replay.command('pause');self.assertFalse(replay.running)

    def test_replay_is_read_only_and_rejects_bad_or_incomplete_runs(self):
        with tempfile.TemporaryDirectory() as root:
            logger,run_id=self.make_run(root); replay=ReplaySession(logger); before=(Path(root)/run_id/'raw.csv').read_bytes(); replay.load(run_id); replay.seek(3); self.assertEqual(before,(Path(root)/run_id/'raw.csv').read_bytes())
            with self.assertRaises(ValueError):replay.seek(99)
            with self.assertRaises(ValueError):replay.command('rate',3)
            other=RunLogger(root);other.start(dict(start_time='now',session_id='s',corridor_id='c',direction='N',timebase='SIMULATION'))
            with self.assertRaises(ValueError):replay.load(other.run_id)
            other.finish('TEST',timestamp=datetime.now(timezone.utc),simulation_seconds=0,model_seconds=0)

    def test_provider_represents_logged_sample(self):
        sample=ReplayPositionProvider('2026-01-01T00:00:00+00:00',2,12.5,4,5)
        self.assertEqual(sample.position_m,12.5)


if __name__=='__main__':unittest.main()
