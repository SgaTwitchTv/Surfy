import concurrent.futures
import hashlib
import json
import threading
import unittest
from urllib.parse import urlencode
from unittest.mock import patch
from greenwave.school_data import Actor
from greenwave.school_records.paging import rfc3339
from test_school_accounts import Fixture,PASS,PREFIX,NEW
import test_school_resources as resources
from scripts.school_resource_fixtures import populate


class RecordsTests(Fixture):
    use=resources.ResourceTests.use
    get=resources.ResourceTests.get
    post=resources.ResourceTests.post
    def setUp(self):
        super().setUp();self.fixture=populate(self.repo,self.service.passwords.hash(PASS))
        self.users=self.fixture['users'];self.trips=self.fixture['trips'];self.tid=self.trips['shared']['id'];self.credentials={}
        for who in self.users:
            self.cookies={};self.preflight();status,data,_=self.auth('login',{'email':who+'@example.test','password':PASS});self.assertEqual(status,200)
            self.credentials[who]=(dict(self.cookies),data['data']['csrf'])
        self.use('driver')
    def new_trip(self,title='Test trip'):
        status,data,_=self.post('/trips',{'title':title,'mode':'SIMULATION','note':'Synthetic'})
        self.assertEqual(status,201,data);return data['data']
    def start(self,trip,key='s'*32):
        status,data,_=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':key})
        self.assertEqual(status,201,data);return data['data']
    def finish(self,nav,key='f'*32):
        return self.request('POST',PREFIX+'/navigation/'+nav['id']+'/control',{'command':'FINISH','expected_revision':nav['revision']},{'Idempotency-Key':key})
    def raw_path(self,tid):
        with self.db.connection() as c:t=dict(c.execute('SELECT * FROM trips WHERE id=?',(tid,)).fetchone())
        return self.storage.run(t['owner_id'],tid,t['run_id'])/'raw.csv'

    def test_failed_start_storage_run_after_intent_releases_reservation(self):
        rec=self.server.resources.recorder;trip=self.new_trip('Failed path')
        self.use('other');second=self.new_trip('Next user');self.use('driver')
        def fail_path(*args):
            with self.db.connection() as c:
                t=c.execute('SELECT status FROM trips WHERE id=?',(trip['id'],)).fetchone()
                op=c.execute("SELECT state FROM recording_operations WHERE trip_id=? AND kind='START'",(trip['id'],)).fetchone()
            self.assertEqual((t[0],op[0]),('STARTING','PENDING'))
            raise OSError('synthetic path preparation failure')
        with patch.object(rec.storage,'run',side_effect=fail_path):
            status,data,_=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'p'*32})
        self.assertNotIn('synthetic path',json.dumps(data))
        with self.db.connection() as c:
            state=c.execute('SELECT status FROM trips WHERE id=?',(trip['id'],)).fetchone()[0]
            intent=c.execute("SELECT state FROM recording_operations WHERE trip_id=? AND kind='START'",(trip['id'],)).fetchone()[0]
        self.assertFalse(any(ctx['trip_id']==trip['id'] for ctx in rec.contexts.values()))
        self.use('other')
        next_status=self.request('POST',PREFIX+'/navigation',{'trip_id':second['id']},{'Idempotency-Key':'q'*32})[0]
        self.assertEqual((status,state,intent,next_status),(503,'INTERRUPTED','FAILED',201))

    def failed_start_state(self,tid):
        with self.db.connection() as c:
            trip=dict(c.execute('SELECT * FROM trips WHERE id=?',(tid,)).fetchone())
            intent=dict(c.execute("SELECT * FROM recording_operations WHERE trip_id=? AND kind='START'",(tid,)).fetchone())
            audits=c.execute("SELECT count(*) FROM audit_events WHERE resource_id=? AND action='RECORDING_INTERRUPTED'",(tid,)).fetchone()[0]
        return trip,intent,audits

    def test_failed_start_constructor_context_and_partial_files(self):
        from greenwave.telemetry import RunLogger
        rec=self.server.resources.recorder;captured=[]
        def logger(root):
            obj=RunLogger(root);captured.append(obj);return obj
        for boundary in ['constructor','start-intent','start-files','start-recording']:
            with self.subTest(boundary=boundary):
                trip=self.new_trip(boundary)
                def fail(point):
                    if point==boundary:raise OSError('synthetic start failure')
                rec.fault=fail
                with patch('greenwave.school_records.recording.RunLogger',side_effect=OSError('synthetic constructor') if boundary=='constructor' else logger):
                    status=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':hashlib.sha256(boundary.encode()).hexdigest()})[0]
                rec.fault=lambda _:None
                self.assertEqual(status,503)
                t,op,audits=self.failed_start_state(trip['id'])
                self.assertEqual((t['status'],op['state'],audits),('INTERRUPTED','FAILED',1))
                self.assertFalse(any(v['trip_id']==trip['id'] for v in rec.contexts.values()))
                self.assertFalse(rec.failed_starts)
                root=self.storage.run(t['owner_id'],t['id'],t['run_id'])
                self.assertFalse((root/'complete.json').exists())
                if boundary!='constructor':
                    obj=captured[-1];self.assertFalse(obj.active);self.assertIsNone(obj.stream)
                if boundary in {'start-files','start-recording'}:
                    before={p.name:p.read_bytes() for p in root.iterdir()}
                    self.assertIn('raw.csv',before);self.assertIn('metadata.json',before)
                    self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':hashlib.sha256(boundary.encode()).hexdigest()})[0],409)
                    self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
                    self.assertEqual(self.failed_start_state(trip['id'])[2],1)
        self.use('other');self.start(self.new_trip('After failures'),key='z'*32)

    def test_failed_start_actual_recording_commit_rollback(self):
        import sqlite3
        rec=self.server.resources.recorder;trip=self.new_trip('Commit rollback')
        original=self.repo.__class__.transition_trip
        def fail(repo,actor,tid,expected,status,**kw):
            result=original(repo,actor,tid,expected,status,**kw)
            if status=='RECORDING':raise sqlite3.OperationalError('synthetic transaction failure')
            return result
        with patch.object(self.repo.__class__,'transition_trip',new=fail):
            self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'t'*32})[0],503)
        t,op,audits=self.failed_start_state(trip['id'])
        self.assertEqual((t['status'],op['state'],audits),('INTERRUPTED','FAILED',1))
        self.assertFalse(rec.contexts);self.start(self.new_trip('Next'))

    def test_failed_start_close_failure_falls_back_to_stream_close(self):
        from greenwave.telemetry import RunLogger
        rec=self.server.resources.recorder;trip=self.new_trip('Close failure');streams=[];loggers=[]
        def fail(point):
            if point=='start-recording':
                obj=next(iter(rec.contexts.values()))['logger'];loggers.append(obj);streams.append(obj.stream)
                raise OSError('synthetic start failure')
        rec.fault=fail
        with patch.object(RunLogger,'close_unfinished',side_effect=OSError('synthetic close wrapper failure')):
            self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'c'*32})[0],503)
        rec.fault=lambda _:None
        self.assertTrue(streams[0].closed);self.assertFalse(loggers[0].active);self.assertIsNone(loggers[0].stream)
        self.assertFalse(rec.contexts);self.assertFalse(rec.failed_starts)
        self.assertEqual(self.failed_start_state(trip['id'])[0]['status'],'INTERRUPTED')

    def test_failed_start_cleanup_db_retry_without_context_and_no_duplicate_audit(self):
        import sqlite3
        rec=self.server.resources.recorder;rec.stop.set();rec.thread.join(timeout=5)
        for boundary in ['path','start-recording']:
            with self.subTest(boundary=boundary):
                self.use('driver');trip=self.new_trip(boundary);observed=[]
                def fail(point):
                    if point=='start-recording' and boundary==point:
                        obj=next(v for v in rec.contexts.values() if v['trip_id']==trip['id'])['logger']
                        observed.append(obj.stream);raise OSError('synthetic partial start')
                rec.fault=fail;original_audit=rec.repo.audit
                def unavailable(*args,**kwargs):
                    if len(args)>5 and str(args[5]).startswith('START_FAILED:'):raise sqlite3.OperationalError('synthetic cleanup database unavailable')
                    return original_audit(*args,**kwargs)
                with patch.object(rec.repo,'audit',side_effect=unavailable):
                    if boundary=='path':
                        with patch.object(rec.storage,'run',side_effect=OSError('synthetic path failure')):
                            response=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':hashlib.sha256(boundary.encode()).hexdigest()})
                    else:response=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':hashlib.sha256(boundary.encode()).hexdigest()})
                    self.assertEqual(response[0],503);rec.fault=lambda _:None
                    t,op,audits=self.failed_start_state(trip['id'])
                    self.assertEqual((t['status'],op['state'],audits),('STARTING','PENDING',0))
                    self.assertFalse(any(v['trip_id']==trip['id'] for v in rec.contexts.values()))
                    self.assertEqual(len(rec.failed_starts),1)
                    if observed:self.assertTrue(observed[0].closed)
                    self.use('other');next_trip=self.new_trip('Blocked next')
                    self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':next_trip['id']},{'Idempotency-Key':hashlib.sha256(('next'+boundary).encode()).hexdigest()})[0],409)
                # The same entry point called by the watchdog retries even with no active ctx.
                rec.reconcile_credentials();rec.reconcile_credentials()
                t,op,audits=self.failed_start_state(trip['id'])
                self.assertEqual((t['status'],op['state'],audits),('INTERRUPTED','FAILED',1))
                self.assertFalse(rec.failed_starts)
                nav=self.start(next_trip,key=hashlib.sha256(('next'+boundary).encode()).hexdigest());self.assertEqual(self.finish(nav,key=hashlib.sha256(('finish'+boundary).encode()).hexdigest())[0],200)

    def test_failed_start_cleanup_stream_retry_keeps_handle_until_closed(self):
        rec=self.server.resources.recorder;rec.stop.set();rec.thread.join(timeout=5)
        trip=self.new_trip('Stream close retry');seen=[]
        class FailingClose:
            def __init__(self,stream):self.stream=stream;self.fail=True
            @property
            def closed(self):return self.stream.closed
            def close(self):
                if self.fail:raise OSError('synthetic stream close failure')
                self.stream.close()
        def fail(point):
            if point=='start-recording':
                obj=next(iter(rec.contexts.values()))['logger'];obj.stream=FailingClose(obj.stream);seen.append(obj.stream)
                raise OSError('synthetic partial start')
        rec.fault=fail
        self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'u'*32})[0],503)
        rec.fault=lambda _:None;self.assertFalse(rec.contexts);self.assertEqual(len(rec.failed_starts),1)
        self.assertFalse(seen[0].closed);self.assertEqual(self.failed_start_state(trip['id'])[0]['status'],'INTERRUPTED')
        seen[0].fail=False;rec.reconcile_credentials();rec.reconcile_credentials()
        self.assertTrue(seen[0].closed);self.assertFalse(rec.failed_starts);self.assertEqual(self.failed_start_state(trip['id'])[2],1)

    def test_failed_start_cleanup_restart_and_revoked_session(self):
        import sqlite3
        from greenwave.school_records.recording import Recording
        rec=self.server.resources.recorder;rec.stop.set();rec.thread.join(timeout=5);trip=self.new_trip('Restart cleanup')
        original_audit=rec.repo.audit
        def unavailable(*args,**kwargs):
            if len(args)>5 and str(args[5]).startswith('START_FAILED:'):raise sqlite3.OperationalError('synthetic cleanup unavailable')
            return original_audit(*args,**kwargs)
        with patch.object(rec.repo,'audit',side_effect=unavailable),patch.object(rec.storage,'run',side_effect=OSError('synthetic path failure')):
            self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'r'*32})[0],503)
        self.assertEqual(self.failed_start_state(trip['id'])[0]['status'],'STARTING')
        with patch.object(rec.repo,'audit',side_effect=unavailable):rec.close()
        self.assertEqual(self.failed_start_state(trip['id'])[0]['status'],'STARTING')
        self.server.resources.recorder=Recording(rec.policy);fresh=self.server.resources.recorder
        self.assertEqual(self.failed_start_state(trip['id'])[0]['status'],'INTERRUPTED')
        self.assertEqual(self.failed_start_state(trip['id'])[1]['state'],'FAILED')
        self.assertFalse(fresh.contexts)
        trip=self.new_trip('Revoke during start');raw=self.cookies['gw_session'];entered=threading.Event();release=threading.Event()
        def barrier(point):
            if point=='start-recording':entered.set();self.assertTrue(release.wait(5))
        fresh.fault=barrier
        # Derive the current session ID in the test, never via a client supplied owner.
        row,_=self.service.sessions.lookup(raw)
        def revoke():
            self.assertTrue(entered.wait(5))
            with self.db.transaction() as c:c.execute('UPDATE browser_sessions SET revoked_at=? WHERE id=?',(self.now,row['id']))
            release.set()
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            pending=pool.submit(revoke)
            response=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'v'*32});pending.result(timeout=5)
        fresh.fault=lambda _:None;self.assertEqual(response[0],401)
        t,op,audits=self.failed_start_state(trip['id']);self.assertEqual((t['status'],op['state'],audits),('INTERRUPTED','FAILED',1))
        self.assertFalse(any(v['trip_id']==trip['id'] for v in fresh.contexts.values()))
        self.use('other');self.start(self.new_trip('After revoked start'),key='w'*32)

    def test_failed_start_watchdog_retries_cleanup_without_active_context(self):
        import sqlite3
        rec=self.server.resources.recorder;trip=self.new_trip('Watchdog cleanup')
        unavailable=threading.Event();unavailable.set();committing=threading.Event()
        original=rec.repo.audit
        def audit(*args,**kwargs):
            if len(args)>5 and str(args[5]).startswith('START_FAILED:'):
                if unavailable.is_set():raise sqlite3.OperationalError('synthetic cleanup unavailable')
                result=original(*args,**kwargs);committing.set();return result
            return original(*args,**kwargs)
        with patch.object(rec.repo,'audit',side_effect=audit):
            with patch.object(rec.storage,'run',side_effect=OSError('synthetic path failure')):
                self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'d'*32})[0],503)
            self.assertEqual(self.failed_start_state(trip['id'])[0]['status'],'STARTING');self.assertFalse(rec.contexts)
            unavailable.clear();self.assertTrue(committing.wait(5),'watchdog did not retry')
            with rec.lock:self.assertFalse(rec.failed_starts)
        t,op,audits=self.failed_start_state(trip['id'])
        self.assertEqual((t['status'],op['state'],audits),('INTERRUPTED','FAILED',1))
        self.use('other');self.start(self.new_trip('Watchdog released'),key='e'*32)

    def test_failed_start_before_reservation_commit_creates_no_files_or_cleanup(self):
        import sqlite3
        rec=self.server.resources.recorder;trip=self.new_trip('Before commit')
        original=self.repo.__class__.transition_trip
        def fail(repo,actor,tid,expected,status,**kw):
            result=original(repo,actor,tid,expected,status,**kw)
            if status=='STARTING':raise sqlite3.OperationalError('synthetic reservation rollback')
            return result
        with patch.object(self.repo.__class__,'transition_trip',new=fail),patch('greenwave.school_records.recording.RunLogger') as logger:
            self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'b'*32})[0],503)
            logger.assert_not_called()
        with self.db.connection() as c:
            self.assertEqual(c.execute('SELECT status FROM trips WHERE id=?',(trip['id'],)).fetchone()[0],'PLANNED')
            self.assertEqual(c.execute('SELECT count(*) FROM recording_operations WHERE trip_id=?',(trip['id'],)).fetchone()[0],0)
            self.assertEqual(c.execute("SELECT count(*) FROM audit_events WHERE resource_id=? AND action='RECORDING_INTERRUPTED'",(trip['id'],)).fetchone()[0],0)
        self.assertFalse(rec.contexts);self.assertFalse(rec.failed_starts)
        self.assertFalse(self.storage.trip(self.users['driver']['id'],trip['id']).exists())
        self.start(trip,key='b'*32)

    def test_failed_start_real_partial_files_and_initial_append(self):
        from greenwave.telemetry import RunLogger,write_new
        rec=self.server.resources.recorder;seen=[]
        def make_logger(root):
            obj=RunLogger(root);seen.append(obj);return obj
        for phase in ['metadata','writer','append']:
            with self.subTest(phase=phase):
                trip=self.new_trip(phase);key=hashlib.sha256(phase.encode()).hexdigest()
                def partial(path,value):
                    write_new(path,value);raise OSError('synthetic failure after metadata fsync')
                target={'metadata':'greenwave.telemetry.write_new','writer':'greenwave.telemetry.csv.DictWriter','append':'greenwave.telemetry.RunLogger.append'}[phase]
                kw={'side_effect':partial} if phase=='metadata' else {'side_effect':OSError('synthetic writer construction')} if phase=='writer' else {'return_value':False}
                with patch('greenwave.school_records.recording.RunLogger',side_effect=make_logger),patch(target,**kw):
                    self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':key})[0],503)
                t,op,audits=self.failed_start_state(trip['id'])
                self.assertEqual((t['status'],op['state'],audits),('INTERRUPTED','FAILED',1))
                root=self.storage.run(t['owner_id'],t['id'],t['run_id']);before={p.name:p.read_bytes() for p in root.iterdir()}
                self.assertIn('metadata.json',before);self.assertNotIn('complete.json',before)
                self.assertFalse(seen[-1].active);self.assertIsNone(seen[-1].stream);self.assertFalse(rec.contexts)
                self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':key})[0],409)
                self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
        self.use('other');self.start(self.new_trip('Partial start released'),key='j'*32)

    def test_full_write_record_correct_share_revoke_archive(self):
        trip=self.new_trip();nav=self.start(trip)
        obsbody={'signal_id':'synthetic-light','state':'RED','event_type':'STATE_SEEN','source_event_id':'record-event'}
        status,data,_=self.post('/trips/'+trip['id']+'/observations',obsbody)
        self.assertEqual(status,201,data);oid=data['data']['id'];self.assertFalse(data['data']['historical']);self.assertEqual(data['data']['journaling_state'],'APPLIED')
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',obsbody)[1]['data']['id'],oid)
        self.assertEqual(self.finish(nav)[0],200)
        self.assertEqual(self.finish(nav)[0],200)
        raw=self.raw_path(trip['id']);before=raw.read_bytes()
        self.assertEqual(self.get('/trips/'+trip['id']+'/export')[0],200)
        current=self.get('/trips/'+trip['id'])[1]['data']
        status,data,_=self.request('PATCH',PREFIX+'/trips/'+trip['id'],{'expected_revision':current['revision'],'title':'Edited'})
        self.assertEqual(status,200,data);current=data['data']
        body={'expected_revision':0,'client_operation_id':'c'*32,'changes':{'state':'GREEN'},'reason':'Synthetic correction'}
        status,data,_=self.post('/observations/'+oid+'/corrections',body)
        self.assertEqual(status,201,data);self.assertEqual(data['data']['observation']['effective']['state'],'GREEN')
        cid=data['data']['correction']['id'];self.assertEqual(self.post('/observations/'+oid+'/corrections',body)[1]['data']['correction']['id'],cid)
        history=self.post('/trips/'+trip['id']+'/observations',{**obsbody,'source_event_id':'history'})[1]['data']
        self.assertTrue(history['historical']);self.assertIsNone(history['measured_at']);self.assertEqual(raw.read_bytes(),before)
        status,data,_=self.post('/trips/'+trip['id']+'/share',{'analyst_email':'analyst@example.test'})
        self.assertEqual(status,201,data);share=data['data']['id']
        self.use('analyst');self.assertEqual(self.get('/trips/'+trip['id'])[0],200)
        self.assertEqual(self.get('/trips/'+trip['id']+'/export')[0],404)
        self.use('driver');self.assertEqual(self.request('DELETE',PREFIX+'/trips/'+trip['id']+'/share',{'expected_share_id':share})[0],204)
        self.assertEqual(self.request('DELETE',PREFIX+'/trips/'+trip['id']+'/share',{'expected_share_id':share})[0],204)
        self.assertEqual(self.request('DELETE',PREFIX+'/trips/'+trip['id'],{'expected_revision':current['revision'],'reason':'Archive test'})[0],204)
        self.assertEqual(self.get('/trips?archived=true')[1]['data']['items'][0]['id'],trip['id']);self.assertEqual(raw.read_bytes(),before)
        with self.db.connection() as c:
            audit=c.execute("SELECT request_id FROM audit_events WHERE resource_id=? AND action='TRIP_CREATED'",(trip['id'],)).fetchone()
            self.assertNotEqual(audit[0],'internal')

    def test_mutation_validation_spoof_csrf_and_foreign(self):
        trip=self.new_trip()
        for method,path,body in [('PATCH','/trips/'+trip['id'],{'expected_revision':1,'note':'note'}),('DELETE','/trips/'+trip['id'],{'expected_revision':1,'reason':'reason'}),('POST','/trips/'+self.tid+'/share',{'analyst_email':'analyst@example.test'})]:
            for headers in [{'X-CSRF-Token':'bad'},{'Origin':'http://evil.test'}]:self.assertEqual(self.request(method,PREFIX+path,body,headers)[0],403)
            for who in ['other','analyst','admin',None]:
                self.use(who);self.assertEqual(self.request(method,PREFIX+path,body)[0],401 if who is None else 404)
            self.use('driver')
        for body in [{'title':'x','mode':'SIMULATION','owner_id':self.users['admin']['id']},{'title':'x','mode':True},{'title':'x','mode':'SIMULATION','route_version_id':False},{'title':'x','mode':'SIMULATION','route_version_id':''},{'title':'x','mode':'LIVE'}]:self.assertEqual(self.post('/trips',body)[0],422)
        for body in [{'expected_revision':True,'title':'x'},{'expected_revision':1,'raw_ref':'x'},{'expected_revision':1}]:self.assertEqual(self.request('PATCH',PREFIX+'/trips/'+trip['id'],body)[0],422)
        nav=self.start(trip)
        invalid={'signal_id':'x','state':'UNKNOWN','event_type':'STATE_START','source_event_id':'x'}
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',invalid)[0],422)
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',{**invalid,'state':'RED','source':'CV'})[0],422)
        self.assertEqual(self.request('DELETE',PREFIX+'/trips/'+trip['id'],{'expected_revision':nav['revision'],'reason':'reason'})[0],409)

    def test_concurrent_revision_and_recording_reservation(self):
        trip=self.new_trip();raw=self.cookies['gw_session'];barrier=threading.Barrier(2)
        def edit(title):barrier.wait();return self.server.resources.writes.edit(raw,trip['id'],{'expected_revision':1,'title':title},'concurrent')
        def outcome(fn,arg):
            try:fn(arg);return 'OK'
            except Exception as error:return type(error).__name__
        with concurrent.futures.ThreadPoolExecutor(2) as pool:self.assertCountEqual(list(pool.map(lambda x:outcome(edit,x),['a','b'])),['OK','Conflict'])
        a=self.new_trip('A');self.use('other');b=self.new_trip('B');otherraw=self.cookies['gw_session'];self.use('driver');ownerraw=self.cookies['gw_session'];barrier=threading.Barrier(2)
        def start(args):
            from greenwave.school_accounts.errors import AuthError
            barrier.wait()
            try:return self.server.resources.recorder.start(args[0],{'trip_id':args[1]},args[2],'concurrent')
            except AuthError as error:
                self.assertEqual((error.status,error.code),(409,'ACTIVE_SESSION_BUSY'));raise
        with concurrent.futures.ThreadPoolExecutor(2) as pool:self.assertCountEqual(list(pool.map(lambda x:outcome(start,x),[(ownerraw,a['id'],'a'*32),(otherraw,b['id'],'b'*32)])),['OK','AuthError'])

    def test_key_conflicts_and_stale_share_revoke(self):
        trip=self.new_trip();nav=self.start(trip)
        self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':'s'*32})[1]['data']['id'],nav['id'])
        other=self.new_trip();self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':other['id']},{'Idempotency-Key':'s'*32})[0],409)
        body={'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'same'}
        oid=self.post('/trips/'+trip['id']+'/observations',body)[1]['data']['id']
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',{**body,'state':'GREEN'})[0],409)
        correction={'expected_revision':0,'client_operation_id':'c'*32,'changes':{'valid':False},'reason':'reason'}
        self.assertEqual(self.post('/observations/'+oid+'/corrections',correction)[0],201)
        self.assertEqual(self.post('/observations/'+oid+'/corrections',{**correction,'reason':'changed'})[0],409)
        old=self.fixture['share'];self.request('DELETE',PREFIX+'/trips/'+self.tid+'/share',{'expected_share_id':old})
        new=self.post('/trips/'+self.tid+'/share',{'analyst_email':'analyst@example.test'})[1]['data']['id']
        self.assertEqual(self.request('DELETE',PREFIX+'/trips/'+self.tid+'/share',{'expected_share_id':old})[0],204)
        with self.db.connection() as c:self.assertIsNone(c.execute('SELECT revoked_at FROM trip_shares WHERE id=?',(new,)).fetchone()[0])

    def test_recording_faults_and_recovery(self):
        rec=self.server.resources.recorder
        for boundary in ['start-intent','start-files','start-recording']:
            trip=self.new_trip(boundary)
            rec.fault=lambda point,b=boundary:(_ for _ in ()).throw(OSError('synthetic failure')) if point==b else None
            self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id']},{'Idempotency-Key':hashlib.sha256(boundary.encode()).hexdigest()})[0],503)
            self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'INTERRUPTED')
        rec.fault=lambda _:None;trip=self.new_trip();nav=self.start(trip)
        rec.fault=lambda point:(_ for _ in ()).throw(OSError('after manifest')) if point=='finish-commit' else None
        self.assertEqual(self.finish(nav)[0],503);before=self.raw_path(trip['id']).read_bytes()
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'FINALIZING')
        rec.fault=lambda _:None;rec.recover()
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'COMPLETE');self.assertEqual(self.raw_path(trip['id']).read_bytes(),before)
        self.assertEqual(self.get('/trips/'+trip['id']+'/export')[0],200)

    def test_journal_retry_after_second_store_failure(self):
        trip=self.new_trip();nav=self.start(trip);rec=self.server.resources.recorder
        rec.fault=lambda point:(_ for _ in ()).throw(OSError('synthetic journal checkpoint failure')) if point=='journal-written' else None
        body={'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'unique'}
        status,data,_=self.post('/trips/'+trip['id']+'/observations',body);self.assertEqual(status,202);self.assertEqual(data['data']['journaling_state'],'FAILED')
        rec.fault=lambda _:None;self.assertEqual(self.post('/trips/'+trip['id']+'/observations',body)[0],201)
        rows=rec.raw.rows({**self.trips['shared'], 'id':trip['id'],'run_id':rec.contexts[nav['id']]['logger'].run_id})
        self.assertEqual(sum(json.loads(r['payload_json']).get('source_event_id')=='unique' for r in rows),1)
        self.assertEqual(self.finish(nav)[0],200)

    def test_logout_reset_and_security_change_finalize(self):
        for action in ['logout','reset','role']:
            self.use('driver')
            if action!='logout':
                self.preflight();_,data,_=self.auth('login',{'email':'driver@example.test','password':PASS});self.csrf=data['data']['csrf']
            trip=self.new_trip(action);nav=self.start(trip,key=hashlib.sha256(action.encode()).hexdigest())
            if action=='logout':self.assertEqual(self.auth('logout',{})[0],204)
            elif action=='reset':
                self.service.request_reset({'email':'driver@example.test'},'synthetic-ip');token=self.mail_token('reset');self.service.use_token({'token':token,'password':PASS,'password_confirmation':PASS},'synthetic-ip','RESET')
            else:
                user=self.repo.get_user(self.users['driver']['id']);self.repo.change_account(Actor(self.users['admin']['id'],self.now),user['id'],user['revision'],role='ANALYST');self.server.resources.recorder.reconcile_credentials()
            with self.db.connection() as c:self.assertEqual(c.execute('SELECT status FROM trips WHERE id=?',(trip['id'],)).fetchone()[0],'COMPLETE')
            self.assertNotIn(nav['id'],self.server.resources.recorder.contexts)

    def test_global_filters_dates_and_signed_keyset(self):
        tid=self.tid
        self.assertEqual(self.get('/observations')[0],200)
        self.assertEqual(rfc3339('2024-03-31T03:00:00+02:00'),rfc3339('2024-03-31T01:00:00Z'))
        self.assertEqual(rfc3339('2024-10-27T02:30:00+02:00')+3600000,rfc3339('2024-10-27T02:30:00+01:00'))
        for i in range(7):self.new_trip('Page '+str(i))
        first=self.get('/trips?limit=2')[1]['data'];cursor=first['page']['next_cursor'];self.assertTrue(cursor)
        ids={r['id'] for r in first['items']}
        while cursor:
            data=self.get('/trips?'+urlencode({'limit':2,'cursor':cursor}))[1]['data']
            self.assertFalse(ids&{r['id'] for r in data['items']});ids.update(r['id'] for r in data['items']);cursor=data['page']['next_cursor']
        self.assertEqual(len(ids),9)
        cursor=first['page']['next_cursor']
        for q in [{'cursor':cursor,'sort':'asc'},{'cursor':cursor,'status':'COMPLETE'},{'cursor':cursor+'x'}]:self.assertEqual(self.get('/trips?'+urlencode(q))[0],400)
        self.use('other');self.assertEqual(self.get('/trips?'+urlencode({'cursor':cursor}))[0],400)
        self.use('driver');self.now+=900000;self.assertEqual(self.get('/trips?'+urlencode({'cursor':cursor}))[0],400)
        self.now-=900000
        for query in [{'from':'1700000000000'},{'from':'2023-01-01T00:00:00'},{'from':'2023-01-01T00:00:00Z','to':'2025-01-01T00:00:00Z'}]:self.assertEqual(self.get('/trips?'+urlencode(query))[0],422)
        data=self.get('/observations?'+urlencode({'source':'MANUAL','valid':'true','state':'GREEN','event_type':'STATE_SEEN','signal_id':'synthetic-light','trip_id':tid}))[1]['data']
        self.assertEqual(len(data['items']),1)

    def test_all_filters_boundaries_routes_corrections_and_share_pages(self):
        admin=Actor(self.users['admin']['id'],self.now)
        config=self.repo.create_config(admin,'ROUTE','test-route',{'stop_lines':[{'stop_line_id':'line'}]})
        config=self.repo.publish_config(admin,config['id'],config['revision'])
        trip=self.post('/trips',{'title':'Route','mode':'SIMULATION','route_version_id':config['id']})[1]['data']
        nav=self.start(trip)
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',{'signal_id':'bad','state':'RED','event_type':'STATE_SEEN','source_event_id':'x'})[0],422)
        self.now+=1000
        body={'signal_id':'line','state':'RED','event_type':'STATE_SEEN','source_event_id':'one'}
        oid=self.post('/trips/'+trip['id']+'/observations',body)[1]['data']['id']
        self.now+=1000;self.post('/trips/'+trip['id']+'/observations',{**body,'source_event_id':'two'})
        self.assertEqual(self.finish(nav)[0],200)
        self.post('/observations/'+oid+'/corrections',{'expected_revision':0,'client_operation_id':'p'*32,'changes':{'state':'GREEN','event_type':'STATE_START','valid':False},'reason':'Correct historical interpretation'})
        dates={'from':'2023-11-14T22:13:21Z','to':'2023-11-14T22:13:22Z'}
        filters={**dates,'route_id':config['logical_id'],'trip_id':trip['id'],'signal_id':'line','state':'GREEN','event_type':'STATE_START','source':'MANUAL','valid':'false'}
        items=self.get('/observations?'+urlencode(filters))[1]['data']['items'];self.assertEqual([r['id'] for r in items],[oid])
        self.assertEqual(items[0]['original']['state'],'RED')
        self.assertEqual(self.get('/trips?'+urlencode({'route_id':config['logical_id'],'status':'COMPLETE','sort':'asc'}))[1]['data']['items'][0]['id'],trip['id'])
        self.post('/trips/'+trip['id']+'/share',{'analyst_email':'analyst@example.test'})
        self.use('analyst');first=self.get('/observations?'+urlencode({'scope':'shared','limit':1,'trip_id':trip['id']}))[1]['data'];cursor=first['page']['next_cursor'];self.assertTrue(cursor)
        self.use('driver')
        with self.db.connection() as c:sid=c.execute('SELECT id FROM trip_shares WHERE trip_id=? AND revoked_at IS NULL',(trip['id'],)).fetchone()[0]
        self.request('DELETE',PREFIX+'/trips/'+trip['id']+'/share',{'expected_share_id':sid})
        self.use('analyst');self.assertEqual(self.get('/observations?'+urlencode({'scope':'shared','limit':1,'trip_id':trip['id'],'cursor':cursor}))[0],404)

    def test_history_larger_than_ten_thousand_no_cutoff(self):
        owner=self.users['driver']['id']
        with self.db.transaction() as c:
            c.executemany("INSERT INTO trips(id,owner_id,title,note,mode,status,created_at) VALUES(?,?,?,'','SIMULATION','PLANNED',?)",[(f'{i:032x}',owner,'bulk',self.now) for i in range(10005)])
        seen=set();cursor=None
        while True:
            q={'limit':100}
            if cursor:q['cursor']=cursor
            status,data,_=self.get('/trips?'+urlencode(q));self.assertEqual(status,200)
            ids={row['id'] for row in data['data']['items']};self.assertFalse(seen&ids);seen|=ids
            cursor=data['data']['page']['next_cursor']
            if not cursor:break
        self.assertEqual(len(seen),10007)

    def test_cursor_as_of_and_mutable_filter_membership(self):
        for _ in range(5):self.new_trip()
        first=self.get('/trips?limit=1')[1]['data'];cursor=first['page']['next_cursor']
        self.now+=1000;new=self.new_trip('New after cursor')
        remaining=[]
        while cursor:
            data=self.get('/trips?'+urlencode({'limit':100,'cursor':cursor}))[1]['data'];remaining+=data['items'];cursor=data['page']['next_cursor']
        self.assertNotIn(new['id'],[r['id'] for r in remaining])

    def test_proactive_share_invalidation_preserves_owner_job_management(self):
        contexts=self.server.resources.contexts;gate=threading.Event();started=[threading.Event(),threading.Event()];finished=threading.Event()
        def block(index):started[index].set();gate.wait(10)
        for i in range(2):contexts.pool.submit(block,i)
        self.addCleanup(gate.set)
        for event in started:self.assertTrue(event.wait(3))
        self.use('analyst');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        original=contexts.execute
        def execute(*args):
            try:return original(*args)
            finally:finished.set()
        with patch.object(contexts,'execute',execute),patch('greenwave.school_resources.contexts.RunAnalysis.analyze') as analyze:
            jid=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[1]['data']['id']
            self.use('driver');self.assertEqual(self.request('DELETE',PREFIX+'/trips/'+self.tid+'/share',{'expected_share_id':self.fixture['share']})[0],204)
            self.assertNotIn(hid,contexts.replays);self.assertTrue(contexts.jobs[jid]['authorization_invalid'])
            self.assertEqual(contexts.jobs[jid]['status'],'CANCELLED')
            self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
            self.post('/trips/'+self.tid+'/share',{'analyst_email':'analyst@example.test'})
            self.use('analyst');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],404);self.assertEqual(self.get('/replays/'+hid)[0],404)
            gate.set();self.assertTrue(finished.wait(3));analyze.assert_not_called()

    def test_restart_pending_journal_and_manifest_recovery_without_raw_mutation(self):
        rec=self.server.resources.recorder;trip=self.new_trip();nav=self.start(trip)
        rec.fault=lambda point:(_ for _ in ()).throw(RuntimeError('DB checkpoint failure')) if point=='journal-written' else None
        body={'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'restart'}
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',body)[0],500)
        # Simulated process loss: close stream without finalization; construct a new coordinator.
        ctx=rec.contexts.pop(nav['id']);ctx['logger'].close_unfinished();before=self.raw_path(trip['id']).read_bytes()
        from greenwave.school_records.recording import Recording
        recovered=Recording(self.server.resources.policy);self.addCleanup(recovered.close)
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'INTERRUPTED')
        items=self.get('/observations?'+urlencode({'trip_id':trip['id']}))[1]['data']['items'];self.assertEqual(items[0]['journaling_state'],'APPLIED')
        self.assertEqual(self.raw_path(trip['id']).read_bytes(),before)
        with self.db.connection() as c:self.assertEqual(c.execute("SELECT state FROM recording_operations WHERE trip_id=? AND kind='JOURNAL_OBSERVATION'",(trip['id'],)).fetchone()[0],'APPLIED')
        self.assertEqual(self.get('/trips/'+trip['id']+'/export')[0],409)

    def test_corrupt_manifest_recovery_and_read_fail_closed(self):
        trip=self.new_trip();nav=self.start(trip);rec=self.server.resources.recorder
        rec.fault=lambda point:(_ for _ in ()).throw(OSError('Lost DB completion')) if point=='finish-commit' else None
        self.assertEqual(self.finish(nav)[0],503)
        ctx=rec.contexts.pop(nav['id']);ctx['logger'].close_unfinished()
        raw=self.raw_path(trip['id']);raw.write_bytes(raw.read_bytes()+b'CORRUPT');before=raw.read_bytes()
        rec.fault=lambda _:None;rec.recover()
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'INTERRUPTED')
        self.assertEqual(raw.read_bytes(),before);self.assertEqual(self.get('/trips/'+trip['id']+'/export')[0],409)

    def test_atomic_audit_and_original_history_trigger(self):
        raw=self.cookies['gw_session']
        from greenwave.school_data import Repository
        with patch.object(Repository,'audit',side_effect=RuntimeError('Synthetic audit failure')):
            self.assertEqual(self.post('/trips',{'title':'Should rollback','mode':'SIMULATION'})[0],500)
        with self.db.connection() as c:self.assertEqual(c.execute("SELECT count(*) FROM trips WHERE title='Should rollback'").fetchone()[0],0)
        trip=self.new_trip();nav=self.start(trip);self.finish(nav)
        oid=self.post('/trips/'+trip['id']+'/observations',{'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'history'})[1]['data']['id']
        from greenwave.school_data.errors import Conflict
        with self.assertRaises(Conflict):
            with self.db.transaction() as c:c.execute("UPDATE observations SET historical=0,journaling_state='FAILED' WHERE id=?",(oid,))

    def test_real_http_acceptance_script_and_server_restart(self):
        from scripts.check_school_records import run,Client
        import contextlib,io
        with contextlib.redirect_stdout(io.StringIO()):tid=run(self.cfg.base_url,PASS)
        # New server/service adapters with the same prepared DB, new boot, new sessions.
        self.server.shutdown();self.server.server_close()
        from greenwave.school_accounts.http import AccountsHTTPServer
        fresh=AccountsHTTPServer(('127.0.0.1',self.cfg.port),self.service)
        thread=threading.Thread(target=fresh.serve_forever,daemon=True);thread.start()
        self.addCleanup(fresh.server_close);self.addCleanup(fresh.shutdown)
        client=Client(self.cfg.base_url);client.login('driver@example.test',PASS)
        self.assertIsNotNone(client.call('GET','/trips/'+tid)['archived_at'])

    def test_observation_checkpoint_db_failure_is_idempotent_on_restart(self):
        import sqlite3
        trip=self.new_trip();nav=self.start(trip);rec=self.server.resources.recorder
        rec.fault=lambda point:(_ for _ in ()).throw(sqlite3.OperationalError('DB failure after raw')) if point=='journal-written' else None
        body={'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'db-failure'}
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',body)[0],503)
        ctx=rec.contexts.pop(nav['id']);ctx['logger'].close_unfinished();before=self.raw_path(trip['id']).read_bytes()
        rec.fault=lambda _:None;rec.recover()
        rows=self.get('/observations?'+urlencode({'trip_id':trip['id']}))[1]['data']['items'];self.assertEqual(rows[0]['journaling_state'],'APPLIED')
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',body)[1]['data']['id'],rows[0]['id'])
        self.assertEqual(self.raw_path(trip['id']).read_bytes(),before)

    def test_filesystem_append_and_finish_failures_preserve_fact(self):
        trip=self.new_trip();nav=self.start(trip);rec=self.server.resources.recorder;logger=rec.contexts[nav['id']]['logger']
        with patch.object(logger,'append',return_value=False):
            status,data,_=self.post('/trips/'+trip['id']+'/observations',{'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'failed'})
            self.assertEqual(status,202);self.assertEqual(data['data']['journaling_state'],'FAILED')
        # A finish unable to write its RUN_END does not create a fake manifest.
        with patch.object(logger,'finish',return_value=None):self.assertEqual(self.finish(nav)[0],409)
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'INTERRUPTED')
        with self.db.connection() as c:self.assertEqual(c.execute('SELECT count(*) FROM observations WHERE trip_id=?',(trip['id'],)).fetchone()[0],1)

    def test_rate_limit_and_neutral_sharing_recipient(self):
        errors=[]
        for address in ['missing@example.test','other@example.test','admin@example.test']:
            status,data,_=self.post('/trips/'+self.tid+'/share',{'analyst_email':address});self.assertEqual(status,422);errors.append(data['error'])
        self.assertEqual(errors[0],errors[1]);self.assertEqual(errors[1],errors[2])
        for _ in range(7):self.assertEqual(self.post('/trips/'+self.tid+'/share',{'analyst_email':'missing@example.test'})[0],422)
        status,_,headers=self.post('/trips/'+self.tid+'/share',{'analyst_email':'missing@example.test'});self.assertEqual(status,429);self.assertIn('Retry-After',dict(headers))

    def test_unbound_active_trip_recovery_never_reads_files(self):
        trip=self.new_trip();actor=Actor(self.users['driver']['id'])
        self.repo.transition_trip(actor,trip['id'],trip['revision'],'STARTING',run_id='e'*32)
        rec=self.server.resources.recorder
        with patch.object(rec.raw,'validate') as validate:rec.recover();validate.assert_not_called()
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'INTERRUPTED')

    def test_logout_all_change_password_and_idle_finalize(self):
        for action in ['logout-all','change-password','idle']:
            self.cookies={};self.preflight();_,data,_=self.auth('login',{'email':'driver@example.test','password':PASS});self.csrf=data['data']['csrf']
            trip=self.new_trip(action);self.start(trip,key=hashlib.sha256(action.encode()).hexdigest())
            if action=='logout-all':self.assertEqual(self.auth('logout-all',{})[0],204)
            elif action=='change-password':self.assertEqual(self.auth('change-password',{'current_password':PASS,'new_password':PASS,'password_confirmation':PASS})[0],200)
            else:self.now+=1800000;self.server.resources.recorder.reconcile_credentials()
            with self.db.connection() as c:self.assertEqual(c.execute('SELECT status FROM trips WHERE id=?',(trip['id'],)).fetchone()[0],'COMPLETE')

    def test_controlled_logger_compatibility_and_close_unfinished(self):
        import tempfile
        from greenwave.telemetry import RunLogger
        from greenwave.school_records.raw import utc
        with tempfile.TemporaryDirectory() as root:
            logger=RunLogger(root)
            with self.assertRaises(ValueError):logger.start({},run_id='../escape')
            logger.start({'start_time':utc(self.now)},run_id='a'*32)
            logger.append('RUN_START',timestamp=utc(self.now),simulation_seconds=0,model_seconds=0)
            logger.close_unfinished()
            from pathlib import Path
            self.assertFalse((Path(root)/('a'*32)/'complete.json').exists())
            self.assertFalse(logger.active)

    def test_partial_raw_pending_fact_recovery_is_failed_not_repaired(self):
        import sqlite3
        trip=self.new_trip();nav=self.start(trip);rec=self.server.resources.recorder
        rec.fault=lambda point:(_ for _ in ()).throw(sqlite3.OperationalError('checkpoint failure')) if point=='journal-written' else None
        self.post('/trips/'+trip['id']+'/observations',{'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'partial'})
        ctx=rec.contexts.pop(nav['id']);ctx['logger'].close_unfinished();raw=self.raw_path(trip['id'])
        raw.write_bytes(raw.read_bytes()+b'partial,broken');before=raw.read_bytes();rec.fault=lambda _:None;rec.recover()
        self.assertEqual(raw.read_bytes(),before)
        with self.db.connection() as c:
            self.assertEqual(c.execute('SELECT journaling_state FROM observations WHERE trip_id=?',(trip['id'],)).fetchone()[0],'FAILED')
            self.assertEqual(c.execute("SELECT state FROM recording_operations WHERE trip_id=? AND kind='JOURNAL_OBSERVATION'",(trip['id'],)).fetchone()[0],'FAILED')

    def test_concurrent_correction_revision_and_historical_no_measurement(self):
        trip=self.new_trip();nav=self.start(trip);self.finish(nav)
        obsbody={'signal_id':'x','state':'RED','event_type':'STATE_SEEN','source_event_id':'history'}
        self.assertEqual(self.post('/trips/'+trip['id']+'/observations',{**obsbody,'measured_at':self.now})[0],422)
        oid=self.post('/trips/'+trip['id']+'/observations',obsbody)[1]['data']['id']
        raw=self.cookies['gw_session'];barrier=threading.Barrier(2)
        def change(key):
            barrier.wait()
            try:self.server.resources.writes.correct(raw,oid,{'expected_revision':0,'client_operation_id':key*32,'changes':{'state':'GREEN'},'reason':'race'},'race');return 'OK'
            except Exception as error:return type(error).__name__
        with concurrent.futures.ThreadPoolExecutor(2) as pool:self.assertCountEqual(list(pool.map(change,['a','b'])),['OK','Conflict'])

    def test_malformed_manifest_shapes_do_not_abort_recovery(self):
        rec=self.server.resources.recorder
        for index,(name,value) in enumerate([('complete.json',[]),('metadata.json',[]),('complete.json',{'sha256':None})]):
            trip=self.new_trip();nav=self.start(trip,key=str(index)*32)
            rec.fault=lambda point:(_ for _ in ()).throw(OSError('lost final commit')) if point=='finish-commit' else None
            self.assertEqual(self.finish(nav,key=str(index+3)*32)[0],503)
            ctx=rec.contexts.pop(nav['id']);ctx['logger'].close_unfinished()
            path=self.raw_path(trip['id']).parent/name;path.write_text(json.dumps(value),encoding='utf-8');before=path.read_bytes()
            rec.fault=lambda _:None;rec.recover()
            self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'INTERRUPTED');self.assertEqual(path.read_bytes(),before)
