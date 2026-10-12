"""Checksummed migrations executed statement by statement in one transaction."""
import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from .database import connect
from .locking import Lease
from .errors import SchemaError


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
                head = buffer.strip().split(None, 1)[0].rstrip(";").upper()
                if head in {"BEGIN", "COMMIT", "ROLLBACK", "END", "VACUUM", "ATTACH", "DETACH", "PRAGMA"}:
                    raise SchemaError("Migration cannot control transactions or connection pragmas")
                yield buffer
                buffer = ""
    if buffer.strip():
        raise SchemaError("Incomplete migration statement")


def migrate(storage, migrations=None, clock=time.time):
    from .backup import snapshot
    migrations = load() if migrations is None else migrations
    with Lease(storage):
        existed = storage.database.exists()
        connection = connect(storage.database)
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
                        connection.execute(statement)
                    connection.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                                       (migration.version, migration.checksum, clock(), "school-data-v1"))
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
