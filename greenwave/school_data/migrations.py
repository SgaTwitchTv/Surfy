"""Checksummed migrations executed statement by statement in one transaction."""
import hashlib
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from .database import connect
from .locking import Lease
from .errors import SchemaError
from .time_units import now_ms, seconds_to_ms, timestamp_ms


@dataclass(frozen=True)
class Migration:
    version: int
    sql: str

    @property
    def checksum(self):
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


def load():
    return [Migration(int(p.name.split("_")[0]), p.read_text(encoding="utf-8"))
            for p in sorted((Path(__file__).parent / "sql").glob("*.sql"))]


def checks(connection):
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise SchemaError("Foreign key validation failed")
    if [r[0] for r in connection.execute("PRAGMA integrity_check")] != ["ok"]:
        raise SchemaError("SQLite integrity validation failed")


def validate(connection, migrations, require_current=False):
    versions = [m.version for m in migrations]
    if versions != list(range(1, len(migrations)+1)):
        raise SchemaError("Migration source versions must be contiguous")
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    mirror = connection.execute("PRAGMA user_version").fetchone()[0]
    if "schema_migrations" not in tables:
        if tables or mirror:
            raise SchemaError("Unrecognized database; automatic adoption is forbidden")
        rows = []
    else:
        rows = connection.execute("SELECT version,checksum FROM schema_migrations ORDER BY version").fetchall()
    if [r[0] for r in rows] != list(range(1, len(rows)+1)) or mirror != len(rows):
        raise SchemaError("Migration history and user_version disagree")
    if len(rows)>len(migrations):
        raise SchemaError("Database schema is newer than this application")
    for row, migration in zip(rows, migrations):
        if row[1] != migration.checksum:
            raise SchemaError("Applied migration checksum differs from its source")
    if require_current and len(rows)!=len(migrations):
        raise SchemaError("Database requires explicit migration")
    checks(connection)
    return {"version": len(rows), "latest": len(migrations), "current": len(rows)==len(migrations)}


def statements(sql):
    buffer = ""
    for line in sql.splitlines(keepends=True):
        # Scan at semicolons so multiple statements on a single line work too.
        for char in line:
            buffer += char
            if char == ";" and sqlite3.complete_statement(buffer):
                yield buffer
                buffer = ""
    if buffer.strip():
        raise SchemaError("Incomplete migration statement")



def execute_migration_statement(connection, statement):
    """SQLite authorizes actual operations, independent of comments/SQL spelling.
    Trigger BEGIN/END belongs to CREATE_TRIGGER, not SQLITE_TRANSACTION.
    Runner BEGIN/COMMIT/PRAGMAs execute outside this temporary authorization scope.
    """
    forbidden = {sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT,
                 sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA}
    def authorize(action, arg1, arg2, database, source):
        return sqlite3.SQLITE_DENY if action in forbidden else sqlite3.SQLITE_OK
    # VACUUM fails before SQLite's ATTACH authorizer event inside a transaction.
    # Strip leading comments only; literal/trigger content must remain untouched.
    leading = re.sub(r"\A(?:\s+|--[^\n]*(?:\n|$)|/\*.*?\*/)*", "", statement, flags=re.S)
    if re.match(r"VACUUM\b", leading, flags=re.I):
        raise SchemaError("VACUUM is forbidden inside a migration")
    connection.set_authorizer(authorize)
    try:
        connection.execute(statement)
    except sqlite3.DatabaseError as exc:
        if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_AUTH:
            raise SchemaError("Migration cannot control transactions, attachments or pragmas") from exc
        raise
    finally:
        connection.set_authorizer(None)

def migrate(storage, migrations=None, clock=now_ms):
    from .backup import snapshot
    migrations = load() if migrations is None else migrations
    with Lease(storage):
        existed = storage.database.exists()
        connection = connect(storage.database)
        connection.create_function("school_seconds_to_ms", 1, seconds_to_ms, deterministic=True)
        try:
            status = validate(connection, migrations)
            if status["current"]:
                return {**status, "backup": None}
            backup = None
            if existed:
                backup = storage._safe(storage.root / "backups" / ("before-migration-" + str(time.time_ns()) + ".sqlite3"))
                snapshot(connection, backup)
            connection.execute("BEGIN IMMEDIATE")
            try:
                for migration in migrations[status["version"]:]:
                    for statement in statements(migration.sql):
                        execute_migration_statement(connection, statement)
                    applied_at = timestamp_ms(clock())
                    # Historical v1 declares REAL seconds; v2 rebuilds it as INTEGER ms.
                    legacy_time = connection.execute("SELECT type FROM pragma_table_info('schema_migrations') WHERE name='applied_at'").fetchone()[0] == 'REAL'
                    if legacy_time:
                        applied_at /= 1000
                    connection.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                                       (migration.version, migration.checksum,
                                        applied_at,
                                        "school-data-v2"))
                    connection.execute("PRAGMA user_version=" + str(migration.version))
                result = validate(connection, migrations, require_current=True)
                connection.commit()
            except Exception:
                connection.rollback()
                validate(connection, migrations)
                raise
            return {**result, "backup": str(backup) if backup else None}
        finally:
            connection.close()


def status(storage):
    with Lease(storage):
        if not storage.database.exists():
            raise SchemaError("Database does not exist")
        connection = connect(storage.database, readonly=True)
        try:
            return validate(connection, load())
        finally:
            connection.close()
