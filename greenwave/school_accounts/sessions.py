import hashlib
import hmac
import threading
from greenwave.school_data import Actor
from .crypto import secret,token_hash,csrf
from .errors import AuthError


class Sessions:
    def __init__(self,repo,key):
        self.repo,self.key=repo,key
        self.preauth={}
        self.lock=threading.Lock()

    def preflight(self):
        raw=secret(); identifier=self.repo.new_id(); expiry=self.repo.clock()+900000
        with self.lock:
            self.preauth={key:value for key,value in self.preauth.items() if value[1]>self.repo.clock()}
            if len(self.preauth)>=1000:
                raise AuthError(503,'PREAUTH_BUSY')
            self.preauth[token_hash(raw)]=(identifier,expiry)
        return raw,{'csrf':csrf(self.key,raw,identifier,'preauth'),'expiry':expiry}

    def check_preauth(self,raw,value):
        try:key=token_hash(raw)
        except AuthError:raise AuthError(403,'CSRF') from None
        with self.lock:record=self.preauth.get(key)
        if not record or record[1]<=self.repo.clock() or not isinstance(value,str) or not hmac.compare_digest(value,csrf(self.key,raw,record[0],'preauth')):
            raise AuthError(403,'CSRF')

    def forget_preauth(self,raw):
        with self.lock:self.preauth.pop(token_hash(raw),None)

    def lookup(self,raw,touch=True,*,connection=None):
        try:key=token_hash(raw)
        except AuthError:raise AuthError(401,'UNAUTHORIZED') from None
        if connection is not None:
            return self._lookup(connection,raw,key,touch)
        with self.repo.database.transaction() as c:
            return self._lookup(c,raw,key,touch)

    def _lookup(self,c,raw,key,touch):
        row=c.execute("SELECT s.*,u.email_display,u.display_name,u.role,u.status,u.security_version AS current_version,u.revision AS user_revision FROM browser_sessions s JOIN users u ON u.id=s.user_id WHERE s.secret_hash=?",(key,)).fetchone()
        now=self.repo.clock()
        if not row or row['status']!='ACTIVE' or row['security_version']!=row['current_version'] or row['revoked_at'] is not None or row['absolute_expiry']<=now or row['last_activity_at']+1800000<=now:
            raise AuthError(401,'UNAUTHORIZED')
        expected_hash=hashlib.sha256(csrf(self.key,raw,row['id'],'session').encode()).hexdigest()
        if not hmac.compare_digest(row['csrf_hash'],expected_hash):
            raise AuthError(401,'UNAUTHORIZED')
        if touch and now-row['last_activity_at']>=60000:
            c.execute('UPDATE browser_sessions SET last_activity_at=? WHERE id=?',(now,row['id']))
        return dict(row),Actor(row['user_id'],row['authenticated_at'])

    def check_csrf(self,raw,row,value):
        expected=csrf(self.key,raw,row['id'],'session')
        if not isinstance(value,str) or not hmac.compare_digest(value,expected) or not hmac.compare_digest(hashlib.sha256(value.encode()).hexdigest(),row['csrf_hash']):
            raise AuthError(403,'CSRF')

    def dto(self,raw,row):
        return {'user':{'id':row['user_id'],'email':row['email_display'],'display_name':row['display_name'],'role':row['role'],'status':row['status'],'revision':row['user_revision']},
                'csrf':csrf(self.key,raw,row['id'],'session'),'expires_at':row['absolute_expiry']}

    def create(self,c,user):
        raw=secret(); sid=self.repo.new_id(); now=self.repo.clock()
        value=csrf(self.key,raw,sid,'session')
        c.execute('INSERT INTO browser_sessions VALUES (?,?,?,?,?,?,?,?,?,NULL)',(sid,user['id'],token_hash(raw),hashlib.sha256(value.encode()).hexdigest(),user['security_version'],now,now,now,now+28800000))
        return raw

    def rotate(self,c,row):
        raw=secret();now=self.repo.clock();value=csrf(self.key,raw,row['id'],'session')
        c.execute('UPDATE browser_sessions SET secret_hash=?,csrf_hash=?,authenticated_at=?,last_activity_at=? WHERE id=?',(token_hash(raw),hashlib.sha256(value.encode()).hexdigest(),now,now,row['id']))
        return raw
