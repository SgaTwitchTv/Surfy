"""Direction-specific control points. Distances in metres, times in seconds."""
from dataclasses import dataclass
from enum import StrEnum
import json
import math
from pathlib import Path


class SignalType(StrEnum):
    FIXED_TIME = 'FIXED_TIME'
    COORDINATED = 'COORDINATED'
    ACTUATED = 'ACTUATED'
    ADAPTIVE = 'ADAPTIVE'
    UNKNOWN = 'UNKNOWN'


@dataclass(frozen=True)
class SignalModel:
    id: str
    name: str
    direction: str
    movement: str
    signal_type: SignalType
    road_position_m: float | None
    cycle_seconds: float | None
    green_duration: float | None
    offset: float | None
    yellow_duration: float | None
    latitude: float | None
    longitude: float | None
    confidence: float | None
    source: str
    last_verified: str | None
    notes: str
    verified: bool
    data_quality: str

    def __post_init__(self):
        for field in ('road_position_m', 'cycle_seconds', 'green_duration', 'offset',
                      'yellow_duration', 'latitude', 'longitude', 'confidence'):
            value = getattr(self, field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f'{self.id}: invalid {field}')
        if not self.id or not self.direction or not self.movement:
            raise ValueError('Control point needs identity, direction and movement')
        if self.road_position_m is not None and self.road_position_m < 0:
            raise ValueError('Negative road position')
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError('Confidence outside [0, 1]')
        for value, bound in ((self.latitude, 90), (self.longitude, 180)):
            if value is not None and not -bound <= value <= bound:
                raise ValueError('Invalid coordinates')
        if self.cycle_seconds is not None and self.cycle_seconds <= 0:
            raise ValueError('Cycle must be positive')
        for duration in (self.green_duration, self.yellow_duration):
            if duration is not None and duration < 0:
                raise ValueError('Negative duration')
        if all(v is not None for v in (self.cycle_seconds, self.green_duration, self.yellow_duration)):
            if self.green_duration + self.yellow_duration >= self.cycle_seconds:
                raise ValueError('Cycle must contain a red phase')
        if self.verified and self.data_quality == 'PLACEHOLDER':
            raise ValueError('Placeholder cannot be verified')


@dataclass(frozen=True)
class Corridor:
    id: str
    name: str
    direction: str
    speed_limit_mps: float | None
    signals: tuple[SignalModel, ...]

    def __post_init__(self):
        if not self.signals or len({s.id for s in self.signals}) != len(self.signals):
            raise ValueError('Signals must be nonempty and uniquely identified')
        if any(s.direction != self.direction for s in self.signals):
            raise ValueError('Mixed corridor directions')
        positions = [s.road_position_m for s in self.signals if s.road_position_m is not None]
        if any(b <= a for a, b in zip(positions, positions[1:])):
            raise ValueError('Positions must be strictly increasing')
        if self.speed_limit_mps is not None and (not math.isfinite(self.speed_limit_mps) or self.speed_limit_mps <= 0):
            raise ValueError('Invalid speed limit')


def load_corridor(path: str | Path) -> Corridor:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.pop('schema_version') != 1:
        raise ValueError('Unsupported schema version')
    signals = tuple(SignalModel(**(s | {'signal_type': SignalType(s['signal_type'])})) for s in data.pop('signals'))
    return Corridor(**data, signals=signals)
