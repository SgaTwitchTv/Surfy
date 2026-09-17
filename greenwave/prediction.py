"""Forecasts from declared knowledge and observations, never simulator truth.

Uncertainty is an engineering margin, not a calibrated confidence interval.
An optional confidence value is a decaying model index, not a probability.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path

from greenwave.events import ObservationType, SignalObservation, SignalState
from greenwave.models import Corridor, SignalModel, SignalType


@dataclass(frozen=True)
class PredictionSettings:
    horizon_seconds: float = 240
    max_age_seconds: float = 240
    observation_state_ttl_seconds: float = 5
    baseline_uncertainty_seconds: float = 2
    assumed_manual_uncertainty_seconds: float = 1
    drift_seconds_per_second: float = .02
    confidence_half_life_seconds: float = 120
    residual_scale_seconds: float = 10

    def __post_init__(self):
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid prediction setting: {name}')
        if min(self.horizon_seconds, self.max_age_seconds, self.confidence_half_life_seconds, self.residual_scale_seconds) <= 0:
            raise ValueError('Prediction horizons and scales must be positive')
        if self.horizon_seconds > 600:
            raise ValueError('M2 prediction horizon is limited to 600 seconds')


@dataclass(frozen=True)
class SignalRelation:
    source_signal_id: str
    target_signal_id: str
    green_start_delta_seconds: float
    uncertainty_seconds: float
    source: str
    verified: bool
    data_quality: str

    def __post_init__(self):
        if not self.source or self.source_signal_id == self.target_signal_id:
            raise ValueError('Relation must have a source and distinct control points')
        if not math.isfinite(self.green_start_delta_seconds) or not math.isfinite(self.uncertainty_seconds) or self.uncertainty_seconds < 0:
            raise ValueError('Invalid relation timing')
        if self.verified and self.data_quality == 'PLACEHOLDER':
            raise ValueError('Placeholder relation cannot be verified')


@dataclass(frozen=True)
class GreenWindow:
    signal_id: str
    start: float
    end: float
    uncertainty_seconds: float
    interior_start: float | None
    interior_end: float | None
    confidence: float | None
    source: str
    model_version: int


@dataclass(frozen=True)
class Prediction:
    signal_id: str
    state: str
    nominal_state: str
    windows: tuple[GreenWindow, ...]
    reason: str
    source: str
    model_version: int
    offset: float | None
    age_seconds: float
    uncertainty_seconds: float | None
    uncertainty_assumed: bool
    confidence: float | None
    valid_until: float
    residual_seconds: float | None
    last_observation: SignalObservation | None
    observation_age_seconds: float | None


@dataclass
class _Estimate:
    offset: float | None
    updated_at: float
    uncertainty: float
    source: str
    assumed: bool = True
    penalty: float = 1
    residual: float | None = None
    blocked: bool = False
    last_observation: SignalObservation | None = None


def load_prediction_config(path: str | Path) -> tuple[PredictionSettings, tuple[SignalRelation, ...]]:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data['schema_version'] != 1:
        raise ValueError('Unsupported prediction configuration')
    return PredictionSettings(**data['settings']), tuple(SignalRelation(**relation) for relation in data['relations'])


class PredictionEngine:
    def __init__(self, corridor: Corridor, session_id: str, settings: PredictionSettings = PredictionSettings(),
                 relations: tuple[SignalRelation, ...] = (), utc_epoch: float | None = None):
        self.corridor = corridor
        self.session_id = session_id
        self.settings = settings
        self.utc_epoch = utc_epoch  # None = simulation seconds; otherwise elapsed UTC.
        self.signals = {s.id: s for s in corridor.signals}
        self.relations = relations
        self.version = 0
        self._accepted: dict[str, SignalObservation] = {}
        self._latest_observation: dict[str, float] = {}
        self.estimates = {s.id: _Estimate(s.offset, 0, settings.baseline_uncertainty_seconds, s.source) for s in corridor.signals}
        for relation in relations:
            source = self.signals.get(relation.source_signal_id)
            target = self.signals.get(relation.target_signal_id)
            if source is None or target is None:
                raise ValueError('Relation references a point outside the corridor')
            if source.signal_type != SignalType.COORDINATED or target.signal_type != SignalType.COORDINATED:
                raise ValueError('M2 propagation requires two explicitly coordinated points')
            if source.cycle_seconds is None or source.cycle_seconds != target.cycle_seconds:
                raise ValueError('Coordinated relation requires a shared known cycle')
            if not relation.verified and not (relation.data_quality == 'PLACEHOLDER' and source.data_quality == target.data_quality == 'PLACEHOLDER'):
                raise ValueError('Unverified relations are only allowed in synthetic fixtures')
        targets = [(r.source_signal_id, r.target_signal_id) for r in relations]
        if len(targets) != len(set(targets)):
            raise ValueError('Duplicate relations')

    def observation_time(self, observation: SignalObservation) -> float:
        return observation.simulation_seconds if self.utc_epoch is None else observation.timestamp.timestamp() - self.utc_epoch

    @staticmethod
    def _periodic(signal: SignalModel) -> bool:
        return signal.signal_type in (SignalType.FIXED_TIME, SignalType.COORDINATED) and all(
            value is not None for value in (signal.cycle_seconds, signal.green_duration, signal.yellow_duration))

    @staticmethod
    def _nominal(signal: SignalModel, offset: float, now: float) -> str:
        phase = (now - offset) % signal.cycle_seconds
        if phase < signal.green_duration:
            return 'GREEN'
        if phase < signal.green_duration + signal.yellow_duration:
            return 'YELLOW'
        return 'RED'

    def observe(self, observation: SignalObservation) -> tuple[str, ...]:
        if observation.session_id != self.session_id:
            return ()  # Old sessions remain in the raw history only.
        if observation.corridor_id != self.corridor.id or observation.signal_id not in self.signals:
            raise ValueError('Observation does not belong to this corridor')
        existing = self._accepted.get(observation.observation_id)
        if existing is not None:
            if existing != observation:
                raise ValueError('Conflicting observation ID')
            return ()
        now = self.observation_time(observation)
        self._accepted[observation.observation_id] = observation
        if now < self._latest_observation.get(observation.signal_id, -math.inf):
            return ()  # Never roll the active estimate back for a late event.
        self._latest_observation[observation.signal_id] = now
        signal = self.signals[observation.signal_id]
        estimate = self.estimates[signal.id]
        if now < estimate.updated_at:
            return ()  # A later propagated update must not be rolled back either.
        estimate.last_observation = observation
        self.version += 1
        if not self._periodic(signal):
            return ()  # An observed green does not reveal an unknown cycle.
        if observation.event_type == ObservationType.STATE_SEEN:
            if estimate.offset is not None and self._nominal(signal, estimate.offset, now) != observation.state.value:
                estimate.blocked = True
                estimate.penalty *= .5
            return ()  # Seeing a colour is not evidence of its starting time.
        phase_offset = {SignalState.GREEN: 0, SignalState.YELLOW: signal.green_duration,
                        SignalState.RED: signal.green_duration + signal.yellow_duration}[observation.state]
        new_offset = now - phase_offset
        residual = None if estimate.offset is None else (new_offset - estimate.offset + signal.cycle_seconds/2) % signal.cycle_seconds - signal.cycle_seconds/2
        uncertainty = observation.timestamp_uncertainty_seconds
        assumed = uncertainty is None
        if assumed:
            uncertainty = self.settings.assumed_manual_uncertainty_seconds
        penalty = 1 if residual is None else math.exp(-abs(residual)/self.settings.residual_scale_seconds)
        self.estimates[signal.id] = _Estimate(new_offset, now, uncertainty, f'{observation.source}:{signal.id}',
                                             assumed, penalty, residual, False, observation)
        changed = [signal.id]
        # One hop only; no inferred reverse edges and no transitive/global shift.
        for relation in self.relations:
            if relation.source_signal_id != signal.id:
                continue
            target = self.estimates[relation.target_signal_id]
            # A direct observation at the same/newer time is stronger evidence.
            if self._latest_observation.get(relation.target_signal_id, -math.inf) >= now or target.updated_at > now:
                continue
            self.estimates[relation.target_signal_id] = _Estimate(
                new_offset + relation.green_start_delta_seconds, now,
                uncertainty + relation.uncertainty_seconds + (abs(residual) * .25 if residual is not None else 0),
                f'RELATION:{signal.id}→{relation.target_signal_id} ({relation.source})',
                assumed or not relation.verified, penalty, residual, False, target.last_observation)
            changed.append(relation.target_signal_id)
        return tuple(changed)

    def predict(self, signal_id: str, now: float) -> Prediction:
        if not math.isfinite(now):
            raise ValueError('Prediction time must be finite')
        signal = self.signals[signal_id]
        estimate = self.estimates[signal_id]
        settings = self.settings
        age = max(0, now - estimate.updated_at)
        observation = estimate.last_observation
        observation_age = None if observation is None else now - self.observation_time(observation)
        expires = estimate.updated_at + settings.max_age_seconds
        uncertainty = estimate.uncertainty + age * settings.drift_seconds_per_second
        confidence = None if signal.confidence is None else signal.confidence * estimate.penalty * 2**(-age/settings.confidence_half_life_seconds)
        reason = ''
        if not self._periodic(signal):
            reason = 'Brak modelu okresowego dla sygnalizacji nieznanej lub zależnej od ruchu.'
        elif signal.green_duration <= 0:
            reason = 'Model nie zawiera zielonej fazy.'
        elif estimate.offset is None:
            reason = 'Nieznany początek cyklu; potrzebna obserwacja początku fazy.'
        elif estimate.blocked:
            reason = 'Obserwacja koloru przeczy modelowi. Zgłoś początek fazy.'
        elif now < estimate.updated_at:
            reason = 'Czas predykcji poprzedza aktualizację modelu.'
        elif now >= expires:
            reason = 'Model stracił ważność. Potrzebna nowa obserwacja początku fazy.'
        windows = []
        nominal = state = 'UNKNOWN'
        if not reason:
            nominal = self._nominal(signal, estimate.offset, now)
            phase = (now - estimate.offset) % signal.cycle_seconds
            boundaries = (0, signal.green_duration, signal.green_duration + signal.yellow_duration)
            distance = min(abs((phase - boundary + signal.cycle_seconds/2) % signal.cycle_seconds - signal.cycle_seconds/2) for boundary in boundaries)
            state = nominal if distance > uncertainty else 'UNCERTAIN'
            index = math.floor((now - estimate.offset) / signal.cycle_seconds) - 1
            horizon = min(now + settings.horizon_seconds, expires)
            # A validated cycle can still be extremely small: cap output work explicitly.
            if settings.horizon_seconds / signal.cycle_seconds > 1000:
                reason = 'Cykl zbyt krótki dla horyzontu M2.'
                state = nominal = 'UNKNOWN'
            else:
                while True:
                    start = estimate.offset + index * signal.cycle_seconds
                    end = start + signal.green_duration
                    if start >= horizon:
                        break
                    future_age = max(age, end - estimate.updated_at)
                    margin = estimate.uncertainty + future_age * settings.drift_seconds_per_second
                    if end + margin > now:
                        interior_start = max(start + margin, now)
                        interior_end = min(end - margin, expires)
                        if interior_start >= interior_end:
                            interior_start = interior_end = None
                        windows.append(GreenWindow(signal.id, start, end, margin, interior_start, interior_end,
                            None if signal.confidence is None else signal.confidence * estimate.penalty * 2**(-future_age/settings.confidence_half_life_seconds),
                            estimate.source, self.version))
                    index += 1
        return Prediction(signal.id, state, nominal, tuple(windows), reason, estimate.source, self.version,
                          estimate.offset, age, None if not self._periodic(signal) else uncertainty, estimate.assumed,
                          None if reason else confidence, expires, estimate.residual, observation, observation_age)

    def predict_all(self, now: float) -> tuple[Prediction, ...]:
        return tuple(self.predict(signal.id, now) for signal in self.corridor.signals)
