import json
import threading
import http.client
from unittest.mock import patch
from greenwave.analysis import RunAnalysis
from concurrent.futures import ThreadPoolExecutor
from test_school_resources import ResourceFixture
from test_school_accounts import PREFIX,PASS
from greenwave.school_data import Actor
from greenwave.school_data.errors import Conflict
from greenwave.school_admin.validation import payload
from greenwave.school_accounts.errors import AuthError

MODEL={'schema_version':1,'settings':{'horizon_seconds':240},'relations':[]}
ROUTE={'schema_version':1,'route_id':'synthetic','geometry_version':'v1','name':'Demo','direction_description':'North','source':{'attribution':'Synthetic'},'coordinates':[[21,52],[21.001,52.001]]}
SIGNAL={'schema_version':1,'id':'demo','name':'Demo','direction':'N','speed_limit_mps':10,'signals':[{'id':'a','name':'A','direction':'N','movement':'STRAIGHT','signal_type':'FIXED_TIME','road_position_m':100,'cycle_seconds':60,'green_duration':20,'offset':0,'yellow_duration':3,'latitude':52,'longitude':21,'confidence':None,'source':'synthetic','notes':''}]}

class AdminTests(ResourceFixture):
    # Inherit fixtures/helpers, not the resource suite again.
    def reauth(self):
        self.reauth_count=getattr(self,'reauth_count',0)+1
        if self.reauth_count%5==0:self.now+=900001
        self.use('admin');status,data,_=self.auth('reauth',{'password':PASS});self.assertEqual(status,200)
        self.credentials['admin']=(dict(self.cookies),data['data']['csrf']);self.csrf=data['data']['csrf']
    def patch(self,path,body,headers=None):return self.request('PATCH',PREFIX+path,body,headers)
    def change(self,who,**values):
        row=self.repo.get_user(self.users[who]['id'])
        return self.patch('/admin/users/'+row['id'],{'expected_revision':row['revision'],'reason':'Synthetic administrative change',**values})
    def test_admin_matrix_reauth_dto_and_audit(self):
        for who,status in [(None,401),('driver',403),('analyst',403),('admin',200)]:
            self.use(who);self.assertEqual(self.get('/admin/users')[0],status);self.assertEqual(self.get('/admin/audit')[0],status)
        self.now+=300001;self.use('admin');self.assertEqual(self.change('other',role='ANALYST')[0],403)
        self.reauth();status,data,_=self.get('/admin/users?limit=2');self.assertEqual(status,200)
        self.assertTrue(data['data']['page']['next_cursor'])
        self.assertNotIn('password_hash',json.dumps(data));self.assertNotIn('security_version',json.dumps(data))
        self.assertEqual(self.change('other',role='ANALYST')[0],200)
        status,data,_=self.get('/admin/audit');self.assertEqual(status,200)
        self.assertNotIn('OBSERVATION',json.dumps(data));self.assertNotIn('raw_ref',json.dumps(data))
        self.assertTrue(any(r['reason']=='Synthetic administrative change' for r in data['data']['items']))
        self.assertEqual(self.get('/admin/audit?action=OBSERVATION_CORRECTED')[0],422)
    def test_block_unblock_revoke_and_pending(self):
        self.reauth();self.assertEqual(self.change('analyst',status='BLOCKED')[0],200)
        self.use('analyst');self.assertEqual(self.get('/trips?scope=shared')[0],401)
        self.reauth();self.assertEqual(self.change('analyst',status='ACTIVE')[0],200)
        self.use('analyst');self.assertEqual(self.get('/trips?scope=shared')[0],401)
        self.preflight();status,data,_=self.auth('login',{'email':'analyst@example.test','password':PASS});self.assertEqual(status,200)
        self.assertEqual(self.get('/trips?scope=shared')[1]['data']['items'],[])
        pending=self.repo.create_user('pending@example.test','Pending','fixture')
        self.reauth();self.assertEqual(self.patch('/admin/users/'+pending['id'],{'expected_revision':1,'status':'ACTIVE','reason':'No verification shortcut'})[0],422)
    def test_last_admin_revision_spoof_and_csrf(self):
        self.reauth();self.assertEqual(self.change('admin',role='DRIVER')[0],409)
        self.assertEqual(self.change('other',role='BAD')[0],422)
        target=self.users['other']['id'];body={'expected_revision':1,'role':'ANALYST','reason':'Good reason'}
        self.assertEqual(self.patch('/admin/users/'+target,{**body,'reauth_at':self.repo.clock()})[0],422)
        self.assertEqual(self.patch('/admin/users/'+target,body,{'X-CSRF-Token':'bad'})[0],403)
        self.assertEqual(self.patch('/admin/users/'+target,body,{'Origin':'https://other.test'})[0],403)
        self.assertEqual(self.patch('/admin/users/'+target,body)[0],200)
        self.assertEqual(self.patch('/admin/users/'+target,body)[0],409)
    def test_last_admin_concurrent_and_self_session(self):
        second=self.repo.create_user('second@example.test','Second','fixture',role='ADMIN',status='ACTIVE',verified_at=self.repo.clock())
        barrier=threading.Barrier(2)
        def demote(uid):
            barrier.wait()
            try:self.repo.change_account(Actor(uid,self.repo.clock()),uid,1,role='DRIVER');return 200
            except Conflict:return 409
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(demote,[second['id'],self.users['admin']['id']]))
        self.assertEqual(sorted(results),[200,409])
        with self.repo.database.connection() as c:self.assertEqual(c.execute("SELECT count(*) FROM users WHERE role='ADMIN' AND status='ACTIVE'").fetchone()[0],1)
    def test_config_all_kinds_validation_ownership_publication(self):
        for kind,body in [('MODEL',MODEL),('ROUTE',ROUTE),('SIGNAL',SIGNAL)]:
            self.use('driver');self.assertEqual(self.post('/config/versions',{'kind':kind,'logical_id':'demo','payload':body,'reason':'Synthetic draft'})[0],403)
            self.use('analyst');status,data,_=self.post('/config/versions',{'kind':kind,'logical_id':'demo','payload':body,'reason':'Synthetic draft'});self.assertEqual(status,201,data);row=data['data']
            self.assertEqual(self.post('/config/versions/'+row['id']+'/publish',{'expected_revision':1,'reason':'Publish synthetic'})[0],403)
            self.reauth();status,data,_=self.post('/config/versions/'+row['id']+'/publish',{'expected_revision':1,'reason':'Publish synthetic'});self.assertEqual(status,200,data)
            self.assertFalse(data['data']['publication_is_field_verification'])
            self.assertEqual(self.patch('/config/versions/'+row['id'],{'expected_revision':1,'payload':body,'reason':'Cannot edit published'})[0],409)
            self.use('driver');self.assertEqual(self.get('/config/versions/'+row['id'])[0],200)
            self.reauth();self.assertEqual(self.request('DELETE',PREFIX+'/config/versions/'+row['id'],{'reason':'Archive synthetic'})[0],204)
            self.use('driver');self.assertEqual(self.get('/config/versions/'+row['id'])[0],403)
        self.reauth();status,data,_=self.post('/config/versions',{'kind':'MODEL','logical_id':'admin-draft','payload':MODEL,'reason':'Admin draft'});cid=data['data']['id']
        self.use('analyst');self.assertEqual(self.patch('/config/versions/'+cid,{'expected_revision':1,'payload':MODEL,'reason':'Foreign draft'})[0],404)
        for bad in [{**MODEL,'verified':True},{**MODEL,'settings':{'horizon_seconds':True}},{**MODEL,'relations':[{'verified':True}]},{**MODEL,'path':'/tmp/data'}, {**MODEL,'settings':{'horizon_seconds':601}}]:
            self.assertEqual(self.post('/config/versions',{'kind':'MODEL','logical_id':'bad','payload':bad,'reason':'Bad draft'})[0],422)
        for bad in [{**ROUTE,'coordinates':[[21,52],[21,52]]},{**SIGNAL,'signals':[{**SIGNAL['signals'][0],'green_duration':60}]}, {**ROUTE,'stop_lines':[{'verification':'FIELD_CHECKED'}]}]:
            with self.assertRaises(AuthError):payload('ROUTE' if 'coordinates' in bad else 'SIGNAL',bad)

    def test_configuration_snapshot_revision_and_nested_rules(self):
        self.use('analyst');status,data,_=self.post('/config/versions',{'kind':'ROUTE','logical_id':'snapshot','payload':ROUTE,'reason':'Initial route'});self.assertEqual(status,201);cid=data['data']['id']
        self.reauth();self.assertEqual(self.post('/config/versions/'+cid+'/publish',{'expected_revision':1,'reason':'Publish route'})[0],200)
        self.use('driver');status,data,_=self.post('/trips',{'title':'Snapshot trip','note':'','mode':'SIMULATION','route_version_id':cid});self.assertEqual(status,201)
        tid=data['data']['id']
        status,data,_=self.request('POST',PREFIX+'/navigation',{'trip_id':tid},headers={'Idempotency-Key':'snapshot-start-000000000000000000'});self.assertEqual(status,201);navigation=data['data']
        self.assertEqual(self.post('/navigation/'+navigation['id']+'/control',{'command':'FINISH','expected_revision':navigation['revision']})[0],422)  # Key required.
        status,data,_=self.request('POST',PREFIX+'/navigation/'+navigation['id']+'/control',{'command':'FINISH','expected_revision':navigation['revision']},headers={'Idempotency-Key':'snapshot-finish-00000000000000000'});self.assertEqual(status,200,data)
        before=self.repo.get_trip(Actor(self.users['driver']['id']),tid)
        runroot=self.storage.run(before['owner_id'],tid,before['run_id']);metadata=(runroot/'metadata.json').read_bytes();raw=(runroot/'raw.csv').read_bytes()
        self.assertEqual(json.loads(metadata)['school_route_snapshot']['version_id'],cid)
        self.use('analyst');status,data,_=self.post('/config/versions',{'kind':'ROUTE','logical_id':'snapshot','base_version_id':cid,'payload':{**ROUTE,'name':'New route'},'reason':'New route version'});new=data['data']
        self.assertEqual(self.patch('/config/versions/'+new['id'],{'expected_revision':1,'payload':ROUTE,'reason':'Edit route'})[0],200)
        self.assertEqual(self.patch('/config/versions/'+new['id'],{'expected_revision':1,'payload':ROUTE,'reason':'Stale revision'})[0],409)
        self.reauth();self.assertEqual(self.post('/config/versions/'+new['id']+'/publish',{'expected_revision':2,'reason':'Publish new route'})[0],200)
        self.assertEqual(self.request('DELETE',PREFIX+'/config/versions/'+cid,{'reason':'Archive old route'})[0],204)
        self.assertEqual(before,self.repo.get_trip(Actor(self.users['driver']['id']),tid))
        self.assertEqual(metadata,(runroot/'metadata.json').read_bytes());self.assertEqual(raw,(runroot/'raw.csv').read_bytes())
        self.use('analyst')
        bads=[('MODEL',{**MODEL,'relations':[{'source_signal_id':'a','target_signal_id':'a','green_start_delta_seconds':0,'uncertainty_seconds':0,'source':'test'}]}),
          ('SIGNAL',{**SIGNAL,'speed_limit_mps':True}),('SIGNAL',{**SIGNAL,'signals':[{**SIGNAL['signals'][0],'name':{}}]}),
          ('ROUTE',{**ROUTE,'coordinates':[[True,52],[21,52]]}),('ROUTE',{**ROUTE,'source':{'attribution':'file:///private'}}),
          ('ROUTE',{**ROUTE,'speed_sections':[{'start_s_m':0,'end_s_m':1,'limit_mps':10,'source':{'attribution':'Synthetic'},'verified':True}]})]
        for kind,value in bads:self.assertEqual(self.post('/config/versions',{'kind':kind,'logical_id':'bad','payload':value,'reason':'Bad config'})[0],422)
    def test_admin_change_finalizes_recording_and_self_revocation(self):
        self.use('driver');status,data,_=self.post('/trips',{'title':'Recording','note':'','mode':'SIMULATION'});self.assertEqual(status,201);tid=data['data']['id']
        status,data,_=self.request('POST',PREFIX+'/navigation',{'trip_id':tid},headers={'Idempotency-Key':'admin-revoke-recording-000000000000'});self.assertEqual(status,201,data)
        self.reauth();self.assertEqual(self.change('driver',status='BLOCKED')[0],200)
        with self.repo.database.connection() as c:
            trip=c.execute('SELECT status FROM trips WHERE id=?',(tid,)).fetchone();self.assertIn(trip['status'],{'COMPLETE','INTERRUPTED'})
        self.use('driver');self.assertEqual(self.get('/trips')[0],401)
        self.reauth();self.assertEqual(self.change('other',role='ADMIN')[0],200)
        self.assertEqual(self.change('admin',role='DRIVER')[0],200)
        self.assertEqual(self.get('/admin/users')[0],401)
    def test_admin_http_concurrent_last_admin(self):
        self.reauth();self.assertEqual(self.change('other',role='ADMIN')[0],200)
        self.cookies={};self.preflight();status,data,_=self.auth('login',{'email':'other@example.test','password':PASS});self.assertEqual(status,200)
        self.credentials['other']=(dict(self.cookies),data['data']['csrf'])
        barrier=threading.Barrier(2)
        def change(who):
            cookies,csrf=self.credentials[who];body=json.dumps({'expected_revision':self.repo.get_user(self.users[who]['id'])['revision'],'role':'DRIVER','reason':'Concurrent demotion'})
            barrier.wait();connection=http.client.HTTPConnection('127.0.0.1',self.cfg.port)
            connection.request('PATCH',PREFIX+'/admin/users/'+self.users[who]['id'],body,{'Cookie':'; '.join(k+'='+v for k,v in cookies.items()),'Content-Type':'application/json','Origin':self.cfg.origin,'X-CSRF-Token':csrf})
            response=connection.getresponse();status=response.status;response.read();connection.close();return status
        with ThreadPoolExecutor(2) as pool:result=list(pool.map(change,['admin','other']))
        self.assertEqual(sorted(result),[200,409])


    def test_block_cancels_running_analysis_and_removes_replay(self):
        self.use('analyst');status,data,_=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'});self.assertEqual(status,201);hid=data['data']['id']
        entered,release,finished=threading.Event(),threading.Event(),threading.Event();original=RunAnalysis.analyze
        def held(analysis,run_id):
            result=original(analysis,run_id);entered.set();self.assertTrue(release.wait(10));return result
        contexts=self.server.resources.contexts;execute=contexts.execute
        def signal(raw,job):
            try:execute(raw,job)
            finally:finished.set()
        with patch.object(RunAnalysis,'analyze',held),patch.object(contexts,'execute',signal):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'});self.assertEqual(status,202);jid=data['data']['id']
            try:
                self.assertTrue(entered.wait(10));job=contexts.jobs[jid];basis=job['authorization'];identity=(job['actor_id'],job['credential'],job['session_id'])
                self.reauth();self.assertEqual(self.change('analyst',status='BLOCKED')[0],200)
                self.assertNotIn(hid,contexts.replays);self.assertEqual(job['status'],'CANCELLED')
                self.use('driver');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
                self.assertEqual(identity,(job['actor_id'],job['credential'],job['session_id']));self.assertEqual(basis,job['authorization'])
            finally:release.set()
            self.assertTrue(finished.wait(10));self.assertIsNone(job['report_id'])
        self.reauth();self.assertEqual(self.change('analyst',status='ACTIVE')[0],200)
        self.use('analyst');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],401)
    def test_audit_projection_cursor_and_source_url_metadata(self):
        with self.repo.database.transaction() as c:
            self.repo.audit(c,Actor(self.users['driver']['id']),'AUTH_LOGIN','TRIP',self.tid,'private GPS note')
            self.repo.audit(c,Actor(self.users['driver']['id']),'AUTH_LOGIN','USER',self.users['driver']['id'],'private note hidden')
        self.use('admin');status,data,_=self.get('/admin/audit?limit=1');self.assertEqual(status,200)
        self.assertNotIn('private',json.dumps(data));cursor=data['data']['page']['next_cursor'];self.assertTrue(cursor)
        self.assertEqual(self.get('/admin/audit?limit=1&cursor='+cursor)[0],200)
        self.assertEqual(self.get('/admin/audit?limit=1&action=AUTH_LOGIN&cursor='+cursor)[0],400)
        self.use('analyst');with_url={**ROUTE,'source':{'attribution':'Synthetic','url':'https://example.test/source','description':'Metadata only'}}
        with patch('urllib.request.urlopen',side_effect=AssertionError('Never fetch source')):
            status,data,_=self.post('/config/versions',{'kind':'ROUTE','logical_id':'url-metadata','payload':with_url,'reason':'Source metadata only'})
        self.assertEqual(status,201,data);self.assertEqual(data['data']['payload']['source']['url'],'https://example.test/source')
        for bad in [{**ROUTE,'url':'https://example.test'}, {**ROUTE,'source':{'attribution':'Synthetic','url':'https://user:secret@example.test'}}]:
            self.assertEqual(self.post('/config/versions',{'kind':'ROUTE','logical_id':'bad','payload':bad,'reason':'Bad metadata'})[0],422)
