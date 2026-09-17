from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from greenwave.clocks import SimulationClock
from greenwave.events import EventBus, ObservationType, SignalState
from greenwave.models import load_corridor
from greenwave.observations import ObservationService


class FakeTime:
    def __init__(self):
        self.seconds = 0.0
        self.utc = datetime(2026, 9, 11, 12, 0, 0, 123456, tzinfo=timezone.utc)

    def advance(self, seconds):
        self.seconds += seconds
        self.utc += timedelta(seconds=seconds)

    def clock(self):
        return SimulationClock(lambda: self.seconds, lambda: self.utc)


class ClockTests(unittest.TestCase):
    def test_pause_keeps_simulation_frozen_but_utc_advances(self):
        time = FakeTime()
        clock = time.clock()
        clock.set_running(True)
        time.advance(3)
        clock.set_running(False)
        first = clock.read()
        time.advance(20)
        second = clock.read()
        self.assertEqual(first.simulation_seconds, 3)
        self.assertEqual(second.simulation_seconds, 3)
        self.assertEqual(second.timestamp - first.timestamp, timedelta(seconds=20))

    def test_rate_changes_account_for_previous_rate_without_tick(self):
        time = FakeTime()
        clock = time.clock()
        clock.set_running(True)
        total = 0
        for rate in (1, 2, 5, 10):
            clock.set_rate(rate)
            time.advance(2)
            total += 2 * rate
        self.assertEqual(clock.read().simulation_seconds, total)
        self.assertEqual(total, 36)

    def test_wall_clock_correction_does_not_move_simulation_backwards(self):
        time = FakeTime()
        clock = time.clock()
        clock.set_running(True)
        time.advance(5)
        before = clock.read()
        time.utc -= timedelta(hours=1)
        time.advance(2)
        after = clock.read()
        self.assertEqual(after.simulation_seconds, 7)
        self.assertLess(after.timestamp, before.timestamp)

    def test_reset_and_resume_do_not_include_pause_time(self):
        time = FakeTime()
        clock = time.clock()
        clock.set_rate(10)
        clock.set_running(True)
        time.advance(5)
        clock.reset()
        time.advance(100)
        self.assertEqual(clock.read().simulation_seconds, 0)
        clock.set_running(True)
        time.advance(1)
        self.assertEqual(clock.read().simulation_seconds, 10)

    def test_invalid_rate_rejected(self):
        clock = FakeTime().clock()
        for rate in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                clock.set_rate(rate)


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.time = FakeTime()
        self.clock = self.time.clock()
        self.bus = EventBus()
        self.received = []
        self.unsubscribe = self.bus.subscribe(self.received.append)
        self.service = ObservationService(self.bus)
        self.corridor = load_corridor(Path(__file__).resolve().parents[1] / 'data/corridors/synthetic_s1_s5.json')
        self.session = self.service.start_session(self.corridor)

    def observe(self, signal='S3', state=SignalState.GREEN, kind=ObservationType.STATE_START):
        return self.service.observe_now(self.session, signal, state, kind, self.clock.read())

    def test_manual_event_has_exact_timestamp_identity_source_and_kind(self):
        observation = self.observe()
        self.assertEqual(observation.timestamp, self.time.utc)
        self.assertEqual(observation.timestamp.microsecond, 123456)
        self.assertEqual(observation.signal_id, 'S3')
        self.assertEqual(observation.session_id, self.session)
        self.assertEqual(observation.corridor_id, self.corridor.id)
        self.assertEqual(observation.source, 'MANUAL')
        self.assertIsNone(observation.timestamp_uncertainty_seconds)
        self.assertEqual(self.received[0].observation, observation)

    def test_colors_and_seen_do_not_become_state_start(self):
        for state in SignalState:
            observation = self.observe(state=state, kind=ObservationType.STATE_SEEN)
            self.assertEqual(observation.state, state)
            self.assertEqual(observation.event_type, ObservationType.STATE_SEEN)
        self.assertEqual(len(self.service.history), 3)

    def test_same_payload_is_idempotent_but_distinct_clicks_are_kept(self):
        observation = self.observe()
        self.assertFalse(self.service.accept(observation))
        self.assertEqual(len(self.received), 1)
        self.assertNotEqual(self.observe().observation_id, observation.observation_id)
        self.assertEqual(len(self.service.history), 2)

    def test_conflicting_duplicate_is_rejected(self):
        observation = self.observe()
        with self.assertRaises(ValueError):
            self.service.accept(replace(observation, state=SignalState.RED))
        self.assertEqual(len(self.received), 1)

    def test_out_of_order_preserves_arrival_history_and_chronological_view(self):
        self.clock.set_running(True)
        self.time.advance(20)
        latest = self.observe()
        late = replace(latest, observation_id='late', simulation_seconds=5, timestamp=latest.timestamp-timedelta(seconds=15))
        self.assertTrue(self.service.accept(late))
        self.assertTrue(self.received[-1].out_of_order)
        self.assertEqual([e.observation for e in self.service.history], [latest, late])
        self.assertEqual(self.service.chronological(self.session), (late, latest))
        other = replace(late, observation_id='other-signal', signal_id='S2')
        self.service.accept(other)
        self.assertFalse(self.received[-1].out_of_order)

    def test_unknown_signal_or_session_or_wrong_corridor_rejected(self):
        observation = self.observe()
        for update in (dict(signal_id='S99'), dict(session_id='other'), dict(corridor_id='other')):
            with self.assertRaises(ValueError):
                self.service.accept(replace(observation, observation_id=str(update), **update))
        self.assertEqual(len(self.service.history), 1)

    def test_reset_sessions_preserve_history_and_do_not_share_ordering(self):
        self.clock.set_running(True)
        self.time.advance(10)
        first = self.observe()
        self.clock.reset()
        self.session = self.service.start_session(self.corridor)
        second = self.observe()
        self.assertNotEqual(first.session_id, second.session_id)
        self.assertFalse(self.received[-1].out_of_order)
        self.assertEqual(len(self.service.history), 2)
        self.assertEqual(self.service.chronological(self.session), (second,))

    def test_invalid_observation_times_and_types(self):
        observation = self.observe()
        for update in (dict(timestamp=datetime(2026, 1, 1)), dict(simulation_seconds=-1),
                       dict(simulation_seconds=float('nan')), dict(timestamp_uncertainty_seconds=-1),
                       dict(source=''), dict(state='BLUE')):
            with self.assertRaises(ValueError):
                replace(observation, **update)

    def test_unsubscribe(self):
        self.unsubscribe()
        self.observe()
        self.assertEqual(self.received, [])
        self.assertEqual(len(self.service.history), 1)
