"""Runtime owns a process lease; individual transactions own SQLite connections."""
import sqlite3
from contextlib import contextmanager
from .locking import Lease
from .errors import SchemaError, Conflict


def connect(path, readonly=False):
    target = path.resolve().as_uri() + "?mode=ro" if readonly else str(path)
    connection = sqlite3.connect(target, uri=readonly, isolation_level=None, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        if not readonly:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
        return connection
    except Exception:
        connection.close()
        raise


class Database:
    def __init__(self, storage):
        self.storage = storage
        self.lease = None

    def __enter__(self):
        from .migrations import validate, load
        self.lease = Lease(self.storage)
        self.lease.__enter__()
        try:
            if not self.storage.database.is_file():
                raise SchemaError("Initialize the database explicitly with the CLI first")
            with self.connection() as connection:
                validate(connection, load(), require_current=True)
        except Exception:
            self.close()
            raise
        return self

    def close(self):
        if self.lease:
            self.lease.__exit__()
            self.lease = None

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def connection(self):
        if self.lease is None:
            raise SchemaError("Database runtime must be opened as a context manager")
        connection = connect(self.storage.database)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self, write=True):
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield connection
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise Conflict("A database integrity constraint rejected this operation") from exc
            except Exception:
                connection.rollback()
                raise
