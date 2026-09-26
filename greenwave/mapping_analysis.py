"""Derived map-matching reports that never mutate immutable source runs."""
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from uuid import uuid4

from greenwave.analysis import RunAnalysis
from greenwave.gps_replay import GPSReplaySession
from greenwave.observation_review import review_observations


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode('utf-8')


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction + .999999))]


class MappingAnalysis:
    def __init__(self, logger, root=None):
        self.logger = logger
        self.root = Path(root) if root is not None else logger.root.parent / 'derived' / 'mapping'

    def analyze(self, run_id, route=None, *, write=False):
        replay = GPSReplaySession(self.logger, route)
        replay.load(run_id)
        replay.seek(replay.duration)
        _metadata, _complete, raw_rows = RunAnalysis(self.logger)._read(run_id)
        route_observations = []
        synthetic_observation_count = 0
        for row in raw_rows:
            if row['event'] == 'ROUTE_OBSERVATION':
                observation = row['payload']
                route_observations.append(dict(
                    event_type='ROUTE_OBSERVATION', record_sequence=row['sequence'],
                    received_at=row['received_at'].isoformat(),
                    observation_id=observation.get('observation_id'),
                    route_id=observation.get('route_id'),
                    geometry_hash=observation.get('geometry_hash'),
                    stop_line_id=observation.get('stop_line_id'),
                    state=observation.get('state'),
                    observation_type=observation.get('event_type'),
                    gps_freshness=observation.get('gps_freshness'),
                    map_match_status=observation.get('map_match_status'),
                    matches_analyzed_route=bool(route is not None and
                        observation.get('route_id') == route.route_id and
                        observation.get('geometry_hash') == route.geometry_hash)))
            elif row['event'] in ('STATE_SEEN', 'GREEN_START', 'YELLOW_START', 'RED_START'):
                synthetic_observation_count += 1
        matches = list(replay.match_history)
        match_rows = []
        for replay_sample, match in zip(replay.samples, matches):
            match_rows.append(dict(
                sample_ref=replay_sample.sample_ref,
                timeline_seconds=replay_sample.timeline_seconds,
                timeline_source=replay_sample.timeline_source,
                received_at=replay_sample.received_at,
                phone_timestamp_seconds=replay_sample.phone_timestamp_seconds,
                result=match))
        status_counts = {}
        reason_counts = {}
        direction_counts = {}
        status_duration_seconds = {}
        for match in matches:
            status = match['status']
            status_counts[status] = status_counts.get(status, 0) + 1
            direction = match['direction']
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
            for reason in match['reason_codes']:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        for index in range(1, len(replay.samples)):
            delta = max(0.0, replay.samples[index].timeline_seconds -
                        replay.samples[index - 1].timeline_seconds)
            status = matches[index - 1]['status']
            status_duration_seconds[status] = status_duration_seconds.get(status, 0.0) + delta
        gaps = [max(0.0, replay.samples[index].timeline_seconds -
                    replay.samples[index - 1].timeline_seconds)
                for index in range(1, len(replay.samples))]
        timeline_source_counts = {}
        for sample in replay.samples:
            timeline_source_counts[sample.timeline_source] = (
                timeline_source_counts.get(sample.timeline_source, 0) + 1)
        cross_tracks = [match['cross_track_m'] for match in matches if match['cross_track_m'] is not None]
        accuracy_values = [sample.position.gps_accuracy_m for sample in replay.samples
                           if sample.position.gps_accuracy_m is not None]
        transition_events = []
        previous_status = None
        for sample, match in zip(replay.samples, matches):
            status = match['status']
            if previous_status == 'MATCHED' and status != 'MATCHED':
                transition_events.append(dict(event_type='MATCH_LOST', sample_ref=sample.sample_ref,
                                              timeline_seconds=sample.timeline_seconds,
                                              from_status=previous_status, to_status=status,
                                              reason_codes=match['reason_codes']))
            elif previous_status not in (None, 'MATCHED') and status == 'MATCHED':
                transition_events.append(dict(event_type='MATCH_RECOVERED', sample_ref=sample.sample_ref,
                                              timeline_seconds=sample.timeline_seconds,
                                              from_status=previous_status, to_status=status,
                                              reason_codes=match['reason_codes']))
            previous_status = status
        crossing_events = [dict(event_type='STOP_LINE_CROSSING', **asdict(event))
                           for event in replay.detector.events]
        confirmed = sum(event['status'] == 'CONFIRMED' for event in crossing_events)
        unconfirmed = sum(event['status'] == 'UNCONFIRMED' for event in crossing_events)
        known_directions = [match['direction'] for match in matches
                            if match['direction'] in ('FORWARD', 'REVERSE')]
        direction_changes = sum(current != previous for previous, current in
                                zip(known_directions, known_directions[1:]))
        source_dir = self.logger._directory(run_id)
        source_hash = hashlib.sha256((source_dir / 'raw.csv').read_bytes()).hexdigest()
        attestation_path = self.logger.root.parent / 'derived' / 'field-review' / run_id / 'attestation.json'
        attestation = None
        if attestation_path.exists():
            candidate = json.loads(attestation_path.read_text(encoding='utf-8'))
            if (candidate.get('run_id') == run_id and candidate.get('source_raw_sha256') == source_hash
                    and route is not None and candidate.get('geometry_hash') == route.geometry_hash):
                attestation = candidate
        observation_review = review_observations(raw_rows, replay, route, attestation)
        report = dict(schema_version=2, run_id=run_id, sample_count=len(replay.samples),
                      duration_seconds=replay.duration, status_counts=status_counts,
                      status_duration_seconds=status_duration_seconds,
                      reason_counts=reason_counts, direction_counts=direction_counts,
                      timeline_source_counts=timeline_source_counts,
                      gaps=dict(over_2_seconds=sum(value > 2 for value in gaps),
                                maximum_seconds=max(gaps, default=0.0)),
                      gps_accuracy_m=dict(minimum=min(accuracy_values, default=None),
                                          mean=(sum(accuracy_values) / len(accuracy_values)
                                                if accuracy_values else None),
                                          p95=_percentile(accuracy_values, .95),
                                          maximum=max(accuracy_values, default=None)),
                      maximum_cross_track_m=max(cross_tracks, default=None),
                      mean_cross_track_m=(sum(cross_tracks) / len(cross_tracks) if cross_tracks else None),
                      p95_cross_track_m=_percentile(cross_tracks, .95),
                      direction_change_count=direction_changes,
                      route_observation_count=len(route_observations),
                      route_observations=route_observations,
                      observation_review=observation_review,
                      synthetic_observation_count=synthetic_observation_count,
                      crossing_count=len(crossing_events), confirmed_crossing_count=confirmed,
                      unconfirmed_crossing_count=unconfirmed,
                      crossing_events=crossing_events,
                      match_transition_count=len(transition_events),
                      match_transition_events=transition_events,
                      route=None if route is None else dict(route_id=route.route_id,
                          geometry_version=route.geometry_version, geometry_hash=route.geometry_hash),
                      source_raw_sha256=source_hash,
                      note='Matcher score is diagnostic and is not a calibrated probability.')
        if not write:
            return report
        analysis_id = uuid4().hex
        directory = self.root / run_id / analysis_id
        directory.mkdir(parents=True, exist_ok=False)
        match_bytes = b''.join(_json_bytes(value) for value in match_rows)
        event_bytes = b''.join(_json_bytes(value) for value in
                               (transition_events + crossing_events + route_observations))
        report_bytes = _json_bytes(report)
        (directory / 'matches.jsonl').write_bytes(match_bytes)
        (directory / 'events.jsonl').write_bytes(event_bytes)
        (directory / 'report.json').write_bytes(report_bytes)
        manifest = dict(schema_version=2, analysis_id=analysis_id, run_id=run_id,
                        created_at=datetime.now(timezone.utc).isoformat(),
                        source_raw_sha256=source_hash,
                        route=report['route'], algorithm_version=replay.match_result.algorithm_version,
                        matcher_config=replay.match_result.config,
                        timeline_method='DEVICE_MONOTONIC_WITH_EXPLICIT_BOUNDARIES',
                        completed=True,
                        sha256={name: hashlib.sha256(content).hexdigest() for name, content in
                                (('matches.jsonl', match_bytes), ('events.jsonl', event_bytes),
                                 ('report.json', report_bytes))})
        (directory / 'manifest.json').write_bytes(_json_bytes(manifest))
        return dict(report, analysis_id=analysis_id)


