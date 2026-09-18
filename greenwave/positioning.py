from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Protocol
import math
import re
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
    device_id: str | None = None
    stream_id: str | None = None
    sample_sequence: int | None = None
    elapsed_realtime_nanos: int | None = None
    speed_accuracy_mps: float | None = None
    heading_accuracy_deg: float | None = None
    altitude_m: float | None = None
    vertical_accuracy_m: float | None = None
    is_mock: bool | None = None


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
    MOVEMENT_RELEASE_SPEED_MPS = 2.7 / 3.6
    MOVEMENT_RELEASE_CALCULATED_MPS = 1.2
    MOVEMENT_RELEASE_SAMPLES = 2

    def __init__(self):
        self.reset()

    def reset(self):
        self._sample = None
        self.received_at = None
        self.count = 0
        self.transmission_count = 0
        self.duplicate_count = 0
        self.last_update_accepted = True
        self.usable_count = 0
        self.quality_rejected_count = 0
        self.last_interval_seconds = None
        self.last_diagnostic = 'Oczekiwanie na pierwszą próbkę.'
        self._last_timestamp = None
        self._points = deque(maxlen=12)
        self._calculated_speeds = deque(maxlen=5)
        self._last_sequence_by_stream = {}
        self._stationary_latched = False
        self._movement_evidence_count = 0

    @staticmethod
    def _number(value, name, *, optional=False):
        if value is None and optional:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{name} must be a finite number')
        return float(value)

    @staticmethod
    def _identifier(value, name, *, optional=True):
        if value is None and optional:
            return None
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}', value):
            raise ValueError(f'{name} must be a 1–80 character identifier')
        return value

    @staticmethod
    def _integer(value, name, *, optional=True):
        if value is None and optional:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f'{name} must be a non-negative integer')
        return value

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
               road_position_m: float | None = None, source: str = 'EXTERNAL',
               device_id: str | None = None, stream_id: str | None = None,
               sample_sequence: int | None = None,
               elapsed_realtime_nanos: int | None = None,
               speed_accuracy_mps: float | None = None,
               heading_accuracy_deg: float | None = None,
               altitude_m: float | None = None,
               vertical_accuracy_m: float | None = None,
               is_mock: bool | None = None):
        timestamp_seconds = self._number(timestamp_seconds, 'timestamp_seconds')
        speed_mps = self._number(speed_mps, 'speed_mps', optional=True)
        latitude = self._number(latitude, 'latitude', optional=True)
        longitude = self._number(longitude, 'longitude', optional=True)
        heading_deg = self._number(heading_deg, 'heading_deg', optional=True)
        gps_accuracy_m = self._number(gps_accuracy_m, 'gps_accuracy_m', optional=True)
        acceleration_mps2 = self._number(acceleration_mps2, 'acceleration_mps2', optional=True)
        road_position_m = self._number(road_position_m, 'road_position_m', optional=True)
        speed_accuracy_mps = self._number(speed_accuracy_mps, 'speed_accuracy_mps', optional=True)
        heading_accuracy_deg = self._number(heading_accuracy_deg, 'heading_accuracy_deg', optional=True)
        altitude_m = self._number(altitude_m, 'altitude_m', optional=True)
        vertical_accuracy_m = self._number(vertical_accuracy_m, 'vertical_accuracy_m', optional=True)
        device_id = self._identifier(device_id, 'device_id')
        stream_id = self._identifier(stream_id, 'stream_id')
        sample_sequence = self._integer(sample_sequence, 'sample_sequence')
        elapsed_realtime_nanos = self._integer(elapsed_realtime_nanos, 'elapsed_realtime_nanos')
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
        if any(value is not None and value < 0 for value in
               (speed_accuracy_mps, heading_accuracy_deg, vertical_accuracy_m)):
            raise ValueError('Accuracy values must be non-negative')
        if is_mock is not None and not isinstance(is_mock, bool):
            raise ValueError('is_mock must be a boolean')
        if not isinstance(source, str) or source not in ('EXTERNAL', 'WEB_GEOLOCATION', 'ANDROID_FUSED'):
            raise ValueError('Unknown external position source')
        native_identity = (device_id, stream_id, sample_sequence)
        if source == 'ANDROID_FUSED' and any(value is None for value in native_identity):
            raise ValueError('ANDROID_FUSED requires device_id, stream_id and sample_sequence')
        if source != 'ANDROID_FUSED' and any(value is not None for value in native_identity):
            raise ValueError('Native identity fields require ANDROID_FUSED source')

        now = time.monotonic()
        self.transmission_count += 1
        if stream_id is not None:
            stream_key = (device_id, stream_id)
            previous_sequence = self._last_sequence_by_stream.get(stream_key)
            if previous_sequence is not None and sample_sequence <= previous_sequence:
                self.duplicate_count += 1
                self.last_update_accepted = False
                self.last_diagnostic = 'Powtórzona próbka Androida została bezpiecznie pominięta.'
                return self._sample
            self._last_sequence_by_stream[stream_key] = sample_sequence
        self.last_update_accepted = True
        self.last_interval_seconds = None if self.received_at is None else max(0.0, now - self.received_at)
        self.received_at = now
        self.count += 1
        reasons = []
        if is_mock:
            reasons.append('MOCK_LOCATION')
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

        stationary_evidence = timestamp_newer and self._stationary_confirmed(
            timestamp_seconds, latitude, longitude, gps_accuracy_m)
        device_movement_reliable = (
            raw_speed is not None and raw_speed >= self.MOVEMENT_RELEASE_SPEED_MPS and
            (speed_accuracy_mps is None or speed_accuracy_mps <= 1.5))
        calculated_movement_reliable = (
            quality in ('GOOD', 'FAIR', 'POOR') and calculated_speed is not None and
            calculated_speed >= self.MOVEMENT_RELEASE_CALCULATED_MPS)
        movement_reliable = timestamp_newer and (
            device_movement_reliable or calculated_movement_reliable)
        movement_released = False
        if self._stationary_latched:
            self._movement_evidence_count = (
                self._movement_evidence_count + 1 if movement_reliable else 0)
            if self._movement_evidence_count >= self.MOVEMENT_RELEASE_SAMPLES:
                self._stationary_latched = False
                self._movement_evidence_count = 0
                movement_released = True
        elif stationary_evidence and (raw_speed is None or raw_speed <= self.STATIONARY_DEVICE_SPEED_MPS):
            self._stationary_latched = True
            self._movement_evidence_count = 0

        if self._stationary_latched:
            selected_speed, speed_source = 0.0, 'STATIONARY_FILTER'
            calculated_speed = 0.0
        elif raw_speed is not None:
            selected_speed, speed_source = raw_speed, 'DEVICE'
        elif calculated_speed is not None:
            selected_speed, speed_source = calculated_speed, 'CALCULATED'
        else:
            selected_speed, speed_source = None, 'UNAVAILABLE'
            reasons.append('SPEED_UNAVAILABLE')

        usable = quality in ('GOOD', 'FAIR', 'POOR') and timestamp_newer and not is_mock
        if usable:
            self.usable_count += 1
        else:
            self.quality_rejected_count += 1
        if is_mock:
            self.last_diagnostic = 'Android oznaczył lokalizację jako testową; próbka nie steruje aplikacją.'
        elif quality == 'UNUSABLE':
            self.last_diagnostic = f'Dokładność GPS {gps_accuracy_m:.0f} m przekracza limit {self.MAX_USABLE_ACCURACY_M:.0f} m.'
        elif not timestamp_newer:
            self.last_diagnostic = 'Telefon przesłał próbkę ze starszym lub powtórzonym czasem.'
        elif selected_speed is None:
            self.last_diagnostic = 'Pozycja dociera, ale telefon nie podał prędkości i brakuje dobrych punktów do jej wyliczenia.'
        elif speed_source == 'STATIONARY_FILTER':
            self.last_diagnostic = 'Filtr utrzymuje potwierdzony postój; ruszenie wymaga dwóch wiarygodnych próbek.'
        elif movement_released:
            self.last_diagnostic = 'Filtr potwierdził ponowne ruszenie na podstawie kolejnych próbek.'
        elif speed_source == 'CALCULATED':
            self.last_diagnostic = 'Prędkość wyliczona z kolejnych punktów GPS.'
        else:
            self.last_diagnostic = 'Telefon podał prędkość bezpośrednio.'

        self._sample = PositionSample(
            elapsed_seconds=timestamp_seconds, road_position_m=road_position_m,
            speed_mps=selected_speed, latitude=latitude, longitude=longitude,
            heading_deg=heading_deg, gps_accuracy_m=gps_accuracy_m,
            acceleration_mps2=acceleration_mps2, source=source,
            raw_speed_mps=raw_speed, calculated_speed_mps=calculated_speed,
            speed_source=speed_source, position_quality=quality,
            usable_for_live=usable, quality_reasons=tuple(dict.fromkeys(reasons)),
            device_id=device_id, stream_id=stream_id,
            sample_sequence=sample_sequence,
            elapsed_realtime_nanos=elapsed_realtime_nanos,
            speed_accuracy_mps=speed_accuracy_mps,
            heading_accuracy_deg=heading_accuracy_deg, altitude_m=altitude_m,
            vertical_accuracy_m=vertical_accuracy_m, is_mock=is_mock)
        return self._sample

    def status(self):
        age = None if self.received_at is None else max(0.0, time.monotonic() - self.received_at)
        state = 'WAITING' if age is None else 'STALE' if age > self.STALE_AFTER_SECONDS else 'RECEIVING'
        sample = self._sample
        return dict(
            received_count=self.count,
            transmission_count=self.transmission_count,
            duplicate_count=self.duplicate_count,
            usable_count=self.usable_count,
            quality_rejected_count=self.quality_rejected_count,
            age_seconds=age,
            sample_interval_seconds=self.last_interval_seconds,
            state=state,
            position_quality=None if sample is None else sample.position_quality,
            speed_source=None if sample is None else sample.speed_source,
            motion_state=('STATIONARY' if self._stationary_latched else
                          'MOVING' if sample and sample.speed_mps is not None and
                          sample.speed_mps >= self.MOVEMENT_RELEASE_SPEED_MPS else 'UNKNOWN'),
            movement_evidence_count=self._movement_evidence_count,
            sample_source=None if sample is None else sample.source,
            device_id=None if sample is None else sample.device_id,
            stream_id=None if sample is None else sample.stream_id,
            usable_for_live=bool(sample and sample.usable_for_live and state == 'RECEIVING'),
            diagnostic=self.last_diagnostic)

    def sample(self) -> PositionSample | None:
        return self._sample
