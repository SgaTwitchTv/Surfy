"""Explicit, fail-closed bridge from live map matching to the speed solver."""
from dataclasses import asdict, dataclass

from greenwave.route_events import next_stop_line


@dataclass(frozen=True)
class LiveNavigationInput:
    route_id: str
    geometry_version: str
    geometry_hash: str
    sample_ref: str
    position_s_m: float
    speed_mps: float
    speed_limit_mps: float
    prediction_time_seconds: float
    stop_line_id: str
    signal_id: str
    distance_m: float


def evaluate_live_navigation(route, result, sample, external_status, *,
                             prediction_time_seconds=None,
                             phase_data_verified=False):
    """Return every failed prerequisite and an input only when all pass."""
    reasons = []
    if sample is None or not external_status.get('live_control_eligible'):
        reasons.append('POSITION_NOT_FRESH_OR_UNVERIFIED')
    if result.status != 'MATCHED':
        reasons.append('ROUTE_NOT_MATCHED')
    if result.direction != 'FORWARD':
        reasons.append('FORWARD_DIRECTION_NOT_CONFIRMED')
    if sample is None or sample.speed_mps is None:
        reasons.append('SPEED_UNAVAILABLE')
    if route is None or route.geometry_verification.get('status') != 'FIELD_CHECKED':
        reasons.append('GEOMETRY_NOT_FIELD_VERIFIED')

    next_line = next_stop_line(route, result)
    line = None
    if next_line is None:
        reasons.append('NEXT_STOP_LINE_UNAVAILABLE')
    elif route is not None:
        line = next((item for item in route.stop_lines
                     if item.stop_line_id == next_line['stop_line_id']), None)
        if line is None or line.verification.get('status') != 'FIELD_CHECKED':
            reasons.append('STOP_LINE_NOT_FIELD_VERIFIED')
        if line is None or not line.signal_id:
            reasons.append('SIGNAL_ID_UNAVAILABLE')

    speed_section = None
    if route is not None and result.accepted_s_m is not None:
        speed_section = next((section for section in route.speed_sections
                              if section['start_s_m'] <= result.accepted_s_m <= section['end_s_m']), None)
    if speed_section is None or speed_section.get('verification', {}).get('status') != 'FIELD_CHECKED':
        reasons.append('SPEED_LIMIT_NOT_FIELD_VERIFIED')
    if not phase_data_verified:
        reasons.append('LIVE_PHASE_DATA_UNAVAILABLE')
    if prediction_time_seconds is None:
        reasons.append('PREDICTION_CLOCK_UNAVAILABLE')

    reasons = list(dict.fromkeys(reasons))
    solver_input = None
    if not reasons:
        solver_input = LiveNavigationInput(
            route_id=route.route_id,
            geometry_version=route.geometry_version,
            geometry_hash=route.geometry_hash,
            sample_ref=result.sample_ref,
            position_s_m=result.accepted_s_m,
            speed_mps=sample.speed_mps,
            speed_limit_mps=speed_section['limit_mps'],
            prediction_time_seconds=prediction_time_seconds,
            stop_line_id=line.stop_line_id,
            signal_id=line.signal_id,
            distance_m=next_line['distance_m'])
    return dict(allowed=not reasons, reason_codes=reasons,
                solver_input=None if solver_input is None else asdict(solver_input),
                target_speed_kmh=None,
                note='Pozycja i dystanse działają niezależnie od rekomendacji live.')
