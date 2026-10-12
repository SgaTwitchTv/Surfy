import sqlite3
import tempfile
import unittest
from pathlib import Path
from greenwave.school_data import Database, Storage
from greenwave.school_data.database import connect
from greenwave.school_data.backup import backup, restore
from greenwave.school_data.errors import Invalid, SchemaError
from greenwave.school_data.migrations import load, migrate, status, Migration
from greenwave.school_data.time_units import seconds_to_ms, timestamp_ms, MAX_TIMESTAMP_MS


def insert(c,table,**values):
    c.execute('INSERT INTO '+table+' ('+','.join(values)+') VALUES ('+','.join('?' for _ in values)+')',list(values.values()))


def seeded_v1(storage):
    migrate(storage,load()[:1],clock=lambda:1700000000123)
    c=connect(storage.database)
    try:
        owner,analyst,admin='1'*32,'2'*32,'3'*32
        for uid,name,role in [(owner,'owner','DRIVER'),(analyst,'analyst','ANALYST'),(admin,'admin','ADMIN')]:
            insert(c,'users',id=uid,email_normalized=name+'@example.test',email_display=name+'@example.test',display_name=name,password_hash='fixture$legacy',role=role,status='ACTIVE',verified_email_at=1.125,created_at=2.9999,updated_at=3.5)
        insert(c,'browser_sessions',id='4'*32,user_id=owner,secret_hash='a'*64,csrf_hash='b'*64,security_version=1,authenticated_at=10.125,created_at=10.125,last_activity_at=11.001,absolute_expiry=28810.125,revoked_at=None)
        insert(c,'account_tokens',id='5'*32,user_id=owner,purpose='RESET',secret_hash='c'*64,security_version=1,issued_at=10.125,expiry=910.125,used_at=None,revoked_at=12.001,delivery_state='SENT')
        insert(c,'auth_rate_limits',key_hash='d'*64,purpose='LOGIN',window_start=10.001,attempts=2,blocked_until=70.001,expires_at=130.001)
        insert(c,'devices',id='6'*32,owner_id=owner,client_device_id='legacy-fixture',label='Phone',status='ACTIVE',token_hash='e'*64,parent_session_id='4'*32,boot_id='legacy',security_version=1,expiry=28810.125,last_seen_at=10.9999)
        insert(c,'pairing_challenges',id='7'*32,code_hmac='f'*64,owner_id=owner,parent_session_id='4'*32,boot_id='legacy',label='Phone',issued_at=10.125,expiry=310.125,used_at=11.5)
        insert(c,'config_versions',id='8'*32,kind='ROUTE',logical_id='route',version=1,payload='{}',payload_hash='a'*64,status='PUBLISHED',creator_id=admin,created_at=2.5,published_at=3.5)
        insert(c,'trips',id='9'*32,owner_id=owner,title='Historical synthetic',note='preserve me',mode='SIMULATION',route_version_id='8'*32,status='COMPLETE',created_at=10.5,started_at=20.001,ended_at=30.002,run_id='a'*32,raw_ref='owners/'+owner+'/trips/'+'9'*32+'/runs/'+'a'*32+'/raw.csv',raw_hash='b'*64,manifest_hash='c'*64)
        insert(c,'observations',id='b'*32,trip_id='9'*32,actor_id=owner,signal_id='s',source='MANUAL',state='RED',event_type='STATE_SEEN',server_received_at=20.0009,measured_at=None,source_event_id='legacy-event')
        insert(c,'observation_corrections',id='c'*32,observation_id='b'*32,actor_id=owner,sequence=1,previous_revision=0,before_json='{"state":"RED"}',after_json='{"state":"GREEN"}',reason='legacy correction',server_at=21.125,client_operation_id='x'*32,request_hash='d'*64)
        insert(c,'trip_shares',id='d'*32,trip_id='9'*32,analyst_id=analyst,grantor_id=owner,created_at=31.001)
        insert(c,'audit_events',actor_id=owner,actor_type='USER',action='PROOF',resource_type='TRIP',resource_id='9'*32,server_at=31.001,request_id='fixture',outcome='OK')
        c.execute("UPDATE sqlite_sequence SET seq=100 WHERE name='audit_events'")
        insert(c,'recording_operations',id='e'*32,trip_id='9'*32,actor_id=owner,kind='FINISH',idempotency_key='x'*32,request_hash='e'*64,state='APPLIED',result_ref=None,created_at=30.002)
    finally:c.close()


