from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Protocol
import math
import time


@dataclass(frozen=True)
class PositionSample:
    elapsed_seconds: float
    road_position_m: float | None
    speed_mps: float | None
    latitude: float | None = None
    longitude: float | None = None
    heading_deg: float | None = None
    gps_accuracy_m: float | None = None
    acceleration_mps2: float | None = None
    source: str = 'SIMULATION'
    raw_speed_mps: float | None = None
    calculated_speed_mps: float | None = None
    speed_source: str = 'UNAVAILABLE'
    position_quality: str = 'UNKNOWN'
    usable_for_live: bool = False
    quality_reasons: tuple[str, ...] = ()


class PositionProvider(Protocol):
    def sample(self) -> PositionSample: ...


class SimulationPositionProvider:
    """Prescribed-speed probe; vehicle dynamics belong to a later milestone."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.elapsed = 0.0
        self.position = 0.0
        self.speed = 0.0

    def advance(self, seconds: float, speed_mps: float, speed_limit_mps: float):
        if not all(math.isfinite(v) for v in (seconds, speed_mps, speed_limit_mps)) or min(seconds, speed_mps, speed_limit_mps) < 0:
            raise ValueError('Invalid simulation step')
        self.speed = min(speed_mps, speed_limit_mps)
        self.position += seconds * self.speed
        self.elapsed += seconds

    def sample(self) -> PositionSample:
        return PositionSample(self.elapsed, self.position, self.speed,
                              raw_speed_mps=self.speed, speed_source='SIMULATION',
                              position_quality='SIMULATION', usable_for_live=True)


def _haversine_m(latitude_a, longitude_a, latitude_b, longitude_b):
    radius_m = 6_371_008.8
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    d_lat = lat_b - lat_a
    d_lon = math.radians(longitude_b - longitude_a)
    value = math.sin(d_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(d_lon / 2) ** 2
    return 2 * radius_m * math.asin(min(1.0, math.sqrt(value)))


class ExternalPositionProvider:
    """Validate, diagnose and smooth the latest phone or GNSS sample.

    Raw browser speed remains available separately. If the device omits it, a
    conservative fallback is calculated from recent, sufficiently accurate GPS
    fixes. Route projection stays optional until corridor geometry is verified.
    """

    STALE_AFTER_SECONDS = 5.0
    MAX_USABLE_ACCURACY_M = 50.0
    MAX_DERIVATION_ACCURACY_M = 30.0
    MAX_PLAUSIBLE_SPEED_MPS = 80.0
    STATIONARY_DEVICE_SPEED_MPS = 3.0 / 3.6

    def __init__(self):
        self.reset()

    def reset(self):
        self._sample = None
        self.received_at = None
        self.count = 0
        self.usable_count = 0
        self.quality_rejected_count = 0
        self.last_interval_seconds = None
        self.last_diagnostic = 'Oczekiwanie na pierwszą próbkę.'
        self._last_timestamp = None
        self._points = deque(maxlen=12)
        self._calculated_speeds = deque(maxlen=5)

    @staticmethod
    def _number(value, name, *, optional=False):
        if value is None and optional:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{name} must be a finite number')
        return float(value)

    @staticmethod
    def _position_quality(latitude, longitude, accuracy):
        if latitude is None or longitude is None:
            return 'MISSING'
        if accuracy is None:
            return 'UNKNOWN'
        if accuracy <= 10:
            return 'GOOD'
        if accuracy <= 25:
            return 'FAIR'
        if accuracy <= ExternalPositionProvider.MAX_USABLE_ACCURACY_M:
            return 'POOR'
        return 'UNUSABLE'

    def _calculate_speed(self, timestamp, latitude, longitude, accuracy):
        if latitude is None or longitude is None or accuracy is None or accuracy > self.MAX_DERIVATION_ACCURACY_M:
            return None
        candidates = []
        for previous_time, previous_latitude, previous_longitude, previous_accuracy in self._points:
            interval = timestamp - previous_time
            if interval < 2.0 or interval > 12.0:
                continue
            distance = _haversine_m(previous_latitude, previous_longitude, latitude, longitude)
            noise_radius = max(3.0, (previous_accuracy + accuracy) / 2)
            if distance <= noise_radius:
                if interval >= 4.0:
                    candidates.append(0.0)
                continue
            estimate = distance / interval
            if estimate <= self.MAX_PLAUSIBLE_SPEED_MPS:
                candidates.append(estimate)
        if not candidates:
            return None
        self._calculated_speeds.append(median(candidates))
        return median(self._calculated_speeds)

    def _stationary_confirmed(self, timestamp, latitude, longitude, accuracy):
        if latitude is None or longitude is None or accuracy is None or accuracy > self.MAX_DERIVATION_ACCURACY_M:
            return False
        recent = [point for point in self._points if 0 <= timestamp - point[0] <= 8.0]
        if len(recent) < 4 or timestamp - recent[0][0] < 4.0:
            return False
        anchor = recent[0]
        maximum_displacement = max(
            _haversine_m(anchor[1], anchor[2], point[1], point[2]) for point in recent)
        accuracy_based_radius = min(3.0, max(1.5, median(point[3] for point in recent) / 4))
        return maximum_displacement <= accuracy_based_radius

    def update(self, *, timestamp_seconds: float, speed_mps: float | None,
               latitude: float | None = None, longitude: float | None = None,
               heading_deg: float | None = None, gps_accuracy_m: float | None = None,
               acceleration_mps2: float | None = None,
               road_position_m: float | None = None, source: str = 'EXTERNAL'):
        timestamp_seconds = self._number(timestamp_seconds, 'timestamp_seconds')
        speed_mps = self._number(speed_mps, 'speed_mps', optional=True)
        latitude = self._number(latitude, 'latitude', optional=True)
        longitude = self._number(longitude, 'longitude', optional=True)
        heading_deg = self._number(heading_deg, 'heading_deg', optional=True)
        gps_accuracy_m = self._number(gps_accuracy_m, 'gps_accuracy_m', optional=True)
        acceleration_mps2 = self._number(acceleration_mps2, 'acceleration_mps2', optional=True)
        road_position_m = self._number(road_position_m, 'road_position_m', optional=True)
        if timestamp_seconds < 0 or speed_mps is not None and speed_mps < 0:
            raise ValueError('Invalid external position')
        if (latitude is None) != (longitude is None):
            raise ValueError('latitude and longitude must be supplied together')
        if latitude is not None and not -90 <= latitude <= 90:
            raise ValueError('latitude must be in [-90, 90]')
        if longitude is not None and not -180 <= longitude <= 180:
            raise ValueError('longitude must be in [-180, 180]')
        if gps_accuracy_m is not None and gps_accuracy_m < 0:
            raise ValueError('gps_accuracy_m must be non-negative')
        if not isinstance(source, str) or source not in ('EXTERNAL', 'WEB_GEOLOCATION', 'ANDROID_FUSED'):
            raise ValueError('Unknown external position source')

        now = time.monotonic()
        self.last_interval_seconds = None if self.received_at is None else max(0.0, now - self.received_at)
        self.received_at = now
        self.count += 1
        reasons = []
        quality = self._position_quality(latitude, longitude, gps_accuracy_m)
        if quality == 'MISSING':
            reasons.append('LOCATION_MISSING')
        elif quality == 'UNKNOWN':
            reasons.append('GPS_ACCURACY_MISSING')
        elif quality == 'POOR':
            reasons.append('GPS_ACCURACY_LIMITED')
        elif quality == 'UNUSABLE':
            reasons.append('GPS_ACCURACY_TOO_LOW')

        timestamp_newer = self._last_timestamp is None or timestamp_seconds > self._last_timestamp
        if not timestamp_newer:
            reasons.append('TIMESTAMP_NOT_NEWER')
        raw_speed = speed_mps
        if raw_speed is not None and raw_speed > self.MAX_PLAUSIBLE_SPEED_MPS:
            reasons.append('DEVICE_SPEED_IMPLAUSIBLE')
            raw_speed = None

        calculated_speed = None
        if timestamp_newer:
            if self._last_timestamp is not None and timestamp_seconds - self._last_timestamp > 12.0:
                self._points.clear()
                self._calculated_speeds.clear()
            calculated_speed = self._calculate_speed(timestamp_seconds, latitude, longitude, gps_accuracy_m)
            if (latitude is not None and gps_accuracy_m is not None and
                    gps_accuracy_m <= self.MAX_DERIVATION_ACCURACY_M):
                self._points.append((timestamp_seconds, latitude, longitude, gps_accuracy_m))
            self._last_timestamp = timestamp_seconds

        stationary = timestamp_newer and self._stationary_confirmed(
            timestamp_seconds, latitude, longitude, gps_accuracy_m)
        if stationary and (raw_speed is None or raw_speed <= self.STATIONARY_DEVICE_SPEED_MPS):
            selected_speed, speed_source = 0.0, 'STATIONARY_FILTER'
            calculated_speed = 0.0
        elif raw_speed is not None:
            selected_speed, speed_source = raw_speed, 'DEVICE'
        elif calculated_speed is not None:
            selected_speed, speed_source = calculated_speed, 'CALCULATED'
        else:
            selected_speed, speed_source = None, 'UNAVAILABLE'
            reasons.append('SPEED_UNAVAILABLE')

        usable = quality in ('GOOD', 'FAIR', 'POOR') and timestamp_newer
        if usable:
            self.usable_count += 1
        else:
            self.quality_rejected_count += 1
        if quality == 'UNUSABLE':
            self.last_diagnostic = f'Dokładność GPS {gps_accuracy_m:.0f} m przekracza limit {self.MAX_USABLE_ACCURACY_M:.0f} m.'
        elif not timestamp_newer:
            self.last_diagnostic = 'Telefon przesłał próbkę ze starszym lub powtórzonym czasem.'
        elif selected_speed is None:
            self.last_diagnostic = 'Pozycja dociera, ale telefon nie podał prędkości i brakuje dobrych punktów do jej wyliczenia.'
        elif speed_source == 'STATIONARY_FILTER':
            self.last_diagnostic = 'Filtr potwierdził postój na podstawie stabilnej serii punktów GPS.'
        elif speed_source == 'CALCULATED':
            self.last_diagnostic = 'Prędkość wyliczona z kolejnych punktów GPS.'
        else:
            self.last_diagnostic = 'Telefon podał prędkość bezpośrednio.'

        self._sample = PositionSample(
            timestamp_seconds, road_position_m, selected_speed, latitude, longitude,
            heading_deg, gps_accuracy_m, acceleration_mps2, source, raw_speed,
            calculated_speed, speed_source, quality, usable, tuple(dict.fromkeys(reasons)))
        return self._sample

    def status(self):
        age = None if self.received_at is None else max(0.0, time.monotonic() - self.received_at)
        state = 'WAITING' if age is None else 'STALE' if age > self.STALE_AFTER_SECONDS else 'RECEIVING'
        sample = self._sample
        return dict(
            received_count=self.count,
            usable_count=self.usable_count,
            quality_rejected_count=self.quality_rejected_count,
            age_seconds=age,
            sample_interval_seconds=self.last_interval_seconds,
            state=state,
            position_quality=None if sample is None else sample.position_quality,
            speed_source=None if sample is None else sample.speed_source,
            usable_for_live=bool(sample and sample.usable_for_live and state == 'RECEIVING'),
            diagnostic=self.last_diagnostic)

    def sample(self) -> PositionSample | None:
        return self._sample
