from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tests.test_map_matching import make_route
from greenwave.route_events import StopLineCrossingDetector


def result(status='MATCHED', s=20, direction='FORWARD', uncertainty=2):
    return SimpleNamespace(status=status, accepted_s_m=s, direction=direction,
                           position_uncertainty_m=uncertainty)


class StopLineCrossingTests(unittest.TestCase):
    def test_starting_beyond_line_does_not_invent_crossing(self):
        with tempfile.TemporaryDirectory() as root:
            detector = StopLineCrossingDetector(make_route(root), 'trip')
            self.assertEqual(detector.update(result(s=90), sample_time_seconds=1), [])

    def test_confirmed_crossing_is_emitted_only_once(self):
        with tempfile.TemporaryDirectory() as root:
            detector = StopLineCrossingDetector(make_route(root), 'trip')
            detector.update(result(s=20), sample_time_seconds=1, sample_ref='before')
            events = detector.update(result(s=90), sample_time_seconds=2, sample_ref='after')
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['status'], 'CONFIRMED')
            self.assertEqual(detector.update(result(s=95), sample_time_seconds=3), [])

    def test_gap_and_wrong_direction_create_unconfirmed_events(self):
        with tempfile.TemporaryDirectory() as root:
            route = make_route(root)
            gap = StopLineCrossingDetector(route, 'gap')
            gap.update(result(s=20), sample_time_seconds=1, sample_ref='before')
            events = gap.update(result(s=90), sample_time_seconds=8, sample_ref='after')
            self.assertEqual(events[0]['reason_code'], 'CONTINUITY_GAP')
            wrong = StopLineCrossingDetector(route, 'wrong')
            wrong.update(result(s=20), sample_time_seconds=1, sample_ref='before')
            events = wrong.update(result(status='WRONG_DIRECTION', s=None, direction='REVERSE'),
                                  sample_time_seconds=2, sample_ref='turn')
            self.assertEqual(events[0]['status'], 'UNCONFIRMED')
            self.assertEqual(events[0]['reason_code'], 'MATCH_LOST_WRONG_DIRECTION')

    def test_uncertain_crossing_is_not_spammed(self):
        with tempfile.TemporaryDirectory() as root:
            detector = StopLineCrossingDetector(make_route(root), 'trip')
            self.assertEqual(detector.update(result(s=0), sample_time_seconds=1), [])
            first = detector.update(result(status='UNCERTAIN', s=None, direction='UNKNOWN'),
                                    sample_time_seconds=2)
            self.assertLessEqual(len(first), 1)
            detector.update(result(s=20), sample_time_seconds=3)
            second = detector.update(result(status='UNCERTAIN', s=None, direction='UNKNOWN'),
                                     sample_time_seconds=4)
            self.assertEqual(len(first) + len(second), 1)
