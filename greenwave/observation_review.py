"""Derived passenger observations joined to exact recorded device samples."""
from datetime import datetime
from dataclasses import asdict


def review_observations(rows, replay, route, attestation=None):
    matches = {sample.sequence: match for sample, match in
               zip(replay.samples, replay.match_history)}
    replay_evidence = {sample.sample_ref: dict(
        status=match['status'], direction=match['direction'],
        reason_codes=match.get('reason_codes', []),
        candidate_s_m=match['candidate_s_m'])
        for sample, match in zip(replay.samples, replay.match_history)
        if hasattr(sample, 'sample_ref')}
    device_samples = {}
    for row in rows:
        if row['event'] == 'EXTERNAL_TELEMETRY':
            p = row['payload']
            key = f"{p.get('device_id')}:{p.get('stream_id')}:{p.get('sample_sequence')}"
            device_samples[key] = row
    lines = {} if route is None else {line.stop_line_id: line for line in route.stop_lines}
    groups = {key: dict(stop_line_id=key, observations=[], intervals=[],
                        crossings=[]) for key in lines}
    previous = {}
    last_raw = {}
    for row in rows:
        if row['event'] != 'ROUTE_OBSERVATION':
            continue
        p = row['payload']
        if route is None or p.get('route_id') != route.route_id or p.get('geometry_hash') != route.geometry_hash:
            continue
        key = p.get('stop_line_id')
        if key not in groups:
            continue
        stamp = datetime.fromisoformat(p['timestamp']) if p.get('timestamp') else row['received_at']
        old = previous.get(key)
        repeated = old is not None and old['state'] == p.get('state')
        delta = None if old is None else (stamp - datetime.fromisoformat(old['timestamp'])).total_seconds()
        last = last_raw.get(key)
        rapid = (last is not None and last['state'] == p.get('state') and
                 0 <= (stamp - datetime.fromisoformat(last['timestamp'])).total_seconds() <= 1)
        classification = ('RAPID_DUPLICATE' if rapid else
                          'REPEATED_STATE_REVIEW' if repeated else 'KEEP')
        transition = (p.get('event_type') == 'STATE_START' or
                      bool(attestation and p.get('state') in attestation.get('transition_states', [])))
        sample = device_samples.get(p.get('sample_ref'))
        match = None if sample is None else matches.get(sample['sequence'])
        distance = None if not match or match['candidate_s_m'] is None else lines[key].s_m - match['candidate_s_m']
        entry = dict(observation_id=p.get('observation_id'), record_sequence=row['sequence'],
            timestamp=stamp.isoformat(), state=p.get('state'), raw_type=p.get('event_type'),
            reviewed_type='STATE_START' if transition else 'STATE_SEEN',
            interpretation_source='RECORDED' if p.get('event_type') == 'STATE_START' else
                'USER_ATTESTATION' if transition else 'RECORDED',
            classification=classification, included_in_intervals=classification == 'KEEP' and transition,
            sample_ref=p.get('sample_ref'), sample_record_sequence=None if sample is None else sample['sequence'],
            latitude=p.get('gps_latitude'), longitude=p.get('gps_longitude'),
            speed_mps=None if sample is None else sample['speed'],
            gps_accuracy_m=None if sample is None else sample['accuracy_value'],
            gps_freshness=p.get('gps_freshness'), gps_receipt_age_seconds=p.get('gps_receipt_age_seconds'),
            recorded_match_status=p.get('map_match_status'),
            reprocessed_match_status=None if match is None else match['status'],
            reprocessed_reason_codes=[] if match is None else match.get('reason_codes', []),
            reprocessed_direction=None if match is None else match['direction'],
            candidate_distance_to_line_m=distance,
            distance_is_accepted=bool(match and match['status'] == 'MATCHED'),
            position_uncertainty_m=None if match is None else match['position_uncertainty_m'])
        groups[key]['observations'].append(entry)
        last_raw[key] = entry
        if classification == 'KEEP':
            if old and old['included_in_intervals'] and entry['included_in_intervals'] and delta > 0:
                groups[key]['intervals'].append(dict(from_state=old['state'], to_state=entry['state'],
                    seconds=delta, start_observation_id=old['observation_id'],
                    end_observation_id=entry['observation_id'],
                    meaning='OBSERVED_RED_INTERVAL' if old['state'] == 'RED' and entry['state'] == 'GREEN'
                        else 'OBSERVED_TRANSITION_INTERVAL_NOT_GREEN_DURATION',
                    note='Passenger click times include reaction delay; no cycle or yellow duration inferred.'))
            previous[key] = entry
    for event in replay.detector.events:
        if event.stop_line_id in groups:
            groups[event.stop_line_id]['crossings'].append(dict(asdict(event),
                before_match=replay_evidence.get(event.before_sample_ref),
                after_match=replay_evidence.get(event.after_sample_ref)))
    return dict(attestation=attestation, points=list(groups.values()),
        note='Derived review only. Raw events, geometry verification and live phase predictions remain unchanged.')
