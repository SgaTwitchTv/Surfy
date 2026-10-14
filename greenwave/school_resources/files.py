"""Read immutable M8/CV artifacts only under an authorized trip; bounded streaming."""
import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from greenwave.school_accounts.errors import AuthError
from .reads import duplicate_checked
from greenwave.telemetry import RunLogger
from greenwave.vision_contracts import decode_vision, VisionObservation
from .policy import resource_id

CHUNK = 65536


@dataclass
class Transfer:
    stream: object
    size: int
    validate: object
    mime: str = 'application/octet-stream'
    status: int = 200
    headers: dict = None
    release: object = lambda: None

    def close(self):
        try: self.stream.close()
        finally: self.release()


class ScopedLogger(RunLogger):
    def __init__(self, storage, trip):
        self.storage, self.trip = storage, trip
        super().__init__(storage.run(trip['owner_id'], trip['id'], trip['run_id']).parent)

    def _directory(self, run_id):
        if run_id != self.trip['run_id']: raise AuthError(404, 'NOT_FOUND')
        directory = self.storage.run(self.trip['owner_id'], self.trip['id'], run_id)
        for name in ('raw.csv', 'metadata.json', 'complete.json'):
            self.storage._safe(directory / name)
        return directory


class Files:
    def __init__(self, policy):
        self.policy, self.storage = policy, policy.repo.database.storage

    def path(self, root, name):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9]+', name):
            raise AuthError(409, 'ARTIFACT_INVALID')
        return self.storage._safe(root / name)

    def json(self, path):
        self.storage._safe(path)
        if path.stat().st_size > 1048576: raise AuthError(409, 'ARTIFACT_TOO_LARGE')
        value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=duplicate_checked,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite')))
        if not isinstance(value, dict): raise AuthError(409, 'ARTIFACT_INVALID')
        return value

    def digest(self, path, validate, max_size=256*1024*1024):
        self.storage._safe(path)
        if not path.is_file() or path.stat().st_size > max_size: raise AuthError(409, 'ARTIFACT_TOO_LARGE')
        value = hashlib.sha256()
        with path.open('rb') as stream:
            while True:
                validate()
                block = stream.read(CHUNK)
                if not block: break
                value.update(block)
        return value.hexdigest()

    def run(self, raw, tid, owner_only=False, *, basis=None):
        _, _, trip, _ = self.policy.bound_trip(raw, basis) if basis is not None else self.policy.trip(raw, tid, owner_only, closed=True)
        logger = ScopedLogger(self.storage, trip)
        root = logger._directory(trip['run_id'])
        validate = (lambda: self.policy.bound_trip(raw, basis)) if basis is not None else (lambda: self.policy.trip(raw, tid, owner_only, closed=True))
        manifest = self.json(root / 'complete.json')
        metadata = self.json(root / 'metadata.json')
        expected_ref = (root / 'raw.csv').relative_to(self.storage.root).as_posix()
        if trip['raw_ref'] != expected_ref or manifest.get('schema_version') != 1 or any(v.get('run_id') != trip['run_id'] for v in [manifest, metadata]):
            raise AuthError(409, 'ARTIFACT_INVALID')
        if self.digest(root / 'complete.json', validate) != trip['manifest_hash']:
            raise AuthError(409, 'ARTIFACT_INVALID')
        for name in ('raw.csv', 'metadata.json'):
            actual = self.digest(root / name, validate, 64*1024*1024)
            if manifest.get('sha256', {}).get(name) != actual or (name == 'raw.csv' and actual != trip['raw_hash']):
                raise AuthError(409, 'ARTIFACT_INVALID')
        if sum((root / n).stat().st_size for n in ('raw.csv', 'metadata.json', 'complete.json')) > 64*1024*1024:
            raise AuthError(409, 'ARTIFACT_TOO_LARGE')
        validate()
        return trip, logger, root, validate

    def export(self, raw, tid, release=lambda: None):
        trip, _, root, validate = self.run(raw, tid, True)
        stream = tempfile.TemporaryFile()
        try:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name in ('raw.csv', 'metadata.json', 'complete.json'):
                    with self.path(root, name).open('rb') as source, archive.open(name, 'w') as dest:
                        while True:
                            validate(); block = source.read(CHUNK)
                            if not block: break
                            dest.write(block)
            size = stream.tell(); stream.seek(0); validate()
            return Transfer(stream, size, validate, 'application/zip', headers={
                'Content-Disposition': 'attachment; filename="trip-' + trip['id'] + '.zip"'}, release=release)
        except BaseException:
            stream.close(); raise

    def capture(self, raw, tid, cid):
        _, _, trip, _ = self.policy.trip(raw, tid, True)
        root = self.storage.cv(trip['owner_id'], tid, resource_id(cid))
        if not (root / 'manifest.json').is_file(): raise AuthError(404, 'NOT_FOUND')
        manifest = self.json(root / 'manifest.json')
        if manifest.get('session_id') != cid or manifest.get('run_id') != trip['run_id']:
            raise AuthError(409, 'ARTIFACT_INVALID')
        return trip, root, manifest

    @staticmethod
    def capture_dto(manifest):
        return {'id': manifest['session_id'], 'status': manifest.get('status'),
                'complete': manifest.get('complete') is True,
                'frames_captured': manifest.get('frames_captured', 0),
                'diagnostic_only': True, 'live_prediction_eligible': False}

    def captures(self, raw, tid, q):
        from .reads import pagination
        _, _, trip, _ = self.policy.trip(raw, tid, True)
        root = self.storage._safe(self.storage.trip(trip['owner_id'], tid) / 'cv')
        limit, offset = pagination(q)
        ids = []
        if root.exists():
            for child in root.iterdir():
                if re.fullmatch('[0-9a-f]{32}', child.name): ids.append(child.name)
                if len(ids) > 1000: raise AuthError(409, 'CAPTURE_INDEX_REQUIRED')
        result = [self.capture_dto(self.capture(raw, tid, cid)[2]) for cid in sorted(ids)[offset:offset+limit]]
        return {'items': result, 'page': {'limit': limit, 'offset': offset}}

    def media(self, raw, tid, cid, segment, range_header):
        trip, root, manifest = self.capture(raw, tid, cid)
        if not manifest.get('complete'): raise AuthError(409, 'CAPTURE_INCOMPLETE')
        artifacts = [v for v in manifest.get('artifacts', []) if v.get('kind') == 'VIDEO']
        if segment >= len(artifacts): raise AuthError(404, 'NOT_FOUND')
        item = artifacts[segment]
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.(mp4|avi|mov|mkv|webm|m4v)', item.get('filename', '')):
            raise AuthError(409, 'ARTIFACT_INVALID')
        path = self.path(root, item['filename'])
        validate = lambda: self.policy.trip(raw, tid, True)
        if self.digest(path, validate) != item.get('sha256'): raise AuthError(409, 'ARTIFACT_INVALID')
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        headers = {'Accept-Ranges': 'bytes'}
        if range_header:
            match = re.fullmatch(r'bytes=([0-9]+)-([0-9]*)', range_header)
            if not match: raise AuthError(416, 'RANGE_INVALID')
            start = int(match[1]); end = min(size-1, int(match[2]) if match[2] else start+1048575)
            if start > end or end - start + 1 > 1048576: raise AuthError(416, 'RANGE_INVALID')
            status = 206; headers['Content-Range'] = f'bytes {start}-{end}/{size}'
        stream = path.open('rb'); stream.seek(start)
        return Transfer(stream, max(0, end-start+1), validate, 'video/x-msvideo' if path.suffix == '.avi' else 'video/mp4', status, headers)

    def events(self, raw, tid, cid, q):
        from .reads import pagination
        _, root, manifest = self.capture(raw, tid, cid)
        limit, offset = pagination(q)
        matches = [v for v in manifest.get('artifacts', []) if v.get('kind') == 'VISION_EVENTS']
        if not matches: return {'items': [], 'page': {'limit': limit, 'offset': offset}}
        item = matches[0]
        if item.get('filename') != 'events.jsonl': raise AuthError(409, 'ARTIFACT_INVALID')
        path = self.path(root, 'events.jsonl')
        validate = lambda: self.policy.trip(raw, tid, True)
        if self.digest(path, validate, 16*1024*1024) != item.get('sha256'): raise AuthError(409, 'ARTIFACT_INVALID')
        result, seen = [], 0
        with path.open(encoding='utf-8') as stream:
            while len(result) < limit:
                validate(); line = stream.readline(1048577)
                if not line: break
                if len(line) > 1048576: raise AuthError(409, 'ARTIFACT_TOO_LARGE')
                envelope = json.loads(line)
                for event in envelope.get('events', []):
                    observation = decode_vision(event['observation'])
                    if not isinstance(observation, VisionObservation): raise AuthError(409, 'ARTIFACT_INVALID')
                    if not re.fullmatch(re.escape(cid) + r'(?::[0-9]+)?', observation.detection.frame.session_id): raise AuthError(409, 'ARTIFACT_INVALID')
                    if seen >= offset and len(result) < limit:
                        result.append({'id': observation.observation_id, 'state': observation.detection.state,
                                       'event_type': observation.event_type, 'track_id': observation.detection.track_id,
                                       'frame_id': observation.detection.frame.frame_id, 'diagnostic_only': True})
                    seen += 1
        return {'items': result, 'page': {'limit': limit, 'offset': offset}}

    def event_exists(self,raw,tid,cid,eid):
        _,root,manifest=self.capture(raw,tid,cid)
        item=next((v for v in manifest.get('artifacts',[]) if v.get('kind')=='VISION_EVENTS'),None)
        if item is None:return False
        if item.get('filename')!='events.jsonl':raise AuthError(409,'ARTIFACT_INVALID')
        path=self.path(root,'events.jsonl');validate=lambda:self.policy.trip(raw,tid,True)
        if self.digest(path,validate,16*1024*1024)!=item.get('sha256'):raise AuthError(409,'ARTIFACT_INVALID')
        with path.open(encoding='utf-8') as stream:
            while True:
                validate();line=stream.readline(1048577)
                if not line:return False
                if len(line)>1048576:raise AuthError(409,'ARTIFACT_TOO_LARGE')
                for event in json.loads(line).get('events',[]):
                    obs=decode_vision(event['observation'])
                    if not isinstance(obs,VisionObservation) or not re.fullmatch(re.escape(cid)+r'(?::[0-9]+)?',obs.detection.frame.session_id):raise AuthError(409,'ARTIFACT_INVALID')
                    if obs.observation_id==eid:return True
