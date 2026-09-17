"""Observation acceptance and session-scoped ordering, independent of any UI."""
from uuid import uuid4
from greenwave.clocks import ClockReading
from greenwave.events import EventBus, ObservationType, SignalObservation, SignalObserved, SignalState
from greenwave.models import Corridor


class ObservationService:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._history: list[SignalObserved] = []
        self._by_id: dict[str, SignalObservation] = {}
        self._sessions: dict[str, Corridor] = {}
        self._latest: dict[tuple[str, str], float] = {}

    @property
    def history(self) -> tuple[SignalObserved, ...]:
        """Arrival order, including old sessions; never rewritten on reset."""
        return tuple(self._history)

    def start_session(self, corridor: Corridor) -> str:
        session_id = str(uuid4())
        self._sessions[session_id] = corridor
        return session_id

    def observe_now(self, session_id: str, signal_id: str, state: SignalState,
                    event_type: ObservationType, reading: ClockReading) -> SignalObservation:
        corridor = self._sessions[session_id]
        observation = SignalObservation(
            observation_id=str(uuid4()), session_id=session_id, corridor_id=corridor.id,
            signal_id=signal_id, state=state, event_type=event_type,
            timestamp=reading.timestamp, simulation_seconds=reading.simulation_seconds,
            source='MANUAL', timestamp_uncertainty_seconds=None,
        )
        self.accept(observation)
        return observation

    def accept(self, observation: SignalObservation) -> bool:
        previous = self._by_id.get(observation.observation_id)
        if previous is not None:
            if previous != observation:
                raise ValueError('Conflicting payload for existing observation ID')
            return False
        corridor = self._sessions.get(observation.session_id)
        if corridor is None or corridor.id != observation.corridor_id:
            raise ValueError('Unknown session or mismatched corridor')
        if observation.signal_id not in {signal.id for signal in corridor.signals}:
            raise ValueError('Unknown control point in this corridor')
        key = (observation.session_id, observation.signal_id)
        latest = self._latest.get(key, -1.0)
        event = SignalObserved(observation, observation.simulation_seconds < latest)
        self._by_id[observation.observation_id] = observation
        self._latest[key] = max(latest, observation.simulation_seconds)
        self._history.append(event)
        self.bus.publish(event)
        return True

    def chronological(self, session_id: str) -> tuple[SignalObservation, ...]:
        # Stable sorting preserves arrival order for equal simulation timestamps.
        return tuple(sorted((e.observation for e in self._history if e.observation.session_id == session_id),
                            key=lambda observation: observation.simulation_seconds))
