from datetime import datetime, timezone
import unittest
from greenwave.telemetry import RunLogger, digest
from greenwave.school_data import Actor, Repository
from greenwave.school_data.errors import Denied, Invalid
from greenwave.school_data.time_units import MAX_TIMESTAMP_MS
from test_school_data_repositories import RepositoryFixture


class ContractBoundaryTests(RepositoryFixture):
    def test_created_and_received_half_open_range_at_five_boundaries(self):
        trips=[];observations=[]
        start,end=2000000,2000010
        for index,time_ms in enumerate([start-1,start,start+5,end,end+1]):
            self.now=time_ms
            trip=self.repo.create_trip(self.actor,'Boundary '+str(index))
            trips.append(trip['id'])
            obs=self.repo.add_observation(self.actor,self.trip['id'],'s','RED','STATE_SEEN','event-'+str(index),measured_at=1)
            observations.append(obs['id'])
        own=self.repo.list_trips(self.actor,after=start,before=end)
        self.assertEqual({r['id'] for r in own},{trips[1],trips[2]})
        rows=self.repo.list_observations(self.actor,self.trip['id'],after=start,before=end)
        self.assertEqual({r['id'] for r in rows},{observations[1],observations[2]})
        self.assertTrue(all(r['measured_at']==1 for r in rows))
        self.assertEqual({r['id'] for r in self.repo.list_trips(self.actor,before=start)},{self.trip['id'],trips[0]})
        self.assertEqual(len(self.repo.list_observations(self.actor,self.trip['id'],after=end)),2)

    def test_invalid_date_types_equal_and_reversed_ranges(self):
        for method in [lambda **kw:self.repo.list_trips(self.actor,**kw),lambda **kw:self.repo.list_observations(self.actor,self.trip['id'],**kw)]:
            for bad in [True,False,1.0,'1000',[],{},float('nan'),float('inf'),-1,MAX_TIMESTAMP_MS+1]:
                for field in ['after','before']:
                    with self.subTest(field=field,value=bad),self.assertRaises(Invalid):method(**{field:bad})
            for after,before in [(1,1),(2,1)]:
                with self.assertRaises(Invalid):method(after=after,before=before)

    def test_real_runlogger_raw_csv_owned_path_and_no_source_mutation(self):
        run_parent=self.storage.trip(self.actor.user_id,self.trip['id'])/'runs'
        logger=RunLogger(run_parent)
        logger.start({'fixture':'synthetic stage3 review'})
        logger.append('gps',timestamp=datetime(2026,1,1,tzinfo=timezone.utc),simulation_seconds=0,model_seconds=0,latitude=52.0,longitude=21.0)
        logger.finish('synthetic-test',timestamp=datetime(2026,1,1,tzinfo=timezone.utc),simulation_seconds=1,model_seconds=1)
        run_id=logger.run_id;run_root=self.storage.run(self.actor.user_id,self.trip['id'],run_id)
        self.assertTrue(all((run_root/name).exists() for name in ['raw.csv','metadata.json','complete.json']))
        original={name:digest(run_root/name) for name in ['raw.csv','metadata.json','complete.json']}
        trip=self.trip
        for state in ['STARTING','RECORDING','FINALIZING']:
            trip=self.repo.transition_trip(self.actor,trip['id'],trip['revision'],state,**({'run_id':run_id} if state=='STARTING' else {}))
        correct=(run_root/'raw.csv').relative_to(self.storage.root).as_posix()
        for wrong in [correct.replace(self.actor.user_id,self.oa.user_id),correct.replace(self.trip['id'],'f'*32),correct.rsplit('/',1)[0]+'/../'+run_id+'/raw.csv',correct.rsplit('/',1)[0]+'/gps.jsonl']:
            with self.assertRaises(Invalid):self.repo.transition_trip(self.actor,trip['id'],trip['revision'],'COMPLETE',raw_ref=wrong,raw_hash=original['raw.csv'],manifest_hash=original['complete.json'])
        done=self.repo.transition_trip(self.actor,trip['id'],trip['revision'],'COMPLETE',raw_ref=correct,raw_hash=original['raw.csv'],manifest_hash=original['complete.json'])
        self.assertEqual(done['raw_ref'],correct)
        self.assertEqual({name:digest(run_root/name) for name in original},original)

    def test_ms_ttl_idle_absolute_pairing_reset_verify_rate_and_reauth(self):
        start=self.now
        session=self.repo.create_session(self.actor,'1'*64,'2'*64)
        with self.db.connection() as c:
            row=c.execute('SELECT * FROM browser_sessions WHERE id=?',(session,)).fetchone()
            self.assertEqual(row['absolute_expiry']-row['created_at'],28800000)
            self.assertIs(type(row['created_at']),int)
        self.now=start+1799999;self.repo.touch_session(self.actor,session)
        self.now=start+3599999
        with self.assertRaises(Denied):self.repo.touch_session(self.actor,session)
        self.now=start
        reset=self.repo.issue_account_token(self.driver['id'],'RESET','3'*64)
        self.now=start+899999;self.repo.consume_account_token('3'*64,'RESET')
        self.now=start
        self.repo.issue_account_token(self.driver['id'],'RESET','4'*64)
        self.now=start+900000
        with self.assertRaises(Denied):self.repo.consume_account_token('4'*64,'RESET')
        pending=self.repo.create_user('verify@example.test','Verify','fixture')
        self.repo.issue_account_token(pending['id'],'VERIFY_EMAIL','5'*64)
        with self.db.connection() as c:
            row=c.execute("SELECT * FROM account_tokens WHERE purpose='VERIFY_EMAIL'").fetchone()
            self.assertEqual(row['expiry']-row['issued_at'],86400000)
        self.now=start
        challenge=self.repo.pairing_challenge(self.actor,session,'6'*64,'boot','Phone')
        self.now=start+299999
        self.repo.bind_device(self.actor,challenge,'phone','7'*64,'boot')
        self.now=start
        challenge=self.repo.pairing_challenge(self.actor,session,'8'*64,'boot','Phone')
        self.now=start+300000
        with self.assertRaises(Denied):self.repo.bind_device(self.actor,challenge,'other','9'*64,'boot')
        self.now=start
        self.repo.rate_attempt('a'*64,'LOGIN',window_ms=60000,limit=2)
        self.assertEqual(self.repo.rate_attempt('a'*64,'LOGIN',window_ms=60000,limit=2)['blocked_until'],start+60000)
        self.now=start+60000
        self.assertEqual(self.repo.rate_attempt('a'*64,'LOGIN')['attempts'],1)
        self.now=start+300000
        self.repo.change_account(Actor(self.admin['id'],start),self.other['id'],1,status='BLOCKED')
        self.now+=1
        with self.assertRaises(Denied):self.repo.change_account(Actor(self.admin['id'],start),self.other['id'],2,status='ACTIVE')
        for bad in [True,1.0,float('nan'),'1000']:
            with self.assertRaises(Invalid):Actor(self.admin['id'],bad)
            with self.assertRaises(Invalid):self.repo.create_user('invalid@example.test','Invalid','fixture',verified_at=bad)
        with self.assertRaises(Invalid):Repository(self.db,clock=lambda:1.0).create_trip(self.actor,"Invalid clock")
        # A read without reauth does not need clock. Exercise a write instead.

    def test_absolute_and_verification_expiry_and_measured_time_validation(self):
        start=self.now
        session=self.repo.create_session(self.actor,'a'*64,'b'*64)
        self.now=start+28800000-1
        with self.db.transaction() as c:
            c.execute('UPDATE browser_sessions SET last_activity_at=? WHERE id=?',(self.now,session))
        self.repo.touch_session(self.actor,session)
        self.now+=1
        with self.assertRaises(Denied):self.repo.touch_session(self.actor,session)
        self.now=start
        pending=self.repo.create_user('expiry@example.test','Expiry','fixture')
        self.repo.issue_account_token(pending['id'],'VERIFY_EMAIL','c'*64)
        self.now=start+86400000
        with self.assertRaises(Denied):self.repo.consume_account_token('c'*64,'VERIFY_EMAIL')
        self.now=start
        for invalid in [True,1.0,self.now+300001]:
            with self.assertRaises(Invalid):self.repo.add_observation(self.actor,self.trip['id'],'s','RED','STATE_SEEN','invalid-time',measured_at=invalid)
