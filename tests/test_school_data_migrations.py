import contextlib
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from greenwave.school_data import Storage, Database
from greenwave.school_data.errors import Busy, Invalid, SchemaError
from greenwave.school_data.migrations import migrate, status, load, Migration, validate
from greenwave.school_data.backup import backup, restore
from greenwave.school_data.database import connect
from greenwave.school_data.__main__ import main


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage=Storage(self.temp.name)

    def test_fresh_idempotent_fourteen_tables_pragmas(self):
        self.assertEqual(migrate(self.storage)["version"],1)
        self.assertIsNone(migrate(self.storage)["backup"])
        self.assertTrue(status(self.storage)["current"])
        with Database(self.storage) as db:
            with db.connection() as c:
                tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                self.assertEqual(tables,{'schema_migrations','users','browser_sessions','account_tokens','auth_rate_limits','devices','pairing_challenges','trips','observations','observation_corrections','trip_shares','audit_events','config_versions','recording_operations'})
                self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0],1)
                self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()[0],'wal')
                self.assertEqual(c.execute('PRAGMA synchronous').fetchone()[0],2)
                self.assertEqual(c.execute('PRAGMA busy_timeout').fetchone()[0],5000)
                indexes={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'")}
                self.assertTrue({'trips_owner_date','trips_owner_filter','observations_date','observations_filter','shares_active'}.issubset(indexes))

    def test_upgrade_backup_and_future_refusal(self):
        migrate(self.storage)
        extra=Migration(2,'CREATE TABLE synthetic_next_version (id INTEGER PRIMARY KEY);')
        result=migrate(self.storage,load()+[extra])
        self.assertTrue(Path(result['backup']).exists())
        c=connect(self.storage.database)
        try:self.assertEqual(validate(c,load()+[extra])['version'],2)
        finally:c.close()
        with self.assertRaises(SchemaError):status(self.storage)
        with self.assertRaises(SchemaError):Database(self.storage).__enter__()
        # Lease was released on refused runtime startup.
        self.assertEqual(migrate(self.storage,load()+[extra])['version'],2)

    def test_upgrade_failure_rollback(self):
        migrate(self.storage)
        bad=Migration(2,'CREATE TABLE transient_table (id INTEGER); INSERT INTO absent VALUES (1);')
        with self.assertRaises(sqlite3.OperationalError):migrate(self.storage,load()+[bad])
        self.assertEqual(status(self.storage)['version'],1)
        c=connect(self.storage.database)
        try:self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='transient_table'").fetchone())
        finally:c.close()
        self.assertEqual(len(list((self.storage.root/'backups').glob('*.sqlite3'))),1)

    def test_fresh_failure_rolls_back_all_schema(self):
        bad=Migration(1,load()[0].sql+'INSERT INTO absent VALUES (1);')
        with self.assertRaises(sqlite3.OperationalError):migrate(self.storage,[bad])
        self.assertEqual(status(self.storage)['version'],0)
        self.assertEqual(migrate(self.storage)['version'],1)

    def test_checksum_user_version_and_unknown_database_refused(self):
        migrate(self.storage)
        c=connect(self.storage.database)
        try:
            c.execute("UPDATE schema_migrations SET checksum='tampered'")
            with self.assertRaises(SchemaError):validate(c,load())
            c.execute('UPDATE schema_migrations SET checksum=?',(load()[0].checksum,))
            c.execute('PRAGMA user_version=9')
            with self.assertRaises(SchemaError):validate(c,load())
            c.execute('PRAGMA user_version=1')
            with self.assertRaises(SchemaError):validate(c,[Migration(2,'SELECT 1;')])
        finally:c.close()
        with tempfile.TemporaryDirectory() as other:
            storage=Storage(other); storage.prepare()
            c=connect(storage.database);c.execute('CREATE TABLE legacy (value TEXT)');c.close()
            with self.assertRaises(SchemaError):migrate(storage)

    def test_transaction_control_and_incomplete_migrations_rejected(self):
        for suffix in ['COMMIT;','CREATE TABLE unfinished (']:
            with self.assertRaises(SchemaError):migrate(self.storage,[Migration(1,load()[0].sql+suffix)])
            self.assertEqual(status(self.storage)['version'],0)

    def test_backup_includes_wal_and_restore_retains_previous(self):
        migrate(self.storage)
        c=connect(self.storage.database)
        try:
            c.execute('PRAGMA wal_autocheckpoint=0')
            c.execute("INSERT INTO auth_rate_limits VALUES (?,?,1,2,NULL,60)",('a'*64,'synthetic'))
            self.assertTrue(Path(str(self.storage.database)+'-wal').exists())
            destination=self.storage.root/'backups'/'sample.sqlite3'
            backup(self.storage,destination)
            c.execute('UPDATE auth_rate_limits SET attempts=7')
        finally:c.close()
        result=restore(self.storage,destination)
        self.assertTrue(Path(result['previous']).exists())
        c=connect(self.storage.database)
        try:self.assertEqual(c.execute('SELECT attempts FROM auth_rate_limits').fetchone()[0],2)
        finally:c.close()
        old=connect(Path(result['previous']),readonly=True)
        try:self.assertEqual(old.execute('SELECT attempts FROM auth_rate_limits').fetchone()[0],7)
        finally:old.close()
        with self.assertRaises(Invalid):backup(self.storage,destination)
        with self.assertRaises(Invalid):restore(self.storage,self.storage.database)

    def test_invalid_restore_preserves_existing(self):
        migrate(self.storage)
        bad=self.storage.root/'bad.sqlite3'
        c=sqlite3.connect(bad);c.execute('CREATE TABLE bad (id)');c.close()
        with self.assertRaises(SchemaError):restore(self.storage,bad)
        self.assertTrue(status(self.storage)['current'])
        with self.assertRaises(Invalid):backup(self.storage,self.storage.root.parent/'escape.sqlite3')

    def test_runtime_and_maintenance_conflict_across_processes(self):
        migrate(self.storage)
        with Database(self.storage) as db:
            for action in [lambda:migrate(self.storage),lambda:status(self.storage),lambda:backup(self.storage,self.storage.root/'copy.sqlite3'),lambda:restore(self.storage,self.storage.database)]:
                with self.assertRaises((Busy,Invalid)):action()
            result=subprocess.run([sys.executable,'-m','greenwave.school_data','--root',str(self.storage.root),'status'],capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn('Busy',result.stdout)
        self.assertTrue(status(self.storage)['current'])
        with self.assertRaises(SchemaError):db.connection().__enter__()

    def test_cli_all_commands_and_no_import_side_effects(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--root',str(self.storage.root),'status']),1)
            self.assertEqual(main(['--root',str(self.storage.root),'init']),0)
            self.assertEqual(main(['--root',str(self.storage.root),'migrate']),0)
            self.assertEqual(main(['--root',str(self.storage.root),'status']),0)
            destination=str(self.storage.root/'backups'/'cli.sqlite3')
            self.assertEqual(main(['--root',str(self.storage.root),'backup',destination]),0)
            self.assertEqual(main(['--root',str(self.storage.root),'restore',destination]),0)
        with tempfile.TemporaryDirectory() as blank:
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]),PYTHONDONTWRITEBYTECODE='1')
            subprocess.run([sys.executable,'-c','import greenwave.school_data'],cwd=blank,env=env,check=True)
            self.assertEqual(list(Path(blank).iterdir()),[])

    def test_no_implicit_init(self):
        with self.assertRaises(SchemaError):Database(self.storage).__enter__()
        self.assertFalse(self.storage.database.exists())
