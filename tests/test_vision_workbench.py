import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from greenwave.route_geometry import RouteRegistry
from greenwave.application import DATA
from greenwave.vision_workbench import VisionWorkbench
from greenwave.vision_contracts import CameraFrameRef,VisionDetection,SignalAssociation,VisionObservation
from greenwave.vision_validation import evaluate


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.routes=RouteRegistry(DATA/'routes');self.route=self.routes.load('arkadia_maczka_okopowa_v1');self.line=self.route.stop_lines[0]
        self.capture=Mock(root=Path(self.temp.name));self.id='a'*32;self.directory=self.capture.root/self.id;self.directory.mkdir()
        self.app=SimpleNamespace(routes=self.routes,selected_route=self.route,session_id='app',view_mode='LIVE',mapping_snapshot=lambda:dict(result={},route_observations=[]))
        self.frame=CameraFrameRef('cam',self.id+':0',1,1,'2026-09-27T00:00:00+00:00',1,640,480,str(self.directory/'video.mp4'),1)
        self.status=dict(status='RUNNING',session_id=self.id,source_type='CAMERA',preview_fresh=True,frame=self.frame.to_dict(),vision=dict(tracks=[dict(track_id='lamp',state='GREEN',continuity_generation=0)]))
        self.capture.status.side_effect=lambda:self.status.copy();self.workbench=VisionWorkbench(self.capture,self.app)
    def assign(self):return self.workbench.assign('lamp',self.route.route_id,self.route.geometry_hash,self.line.stop_line_id)
    def event(self):
        detection=VisionDetection('d',self.frame,(1.,1.,10.,20.),'GREEN',.9,'model','b'*64,track_id='lamp')
        observation=VisionObservation('event',detection,SignalAssociation(self.frame.session_id,'lamp','UNASSIGNED','NONE'))
        (self.directory/'events.jsonl').write_text(json.dumps(dict(events=[dict(observation=observation.to_dict())]))+'\n')
        (self.directory/'manifest.json').write_text(json.dumps(dict(artifacts=[dict(kind='VIDEO',filename='video.mp4')],run_id=None)))
    def test_assignment_expires_on_gap_epoch_route_and_app_session(self):
        self.assign();self.assertEqual(self.workbench.status()['signals'][0]['state'],'GREEN')
        self.status['vision']['tracks'][0]['continuity_generation']=1
        self.assertEqual(self.workbench.status()['associations'],[])
        self.assign();self.status['preview_fresh']=False;self.assertEqual(self.workbench.status()['signals'],[])
        self.status['preview_fresh']=True;self.assign();self.app.session_id='reset';self.assertEqual(self.workbench.status()['associations'],[])
    def test_wrong_geometry_and_stale_track_rejected(self):
        with self.assertRaises(ValueError):self.workbench.assign('lamp',self.route.route_id,'c'*64,self.line.stop_line_id)
        self.status['preview_fresh']=False
        with self.assertRaises(ValueError):self.assign()
    def test_pedestrian_and_wrong_arrow_cannot_associate_to_vehicle_line(self):
        for pictogram in ('PEDESTRIAN','ARROW_LEFT'):
            self.status['vision']['tracks'][0]['pictogram']=pictogram
            with self.assertRaises(ValueError):self.assign()
    def test_live_manual_cv_conflict_is_visible_without_overwriting(self):
        self.assign();manual=dict(route_id=self.route.route_id,geometry_hash=self.route.geometry_hash,stop_line_id=self.line.stop_line_id,state='RED',timestamp='2026-09-27T00:00:00+00:00')
        self.app.mapping_snapshot=lambda:dict(result={},route_observations=[manual])
        signal=self.workbench.status()['signals'][0]
        self.assertEqual(signal['state'],'CONFLICT');self.assertEqual(manual['state'],'RED')
    def test_conflicting_lamps_do_not_show_green(self):
        self.assign();self.status['vision']['tracks'].append(dict(track_id='lamp2',state='RED',continuity_generation=0))
        self.workbench.assign('lamp2',self.route.route_id,self.route.geometry_hash,self.line.stop_line_id)
        self.assertEqual(self.workbench.status()['signals'][0]['state'],'CONFLICT')
    def test_independent_lines_and_changed_route(self):
        self.assign();self.status['vision']['tracks'].append(dict(track_id='second',state='RED',continuity_generation=0))
        self.workbench.assign('second',self.route.route_id,self.route.geometry_hash,self.route.stop_lines[1].stop_line_id)
        signals=self.workbench.status()['signals'];self.assertEqual({s['state'] for s in signals},{'GREEN','RED'})
        self.app.selected_route=self.routes.load('zwirki_wigury_draft');self.assertEqual(self.workbench.status()['associations'],[])
    def test_review_is_separate_durable_and_idempotent(self):
        self.event();original=(self.directory/'events.jsonl').read_bytes();self.workbench.history(self.id);self.workbench.history(self.id)
        kwargs=dict(capture_id=self.id,event_id='event',status='ACCEPTED',reviewer='passenger',route_id=self.route.route_id,geometry_hash=self.route.geometry_hash,stop_line_id=self.line.stop_line_id)
        self.workbench.review(**kwargs);self.workbench.review(**kwargs)
        history=VisionWorkbench(self.capture,self.app).history(self.id)
        self.assertEqual(len(history['entries']),1);self.assertEqual(len(history['entries'][0]['decisions']),1)
        self.assertFalse(history['entries'][0]['decisions'][0]['phase_learning_eligible'])
        self.workbench.review(self.id,'event','REJECTED','passenger');self.assertEqual(len(self.workbench.history(self.id)['entries'][0]['decisions']),2)
        self.assertEqual(original,(self.directory/'events.jsonl').read_bytes())
    def test_review_requires_route_and_reviewer(self):
        self.event()
        with self.assertRaises(ValueError):self.workbench.review(self.id,'event','ACCEPTED','passenger',self.route.route_id,'bad',self.line.stop_line_id)
        with self.assertRaises(ValueError):self.workbench.review(self.id,'event','REJECTED','')
    def test_history_pagination_keeps_older_events_without_duplicates(self):
        self.event();payload=json.loads((self.directory/'events.jsonl').read_text())
        with (self.directory/'events.jsonl').open('w') as stream:
            for index in range(205):
                payload['events'][0]['observation']['data']['observation_id']='event-'+str(index)
                stream.write(json.dumps(payload)+'\n')
        page=self.workbench.history(self.id)
        while page['import_progress']['pending']:page=self.workbench.history(self.id)
        self.assertEqual(len(page['entries']),200)
        older=self.workbench.history(self.id,page['next_cursor']);self.assertEqual(len(older['entries']),5)
        self.assertEqual(len({e['event_id'] for e in page['entries']+older['entries']}),205)
        with self.assertRaises(ValueError):self.workbench.history(self.id,0)
    def test_validation_counts_false_green_unknown_and_split_leak(self):
        rows=[dict(frame=dict(data=dict(frame_id=1)),tracks=[dict(bbox_xyxy=[0,0,10,20],state='GREEN',track_id='a')],inference_ms=10)]
        labels=dict(source_sha256='hash',split='ACCEPTANCE',frames=[dict(frame_id=1,lamps=[dict(bbox_xyxy=[0,0,10,20],state='RED',lamp_id='truth')])])
        report=evaluate(rows,labels,'hash');self.assertEqual(report['false_green_matched'],1);self.assertFalse(report['road_quality_accepted'])
        labels['tuning_source_sha256']=['hash']
        with self.assertRaises(ValueError):evaluate(rows,labels,'hash')
    def test_validation_switches_and_transition_evidence_not_double_counted(self):
        rows=[dict(frame=dict(data=dict(frame_id=i,session_id='one')),tracks=[dict(bbox_xyxy=[0,0,10,20],state='UNKNOWN',track_id=str(i))],inference_ms=10,events=[])
            for i in (1,2)]
        rows[1]['events']=[dict(observation=dict(data=dict(event_type='STATE_START',detection=dict(track_id='2',state='GREEN'))),interval_seconds=[1,1.2])]
        labels=dict(source_sha256='hash',split='TUNING',frames=[dict(frame_id=i,lamps=[dict(bbox_xyxy=[0,0,10,20],state='RED',lamp_id='truth')]) for i in (2,1)],
            transitions=[dict(track_id='2',state='GREEN',interval_seconds=[1,1.2])]*2)
        report=evaluate(rows,labels,'hash');self.assertEqual(report['track_switches'],1);self.assertEqual(report['unknown_matched'],2);self.assertEqual(report['transition_missing'],1)