class MappingAnalysisJobs:
    """Run immutable full-log analyses away from the HTTP request thread."""

    def __init__(self, analysis):
        self.analysis = analysis
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='mapping-analysis')
        self._lock = threading.Lock()
        self._jobs = {}

    def start(self, run_id, route, *, write=False):
        # Validate the identifier before returning an asynchronous job.
        self.analysis.logger._directory(run_id)
        if not isinstance(write, bool):
            raise ValueError('write must be boolean')
        job_id = uuid4().hex
        route_snapshot = route
        with self._lock:
            self._jobs[job_id] = dict(job_id=job_id, status='RUNNING', result=None, error=None)
        self._executor.submit(self._run, job_id, run_id, route_snapshot, write)
        return self.status(job_id)

    def _run(self, job_id, run_id, route, write):
        try:
            result = self.analysis.analyze(run_id, route, write=write)
        except Exception as error:  # surfaced as local diagnostic state
            with self._lock:
                self._jobs[job_id] = dict(job_id=job_id, status='FAILED', result=None,
                                          error=str(error))
        else:
            with self._lock:
                self._jobs[job_id] = dict(job_id=job_id, status='COMPLETED', result=result,
                                          error=None)

    def status(self, job_id):
        if not isinstance(job_id, str) or len(job_id) != 32 or any(
                character not in '0123456789abcdef' for character in job_id):
            raise ValueError('Invalid mapping analysis job ID')
        with self._lock:
            value = self._jobs.get(job_id)
            if value is None:
                raise ValueError('Mapping analysis job not found')
            return dict(value)

    def close(self):
        self._executor.shutdown(wait=False, cancel_futures=True)
