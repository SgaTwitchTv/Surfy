import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_school_data_repositories import RepositoryFixture, HASH
from greenwave.school_data import Actor, Storage
from greenwave.school_data.errors import Denied, Invalid, Conflict
from greenwave.school_data.validation import canonical, digest, email, operation_key, text, observation


class SecurityTests(RepositoryFixture):
    # Reuse fixture, without duplicating inherited test cases in discovery.
    def test_credentials_ownership_boot_expiry_and_logout(self):
        session=self.repo.create_session(self.actor,HASH,'b'*64)
        with self.assertRaises(Invalid):self.repo.create_session(self.actor,'RAW SECRET','b'*64)
        with self.assertRaises(Conflict):self.repo.create_session(self.actor,HASH,'b'*64)
        with self.assertRaises(Denied):self.repo.touch_session(self.oa,session)
        self.repo.touch_session(self.actor,session)
        challenge=self.repo.pairing_challenge(self.actor,session,'c'*64,'boot-1','Synthetic phone')
        with self.assertRaises(Denied):self.repo.bind_device(self.oa,challenge,'client','d'*64,'boot-1')
        device=self.repo.bind_device(self.actor,challenge,'client','d'*64,'boot-1')
        self.assertEqual(self.repo.device_owner('d'*64,'boot-1'),self.driver['id'])
        with self.assertRaises(Denied):self.repo.device_owner('d'*64,'boot-2')
        with self.assertRaises(Denied):self.repo.bind_device(self.actor,challenge,'client','e'*64,'boot-1')
        replacement=self.repo.pairing_challenge(self.actor,session,'e'*64,'boot-1','Replacement')
        self.assertEqual(self.repo.bind_device(self.actor,replacement,'client','f'*64,'boot-1'),device)
        with self.assertRaises(Denied):self.repo.device_owner('d'*64,'boot-1')
        self.assertEqual(self.repo.device_owner('f'*64,'boot-1'),self.driver['id'])
        with self.assertRaises(Denied):self.repo.revoke_session(self.oa,session)
        self.repo.revoke_session(self.actor,session)
        self.repo.revoke_session(self.actor,session)
        with self.assertRaises(Denied):self.repo.device_owner('f'*64,'boot-1')
        with self.assertRaises(Denied):self.repo.pairing_challenge(self.actor,session,'a'*64,'boot-1','Phone')
        expired=self.repo.create_session(self.actor,'1'*64,'2'*64)
        self.now+=1800000
        with self.assertRaises(Denied):self.repo.touch_session(self.actor,expired)

    def test_token_rotation_expiry_single_use_and_atomic_callback(self):
        token=self.repo.issue_account_token(self.driver['id'],'RESET',HASH)
        self.repo.issue_account_token(self.driver['id'],'RESET','b'*64)
        with self.assertRaises(Denied):self.repo.consume_account_token(HASH,'RESET')
        def fail(c,token):
            c.execute("UPDATE users SET display_name='Should rollback' WHERE id=?",(token['user_id'],))
            raise RuntimeError('synthetic failure')
        with self.assertRaises(RuntimeError):self.repo.consume_account_token('b'*64,'RESET',apply=fail)
        self.assertEqual(self.repo.get_user(self.driver['id'])['display_name'],'driver')
        self.assertEqual(self.repo.consume_account_token('b'*64,'RESET')['user_id'],self.driver['id'])
        with self.assertRaises(Denied):self.repo.consume_account_token('b'*64,'RESET')
        self.repo.issue_account_token(self.driver['id'],'RESET','c'*64)
        self.now+=900000
        with self.assertRaises(Denied):self.repo.consume_account_token('c'*64,'RESET')
        pending=self.repo.create_user('pending@example.test','Pending','fixture')
        self.repo.issue_account_token(pending['id'],'VERIFY_EMAIL','d'*64)
        self.assertEqual(self.repo.consume_account_token('d'*64,'VERIFY_EMAIL')['purpose'],'VERIFY_EMAIL')
        with self.assertRaises(Denied):self.repo.issue_account_token(pending['id'],'RESET','e'*64)
        with self.assertRaises(Denied):self.repo.issue_account_token(self.driver['id'],'VERIFY_EMAIL','e'*64)
        with self.assertRaises(Invalid):self.repo.issue_account_token(self.driver['id'],'OTHER','e'*64)

    def test_role_change_blocking_revokes_secrets_and_share(self):
        self.complete();share=self.repo.share_trip(self.actor,self.trip['id'],'analyst@example.test')
        session=self.repo.create_session(self.aa,'1'*64,'2'*64)
        challenge=self.repo.pairing_challenge(self.aa,session,'3'*64,'boot','Phone')
        self.repo.bind_device(self.aa,challenge,'phone','4'*64,'boot')
        self.repo.issue_account_token(self.analyst['id'],'RESET','5'*64)
        self.repo.change_account(self.ad,self.analyst['id'],1,role='DRIVER')
        with self.assertRaises(Denied):self.repo.get_shared_trip(self.aa,self.trip['id'])
        with self.assertRaises(Denied):self.repo.touch_session(self.aa,session)
        with self.assertRaises(Denied):self.repo.device_owner('4'*64,'boot')
        with self.assertRaises(Denied):self.repo.consume_account_token('5'*64,'RESET')
        self.repo.change_account(self.ad,self.other['id'],1,status='BLOCKED')
        with self.assertRaises(Denied):self.repo.list_trips(self.oa)
        with self.assertRaises(Denied):self.repo.change_account(self.actor,self.driver['id'],1,status='BLOCKED')
        with self.assertRaises(Denied):self.repo.change_account(self.ad,'0'*32,1,status='BLOCKED')

    def test_rate_windows_pairing_rotation_and_constraints(self):
        self.assertEqual(self.repo.rate_attempt(HASH,'LOGIN',limit=2)['attempts'],1)
        self.assertEqual(self.repo.rate_attempt(HASH,'LOGIN',limit=2)['blocked_until'],1060000)
        self.now+=61000
        self.assertEqual(self.repo.rate_attempt(HASH,'LOGIN',limit=2)['attempts'],1)
        with self.assertRaises(Invalid):self.repo.rate_attempt(HASH,'RESET')
        with self.assertRaises(Invalid):self.repo.rate_attempt(HASH,'LOGIN',limit=0)
        session=self.repo.create_session(self.actor,'1'*64,'2'*64)
        first=self.repo.pairing_challenge(self.actor,session,'3'*64,'boot','Phone')
        second=self.repo.pairing_challenge(self.actor,session,'4'*64,'boot','Phone')
        with self.assertRaises(Denied):self.repo.bind_device(self.actor,first,'phone','5'*64,'boot')
        self.now+=300000
        with self.assertRaises(Denied):self.repo.bind_device(self.actor,second,'phone','5'*64,'boot')
        # Direct SQL cannot pair a session of a different owner.
        with self.assertRaises(Conflict):
            with self.db.transaction() as c:
                c.execute("INSERT INTO pairing_challenges VALUES (?,?,?,?,?,?,?,?,0,NULL,NULL)",('a'*32,'6'*64,self.other['id'],session,'boot','Phone',self.now,self.now+300000))

    def test_observation_validation_archived_and_missing_records(self):
        with self.assertRaises(Invalid):self.repo.add_observation(self.actor,self.trip['id'],'s','RED','STATE_SEEN','e',source='OTHER')
        obs=self.obs()
        for kwargs in [{'limit':0},{'offset':-1},{'state':'BLUE'},{'event_type':'START'},{'after':2,'before':1}]:
            with self.assertRaises(Invalid):self.repo.list_observations(self.actor,self.trip['id'],**kwargs)
        self.assertEqual(self.repo.list_observations(self.actor,self.trip['id'],after=2000000),[])
        self.assertEqual(len(self.repo.list_observations(self.actor,self.trip['id'],signal='signal-1',event_type='STATE_SEEN')),1)
        with self.assertRaises(Denied):self.repo.correction_history(self.oa,obs['id'])
        with self.assertRaises(Denied):self.repo.correction_history(self.actor,'0'*32)
        with self.assertRaises(Denied):self.repo.correct_observation(self.actor,'0'*32,0,{'state':'GREEN','event_type':'STATE_SEEN','valid':True},'reason','x'*32)
        with self.assertRaises(Invalid):self.repo.correct_observation(self.actor,obs['id'],-1,{'state':'GREEN','event_type':'STATE_SEEN','valid':True},'reason','x'*32)
        with self.assertRaises(Invalid):self.repo.journal_observation(self.actor,obs['id'],-1,'APPLIED')
        with self.assertRaises(Denied):self.repo.journal_observation(self.actor,'0'*32,1,'APPLIED')
        self.repo.archive_trip(self.actor,self.trip['id'],1)
        with self.assertRaises(Conflict):self.obs()
        with self.assertRaises(Conflict):self.repo.correct_observation(self.actor,obs['id'],0,{'state':'GREEN','event_type':'STATE_SEEN','valid':True},'reason','x'*32)

    def test_transition_and_configuration_invalid_paths(self):
        with self.assertRaises(Conflict):self.repo.transition_trip(self.actor,self.trip['id'],1,'COMPLETE')
        with self.assertRaises(Conflict):self.repo.transition_trip(self.actor,self.trip['id'],0,'STARTING',run_id='b'*32)
        started=self.repo.transition_trip(self.actor,self.trip['id'],1,'STARTING',run_id='b'*32)
        with self.assertRaises(Conflict):self.repo.archive_trip(self.actor,self.trip['id'],started['revision'])
        interrupted=self.repo.transition_trip(self.actor,self.trip['id'],started['revision'],'INTERRUPTED')
        with self.assertRaises(Conflict):
            with self.db.transaction() as c:c.execute("UPDATE trips SET run_id=? WHERE id=?",('c'*32,self.trip['id']))
        for args in [('BAD',{}),('ROUTE',[]),('ROUTE',{'x':'x'*262145})]:
            with self.assertRaises(Invalid):self.repo.create_config(self.aa,args[0],'r',args[1])
        with self.assertRaises(Denied):self.repo.publish_config(self.ad,'0'*32,1)
        intent=self.repo.recording_intent(self.actor,self.trip['id'],'FINISH','k'*32,HASH)
        with self.assertRaises(Invalid):self.repo.finish_intent(self.actor,intent['id'],'UNKNOWN')
        with self.assertRaises(Denied):self.repo.finish_intent(self.actor,'0'*32,'APPLIED')
        with self.assertRaises(Invalid):self.repo.finish_intent(self.actor,intent['id'],'APPLIED','C:/escape')
        with self.assertRaises(Invalid):self.repo.finish_intent(self.actor,intent['id'],'APPLIED','owners/'+self.other['id']+'/trips/'+self.trip['id']+'/result')
        reference=self.storage.derived(self.driver['id'],self.trip['id']).relative_to(self.storage.root).as_posix()+'/result.json'
        escape=reference.rsplit('/',2)[0]+'/../'+'f'*32+'/result.json'
        with self.assertRaises(Invalid):self.repo.finish_intent(self.actor,intent['id'],'APPLIED',escape)
        self.repo.finish_intent(self.actor,intent['id'],'APPLIED',reference)


