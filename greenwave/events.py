"""Input contracts shared by manual observations and future source adapters."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import math
from typing import Callable


class SignalState(StrEnum):
    GREEN = 'GREEN'
    YELLOW = 'YELLOW'
    RED = 'RED'


class ObservationType(StrEnum):
    STATE_START = 'STATE_START'
    STATE_SEEN = 'STATE_SEEN'


@dataclass(frozen=True)
class SignalObservation:
    observation_id: str
    session_id: str
    corridor_id: str
    signal_id: str
    state: SignalState
    event_type: ObservationType
    timestamp: datetime
    simulation_seconds: float
    source: str
    timestamp_uncertainty_seconds: float | None = None

    def __post_init__(self):
        for value in (self.observation_id, self.session_id, self.corridor_id, self.signal_id, self.source):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Observation identifiers and source must be nonempty')
        if not isinstance(self.state, SignalState) or not isinstance(self.event_type, ObservationType):
            raise ValueError('Invalid observation state or event type')
        if self.timestamp.utcoffset() != timedelta(0):
            raise ValueError('Observation timestamp must be timezone-aware UTC')
        for value in (self.simulation_seconds, self.timestamp_uncertainty_seconds):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError('Observation times must be finite and nonnegative')
        if self.simulation_seconds is None:
            raise ValueError('Simulation time is required')


@dataclass(frozen=True)
class SignalObserved:
    observation: SignalObservation
    out_of_order: bool


@dataclass(frozen=True)
class ModelResynchronized:
    session_id: str
    observation_id: str
    signal_ids: tuple[str, ...]
    model_version: int


@dataclass(frozen=True)
class PredictionUpdated:
    session_id: str
    model_version: int


class EventBus:
    """Synchronous application-thread dispatch; adapters must enter that thread."""
    def __init__(self):
        self._listeners: list[tuple[Callable, type | None]] = []

    def subscribe(self, listener: Callable, event_type: type | None = None) -> Callable[[], None]:
        entry = (listener, event_type)
        self._listeners.append(entry)

        def unsubscribe():
            if entry in self._listeners:
                self._listeners.remove(entry)

        return unsubscribe

    def publish(self, event):
        for listener, event_type in tuple(self._listeners):
            if event_type is None or isinstance(event, event_type):
                listener(event)
