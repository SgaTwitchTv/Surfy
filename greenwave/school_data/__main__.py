"""Explicit database maintenance; no account/login/SMTP commands."""
import argparse
import json
import sqlite3
from .storage import Storage
from .errors import DataError
from .migrations import migrate, status
from .backup import backup, restore


def main(argv=None):
    parser = argparse.ArgumentParser(description="GreenWave School database maintenance (DB only)")
    parser.add_argument("--root", required=True, help="Absolute, dedicated NEW school data directory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("migrate")
    commands.add_parser("status")
    commands.add_parser("backup").add_argument("destination")
    commands.add_parser("restore").add_argument("source")
    args = parser.parse_args(argv)
    try:
        storage = Storage(args.root)
        if args.command in {"init", "migrate"}:
            result = migrate(storage)
        elif args.command == "status":
            result = status(storage)
        elif args.command == "backup":
            result = {"backup": backup(storage, args.destination)}
        else:
            result = restore(storage, args.source)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (DataError, sqlite3.Error, OSError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
