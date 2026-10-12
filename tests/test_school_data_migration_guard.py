import sqlite3
import tempfile
import unittest
from greenwave.school_data import Storage
from greenwave.school_data.database import connect
from greenwave.school_data.errors import SchemaError
from greenwave.school_data.migrations import Migration, migrate, load, status, statements, execute_migration_statement

PROOF = """CREATE TABLE schema_migrations(
version INTEGER PRIMARY KEY,
checksum TEXT,
applied_at REAL,
app_version TEXT
);
CREATE TABLE proof_marker(id INTEGER);
-- transaction command hidden behind comment
COMMIT;
THIS IS INVALID;
"""


class GuardTests(unittest.TestCase):
    def test_exact_review_reproducer_no_tables_and_connection_reusable(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage=Storage(tmp)
            with self.assertRaises(SchemaError):migrate(storage,[Migration(1,PROOF)])
            c=connect(storage.database)
            try:
                self.assertFalse(c.in_transaction)
                self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[])
                self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],0)
                c.execute('BEGIN IMMEDIATE');c.execute('CREATE TABLE retry (id INTEGER)');c.rollback()
                self.assertFalse(c.in_transaction)
            finally:c.close()
            self.assertEqual(migrate(storage)['version'],len(load()))

    def test_comments_commands_and_failed_upgrade_preserve_data(self):
        commands=['COMMIT','eNd','ROLLBACK','BEGIN','SAVEPOINT hidden','RELEASE hidden',"ATTACH ':memory:' AS hidden",'DETACH main','VACUUM','PRAGMA user_version=99','PRAGMA foreign_keys=OFF']
        prefixes=['-- preceding comment\n  ','/* multi\nline ; COMMIT */\n\t','  -- first\n /* second */ ']
        with tempfile.TemporaryDirectory() as tmp:
            storage=Storage(tmp);migrate(storage)
            c=connect(storage.database)
            c.execute("INSERT INTO auth_rate_limits VALUES (?,'proof',1,2,NULL,60)",('a'*64,));c.close()
            for command in commands:
                for prefix in prefixes:
                    with self.subTest(command=command,prefix=prefix):
                        bad=Migration(len(load())+1,'CREATE TABLE proof_marker(id INTEGER);'+prefix+command+'; THIS IS INVALID;')
                        with self.assertRaises(SchemaError):migrate(storage,load()+[bad])
                        self.assertTrue(status(storage)['current'])
                        c=connect(storage.database)
                        try:
                            self.assertEqual(c.execute('SELECT attempts FROM auth_rate_limits').fetchone()[0],2)
                            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='proof_marker'").fetchone())
                            self.assertFalse(c.in_transaction)
                        finally:c.close()

    def test_guard_restores_authorizer_and_keeps_runner_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=connect(Storage(tmp).database)
            try:
                c.execute('BEGIN IMMEDIATE')
                with self.assertRaises(SchemaError):execute_migration_statement(c,'/* comment */ COMMIT;')
                self.assertTrue(c.in_transaction)
                c.rollback();self.assertFalse(c.in_transaction)
                c.execute('PRAGMA user_version=0')
            finally:c.close()

    def test_literals_and_legal_trigger_begin_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage=Storage(tmp);migrate(storage)
            sql="""CREATE TABLE proof_marker(value TEXT);
CREATE TRIGGER proof_trigger AFTER INSERT ON proof_marker WHEN NEW.value='COMMIT; END;'
BEGIN UPDATE proof_marker SET value='legal; COMMIT' WHERE rowid=NEW.rowid; END;
INSERT INTO proof_marker VALUES ('COMMIT; END;');"""
            extra=Migration(len(load())+1,sql)
            migrate(storage,load()+[extra])
            c=connect(storage.database)
            try:self.assertEqual(c.execute('SELECT value FROM proof_marker').fetchone()[0],'legal; COMMIT')
            finally:c.close()
