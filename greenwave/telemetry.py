"""Append-only raw runs. Completed files are never reopened for writing.

UTC is ingestion/observation time, simulation/model seconds are separate.
An absent completion manifest means an interrupted or failed recording.
"""
import csv
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
from uuid import uuid4
import zipfile


FIELDS = ('schema_version','run_id','sequence','timestamp','simulation_seconds','model_seconds',
          'event','signal_id','source','latitude','longitude','speed_mps','heading','gps_accuracy',
          'current_corridor_position','next_signal','target_speed_mps','payload_json')
RUN_ID = re.compile(r'^[0-9a-f]{32}$')


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      default=lambda obj: obj.isoformat() if isinstance(obj, datetime) else _unsupported(obj))


def _unsupported(obj):
    raise TypeError(f'Unsupported log value: {type(obj).__name__}')


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='') as stream:
        stream.write(encode(value)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class RunLogger:
    def __init__(self, root):
        self.root = Path(root)
        self.run_id = None
        self.active = False
        self.error = None
        self.sequence = 0
        self.stream = None
        self.writer = None
        self.counts = {}

    def status(self):
        return dict(active=self.active, run_id=self.run_id, records=self.sequence, error=self.error)

    def _fail(self, error):
        self.error = f'Zapis przerwany: {error}. Surowe pliki pozostają na dysku.'
        self.active = False
        if self.stream:
            try: self.stream.close()
            except OSError: pass
        self.stream = self.writer = None

    def start(self, metadata):
        if self.active: raise ValueError('Nagranie już trwa')
        self.run_id = uuid4().hex
        self.error = None
        self.sequence = 0
        self.counts = {}
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            directory = self.root/self.run_id
            directory.mkdir()  # Exclusive creation: never reuse a run directory.
            write_new(directory/'metadata.json', dict(metadata, schema_version=1, run_id=self.run_id,
                format='GreenWave raw CSV v1', sample_interval_seconds=1,
                coordinate_policy='GPS unavailable: empty CSV cells; demo map coordinates are not measurements'))
            self.stream = (directory/'raw.csv').open('x', encoding='utf-8', newline='')
            self.writer = csv.DictWriter(self.stream, fieldnames=FIELDS)
            self.writer.writeheader()
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.active = True
        except (OSError, ValueError, TypeError) as error:
            self._fail(error)
            raise ValueError(self.error) from error

    def append(self, event, *, timestamp, simulation_seconds, model_seconds, payload=None, **fields):
        if not self.active: return False
        try:
            row = dict(schema_version=1, run_id=self.run_id, sequence=self.sequence+1,
                       timestamp=timestamp.isoformat(), simulation_seconds=simulation_seconds,
                       model_seconds=model_seconds, event=event, payload_json=encode(payload or {}), **fields)
            # Serialize before writing so validation errors cannot leave half a CSV row.
            buffer = io.StringIO(newline='')
            csv.DictWriter(buffer, fieldnames=FIELDS).writerow(row)
            self.stream.write(buffer.getvalue())
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.sequence += 1
            self.counts[event] = self.counts.get(event, 0)+1
            return True
        except (OSError, ValueError, TypeError) as error:
            self._fail(error)
            return False

    def finish(self, reason, **context):
        if not self.active: return
        if not self.append('RUN_END', payload=dict(reason=reason), **context): return
        try:
            self.stream.close()
            self.stream = self.writer = None
            directory = self.root/self.run_id
            write_new(directory/'complete.json', dict(schema_version=1, run_id=self.run_id,
                reason=reason, records=self.sequence, counts=self.counts,
                end_time=context['timestamp'], end_model_seconds=context['model_seconds'],
                sha256={name:digest(directory/name) for name in ('metadata.json','raw.csv')}))
            self.active = False
        except (OSError, ValueError, TypeError) as error:
            self._fail(error)

    def _directory(self, run_id):
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise ValueError('Invalid run ID')
        directory = self.root/run_id
        if not directory.is_dir() or directory.resolve().parent != self.root.resolve():
            raise ValueError('Run not found')
        if any((directory/name).exists() and (directory/name).resolve().parent != directory.resolve()
               for name in ('metadata.json','raw.csv','complete.json')):
            raise ValueError('Invalid run file')
        return directory

    def list_runs(self):
        if not self.root.exists(): return []
        runs = []
        for directory in self.root.iterdir():
            if not RUN_ID.fullmatch(directory.name): continue
            try:
                directory = self._directory(directory.name)
                metadata = json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
                complete = directory/'complete.json'
                status = 'RECORDING' if self.active and directory.name==self.run_id else 'COMPLETED' if complete.exists() else 'UNFINISHED'
                summary = json.loads(complete.read_text(encoding='utf-8')) if complete.exists() else {}
                runs.append(dict(run_id=directory.name, start_time=metadata['start_time'],
                    corridor_id=metadata['corridor_id'], status=status, reason=summary.get('reason'),
                    records=summary.get('records'),
                    external_samples=summary.get('counts',{}).get('EXTERNAL_TELEMETRY',0),
                    mode=metadata.get('timebase')))
            except (OSError, ValueError, KeyError):
                runs.append(dict(run_id=directory.name, start_time='', corridor_id='?', status='DAMAGED', records=None, external_samples=None))
        return sorted(runs, key=lambda run:run['start_time'], reverse=True)

    def export(self, run_id):
        directory = self._directory(run_id)
        if self.active and run_id == self.run_id:
            raise ValueError('Zakończ zapis przed pobraniem nagrania')
        files = [directory/name for name in ('metadata.json','raw.csv','complete.json') if (directory/name).exists()]
        if any(path.resolve().parent != directory.resolve() for path in files):
            raise ValueError('Invalid run file')
        if sum(path.stat().st_size for path in files) > 64*1024*1024:
            raise ValueError('Nagranie przekracza 64 MB; skopiuj katalog nagrania bezpośrednio z data/runs')
        # Do not repair or normalize a damaged raw log, even during export.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files: archive.writestr(path.name, path.read_bytes())
        return buffer.getvalue()
