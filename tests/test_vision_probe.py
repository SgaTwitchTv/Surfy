import unittest
from greenwave.vision_contracts import decode_vision
from greenwave.vision_demos import vision_demo
from greenwave.vision_probe import class_semantics, make_detection, percentile, evaluate_boxes


class VisionProbeTests(unittest.TestCase):
    def frame(self):return decode_vision(vision_demo('good_detection')['detections'][0]).frame

    def test_class_mapping_preserves_red_yellow_and_unknown_pictogram(self):
        self.assertEqual(class_semantics('circle_red_yellow'),('RED_YELLOW','CIRCLE'))
        self.assertEqual(class_semantics('arrow_left_green'),('GREEN','ARROW_LEFT'))
        self.assertEqual(class_semantics('traffic light'),('UNKNOWN','UNKNOWN'))
        self.assertEqual(class_semantics('arrow_straight_left_green'),('GREEN','UNKNOWN'))

    def test_small_or_low_score_signal_is_unknown_and_bbox_uses_original_frame(self):
        frame=self.frame()
        small=make_detection(frame,(800,200,810,205),.9,'green','model','0'*64,0)
        weak=make_detection(frame,(800,200,840,300),.4,'green','model','0'*64,1)
        good=make_detection(frame,(-1,200,40,300),.9,'red','model','0'*64,2)
        self.assertEqual(small.state,'UNKNOWN');self.assertEqual(weak.state,'UNKNOWN')
        self.assertEqual(good.state,'RED');self.assertEqual(good.bbox_xyxy[0],0)
        self.assertEqual(decode_vision(good.to_json()),good)

    def test_invalid_output_and_empty_clipped_box_are_rejected(self):
        for bbox,score in [((0,0,10,20),float('nan')),((2000,0,2100,20),.9),
                           ((0,0,float('inf'),20),.9)]:
            with self.assertRaises(ValueError):make_detection(self.frame(),bbox,score,'red','m','0'*64,0)

    def test_percentile_handles_empty_single_and_interpolated_samples(self):
        self.assertIsNone(percentile([],.95));self.assertEqual(percentile([10],.95),10)
        self.assertEqual(percentile([10,20,30],.5),20)
        self.assertAlmostEqual(percentile([10,20,30],.95),29)

    def test_smoke_comparison_matches_geometry_before_scoring_color(self):
        detected=make_detection(self.frame(),(800,200,840,300),.9,'green','model','0'*64,0).to_dict()
        report=evaluate_boxes([detected],[dict(bbox_xyxy=[800,200,840,300],state='RED')])
        self.assertEqual(report['matched'],1);self.assertEqual(report['false_green_matched'],1)
        self.assertEqual(report['correct_states'],0)
        self.assertEqual(evaluate_boxes([], [dict(bbox_xyxy=[0,0,10,20],state='RED')])['missed'],1)
