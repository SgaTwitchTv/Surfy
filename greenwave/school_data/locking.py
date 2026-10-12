"""Nonblocking process lease: one runtime OR one maintenance process per root."""
import os
from .errors import Busy


class Lease:
    def __init__(self, storage):
        self.storage = storage
        self.file = None

    def __enter__(self):
        self.storage.prepare()
        path = self.storage._safe(self.storage.root / ".school.lock")
        self.file = open(path, "a+b")
        try:
            self.file.seek(0, 2)
            if self.file.tell() == 0:
                self.file.write(b"0")
                self.file.flush()
            self.file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            self.file = None
            raise Busy("School runtime is active or maintenance is in progress") from exc
        return self

    def __exit__(self, *args):
        if self.file is not None:
            try:
                self.file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            finally:
                self.file.close()
                self.file = None
