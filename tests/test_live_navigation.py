import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from greenwave.live_navigation import evaluate_live_navigation
from greenwave.positioning import PositionSample
from greenwave.route_geometry import load_route


def field_route(root):
    value = dict(
        schema_version=1, route_id='field', geometry_version='v1', name='Field route',
        direction_description='north', coordinates=[[21.0, 52.0], [21.0, 52.001]],
        source={'attribution': 'synthetic'}, geometry_verification={'status': 'FIELD_CHECKED'},
        speed_sections=[dict(start_s_m=0, end_s_m=100, limit_mps=13.89,
                             source={'kind': 'test'}, verification={'status': 'FIELD_CHECKED'})],
        stop_lines=[dict(stop_line_id='L1', signal_id='S1', segment_index=0,
                         coordinates=[[20.9999, 52.0006], [21.0001, 52.0006]],
                         direction='FORWARD', movement='STRAIGHT', source={'kind': 'test'},
                         verification={'status': 'FIELD_CHECKED'}, position_uncertainty_m=2)])
    path = Path(root) / 'field.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    return load_route(path)


class LiveNavigationTests(unittest.TestCase):
    def test_builds_explicit_solver_input_only_after_all_checks(self):
        with tempfile.TemporaryDirectory() as root:
            route = field_route(root)
            result = SimpleNamespace(status='MATCHED', direction='FORWARD', accepted_s_m=20,
                                     position_uncertainty_m=4, sample_ref='p:s:3')
            sample = PositionSample(100, None, 8, latitude=52, longitude=21,
                                    live_control_eligible=True)
            gate = evaluate_live_navigation(
                route, result, sample, {'live_control_eligible': True},
                prediction_time_seconds=15, phase_data_verified=True)
            self.assertTrue(gate['allowed'])
            self.assertEqual(gate['solver_input']['position_s_m'], 20)
            self.assertEqual(gate['solver_input']['speed_mps'], 8)
            self.assertEqual(gate['solver_input']['signal_id'], 'S1')

    def test_withdraws_input_and_reports_all_missing_conditions(self):
        result = SimpleNamespace(status='STALE', direction='UNKNOWN', accepted_s_m=None,
                                 position_uncertainty_m=None, sample_ref='old')
        gate = evaluate_live_navigation(None, result, None, {'live_control_eligible': False})
        self.assertFalse(gate['allowed'])
        self.assertIsNone(gate['solver_input'])
        self.assertIn('POSITION_NOT_FRESH_OR_UNVERIFIED', gate['reason_codes'])
        self.assertIn('ROUTE_NOT_MATCHED', gate['reason_codes'])
        self.assertIn('LIVE_PHASE_DATA_UNAVAILABLE', gate['reason_codes'])
        self.assertIn('PREDICTION_CLOCK_UNAVAILABLE', gate['reason_codes'])
