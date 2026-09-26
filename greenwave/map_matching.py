"""Deterministic online matcher for one explicitly selected local route."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from greenwave.route_geometry import RouteProjection


ALGORITHM_VERSION = 'm8-local-beam-v2'


@dataclass(frozen=True)
class MatcherConfig:
    max_accuracy_m: float = 25.0
    max_gap_seconds: float = 5.0
    min_search_radius_m: float = 12.0
    max_search_radius_m: float = 50.0
    minimum_heading_speed_mps: float = 2.0
    maximum_heading_accuracy_deg: float = 30.0
    acquire_samples: int = 2
    off_route_samples: int = 3
    reverse_samples: int = 2
    ambiguity_margin: float = 2.0
    beam_size: int = 5


@dataclass(frozen=True)
class MapMatchResult:
    sample_ref: str | None
    route_id: str | None
    geometry_version: str | None
    geometry_hash: str | None
    algorithm_version: str
    status: str
    reason_codes: tuple[str, ...]
    candidate_segment_index: int | None = None
    candidate_s_m: float | None = None
    candidate_latitude: float | None = None
    candidate_longitude: float | None = None
    cross_track_m: float | None = None
    accepted_s_m: float | None = None
    accepted_latitude: float | None = None
    accepted_longitude: float | None = None
    direction: str = 'UNKNOWN'
    position_uncertainty_m: float | None = None
    receipt_age_seconds: float | None = None
    measurement_age_lower_bound_seconds: float | None = None
    config: dict | None = None

    def as_dict(self):
        return asdict(self)


@dataclass
class _Hypothesis:
    projection: RouteProjection
    cost: float


def _angle_difference(a, b):
    return abs((a - b + 180) % 360 - 180)


class MapMatcher:
    def __init__(self, route=None, config=None):
        self.config = config or MatcherConfig()
        self.route = route
        self.reset()

    def set_route(self, route):
        self.route = route
        self.reset()

    def reset(self):
        self._hypotheses = []
        self._previous_sample = None
        self._previous_best = None
        self._acquire_count = 0
        self._off_route_count = 0
        self._reverse_count = 0
        self.last_result = self._result('NO_ROUTE' if self.route is None else 'NO_FIX', ('NO_SAMPLE',))

    def _result(self, status, reasons, projection=None, direction='UNKNOWN', *, sample_ref=None,
                receipt_age=None, measurement_age=None, accepted=False):
        route = self.route
        result = MapMatchResult(
            sample_ref=sample_ref,
            route_id=None if route is None else route.route_id,
            geometry_version=None if route is None else route.geometry_version,
            geometry_hash=None if route is None else route.geometry_hash,
            algorithm_version=ALGORITHM_VERSION, status=status,
            reason_codes=tuple(dict.fromkeys(reasons)),
            candidate_segment_index=None if projection is None else projection.segment_index,
            candidate_s_m=None if projection is None else projection.s_m,
            candidate_latitude=None if projection is None else projection.latitude,
            candidate_longitude=None if projection is None else projection.longitude,
            cross_track_m=None if projection is None else projection.cross_track_m,
            accepted_s_m=projection.s_m if accepted and projection is not None else None,
            accepted_latitude=projection.latitude if accepted and projection is not None else None,
            accepted_longitude=projection.longitude if accepted and projection is not None else None,
            direction=direction,
            position_uncertainty_m=(None if projection is None else
                max(5.0, projection.cross_track_m,
                    float(getattr(self._current_sample, 'gps_accuracy_m', 0) or 0))),
            receipt_age_seconds=receipt_age,
            measurement_age_lower_bound_seconds=measurement_age,
            config=asdict(self.config))
        self.last_result = result
        return result

    def current(self, receipt_age_seconds=None):
        old = self.last_result
        total_age = None
        if (receipt_age_seconds is not None and
                old.measurement_age_lower_bound_seconds is not None):
            total_age = receipt_age_seconds + old.measurement_age_lower_bound_seconds
        if (receipt_age_seconds is not None and receipt_age_seconds > self.config.max_gap_seconds) or (
                total_age is not None and total_age > self.config.max_gap_seconds):
            reasons = []
            if receipt_age_seconds is not None and receipt_age_seconds > self.config.max_gap_seconds:
                reasons.append('RECEIPT_STALE')
            if total_age is not None and total_age > self.config.max_gap_seconds:
                reasons.append('MEASUREMENT_STALE')
            return MapMatchResult(**{**asdict(old), 'status': 'STALE',
                'reason_codes': tuple(reasons), 'accepted_s_m': None,
                'accepted_latitude': None, 'accepted_longitude': None,
                'receipt_age_seconds': receipt_age_seconds})
        return self.last_result

    def update(self, sample, *, sample_ref=None, receipt_age_seconds=0.0,
               measurement_age_lower_bound_seconds=None, continuity_reset=False,
               diagnostic_replay=False):
        self._current_sample = sample
        advisories = []
        if self.route is None:
            return self._result('NO_ROUTE', ('NO_ROUTE_SELECTED',), sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)
        if sample is None or sample.latitude is None or sample.longitude is None:
            return self._result('NO_FIX', ('LOCATION_MISSING',), sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)
        total_age = (None if receipt_age_seconds is None or
                     measurement_age_lower_bound_seconds is None else
                     receipt_age_seconds + measurement_age_lower_bound_seconds)
        if (receipt_age_seconds is not None and receipt_age_seconds > self.config.max_gap_seconds) or (
                total_age is not None and total_age > self.config.max_gap_seconds):
            self._clear_continuity()
            reasons = []
            if receipt_age_seconds is not None and receipt_age_seconds > self.config.max_gap_seconds:
                reasons.append('RECEIPT_STALE')
            if total_age is not None and total_age > self.config.max_gap_seconds:
                reasons.append('MEASUREMENT_STALE')
            return self._result('STALE', reasons, sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)
        if measurement_age_lower_bound_seconds is None and not diagnostic_replay:
            self._clear_continuity()
            return self._result('UNCERTAIN', ('FRESHNESS_UNKNOWN',), sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=None)
        if measurement_age_lower_bound_seconds is None:
            advisories.append('FRESHNESS_UNKNOWN_REPLAY_ONLY')
        if (measurement_age_lower_bound_seconds is not None and
                measurement_age_lower_bound_seconds > self.config.max_gap_seconds):
            self._clear_continuity()
            return self._result('STALE', ('MEASUREMENT_STALE',), sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)
        if sample.is_mock or not sample.usable_for_live:
            self._clear_continuity()
            return self._result('UNCERTAIN', tuple(sample.quality_reasons) or ('SAMPLE_NOT_USABLE',),
                                sample_ref=sample_ref, receipt_age=receipt_age_seconds,
                                measurement_age=measurement_age_lower_bound_seconds)
        accuracy = sample.gps_accuracy_m
        if accuracy is None or accuracy > self.config.max_accuracy_m:
            self._clear_continuity()
            return self._result('UNCERTAIN', ('GPS_ACCURACY_LIMITED',), sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)
        if continuity_reset:
            self._clear_continuity()

        radius = min(self.config.max_search_radius_m,
                     max(self.config.min_search_radius_m, 2 * accuracy))
        projections = self.route.project(sample.longitude, sample.latitude, max_distance_m=radius)
        # A clamped endpoint is not a separate route hypothesis when the
        # adjoining segment brings us closer to the same GPS fix. Otherwise
        # dense polylines manufacture competing positions along one road.
        by_segment = {item.segment_index: item for item in projections}
        projections = tuple(item for item in projections if not any(
            neighbor is not None and neighbor.cross_track_m < item.cross_track_m - 1e-7
            for neighbor in (
                by_segment.get(item.segment_index - 1) if item.t == 0 else None,
                by_segment.get(item.segment_index + 1) if item.t == 1 else None)))
        if not projections:
            self._off_route_count += 1
            self._acquire_count = 0
            self._hypotheses = []
            status = 'OFF_ROUTE' if self._off_route_count >= self.config.off_route_samples else 'UNCERTAIN'
            return self._result(status, tuple(advisories) + ('NO_CANDIDATE',), sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)

        reliable_heading = (sample.heading_deg is not None and sample.speed_mps is not None and
                            sample.speed_mps >= self.config.minimum_heading_speed_mps and
                            sample.heading_accuracy_deg is not None and
                            sample.heading_accuracy_deg <= self.config.maximum_heading_accuracy_deg)
        hypotheses = []
        for projection in projections:
            sigma = max(accuracy, 5.0)
            cost = (projection.cross_track_m / sigma) ** 2
            direction = 'UNKNOWN'
            if reliable_heading:
                forward_delta = _angle_difference(sample.heading_deg, projection.segment_heading_deg)
                reverse_delta = _angle_difference(sample.heading_deg, (projection.segment_heading_deg + 180) % 360)
                direction = 'FORWARD' if forward_delta <= reverse_delta else 'REVERSE'
                cost += (min(forward_delta, reverse_delta) / 45.0) ** 2
            previous_choices = []
            for old in self._hypotheses:
                transition = self._transition_cost(old.projection, projection, self._previous_sample, sample)
                if transition is not None:
                    previous_choices.append(0.5 * old.cost + transition)
            if self._hypotheses and not previous_choices:
                continue
            if previous_choices:
                cost += min(previous_choices)
            hypotheses.append((_Hypothesis(projection, cost), direction))

        if not hypotheses:
            self._clear_continuity()
            return self._result('UNCERTAIN', tuple(advisories) + ('IMPOSSIBLE_TRANSITION',), projections[0], sample_ref=sample_ref,
                                receipt_age=receipt_age_seconds, measurement_age=measurement_age_lower_bound_seconds)
        hypotheses.sort(key=lambda item: (item[0].cost, item[0].projection.segment_index))
        baseline = hypotheses[0][0].cost
        hypotheses = [(_Hypothesis(item.projection, item.cost - baseline), direction)
                      for item, direction in hypotheses[:self.config.beam_size]]
        best, direction = hypotheses[0]
        alternatives = [item for item, _ in hypotheses[1:]
                        if not (abs(item.projection.s_m - best.projection.s_m) <= 5 and
                                abs(item.projection.segment_index - best.projection.segment_index) <= 1)]
        ambiguous = bool(alternatives and alternatives[0].cost < self.config.ambiguity_margin)

        if not reliable_heading and self._previous_best is not None and self._previous_sample is not None:
            delta = best.projection.s_m - self._previous_best.s_m
            noise = accuracy + (self._previous_sample.gps_accuracy_m or accuracy)
            if abs(delta) > noise:
                direction = 'FORWARD' if delta > 0 else 'REVERSE'

        self._hypotheses = [item for item, _ in hypotheses]
        self._previous_sample = sample
        self._previous_best = best.projection
        self._off_route_count = 0
        if direction == 'REVERSE':
            self._reverse_count += 1
        else:
            self._reverse_count = 0
        if ambiguous:
            self._acquire_count = 0
            return self._result('UNCERTAIN', tuple(advisories) + ('AMBIGUOUS_CANDIDATES',), best.projection, direction,
                                sample_ref=sample_ref, receipt_age=receipt_age_seconds,
                                measurement_age=measurement_age_lower_bound_seconds)
        self._acquire_count += 1
        if self._reverse_count >= self.config.reverse_samples:
            return self._result('WRONG_DIRECTION', tuple(advisories) + ('REVERSE_DIRECTION',), best.projection, 'REVERSE',
                                sample_ref=sample_ref, receipt_age=receipt_age_seconds,
                                measurement_age=measurement_age_lower_bound_seconds)
        if self._acquire_count < self.config.acquire_samples:
            return self._result('ACQUIRING', tuple(advisories) + ('NEEDS_CONFIRMATION',), best.projection, direction,
                                sample_ref=sample_ref, receipt_age=receipt_age_seconds,
                                measurement_age=measurement_age_lower_bound_seconds)
        return self._result('MATCHED', tuple(advisories), best.projection, direction, sample_ref=sample_ref,
                            receipt_age=receipt_age_seconds,
                            measurement_age=measurement_age_lower_bound_seconds, accepted=True)

    def _clear_continuity(self):
        self._hypotheses = []
        self._previous_sample = None
        self._previous_best = None
        self._acquire_count = 0
        self._reverse_count = 0
        self._off_route_count = 0

    def _transition_cost(self, previous, current, previous_sample, sample):
        if previous_sample is None:
            return 0.0
        previous_time = previous_sample.elapsed_realtime_nanos
        current_time = sample.elapsed_realtime_nanos
        if previous_time is not None and current_time is not None:
            dt = (current_time - previous_time) / 1_000_000_000
        else:
            dt = sample.elapsed_seconds - previous_sample.elapsed_seconds
        if dt <= 0 or dt > self.config.max_gap_seconds:
            return None
        delta = abs(current.s_m - previous.s_m)
        speeds = [value for value in (previous_sample.speed_mps, sample.speed_mps)
                  if value is not None and value >= 0]
        accuracy_sum = (previous_sample.gps_accuracy_m or 0) + (sample.gps_accuracy_m or 0)
        if speeds:
            expected = sum(speeds) / len(speeds) * dt
            vmax = max(5.0, max(speeds) + 5.0)
        else:
            expected = None
            vmax = 80.0
        if delta > vmax * dt + 2 * accuracy_sum + 10:
            return None
        if expected is None:
            return 0.0
        return ((delta - expected) / max(10.0, accuracy_sum)) ** 2
