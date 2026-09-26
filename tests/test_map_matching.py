from pathlib import Path
import json
import tempfile
import unittest

from greenwave.map_matching import MapMatcher
from greenwave.positioning import PositionSample
from greenwave.route_events import StopLineCrossingDetector
from greenwave.route_geometry import load_route


def make_route(root, stop=True):
    value = dict(schema_version=1, route_id='north', geometry_version='v1', name='North',
        direction_description='northbound', coordinates=[[21.0, 52.0], [21.0, 52.001]],
        source={'attribution': 'synthetic'}, geometry_verification={'status': 'DRAFT'},
        speed_sections=[], stop_lines=[])
    if stop:
        value['stop_lines'] = [dict(stop_line_id='L1', signal_id='S1', segment_index=0,
            coordinates=[[20.9999, 52.0005], [21.0001, 52.0005]], direction='FORWARD', movement='STRAIGHT',
            source={'kind': 'synthetic'}, verification={'status': 'DRAFT'}, position_uncertainty_m=2)]
    path = Path(root) / 'north.json'; path.write_text(json.dumps(value), encoding='utf-8')
    return load_route(path)


def sample(latitude, *, sequence=1, heading=0, speed=5, accuracy=4, nanos=None):
    return PositionSample(elapsed_seconds=float(sequence), road_position_m=None, speed_mps=speed,
        latitude=latitude, longitude=21.0, heading_deg=heading, gps_accuracy_m=accuracy,
        source='ANDROID_FUSED', raw_speed_mps=speed, speed_source='DEVICE', position_quality='GOOD',
        usable_for_live=True, device_id='phone', stream_id='stream', sample_sequence=sequence,
        elapsed_realtime_nanos=nanos or sequence * 1_000_000_000,
        sent_elapsed_realtime_nanos=(nanos or sequence * 1_000_000_000) + 100_000_000,
        measurement_age_lower_bound_seconds=.1, freshness_status='FRESH', live_control_eligible=True,
        heading_accuracy_deg=5, is_mock=False)


