"""Explicit DTOs and bounded, parameterized scoped reads."""
import json
from urllib.parse import parse_qsl
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.time_units import date_range
from .policy import resource_id

TRIP_FIELDS = ('id', 'title', 'note', 'mode', 'route_version_id', 'status', 'created_at',
               'started_at', 'ended_at', 'revision', 'archived_at')
OBS_FIELDS = ('id', 'trip_id', 'signal_id', 'source', 'state', 'event_type',
              'server_received_at', 'measured_at', 'effective', 'correction_revision')
CONFIG_FIELDS = ('id', 'kind', 'logical_id', 'version', 'status', 'created_at', 'published_at', 'revision')


def pick(row, fields): return {key: row[key] for key in fields}
def trip_dto(trip, own):
    return {**pick(trip, TRIP_FIELDS), 'capabilities': {'read': True, 'export': own,
             'cv': own, 'replay': trip['status'] == 'COMPLETE' and trip['archived_at'] is None,
             'analysis': trip['status'] == 'COMPLETE' and trip['archived_at'] is None}}


def query(raw, allowed):
    if len(raw) > 2048: raise AuthError(400, 'BAD_REQUEST')
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=20)
    if len({key for key, _ in pairs}) != len(pairs) or any(key not in allowed for key, _ in pairs):
        raise AuthError(422, 'VALIDATION')
    return dict(pairs)


def integer(q, key, default=None, maximum=253402300799999):
    if key not in q: return default
    value = q[key]
    if not value.isascii() or not value.isdecimal() or len(value) > 15:
        raise AuthError(422, 'VALIDATION')
    result = int(value)
    if result > maximum: raise AuthError(422, 'VALIDATION')
    return result


def pagination(q):
    limit = integer(q, 'limit', 25, 100)
    offset = integer(q, 'offset', 0, 10000)
    if not limit: raise AuthError(422, 'VALIDATION')
    return limit, offset


def scope(q):
    result = q.get('scope', 'own')
    if result not in {'own', 'shared'}: raise AuthError(422, 'VALIDATION')
    return result


