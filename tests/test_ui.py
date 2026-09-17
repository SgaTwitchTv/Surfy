"""Tk integration test; requires desktop/Tcl access (not a headless mock)."""
from datetime import datetime, timedelta, timezone
import tkinter as tk
import unittest

from greenwave.clocks import SimulationClock
from greenwave.events import SignalState
from greenwave.ui import App


class UiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f'Tk unavailable: {error}')
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.seconds = 0
        clock = SimulationClock(lambda: self.seconds, lambda: datetime(2026, 9, 11, tzinfo=timezone.utc) + timedelta(seconds=self.seconds))
        self.app = App(self.root, clock)
        self.root.update()

    def test_buttons_pause_rate_reset_and_unknown_dataset(self):
        app = self.app
        app.selected_signal.set(list(app.signal_choices)[2])
        app.toggle()
        self.seconds = 2
        app.observation_buttons[SignalState.GREEN].invoke()
        first = app.observations.history[-1].observation
        self.assertEqual((first.signal_id, first.simulation_seconds), ('S3', 2))
        self.assertEqual(app.position.sample().elapsed_seconds, 2)
        app.rate.set('10')
        app.change_rate()
        self.seconds = 3
        app.toggle()
        self.seconds = 8
        app.observation_type.set('Widzę stan teraz')
        app.observation_buttons[SignalState.YELLOW].invoke()
        second = app.observations.history[-1].observation
        self.assertEqual(second.simulation_seconds, 12)
        self.assertEqual(second.event_type.value, 'STATE_SEEN')
        self.assertEqual((second.timestamp-first.timestamp).total_seconds(), 6)
        app.dataset.set('zwirki_wigury')
        app.reset()
        app.observation_buttons[SignalState.RED].invoke()
        third = app.observations.history[-1].observation
        self.assertFalse(app.available)
        self.assertEqual(third.simulation_seconds, 0)
        self.assertNotEqual(third.session_id, first.session_id)
        self.assertEqual(third.corridor_id, 'zwirki_wigury')
        self.assertEqual(len(app.history_table.get_children()), 3)
        self.assertEqual(len(app.table.get_children()), 5)
