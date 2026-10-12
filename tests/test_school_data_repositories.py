import concurrent.futures
import json
import sqlite3
import tempfile
import unittest
from greenwave.school_data import Actor, Database, Repository, Storage
from greenwave.school_data.migrations import migrate
from greenwave.school_data.errors import Conflict, Denied, Invalid

HASH='a'*64
KEY='operation_'+'a'*32


class RepositoryFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.storage=Storage(self.temp.name);migrate(self.storage)
        self.db=Database(self.storage).__enter__();self.addCleanup(self.db.close)
        self.now=1000.0
        self.repo=Repository(self.db,clock=lambda:self.now)
        self.driver=self.account('driver');self.other=self.account('other')
        self.analyst=self.account('analyst','ANALYST');self.admin=self.account('admin','ADMIN')
        self.actor=Actor(self.driver['id']);self.oa=Actor(self.other['id']);self.aa=Actor(self.analyst['id']);self.ad=Actor(self.admin['id'],self.now)
        self.trip=self.repo.create_trip(self.actor,'Synthetic trip')

    def account(self,name,role='DRIVER'):
        return self.repo.create_user(name+'@example.test',name,'fixture$NOT_AUTHENTICATION',role=role,status='ACTIVE',verified_at=900)

    def complete(self):
        trip=self.trip
        run='b'*32
        for state in ['STARTING','RECORDING','FINALIZING','COMPLETE']:
            kwargs={'run_id':run} if state=='STARTING' else {}
            if state=='COMPLETE':kwargs={'raw_ref':self.storage.run(self.driver['id'],trip['id'],run).relative_to(self.storage.root).as_posix()+'/gps.jsonl','raw_hash':HASH,'manifest_hash':HASH}
            trip=self.repo.transition_trip(self.actor,trip['id'],trip['revision'],state,**kwargs)
        self.trip=trip
        return trip

    def obs(self):
        return self.repo.add_observation(self.actor,self.trip['id'],'signal-1','RED','STATE_SEEN','synthetic-event')



