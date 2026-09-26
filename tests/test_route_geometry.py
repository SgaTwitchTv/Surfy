from pathlib import Path
import json
import tempfile
import unittest

from greenwave.route_geometry import RouteRegistry, load_route


def route_document(**changes):
    value = dict(schema_version=1, route_id='test_route', geometry_version='v1', name='Test',
        direction_description='south to north', coordinates=[[21.0, 52.0], [21.0, 52.001]],
        source={'attribution': 'synthetic test'},
        geometry_verification={'status': 'DRAFT', 'date': '2026-09-18'},
        speed_sections=[], stop_lines=[])
    value.update(changes)
    return value


class RouteGeometryTests(unittest.TestCase):
    def write(self, root, value, name='test_route.json'):
        path = Path(root) / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_recording_route_association_requires_exact_source_run_id(self):
        run_id = 'a' * 32
        with tempfile.TemporaryDirectory() as root:
            self.write(root, route_document(source={'attribution': 'synthetic', 'run_id': run_id}))
            registry = RouteRegistry(root)
            self.assertEqual(registry.for_recording(run_id).route_id, 'test_route')
            self.assertIsNone(registry.for_recording('b' * 32))
            self.assertIsNone(registry.for_recording('../bad'))

    def test_projection_uses_metres_and_clamps_to_segment(self):
        with tempfile.TemporaryDirectory() as root:
            route = load_route(self.write(root, route_document()))
            self.assertAlmostEqual(route.length_m, 111.2, delta=.5)
            middle = route.project(21.00005, 52.0005)[0]
            self.assertAlmostEqual(middle.s_m, route.length_m / 2, delta=.5)
            self.assertGreater(middle.cross_track_m, 3)
            beyond = route.project(21.0, 52.002)[0]
            self.assertAlmostEqual(beyond.s_m, route.length_m)

    def test_stop_line_is_bound_to_assigned_segment(self):
        value = route_document(stop_lines=[dict(stop_line_id='L1', signal_id='S1', segment_index=0,
            coordinates=[[20.9999, 52.0005], [21.0001, 52.0005]], direction='FORWARD', movement='STRAIGHT',
            source={'kind': 'synthetic'}, verification={'status': 'DRAFT'}, position_uncertainty_m=2)])
        with tempfile.TemporaryDirectory() as root:
            route = load_route(self.write(root, value))
            self.assertAlmostEqual(route.stop_lines[0].s_m, route.length_m / 2, delta=.5)

    def test_invalid_or_oversized_routes_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                load_route(self.write(root, route_document(coordinates=[[21, 52], [21, 52]])))
            with self.assertRaises(ValueError):
                load_route(self.write(root, route_document(coordinates=[[21, 52], [21, 53]])))

    def test_registry_does_not_accept_paths_from_route_id(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, route_document())
            registry = RouteRegistry(root)
            self.assertEqual(registry.load('test_route').route_id, 'test_route')
            with self.assertRaises(ValueError): registry.load('../secret')

    def test_loop_keeps_distinct_occurrences_at_the_same_coordinate(self):
        value = route_document(coordinates=[[21,52],[21,52.001],[21.0001,52.001],
                                            [21.0001,52],[21,52]])
        with tempfile.TemporaryDirectory() as root:
            route = load_route(self.write(root, value))
            occurrences = route.project(21, 52)
            self.assertGreaterEqual(len(occurrences), 2)
            self.assertEqual(occurrences[0].s_m, 0)
            self.assertAlmostEqual(max(item.s_m for item in occurrences), route.length_m)

    def test_hash_changes_with_canonical_geometry_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            first = load_route(self.write(root, route_document(), 'first.json'))
            second = load_route(self.write(root, route_document(name='Changed'), 'second.json'))
            self.assertNotEqual(first.geometry_hash, second.geometry_hash)

    def test_overlapping_speed_sections_and_invalid_stop_direction_are_rejected(self):
        sections = [
            dict(start_s_m=0, end_s_m=80, limit_mps=10, source={'kind':'test'},
                 verification={'status':'DRAFT'}),
            dict(start_s_m=70, end_s_m=100, limit_mps=12, source={'kind':'test'},
                 verification={'status':'DRAFT'})]
        stop = dict(stop_line_id='L1', signal_id='S1', segment_index=0,
                    coordinates=[[20.9999,52.0005],[21.0001,52.0005]], direction='SIDEWAYS',
                    movement='STRAIGHT', source={'kind':'test'},
                    verification={'status':'DRAFT'}, position_uncertainty_m=2)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                load_route(self.write(root, route_document(speed_sections=sections), 'speed.json'))
            with self.assertRaises(ValueError):
                load_route(self.write(root, route_document(stop_lines=[stop]), 'stop.json'))

    def test_arkadia_pilot_fixture_has_reviewable_boundaries_and_draft_lines(self):
        path = Path(__file__).parents[1] / 'data/routes/arkadia_maczka_okopowa_v1.json'
        route = load_route(path)
        self.assertEqual(route.geometry_verification['status'], 'DESK_CHECKED')
        self.assertAlmostEqual(route.length_m, 3755, delta=20)
        self.assertLess(route.project(20.932530, 52.268550)[0].cross_track_m, 10)
        self.assertLess(route.project(20.981089, 52.253278)[0].cross_track_m, 10)
        self.assertEqual(len(route.stop_lines), 10)
        self.assertTrue(all(line.verification['status'] == 'DRAFT' for line in route.stop_lines))
        self.assertEqual(route.stop_lines[-1].stop_line_id, 'SL10_POWAZKOWSKA_OKOPOWA')
        self.assertEqual(route.speed_sections[0]['verification']['status'], 'DESK_CHECKED')
        self.assertAlmostEqual(route.speed_sections[0]['limit_mps'] * 3.6, 50)