class Reads:
    def __init__(self, policy): self.policy, self.repo = policy, policy.repo

    def trips(self, raw, q):
        row, actor = self.policy.session(raw)
        shared = scope(q) == 'shared'
        if shared: self.policy.role(raw, {'ANALYST'})
        limit, offset = pagination(q)
        after, before = integer(q, 'from'), integer(q, 'to')
        date_range(after, before)
        status = q.get('status')
        if status is not None and status not in {'PLANNED', 'STARTING', 'RECORDING', 'FINALIZING', 'COMPLETE', 'INTERRUPTED'}:
            raise AuthError(422, 'VALIDATION')
        archived = q.get('archived', 'false')
        if archived not in {'true', 'false'}: raise AuthError(422, 'VALIDATION')
        clauses = ['t.owner_id=?'] if not shared else ["s.analyst_id=?", "s.revoked_at IS NULL", "t.status='COMPLETE'", 't.archived_at IS NULL']
        values = [actor.user_id]
        if not shared: clauses.append('t.archived_at IS ' + ('NOT ' if archived == 'true' else '') + 'NULL')
        for col, op, value in [('created_at', '>=', after), ('created_at', '<', before), ('status', '=', status), ('route_version_id', '=', q.get('route_id'))]:
            if value is not None:
                if col == 'route_version_id': resource_id(value)
                clauses.append('t.' + col + op + '?'); values.append(value)
        join = ' JOIN trip_shares s ON s.trip_id=t.id' if shared else ''
        with self.repo.database.transaction(False) as c:
            self.repo.user(c, actor, {'ANALYST'} if shared else None)
            rows = c.execute('SELECT t.* FROM trips t' + join + ' WHERE ' + ' AND '.join(clauses) + ' ORDER BY t.created_at DESC,t.id DESC LIMIT ? OFFSET ?', (*values, limit, offset)).fetchall()
        return {'items': [trip_dto(r, not shared) for r in rows], 'page': {'limit': limit, 'offset': offset}}

    def observations(self, raw, q):
        _, actor = self.policy.session(raw)
        shared = scope(q) == 'shared'
        if shared: self.policy.role(raw, {'ANALYST'})
        if 'trip_id' not in q: raise AuthError(422, 'TRIP_FILTER_REQUIRED')
        _, _, _, own = self.policy.trip(raw, q['trip_id'])
        # Scope is explicit; own cannot silently fall back to shared.
        if shared == own: raise AuthError(404, 'NOT_FOUND')
        limit, offset = pagination(q)
        rows = self.repo.list_observations(actor, q['trip_id'], shared=shared,
            after=integer(q, 'from'), before=integer(q, 'to'), signal=q.get('signal_id'),
            state=q.get('state'), event_type=q.get('event_type'), limit=limit, offset=offset)
        return {'items': [pick(r, OBS_FIELDS) for r in rows], 'page': {'limit': limit, 'offset': offset}}

    def corrections(self, raw, oid, q):
        (_, actor, _, own), observation = self.policy.observation(raw, oid)
        limit, offset = pagination(q)
        with self.repo.database.transaction(False) as c:
            self.repo.shared_trip(c, actor, observation['trip_id']) if not own else self.repo.own_trip(c, actor, observation['trip_id'])
            rows = [dict(r) for r in c.execute('SELECT * FROM observation_corrections WHERE observation_id=? ORDER BY sequence LIMIT ? OFFSET ?', (oid, limit, offset))]
        return {'items': [{**pick(r, ('id', 'observation_id', 'actor_id', 'sequence', 'server_at', 'reason')),
                          'before': json.loads(r['before_json']), 'after': json.loads(r['after_json'])} for r in rows],
                'page': {'limit': limit, 'offset': offset}}

    def configs(self, raw, q, cid=None):
        row, actor = self.policy.session(raw)
        status = q.get('status', 'PUBLISHED')
        if status not in {'PUBLISHED', 'DRAFT', 'ARCHIVED'}: raise AuthError(422, 'VALIDATION')
        if status != 'PUBLISHED': self.policy.role(raw, {'ANALYST', 'ADMIN'})
        limit, offset = pagination(q)
        clauses, values = ['status=?'], [status]
        if cid:
            clauses, values = ['id=?'], [resource_id(cid)]
        for col in ['kind', 'logical_id']:
            if col in q:
                if col == 'kind' and q[col] not in {'ROUTE', 'SIGNAL', 'MODEL'}: raise AuthError(422, 'VALIDATION')
                clauses.append(col + '=?'); values.append(q[col])
        with self.repo.database.transaction(False) as c:
            self.repo.user(c, actor)
            rows = c.execute('SELECT * FROM config_versions WHERE ' + ' AND '.join(clauses) + ' ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?', (*values, limit, offset)).fetchall()
        if cid and not rows: raise AuthError(404, 'NOT_FOUND')
        if any(r['status'] != 'PUBLISHED' for r in rows) and row['role'] == 'DRIVER': raise AuthError(403, 'FORBIDDEN')
        result = [{**pick(r, CONFIG_FIELDS), 'payload': public_config(json.loads(r['payload'])), 'publication_is_field_verification': False} for r in rows]
        return result[0] if cid else {'items': result, 'page': {'limit': limit, 'offset': offset}}


def duplicate_checked(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


# Until configuration write validation is integrated in stage8, refuse payloads
# containing storage/credential attributes rather than attempting to redact them.
def public_config(value):
    forbidden = {'password', 'password_hash', 'token', 'token_hash', 'secret', 'secret_hash',
                 'path', 'filepath', 'filename', 'raw_ref', 'media_ref', 'root', 'smtp_password'}
    def check(item, depth=0):
        if depth > 30: raise AuthError(409, 'CONFIG_INVALID')
        if isinstance(item, dict):
            if any(key.lower() in forbidden for key in item): raise AuthError(409, 'CONFIG_INVALID')
            for child in item.values(): check(child, depth+1)
        elif isinstance(item, list):
            for child in item: check(child, depth+1)
        elif isinstance(item, str):
            if item.startswith(('/', '\\')) or (len(item) > 2 and item[1:3] in {':/', ':\\'}):
                raise AuthError(409, 'CONFIG_INVALID')
        elif isinstance(item, float):
            import math
            if not math.isfinite(item): raise AuthError(409, 'CONFIG_INVALID')
    check(value)
    return value
