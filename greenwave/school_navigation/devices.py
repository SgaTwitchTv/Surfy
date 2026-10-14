"""Phone credentials are scoped to a browser, boot and one authorized live drive."""
import hashlib
import hmac
import math
import re
import secrets
from greenwave.school_accounts.crypto import secret, token_hash
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data import Actor
from greenwave.school_data.errors import Denied
from greenwave.school_data.validation import text
from greenwave.school_records.writes import fields
from greenwave.school_resources.policy import resource_id

PHONE_FIELDS={'session_id','timestamp_seconds','latitude','longitude','gps_accuracy_m','speed_mps',
 'speed_accuracy_mps','heading_deg','heading_accuracy_deg','altitude_m','vertical_accuracy_m','is_mock',
 'source','device_id','stream_id','sample_sequence','elapsed_realtime_nanos','sent_elapsed_realtime_nanos'}


class Devices:
    def __init__(self, recorder):
        self.recorder=recorder;self.policy=recorder.policy;self.repo=recorder.repo
        self.key=self.policy.accounts.config.rate_key
        # A new boot never inherits a phone credential or fresh GPS.
        with self.repo.database.transaction() as c:
            now=self.repo.clock()
            c.execute("UPDATE devices SET status='REVOKED',token_hash=NULL,revoked_at=? WHERE boot_id!=? AND status='ACTIVE'",(now,recorder.boot))
            c.execute('UPDATE pairing_challenges SET revoked_at=? WHERE boot_id!=? AND used_at IS NULL AND revoked_at IS NULL',(now,recorder.boot))

    def real(self):
        if self.policy.accounts.config.profile!='real':raise AuthError(403,'REAL_PROFILE_REQUIRED')

    def code_hash(self, code):
        return hmac.new(self.key,('pair|'+code).encode('ascii'),hashlib.sha256).hexdigest()

    @staticmethod
    def dto(row):
        return {k:row[k] for k in ('id','label','status','last_seen_at')}

    def list(self, raw, q):
        from greenwave.school_records.paging import Paging
        _,actor=self.policy.session(raw)
        paging=Paging(self.repo,self.key);limit,_,cursor=paging.page(actor,'devices',q)
        clauses=['owner_id=?'];values=[actor.user_id]
        if 'status' in q:
            if q['status'] not in {'ACTIVE','REVOKED'}:raise AuthError(422,'VALIDATION')
            clauses.append('status=?');values.append(q['status'])
        if cursor['last'] is not None:
            clauses.append('(expiry,id)<(?,?)');values.extend(cursor['last'])
        with self.repo.database.connection() as c:
            rows=c.execute('SELECT * FROM devices WHERE '+' AND '.join(clauses)+' ORDER BY expiry DESC,id DESC LIMIT ?',(*values,limit+1)).fetchall()
        rows,page=paging.result(rows,limit,cursor,'expiry')
        return {'items':[self.dto(row) for row in rows],'page':page}

    def write(self, raw, did, body, revoke=False):
        fields(body,{'reason'} if revoke else {'label'})
        text(body['reason' if revoke else 'label'],3 if revoke else 1,500 if revoke else 80)
        with self.repo.atomic() as (repo,c):
            _,actor=self.policy.session(raw,connection=c)
            d=c.execute('SELECT * FROM devices WHERE id=? AND owner_id=?',(resource_id(did),actor.user_id)).fetchone()
            if not d:raise AuthError(404,'NOT_FOUND')
            if revoke:
                c.execute("UPDATE devices SET status='REVOKED',token_hash=NULL,revoked_at=COALESCE(revoked_at,?) WHERE id=?",(repo.clock(),did))
            else:c.execute('UPDATE devices SET label=? WHERE id=?',(body['label'],did))
            repo.audit(c,actor,'DEVICE_REVOKED' if revoke else 'DEVICE_LABEL','DEVICE',did,body.get('reason',''))
            result=self.dto(c.execute('SELECT * FROM devices WHERE id=?',(did,)).fetchone())
        self.recorder.reconcile_credentials()
        return result

    def challenge(self, raw, body):
        self.real();fields(body,{'label'});text(body['label'],1,80)
        self.policy.accounts.limits.take('PAIR_BROWSER',self.policy.session(raw)[0]['id'],10,900000)
        with self.repo.atomic() as (repo,c):
            row,actor=self.policy.session(raw,connection=c)
            for _ in range(32):
                code=f'{secrets.randbelow(1000000):06d}'
                if not c.execute('SELECT 1 FROM pairing_challenges WHERE code_hmac=? AND used_at IS NULL AND revoked_at IS NULL AND expiry>?',(self.code_hash(code),repo.clock())).fetchone():break
            else:raise AuthError(503,'PAIR_BUSY')
            cid=repo.pairing_challenge(actor,row['id'],self.code_hash(code),self.recorder.boot,body['label'])
            return {'id':cid,'challenge_id':cid,'code':code,'expires_at':repo.clock()+300000}

    def revoke_challenge(self,raw,cid,body):
        fields(body,set())
        with self.repo.atomic() as (repo,c):
            row,actor=self.policy.session(raw,connection=c)
            challenge=c.execute('SELECT id FROM pairing_challenges WHERE id=? AND owner_id=? AND parent_session_id=?',(resource_id(cid),actor.user_id,row['id'])).fetchone()
            if not challenge:raise AuthError(404,'NOT_FOUND')
            c.execute('UPDATE pairing_challenges SET revoked_at=COALESCE(revoked_at,?) WHERE id=?',(repo.clock(),cid))

    def pair(self,body,ip):
        self.real();fields(body,{'code','client_device_id','label'})
        if not isinstance(body['code'],str) or not re.fullmatch('[0-9]{6}',body['code']):raise AuthError(422,'VALIDATION')
        if not isinstance(body['client_device_id'],str) or not re.fullmatch('[A-Za-z0-9._:-]{1,80}',body['client_device_id']):raise AuthError(422,'VALIDATION')
        text(body['label'],1,80)
        self.policy.accounts.limits.take('PAIR_IP',ip,20,900000)
        self.policy.accounts.limits.take('PAIR_CODE',body['code'],5,300000)
        try:
            with self.repo.atomic() as (repo,c):
                challenge=c.execute('SELECT * FROM pairing_challenges WHERE code_hmac=? AND boot_id=? AND revoked_at IS NULL AND used_at IS NULL AND expiry>? AND attempts<5',(self.code_hash(body['code']),self.recorder.boot,repo.clock())).fetchone()
                if not challenge:raise AuthError(403,'PAIR_UNAVAILABLE')
                token=secret();did=repo.bind_device(Actor(challenge['owner_id']),challenge['id'],body['client_device_id'],token_hash(token),self.recorder.boot)
                c.execute('UPDATE devices SET label=? WHERE id=?',(body['label'],did))
        except Denied:raise AuthError(403,'PAIR_UNAVAILABLE') from None
        self.recorder.reconcile_credentials()
        return {'device_token':token,'device_id':did,'app_session_id':None,'server_version':'school-navigation-9'}

    def authenticate(self, header, c):
        self.real()
        try:
            if not isinstance(header,str) or not header.startswith('Bearer '):raise ValueError()
            digest=token_hash(header[7:])
            row=c.execute("SELECT d.* FROM devices d JOIN users u ON u.id=d.owner_id WHERE token_hash=? AND d.boot_id=? AND d.status='ACTIVE' AND d.revoked_at IS NULL AND d.expiry>? AND u.status='ACTIVE' AND d.security_version=u.security_version",(digest,self.recorder.boot,self.repo.clock())).fetchone()
            if not row:raise ValueError()
            self.repo.session(c,row['parent_session_id'],row['owner_id'])
            return row
        except (ValueError,Denied,AuthError):raise AuthError(403,'DEVICE_REPAIR_REQUIRED') from None

    def active(self, device):
        return next((ctx for ctx in self.recorder.contexts.values() if ctx.get('device_id')==device['id'] and ctx.get('device_credential')==device['token_hash'] and ctx['session_id']==device['parent_session_id'] and ctx.get('drive') and not ctx['drive'].closed),None)

    def session(self,header):
        with self.recorder.lock,self.repo.database.transaction(False) as c:
            device=self.authenticate(header,c);ctx=self.active(device)
            return {'app_session_id':None if ctx is None else ctx['id'],'active':ctx is not None,'repair_required':False}

    def validate_position(self,body):
        fields(body,PHONE_FIELDS)
        for k in ('device_id','stream_id'):
            if not isinstance(body[k],str) or not re.fullmatch('[A-Za-z0-9._:-]{1,80}',body[k]):raise AuthError(422,'VALIDATION')
        for k in ('sample_sequence','elapsed_realtime_nanos','sent_elapsed_realtime_nanos'):
            if type(body[k]) is not int or not 0<=body[k]<2**63:raise AuthError(422,'VALIDATION')
        if body['sent_elapsed_realtime_nanos']<body['elapsed_realtime_nanos'] or type(body['is_mock']) is not bool or body['source']!='ANDROID_FUSED':raise AuthError(422,'VALIDATION')
        for k in PHONE_FIELDS-{'session_id','source','device_id','stream_id','is_mock','sample_sequence','elapsed_realtime_nanos','sent_elapsed_realtime_nanos'}:
            v=body[k]
            if v is None and k not in {'timestamp_seconds','latitude','longitude'}:continue
            if type(v) not in {int,float} or not math.isfinite(v):raise AuthError(422,'VALIDATION')
            if k in {'timestamp_seconds','gps_accuracy_m','speed_mps','speed_accuracy_mps','heading_accuracy_deg','vertical_accuracy_m'} and v<0:raise AuthError(422,'VALIDATION')
        if not -90<=body['latitude']<=90 or not -180<=body['longitude']<=180 or (body['heading_deg'] is not None and not 0<=body['heading_deg']<360):raise AuthError(422,'VALIDATION')
        resource_id(body['session_id'])

    def ingest(self,header,body):
        self.validate_position(body)
        with self.repo.database.connection() as pre:
            device=self.authenticate(header,pre)
        self.policy.accounts.limits.take('TELEMETRY_DEVICE',device['id'],100,60000)
        with self.recorder.lock:
            ctx=None
            try:
                with self.repo.atomic() as (_,c):
                    device=self.authenticate(header,c);ctx=self.active(device)
                    if not ctx or body['session_id']!=ctx['id']:raise AuthError(409,'SESSION_CHANGED')
                    if body['device_id']!=device['client_device_id']:raise AuthError(403,'DEVICE_REPAIR_REQUIRED')
                    try:ctx['drive'].app.ingest_external_position(**{k:v for k,v in body.items() if k!='session_id'})
                    except ValueError:raise AuthError(422,'VALIDATION') from None
                    if not ctx['logger'].active or ctx['logger'].error:raise AuthError(503,'RECORDING_WRITE_FAILED')
                    provider=ctx['drive'].app.external_position
                    now=self.repo.clock()
                    c.execute('UPDATE devices SET last_seen_at=? WHERE id=?',(now,device['id']))
                    c.execute('UPDATE browser_sessions SET last_activity_at=? WHERE id=? AND absolute_expiry>?',(now,device['parent_session_id'],now))
                    return {'accepted':provider.last_update_accepted,'duplicate':not provider.last_update_accepted,'external_status':provider.status()}
            except AuthError as error:
                if error.code=='RECORDING_WRITE_FAILED' and ctx is not None:
                    ctx['drive'].close();self.recorder.close_failed_logger(ctx['logger'])
                    if getattr(self.recorder,'vision',None):self.recorder.vision.close_trip(ctx['trip_id'])
                    # Outside the ingest transaction; failed DB cleanup remains retriable
                    # by the existing watchdog/startup recovery and holds its SQL lease.
                    self.recorder.interrupt(ctx['trip_id'],'TELEMETRY_WRITE_FAILED')
                raise
