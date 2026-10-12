"""Explicit storage roots and identifiers, never paths from a browser DTO."""
import os
import re
from pathlib import Path
from .errors import Invalid


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise Invalid("Expected a controlled 32 character hex identifier")
    return value


class Storage:
    def __init__(self, root):
        if not root or not Path(root).is_absolute():
            raise Invalid("An explicit absolute school storage root is required")
        self.root = Path(root)
        # Reject legacy roots lexically, without inspecting their contents.
        parts = [part.lower() for part in self.root.parts]
        for a, b in zip(parts, parts[1:]):
            if (a, b) in {( "data", "runs"), ("data", "derived"), ("runtime", "school")}:
                raise Invalid("Legacy/private storage cannot be used as school storage")
        self._safe(self.root)

    def _safe(self, path):
        for parent in (path, *path.parents):
            if parent.is_symlink():
                raise Invalid("Symlinks are not permitted in school storage paths")
            if parent.exists():
                attributes = getattr(parent.lstat(), "st_file_attributes", 0)
                if attributes & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT, including junctions
                    raise Invalid("Reparse points are not permitted in school storage paths")
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError as exc:
            raise Invalid("Storage path escaped its root") from exc
        return path

    def prepare(self):
        self._safe(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def database(self):
        return self._safe(self.root / "school.sqlite3")

    def trip(self, owner_id, trip_id):
        return self._safe(self.root / "owners" / identifier(owner_id) / "trips" / identifier(trip_id))

    def run(self, owner_id, trip_id, run_id):
        return self._safe(self.trip(owner_id, trip_id) / "runs" / identifier(run_id))

    def derived(self, owner_id, trip_id):
        return self._safe(self.trip(owner_id, trip_id) / "derived")

    def cv(self, owner_id, trip_id, capture_id):
        return self._safe(self.trip(owner_id, trip_id) / "cv" / identifier(capture_id))

    def index(self, owner_id):
        return self._safe(self.root / "owners" / identifier(owner_id) / "indexes")

    def config(self, version_id):
        return self._safe(self.root / "shared" / "config" / identifier(version_id))