class StorageTests(unittest.TestCase):
    def test_explicit_root_and_controlled_ids(self):
        for root in ['', 'relative', str(Path(tempfile.gettempdir())/'data'/'runs'/'private'), str(Path(tempfile.gettempdir())/'runtime'/'school')]:
            with self.assertRaises(Invalid):Storage(root)
        with tempfile.TemporaryDirectory() as tmp:
            storage=Storage(tmp)
            for value in ['../escape','x'*32,'A'*32,'0'*31,1]:
                with self.assertRaises(Invalid):storage.trip(value,'1'*32)
            owner,trip='1'*32,'2'*32
            self.assertEqual(storage.run(owner,trip,'3'*32).name,'3'*32)
            self.assertEqual(storage.cv(owner,trip,'4'*32).name,'4'*32)
            self.assertEqual(storage.index(owner).name,'indexes')
            self.assertEqual(storage.config('5'*32).name,'5'*32)
            with self.assertRaises(Invalid):storage._safe(Path(tmp)/'..'/'escape')

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            storage=Storage(tmp)
            try:(Path(tmp)/'owners').symlink_to(outside,target_is_directory=True)
            except OSError as exc:self.skipTest('Windows symlink privilege unavailable: '+str(exc))
            with self.assertRaises(Invalid):storage.trip('1'*32,'2'*32)
            with self.assertRaises(Invalid):Storage(str(Path(tmp)/'owners'))

    @unittest.skipUnless(os.name=='nt','Windows junction test; POSIX uses symlink test')
    def test_windows_junction_escape(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            storage=Storage(tmp)
            link=Path(tmp)/'owners'
            result=subprocess.run(['cmd','/c','mklink','/J',str(link),outside],capture_output=True)
            if result.returncode:
                self.skipTest('Junction creation unavailable, exit '+str(result.returncode))
            try:
                with self.assertRaises(Invalid):storage.trip('1'*32,'2'*32)
                with self.assertRaises(Invalid):Storage(str(link))
            finally:
                # Remove only the junction itself; never recurse into its target.
                os.rmdir(link)

    def test_validation_helpers(self):
        for call in [lambda:digest('raw'),lambda:operation_key('short'),lambda:text(' a ',1,80),lambda:text('a\n',1,80),lambda:canonical(float('nan')),lambda:observation({'state':'RED','event_type':'STATE_SEEN','valid':1}),lambda:email(None)]:
            with self.assertRaises(Invalid):call()
        self.assertEqual(email(' NAME+tag@Example.test '),'name+tag@example.test')
