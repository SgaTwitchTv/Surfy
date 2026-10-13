"""Ephemeral per-session replay and bounded jobs, reauthorized at every boundary."""
import concurrent.futures
import hashlib
import json
import math
import threading
import time
from greenwave.analysis import RunAnalysis
from greenwave.gps_replay import GPSReplaySession
from greenwave.school_accounts.errors import AuthError
from .policy import resource_id


class Contexts:
    def __init__(self, policy, files):
        self.policy, self.files = policy, files
        self.repo = policy.repo
        self.lock = threading.RLock()
        self.replays, self.jobs = {}, {}
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='school-analysis')

    def close(self):
        with self.lock:
            for job in self.jobs.values(): job['cancelled'] = True
            self.replays.clear()
        self.pool.shutdown(wait=True, cancel_futures=True)

    def purge(self):
        now = self.repo.clock()
        for hid, context in list(self.replays.items()):
            if context['expiry'] <= now: del self.replays[hid]
        for jid, job in list(self.jobs.items()):
            if job['expiry'] <= now:
                job['cancelled'] = True
                del self.jobs[jid]

    def replay_create(self, raw, tid, body):
        if body != {'mode': 'GPS'}: raise AuthError(422, 'REPLAY_MODE_UNAVAILABLE')
        row, _, _, basis = self.policy.basis_trip(raw, tid, closed=True)
        trip, logger, _, _ = self.files.run(raw, tid, basis=basis)
        replay = GPSReplaySession(logger)
        try: replay.load(trip['run_id'])
        except ValueError: raise AuthError(409, 'GPS_REPLAY_UNAVAILABLE') from None
        self.policy.bound_trip(raw, basis)
        with self.lock:
            self.purge()
            for hid, context in list(self.replays.items()):
                if context['session_id'] == row['id']: del self.replays[hid]
            if len(self.replays) >= 64: raise AuthError(503, 'REPLAY_BUSY')
            hid = self.repo.new_id()
            self.replays[hid] = {'session_id': row['id'], 'credential': row['secret_hash'], 'trip_id': tid, 'authorization': basis,
                'expiry': self.repo.clock()+1800000, 'replay': replay, 'tick': time.monotonic()}
            return self.replay_read(raw, hid)

    def replay_context(self, raw, hid):
        row, _ = self.policy.session(raw)
        self.purge()
        context = self.replays.get(resource_id(hid))
        if not context or context['session_id'] != row['id'] or context['credential'] != row['secret_hash']:
            raise AuthError(404, 'NOT_FOUND')
        try: self.policy.bound_trip(raw, context['authorization'])
        except AuthError:
            del self.replays[hid]
            raise AuthError(404, 'NOT_FOUND') from None
        return context

    def replay_read(self, raw, hid):
        with self.lock:
            context = self.replay_context(raw, hid)
            # GET does not advance/mutate the playback timeline. Controls are explicit POST.
            state = context['replay'].state()
            sample = state['sample']
            position = None if sample is None else {k: sample['position'][k] for k in ('latitude', 'longitude', 'speed_mps')}
            return {'id': hid, 'trip_id': context['trip_id'], 'timeline_seconds': state['timeline_seconds'],
                    'duration_seconds': state['duration'], 'sample_count': state['sample_count'],
                    'running': state['running'], 'rate': state['rate'], 'position': position,
                    'diagnostic_only': True, 'live_recommendation': None}

    def replay_control(self, raw, hid, body):
        command = body.get('command')
        if command not in {'PLAY', 'PAUSE', 'SEEK', 'RATE'}: raise AuthError(422, 'VALIDATION')
        if set(body) != ({'command', 'value'} if command in {'SEEK', 'RATE'} else {'command'}): raise AuthError(422, 'VALIDATION')
        value = body.get('value')
        if command in {'SEEK', 'RATE'} and (type(value) not in {int, float} or not math.isfinite(value)):
            raise AuthError(422, 'VALIDATION')
        # Existing M8 supports rates 1,2,5. Rate10 remains unavailable until stage9.
        if command == 'RATE' and value not in {1, 2, 5}: raise AuthError(422, 'VALIDATION')
        with self.lock:
            context = self.replay_context(raw, hid)
            now = time.monotonic()
            context['replay'].advance(min(30, max(0, now-context['tick'])))
            context['tick'] = now
            try: context['replay'].command(command.lower(), value)
            except ValueError: raise AuthError(422, 'VALIDATION') from None
            return self.replay_read(raw, hid)

    def replay_close(self, raw, hid):
        with self.lock:
            self.replay_context(raw, hid); del self.replays[hid]

    @staticmethod
    def job_dto(job):
        return {k: job[k] for k in ('id', 'trip_id', 'type', 'status', 'report_id')}

    def invalidate_job_execution(self, job):
        """Invalid execution is permanent; completed results remain completed."""
        with self.lock:
            job['authorization_invalid'] = True
            job['cancelled'] = True
            if job['status'] in {'QUEUED', 'RUNNING'}:
                job['status'] = 'CANCELLED'

    def execution_trip(self, c, job):
        """Original actor/session/credential/grant, never the managing owner."""
        if job['authorization_invalid']: raise AuthError(404, 'NOT_FOUND')
        trip = c.execute('SELECT * FROM trips WHERE id=?', (job['trip_id'],)).fetchone()
        if trip is None: raise AuthError(404, 'NOT_FOUND')
        self.policy.check_basis(c, job['authorization'], trip)
        if trip['status'] != 'COMPLETE' or trip['archived_at'] is not None:
            raise AuthError(404, 'NOT_FOUND')
        session = c.execute('SELECT s.*,u.status,u.security_version AS current_version FROM browser_sessions s JOIN users u ON u.id=s.user_id WHERE s.id=? AND s.user_id=? AND s.secret_hash=?',
                            (job['session_id'], job['actor_id'], job['credential'])).fetchone()
        now = self.repo.clock()
        if (session is None or session['status'] != 'ACTIVE' or session['revoked_at'] is not None
                or session['security_version'] != session['current_version']
                or session['absolute_expiry'] <= now or session['last_activity_at'] + 1800000 <= now):
            raise AuthError(404, 'NOT_FOUND')
        return dict(trip)

    def authorize_job_execution(self, raw, job):
        row, actor = self.policy.session(raw)
        if (actor.user_id != job['actor_id'] or row['id'] != job['session_id']
                or row['secret_hash'] != job['credential']):
            raise AuthError(404, 'NOT_FOUND')
        try:
            with self.repo.database.transaction(False) as c:
                return self.execution_trip(c, job)
        except AuthError:
            self.invalidate_job_execution(job)
            raise

    def authorize_job_management(self, raw, job):
        row, actor = self.policy.session(raw)
        with self.repo.database.transaction(False) as c:
            trip = c.execute('SELECT * FROM trips WHERE id=?', (job['trip_id'],)).fetchone()
            if trip is None: raise AuthError(404, 'NOT_FOUND')
            # Ownership is independent of closed/archive/share/execution flags.
            if trip['owner_id'] == actor.user_id:
                try: self.execution_trip(c, job)
                except AuthError: self.invalidate_job_execution(job)
                return dict(trip)
        # Nonowners retain the original requester/session/grant policy.
        return self.authorize_job_execution(raw, job)

    def job_create(self, raw, tid, body):
        if body != {'type': 'GPS_QUALITY'}: raise AuthError(422, 'ANALYSIS_TYPE_UNAVAILABLE')
        row, actor, trip, basis = self.policy.basis_trip(raw, tid, closed=True)
        # Check complete manifest before allocating a job; recheck in the worker.
        self.files.run(raw, tid, basis=basis)
        with self.lock:
            self.purge()
            pending = [j for j in self.jobs.values() if j['status'] in {'QUEUED', 'RUNNING'}]
            if any(j['actor_id'] == actor.user_id and j['trip_id'] == tid for j in pending): raise AuthError(409, 'JOB_EXISTS')
            if len(pending) >= 22 or len(self.jobs) >= 1000: raise AuthError(503, 'ANALYSIS_BUSY')
            jid = self.repo.new_id()
            job = {'id': jid, 'trip_id': tid, 'actor_id': actor.user_id, 'session_id': row['id'],
                   'credential': row['secret_hash'], 'authorization': basis, 'authorization_invalid': False, 'type': 'GPS_QUALITY', 'status': 'QUEUED',
                   'report_id': None, 'cancelled': False, 'expiry': self.repo.clock()+1800000}
            self.jobs[jid] = job
            self.pool.submit(self.execute, raw, job)
            return self.job_dto(job)

    def execute(self, raw, job):
        try:
            with self.lock:
                if job['cancelled']: job['status'] = 'CANCELLED'; return
                job['status'] = 'RUNNING'
            self.authorize_job_execution(raw, job)
            trip, logger, _, _ = self.files.run(raw, job['trip_id'], basis=job['authorization'])
            self.authorize_job_execution(raw, job)
            analysis = RunAnalysis(logger).analyze(trip['run_id'])
            self.authorize_job_execution(raw, job)
            with self.lock:
                if job['cancelled']: job['status'] = 'CANCELLED'; return
                # Serialize the last session/grant check and manifest publication
                # against revoke/archive/security changes using BEGIN IMMEDIATE.
                with self.repo.database.transaction() as c:
                    self.execution_trip(c, job)
                    current, _, trip, _ = self.policy.bound_trip(raw, job['authorization'], connection=c)
                    if current['id'] != job['session_id'] or current['secret_hash'] != job['credential']:
                        raise AuthError(404, 'NOT_FOUND')
                    rid = self.repo.new_id()
                    report = {'id': rid, 'trip_id': trip['id'], 'type': job['type'],
                              'created_at': self.repo.clock(), 'source_raw_sha256': trip['raw_hash'],
                              'diagnostic_only': True, 'metrics': analysis['gps_quality']}
                    root = self.files.storage._safe(self.files.storage.derived(trip['owner_id'], trip['id']) / rid)
                    root.mkdir(parents=True, exist_ok=False)
                    content = json.dumps(report, allow_nan=False, sort_keys=True).encode()
                    (root / 'report.json').write_bytes(content)
                    manifest = {'id': rid, 'trip_id': trip['id'], 'source_raw_sha256': trip['raw_hash'],
                                'sha256': hashlib.sha256(content).hexdigest()}
                    (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                    job['report_id'], job['status'] = rid, 'COMPLETE'
        except AuthError:
            with self.lock: job['status'] = 'CANCELLED'
        except Exception:
            # No raw paths, SQL, exception details, GPS or credentials are exposed.
            with self.lock: job['status'] = 'FAILED'

    def job_read(self, raw, jid):
        self.policy.session(raw)
        with self.lock:
            self.purge(); job = self.jobs.get(resource_id(jid))
            if not job: raise AuthError(404, 'NOT_FOUND')
            self.authorize_job_management(raw, job)
            return self.job_dto(job)

    def job_cancel(self, raw, jid):
        with self.lock:
            self.job_read(raw, jid)
            job = self.jobs[jid]; job['cancelled'] = True
            if job['status'] in {'QUEUED', 'RUNNING'}: job['status'] = 'CANCELLED'

    def report(self, raw, tid, rid):
        _, _, trip, _ = self.policy.trip(raw, tid, closed=True)
        root = self.files.storage._safe(self.files.storage.derived(trip['owner_id'], tid) / resource_id(rid))
        if not (root / 'manifest.json').is_file(): raise AuthError(404, 'NOT_FOUND')
        manifest = self.files.json(root / 'manifest.json')
        report = self.files.json(root / 'report.json')
        validate = lambda: self.policy.trip(raw, tid, closed=True)
        if (manifest.get('id') != rid or manifest.get('trip_id') != tid or manifest.get('source_raw_sha256') != trip['raw_hash']
                or manifest.get('sha256') != self.files.digest(root / 'report.json', validate, 1048576)
                or report.get('id') != rid or report.get('trip_id') != tid or report.get('source_raw_sha256') != trip['raw_hash']):
            raise AuthError(409, 'ARTIFACT_INVALID')
        # Reports are generated only by this adapter. Fixed DTO, no manifest paths.
        return {k: report[k] for k in ('id', 'trip_id', 'type', 'created_at', 'diagnostic_only', 'metrics')}

    def reports(self, raw, tid, q):
        import re
        from .reads import pagination
        _, _, trip, _ = self.policy.trip(raw, tid, closed=True)
        root = self.files.storage.derived(trip['owner_id'], tid)
        limit, offset = pagination(q)
        ids = []
        if root.exists():
            for child in root.iterdir():
                if re.fullmatch('[0-9a-f]{32}', child.name): ids.append(child.name)
                if len(ids) > 1000: raise AuthError(409, 'REPORT_INDEX_REQUIRED')
        return {'items': [self.report(raw, tid, rid) for rid in sorted(ids)[offset:offset+limit]],
                'page': {'limit': limit, 'offset': offset}}
