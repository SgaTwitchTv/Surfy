from dataclasses import replace
import unittest
from greenwave.vehicle import DynamicVehicle
from greenwave.models import load_corridor
from greenwave.application import DATA


class VehicleTests(unittest.TestCase):
    def setUp(self):
        self.vehicle=DynamicVehicle()
        self.signal=load_corridor(DATA/'corridors/synthetic_s1_s5.json').signals[0]

    def test_reaction_delay_then_bounded_acceleration(self):
        self.vehicle.command(10)
        for _ in range(10):self.vehicle.step(.1,14)
        self.assertEqual(self.vehicle.speed,0)
        self.vehicle.step(.1,14)
        self.assertAlmostEqual(self.vehicle.speed,.1)
        for _ in range(300):self.vehicle.step(.1,14)
        self.assertAlmostEqual(self.vehicle.speed,10)

    def test_deceleration_does_not_jump_or_go_negative(self):
        self.vehicle.speed=10
        self.vehicle.command(0)
        for _ in range(100):
            previous=self.vehicle.speed
            self.vehicle.step(.1,14)
            self.assertLessEqual(abs(self.vehicle.speed-previous),.150001)
            self.assertGreaterEqual(self.vehicle.speed,0)
        self.assertEqual(self.vehicle.speed,0)

    def test_red_stops_before_line_then_green_allows_departure(self):
        self.vehicle.speed=10
        self.vehicle.command(10)
        signal=replace(self.signal,road_position_m=80)
        for _ in range(200):self.vehicle.step(.1,14,signal,lambda *_:'RED')
        self.assertIsNone(self.vehicle.incident)
        self.assertLess(self.vehicle.position,80)
        self.assertLess(self.vehicle.speed,.11)
        for _ in range(200):
            if self.vehicle.crossings:break
            self.vehicle.step(.1,14,signal,lambda *_:'GREEN')
        self.assertEqual(self.vehicle.crossings[0]['state'],'GREEN')

    def test_impossible_red_stop_reports_incident_without_teleporting(self):
        self.vehicle.speed=14
        before=self.vehicle.position
        self.vehicle.step(.1,14,replace(self.signal,road_position_m=3),lambda *_:'RED')
        self.assertIsNotNone(self.vehicle.incident)
        self.assertEqual(self.vehicle.position,before)
        self.assertEqual(self.vehicle.speed,14)

    def test_phase_change_at_crossing_is_checked(self):
        self.vehicle.speed=10
        signal=replace(self.signal,road_position_m=.5)
        self.vehicle.step(.1,14,signal,lambda s,t:'GREEN' if t<.02 else 'RED')
        self.assertIsNotNone(self.vehicle.incident)
        self.assertFalse(self.vehicle.crossings)
