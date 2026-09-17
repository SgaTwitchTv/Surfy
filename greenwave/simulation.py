"""Synthetic ground truth, intentionally separate from future predictions."""
from dataclasses import dataclass
import hashlib
import math
import random
from greenwave.models import SignalModel, SignalType


@dataclass(frozen=True)
class SimulationSettings:
    seed: int = 42
    jitter_seconds: float = 0
    extension_probability: float = 0
    extension_seconds: float = 0

    def __post_init__(self):
        values = (self.jitter_seconds, self.extension_probability, self.extension_seconds)
        if not all(math.isfinite(v) for v in values) or min(values) < 0 or self.extension_probability > 1:
            raise ValueError('Invalid simulator settings')


class SignalSimulator:
    def __init__(self, settings: SimulationSettings = SimulationSettings()):
        self.settings = settings

    def window(self, signal: SignalModel, cycle_index: int) -> tuple[float, float]:
        s = self.settings
        if signal.cycle_seconds is None or signal.offset is None or signal.green_duration is None or signal.yellow_duration is None:
            raise ValueError('Missing timing parameters')
        if signal.green_duration + signal.yellow_duration + 2*s.jitter_seconds + s.extension_seconds >= signal.cycle_seconds:
            raise ValueError('Jitter/extension could overlap consecutive cycles')
        seed = hashlib.sha256(f'{s.seed}:{signal.id}:{cycle_index}'.encode()).digest()
        rng = random.Random(seed)
        start = signal.offset + cycle_index * signal.cycle_seconds + rng.uniform(-s.jitter_seconds, s.jitter_seconds)
        extension = s.extension_seconds if rng.random() < s.extension_probability else 0
        return start, start + signal.green_duration + extension

    def state_at(self, signal: SignalModel, elapsed_seconds: float) -> str:
        if not math.isfinite(elapsed_seconds):
            raise ValueError('Invalid model time')
        if signal.signal_type not in (SignalType.FIXED_TIME, SignalType.COORDINATED):
            return 'UNKNOWN'
        if any(v is None for v in (signal.cycle_seconds, signal.green_duration, signal.offset, signal.yellow_duration)):
            return 'UNKNOWN'
        index = math.floor((elapsed_seconds - signal.offset) / signal.cycle_seconds)
        for n in (index - 1, index, index + 1):
            start, end = self.window(signal, n)
            if start <= elapsed_seconds < end:
                return 'GREEN'
            if end <= elapsed_seconds < end + signal.yellow_duration:
                return 'YELLOW'
        return 'RED'
