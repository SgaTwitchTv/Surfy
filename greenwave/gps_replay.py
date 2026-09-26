"""Read-only, deterministic replay of immutable external GPS telemetry."""
from dataclasses import asdict, dataclass

from greenwave.analysis import RunAnalysis
from greenwave.map_matching import MapMatcher
from greenwave.positioning import PositionSample
from greenwave.route_events import StopLineCrossingDetector, next_stop_line


@dataclass(frozen=True)
class GPSReplaySample:
    sample_ref: str
    sequence: int
    timeline_seconds: float
    received_at: str
    phone_timestamp_seconds: float | None
    receipt_offset_seconds: float
    timeline_source: str
    position: PositionSample


class GPSReplaySession:
    def __init__(self, logger, route=None):
        self.logger = logger
        self.route = route
        self.reset()

    def reset(self):
        self.run_id = None
        self.samples = []
        self.time = 0.0
        self.cursor = 0
        self.running = False
        self.rate = 1.0
        self.error = None
        self.bounds = None
        self.endpoints = None
        self.current_sample = None
        self._previous_processed = None
        self.trail = []
        self.match_history = []
        self.matcher = MapMatcher(self.route)
        self.detector = StopLineCrossingDetector(self.route, 'replay')
        self.match_result = self.matcher.last_result

    def set_route(self, route):
        self.route = route
        self.matcher.set_route(route)
        self.detector.set_route(route, 'replay')
        if self.run_id is not None:
            self._rebuild()

    @property
    def duration(self):
        return self.samples[-1].timeline_seconds if self.samples else 0.0

    def load(self, run_id):
        _, _, rows = RunAnalysis(self.logger)._read(run_id)
        external = [row for row in rows if row['event'] == 'EXTERNAL_TELEMETRY']
        if not external:
            raise ValueError('Nagranie nie zawiera EXTERNAL_TELEMETRY')
        first_received = external[0]['received_at']
        timeline = 0.0
        previous = None
        samples = []
        for row in external:
            payload = row['payload']
            stream = (payload.get('device_id'), payload.get('stream_id'))
            elapsed = payload.get('elapsed_realtime_nanos')
            phone = payload.get('phone_timestamp_seconds')
            source = 'START'
            if previous is not None:
                previous_payload = previous['payload']
                previous_stream = (previous_payload.get('device_id'), previous_payload.get('stream_id'))
                previous_elapsed = previous_payload.get('elapsed_realtime_nanos')
                previous_phone = previous_payload.get('phone_timestamp_seconds')
                receipt_delta = max(0.0, (row['received_at'] - previous['received_at']).total_seconds())
                if stream == previous_stream and isinstance(elapsed, int) and isinstance(previous_elapsed, int):
                    if elapsed > previous_elapsed:
                        delta, source = (elapsed - previous_elapsed) / 1_000_000_000, 'DEVICE_MONOTONIC'
                    else:
                        # A monotonic clock must never move backwards inside a
                        # stream.  Treat this as a hard continuity boundary;
                        # wall-clock time cannot repair that identity break.
                        delta, source = receipt_delta, 'RECEIPT_BOUNDARY'
                elif stream == previous_stream and isinstance(phone, (int, float)) and isinstance(previous_phone, (int, float)) and phone > previous_phone:
                    delta, source = phone - previous_phone, 'PHONE_UTC_FALLBACK'
                else:
                    delta, source = receipt_delta, 'RECEIPT_BOUNDARY'
                timeline += max(0.0, delta)
            position = PositionSample(
                elapsed_seconds=float(phone if isinstance(phone, (int, float)) else timeline),
                road_position_m=row['position'], speed_mps=row['speed'],
                latitude=row['latitude_value'], longitude=row['longitude_value'],
                heading_deg=float(row['heading']) if row.get('heading') else None,
                gps_accuracy_m=row['accuracy_value'],
                acceleration_mps2=payload.get('acceleration_mps2'),
                source=row.get('source') or 'EXTERNAL',
                raw_speed_mps=payload.get('raw_speed_mps'),
                calculated_speed_mps=payload.get('calculated_speed_mps'),
                speed_source=payload.get('speed_source') or 'UNAVAILABLE',
                position_quality=payload.get('position_quality') or 'UNKNOWN',
                usable_for_live=payload.get('usable_for_live') is True,
                quality_reasons=tuple(payload.get('quality_reasons') or ()),
                device_id=payload.get('device_id'), stream_id=payload.get('stream_id'),
                sample_sequence=payload.get('sample_sequence'), elapsed_realtime_nanos=elapsed,
                sent_elapsed_realtime_nanos=payload.get('sent_elapsed_realtime_nanos'),
                measurement_age_lower_bound_seconds=payload.get('measurement_age_lower_bound_seconds'),
                freshness_status=payload.get('freshness_status', 'UNKNOWN'),
                speed_accuracy_mps=payload.get('speed_accuracy_mps'),
                heading_accuracy_deg=payload.get('heading_accuracy_deg'),
                altitude_m=payload.get('altitude_m'), vertical_accuracy_m=payload.get('vertical_accuracy_m'),
                is_mock=payload.get('is_mock'))
            samples.append(GPSReplaySample(
                sample_ref=f'{run_id}:{row["sequence"]}', sequence=row['sequence'], timeline_seconds=timeline,
                received_at=row['received_at'].isoformat(), phone_timestamp_seconds=phone,
                receipt_offset_seconds=(row['received_at'] - first_received).total_seconds(),
                timeline_source=source, position=position))
            previous = row
        self.run_id, self.samples = run_id, samples
        coordinates = [(sample.position.longitude, sample.position.latitude) for sample in samples
                       if sample.position.longitude is not None and sample.position.latitude is not None]
        self.bounds = (None if not coordinates else
                       [min(value[0] for value in coordinates), min(value[1] for value in coordinates),
                        max(value[0] for value in coordinates), max(value[1] for value in coordinates)])
        valid_samples = [sample for sample in samples if sample.position.longitude is not None and
                         sample.position.latitude is not None]
        self.endpoints = (None if not valid_samples else dict(
            start=dict(longitude=valid_samples[0].position.longitude,
                       latitude=valid_samples[0].position.latitude),
            end=dict(longitude=valid_samples[-1].position.longitude,
                     latitude=valid_samples[-1].position.latitude)))
        self.time = 0.0
        self.running = False
        self.error = None
        self._rebuild()
        return self.state()

    def _rebuild(self):
        self.cursor = 0
        self.current_sample = None
        self._previous_processed = None
        self.trail = []
        self.match_history = []
        self.matcher.reset()
        self.detector.reset('replay')
        self.match_result = self.matcher.last_result
        self._process_until(self.time)

    def _process_until(self, target_time):
        while (self.cursor < len(self.samples) and
               self.samples[self.cursor].timeline_seconds <= target_time + 1e-9):
            sample = self.samples[self.cursor]
            previous = self._previous_processed
            stream = (sample.position.device_id, sample.position.stream_id)
            previous_stream = (None if previous is None else
                               (previous.position.device_id, previous.position.stream_id))
            continuity_reset = previous is not None and (
                sample.timeline_source == 'RECEIPT_BOUNDARY' or
                stream != previous_stream or
                sample.timeline_seconds - previous.timeline_seconds > self.matcher.config.max_gap_seconds)
            measurement_age = sample.position.measurement_age_lower_bound_seconds
            # Old immutable logs remain replayable for diagnostics, but are explicitly marked unknown.
            self.match_result = self.matcher.update(sample.position, sample_ref=sample.sample_ref,
                receipt_age_seconds=0.0, measurement_age_lower_bound_seconds=measurement_age,
                continuity_reset=continuity_reset, diagnostic_replay=True)
            self.match_history.append(self.match_result.as_dict())
            self.detector.update(self.match_result, sample_time_seconds=sample.timeline_seconds,
                                 sample_ref=sample.sample_ref)
            self.current_sample = sample
            self.trail.append(dict(latitude=sample.position.latitude, longitude=sample.position.longitude,
                                   accepted=(sample.position.usable_for_live and
                                             self.match_result.status not in ('STALE', 'NO_FIX')),
                                   quality_reasons=list(sample.position.quality_reasons),
                                   sample_ref=sample.sample_ref, timeline_seconds=sample.timeline_seconds,
                                   matched_latitude=self.match_result.accepted_latitude,
                                   matched_longitude=self.match_result.accepted_longitude,
                                   match_status=self.match_result.status))
            self.cursor += 1
            self._previous_processed = sample

    def seek(self, seconds):
        if self.run_id is None:
            raise ValueError('Najpierw wczytaj nagranie GPS')
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 <= seconds <= self.duration:
            raise ValueError('Seek poza nagraniem GPS')
        self.time = float(seconds)
        self.running = False
        self._rebuild()
        return self.state()

    def advance(self, real_seconds):
        if not self.running or self.run_id is None:
            return self.state()
        if isinstance(real_seconds, bool) or not isinstance(real_seconds, (int, float)) or real_seconds < 0:
            raise ValueError('Invalid GPS replay delta')
        self.time = min(self.duration, self.time + real_seconds * self.rate)
        self._process_until(self.time)
        if self.time >= self.duration - 1e-9:
            self.running = False
        return self.state()

    def command(self, command, value=None):
        if command == 'load': return self.load(value)
        if command == 'play':
            if self.run_id is None: raise ValueError('Najpierw wczytaj nagranie GPS')
            self.running = True; return self.state()
        if command == 'pause': self.running = False; return self.state()
        if command == 'seek': return self.seek(value)
        if command == 'rate':
            if value not in (1, 2, 5): raise ValueError('Allowed GPS replay rates: 1, 2, 5')
            self.rate = value; return self.state()
        if command == 'reset':
            if self.run_id is None: raise ValueError('Najpierw wczytaj nagranie GPS')
            return self.seek(0)
        raise ValueError('Unknown GPS replay command')

    def state(self):
        sample = None
        if self.current_sample is not None:
            sample = asdict(self.current_sample)
        return dict(loaded=self.run_id is not None, run_id=self.run_id, running=self.running,
                    rate=self.rate, timeline_seconds=self.time, duration=self.duration,
                    cursor=self.cursor, sample_count=len(self.samples), sample=sample,
                    trail=self.trail, bounds=self.bounds, endpoints=self.endpoints,
                    mapping=self.match_result.as_dict(),
                    next_stop_line=next_stop_line(self.route, self.match_result),
                    crossing_events=[asdict(event) for event in self.detector.events], error=self.error)
