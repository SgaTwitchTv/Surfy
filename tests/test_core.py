from dataclasses import replace
from pathlib import Path
import unittest
from greenwave.models import load_corridor, SignalType
from greenwave.positioning import SimulationPositionProvider
from greenwave.simulation import SignalSimulator, SimulationSettings

DATA = Path(__file__).resolve().parents[1] / 'data/corridors'


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.corridor = load_corridor(DATA / 'synthetic_s1_s5.json')
        self.signal = self.corridor.signals[0]

    def test_phase_boundaries_and_wrap(self):
        sim=SignalSimulator()
        for t,state in [(0,'GREEN'),(34.999,'GREEN'),(35,'YELLOW'),(38,'RED'),(119.999,'RED'),(120,'GREEN'),(-1,'RED')]:
            self.assertEqual(sim.state_at(self.signal,t),state)

    def test_offset(self):
        sim=SignalSimulator()
        signal=self.corridor.signals[1]
        self.assertEqual(sim.state_at(signal,29.999),'RED')
        self.assertEqual(sim.state_at(signal,30),'GREEN')

    def test_real_data_unknown(self):
        corridor=load_corridor(DATA/'zwirki_wigury.json')
        self.assertIsNone(corridor.speed_limit_mps)
        for signal in corridor.signals:
            self.assertIsNone(signal.road_position_m)
            self.assertEqual(SignalSimulator().state_at(signal,10),'UNKNOWN')

    def test_adaptive_not_treated_as_fixed(self):
        for kind in (SignalType.ADAPTIVE,SignalType.ACTUATED,SignalType.UNKNOWN):
            self.assertEqual(SignalSimulator().state_at(replace(self.signal,signal_type=kind),0),'UNKNOWN')

    def test_deterministic_random_access(self):
        settings=SimulationSettings(seed=7,jitter_seconds=2,extension_probability=.5,extension_seconds=8)
        a,b=SignalSimulator(settings),SignalSimulator(settings)
        expected={i:a.window(self.signal,i) for i in range(-10,10)}
        for i in reversed(range(-10,10)):
            self.assertEqual(expected[i],b.window(self.signal,i))
            start,end=expected[i]
            self.assertLessEqual(abs(start-i*120),2)
            self.assertAlmostEqual(min(abs(end-start-35),abs(end-start-43)),0)

    def test_invalid_models(self):
        for update in [dict(cycle_seconds=0),dict(green_duration=120),dict(confidence=1.1),dict(offset=float('nan')),dict(road_position_m=-1),dict(verified=True)]:
            with self.assertRaises(ValueError):
                replace(self.signal,**update)
        with self.assertRaises(ValueError):
            replace(self.corridor,signals=(self.signal,self.signal))
        with self.assertRaises(ValueError):
            replace(self.corridor,signals=tuple(reversed(self.corridor.signals)))

    def test_jitter_cannot_overlap_cycles(self):
        with self.assertRaises(ValueError):
            SignalSimulator(SimulationSettings(jitter_seconds=60)).window(self.signal,0)

    def test_position_speed_limit_and_reset(self):
        provider=SimulationPositionProvider()
        provider.advance(2,30,10)
        self.assertEqual(provider.sample().road_position_m,20)
        self.assertEqual(provider.sample().speed_mps,10)
        with self.assertRaises(ValueError):
            provider.advance(-1,10,10)
        provider.reset()
        self.assertEqual(provider.sample().road_position_m,0)


if __name__ == '__main__':
    unittest.main()
