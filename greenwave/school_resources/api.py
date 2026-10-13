"""Explicit school namespace; no delegation to the legacy HTTP handler."""
import re
import threading
from greenwave.school_accounts.errors import AuthError
from .policy import Policy
from .reads import Reads, query, trip_dto, integer
from .files import Files
from .contexts import Contexts
from greenwave.school_records.lists import Lists
from greenwave.school_records.recording import Recording
from greenwave.school_records.writes import Writes


class ResourceAPI:
    def __init__(self, accounts):
        self.policy = Policy(accounts)
        self.reads = Reads(self.policy)
        self.files = Files(self.policy)
        self.contexts = Contexts(self.policy, self.files)
        self.recorder = Recording(self.policy)
        self.writes = Writes(self.policy,self.contexts,self.recorder)
        self.lists = Lists(self.policy,accounts.config.csrf_key)
        self.export_lock = threading.Lock()
        self.exports = set()

    def close(self):
        self.recorder.close()
        self.contexts.close()

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
            ('POST',r'/trips',set(),'create'),
            ('PATCH',r'/trips/([^/]+)',set(),'edit'),
            ('DELETE',r'/trips/([^/]+)',set(),'archive'),
            ('POST',r'/trips/([^/]+)/observations',set(),'observe'),
            ('POST',r'/observations/([^/]+)/corrections',set(),'correct'),
            ('POST',r'/trips/([^/]+)/share',set(),'share'),
            ('DELETE',r'/trips/([^/]+)/share',set(),'revoke'),
            ('POST',r'/navigation',set(),'nav_start'),
            ('GET',r'/navigation/([^/]+)',set(),'nav_read'),
            ('POST',r'/navigation/([^/]+)/control',set(),'nav_finish'),
            ('GET', r'/trips', {'from','to','route_id','status','archived','scope','limit','cursor','sort'}, 'trips'),
            ('GET', r'/trips/([^/]+)', set(), 'trip'),
            ('GET', r'/observations', {'trip_id','scope','from','to','signal_id','state','event_type','route_id','source','valid','limit','cursor','sort'}, 'observations'),
            ('GET', r'/observations/([^/]+)/corrections', {'limit','offset'}, 'corrections'),
            ('GET', r'/trips/([^/]+)/export', set(), 'export'),
            ('HEAD', r'/trips/([^/]+)/export', set(), 'export_check'),
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
                if method not in {'GET','HEAD'}:
                    self.policy.accounts.sessions.check_csrf(raw, row, handler.headers.get('X-CSRF-Token',''))
                    body = handler.resource_body()
                if operation in {'create','edit','archive','observe','correct','share','revoke'}:
                    data=getattr(self.writes,operation)(raw,*args,body,handler.request_id)
                elif operation in {'nav_start','nav_finish'}:
                    if len(handler.headers.get_all('Idempotency-Key',[]))!=1:raise AuthError(422,'IDEMPOTENCY_KEY_REQUIRED')
                    data=getattr(self.recorder,'start' if operation=='nav_start' else 'finish')(raw,*args,body,handler.headers['Idempotency-Key'],handler.request_id)
                elif operation=='nav_read':data=self.recorder.navigation(raw,*args)
                elif operation == 'trips': data = self.lists.read(raw,q,'trips')
                elif operation == 'trip':
                    _, _, trip, own = self.policy.trip(raw, args[0]); data = trip_dto(trip, own)
                    if own:
                        with self.policy.repo.database.connection() as c:
                            share=c.execute('SELECT id,permission,created_at FROM trip_shares WHERE trip_id=? AND revoked_at IS NULL',(trip['id'],)).fetchone()
                        data['share']=None if share is None else dict(share)
                elif operation == 'observations': data = self.lists.read(raw,q,'observations')
                elif operation == 'corrections': data = self.reads.corrections(raw, args[0], q)
                elif operation == 'configs': data = self.reads.configs(raw, q)
                elif operation == 'config': data = self.reads.configs(raw, q, args[0])
                elif operation == 'export_check':self.files.run(raw,args[0],True);data=None
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
                if operation=='observe' and data['journaling_state']!='APPLIED':return True,data,202
                return True, data, 201 if operation in {'replay_create','create','correct','observe','share','nav_start'} else 202 if operation == 'job_create' else 204 if operation in {'replay_close','job_cancel','archive','revoke'} else 200
        return False, None, None