class RepositoryTests(RepositoryFixture):
    def test_email_normalization_uniqueness_validation_and_no_auto_import(self):
        with self.assertRaises(Conflict):self.repo.create_user(' DRIVER@example.test ','New','fixture')
        for address in ['no-at','a@localhost','a..b@example.test','x@-bad.test','a@example..test','ą@example.test']:
            with self.assertRaises(Invalid):self.repo.create_user(address,'New','fixture')
        pending=self.repo.create_user('new+tag@example.test','New','fixture')
        self.assertEqual(pending['status'],'PENDING_VERIFICATION')
        with self.assertRaises(Denied):self.repo.list_trips(Actor(pending['id']))
        with self.assertRaises(Invalid):self.repo.create_user('x@example.test','New','fixture',status='ACTIVE')
        with self.assertRaises(Invalid):self.repo.create_user('x@example.test','New','fixture',role='ROOT')
        self.assertEqual(self.repo.list_trips(self.oa),[])
        self.assertIsNone(self.repo.get_user('0'*32))

    def test_owner_admin_and_untrusted_context_isolation(self):
        self.assertEqual(self.repo.get_trip(self.actor,self.trip['id'])['owner_id'],self.driver['id'])
        for actor in [self.oa,self.aa,self.ad,{'user_id':self.driver['id']}]:
            with self.assertRaises(Denied):self.repo.get_trip(actor,self.trip['id'])
            with self.assertRaises(Denied):self.repo.list_observations(actor,self.trip['id'])
        self.assertEqual(self.repo.list_trips(self.ad),[])
        admin_trip=self.repo.create_trip(self.ad,'Admin own trip')
        self.assertEqual(self.repo.get_trip(self.ad,admin_trip['id'])['title'],'Admin own trip')

    def test_sharing_lifecycle_and_read_only_recipient(self):
        self.complete();obs=self.obs()
        with self.assertRaises(Denied):self.repo.get_shared_trip(self.aa,self.trip['id'])
        share=self.repo.share_trip(self.actor,self.trip['id'],' ANALYST@EXAMPLE.TEST ')
        self.assertEqual(self.repo.get_shared_trip(self.aa,self.trip['id'])['id'],self.trip['id'])
        self.assertEqual(len(self.repo.list_observations(self.aa,self.trip['id'],shared=True)),1)
        self.assertEqual(self.repo.correction_history(self.aa,obs['id'],shared=True),[])
        with self.assertRaises(Conflict):self.repo.share_trip(self.actor,self.trip['id'],'analyst@example.test')
        with self.assertRaises(Denied):self.repo.get_shared_trip(self.ad,self.trip['id'])
        with self.assertRaises(Denied):self.repo.edit_trip(self.aa,self.trip['id'],self.trip['revision'],title='Other',note='')
        with self.assertRaises(Denied):self.repo.correct_observation(self.aa,obs['id'],0,{'state':'GREEN','event_type':'STATE_SEEN','valid':True},'reason',KEY)
        self.repo.revoke_share(self.actor,self.trip['id'],share)
        self.repo.revoke_share(self.actor,self.trip['id'],share)
        with self.assertRaises(Denied):self.repo.get_shared_trip(self.aa,self.trip['id'])
        with self.assertRaises(Denied):self.repo.list_observations(self.aa,self.trip['id'],shared=True)
        newer=self.repo.share_trip(self.actor,self.trip['id'],'analyst@example.test')
        self.repo.revoke_share(self.actor,self.trip['id'],share)
        self.assertEqual(self.repo.get_shared_trip(self.aa,self.trip['id'])['id'],self.trip['id'])
        with self.assertRaises(Conflict):self.repo.revoke_share(self.actor,self.trip['id'],'0'*32)
        self.repo.archive_trip(self.actor,self.trip['id'],self.trip['revision'])
        with self.assertRaises(Denied):self.repo.get_shared_trip(self.aa,self.trip['id'])
        with self.assertRaises(Conflict):self.repo.share_trip(self.actor,self.trip['id'],'analyst@example.test')

    def test_share_incomplete_wrong_recipient_and_inactive_analyst(self):
        with self.assertRaises(Conflict):self.repo.share_trip(self.actor,self.trip['id'],'analyst@example.test')
        self.complete()
        for address in ['other@example.test','admin@example.test','missing@example.test']:
            with self.assertRaises(Denied):self.repo.share_trip(self.actor,self.trip['id'],address)
        self.repo.change_account(self.ad,self.analyst['id'],1,status='BLOCKED')
        with self.assertRaises(Denied):self.repo.share_trip(self.actor,self.trip['id'],'analyst@example.test')

    def test_metadata_revision_filters_archive_and_durability(self):
        changed=self.repo.edit_trip(self.actor,self.trip['id'],1,title='Edited',note='note')
        with self.assertRaises(Conflict):self.repo.edit_trip(self.actor,self.trip['id'],1,title='stale',note='')
        self.assertEqual(len(self.repo.list_trips(self.actor,after=999,before=1001,status='PLANNED')),1)
        self.assertEqual(self.repo.list_trips(self.actor,after=1001),[])
        for kw in [{'limit':101},{'offset':-1},{'status':'BAD'},{'after':2,'before':1}]:
            with self.assertRaises(Invalid):self.repo.list_trips(self.actor,**kw)
        self.db.close()
        with Database(self.storage) as reopened:
            repo=Repository(reopened,clock=lambda:self.now)
            self.assertEqual(repo.get_trip(self.actor,self.trip['id'])['note'],'note')
            repo.archive_trip(self.actor,self.trip['id'],changed['revision'])
            self.assertIsNotNone(repo.get_trip(self.actor,self.trip['id'])['archived_at'])

    def test_observation_original_corrections_journaling_and_idempotency(self):
        obs=self.obs();self.assertEqual(self.obs()['id'],obs['id'])
        with self.assertRaises(Conflict):self.repo.add_observation(self.actor,self.trip['id'],'signal-1','GREEN','STATE_SEEN','synthetic-event')
        after={'state':'GREEN','event_type':'STATE_START','valid':True}
        correction=self.repo.correct_observation(self.actor,obs['id'],0,after,'Observed correction',KEY)
        self.assertEqual(self.repo.correct_observation(self.actor,obs['id'],0,after,'Observed correction',KEY)['id'],correction['id'])
        with self.assertRaises(Conflict):self.repo.correct_observation(self.actor,obs['id'],0,after,'Changed reason',KEY)
        with self.assertRaises(Conflict):self.repo.correct_observation(self.actor,obs['id'],0,after,'Second correction','z'*32)
        effective=self.repo.list_observations(self.actor,self.trip['id'],state='GREEN')[0]
        self.assertEqual(effective['state'],'RED');self.assertEqual(effective['effective']['state'],'GREEN')
        self.assertEqual(self.repo.list_observations(self.actor,self.trip['id'],state='RED'),[])
        self.assertEqual(self.repo.correction_history(self.actor,obs['id'])[0]['before_json'],'{"event_type":"STATE_SEEN","state":"RED","valid":true}')
        self.repo.journal_observation(self.actor,obs['id'],2,'APPLIED')
        with self.db.transaction() as c:
            row=c.execute('SELECT * FROM observations WHERE id=?',(obs['id'],)).fetchone()
            self.assertEqual(row['raw_sequence'],2);self.assertEqual(row['state'],'RED')
        for sql in ["UPDATE observations SET state='GREEN'","UPDATE observations SET raw_sequence=3,state='GREEN'","DELETE FROM observations","UPDATE observation_corrections SET reason='altered'","DELETE FROM observation_corrections","UPDATE audit_events SET action='altered'","DELETE FROM audit_events"]:
            with self.assertRaises(Conflict):
                with self.db.transaction() as c:c.execute(sql)
        self.assertEqual(len(self.repo.correction_history(self.actor,obs['id'])),1)

    def test_concurrent_corrections_one_revision_winner(self):
        obs=self.obs()
        def apply(index):
            try:
                self.repo.correct_observation(self.actor,obs['id'],0,{'state':'GREEN','event_type':'STATE_SEEN','valid':True},'Concurrent correction',str(index)*32)
                return 'OK'
            except Conflict:return 'CONFLICT'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(apply,[1,2])),['OK','CONFLICT'])
        self.assertEqual(len(self.repo.correction_history(self.actor,obs['id'])),1)

    def test_sql_fk_check_unique_and_invalid_dto_rollback(self):
        for sql,args in [("INSERT INTO trips(id,owner_id,title,mode,status,created_at) VALUES (?,?,?,'SIMULATION','PLANNED',1)",('d'*32,'0'*32,'title')),
                         ("UPDATE users SET role='ROOT' WHERE id=?",(self.driver['id'],)),
                         ("UPDATE trips SET owner_id=? WHERE id=?",(self.other['id'],self.trip['id'])),
                         ("UPDATE trips SET status='COMPLETE' WHERE id=?",(self.trip['id'],))]:
            with self.assertRaises(Conflict):
                with self.db.transaction() as c:c.execute(sql,args)
        for args in [('UNKNOWN','STATE_START'),('BLUE','STATE_SEEN')]:
            with self.assertRaises(Invalid):self.repo.add_observation(self.actor,self.trip['id'],'s',*args,'event')
        with self.assertRaises(Invalid):self.repo.add_observation(self.actor,self.trip['id'],'s','RED','STATE_SEEN','event',measured_at=float('nan'))
        with self.assertRaises(Invalid):self.repo.create_trip(self.actor,'')
        with self.assertRaises(Invalid):self.repo.create_trip(self.actor,'title',mode='FLY')
        with self.assertRaises(Invalid):self.repo.create_trip(self.actor,'title',route_version_id='f'*32)

    def test_recording_intent_idempotency_and_persistence_only(self):
        intent=self.repo.recording_intent(self.actor,self.trip['id'],'START',KEY,HASH)
        self.assertEqual(self.repo.recording_intent(self.actor,self.trip['id'],'START',KEY,HASH)['id'],intent['id'])
        with self.assertRaises(Conflict):self.repo.recording_intent(self.actor,self.trip['id'],'START',KEY,'b'*64)
        with self.assertRaises(Denied):self.repo.recording_intent(self.oa,self.trip['id'],'START',KEY,HASH)
        with self.assertRaises(Invalid):self.repo.recording_intent(self.actor,self.trip['id'],'PURGE',KEY,HASH)
        with self.assertRaises(Invalid):self.repo.finish_intent(self.actor,intent['id'],'APPLIED','../escape')
        self.repo.finish_intent(self.actor,intent['id'],'APPLIED')
        self.repo.finish_intent(self.actor,intent['id'],'APPLIED')
        with self.assertRaises(Conflict):self.repo.finish_intent(self.actor,intent['id'],'FAILED')
        self.assertEqual(self.repo.get_trip(self.actor,self.trip['id'])['status'],'PLANNED')
        self.assertFalse((self.storage.root/'owners').exists())

    def test_config_snapshot_roles_revision_and_last_admin(self):
        with self.assertRaises(Denied):self.repo.create_config(self.actor,'ROUTE','r',{})
        draft=self.repo.create_config(self.aa,'ROUTE','r',{'field_verification':'UNVERIFIED'})
        with self.assertRaises(Denied):self.repo.publish_config(self.aa,draft['id'],1)
        with self.assertRaises(Denied):self.repo.publish_config(Actor(self.admin['id']),draft['id'],1)
        with self.assertRaises(Conflict):self.repo.publish_config(self.ad,draft['id'],2)
        published=self.repo.publish_config(self.ad,draft['id'],1)
        self.assertIn('UNVERIFIED',published['payload'])
        self.assertEqual(self.repo.create_config(self.aa,'ROUTE','r',{})['version'],2)
        self.assertEqual(self.repo.create_trip(self.actor,'Route',route_version_id=published['id'])['route_version_id'],published['id'])
        with self.assertRaises(Conflict):
            with self.db.transaction() as c:c.execute("UPDATE config_versions SET payload='{}' WHERE id=?",(published['id'],))
        for kwargs in [{'role':'DRIVER'},{'status':'BLOCKED'}]:
            with self.assertRaises(Conflict):self.repo.change_account(self.ad,self.admin['id'],1,**kwargs)
        other_admin=self.account('admin2','ADMIN')
        self.repo.change_account(self.ad,other_admin['id'],1,role='DRIVER')
        with self.assertRaises(Conflict):self.repo.change_account(self.ad,self.driver['id'],0,status='BLOCKED')
        with self.assertRaises(Invalid):self.repo.change_account(self.ad,self.driver['id'],1,role='ROOT')

    def test_edit_draft_and_transition_complete_checks(self):
        draft=self.repo.create_config(self.aa,'SIGNAL','s',{})
        edited=self.repo.edit_config(self.aa,draft['id'],1,{'field_verification':'UNVERIFIED'})
        with self.assertRaises(Conflict):self.repo.edit_config(self.aa,draft['id'],1,{})
        other=self.account('analyst2','ANALYST')
        with self.assertRaises(Denied):self.repo.edit_config(Actor(other['id']),draft['id'],2,{})
        with self.assertRaises(Invalid):self.repo.edit_config(self.aa,draft['id'],2,[])
        self.repo.publish_config(self.ad,draft['id'],edited['revision'])
        with self.assertRaises(Conflict):self.repo.edit_config(self.aa,draft['id'],edited['revision']+1,{})
        trip=self.trip
        for state in ['STARTING','RECORDING','FINALIZING']:
            trip=self.repo.transition_trip(self.actor,trip['id'],trip['revision'],state,**({'run_id':'b'*32} if state=='STARTING' else {}))
        with self.assertRaises(Invalid):self.repo.transition_trip(self.actor,trip['id'],trip['revision'],'COMPLETE',raw_ref='other/gps.jsonl',raw_hash=HASH,manifest_hash=HASH)
        self.assertEqual(self.repo.get_trip(self.actor,trip['id'])['status'],'FINALIZING')