class MapMatcherTests(unittest.TestCase):
    def test_dense_vertices_do_not_create_alternative_positions_on_one_road(self):
        with tempfile.TemporaryDirectory() as root:
            coarse = make_route(root, False)
            path = Path(root) / 'dense.json'
            value = json.loads((Path(root) / 'north.json').read_text(encoding='utf-8'))
            value['coordinates'] = [[21.0, 52.0 + index * .00003] for index in range(34)]
            value['coordinates'].append([21.0, 52.001])
            path.write_text(json.dumps(value), encoding='utf-8')
            matchers = [MapMatcher(coarse), MapMatcher(load_route(path))]
            # Include a fix before the start, movement and a stationary fix.
            for sequence, latitude in enumerate((51.99998, 52.00001, 52.00007,
                                                  52.00013, 52.00013), 1):
                results = [matcher.update(sample(latitude, sequence=sequence, accuracy=10,
                                                 speed=0 if sequence == 5 else 5),
                                          measurement_age_lower_bound_seconds=.1)
                           for matcher in matchers]
                self.assertEqual(results[0].status, results[1].status)
                self.assertAlmostEqual(results[0].candidate_s_m, results[1].candidate_s_m, places=5)
            self.assertEqual(results[1].status, 'MATCHED')

    def test_acquires_then_matches_forward_and_crosses_once(self):
        with tempfile.TemporaryDirectory() as root:
            route = make_route(root)
            matcher = MapMatcher(route)
            first = matcher.update(sample(52.0002, sequence=1), sample_ref='1',
                                   measurement_age_lower_bound_seconds=.1)
            self.assertEqual(first.status, 'ACQUIRING')
            second = matcher.update(sample(52.0003, sequence=2), sample_ref='2',
                                    measurement_age_lower_bound_seconds=.1)
            self.assertEqual(second.status, 'MATCHED')
            self.assertEqual(second.direction, 'FORWARD')
            detector = StopLineCrossingDetector(route, 'trip')
            detector.update(second, sample_time_seconds=2, sample_ref='2')
            third = matcher.update(sample(52.0008, sequence=5, speed=20), sample_ref='3',
                                   measurement_age_lower_bound_seconds=.1)
            events = detector.update(third, sample_time_seconds=5, sample_ref='3')
            self.assertEqual(len(events), 1)
            self.assertEqual(detector.update(third, sample_time_seconds=3.1), [])

    def test_stale_and_bad_accuracy_are_never_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            matcher = MapMatcher(make_route(root, False))
            stale = matcher.update(sample(52.0002), measurement_age_lower_bound_seconds=6)
            self.assertEqual(stale.status, 'STALE')
            poor = matcher.update(sample(52.0002, accuracy=40), measurement_age_lower_bound_seconds=.1)
            self.assertEqual(poor.status, 'UNCERTAIN')
            self.assertIsNone(poor.accepted_s_m)

    def test_capture_age_and_receipt_age_are_combined(self):
        with tempfile.TemporaryDirectory() as root:
            matcher = MapMatcher(make_route(root, False))
            matcher.update(sample(52.0002, sequence=1),
                           measurement_age_lower_bound_seconds=4.5)
            matched = matcher.update(sample(52.0003, sequence=2),
                                     measurement_age_lower_bound_seconds=4.5)
            self.assertEqual(matched.status, 'MATCHED')
            current = matcher.current(receipt_age_seconds=0.6)
            self.assertEqual(current.status, 'STALE')
            self.assertIn('MEASUREMENT_STALE', current.reason_codes)
            self.assertIsNone(current.accepted_s_m)

    def test_uncertainty_between_sides_prevents_confirmed_crossing(self):
        with tempfile.TemporaryDirectory() as root:
            route = make_route(root)
            matcher = MapMatcher(route)
            detector = StopLineCrossingDetector(route, 'trip')
            matcher.update(sample(52.0001, sequence=1), measurement_age_lower_bound_seconds=.1)
            before = matcher.update(sample(52.0002, sequence=2), measurement_age_lower_bound_seconds=.1)
            detector.update(before, sample_time_seconds=2, sample_ref='before')
            uncertain = matcher.update(sample(52.0002, sequence=3, accuracy=40),
                                       measurement_age_lower_bound_seconds=.1)
            interrupted = detector.update(uncertain, sample_time_seconds=3, sample_ref='bad')
            self.assertEqual(interrupted[0]['status'], 'UNCONFIRMED')
            after = matcher.update(sample(52.0008, sequence=4), measurement_age_lower_bound_seconds=.1,
                                   continuity_reset=True)
            after = matcher.update(sample(52.00085, sequence=5), measurement_age_lower_bound_seconds=.1)
            self.assertEqual(detector.update(after, sample_time_seconds=5, sample_ref='after'), [])
            self.assertFalse(any(event.status == 'CONFIRMED' for event in detector.events))

    def test_off_route_requires_confirmation_and_reverse_is_explicit(self):
        with tempfile.TemporaryDirectory() as root:
            matcher = MapMatcher(make_route(root, False))
            off = None
            for index in range(1, 4):
                value = sample(52.0002, sequence=index)
                value = PositionSample(**{**value.__dict__, 'longitude': 21.01})
                off = matcher.update(value, measurement_age_lower_bound_seconds=.1)
            self.assertEqual(off.status, 'OFF_ROUTE')
            matcher.reset()
            matcher.update(sample(52.0008, sequence=10, heading=180), measurement_age_lower_bound_seconds=.1)
            reverse = matcher.update(sample(52.0007, sequence=11, heading=180), measurement_age_lower_bound_seconds=.1)
            self.assertEqual(reverse.status, 'WRONG_DIRECTION')
            self.assertIsNone(reverse.accepted_s_m)

    def test_stationary_heading_is_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            matcher = MapMatcher(make_route(root, False))
            matcher.update(sample(52.0002, sequence=1, heading=180, speed=.1),
                           measurement_age_lower_bound_seconds=.1)
            current = matcher.update(sample(52.0002, sequence=2, heading=180, speed=.1),
                                     measurement_age_lower_bound_seconds=.1)
            self.assertEqual(current.status, 'MATCHED')
            self.assertEqual(current.direction, 'UNKNOWN')

    def test_gap_requires_reacquisition(self):
        with tempfile.TemporaryDirectory() as root:
            matcher = MapMatcher(make_route(root, False))
            matcher.update(sample(52.0001, sequence=1), measurement_age_lower_bound_seconds=.1)
            self.assertEqual(matcher.update(sample(52.0002, sequence=2),
                                            measurement_age_lower_bound_seconds=.1).status, 'MATCHED')
            reacquire = matcher.update(sample(52.0005, sequence=10, nanos=10_000_000_000),
                                       measurement_age_lower_bound_seconds=.1,
                                       continuity_reset=True)
            self.assertEqual(reacquire.status, 'ACQUIRING')
            self.assertEqual(matcher.update(sample(52.00055, sequence=11, nanos=11_000_000_000),
                                            measurement_age_lower_bound_seconds=.1).status, 'MATCHED')

    def test_impossible_jump_is_not_forced_onto_route(self):
        with tempfile.TemporaryDirectory() as root:
            matcher = MapMatcher(make_route(root, False))
            matcher.update(sample(52.0001, sequence=1, speed=1),
                           measurement_age_lower_bound_seconds=.1)
            jump = matcher.update(sample(52.0009, sequence=2, speed=1),
                                  measurement_age_lower_bound_seconds=.1)
            self.assertEqual(jump.status, 'UNCERTAIN')
            self.assertIn('IMPOSSIBLE_TRANSITION', jump.reason_codes)
            self.assertIsNone(jump.accepted_s_m)

    def test_parallel_return_segments_remain_ambiguous_without_heading(self):
        with tempfile.TemporaryDirectory() as root:
            value = dict(schema_version=1, route_id='hairpin', geometry_version='v1', name='Hairpin',
                direction_description='out and back',
                coordinates=[[21,52],[21,52.001],[21.0001,52.001],[21.0001,52]],
                source={'attribution':'synthetic'}, geometry_verification={'status':'DRAFT'},
                speed_sections=[], stop_lines=[])
            path = Path(root) / 'hairpin.json'; path.write_text(json.dumps(value), encoding='utf-8')
            matcher = MapMatcher(load_route(path))
            point = sample(52.0005, heading=None, speed=.1)
            point = PositionSample(**{**point.__dict__, 'longitude': 21.00005})
            match = matcher.update(point, measurement_age_lower_bound_seconds=.1)
            self.assertEqual(match.status, 'UNCERTAIN')
            self.assertIn('AMBIGUOUS_CANDIDATES', match.reason_codes)

    def test_corner_changes_segment_without_losing_forward_match(self):
        with tempfile.TemporaryDirectory() as root:
            value = dict(schema_version=1, route_id='turn', geometry_version='v1', name='Turn',
                direction_description='north then east',
                coordinates=[[21,52],[21,52.0005],[21.0005,52.0005]],
                source={'attribution':'synthetic'}, geometry_verification={'status':'DRAFT'},
                speed_sections=[], stop_lines=[])
            path = Path(root) / 'turn.json'; path.write_text(json.dumps(value), encoding='utf-8')
            matcher = MapMatcher(load_route(path))
            points = [(52.0002,21,0),(52.0004,21,0),(52.0005,21.0001,90)]
            result = None
            for sequence, (latitude, longitude, heading) in enumerate(points, 1):
                value = sample(latitude, sequence=sequence, heading=heading)
                value = PositionSample(**{**value.__dict__, 'longitude': longitude})
                result = matcher.update(value, measurement_age_lower_bound_seconds=.1)
            self.assertEqual(result.status, 'MATCHED')
            self.assertEqual(result.candidate_segment_index, 1)
            self.assertEqual(result.direction, 'FORWARD')

    def test_history_disambiguates_a_self_intersection(self):
        with tempfile.TemporaryDirectory() as root:
            value = dict(schema_version=1, route_id='cross', geometry_version='v1', name='Cross',
                direction_description='first diagonal',
                coordinates=[[21,52],[21.001,52.001],[21,52.001],[21.001,52]],
                source={'attribution':'synthetic'}, geometry_verification={'status':'DRAFT'},
                speed_sections=[], stop_lines=[])
            path = Path(root) / 'cross.json'; path.write_text(json.dumps(value), encoding='utf-8')
            matcher = MapMatcher(load_route(path))
            result = None
            for sequence, coordinate in enumerate(((52.0002,21.0002),(52.0004,21.0004),
                                                    (52.0005,21.0005)), 1):
                value = sample(coordinate[0], sequence=sequence, heading=32, speed=8)
                value = PositionSample(**{**value.__dict__, 'longitude': coordinate[1]})
                result = matcher.update(value, measurement_age_lower_bound_seconds=.1)
            self.assertEqual(result.status, 'MATCHED')
            self.assertEqual(result.candidate_segment_index, 0)
