from contextlib import contextmanager
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.validation import text,email,observation,request_hash,operation_key
from greenwave.school_data.errors import Conflict,Denied,Invalid
from greenwave.school_resources.policy import resource_id
from greenwave.school_data.storage import identifier
from greenwave.school_resources.reads import trip_dto,pick,OBS_FIELDS


def fields(body,required,optional=()):
    if not isinstance(body,dict) or not set(required)<=set(body) or set(body)-set(required)-set(optional):raise AuthError(422,'VALIDATION')


def revision(value):
    if type(value) is not int or not 0<=value<=2147483647:raise AuthError(422,'VALIDATION')
    return value


def observation_dto(repo,c,row):
    row=dict(row);row['effective'],row['correction_revision']=repo.effective(c,row)
    return {**pick(row,OBS_FIELDS),'historical':bool(row['historical']),
            'original':pick(row,('state','event_type','server_received_at','measured_at')),
            'journaling_state':row['journaling_state']}


class Writes:
    def __init__(self,policy,contexts,recorder):self.policy,self.repo,self.contexts,self.recorder=policy,policy.repo,contexts,recorder
    @contextmanager
    def unit(self,raw,request_id):
        with self.repo.atomic(request_id) as (repo,c):
            row,actor=self.policy.accounts.sessions.lookup(raw,connection=c)
            yield repo,c,row,actor

    def create(self,raw,body,request_id):
        fields(body,{'title','mode'},{'note','route_version_id'})
        if body['mode']=='LIVE' and not body.get('route_version_id'):raise AuthError(422,'VALIDATION')
        with self.unit(raw,request_id) as (repo,c,_,actor):
            return trip_dto(repo.create_trip(actor,body['title'],body.get('note',''),body['mode'],body.get('route_version_id')),True)

    def edit(self,raw,tid,body,request_id):
        fields(body,{'expected_revision'},{'title','note'});revision(body['expected_revision'])
        if not set(body)&{'title','note'}:raise AuthError(422,'VALIDATION')
        with self.unit(raw,request_id) as (repo,c,_,actor):
            old=repo.own_trip(c,actor,resource_id(tid))
            if old['archived_at'] is not None:raise Conflict('Archived trip')
            return trip_dto(repo.edit_trip(actor,tid,body['expected_revision'],title=body.get('title',old['title']),note=body.get('note',old['note'])),True)

    def archive(self,raw,tid,body,request_id):
        fields(body,{'expected_revision','reason'});revision(body['expected_revision']);text(body['reason'],3,500)
        with self.unit(raw,request_id) as (repo,c,_,actor):
            repo.archive_trip(actor,resource_id(tid),body['expected_revision'])
            repo.audit(c,actor,'TRIP_ARCHIVE_REASON','TRIP',tid,body['reason'])
        self.revoke_contexts(tid)

    def share(self,raw,tid,body,request_id):
        fields(body,{'analyst_email'});email(body['analyst_email'])
        _,actor,_,_=self.policy.trip(raw,tid,True)
        self.policy.accounts.limits.take('SHARE_USER',actor.user_id,10,3600000)
        with self.unit(raw,request_id) as (repo,c,_,actor):
            try:sid=repo.share_trip(actor,resource_id(tid),body['analyst_email'])
            except Denied:raise AuthError(422,'RECIPIENT_UNAVAILABLE') from None
            return {'id':sid,'trip_id':tid,'permission':'READ_ANALYZE','created_at':repo.clock()}

    def revoke(self,raw,tid,body,request_id):
        fields(body,{'expected_share_id'});identifier(body['expected_share_id'])
        with self.unit(raw,request_id) as (repo,c,_,actor):repo.revoke_share(actor,resource_id(tid),body['expected_share_id'])
        self.revoke_contexts(tid)

    def revoke_contexts(self,tid):
        # Proactive invalidation; never wait for the analyst's next request.
        with self.contexts.lock:
            with self.repo.database.transaction(False) as c:
                trip=c.execute('SELECT * FROM trips WHERE id=?',(tid,)).fetchone()
                for hid,ctx in list(self.contexts.replays.items()):
                    if ctx['trip_id']==tid:
                        try:
                            self.policy.check_basis(c,ctx['authorization'],trip)
                            if trip['archived_at'] is not None:raise AuthError(404,'NOT_FOUND')
                        except AuthError:del self.contexts.replays[hid]
                for job in self.contexts.jobs.values():
                    if job['trip_id']==tid:
                        try:self.contexts.execution_trip(c,job)
                        except AuthError:self.contexts.invalidate_job_execution(job)

    def signal(self,c,trip,signal):
        text(signal,1,120)
        if trip['route_version_id'] is not None:
            import json
            payload=json.loads(c.execute('SELECT payload FROM config_versions WHERE id=?',(trip['route_version_id'],)).fetchone()[0])
            lines=payload.get('stop_lines',[])
            if signal not in {line.get('stop_line_id',line.get('signal_id')) for line in lines}:raise AuthError(422,'INVALID_SIGNAL')
        elif trip['mode']!='SIMULATION':raise AuthError(422,'INVALID_SIGNAL')

    def observe(self,raw,tid,body,request_id):
        fields(body,{'signal_id','state','event_type','source_event_id'})
        text(body['source_event_id'],1,128)
        observation({'state':body['state'],'event_type':body['event_type'],'valid':True})
        with self.recorder.lock:
            with self.unit(raw,request_id) as (repo,c,session,actor):
                trip=repo.own_trip(c,actor,resource_id(tid));self.signal(c,trip,body['signal_id'])
                existing=c.execute("SELECT * FROM observations WHERE trip_id=? AND source='MANUAL' AND source_event_id=?",(tid,body['source_event_id'])).fetchone()
                historical=bool(existing['historical']) if existing else trip['status'] in {'COMPLETE','INTERRUPTED'}
                if not existing and trip['status'] not in {'RECORDING','COMPLETE','INTERRUPTED'}:raise Conflict('Trip not recording or closed')
                if not historical and not existing:self.recorder.own_context(session,tid)
                row=repo.add_observation(actor,tid,body['signal_id'],body['state'],body['event_type'],body['source_event_id'],historical=historical)
                if historical:
                    c.execute("UPDATE observations SET journaling_state='APPLIED' WHERE id=?",(row['id'],))
                else:
                    key=request_hash({'trip':tid,'source_event_id':body['source_event_id']})
                    old=c.execute("SELECT id FROM recording_operations WHERE actor_id=? AND kind='JOURNAL_OBSERVATION' AND idempotency_key=?",(actor.user_id,key)).fetchone()
                    if not old:
                        c.execute("INSERT INTO recording_operations(id,trip_id,actor_id,kind,idempotency_key,request_hash,state,created_at,parent_session_id,boot_id,observation_id) VALUES(?,?,?,'JOURNAL_OBSERVATION',?,?,'PENDING',?,?,?,?)",(repo.new_id(),tid,actor.user_id,key,request_hash(body),repo.clock(),session['id'],self.recorder.boot,row['id']))
            if not historical:self.recorder.journal(row['id'],request_id)
            with self.repo.database.transaction(False) as c:
                row=c.execute('SELECT * FROM observations WHERE id=?',(row['id'],)).fetchone()
                return observation_dto(self.repo,c,row)

    def correct(self,raw,oid,body,request_id):
        fields(body,{'expected_revision','client_operation_id','changes','reason'})
        revision(body['expected_revision']);operation_key(body['client_operation_id']);text(body['reason'],3,500)
        changes=body['changes']
        if not isinstance(changes,dict) or not changes or set(changes)-{'state','event_type','valid'}:raise AuthError(422,'VALIDATION')
        if 'valid' in changes and type(changes['valid']) is not bool:raise AuthError(422,'VALIDATION')
        with self.unit(raw,request_id) as (repo,c,_,actor):
            row=c.execute('SELECT * FROM observations WHERE id=?',(resource_id(oid),)).fetchone()
            if not row:raise Denied('Observation unavailable')
            repo.own_trip(c,actor,row['trip_id'])
            previous=c.execute('SELECT * FROM observation_corrections WHERE actor_id=? AND client_operation_id=?',(actor.user_id,body['client_operation_id'])).fetchone()
            fingerprint=request_hash({'observation_id':oid,'body':body})
            if previous:
                if previous['request_hash']!=fingerprint:raise Conflict('Changed idempotent correction')
                result=dict(previous)
            else:
                current,_=repo.effective(c,row)
                result=repo.correct_observation(actor,oid,body['expected_revision'],{**current,**changes},body['reason'],body['client_operation_id'],request_fingerprint=fingerprint)
            return {'correction':pick(result,('id','observation_id','actor_id','sequence','server_at','reason')),'observation':observation_dto(repo,c,row)}
