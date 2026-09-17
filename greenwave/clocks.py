"""UTC records when something happened; monotonic time drives simulation only."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import time
from typing import Callable


@dataclass(frozen=True)
class ClockReading:
    timestamp: datetime
    simulation_seconds: float


class SimulationClock:
    def __init__(self, monotonic: Callable[[], float] = time.monotonic,
                 utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._monotonic = monotonic
        self._utc_now = utc_now
        self._elapsed = 0.0
        self._anchor = monotonic()
        self.running = False
        self.rate = 1.0

    def _settle(self):
        now = self._monotonic()
        if self.running:
            self._elapsed += (now - self._anchor) * self.rate
        self._anchor = now

    def read(self) -> ClockReading:
        self._settle()
        timestamp = self._utc_now()
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError('UTC clock must return a timezone-aware datetime')
        return ClockReading(timestamp.astimezone(timezone.utc), self._elapsed)

    def set_running(self, running: bool):
        self._settle()
        self.running = running

    def set_rate(self, rate: float):
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError('Clock rate must be positive and finite')
        self._settle()  # Account for time at the OLD rate before switching.
        self.rate = rate

    def reset(self):
        self._elapsed = 0.0
        self._anchor = self._monotonic()
        self.running = False
