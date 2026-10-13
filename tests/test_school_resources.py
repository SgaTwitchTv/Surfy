import hashlib
import io
import json
import time
import unittest
import zipfile
from unittest.mock import patch
from greenwave.school_data import Actor
from greenwave.school_accounts.errors import AuthError
from greenwave.school_resources.policy import Policy
from test_school_accounts import Fixture, PASS, NEW, PREFIX
from scripts.school_resource_fixtures import populate


class ResourceFixture(Fixture):
    def setUp(self):
        super().setUp()
        self.fixture=populate(self.repo,self.service.passwords.hash(PASS))
        self.users=self.fixture['users'];self.trips=self.fixture['trips']
        self.tid=self.trips['shared']['id'];self.private=self.trips['private']['id']
        self.oid=self.fixture['observations']['shared']['id'];self.cid=self.fixture['captures']['shared']
        self.credentials={}
        for who in self.users:
            self.cookies={}
            self.preflight();status,data,_=self.auth('login',{'email':who+'@example.test','password':PASS})
            self.assertEqual(status,200)
            self.credentials[who]=(dict(self.cookies),data['data']['csrf'])
        self.use(None)

    def use(self,who):
        self.cookies,self.csrf=({},{}) if who is None else (dict(self.credentials[who][0]),self.credentials[who][1])
        if who is None:self.csrf=''

    def get(self,path):
        if path.endswith('/export'):
            import http.client
            c=http.client.HTTPConnection('127.0.0.1',self.cfg.port)
            c.request('GET',PREFIX+path,headers={'Cookie':'; '.join(k+'='+v for k,v in self.cookies.items())})
            r=c.getresponse();status=r.status;data=r.read();headers=r.getheaders();c.close()
            return status,data,headers
        return self.request('GET',PREFIX+path)
    def post(self,path,body):return self.request('POST',PREFIX+path,body)
    def delete(self,path):
        return self.request('DELETE',PREFIX+path,headers={'Content-Type':'application/json','Content-Length':'2',
            'Origin':self.cfg.origin,'X-CSRF-Token':self.csrf})

    def create_job(self,who='driver',tid=None):
        self.use(who);status,data,_=self.post('/trips/'+(tid or self.tid)+'/analysis-jobs',{'type':'GPS_QUALITY'})
        self.assertEqual(status,202);jid=data['data']['id']
        for _ in range(200):
            status,data,_=self.get('/analysis-jobs/'+jid)
            if data['data']['status'] not in {'QUEUED','RUNNING'}:break
            time.sleep(.01)
        self.assertEqual(data['data']['status'],'COMPLETE');return jid,data['data']['report_id']


