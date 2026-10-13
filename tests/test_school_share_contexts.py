"""Regrant must never resurrect a context authorized by a revoked share."""
import threading
import time
from unittest.mock import patch
from greenwave.school_data import Actor
from greenwave.analysis import RunAnalysis
from test_school_accounts import Fixture, PASS, PREFIX
import test_school_resources as resource_tests
from scripts.school_resource_fixtures import populate


class ShareContextTests(Fixture):
    use = resource_tests.ResourceTests.use
    get = resource_tests.ResourceTests.get
    post = resource_tests.ResourceTests.post
    create_job = resource_tests.ResourceTests.create_job

    def setUp(self):
        super().setUp()
        self.fixture = populate(self.repo, self.service.passwords.hash(PASS))
        self.users = self.fixture['users']; self.trips = self.fixture['trips']
        self.tid = self.trips['shared']['id']
        self.credentials = {}
        for who in self.users:
            self.cookies = {}; self.preflight()
            status, data, _ = self.auth('login', {'email': who+'@example.test', 'password': PASS})
            self.assertEqual(status, 200)
            self.credentials[who] = (dict(self.cookies), data['data']['csrf'])
        self.use('analyst')

    def regrant(self):
        owner = Actor(self.users['driver']['id'])
        self.repo.revoke_share(owner, self.tid, self.fixture['share'])
        # Intentionally NO HTTP/read/check of the context between these mutations.
        new = self.repo.share_trip(owner, self.tid, 'analyst@example.test')
        self.assertNotEqual(new, self.fixture['share'])
        self.fixture['share'] = new

    def test_exact_reproducer_revoke_regrant_without_intermediate_read(self):
        status, data, _ = self.post('/trips/'+self.tid+'/replays', {'mode': 'GPS'})
        self.assertEqual(status, 201); hid = data['data']['id']
        self.regrant()
        self.assertEqual(self.get('/replays/'+hid)[0], 404)

    def test_old_replay_control_close_and_new_replay_after_regrant(self):
        for operation in ['control', 'close']:
            status, data, _ = self.post('/trips/'+self.tid+'/replays', {'mode':'GPS'})
            self.assertEqual(status,201);hid=data['data']['id']
            self.regrant()
            if operation=='control':status=self.post('/replays/'+hid+'/control',{'command':'PLAY'})[0]
            else:status=self.request('DELETE',PREFIX+'/replays/'+hid,{})[0]
            self.assertEqual(status,404)
            self.assertNotIn(hid,self.server.resources.contexts.replays)
        data=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']
        self.assertEqual(self.get('/replays/'+data['id'])[0],200)
        for private in ['authorization','share_id','credential','actor_id']:
            self.assertNotIn(private,data)
        self.use('driver')
        data=self.post('/trips/'+self.tid+'/replays',{'mode':'GPS'})[1]['data']
        self.regrant()
        self.assertEqual(self.get('/replays/'+data['id'])[0],200)

    def test_completed_job_status_cancel_and_existing_reports_after_regrant(self):
        jid,rid=self.create_job('analyst')
        self.regrant()
        self.assertEqual(self.get('/analysis-jobs/'+jid)[0],404)
        self.assertEqual(self.request('DELETE',PREFIX+'/analysis-jobs/'+jid,{})[0],404)
        # Previously published reports remain owner's data. A new grant permits
        # a fresh report read but does not resurrect the old ephemeral job handle.
        self.assertEqual(self.get('/trips/'+self.tid+'/reports/'+rid)[0],200)
        self.use('driver');self.assertEqual(self.get('/trips/'+self.tid+'/reports/'+rid)[0],200)
        jid,_=self.create_job('analyst')
        self.regrant()  # No preceding status read after this revoke/regrant.
        self.assertEqual(self.request('DELETE',PREFIX+'/analysis-jobs/'+jid,{})[0],404)
        self.assertTrue(self.server.resources.contexts.jobs[jid]['authorization_invalid'])
        _,_=self.create_job('analyst')

    def test_queued_job_regrant_does_not_restore_execution(self):
        gate=threading.Event();contexts=self.server.resources.contexts
        blockers=[contexts.pool.submit(gate.wait,10) for _ in range(2)]
        self.addCleanup(gate.set)
        with patch.object(RunAnalysis,'analyze') as analyze:
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id']
            self.regrant();gate.set()
            self.await_status(jid,'CANCELLED')
            analyze.assert_not_called()
            self.assertIsNone(contexts.jobs[jid]['report_id'])
            self.assertEqual(self.get('/analysis-jobs/'+jid)[0],404)

    def await_status(self,jid,expected):
        for _ in range(200):
            if self.server.resources.contexts.jobs[jid]['status']==expected:return
            time.sleep(.01)
        self.fail('Unexpected internal job status: '+self.server.resources.contexts.jobs[jid]['status'])

    def test_running_job_regrant_before_publication_produces_no_report(self):
        gate=threading.Event();entered=threading.Event();original=RunAnalysis.analyze
        self.addCleanup(gate.set)
        def slow(analysis,runid):
            entered.set();gate.wait(10);return original(analysis,runid)
        with patch.object(RunAnalysis,'analyze',slow):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id'];self.assertTrue(entered.wait(3))
            self.regrant();gate.set();self.await_status(jid,'CANCELLED')
        self.assertIsNone(self.server.resources.contexts.jobs[jid]['report_id'])
        root=self.storage.derived(self.users['driver']['id'],self.tid)
        self.assertFalse(root.exists())

    def test_regrant_between_file_validation_and_analysis_is_denied(self):
        contexts=self.server.resources.contexts;original=contexts.files.run
        gate=threading.Event();entered=threading.Event();self.addCleanup(gate.set)
        calls=[]
        def intercepted(*args,**kwargs):
            result=original(*args,**kwargs);calls.append(1)
            if len(calls)==2:entered.set();gate.wait(10)  # Worker file check, not enqueue.
            return result
        with patch.object(contexts.files,'run',intercepted),patch.object(RunAnalysis,'analyze') as analyze:
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id'];self.assertTrue(entered.wait(3))
            self.regrant();gate.set();self.await_status(jid,'CANCELLED');analyze.assert_not_called()

    def test_same_share_id_wrong_recipient_or_trip_and_no_owner_fallback(self):
        from dataclasses import replace
        from greenwave.school_accounts.errors import AuthError
        policy=self.server.resources.policy;raw=self.cookies['gw_session']
        _,_,_,basis=policy.basis_trip(raw,self.tid,closed=True)
        self.assertEqual(basis.kind,'SHARE');self.assertEqual(basis.share_id,self.fixture['share'])
        for forged in [replace(basis,actor_id=self.users['other']['id']),
                       replace(basis,trip_id=self.trips['private']['id']),replace(basis,kind='OWN')]:
            with self.assertRaises(AuthError):policy.bound_trip(raw,forged)
        self.regrant()
        with self.assertRaises(AuthError):policy.bound_trip(raw,basis)

    def test_regrant_after_last_check_before_publication_is_denied(self):
        contexts=self.server.resources.contexts;original=contexts.authorize_job_execution;calls=[]
        def intercepted(raw,job,**kwargs):
            result=original(raw,job,**kwargs)
            calls.append(1)
            if len(calls)==3:self.regrant()  # Last check succeeded, then revoke.
            return result
        with patch.object(contexts,'authorize_job_execution',intercepted):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id'];self.await_status(jid,'CANCELLED')
        self.assertIsNone(contexts.jobs[jid]['report_id'])
        self.assertFalse(self.storage.derived(self.users['driver']['id'],self.tid).exists())

    def completed_analyst_job(self):
        contexts=self.server.resources.contexts;finished=threading.Event();original=contexts.execute
        def execute(*args):
            try:return original(*args)
            finally:finished.set()
        self.use('analyst')
        with patch.object(contexts,'execute',execute):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);self.assertTrue(finished.wait(10),'Worker did not finish')
        job=contexts.jobs[data['data']['id']]
        self.assertEqual(job['status'],'COMPLETE')
        return job['id'],job['report_id']

    def test_owner_status_reproducer_before_and_after_analyst_denial(self):
        for regrant in [False,True]:
            jid,rid=self.completed_analyst_job()
            self.use('driver');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
            owner=Actor(self.users['driver']['id'])
            if regrant:self.regrant()
            else:self.repo.revoke_share(owner,self.tid,self.fixture['share'])
            with self.subTest(regrant=regrant,phase='before analyst read'):
                self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
            self.use('analyst');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],404)
            self.use('driver')
            with self.subTest(regrant=regrant,phase='after analyst read'):
                self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
            self.assertEqual(self.get('/trips/'+self.tid+'/reports/'+rid)[0],200)
            if not regrant:
                self.fixture['share']=self.repo.share_trip(owner,self.tid,'analyst@example.test')

    def job_identity(self,jid):
        job=self.server.resources.contexts.jobs[jid]
        return {key:job[key] for key in ['actor_id','session_id','credential','authorization']}

    def test_owner_completed_cancel_and_access_matrix_after_regrant(self):
        jid,rid=self.completed_analyst_job();identity=self.job_identity(jid)
        self.regrant();path='/analysis-jobs/'+jid
        for who in ['driver','analyst','other','admin',None]:
            self.use(who)
            expected=200 if who=='driver' else 401 if who is None else 404
            self.assertEqual(self.get(path)[0],expected,who)
            expected=204 if who=='driver' else 401 if who is None else 404
            self.assertEqual(self.request('DELETE',PREFIX+path,{})[0],expected,who)
        self.use('driver')
        for _ in range(2):self.assertEqual(self.request('DELETE',PREFIX+path,{})[0],204)
        data=self.get(path)[1]['data'];self.assertEqual(data['status'],'COMPLETE')
        self.assertEqual(data['report_id'],rid);self.assertEqual(self.get('/trips/'+self.tid+'/reports/'+rid)[0],200)
        self.assertEqual(self.job_identity(jid),identity)
        self.assertEqual(set(data),{'id','trip_id','type','status','report_id'})
        new_id,_=self.completed_analyst_job();self.assertNotEqual(jid,new_id)

    def test_owner_cancel_queued_after_revoke_without_execution(self):
        contexts=self.server.resources.contexts;release=threading.Event()
        started=[threading.Event(),threading.Event()];finished=threading.Event();original=contexts.execute
        def blocker(index):started[index].set();release.wait(10)
        def execute(*args):
            try:return original(*args)
            finally:finished.set()
        for index in range(2):contexts.pool.submit(blocker,index)
        self.addCleanup(release.set)
        for event in started:self.assertTrue(event.wait(3))
        with patch.object(contexts,'execute',execute),patch.object(RunAnalysis,'analyze') as analyze:
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id'];identity=self.job_identity(jid)
            self.repo.revoke_share(Actor(self.users['driver']['id']),self.tid,self.fixture['share'])
            self.use('driver');status,data,_=self.get('/analysis-jobs/'+jid)
            self.assertEqual(status,200);self.assertEqual(data['data']['status'],'CANCELLED')
            self.assertEqual(self.request('DELETE',PREFIX+'/analysis-jobs/'+jid,{})[0],204)
            self.assertEqual(self.job_identity(jid),identity)
            release.set();self.assertTrue(finished.wait(3));analyze.assert_not_called()
        self.assertIsNone(contexts.jobs[jid]['report_id'])

    def test_owner_cancel_running_after_revoke_prevents_publication(self):
        contexts=self.server.resources.contexts;entered=threading.Event();release=threading.Event();finished=threading.Event()
        original_execute=contexts.execute;original_analyze=RunAnalysis.analyze
        def analyze(instance,runid):entered.set();release.wait(10);return original_analyze(instance,runid)
        def execute(*args):
            try:return original_execute(*args)
            finally:finished.set()
        self.addCleanup(release.set)
        with patch.object(contexts,'execute',execute),patch.object(RunAnalysis,'analyze',analyze):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id'];identity=self.job_identity(jid)
            self.assertTrue(entered.wait(3));self.regrant()
            # Owner can cancel immediately, before an analyst denial sets flags.
            self.use('driver');self.assertEqual(self.request('DELETE',PREFIX+'/analysis-jobs/'+jid,{})[0],204)
            self.assertEqual(self.get('/analysis-jobs/'+jid)[1]['data']['status'],'CANCELLED')
            self.use('analyst');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],404)
            self.use('driver');self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
            self.assertEqual(self.job_identity(jid),identity)
            release.set();self.assertTrue(finished.wait(3))
        self.assertIsNone(contexts.jobs[jid]['report_id'])
        self.assertFalse(self.storage.derived(self.users['driver']['id'],self.tid).exists())

    def test_owner_own_job_after_archive_and_handle_ttl(self):
        contexts=self.server.resources.contexts;finished=threading.Event();original=contexts.execute
        def execute(*args):
            try:return original(*args)
            finally:finished.set()
        self.use('driver')
        with patch.object(contexts,'execute',execute):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);self.assertTrue(finished.wait(3))
        jid=data['data']['id'];identity=self.job_identity(jid)
        self.repo.archive_trip(Actor(self.users['driver']['id']),self.tid,self.trips['shared']['revision'])
        self.assertEqual(self.get('/analysis-jobs/'+jid)[0],200)
        self.assertEqual(self.request('DELETE',PREFIX+'/analysis-jobs/'+jid,{})[0],204)
        self.assertEqual(self.job_identity(jid),identity)
        self.assertEqual(self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})[0],409)
        self.now+=1800000
        # Fresh active owner session, but memory handle TTL has elapsed.
        self.preflight();_,data,_=self.auth('login',{'email':'driver@example.test','password':PASS});self.csrf=data['data']['csrf']
        self.assertEqual(self.get('/analysis-jobs/'+jid)[0],404)

    def test_owner_job_management_session_csrf_origin_and_revocation(self):
        jid,_=self.completed_analyst_job();self.regrant();self.use('driver');path='/analysis-jobs/'+jid
        for headers in [{'X-CSRF-Token':''},{'X-CSRF-Token':'bad'},{'Origin':'http://evil.test'}]:
            self.assertEqual(self.request('DELETE',PREFIX+path,{},headers)[0],403)
        raw=self.cookies['gw_session']
        self.now+=1800000
        for method in ['GET','DELETE']:
            self.cookies={'gw_session':raw}
            self.assertEqual(self.request(method,PREFIX+path,{} if method=='DELETE' else None)[0],401)
        self.now-=1800000;self.use('driver');self.assertEqual(self.auth('logout',{})[0],204)
        for method in ['GET','DELETE']:
            self.cookies={'gw_session':raw}
            self.assertEqual(self.request(method,PREFIX+path,{} if method=='DELETE' else None)[0],401)
