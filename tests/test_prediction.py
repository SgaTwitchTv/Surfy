from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from uuid import uuid4

from greenwave.events import ObservationType, SignalObservation, SignalState
from greenwave.models import load_corridor, SignalType
from greenwave.prediction import PredictionEngine, PredictionSettings, SignalRelation, load_prediction_config

DATA = Path(__file__).resolve().parents[1] / 'data'
EPOCH = datetime(2026, 9, 11, tzinfo=timezone.utc)


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.corridor = load_corridor(DATA / 'corridors/synthetic_s1_s5.json')
        self.settings, self.relations = load_prediction_config(DATA / 'prediction/synthetic_s1_s5.json')
        self.engine = PredictionEngine(self.corridor, 'test', self.settings)

    def observation(self, time, signal='S1', state=SignalState.GREEN, kind=ObservationType.STATE_START, **kwargs):
        return SignalObservation(str(uuid4()), 'test', self.corridor.id, signal, state, kind,
                                 EPOCH + timedelta(seconds=time), time, 'TEST', **kwargs)

    def test_fixed_prediction_offsets_and_windows(self):
        signal = replace(self.corridor.signals[0], signal_type=SignalType.FIXED_TIME)
        corridor = replace(self.corridor, signals=(signal,))
        engine = PredictionEngine(corridor, 'test')
        p = engine.predict('S1', 10)
        self.assertEqual(p.state, 'GREEN')
        self.assertEqual((p.windows[0].start, p.windows[0].end), (0, 35))
        self.assertEqual(self.engine.predict('S2', 10).windows[0].start, 30)

    def test_cycle_boundaries_have_uncertain_state(self):
        for time in (0, 35, 38, 120):
            self.assertEqual(self.engine.predict('S1', time).state, 'UNCERTAIN')
        self.assertEqual(self.engine.predict('S1', 80).state, 'RED')

    def test_green_now_resynchronizes_only_selected_signal(self):
        before = {s.id:self.engine.predict(s.id, 10).offset for s in self.corridor.signals}
        self.assertEqual(self.engine.observe(self.observation(10)), ('S1',))
        self.assertEqual(self.engine.predict('S1', 10).windows[0].start, 10)
        for signal in self.corridor.signals[1:]:
            self.assertEqual(self.engine.predict(signal.id, 10).offset, before[signal.id])
        self.assertEqual(self.engine.version, 1)

    def test_yellow_and_red_start_use_phase_durations(self):
        self.engine.observe(self.observation(50, state=SignalState.YELLOW))
        self.assertEqual(self.engine.predict('S1', 50).offset, 15)
        self.engine.observe(self.observation(70, state=SignalState.RED))
        self.assertEqual(self.engine.predict('S1', 70).offset, 32)

    def test_seen_does_not_invent_green_start(self):
        self.engine.observe(self.observation(10, kind=ObservationType.STATE_SEEN))
        self.assertEqual(self.engine.predict('S1', 10).offset, 0)
        self.assertTrue(self.engine.predict('S1', 10).windows)

    def test_conflicting_seen_withholds_prediction_until_start(self):
        self.engine.observe(self.observation(10, state=SignalState.RED, kind=ObservationType.STATE_SEEN))
        self.assertFalse(self.engine.predict('S1', 11).windows)
        self.engine.observe(self.observation(20))
        self.assertTrue(self.engine.predict('S1', 20).windows)

    def test_explicit_relations_propagate_but_no_transitive_edges(self):
        edge = self.relations[0]
        second = replace(edge, source_signal_id='S2', target_signal_id='S3', green_start_delta_seconds=30)
        engine = PredictionEngine(self.corridor, 'test', relations=(edge, second))
        self.assertEqual(engine.observe(self.observation(10)), ('S1','S2'))
        self.assertEqual(engine.predict('S2', 10).offset, 40)
        self.assertEqual(engine.predict('S3', 10).offset, 60)

    def test_direct_newer_observation_wins_over_propagation(self):
        engine = PredictionEngine(self.corridor, 'test', relations=self.relations)
        engine.observe(self.observation(20, 'S2'))
        engine.observe(self.observation(10, 'S1'))
        self.assertEqual(engine.predict('S2', 20).offset, 20)

    def test_late_events_and_duplicate_cannot_roll_back_or_increment_version(self):
        event = self.observation(20)
        self.engine.observe(event)
        self.engine.observe(event)
        self.engine.observe(self.observation(5))
        self.assertEqual(self.engine.version, 1)
        self.assertEqual(self.engine.predict('S1', 30).offset, 20)

    def test_conflicting_duplicate_rejected(self):
        event = self.observation(20)
        self.engine.observe(event)
        with self.assertRaises(ValueError):
            self.engine.observe(replace(event, state=SignalState.RED))

    def test_unknown_and_adaptive_never_get_periodic_forecasts(self):
        for kind in (SignalType.UNKNOWN, SignalType.ACTUATED, SignalType.ADAPTIVE):
            signal=replace(self.corridor.signals[0], signal_type=kind)
            engine=PredictionEngine(replace(self.corridor, signals=(signal,)), 'test')
            engine.observe(self.observation(20))
            p=engine.predict('S1',21)
            self.assertFalse(p.windows)
            self.assertEqual(p.state,'UNKNOWN')
            self.assertEqual(p.last_observation.state,SignalState.GREEN)
            self.assertEqual(p.observation_age_seconds,1)
            self.assertIsNone(p.confidence)

    def test_missing_offset_can_be_anchored_but_missing_cycle_cannot(self):
        for cycle in (120, None):
            signal=replace(self.corridor.signals[0],offset=None,cycle_seconds=cycle)
            engine=PredictionEngine(replace(self.corridor,signals=(signal,)),'test')
            self.assertFalse(engine.predict('S1',0).windows)
            engine.observe(self.observation(10))
            self.assertEqual(bool(engine.predict('S1',10).windows),cycle is not None)

    def test_age_grows_uncertainty_and_expires_model(self):
        p1=self.engine.predict('S1',10)
        p2=self.engine.predict('S1',100)
        self.assertGreater(p2.uncertainty_seconds,p1.uncertainty_seconds)
        self.assertFalse(self.engine.predict('S1',240).windows)
        self.engine.observe(self.observation(250))
        self.assertTrue(self.engine.predict('S1',251).windows)

    def test_confidence_optional_and_decays_with_age_and_residual(self):
        self.assertIsNone(self.engine.predict('S1',10).confidence)
        signal=replace(self.corridor.signals[0],confidence=.98)
        engine=PredictionEngine(replace(self.corridor,signals=(signal,)),'test')
        before=engine.predict('S1',0).confidence
        aged=engine.predict('S1',120).confidence
        self.assertAlmostEqual(aged,before/2)
        engine.observe(self.observation(20))
        self.assertLess(engine.predict('S1',20).confidence,aged)

    def test_cycle_wrapped_residual_is_small(self):
        self.engine.observe(self.observation(121))
        self.assertEqual(self.engine.predict('S1',121).residual_seconds,1)

    def test_manual_uncertainty_is_explicit_assumption(self):
        self.engine.observe(self.observation(10))
        p=self.engine.predict('S1',10)
        self.assertTrue(p.uncertainty_assumed)
        self.assertEqual(p.uncertainty_seconds,1)
        self.engine.observe(self.observation(20,timestamp_uncertainty_seconds=.2))
        self.assertFalse(self.engine.predict('S1',20).uncertainty_assumed)

    def test_wide_uncertainty_removes_interior_window(self):
        settings=replace(self.settings,baseline_uncertainty_seconds=60)
        p=PredictionEngine(self.corridor,'test',settings).predict('S1',10)
        self.assertTrue(p.windows)
        self.assertTrue(all(w.interior_start is None for w in p.windows))
        self.assertEqual(p.state,'UNCERTAIN')

    def test_utc_timebase_not_paused_simulation_time(self):
        engine=PredictionEngine(self.corridor,'test',utc_epoch=EPOCH.timestamp())
        observation=replace(self.observation(20),simulation_seconds=0)
        engine.observe(observation)
        self.assertEqual(engine.predict('S1',21).offset,20)
        self.assertEqual(engine.predict('S1',21).observation_age_seconds,1)

    def test_no_predictions_before_model_update(self):
        self.engine.observe(self.observation(20))
        self.assertFalse(self.engine.predict('S1',19).windows)

    def test_future_window_interiors_do_not_outlive_validity(self):
        for p in self.engine.predict_all(220):
            for w in p.windows:
                self.assertLess(w.start,p.valid_until)
                if w.interior_end is not None:self.assertLessEqual(w.interior_end,p.valid_until)

    def test_relations_reject_unknown_points_and_unverified_real_claims(self):
        for relation in (replace(self.relations[0],target_signal_id='S9'),
                         replace(self.relations[0],data_quality='UNVERIFIED')):
            with self.assertRaises(ValueError):
                PredictionEngine(self.corridor,'test',relations=(relation,))

    def test_zero_green_and_tiny_cycles_are_bounded(self):
        for changes in (dict(green_duration=0),dict(cycle_seconds=.001,green_duration=.0001,yellow_duration=.0001)):
            signal=replace(self.corridor.signals[0],**changes)
            p=PredictionEngine(replace(self.corridor,signals=(signal,)),'test').predict('S1',10)
            self.assertFalse(p.windows)

    def test_settings_validation(self):
        for changes in (dict(max_age_seconds=0),dict(horizon_seconds=601),dict(drift_seconds_per_second=-1)):
            with self.assertRaises(ValueError):replace(self.settings,**changes)
