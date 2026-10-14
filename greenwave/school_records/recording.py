"""SQLite intentions plus immutable RunLogger artifacts; no cross-store transaction claim."""
import threading
import json
from greenwave.telemetry import RunLogger
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.errors import Conflict
from greenwave.school_data.validation import request_hash,operation_key
from greenwave.school_resources.policy import resource_id
from greenwave.school_data.storage import identifier
from .raw import Raw,utc
from .writes import fields,revision


class Recording:
    def __init__(self,policy):
        self.policy,self.repo=policy,policy.repo;self.storage=self.repo.database.storage
        self.raw=Raw(self.storage);self.boot=self.repo.new_id();self.lock=threading.RLock();self.contexts={};self.failed_starts={}
        self.fault=lambda boundary:None
        self.recover()
        self.stop=threading.Event();self.thread=threading.Thread(target=self.watch,daemon=True,name='school-recording-revocations');self.thread.start()
        self.policy.accounts.credential_observers.append(self.reconcile_credentials)

    def close(self):
        self.stop.set();self.thread.join(timeout=6)
        try:self.policy.accounts.credential_observers.remove(self.reconcile_credentials)
        except ValueError:pass
        with self.lock:
            self.retry_failed_starts()
            for ctx in list(self.contexts.values()):
                try:self.finish_context(ctx,'shutdown',system=True)
                except Exception:ctx['logger'].close_unfinished()

    def watch(self):
        while not self.stop.wait(.25):
            try:self.reconcile_credentials()
            except Exception:pass  # Retry from durable intentions; never log private artifacts.

    def reconcile_credentials(self):
        with self.lock:
            self.retry_failed_starts()
            for ctx in list(self.contexts.values()):
                try:
                    row,_=self.policy.accounts.sessions.lookup(ctx['raw'],touch=False)
                    if row['id']!=ctx['session_id'] or row['secret_hash']!=ctx['credential']:raise AuthError(401,'UNAUTHORIZED')
                    if ctx.get('device_id'):
                        with self.repo.database.connection() as c:
                            if not c.execute("SELECT 1 FROM devices WHERE id=? AND token_hash=? AND status='ACTIVE' AND revoked_at IS NULL AND expiry>? AND boot_id=? AND security_version=?",(ctx['device_id'],ctx['device_credential'],self.repo.clock(),self.boot,row['security_version'])).fetchone():raise AuthError(401,'UNAUTHORIZED')
                except AuthError:self.finish_context(ctx,'credentials-revoked',system=True);continue
                drive=ctx.get('drive')
                if drive and not drive.closed:
                    try:
                        drive.tick()
                    except Exception:
                        drive.close();self.close_failed_logger(ctx['logger'])
                        if getattr(self,'vision',None):self.vision.close_trip(ctx['trip_id'])
                        self.interrupt(ctx['trip_id'],'ENGINE_FAILED');self.contexts.pop(ctx['id'],None);continue
                if drive and not ctx['logger'].active:
                    with self.repo.database.connection() as c:status=c.execute('SELECT status FROM trips WHERE id=?',(ctx['trip_id'],)).fetchone()[0]
                    # Preserve successful user FINISH handles for identical retries.
                    if status in {'RECORDING','FINALIZING'}:self.finish_context(ctx,'engine-ended',system=True)

    def dto(self,ctx):
        with self.repo.database.connection() as c:t=c.execute('SELECT * FROM trips WHERE id=?',(ctx['trip_id'],)).fetchone()
        return {'id':ctx['id'],'trip_id':ctx['trip_id'],'status':t['status'],'revision':t['revision'],
                'mode':t['mode'],'live_recommendation':None,'diagnostic_only':True,
                **(ctx['drive'].dto() if ctx.get('drive') else {})}

    def own_context(self,session,tid):
        ctx=next((v for v in self.contexts.values() if v['trip_id']==tid),None)
        if not ctx or ctx['session_id']!=session['id'] or ctx['credential']!=session['secret_hash']:raise AuthError(409,'RECORDING_SESSION_REQUIRED')
        return ctx

    def navigation(self,raw,nid):
        row,_=self.policy.session(raw)
        with self.lock:
            ctx=self.contexts.get(resource_id(nid))
            if not ctx or ctx['session_id']!=row['id'] or ctx['credential']!=row['secret_hash']:raise AuthError(404,'NOT_FOUND')
            _,_,trip,_=self.policy.trip(raw,ctx['trip_id'],True)
            if trip['status'] in {'COMPLETE','INTERRUPTED'}:raise AuthError(409,'NAVIGATION_CLOSED')
            return self.dto(ctx)

    def control(self,raw,nid,body):
        fields(body,{'command','expected_revision'})
        with self.lock:
            self.navigation(raw,nid);ctx=self.contexts[nid]
            if not ctx.get('drive'):raise AuthError(409,'NAVIGATION_CLOSED')
            ctx['drive'].control(body['command'],body['expected_revision'])
            return self.dto(ctx)

    def simulation(self,raw,nid,body):
        with self.lock:
            self.navigation(raw,nid);ctx=self.contexts[nid]
            if not ctx.get('drive'):raise AuthError(409,'NAVIGATION_CLOSED')
            ctx['drive'].configure(body)
            return self.dto(ctx)

    def start(self,raw,body,key,request_id):
        fields(body,{'trip_id'},{'device_id'});operation_key(key);identifier(body['trip_id'])
        with self.lock:
            self.retry_failed_starts()
            with self.repo.atomic(request_id) as (repo,c):
                row,actor=self.policy.accounts.sessions.lookup(raw,connection=c)
                trip=repo.own_trip(c,actor,body['trip_id'])
                route=c.execute('SELECT id,payload,payload_hash FROM config_versions WHERE id=?',(trip['route_version_id'],)).fetchone() if trip['route_version_id'] else None
                route_snapshot=None if route is None else {'version_id':route['id'],'payload':json.loads(route['payload']),'payload_hash':route['payload_hash']}
                old=c.execute("SELECT * FROM recording_operations WHERE actor_id=? AND kind='START' AND idempotency_key=?",(actor.user_id,key)).fetchone()
                if old:
                    if old['trip_id']!=trip['id'] or old['request_hash']!=request_hash(body):raise Conflict('Changed start key')
                    ctx=self.contexts.get(old['id'])
                    if not ctx:raise Conflict('Navigation requires a new planned trip after restart/failure')
                    if ctx['session_id']!=row['id'] or ctx['credential']!=row['secret_hash']:raise AuthError(404,'NOT_FOUND')
                    return self.dto(ctx)
                device=None
                if trip['mode']=='LIVE':
                    self.devices.real()
                    device=c.execute("SELECT * FROM devices WHERE id=? AND owner_id=? AND parent_session_id=? AND boot_id=? AND status='ACTIVE' AND revoked_at IS NULL AND expiry>? AND security_version=?",(resource_id(body.get('device_id')),actor.user_id,row['id'],self.boot,repo.clock(),row['security_version'])).fetchone()
                    if device is None:raise AuthError(404,'NOT_FOUND')
                elif 'device_id' in body:raise AuthError(422,'VALIDATION')
                if trip['status']!='PLANNED' or trip['archived_at'] is not None:raise Conflict('Trip not planned')
                if c.execute("SELECT 1 FROM trips WHERE status IN ('STARTING','RECORDING','FINALIZING') LIMIT 1").fetchone():raise AuthError(409,'ACTIVE_SESSION_BUSY')
                run_id=repo.new_id();nid=repo.new_id()
                repo.transition_trip(actor,trip['id'],trip['revision'],'STARTING',run_id=run_id)
                c.execute("INSERT INTO recording_operations(id,trip_id,actor_id,kind,idempotency_key,request_hash,state,created_at,parent_session_id,boot_id) VALUES(?,?,?,'START',?,?,'PENDING',?,?,?)",(nid,trip['id'],actor.user_id,key,request_hash(body),repo.clock(),row['id'],self.boot))
            logger=None
            try:
                self.fault('start-path')
                logger=RunLogger(self.storage.run(actor.user_id,trip['id'],run_id).parent)
                ctx={'id':nid,'trip_id':trip['id'],'owner_id':actor.user_id,'session_id':row['id'],'credential':row['secret_hash'],'raw':raw,'logger':logger,'started_at':repo.clock(),'device_id':None if device is None else device['id'],'device_credential':None if device is None else device['token_hash']}
                self.contexts[nid]=ctx
                self.fault('start-intent')
                now=utc(repo.clock())
                from greenwave.school_navigation.engine import Drive
                drive=Drive(self,ctx,trip['mode']);ctx['drive']=drive
                if trip['mode']=='LIVE':
                    from greenwave.school_navigation.maps import snapshot_route
                    selected=snapshot_route(self.storage,route_snapshot)
                    from greenwave.school_navigation.maps import BoundRoutes
                    drive.app.routes=BoundRoutes(selected)
                    drive.app.selected_route=selected;drive.app.map_matcher.set_route(selected);drive.app.route_events.set_route(selected,nid)
                logger.start({**drive.metadata(),'start_time':now,'timebase':'SIMULATION' if trip['mode']=='SIMULATION' else 'UTC_ELAPSED','school_owner_id':actor.user_id,'school_trip_id':trip['id'],'school_route_snapshot':route_snapshot},run_id=run_id)
                self.fault('start-files')
                if not logger.append('RUN_START',timestamp=now,simulation_seconds=0,model_seconds=0):raise OSError('Logger start failed')
                if trip['mode']=='SIMULATION' and not logger.append('TELEMETRY',timestamp=now,simulation_seconds=0,model_seconds=0,source='SIMULATION',current_corridor_position=0,speed_mps=0):raise OSError('Logger sample failed')
                self.fault('start-recording')
                with self.repo.atomic(request_id) as (repo,c):
                    # A revoked credential cannot turn a STARTING intent into an active drive.
                    self.policy.accounts.sessions.lookup(raw,connection=c)
                    if device is not None and not c.execute("SELECT 1 FROM devices WHERE id=? AND status='ACTIVE' AND revoked_at IS NULL AND expiry>?",(device['id'],repo.clock())).fetchone():raise AuthError(403,'DEVICE_REPAIR_REQUIRED')
                    t=repo.own_trip(c,actor,trip['id']);repo.transition_trip(actor,trip['id'],t['revision'],'RECORDING')
                    c.execute("UPDATE recording_operations SET state='APPLIED',result_ref=? WHERE id=?",(self.raw.root({**dict(t),'run_id':run_id}).relative_to(self.storage.root).as_posix(),nid))
                drive.start()
            except Exception as error:
                # The committed intention exists even if path/logger/context creation failed.
                failed_context=self.contexts.pop(nid,None)
                if failed_context and failed_context.get('drive'):failed_context['drive'].close()
                self.failed_starts[nid]={'id':nid,'trip_id':trip['id'],'owner_id':actor.user_id,
                    'run_id':run_id,'logger':logger,'request_id':request_id,
                    'cause':type(error.__cause__ if isinstance(error.__cause__,OSError) else error).__name__}
                self.retry_failed_starts()
                # RunLogger wraps filesystem errors in ValueError; keep them server failures.
                if isinstance(error,ValueError) and isinstance(error.__cause__,OSError):
                    raise OSError('Recording start unavailable') from None
                raise
            return self.dto(ctx)

    @staticmethod
    def close_failed_logger(logger):
        """Close without a manifest, including failure of the convenience close method."""
        if logger is None:return True
        stream=logger.stream
        logger.active=False
        try:
            logger.close_unfinished()
        except Exception:
            pass
        # Keep the captured stream reachable if close_unfinished clears its reference.
        try:
            if stream is not None and not stream.closed:stream.close()
        except Exception:
            logger.stream=stream
            return False
        logger.stream=logger.writer=None
        return True

    def retry_failed_starts(self):
        """Retry local cleanup independently of active contexts; SQLite remains authoritative."""
        with self.lock:
            for nid,item in list(self.failed_starts.items()):
                closed=self.close_failed_logger(item['logger'])
                try:
                    with self.repo.database.transaction() as c:
                        op=c.execute("SELECT state FROM recording_operations WHERE id=? AND trip_id=? AND actor_id=? AND boot_id=? AND kind='START'",
                            (nid,item['trip_id'],item['owner_id'],self.boot)).fetchone()
                        if op is None:raise Conflict('Missing failed start intention')
                        changed=c.execute("UPDATE trips SET status='INTERRUPTED',ended_at=?,revision=revision+1 WHERE id=? AND owner_id=? AND run_id=? AND status IN ('STARTING','RECORDING')",
                            (self.repo.clock(),item['trip_id'],item['owner_id'],item['run_id'])).rowcount
                        if op['state'] in {'PENDING','APPLIED'}:
                            c.execute("UPDATE recording_operations SET state='FAILED' WHERE id=?",(nid,))
                        if changed:
                            self.repo.audit(c,None,'RECORDING_INTERRUPTED','TRIP',item['trip_id'],
                                'START_FAILED:'+item['cause'],item['request_id'])
                    if closed:self.failed_starts.pop(nid,None)
                except Exception as error:
                    # Retain controlled IDs and exception classes only, not paths/secret payloads.
                    item['cleanup_cause']=type(error).__name__
                    # No claim of releasing the SQLite reservation until the transaction commits.


    def journal(self,oid,request_id):
        with self.lock:
            with self.repo.database.connection() as c:
                obs=dict(c.execute('SELECT * FROM observations WHERE id=?',(oid,)).fetchone())
                trip=dict(c.execute('SELECT * FROM trips WHERE id=?',(obs['trip_id'],)).fetchone())
            if obs['journaling_state']=='APPLIED':return
            ctx=next((v for v in self.contexts.values() if v['trip_id']==trip['id']),None)
            try:
                sequence=self.raw.journal_sequence(trip,obs)
                if sequence is None:
                    if not ctx or not ctx['logger'].active or trip['status'] not in {'RECORDING','FINALIZING'}:raise OSError('No active raw writer')
                    elapsed=ctx['drive'].app.clock.read().simulation_seconds if ctx.get('drive') else max(0,self.repo.clock()-ctx['started_at'])/1000
                    if not ctx['logger'].append('MANUAL_OBSERVATION',timestamp=utc(obs['server_received_at']),simulation_seconds=elapsed,model_seconds=elapsed,
                        signal_id=obs['signal_id'],source='MANUAL',payload={'observation_id':oid,'source_event_id':obs['source_event_id'],'state':obs['state'],'event_type':obs['event_type']}):raise OSError('Journal write failed')
                    sequence=ctx['logger'].sequence
                self.fault('journal-written')
                with self.repo.database.transaction() as c:
                    c.execute("UPDATE observations SET raw_sequence=?,journaling_state='APPLIED' WHERE id=?",(sequence,oid))
                    c.execute("UPDATE recording_operations SET state='APPLIED' WHERE observation_id=? AND state='PENDING'",(oid,))
            except (OSError,ValueError):
                # Durable fact survives raw failure. It is explicitly not an applied journal.
                with self.repo.database.transaction() as c:
                    c.execute("UPDATE observations SET journaling_state='FAILED' WHERE id=?",(oid,))
                    if ctx is None:c.execute("UPDATE recording_operations SET state='FAILED' WHERE observation_id=? AND state='PENDING'",(oid,))

    def finish(self,raw,nid,body,key,request_id):
        fields(body,{'command','expected_revision'});revision(body['expected_revision']);operation_key(key)
        if body['command']!='FINISH':raise AuthError(422,'COMMAND_NOT_INTEGRATED')
        row,_=self.policy.session(raw)
        with self.lock:
            ctx=self.contexts.get(resource_id(nid))
            if not ctx or ctx['session_id']!=row['id'] or ctx['credential']!=row['secret_hash']:raise AuthError(404,'NOT_FOUND')
            self.policy.trip(raw,ctx['trip_id'],True)
            result=self.finish_context(ctx,request_id,body,key)
            self.policy.session(raw)
            return result

    def finish_context(self,ctx,request_id,body=None,key=None,system=False):
        fingerprint=request_hash({'navigation':ctx['id'],'system_finish':True}) if system else request_hash({'navigation':ctx['id'],'body':body})
        key=key or request_hash({'system_finish':ctx['id']})
        with self.repo.database.transaction() as c:
            trip=dict(c.execute('SELECT * FROM trips WHERE id=?',(ctx['trip_id'],)).fetchone())
            old=c.execute("SELECT * FROM recording_operations WHERE actor_id=? AND kind='FINISH' AND idempotency_key=?",(ctx['owner_id'],key)).fetchone()
            if old and (old['trip_id']!=trip['id'] or old['request_hash']!=fingerprint):raise Conflict('Changed finish key')
            if trip['status']=='COMPLETE':
                if not old and not system:raise Conflict('Trip already complete with another finish')
                if system:self.contexts.pop(ctx['id'],None)
                return self.dto(ctx)
            if trip['status'] not in {'RECORDING','FINALIZING'}:raise Conflict('Trip not recording')
            if not old:
                if not system and trip['revision']!=body['expected_revision']:raise Conflict('Navigation revision')
                c.execute("INSERT INTO recording_operations(id,trip_id,actor_id,kind,idempotency_key,request_hash,state,created_at,parent_session_id,boot_id) VALUES(?,?,?,'FINISH',?,?,'PENDING',?,?,?)",(self.repo.new_id(),trip['id'],ctx['owner_id'],key,fingerprint,self.repo.clock(),ctx['session_id'],self.boot))
            if trip['status']=='RECORDING':c.execute("UPDATE trips SET status='FINALIZING',revision=revision+1 WHERE id=?",(trip['id'],))
            self.repo.audit(c,None if system else self._actor(ctx),'RECORDING_FINALIZING','TRIP',trip['id'],'CREDENTIALS_REVOKED' if system else 'USER_FINISH',request_id)
        self.fault('finish-intent')
        # Reconcile pending DB facts while raw is still writable, never after completion.
        with self.repo.database.connection() as c:pending=[r[0] for r in c.execute("SELECT id FROM observations WHERE trip_id=? AND historical=0 AND journaling_state!='APPLIED'",(trip['id'],))]
        for oid in pending:self.journal(oid,request_id)
        if getattr(self,'vision',None):self.vision.close_trip(ctx['trip_id'])
        if ctx.get('drive'):ctx['drive'].close()
        root=self.raw.root(trip)
        if not (root/'complete.json').exists():
            elapsed=ctx['drive'].app.clock.read().simulation_seconds if ctx.get('drive') else max(0,self.repo.clock()-ctx['started_at'])/1000
            ctx['logger'].finish('CREDENTIALS_REVOKED' if system else 'USER_STOP',timestamp=utc(self.repo.clock()),simulation_seconds=elapsed,model_seconds=elapsed)
        self.fault('finish-manifest')
        try:reference,raw_hash,manifest_hash=self.raw.validate(trip)
        except (OSError,ValueError):
            ctx['logger'].close_unfinished();self.interrupt(trip['id'],'INVALID_FINAL_MANIFEST',request_id)
            raise Conflict('Recording incomplete') from None
        self.fault('finish-commit')
        with self.repo.database.transaction() as c:
            self.complete(c,trip,reference,raw_hash,manifest_hash,request_id,'SYSTEM_FINISH' if system else 'RECORDING_COMPLETE',None if system else self._actor(ctx))
        if system:self.contexts.pop(ctx['id'],None)
        return self.dto(ctx)

    def _actor(self,ctx):
        from greenwave.school_data import Actor
        return Actor(ctx['owner_id'])

    def complete(self,c,trip,reference,raw_hash,manifest_hash,request_id,action,actor=None):
        import json
        from .paging import rfc3339
        ended=rfc3339(json.loads((self.raw.root(trip)/'complete.json').read_text(encoding='utf-8'))['end_time'])
        c.execute("UPDATE trips SET status='COMPLETE',ended_at=?,raw_ref=?,raw_hash=?,manifest_hash=?,revision=revision+1 WHERE id=?",(ended,reference,raw_hash,manifest_hash,trip['id']))
        c.execute("UPDATE recording_operations SET state='APPLIED' WHERE trip_id=? AND state='PENDING' AND kind IN ('START','FINISH')",(trip['id'],))
        self.repo.audit(c,actor,action,'TRIP',trip['id'],action,request_id)

    def interrupt(self,tid,reason,request_id='recovery'):
        with self.repo.database.transaction() as c:
            c.execute("UPDATE trips SET status='INTERRUPTED',ended_at=?,revision=revision+1 WHERE id=? AND status IN ('STARTING','RECORDING','FINALIZING')",(self.repo.clock(),tid))
            c.execute("UPDATE recording_operations SET state='FAILED' WHERE trip_id=? AND state='PENDING' AND kind IN ('START','FINISH')",(tid,))
            self.repo.audit(c,None,'RECORDING_INTERRUPTED','TRIP',tid,reason,request_id)

    def recover(self):
        with self.repo.database.connection() as c:trips=[dict(t) for t in c.execute("SELECT t.* FROM trips t WHERE t.status IN ('STARTING','RECORDING','FINALIZING')")]
        for trip in trips:
            with self.repo.database.connection() as c:
                bound=c.execute("SELECT 1 FROM recording_operations WHERE trip_id=? AND actor_id=? AND kind='START' AND parent_session_id IS NOT NULL AND boot_id IS NOT NULL",(trip['id'],trip['owner_id'])).fetchone()
            if not bound:
                self.interrupt(trip['id'],'UNBOUND_RECOVERY')
                with self.repo.database.transaction() as c:
                    c.execute("UPDATE observations SET journaling_state='FAILED' WHERE trip_id=? AND journaling_state='PENDING'",(trip['id'],))
                    c.execute("UPDATE recording_operations SET state='FAILED' WHERE trip_id=? AND state='PENDING'",(trip['id'],))
                continue
            try:
                reference,raw_hash,manifest_hash=self.raw.validate(trip)
                with self.repo.database.transaction() as c:self.complete(c,trip,reference,raw_hash,manifest_hash,'startup-recovery','RECOVERY_COMPLETE')
            except (OSError,ValueError,TypeError):self.interrupt(trip['id'],'RECOVERY_INTERRUPTED')
            with self.repo.database.connection() as c:observations=[r[0] for r in c.execute("SELECT id FROM observations WHERE trip_id=? AND historical=0 AND journaling_state!='APPLIED'",(trip['id'],))]
            for oid in observations:self.journal(oid,'startup-recovery')
