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
        from greenwave.school_admin.service import Administration
        self.admin = Administration(self.policy)
        self.reads = Reads(self.policy)
        self.files = Files(self.policy)
        self.contexts = Contexts(self.policy, self.files)
        self.recorder = Recording(self.policy)
        from greenwave.school_navigation.devices import Devices
        self.devices=Devices(self.recorder);self.recorder.devices=self.devices
        from greenwave.school_navigation.cv import Vision
        self.vision=Vision(self.recorder,self.files);self.recorder.vision=self.vision
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
        if route in {'/device/pair','/device/session','/device/position'}:
            if query_string:raise AuthError(400,'BAD_REQUEST')
            if len(handler.headers.get_all('Authorization',[]))>1:raise AuthError(400,'BAD_REQUEST')
            bearer=handler.headers.get('Authorization','')
            if route=='/device/pair' and method=='POST':return True,self.devices.pair(handler.resource_body(),handler.client_ip),200
            if route=='/device/session' and method=='GET':return True,self.devices.session(bearer),200
            if route=='/device/position' and method=='POST':return True,self.devices.ingest(bearer,handler.resource_body()),200
            return False,None,None
        routes = [
            ('POST',r'/trips/([^/]+)/cv/captures',set(),'cv_start'),
            ('POST',r'/trips/([^/]+)/cv/captures/([^/]+)/stop',set(),'cv_stop'),
            ('GET',r'/trips/([^/]+)/cv/captures/([^/]+)/frames/([^/]+)',set(),'cv_frame'),
            ('POST',r'/trips/([^/]+)/cv/captures/([^/]+)/reviews',set(),'cv_review'),
            ('POST',r'/trips/([^/]+)/cv/captures/([^/]+)/associations',set(),'cv_associate'),
            ('DELETE',r'/trips/([^/]+)/cv/captures/([^/]+)/associations/([^/]+)',set(),'cv_unassociate'),
            ('GET',r'/cv/sources',set(),'cv_sources'),
            ('GET',r'/maps/([^/]+)',set(),'map'),
            ('GET',r'/devices',{'status','limit','cursor'},'devices'),
            ('PATCH',r'/devices/([^/]+)',set(),'device_edit'),
            ('DELETE',r'/devices/([^/]+)',set(),'device_revoke'),
            ('POST',r'/pairing-challenges',set(),'challenge'),
            ('DELETE',r'/pairing-challenges/([^/]+)',set(),'challenge_revoke'),
            ('GET',r'/admin/users',{'email','role','status','limit','cursor'},'admin_users'),
            ('PATCH',r'/admin/users/([^/]+)',set(),'admin_change'),
            ('GET',r'/admin/audit',{'actor','action','from','to','limit','cursor'},'admin_audit'),
            ('POST',r'/config/versions',set(),'config_create'),
            ('PATCH',r'/config/versions/([^/]+)',set(),'config_edit'),
            ('POST',r'/config/versions/([^/]+)/publish',set(),'config_publish'),
            ('DELETE',r'/config/versions/([^/]+)',set(),'config_archive'),
            ('POST',r'/trips',set(),'create'),
            ('PATCH',r'/trips/([^/]+)',set(),'edit'),
            ('DELETE',r'/trips/([^/]+)',set(),'archive'),
            ('POST',r'/trips/([^/]+)/observations',set(),'observe'),
            ('POST',r'/observations/([^/]+)/corrections',set(),'correct'),
            ('POST',r'/trips/([^/]+)/share',set(),'share'),
            ('DELETE',r'/trips/([^/]+)/share',set(),'revoke'),
            ('POST',r'/navigation',set(),'nav_start'),
            ('GET',r'/navigation',set(),'nav_active'),
            ('GET',r'/navigation/([^/]+)',set(),'nav_read'),
            ('PATCH',r'/navigation/([^/]+)/simulation',set(),'nav_configure'),
            ('POST',r'/navigation/([^/]+)/control',set(),'nav_finish'),
            ('GET', r'/trips', {'from','to','route_id','status','archived','scope','limit','cursor','sort'}, 'trips'),
            ('GET', r'/trips/([^/]+)', set(), 'trip'),
            ('GET', r'/observations', {'trip_id','scope','from','to','signal_id','state','event_type','route_id','source','valid','limit','cursor','sort'}, 'observations'),
            ('GET', r'/observations/([^/]+)/corrections', {'limit','offset'}, 'corrections'),
            ('GET', r'/trips/([^/]+)/export', set(), 'export'),
            ('HEAD', r'/trips/([^/]+)/export', set(), 'export_check'),
            ('GET', r'/config/versions', {'kind','logical_id','status','limit','offset','cursor'}, 'configs'),
            ('GET', r'/config/versions/([^/]+)', set(), 'config'),
            ('GET',r'/trips/([^/]+)/replay-options',set(),'replay_options'),
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
                if operation=='cv_sources':data={'items':[{'id':name,'type':'CAMERA' if name.startswith('camera:') else 'FILE'} for name in self.vision.sources if not name.startswith('camera:') or self.policy.accounts.config.profile=='real'],'detector_configured':self.vision.model is not None}
                elif operation=='cv_associate':data=self.vision.associate(raw,*args,body)
                elif operation=='cv_unassociate':
                    if body!={}:raise AuthError(422,'VALIDATION')
                    data=self.vision.associate(raw,args[0],args[1],{'track_id':args[2]},True)
                elif operation=='cv_start':data=self.vision.start(raw,args[0],body)
                elif operation=='cv_stop':data=self.vision.stop(raw,*args,body)
                elif operation=='cv_frame':return True,self.vision.frame(raw,*args),200
                elif operation=='cv_review':data=self.vision.review(raw,*args,body,handler.request_id)
                elif operation=='map':
                    from greenwave.school_navigation.maps import bundled_map
                    data=bundled_map(self.policy,raw,args[0])
                elif operation=='devices':data=self.devices.list(raw,q)
                elif operation=='challenge':data=self.devices.challenge(raw,body)
                elif operation=='challenge_revoke':data=self.devices.revoke_challenge(raw,args[0],body)
                elif operation in {'device_edit','device_revoke'}:data=self.devices.write(raw,args[0],body,operation=='device_revoke')
                elif operation=='admin_users':data=self.admin.accounts(raw,q)
                elif operation=='admin_audit':data=self.admin.audit(raw,q)
                elif operation=='admin_change':data=self.admin.account_change(raw,args[0],body,handler.request_id)
                elif operation in {'config_create','config_edit','config_publish','config_archive'}:
                    data=self.admin.config_write(raw,args[0] if args else None,operation[7:],body,handler.request_id)
                elif operation in {'create','edit','archive','observe','correct','share','revoke'}:
                    data=getattr(self.writes,operation)(raw,*args,body,handler.request_id)
                elif operation=='nav_configure':data=self.recorder.simulation(raw,args[0],body)
                elif operation=='nav_finish' and body.get('command') in {'PAUSE','RESUME'}:data=self.recorder.control(raw,args[0],body)
                elif operation in {'nav_start','nav_finish'}:
                    if len(handler.headers.get_all('Idempotency-Key',[]))!=1:raise AuthError(422,'IDEMPOTENCY_KEY_REQUIRED')
                    data=getattr(self.recorder,'start' if operation=='nav_start' else 'finish')(raw,*args,body,handler.headers['Idempotency-Key'],handler.request_id)
                elif operation=='nav_active':
                    with self.recorder.lock:
                        active=next((v for v in self.recorder.contexts.values() if v['session_id']==row['id'] and v['credential']==row['secret_hash'] and v.get('drive') and not v['drive'].closed),None)
                        data=None if active is None else self.recorder.navigation(raw,active['id'])
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
                elif operation=='replay_options':data=self.contexts.replay_options(raw,args[0])
                elif operation.startswith('replay_') or operation in {'job_create','job_cancel','job_read'}:
                    if operation in {'replay_close','job_cancel'} and body != {}: raise AuthError(422, 'VALIDATION')
                    fn = getattr(self.contexts, operation)
                    data = fn(raw, *args, body) if operation in {'replay_create','replay_control','job_create'} else fn(raw, *args)
                elif operation == 'reports': data = self.contexts.reports(raw, args[0], q)
                elif operation == 'report': data = self.contexts.report(raw, *args)
                elif operation == 'captures': data = self.files.captures(raw, args[0], q)
                elif operation == 'capture': data = self.vision.status(raw,*args)
                elif operation == 'events': data = self.vision.events(raw, *args, q)
                elif operation == 'media':
                    segment = integer({'segment': args[2]}, 'segment', maximum=10000)
                    if len(handler.headers.get_all('Range', [])) > 1: raise AuthError(416, 'RANGE_INVALID')
                    return True, self.files.media(raw, args[0], args[1], segment, handler.headers.get('Range')), 200
                if operation=='observe' and data['journaling_state']!='APPLIED':return True,data,202
                return True, data, 201 if operation in {'cv_start','cv_review','challenge','config_create','replay_create','create','correct','observe','share','nav_start'} else 202 if operation == 'job_create' else 204 if operation in {'cv_unassociate','device_revoke','challenge_revoke','config_archive','replay_close','job_cancel','archive','revoke'} else 200
        return False, None, None
