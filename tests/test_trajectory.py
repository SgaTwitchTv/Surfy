from dataclasses import replace
import json
import math
import unittest

from greenwave.application import GreenWaveApplication
from greenwave.clocks import SimulationClock
from greenwave.prediction import GreenWindow, PredictionEngine
from greenwave.solver import SingleSignalSolver, arrival_time, profile_distance
from greenwave.trajectory import TrajectorySettings, TrajectorySolver


class TrajectoryTests(unittest.TestCase):
    def setUp(self):
        app = GreenWaveApplication()
        self.base = app.prediction.predict('S1', 0)
        self.solver = TrajectorySolver(SingleSignalSolver())

    def prediction(self, id, windows, confidence=.95):
        return replace(self.base, signal_id=id, valid_until=240, confidence=confidence,
            windows=tuple(GreenWindow(id, a, b, 0, a, b, confidence, 'fixture', 0) for a,b in windows))

    def solve(self, points, speed=50/3.6, **kwargs):
        return self.solver.solve(points, position=0, speed=speed, speed_limit=50/3.6, now=0, **kwargs)

    def trap(self):
        return [(300,self.prediction('S1',[(0,70),(120,155)])),
                (700,self.prediction('S2',[(97,112),(197,212)]))]

    def test_lookahead_slows_before_first_to_avoid_greedy_stop_at_second(self):
        raw, plan = self.solve(self.trap())
        self.assertEqual(plan['status'], 'COMPLETE')
        self.assertEqual(plan['cost']['raw']['stops'], 0)
        self.assertEqual(plan['baseline']['cost']['raw']['stops'], 1)
        self.assertLess(raw.target_kmh, plan['baseline']['legs'][0]['target_kmh'])
        self.assertLess(plan['cost']['total'], plan['baseline']['cost']['total'])
        self.assertEqual(raw.range_min_kmh, raw.range_max_kmh)

    def test_each_leg_integrates_to_distance_and_crossing_state_is_continuous(self):
        _, plan = self.solve(self.trap())
        previous_speed = 50/3.6
        previous_time = 0
        for leg in plan['legs']:
            c = leg['candidate']
            self.assertAlmostEqual(leg['start_speed_mps'], previous_speed)
            self.assertAlmostEqual(leg['start_at'], previous_time)
            distance = profile_distance(leg['duration'], previous_speed, leg['target_kmh']/3.6,
                c['acceleration_mps2'], c['deceleration_mps2'], c['reaction_seconds'])
            self.assertAlmostEqual(distance, leg['distance_m'])
            self.assertGreaterEqual(leg['arrival_at'], c['interior_start']-1e-6)
            self.assertLessEqual(leg['arrival_at'], c['interior_end']+1e-6)
            self.assertLessEqual(leg['crossing_speed_mps'], 50/3.6)
            previous_speed, previous_time = leg['crossing_speed_mps'], leg['arrival_at']

    def test_crossing_during_ramp_does_not_assume_target_already_reached(self):
        _, plan = self.solve([(10,self.prediction('S1',[(0,100)])),
                              (200,self.prediction('S2',[(0,100)]))], speed=0)
        first, second = plan['legs']
        self.assertLess(first['crossing_speed_mps'], first['target_kmh']/3.6)
        self.assertEqual(second['start_speed_mps'], first['crossing_speed_mps'])

    def test_required_stop_wait_and_restart_are_physical(self):
        raw, plan = self.solve([(300,self.prediction('S1',[(100,120)]))], speed=10)
        self.assertEqual(raw.status, 'STOP_REQUIRED')
        leg = plan['legs'][0]
        self.assertEqual(leg['stops'], 1)
        self.assertGreater(leg['wait_seconds'], 0)
        self.assertAlmostEqual(leg['stop_distance_m'], 10+100/3)
        self.assertLess(leg['stop_distance_m'], 298)
        c = leg['candidate']
        distance = profile_distance(leg['arrival_at']-leg['departure_at'], 0, leg['target_kmh']/3.6,
            c['acceleration_mps2'], c['deceleration_mps2'], c['reaction_seconds'])
        self.assertAlmostEqual(distance+leg['stop_distance_m'], 300)

    def test_already_stationary_does_not_count_initial_stop(self):
        _, plan = self.solve([(300,self.prediction('S1',[(100,120)]))], speed=0)
        self.assertEqual(plan['cost']['raw']['stops'], 0)

    def test_unknown_middle_point_is_boundary_not_skipped(self):
        points=self.trap()
        points.insert(1,(400,replace(self.prediction('UNKNOWN',[]),reason='unknown')))
        raw, plan=self.solve(points)
        self.assertEqual(plan['status'],'PARTIAL')
        self.assertEqual([l['signal_id'] for l in plan['legs']],['S1'])
        self.assertEqual(plan['boundary'],'UNKNOWN')

    def test_unknown_first_withdraws_target(self):
        raw, plan=self.solve([(300,replace(self.base,reason='stale'))])
        self.assertEqual(raw.status,'NO_PREDICTION')
        self.assertIsNone(raw.target_kmh)
        self.assertEqual(plan['legs'],[])

    def test_horizon_and_number_of_points_are_bounded(self):
        self.solver=TrajectorySolver(SingleSignalSolver(),TrajectorySettings(max_signals=1))
        _, plan=self.solve(self.trap())
        self.assertEqual(len(plan['legs']),1)
        self.solver=TrajectorySolver(SingleSignalSolver(),TrajectorySettings(horizon_seconds=5))
        raw, plan=self.solve(self.trap())
        self.assertIsNone(raw.target_kmh)
        self.assertEqual(plan['status'],'NO_PLAN')

    def test_cost_breakdown_and_configurable_weights(self):
        _, plan=self.solve(self.trap())
        cost=plan['cost']
        self.assertAlmostEqual(cost['total'],sum(cost['weighted'].values()))
        self.solver=TrajectorySolver(SingleSignalSolver(),TrajectorySettings(stop_weight=0,braking_weight=0,variation_weight=0,time_weight=1,risk_weight=0))
        _, other=self.solve(self.trap())
        self.assertAlmostEqual(other['cost']['total'],other['cost']['raw']['time'])
        self.assertGreater(other['cost']['raw']['stops'],0)

    def test_unknown_confidence_cost_is_explicit_and_no_nan_in_output(self):
        raw, plan=self.solve([(300,self.prediction('S1',[(0,100)],None))],speed=0)
        self.assertEqual(plan['cost']['raw']['risk'],.5)
        self.assertLessEqual(raw.acceleration_mps2,.8)
        json.dumps(plan,allow_nan=False)

    def test_invalid_configuration_and_input(self):
        for value in (dict(beam_width=0),dict(max_signals=True),dict(horizon_seconds=math.inf),dict(stop_weight=-1),dict(unknown_risk=2)):
            with self.assertRaises(ValueError):TrajectorySettings(**value)
        with self.assertRaises(ValueError):self.solve([(math.nan,self.base)])

    def test_future_observation_replans_entire_corridor_immediately(self):
        app=GreenWaveApplication()
        before=app.trajectory
        app.observe('S3','GREEN','STATE_START')
        self.assertEqual(app.trajectory['model_version'],1)
        self.assertNotEqual(before['legs'],app.trajectory['legs'])
        self.assertEqual(app.recommendation.model_version,1)
        app.observe('S2','GREEN','STATE_SEEN')
        self.assertEqual(app.trajectory['boundary'],'S2')
        self.assertEqual(len(app.trajectory['legs']),1)

    def test_deterministic_results(self):
        self.assertEqual(self.solve(self.trap()),self.solve(self.trap()))

    def test_unknown_close_boundary_does_not_get_unstoppable_approach(self):
        raw, plan=self.solve([(300,self.prediction('S1',[(0,70)])),
                             (301,replace(self.base,signal_id='S2',reason='unknown'))])
        self.assertIsNone(raw.target_kmh)
        self.assertEqual(plan['status'],'NO_PLAN')

    def test_integrated_driver_executes_lookahead_and_required_stop(self):
        for stop_required in (False,True):
            with self.subTest(stop_required=stop_required):
                now=[0.0]
                app=GreenWaveApplication(SimulationClock(lambda:now[0]))
                if stop_required:
                    signals=(replace(app.corridor.signals[0],green_duration=25,offset=100),)
                else:
                    signals=(replace(app.corridor.signals[0],green_duration=70,offset=0),
                             replace(app.corridor.signals[1],green_duration=15,offset=97))
                app.corridor=replace(app.corridor,signals=signals)
                app.prediction=PredictionEngine(app.corridor,app.session_id)
                app.position.pending.clear()
                app.position.last_command=None
                app.position.speed=app.position.target=10 if stop_required else 50/3.6
                app._plan()
                app.control(running=True)
                stopped=False
                for i in range(1,150):
                    now[0]=i
                    state=app.snapshot()
                    stopped |= app.position.speed<=.05
                    self.assertIsNone(state['incident'])
                    if not state['running']:break
                self.assertEqual(app.recommendation.status,'COMPLETE')
                self.assertEqual(stopped,stop_required)
                self.assertEqual(len(state['crossings']),len(signals))
                self.assertTrue(all(c['state']=='GREEN' for c in state['crossings']))


if __name__=='__main__':unittest.main()
