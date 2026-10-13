import csv
from datetime import datetime,timedelta,timezone
import hashlib
import json
from greenwave.telemetry import FIELDS,digest
from greenwave.analysis import RunAnalysis
from greenwave.school_resources.files import ScopedLogger


def utc(ms):return datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=ms)


class Raw:
    def __init__(self,storage):self.storage=storage
    def root(self,trip):return self.storage.run(trip['owner_id'],trip['id'],trip['run_id'])
    def rows(self,trip):
        path=self.storage._safe(self.root(trip)/'raw.csv')
        if path.stat().st_size>64*1024*1024:raise ValueError('Raw size limit')
        with path.open(encoding='utf-8',newline='') as stream:
            reader=csv.DictReader(stream)
            if tuple(reader.fieldnames or ())!=FIELDS:raise ValueError('Raw schema mismatch')
            try:rows=list(reader)
            except csv.Error:raise ValueError('Malformed CSV') from None
        for index,row in enumerate(rows,1):
            if set(row)!=set(FIELDS) or any(v is None for v in row.values()):raise ValueError('Incomplete CSV row')
            if row['run_id']!=trip['run_id'] or int(row['sequence'])!=index or row.get(None) is not None:raise ValueError('Raw sequence mismatch')
            if not isinstance(json.loads(row['payload_json']),dict):raise ValueError('Invalid raw payload')
            datetime.fromisoformat(row['timestamp'])
        return rows
    def validate(self,trip):
        root=self.root(trip)
        for name in ['raw.csv','metadata.json','complete.json']:self.storage._safe(root/name)
        for name in ['metadata.json','complete.json']:
            if (root/name).stat().st_size>1048576:raise ValueError('Metadata size limit')
        meta=json.loads((root/'metadata.json').read_text(encoding='utf-8'))
        complete=json.loads((root/'complete.json').read_text(encoding='utf-8'))
        if any(v.get('run_id')!=trip['run_id'] or v.get('schema_version')!=1 for v in [meta,complete]):raise ValueError('Manifest identity')
        if meta.get('school_owner_id')!=trip['owner_id'] or meta.get('school_trip_id')!=trip['id']:raise ValueError('Metadata owner binding')
        for name in ['metadata.json','raw.csv']:
            if complete.get('sha256',{}).get(name)!=digest(root/name):raise ValueError('Artifact hash mismatch')
        from collections import Counter
        from .paging import rfc3339
        from greenwave.school_accounts.errors import AuthError
        try:ended=rfc3339(complete['end_time'])
        except (AuthError,KeyError):raise ValueError('Invalid completion time') from None
        if trip.get('started_at') is not None and ended<trip['started_at']:raise ValueError('Completion precedes start')
        rows=self.rows(trip)
        if dict(Counter(r['event'] for r in rows))!=complete.get('counts'):raise ValueError('Event counts mismatch')
        if not rows or rows[0]['event']!='RUN_START' or rows[-1]['event']!='RUN_END' or len(rows)!=complete.get('records'):raise ValueError('Incomplete raw')
        RunAnalysis(ScopedLogger(self.storage,trip))._read(trip['run_id'])
        return (root/'raw.csv').relative_to(self.storage.root).as_posix(),digest(root/'raw.csv'),digest(root/'complete.json')
    def journal_sequence(self,trip,observation):
        for row in self.rows(trip):
            payload=json.loads(row['payload_json'])
            if payload.get('observation_id')==observation['id']:
                if row['event']!='MANUAL_OBSERVATION' or row['source']!='MANUAL' or row['signal_id']!=observation['signal_id'] or datetime.fromisoformat(row['timestamp'])!=utc(observation['server_received_at']) or payload.get('source_event_id')!=observation['source_event_id'] or payload.get('state')!=observation['state'] or payload.get('event_type')!=observation['event_type']:raise ValueError('Conflicting journal event')
                return int(row['sequence'])
        return None