class EpochUpgradeTests(unittest.TestCase):
    def test_v1_upgrade_preserves_all_records_relations_indexes_and_triggers(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Storage(tmp);seeded_v1(s)
            c=connect(s.database)
            tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            before={t:[dict(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
            times={t:[r[1] for r in c.execute('PRAGMA table_info('+t+')') if r[2]=='REAL'] for t in tables}
            objects={(r[0],r[1]) for r in c.execute("SELECT type,name FROM sqlite_master WHERE type IN ('index','trigger')")}
            checksum=load()[0].checksum;c.close()
            result=migrate(s);self.assertEqual(result['version'],2);self.assertTrue(Path(result['backup']).exists())
            self.assertIsNone(migrate(s)['backup'])
            with Database(s) as db:
                with db.connection() as c:
                    after_objects={(r[0],r[1]) for r in c.execute("SELECT type,name FROM sqlite_master WHERE type IN ('index','trigger')")}
                    self.assertEqual(objects,after_objects)
                    self.assertEqual(c.execute("SELECT seq FROM sqlite_sequence WHERE name='audit_events'").fetchone()[0],100)
                    self.assertEqual(c.execute('SELECT checksum FROM schema_migrations WHERE version=1').fetchone()[0],checksum)
                    for t in tables:
                        after=[dict(r) for r in c.execute('SELECT * FROM '+t)]
                        if t=='schema_migrations':after=after[:1]
                        expected=[{k:seconds_to_ms(v) if k in times[t] else v for k,v in row.items()} for row in before[t]]
                        self.assertEqual(after,expected,t)
                        for row in c.execute('PRAGMA table_info('+t+')'):
                            if row[1] in times[t]:self.assertEqual(row[2],'INTEGER')
                        for row in after:
                            for field in times[t]:self.assertTrue(row[field] is None or type(row[field]) is int)
                    self.assertEqual(len(tables),14)
                    self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
                    with self.assertRaises(sqlite3.IntegrityError):c.execute("UPDATE observations SET state='GREEN'")
                    with self.assertRaises(sqlite3.IntegrityError):c.execute("DELETE FROM audit_events")
                    with self.assertRaises(sqlite3.IntegrityError):c.execute("UPDATE auth_rate_limits SET window_start=1.5")

    def test_invalid_legacy_time_rolls_back_rebuild_and_preserves_v1(self):
        for invalid in [-1,1e40,'invalid',float('inf')]:
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory() as tmp:
                s=Storage(tmp);seeded_v1(s);c=connect(s.database)
                c.execute('UPDATE auth_rate_limits SET window_start=?',(invalid,));c.close()
                with self.assertRaises(sqlite3.OperationalError):migrate(s)
                self.assertEqual(status(s)['version'],1);self.assertFalse(status(s)['current'])
                c=connect(s.database)
                try:
                    self.assertEqual(c.execute("SELECT note FROM trips").fetchone()[0],'preserve me')
                    self.assertEqual(c.execute("SELECT type FROM pragma_table_info('users') WHERE name='created_at'").fetchone()[0],'REAL')
                    self.assertFalse(c.in_transaction)
                    self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name LIKE 'ms_%'").fetchone())
                finally:c.close()
                self.assertEqual(len(list((s.root/'backups').glob('*.sqlite3'))),1)

    def test_failed_after_full_conversion_restores_v1_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Storage(tmp);seeded_v1(s)
            bad=Migration(2,load()[1].sql+'THIS IS INVALID;')
            with self.assertRaises(sqlite3.OperationalError):migrate(s,[load()[0],bad])
            self.assertEqual(status(s)['version'],1)
            c=connect(s.database)
            try:self.assertEqual(c.execute('SELECT server_received_at FROM observations').fetchone()[0],20.0009)
            finally:c.close()

    def test_v1_backup_restore_requires_explicit_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Storage(tmp);seeded_v1(s)
            old=s.root/'backups'/'v1.sqlite3'
            writer=connect(s.database)
            try:
                writer.execute('PRAGMA wal_autocheckpoint=0')
                writer.execute('UPDATE auth_rate_limits SET attempts=9')
                self.assertTrue(Path(str(s.database)+'-wal').exists())
                backup(s,old)
            finally:writer.close()
            migrate(s);self.assertEqual(status(s)['version'],2)
            result=restore(s,old);self.assertTrue(Path(result['previous']).exists())
            self.assertEqual(result['schema'],{'version':1,'latest':2,'current':False})
            self.assertEqual(status(s),{'version':1,'latest':2,'current':False})
            with self.assertRaises(SchemaError):Database(s).__enter__()
            again=s.root/'backups'/'v1-again.sqlite3';backup(s,again)
            migrate(s);self.assertTrue(status(s)['current'])
            with Database(s) as db:
                with db.connection() as c:self.assertEqual(c.execute('SELECT server_received_at FROM observations').fetchone()[0],20000)
            foreign=s.root/'empty.sqlite3';sqlite3.connect(foreign).close()
            with self.assertRaises(SchemaError):restore(s,foreign)

    def test_conversion_null_boundaries_floor_and_invalid_types(self):
        self.assertIsNone(seconds_to_ms(None))
        self.assertEqual(seconds_to_ms(0),0)
        self.assertEqual(seconds_to_ms(1.9999),1999)
        self.assertEqual(seconds_to_ms(0.001),1)
        self.assertEqual(seconds_to_ms(253402300799.999),MAX_TIMESTAMP_MS)
        self.assertEqual(timestamp_ms(MAX_TIMESTAMP_MS),MAX_TIMESTAMP_MS)
        for value in [True,'1',-1,float('nan'),float('inf'),253402300800]:
            with self.assertRaises(Invalid):seconds_to_ms(value)
        for value in [True,1.0,'1',-1,float('nan'),float('inf'),MAX_TIMESTAMP_MS+1]:
            with self.assertRaises(Invalid):timestamp_ms(value)
