"""Explicit school namespace; no delegation to the legacy HTTP handler."""
import re
import threading
from greenwave.school_accounts.errors import AuthError
from .policy import Policy
from .reads import Reads, query, trip_dto, integer
from .files import Files
from .contexts import Contexts


class ResourceAPI:
    def __init__(self, accounts):
        self.policy = Policy(accounts)
        self.reads = Reads(self.policy)
        self.files = Files(self.policy)
        self.contexts = Contexts(self.policy, self.files)
        self.export_lock = threading.Lock()
        self.exports = set()

    def close(self): self.contexts.close()

    def export(self, raw, tid):
        _, actor, _, _ = self.policy.trip(raw, tid, True, closed=True)
        with self.export_lock:
            if actor.user_id in self.exports: raise AuthError(409, 'EXPORT_BUSY')
            self.exports.add(actor.user_id)
        def release():
            with self.export_lock: self.exports.discard(actor.user_id)
        try: return self.files.export(raw, tid, release)
        except BaseException: release(); raise

    def dispatch(self, handler, route, query_string, raw):
        method = handler.command
        routes = [
            ('GET', r'/trips', {'from','to','route_id','status','archived','scope','limit','offset'}, 'trips'),
            ('GET', r'/trips/([^/]+)', set(), 'trip'),
            ('GET', r'/observations', {'trip_id','scope','from','to','signal_id','state','event_type','limit','offset'}, 'observations'),
            ('GET', r'/observations/([^/]+)/corrections', {'limit','offset'}, 'corrections'),
            ('GET', r'/trips/([^/]+)/export', set(), 'export'),
            ('GET', r'/config/versions', {'kind','logical_id','status','limit','offset'}, 'configs'),
            ('GET', r'/config/versions/([^/]+)', set(), 'config'),
            ('POST', r'/trips/([^/]+)/replays', set(), 'replay_create'),
            ('GET', r'/replays/([^/]+)', set(), 'replay_read'),
            ('POST', r'/replays/([^/]+)/control', set(), 'replay_control'),
            ('DELETE', r'/replays/([^/]+)', set(), 'replay_close'),
            ('POST', r'/trips/([^/]+)/analysis-jobs', set(), 'job_create'),
            ('GET', r'/analysis-jobs/([^/]+)', set(), 'job_read'),
            ('DELETE', r'/analysis-jobs/([^/]+)', set(), 'job_cancel'),
            ('GET', r'/trips/([^/]+)/reports', {'limit','offset'}, 'reports'),
            ('GET', r'/trips/([^/]+)/reports/([^/]+)', set(), 'report'),
            ('GET', r'/trips/([^/]+)/cv/captures', {'limit','offset'}, 'captures'),
            ('GET', r'/trips/([^/]+)/cv/captures/([^/]+)', set(), 'capture'),
            ('GET', r'/trips/([^/]+)/cv/captures/([^/]+)/events', {'limit','offset'}, 'events'),
            ('GET', r'/trips/([^/]+)/cv/captures/([^/]+)/media/([^/]+)', set(), 'media')]
        for expected, pattern, allowed, operation in routes:
            match = re.fullmatch(pattern, route)
            if method == expected and match:
                row, _ = self.policy.session(raw)
                q = query(query_string, allowed)
                args = match.groups()
                body = None
                if method != 'GET':
                    self.policy.accounts.sessions.check_csrf(raw, row, handler.headers.get('X-CSRF-Token',''))
                    body = handler.resource_body()
                if operation == 'trips': data = self.reads.trips(raw, q)
                elif operation == 'trip':
                    _, _, trip, own = self.policy.trip(raw, args[0]); data = trip_dto(trip, own)
                elif operation == 'observations': data = self.reads.observations(raw, q)
                elif operation == 'corrections': data = self.reads.corrections(raw, args[0], q)
                elif operation == 'configs': data = self.reads.configs(raw, q)
                elif operation == 'config': data = self.reads.configs(raw, q, args[0])
                elif operation == 'export': return True, self.export(raw, args[0]), 200
                elif operation.startswith('replay_') or operation in {'job_create','job_cancel','job_read'}:
                    if operation in {'replay_close','job_cancel'} and body != {}: raise AuthError(422, 'VALIDATION')
                    fn = getattr(self.contexts, operation)
                    data = fn(raw, *args, body) if operation in {'replay_create','replay_control','job_create'} else fn(raw, *args)
                elif operation == 'reports': data = self.contexts.reports(raw, args[0], q)
                elif operation == 'report': data = self.contexts.report(raw, *args)
                elif operation == 'captures': data = self.files.captures(raw, args[0], q)
                elif operation == 'capture': data = self.files.capture_dto(self.files.capture(raw, *args)[2])
                elif operation == 'events': data = self.files.events(raw, *args, q)
                elif operation == 'media':
                    segment = integer({'segment': args[2]}, 'segment', maximum=10000)
                    if len(handler.headers.get_all('Range', [])) > 1: raise AuthError(416, 'RANGE_INVALID')
                    return True, self.files.media(raw, args[0], args[1], segment, handler.headers.get('Range')), 200
                return True, data, 201 if operation == 'replay_create' else 202 if operation == 'job_create' else 204 if operation in {'replay_close','job_cancel'} else 200
        return False, None, None
