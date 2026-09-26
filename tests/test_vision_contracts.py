from dataclasses import replace
import unittest

from greenwave.vision_contracts import decode_vision, VisionObservation
from greenwave.vision_demos import all_vision_demos, vision_demo


class VisionContractTests(unittest.TestCase):
    def detection(self):
        return decode_vision(vision_demo('good_detection')['detections'][0])

    def association(self):
        return decode_vision(vision_demo('good_detection')['associations'][0])

    def test_every_demo_dto_roundtrips_and_cannot_enable_live(self):
        for scenario in all_vision_demos():
            self.assertTrue(scenario['synthetic'])
            self.assertFalse(scenario['live_prediction_eligible'])
            for key in ('detections','tracks','associations','observations'):
                for value in scenario[key]:
                    dto=decode_vision(value)
                    self.assertEqual(decode_vision(dto.to_json()),dto)
                    if isinstance(dto,VisionObservation):self.assertFalse(dto.live_prediction_eligible)

    def test_first_sighting_does_not_claim_start_and_confirmed_is_not_live(self):
        d=self.detection();a=self.association()
        seen=VisionObservation('o',d,a,review_status='ACCEPTED',reviewer='passenger')
        self.assertIsNone(seen.transition_monotonic_interval_ns)
        self.assertFalse(seen.live_prediction_eligible)
        with self.assertRaises(ValueError):replace(seen,event_type='STATE_START')

    def test_transition_requires_same_continuous_track_with_distinct_states(self):
        d=self.detection();a=self.association()
        later=replace(d,detection_id='later',state='RED',frame=replace(d.frame,frame_id=2,
            captured_monotonic_ns=2_000_000_000,captured_utc='2026-09-26T12:00:01+00:00'))
        event=VisionObservation('change',later,a,event_type='STATE_START',previous_detection=d,
                                continuity_confirmed=True)
        self.assertEqual(event.transition_monotonic_interval_ns,(1_000_000_000,2_000_000_000))
        self.assertEqual(decode_vision(event.to_json()),event)
        for changes in ({'continuity_confirmed':False},
                        {'previous_detection':replace(d,track_id='different')},
                        {'previous_detection':replace(d,state='UNKNOWN')},
                        {'previous_detection':replace(d,state='RED')},
                        {'previous_detection':replace(d,model_sha256='1'*64)},
                        {'previous_detection':replace(d,frame=later.frame)}):
            with self.assertRaises(ValueError):replace(event,**changes)

    def test_invalid_boxes_scores_coordinates_and_schema_are_rejected(self):
        d=self.detection()
        for changes in ({'bbox_xyxy':(0,0,2000,100)}, {'bbox_xyxy':(10,10,9,20)},
                        {'model_score':float('nan')},{'model_score':1.1}, {'state':'BLUE'},
                        {'model_sha256':'bad'}):
            with self.assertRaises(ValueError):replace(d,**changes)
        with self.assertRaises(ValueError):replace(d.frame,width=True)
        with self.assertRaises(ValueError):replace(d.frame,captured_utc='2026-09-26T12:00:00')
        with self.assertRaises(ValueError):replace(self.association(),stop_line_latitude=91)
        with self.assertRaises(ValueError):replace(self.association(),geometry_hash='bad')
        envelope=d.to_dict();envelope['schema_version']=2
        with self.assertRaises(ValueError):decode_vision(envelope)
        envelope=d.to_dict();envelope['data']['unexpected']=1
        with self.assertRaises(ValueError):decode_vision(envelope)

    def test_automatic_and_ambiguous_assignments_cannot_be_accepted(self):
        d=self.detection();a=self.association()
        with self.assertRaises(ValueError):replace(a,method='GPS_PROPOSAL')
        with self.assertRaises(ValueError):replace(a,stop_line_id=None)
        with self.assertRaises(ValueError):VisionObservation('o',d,replace(a,status='AMBIGUOUS'),
            review_status='ACCEPTED',reviewer='passenger')
        with self.assertRaises(ValueError):VisionObservation('o',d,replace(a,session_id='different'))

    def test_red_yellow_is_preserved_as_distinct_state(self):
        d=replace(self.detection(),state='RED_YELLOW')
        self.assertEqual(decode_vision(d.to_json()).state,'RED_YELLOW')
