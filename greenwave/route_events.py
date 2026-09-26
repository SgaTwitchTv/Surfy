"""Route-derived distances and conservative stop-line crossing events."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StopLineCrossing:
    traversal_id: str
    stop_line_id: str
    signal_id: str | None
    before_sample_ref: str | None
    after_sample_ref: str | None
    time_start_seconds: float
    time_end_seconds: float
    estimated_time_seconds: float | None
    status: str = 'CONFIRMED'
    reason_code: str | None = None


def next_stop_line(route, result):
    if route is None or result is None or result.status != 'MATCHED' or result.accepted_s_m is None:
        return None
    candidates = [line for line in route.stop_lines if line.s_m >= result.accepted_s_m]
    if not candidates:
        return None
    line = min(candidates, key=lambda item: item.s_m)
    distance = line.s_m - result.accepted_s_m
    uncertainty = (result.position_uncertainty_m or 0) + line.position_uncertainty_m
    return dict(stop_line_id=line.stop_line_id, signal_id=line.signal_id, s_m=line.s_m,
                distance_m=distance, distance_min_m=distance - uncertainty,
                distance_max_m=distance + uncertainty,
                verification=line.verification, position_uncertainty_m=line.position_uncertainty_m)


class StopLineCrossingDetector:
    def __init__(self, route=None, traversal_id='live-1'):
        self.route = route
        self.traversal_id = traversal_id
        self.reset(traversal_id)

    def set_route(self, route, traversal_id=None):
        self.route = route
        self.reset(traversal_id or self.traversal_id)

    def reset(self, traversal_id='live-1'):
        self.traversal_id = traversal_id
        self._armed = {}
        self._emitted = set()
        self._unconfirmed = set()
        self.events = []

    def update(self, result, *, sample_time_seconds, sample_ref=None):
        if self.route is None:
            return []
        if result.status != 'MATCHED' or result.direction != 'FORWARD' or result.accepted_s_m is None:
            return self._interrupt(sample_time_seconds, sample_ref,
                                   f'MATCH_LOST_{result.status}')
        low = result.accepted_s_m - (result.position_uncertainty_m or 0)
        high = result.accepted_s_m + (result.position_uncertainty_m or 0)
        created = []
        for line in self.route.stop_lines:
            key = (self.traversal_id, line.stop_line_id)
            if key in self._emitted:
                continue
            uncertainty = line.position_uncertainty_m
            if high < line.s_m - uncertainty:
                if line.s_m - result.accepted_s_m <= 80:
                    self._armed[line.stop_line_id] = (sample_time_seconds, sample_ref, result.accepted_s_m)
                continue
            if low <= line.s_m + uncertainty:
                continue
            before = self._armed.pop(line.stop_line_id, None)
            if before is None:
                continue
            before_time, before_ref, before_s = before
            if sample_time_seconds <= before_time or sample_time_seconds - before_time > 5:
                if key not in self._unconfirmed:
                    event = StopLineCrossing(
                        self.traversal_id, line.stop_line_id, line.signal_id,
                        before_ref, sample_ref, before_time, sample_time_seconds, None,
                        'UNCONFIRMED', 'CONTINUITY_GAP')
                    self._unconfirmed.add(key)
                    self.events.append(event)
                    created.append(asdict(event))
                continue
            denominator = result.accepted_s_m - before_s
            ratio = None if denominator <= 0 else max(0.0, min(1.0, (line.s_m - before_s) / denominator))
            estimate = None if ratio is None else before_time + ratio * (sample_time_seconds - before_time)
            event = StopLineCrossing(self.traversal_id, line.stop_line_id, line.signal_id,
                                     before_ref, sample_ref, before_time, sample_time_seconds, estimate)
            self._emitted.add(key)
            self.events.append(event)
            created.append(asdict(event))
        return created

    def _interrupt(self, sample_time_seconds, sample_ref, reason_code):
        created = []
        for stop_line_id, (before_time, before_ref, _before_s) in list(self._armed.items()):
            line = next((item for item in self.route.stop_lines
                         if item.stop_line_id == stop_line_id), None)
            key = (self.traversal_id, stop_line_id)
            if line is None or key in self._unconfirmed or line.s_m - _before_s > 80:
                continue
            event = StopLineCrossing(
                self.traversal_id, line.stop_line_id, line.signal_id,
                before_ref, sample_ref, before_time, sample_time_seconds, None,
                'UNCONFIRMED', reason_code)
            self.events.append(event)
            created.append(asdict(event))
            self._unconfirmed.add(key)
        self._armed.clear()
        return created
