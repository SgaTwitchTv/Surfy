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
        contexts=self.server.resources.contexts;original=contexts.job_authorize;calls=[]
        def intercepted(raw,job,**kwargs):
            result=original(raw,job,**kwargs)
            if kwargs.get('execution'):
                calls.append(1)
                if len(calls)==3:self.regrant()  # Last check succeeded, then revoke.
            return result
        with patch.object(contexts,'job_authorize',intercepted):
            status,data,_=self.post('/trips/'+self.tid+'/analysis-jobs',{'type':'GPS_QUALITY'})
            self.assertEqual(status,202);jid=data['data']['id'];self.await_status(jid,'CANCELLED')
        self.assertIsNone(contexts.jobs[jid]['report_id'])
        self.assertFalse(self.storage.derived(self.users['driver']['id'],self.tid).exists())
