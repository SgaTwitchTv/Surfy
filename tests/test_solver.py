from dataclasses import replace
import math
import unittest
from greenwave.models import load_corridor
from greenwave.prediction import PredictionEngine,GreenWindow
from greenwave.application import DATA
from greenwave.solver import SingleSignalSolver,RecommendationStabilizer,profile_distance,arrival_time,average_speed_window


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.solver=SingleSignalSolver()
        corridor=load_corridor(DATA/'corridors/synthetic_s1_s5.json')
        self.base=PredictionEngine(corridor,'test').predict('S1',0)

    def prediction(self,windows,confidence=.95,margin=0):
        return replace(self.base,reason='',confidence=confidence,valid_until=1000,windows=tuple(
            GreenWindow('S1',start,end,margin,start,end,confidence,'test',0) for start,end in windows))

    def solve(self,windows,distance=500,speed=10,limit=50/3.6,**kwargs):
        return self.solver.solve(self.prediction(windows,**kwargs),distance=distance,speed=speed,speed_limit=limit,now=0)

    def test_single_signal_average_speed_window(self):
        low,high=average_speed_window(500,0,40,55,5,50/3.6)
        self.assertAlmostEqual(low*3.6,32.7272727)
        self.assertAlmostEqual(high*3.6,45)
        self.assertIsNone(average_speed_window(500,60,40,55,5,14))

    def test_analytical_profile_and_inverse_for_acceleration_and_braking(self):
        for initial,target in [(0,10),(10,5),(10,10),(12,2)]:
            for seconds in (1,3,10,40):
                d=profile_distance(seconds,initial,target,1,.5,1)
                if d>0:self.assertAlmostEqual(arrival_time(d,initial,target,1,.5,1),seconds)

    def test_speed_limit_and_every_integer_in_reported_range(self):
        result=self.solve([(40,65)])
        self.assertEqual(result.status,'READY')
        self.assertLessEqual(result.range_max_kmh,50)
        for target in range(result.range_min_kmh,result.range_max_kmh+1):
            arrival=arrival_time(500,10,target/3.6,result.acceleration_mps2,result.deceleration_mps2,1)
            self.assertGreaterEqual(arrival,40.5-1e-6)
            self.assertLessEqual(arrival,64.5+1e-6)

    def test_later_window_selected_when_first_is_unreachable(self):
        r=self.solve([(1,5),(40,70)])
        self.assertEqual(r.status,'READY')
        self.assertEqual(r.window_start,40)

    def test_no_stop_solution_reports_failure_without_fake_target(self):
        r=self.solve([(1,5)])
        self.assertEqual(r.status,'STOP_REQUIRED')
        self.assertIsNone(r.target_kmh)

    def test_reaction_delay_can_make_near_signal_unreachable(self):
        r=self.solve([(2,4)],distance=5,speed=10)
        self.assertEqual(r.status,'UNSAFE')
        self.assertIsNone(r.target_kmh)

    def test_unknown_or_expired_prediction_immediately_withdraws_target(self):
        for p in (None,replace(self.base,reason='unknown'),replace(self.base,valid_until=0)):
            r=self.solver.solve(p,distance=500,speed=10,speed_limit=14,now=0)
            self.assertEqual(r.status,'NO_PREDICTION')
            self.assertIsNone(r.target_kmh)

    def test_already_passed_point(self):
        self.assertEqual(self.solve([(40,60)],distance=-1).status,'PASSED')

    def test_current_green_handles_nonpositive_window_start(self):
        r=self.solve([(-10,40)],distance=200)
        self.assertEqual(r.status,'READY')
        self.assertLess(r.arrival_at,39.5)

    def test_no_instant_speed_jump_from_standstill(self):
        r=self.solve([(1,20)],distance=200,speed=0)
        self.assertNotEqual(r.status,'READY')
        r=self.solve([(20,50)],distance=200,speed=0)
        self.assertEqual(r.status,'READY')
        self.assertGreater(r.arrival_at,200/(r.target_kmh/3.6))

    def test_low_confidence_and_large_uncertainty_cannot_trigger_acceleration(self):
        for kwargs in (dict(confidence=.2),dict(margin=12)):
            r=self.solve([(20,30)],distance=350,speed=5,**kwargs)
            self.assertNotEqual(r.status,'READY')

    def test_unknown_confidence_caps_acceleration(self):
        r=self.solve([(20,60)],distance=200,speed=0,confidence=None)
        self.assertEqual(r.status,'READY')
        self.assertLessEqual(r.acceleration_mps2,.8)

    def test_prefers_coast_when_it_is_feasible(self):
        r=self.solve([(45,70)],distance=500,speed=13)
        self.assertEqual(r.status,'READY')
        self.assertEqual(r.deceleration_mps2,self.solver.vehicle.coast_deceleration)

    def test_limit_below_minimum_and_invalid_input(self):
        self.assertNotEqual(self.solve([(40,60)],limit=3).status,'READY')
        with self.assertRaises(ValueError):self.solve([(40,60)],distance=math.nan)

    def test_stabilizer_never_keeps_invalid_target(self):
        stable=RecommendationStabilizer(self.solver)
        ready=self.solve([(40,65)])
        stable.update(ready,now=0,distance=500,speed=10)
        invalid=replace(ready,status='NO_PREDICTION',target_kmh=None,range_min_kmh=None,range_max_kmh=None)
        result=stable.update(invalid,now=.1,distance=500,speed=10)
        self.assertIsNone(result.target_kmh)

    def test_stabilizer_holds_only_within_new_feasible_range(self):
        stable=RecommendationStabilizer(self.solver)
        ready=self.solve([(40,65)])
        first=stable.update(ready,now=0,distance=500,speed=10)
        second=stable.update(ready,now=.1,distance=499,speed=10)
        self.assertEqual(first.target_kmh,second.target_kmh)
        changed=self.solve([(25,40)],distance=400)
        if changed.status=='READY':
            second=stable.update(changed,now=.2,distance=400,speed=10)
            self.assertTrue(changed.range_min_kmh<=second.target_kmh<=changed.range_max_kmh)

    def test_action_classes(self):
        self.assertEqual(self.solver.command(36,10,'COAST'),'HOLD')
        self.assertEqual(self.solver.command(40,10,'COAST'),'ACCELERATE')
        for mode in ('COAST','ENGINE_BRAKE','BRAKE'):
            self.assertEqual(self.solver.command(30,10,mode),mode)

    def test_existing_command_keeps_remaining_reaction_delay(self):
        prediction=self.prediction([(0,33)])
        r=self.solver.solve(prediction,distance=300,speed=0,speed_limit=50/3.6,now=.5,
            committed_command=(50/3.6,1,.15),committed_reaction_seconds=.5)
        self.assertEqual(r.status,'READY')
        self.assertLessEqual(r.arrival_at,32.5)

    def test_random_feasible_ranges_respect_windows_and_limits(self):
        import random
        rng=random.Random(17)
        for _ in range(100):
            distance=rng.uniform(20,700);speed=rng.uniform(0,50/3.6)
            start=rng.uniform(0,70);end=start+rng.uniform(5,40)
            result=self.solve([(start,end)],distance=distance,speed=speed)
            if result.status!='READY':continue
            for target in (result.range_min_kmh,result.target_kmh,result.range_max_kmh):
                arrival=arrival_time(distance,speed,target/3.6,result.acceleration_mps2,result.deceleration_mps2,result.reaction_seconds)
                self.assertTrue(start+.5-1e-6<=arrival<=end-.5+1e-6)
                self.assertTrue(18<=target<=50)
