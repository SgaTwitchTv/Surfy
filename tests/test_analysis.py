import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from greenwave.telemetry import RunLogger
from greenwave.analysis import RunAnalysis

class AnalysisTests(unittest.TestCase):
 def make_run(self,root,offset=0,green=True):
  log=RunLogger(root);now=datetime.now(timezone.utc);log.start(dict(start_time=now,session_id='s',corridor_id='c',direction='N',timebase='SIMULATION',dataset='fixture'))
  log.append('RUN_START',timestamp=now,simulation_seconds=offset,model_seconds=offset,source='TEST')
  for i,speed in enumerate((0,5,10,5,0)):
   log.append('TELEMETRY',timestamp=now,simulation_seconds=i+offset,model_seconds=i+offset,source='TEST',current_corridor_position=i*10,speed_mps=speed,target_speed_mps=10)
  log.append('PASS_STOP_LINE',timestamp=now,simulation_seconds=5+offset,model_seconds=5+offset,source='TEST',signal_id='S1',speed_mps=5,payload={'state':'GREEN' if green else 'RED'})
  log.finish('USER_STOP',timestamp=now,simulation_seconds=6+offset,model_seconds=6+offset);return log.run_id
 def make_gps_run(self,root):
  log=RunLogger(root);now=datetime.now(timezone.utc);log.start(dict(start_time=now,session_id='s',corridor_id='c',direction='N',timebase='SIMULATION',dataset='fixture'))
  log.append('RUN_START',timestamp=now,simulation_seconds=0,model_seconds=0,source='TEST')
  for i in range(40):
   stopped=i<10 or i>=30;speed=0 if stopped else 2;source='STATIONARY_FILTER' if stopped else 'DEVICE'
   log.append('EXTERNAL_TELEMETRY',timestamp=now+timedelta(seconds=i),simulation_seconds=i,model_seconds=i,source='WEB_GEOLOCATION',latitude=52.2+i*.00001,longitude=20.9,speed_mps=speed,gps_accuracy=8,payload=dict(phone_timestamp_seconds=1000+i,raw_speed_mps=.4 if stopped else 2,calculated_speed_mps=0 if stopped else 2,speed_source=source,position_quality='GOOD',usable_for_live=True,quality_reasons=[]))
  log.finish('USER_STOP',timestamp=now+timedelta(seconds=40),simulation_seconds=40,model_seconds=40);return log.run_id
 def test_metrics_and_comparison_never_change_raw(self):
  with tempfile.TemporaryDirectory() as root:
   log=RunLogger(root);a=self.make_run(root);raw=(__import__('pathlib').Path(root)/a/'raw.csv').read_bytes();m=RunAnalysis(log).analyze(a)
   self.assertEqual(m['distance'],40);self.assertEqual(m['green_passes'],1);self.assertEqual(m['red_arrivals'],0);self.assertEqual(m['number_of_complete_stops'],1);self.assertTrue(m['brake_events']>0);self.assertEqual(m['gps_quality']['status'],'NO_DATA');self.assertEqual(raw,(__import__('pathlib').Path(root)/a/'raw.csv').read_bytes())
   b=self.make_run(root,10,False);comparison=RunAnalysis(log).compare(a,b);self.assertEqual(comparison['baseline']['green_passes'],1);self.assertEqual(comparison['greenwave']['red_arrivals'],1);self.assertIn('number_of_complete_stops',comparison['delta'])
 def test_tampering_and_invalid_sequence_are_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   log=RunLogger(root);run_id=self.make_run(root);p=__import__('pathlib').Path(root)/run_id/'raw.csv';p.write_text(p.read_text().replace('TELEMETRY','BROKEN',1),encoding='utf-8')
   with self.assertRaises(ValueError):RunAnalysis(log).analyze(run_id)
 def test_missing_values_are_supported_and_json_finite(self):
  with tempfile.TemporaryDirectory() as root:
   log=RunLogger(root);rid=self.make_run(root);result=RunAnalysis(log).analyze(rid);json.dumps(result,allow_nan=False)
 def test_gps_quality_report_covers_transport_accuracy_speed_and_motion(self):
  with tempfile.TemporaryDirectory() as root:
   log=RunLogger(root);rid=self.make_gps_run(root);raw=(__import__('pathlib').Path(root)/rid/'raw.csv').read_bytes();gps=RunAnalysis(log).analyze(rid)['gps_quality']
   self.assertEqual(gps['status'],'READY');self.assertEqual(gps['sample_count'],40);self.assertAlmostEqual(gps['sample_rate_hz'],1);self.assertEqual(gps['largest_gap_seconds'],1);self.assertEqual(gps['gaps_over_2_seconds'],0)
   self.assertEqual(gps['largest_phone_gap_seconds'],1);self.assertEqual(gps['phone_gaps_over_2_seconds'],0);self.assertEqual(gps['transport_only_gaps_over_2_seconds'],0)
   self.assertEqual(gps['accuracy']['median_m'],8);self.assertEqual(gps['accuracy']['within_10m_ratio'],1);self.assertEqual(gps['usable_ratio'],1);self.assertEqual(gps['speed']['final_available_ratio'],1)
   self.assertEqual(gps['speed']['source_counts']['DEVICE'],20);self.assertEqual(gps['location_source_counts']['WEB_GEOLOCATION'],40);self.assertEqual(gps['movement_transitions'],2);self.assertEqual(gps['movement_starts'],1);self.assertEqual(gps['stop_confirmations'],1);self.assertFalse(gps['issues'])
   self.assertEqual(raw,(__import__('pathlib').Path(root)/rid/'raw.csv').read_bytes())

if __name__=='__main__':unittest.main()
