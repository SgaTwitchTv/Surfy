import unittest
from greenwave.vision_contracts import CameraFrameRef,VisionDetection
from greenwave.vision_tracking import LampTracker


class TrackingTests(unittest.TestCase):
    def setUp(self):self.tracker=LampTracker();self.index=0
    def tick(self,states=('RED',),time=None,session='one',boxes=None):
        self.index+=1;t=self.index*.1 if time is None else time
        frame=CameraFrameRef('camera',session,self.index,int(t*1e9),'2026-09-27T00:00:00+00:00',1,640,480,pts_seconds=t)
        detections=[VisionDetection(str(i),frame,(20+i*100,20,40+i*100,70) if boxes is None else boxes[i],state,.9,'model','a'*64) for i,state in enumerate(states)]
        return self.tracker.update(frame,detections,t)
    def settle(self,state='RED'):
        outputs=[self.tick((state,)) for _ in range(4)]
        return outputs[-1],sum((out[1] for out in outputs),[])
    def test_first_seen_then_transition_with_original_interval(self):
        (_,seen)=self.settle();self.assertEqual(seen[0]['observation']['data']['event_type'],'STATE_SEEN')
        (_,events)=self.settle('GREEN');self.assertEqual(len(events),1)
        event=events[0];self.assertEqual(event['observation']['data']['event_type'],'STATE_START')
        self.assertAlmostEqual(event['interval_seconds'][0],.4);self.assertAlmostEqual(event['interval_seconds'][1],.5)
        self.assertFalse(event['live_prediction_eligible'])
    def test_unknown_and_missing_frame_break_transition_evidence(self):
        for missing in ((),('UNKNOWN',),('OFF',)):
            self.setUp();self.settle();self.tick(missing)
            _,events=self.settle('GREEN');self.assertEqual(events[0]['observation']['data']['event_type'],'STATE_SEEN')
    def test_short_color_flash_does_not_emit_transition(self):
        self.settle();tracks,events=self.tick(('GREEN',));self.assertEqual(tracks[0]['state'],'UNKNOWN');self.assertEqual(events,[])
        _,events=self.tick(('RED',));self.assertEqual(events,[])
    def test_large_gap_and_segment_change_reset_evidence(self):
        self.settle();_,events=self.tick(('GREEN',),time=2)
        self.assertEqual(events,[])
        outputs=[self.tick(('GREEN',),time=2+i*.1,session='new') for i in range(1,5)]
        events=sum((out[1] for out in outputs),[])
        self.assertEqual(events[0]['observation']['data']['event_type'],'STATE_SEEN')
    def test_two_lamps_keep_distinct_ids(self):
        ids=[]
        for _ in range(4):tracks,_=self.tick(('RED','GREEN'));ids.append([t['track_id'] for t in tracks])
        self.assertEqual(ids[0],ids[-1]);self.assertNotEqual(ids[0][0],ids[0][1])
    def test_ambiguous_overlap_does_not_reuse_identity(self):
        self.settle();tracks,events=self.tick(('GREEN','GREEN'),boxes=[(20,20,40,70),(21,20,41,70)])
        self.assertEqual(events,[]);self.assertTrue(all(t['state']=='UNKNOWN' for t in tracks))
        self.assertTrue(all(not t['track_id'].endswith('lamp-1') for t in tracks))
    def test_reversed_media_clock_resets(self):
        self.settle();_,events=self.tick(('GREEN',),time=.1);self.assertEqual(events,[])
