"""SQLite online backup, checked restore and retained pre-restore snapshots.
Only school.sqlite3 is covered: GPS, manifests and media require a separate backup.
All supported consumers must hold the runtime lease.
"""
import os
import sqlite3
import time
from pathlib import Path
from .database import connect
from .errors import Invalid, Busy
from .locking import Lease
from .migrations import validate, load
from .storage import Storage


def snapshot(source, destination):
    destination = Path(destination)
    if destination.exists():
        raise Invalid("Backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
    return destination


def checked(path):
    # Guard legacy paths and symlinks, even for a CLI backup source outside root.
    path = Path(path)
    Storage(path.absolute().parent)._safe(path.absolute())
    connection = connect(path, readonly=True)
    try:
        validate(connection, load(), require_current=True)
    except Exception:
        connection.close()
        raise
    return connection


def backup(storage, destination):
    destination = Path(destination)
    storage._safe(destination)
    if destination == storage.database:
        raise Invalid("Backup must be a separate file")
    with Lease(storage):
        source = checked(storage.database)
        try:
            snapshot(source, destination)
        finally:
            source.close()
        check = checked(destination)
        check.close()
    return str(destination)


def restore(storage, source):
    source = Path(source).absolute()
    if source == storage.database.absolute():
        raise Invalid("Restore source must be a separate backup")
    with Lease(storage):
        backup_connection = checked(source)
        staging = storage._safe(storage.root / ("restore-" + str(time.time_ns()) + ".sqlite3"))
        previous = None
        try:
            snapshot(backup_connection, staging)
            checked(staging).close()
            if storage.database.exists():
                existing = connect(storage.database)
                try:
                    # Catch outstanding unmanaged WAL readers/writers as far as SQLite permits.
                    result = existing.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                    if result[0]:
                        raise Busy("Database WAL is in use")
                    existing.execute("BEGIN EXCLUSIVE")
                    existing.rollback()
                    previous = storage._safe(storage.root / "backups" / ("before-restore-" + str(time.time_ns()) + ".sqlite3"))
                    snapshot(existing, previous)
                finally:
                    existing.close()
            # Every supported runtime uses Lease; replacement happens only while it is stopped.
            os.replace(staging, storage.database)
            checked(storage.database).close()
            return {"restored": str(storage.database), "previous": str(previous) if previous else None}
        finally:
            backup_connection.close()
            if staging.exists():
                staging.unlink()