class ResourceTests(ResourceFixture):
    def test_get_matrix_all_active_resource_endpoints(self):
        jid,rid=self.create_job()
        self.use('driver');status,data,_=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})
        self.assertEqual(status,201);hid=data['data']['id']
        readable=['/trips/'+self.tid,'/observations?trip_id='+self.tid,
                  '/observations/'+self.oid+'/corrections','/analysis-jobs/'+jid,
                  '/trips/'+self.tid+'/reports','/trips/'+self.tid+'/reports/'+rid]
        private=['/trips/'+self.tid+'/export','/trips/'+self.tid+'/cv/captures',
                 '/trips/'+self.tid+'/cv/captures/'+self.cid,
                 '/trips/'+self.tid+'/cv/captures/'+self.cid+'/events',
                 '/trips/'+self.tid+'/cv/captures/'+self.cid+'/media/0']
        for path in readable+private+['/replays/'+hid]:
            for who in [None,'driver','other','analyst','admin']:
                self.use(who)
                actual=path+('&scope=shared' if who=='analyst' and path.startswith('/observations?') else '')
                expected=401 if who is None else 200 if who=='driver' or (who=='analyst' and path in readable and not path.startswith('/analysis-jobs/')) else 404
                with self.subTest(path=actual,who=who):self.assertEqual(self.get(actual)[0],expected)
        for path in ['/trips','/config/versions','/config/versions/'+self.fixture['published']['id']]:
            for who in [None,*self.users]:
                self.use(who);self.assertEqual(self.get(path)[0],401 if who is None else 200)
        self.use('analyst')
        self.assertEqual(self.get('/trips/'+self.private)[0],404)
        items=self.get('/trips?scope=shared')[1]['data']['items']
        self.assertEqual([t['id'] for t in items],[self.tid])
        for who in ['driver','other','admin']:
            self.use(who);self.assertEqual(self.get('/trips?scope=shared')[0],403)

    def test_lists_filters_safe_dtos_and_configuration_roles(self):
        for who in self.users:
            self.use(who);items=self.get('/trips')[1]['data']['items']
            expected={t['id'] for t in self.trips.values() if t['owner_id']==self.users[who]['id']}
            self.assertEqual({t['id'] for t in items},expected)
            encoded=json.dumps(items)
            for secret in ['owner_id','raw_ref','manifest_hash','password_hash','token_hash',str(self.storage.root)]:self.assertNotIn(secret,encoded)
            result=self.get('/config/versions?status=DRAFT')[0]
            self.assertEqual(result,200 if who in {'analyst','admin'} else 403)
            self.assertEqual(self.get('/config/versions/'+self.fixture['draft']['id'])[0],200 if who in {'analyst','admin'} else 403)
        self.use('driver')
        rows=self.get('/observations?trip_id='+self.tid+'&state=GREEN')[1]['data']['items']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['effective']['state'],'GREEN')
        for q in ['limit=0','limit=101','offset=-1','from=NaN','from=true','from=1&to=1','owner_id=x','scope=all','limit=1&limit=2','cursor=x','status=BOGUS','archived=1']:
            self.assertEqual(self.get('/trips?'+q)[0],400 if q=='cursor=x' else 422,q)
        self.assertEqual(self.get('/observations')[0],200)
        self.assertEqual(self.get('/observations?trip_id='+self.tid+'&scope=shared')[0],403)
        self.assertEqual(self.get('/observations/'+self.oid+'/corrections?limit=1')[1]['data']['items'][0]['before']['state'],'RED')

    def test_export_manifest_integrity_and_no_raw_changes(self):
        self.use('driver');trip=self.trips['shared'];root=self.storage.run(trip['owner_id'],self.tid,trip['run_id'])
        before=hashlib.sha256((root/'raw.csv').read_bytes()).hexdigest()
        # HTTP binary inspected through a dedicated connection, never decoded as text.
        import http.client
        connection=http.client.HTTPConnection('127.0.0.1',self.cfg.port)
        connection.request('GET',PREFIX+'/trips/'+self.tid+'/export',headers={'Cookie':'gw_session='+self.cookies['gw_session']})
        response=connection.getresponse();self.assertEqual(response.status,200)
        archive=zipfile.ZipFile(io.BytesIO(response.read()));self.assertEqual(set(archive.namelist()),{'raw.csv','metadata.json','complete.json'})
        self.assertEqual(hashlib.sha256(archive.read('raw.csv')).hexdigest(),before);connection.close()
        (root/'raw.csv').write_bytes(b'CORRUPT SYNTHETIC FILE')
        self.assertEqual(self.get('/trips/'+self.tid+'/export')[0],409)
        self.assertEqual(self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[0],409)
        self.assertEqual(self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[0],409)

    def test_media_range_and_events_no_filename_leak(self):
        self.use('driver');path='/trips/'+self.tid+'/cv/captures/'+self.cid+'/media/0'
        status,data,headers=self.request('GET',PREFIX+path,headers={'Range':'bytes=0-8'})
        self.assertEqual(status,206);self.assertEqual(data,'SYNTHETIC');self.assertIn('Content-Range',dict(headers))
        for value in ['bytes=99-100','bytes=3-1','bytes=-4','bytes=0-1,4-5','items=0-1']:
            self.assertEqual(self.request('GET',PREFIX+path,headers={'Range':value})[0],416)
        for who in [None,'other','analyst','admin']:
            self.use(who);self.assertEqual(self.request('GET',PREFIX+path,headers={'Range':'bytes=0-8'})[0],401 if who is None else 404)
        self.use('driver');result=self.get('/trips/'+self.tid+'/cv/captures/'+self.cid+'/events')[1]['data']
        self.assertEqual(result['items'][0]['state'],'RED')
        for value in ['private-source-path','video.avi','media_ref','configuration']:
            self.assertNotIn(value,json.dumps(result));self.assertNotIn(value,json.dumps(self.get('/trips/'+self.tid+'/cv/captures/'+self.cid)[1]))

    def test_mutation_matrix_and_csrf_origin(self):
        for path,body in [('/trips/'+self.private+'/replays',{'mode':'GPS'}),('/trips/'+self.private+'/analysis-jobs',{'type':'GPS_QUALITY'})]:
            for who in [None,'driver','other','analyst','admin']:
                self.use(who);status=self.post(path,body)[0]
                self.assertEqual(status,401 if who is None else 201 if who=='driver' and path.endswith('replays') else 202 if who=='driver' else 404)
        self.use('driver');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        for path,body in [('/trips/'+self.tid+'/replays',{'mode':'GPS'}),('/replays/'+hid+'/control',{'command':'PLAY'}),('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})]:
            for header in [{'Origin':'http://evil.test'},{'X-CSRF-Token':'bad'}]:
                self.assertEqual(self.request('POST',PREFIX+path,body,header)[0],403)
        for body in [{'command':'SEEK','value':-1},{'command':'RATE','value':10},{'command':'RATE','value':True},{'command':'PLAY','owner_id':'fake'},{'command':'PLAY','value':1}]:
            self.assertEqual(self.post('/replays/'+hid+'/control',body)[0],422)
        self.assertEqual(self.post('/replays/'+hid+'/control',{'command':'SEEK','value':2})[0],200)
        self.assertEqual(self.post('/trips/'+self.tid+'/replays',{'mode':'SIMULATION'})[0],422)
        self.assertEqual(self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'MAPPING'})[0],422)

    def test_shared_replay_job_and_revocation_cuts_all_contexts(self):
        jid,rid=self.create_job('analyst')
        self.use('analyst');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        self.assertEqual(self.get('/replays/'+hid)[0],200)
        self.repo.revoke_share(Actor(self.users['driver']['id']),self.tid,self.fixture['share'])
        for path in ['/trips/'+self.tid,'/observations/'+self.oid+'/corrections','/replays/'+hid,'/analysis-jobs/'+jid,'/trips/'+self.tid+'/reports/'+rid]:
            self.assertEqual(self.get(path)[0],404,path)
        self.assertEqual(self.get('/trips?scope=shared')[1]['data']['items'],[])
        self.use('driver');self.assertEqual(self.get('/trips/'+self.tid+'/reports/'+rid)[0],200)

    def test_replay_session_binding_rotation_and_logout(self):
        self.use('driver');old=self.cookies['gw_session'];hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        self.preflight();status,data,_=self.auth('login',{'email':'driver@example.test','password':PASS});self.csrf=data['data']['csrf']
        self.assertEqual(self.get('/replays/'+hid)[0],404)
        hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        self.auth('reauth',{'password':PASS});self.assertEqual(self.get('/replays/'+hid)[0],404)
        self.csrf=self.get('/auth/me')[1]['data']['csrf']
        hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        self.auth('logout',{});self.assertEqual(self.get('/replays/'+hid)[0],401)
        self.assertEqual(self.request('GET',PREFIX+'/trips',headers={'Cookie':'gw_session='+old})[0],401)

    def test_block_role_archive_expiry_and_password_reset(self):
        self.use('analyst');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        admin=Actor(self.users['admin']['id'],self.now)
        self.repo.change_account(admin,self.users['analyst']['id'],1,role='DRIVER')
        self.assertEqual(self.get('/replays/'+hid)[0],401)
        self.use('other');self.repo.change_account(admin,self.users['other']['id'],1,status='BLOCKED')
        self.assertEqual(self.get('/trips')[0],401)
        self.use('driver');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        self.repo.archive_trip(Actor(self.users['driver']['id']),self.tid,self.trips['shared']['revision'])
        self.assertEqual(self.get('/replays/'+hid)[0],404)
        self.assertEqual(self.get('/trips?archived=true')[1]['data']['items'][0]['id'],self.tid)
        self.service.request_reset({'email':'driver@example.test'},'synthetic-ip');token=self.mail_token('reset')
        self.service.use_token({'token':token,'password':NEW,'password_confirmation':NEW},'synthetic-ip','RESET')
        self.assertEqual(self.get('/trips')[0],401)
        self.use('admin');self.now+=1800000;self.assertEqual(self.get('/trips')[0],401)

    def test_id_substitution_spoof_and_disabled_legacy(self):
        self.use('driver')
        for path in ['/trips/'+self.trips['other']['id'], '/observations/'+self.fixture['observations']['other']['id']+'/corrections',
                     '/trips/'+self.tid+'/cv/captures/'+self.fixture['captures']['other'], '/analysis-jobs/'+'a'*32,'/replays/'+'a'*32,
                     '/trips/'+self.tid+'/reports/'+'a'*32,'/trips/'+self.tid+'/cv/captures/'+self.cid+'/media/1',
                     '/trips/%2e%2e','/trips/..','/trips/'+self.tid+'/export/../../school.sqlite3']:
            self.assertEqual(self.get(path)[0],404,path)
        self.use('other');self.assertEqual(self.request('GET',PREFIX+'/trips/'+self.tid,headers={'X-Owner-ID':self.users['driver']['id'],'X-Role':'ADMIN'})[0],404)
        for path in ['/api/state','/api/runs','/api/vision/media','/runtime/school.sqlite3','/backups/x.sqlite3',
                     PREFIX+'/devices',PREFIX+'/navigation',PREFIX+'/device/session',
                     PREFIX+'/trips/'+self.tid+'/cv/captures/'+self.cid+'/frames/0']:
            self.assertEqual(self.request('GET',path)[0],404)
        self.assertEqual(self.get('/admin/users')[0],403)  # Stage8 implements admin API; DRIVER remains forbidden.
        self.assertEqual(self.post('/trips',{'title':'fake','owner_id':self.users['driver']['id']})[0],422)

    def test_policy_reauth_default_deny_and_transfer_revocation(self):
        self.use('driver');raw=self.cookies['gw_session'];policy=Policy(self.service)
        with self.assertRaises(AuthError) as result:policy.role(raw,{'ADMIN'},True)
        self.assertEqual(result.exception.status,403)
        self.use('admin');policy.role(self.cookies['gw_session'],{'ADMIN'},True)
        self.now+=300001
        with self.assertRaises(AuthError):policy.role(self.cookies['gw_session'],{'ADMIN'},True)
        self.use('driver');transfer=self.server.resources.export(raw,self.tid)
        with self.assertRaises(AuthError) as result:self.server.resources.export(raw,self.tid)
        self.assertEqual(result.exception.status,409)
        self.service.logout(self.service.sessions.lookup(raw)[0])
        with self.assertRaises(AuthError):transfer.validate()
        transfer.close();self.assertEqual(self.server.resources.exports,set())

    def test_symlink_or_junction_file_escape(self):
        import os,subprocess
        self.use('driver');trip=self.trips['shared'];root=self.storage.run(trip['owner_id'],self.tid,trip['run_id'])
        target=self.storage.root/'synthetic-outside';target.mkdir();(target/'raw.csv').write_text('SYNTHETIC',encoding='utf-8')
        link=root/'escape'
        if os.name=='nt':
            subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],check=True,stdout=subprocess.DEVNULL)
        else:link.symlink_to(target,target_is_directory=True)
        from greenwave.school_data.errors import Invalid
        with self.assertRaises(Invalid):self.server.resources.files.path(link,'raw.csv')
        # Remove junction itself with rmdir, never recurse into its target.
        if os.name=='nt':os.rmdir(link)
        else:link.unlink()

    def test_delete_context_matrix_csrf_and_unknown_body(self):
        jid,_=self.create_job('analyst')
        self.use('analyst');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        for path in ['/replays/'+hid,'/analysis-jobs/'+jid]:
            for who in [None,'other','admin']:
                self.use(who);self.assertEqual(self.request('DELETE',PREFIX+path,{})[0],401 if who is None else 404)
            self.use('analyst')
            for headers in [{'X-CSRF-Token':'wrong'},{'Origin':'http://evil.test'}]:
                self.assertEqual(self.request('DELETE',PREFIX+path,{},headers)[0],403)
            self.assertEqual(self.request('DELETE',PREFIX+path,{'owner_id':'fake'})[0],422)
            self.assertEqual(self.request('DELETE',PREFIX+path,{})[0],204)
        self.assertEqual(self.get('/replays/'+hid)[0],404)
        # Owner can close an analysis job, but cannot take over another session replay.
        self.use('driver');self.assertEqual(self.request('DELETE',PREFIX+'/analysis-jobs/'+jid,{})[0],204)

    def test_expired_session_matrix_and_uniform_missing_foreign_errors(self):
        jid,rid=self.create_job()
        self.use('driver');hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        raw=self.cookies['gw_session']
        paths=['/trips','/trips/'+self.tid,'/observations?trip_id='+self.tid,
               '/observations/'+self.oid+'/corrections','/trips/'+self.tid+'/export',
               '/config/versions','/config/versions/'+self.fixture['published']['id'],
               '/replays/'+hid,'/analysis-jobs/'+jid,'/trips/'+self.tid+'/reports',
               '/trips/'+self.tid+'/reports/'+rid,'/trips/'+self.tid+'/cv/captures',
               '/trips/'+self.tid+'/cv/captures/'+self.cid,
               '/trips/'+self.tid+'/cv/captures/'+self.cid+'/events',
               '/trips/'+self.tid+'/cv/captures/'+self.cid+'/media/0']
        self.now+=28800000
        for path in paths:
            self.cookies={'gw_session':raw};self.assertEqual(self.get(path)[0],401,path)
        self.now-=28800000;self.use('driver')
        foreign=self.get('/trips/'+self.trips['other']['id'])[1]['error']
        missing=self.get('/trips/'+'a'*32)[1]['error'];self.assertEqual(foreign,missing)

    def test_revocation_during_job_and_report_integrity(self):
        import threading
        entered=threading.Event();release=threading.Event()
        from greenwave.analysis import RunAnalysis
        original=RunAnalysis.analyze
        def slow(analysis,run_id):
            entered.set();release.wait(5);return original(analysis,run_id)
        self.use('analyst')
        with patch.object(RunAnalysis,'analyze',slow):
            data=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[1]['data']
            self.assertTrue(entered.wait(2))
            self.repo.revoke_share(Actor(self.users['driver']['id']),self.tid,self.fixture['share'])
            release.set()
            for _ in range(100):
                if self.server.resources.contexts.jobs[data['id']]['status']=='CANCELLED':break
                time.sleep(.02)
        self.assertEqual(self.server.resources.contexts.jobs[data['id']]['status'],'CANCELLED')
        self.assertIsNone(self.server.resources.contexts.jobs[data['id']]['report_id'])
        jid,rid=self.create_job('driver')
        root=self.storage.derived(self.users['driver']['id'],self.tid)/rid
        (root/'report.json').write_text('{}',encoding='utf-8')
        self.assertEqual(self.get('/trips/'+self.tid+'/reports/'+rid)[0],409)

    def test_file_manifest_traversal_and_data_error_statuses(self):
        self.use('driver');root=self.storage.cv(self.users['driver']['id'],self.tid,self.cid)
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        for name in ['../school.sqlite3','%2e%2e%2fschool.sqlite3','school.sqlite3','x\\raw.csv','http://evil.test/x.avi']:
            manifest['artifacts'][0]['filename']=name
            (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            self.assertEqual(self.get('/trips/'+self.tid+'/cv/captures/'+self.cid+'/media/0')[0],409,name)
        from greenwave.school_data.errors import Denied,Conflict,Invalid
        for error,status in [(Denied('synthetic'),404),(Conflict('synthetic'),409),(Invalid('synthetic'),422)]:
            with patch.object(self.server.resources.lists,'read',side_effect=error):self.assertEqual(self.get('/trips')[0],status)

    def test_bounded_contexts_configs_and_failure_paths(self):
        self.use('driver');raw=self.cookies['gw_session'];contexts=self.server.resources.contexts
        hid=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']['id']
        self.now+=1800000
        with self.assertRaises(AuthError):contexts.replay_read(raw,hid)
        self.now-=1800000
        with patch('greenwave.school_resources.contexts.RunAnalysis.analyze',side_effect=ValueError('synthetic secret path')):
            data=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[1]['data']
            for _ in range(100):
                if contexts.jobs[data['id']]['status']=='FAILED':break
                time.sleep(.02)
            self.assertEqual(contexts.jobs[data['id']]['status'],'FAILED')
        root=self.storage.cv(self.users['driver']['id'],self.tid,self.cid)
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        manifest['complete']=False;(root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        self.assertEqual(self.get('/trips/'+self.tid+'/cv/captures/'+self.cid+'/media/0')[0],409)
        manifest['artifacts']=[];(root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        self.assertEqual(self.get('/trips/'+self.tid+'/cv/captures/'+self.cid+'/events')[1]['data']['items'],[])
        self.use('admin')
        draft=self.repo.create_config(Actor(self.users['admin']['id']),'MODEL','unsafe',{'path':'C:/secret'})
        self.assertEqual(self.get('/config/versions/'+draft['id'])[0],409)
        self.assertEqual(self.get('/config/versions?kind=WRONG')[0],422)
        self.assertEqual(self.get('/config/versions/'+'a'*32)[0],404)

    def test_job_queue_access_rechecked_before_execution(self):
        import threading
        gate=threading.Event();contexts=self.server.resources.contexts
        blockers=[contexts.pool.submit(gate.wait,5) for _ in range(2)]
        self.use('analyst')
        with patch('greenwave.school_resources.contexts.RunAnalysis.analyze') as analyze:
            data=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[1]['data']
            self.assertEqual(self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[0],409)
            self.repo.revoke_share(Actor(self.users['driver']['id']),self.tid,self.fixture['share'])
            gate.set()
            for _ in range(100):
                if contexts.jobs[data['id']]['status']=='CANCELLED':break
                time.sleep(.02)
            self.assertEqual(contexts.jobs[data['id']]['status'],'CANCELLED');analyze.assert_not_called()
