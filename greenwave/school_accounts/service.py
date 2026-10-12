import hashlib
import hmac
from greenwave.school_data import Actor
from greenwave.school_data.validation import email,text
from greenwave.school_data.errors import Invalid
from .crypto import Passwords,password,secret,token_hash
from .errors import AuthError
from .limits import Limits
from .sessions import Sessions
from .mail import Mailer


class AccountsService:
    def __init__(self,repo,config,passwords=None,transport=None,mail_capacity=100):
        self.repo,self.config=repo,config.validate()
        self.passwords=passwords or Passwords()
        self.limits=Limits(repo,config.rate_key)
        self.sessions=Sessions(repo,config.csrf_key)
        # Explicit startup recovery, no raw token retry after process restart.
        with repo.database.transaction() as c:
            c.execute("UPDATE account_tokens SET delivery_state='FAILED',revoked_at=COALESCE(revoked_at,?) WHERE delivery_state='PENDING'",(repo.clock(),))
        self.mailer=Mailer(repo,config,mail_capacity,transport)

    def close(self):
        self.mailer.close()

    def address(self,value):
        try:normalized=email(value)
        except Invalid:raise AuthError(422,'VALIDATION',{'email':'Podaj poprawny adres email.'}) from None
        if self.config.profile=='demo' and not normalized.endswith('@example.test'):
            raise AuthError(422,'VALIDATION',{'email':'Demo używa wyłącznie adresów @example.test.'})
        return normalized

    def find(self,normalized):
        with self.repo.database.transaction(False) as c:
            row=c.execute('SELECT * FROM users WHERE email_normalized=?',(normalized,)).fetchone()
            return dict(row) if row else None

    def issue(self,c,user,purpose,raw):
        now=self.repo.clock();tid=self.repo.new_id()
        c.execute('UPDATE account_tokens SET revoked_at=? WHERE user_id=? AND purpose=? AND used_at IS NULL AND revoked_at IS NULL',(now,user['id'],purpose))
        c.execute("INSERT INTO account_tokens VALUES (?,?,?,?,?,?,?,NULL,NULL,'PENDING')",(tid,user['id'],purpose,token_hash(raw),user['security_version'],now,now+(900000 if purpose=='RESET' else 86400000)))
        return tid

    def register(self,body,ip):
        address=self.address(body['email'])
        try:text(body['display_name'],1,80)
        except Invalid:raise AuthError(422,'VALIDATION',{'display_name':'Nazwa: 1–80 znaków, bez znaków sterujących.'}) from None
        password(body['password'],body['password_confirmation'])
        self.limits.take('REGISTER_IP',ip,5,3600000)
        self.limits.take('ACTIVATE_EMAIL',address,3,3600000)
        self.limits.take('ACTIVATE_IP',ip,10,3600000)
        # Always hash valid registration input, also for an existing address.
        encoded=self.passwords.hash(body['password'])
        reserved=self.mailer.reserve();job=None
        try:
            with self.repo.database.transaction() as c:
                user=c.execute('SELECT * FROM users WHERE email_normalized=?',(address,)).fetchone()
                if not user:
                    uid=self.repo.new_id();now=self.repo.clock()
                    c.execute("INSERT INTO users(id,email_normalized,email_display,display_name,password_hash,role,status,created_at,updated_at) VALUES (?,?,?,?,?,'DRIVER','PENDING_VERIFICATION',?,?)",(uid,address,body['email'].strip(),body['display_name'],encoded,now,now))
                    user=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
                    self.repo.audit(c,None,'AUTH_REGISTER','USER',uid)
                if user['status']=='PENDING_VERIFICATION' and reserved:
                    raw=secret();tid=self.issue(c,user,'VERIFY_EMAIL',raw)
                    job=(tid,address,'VERIFY_EMAIL',raw)
            if job:self.mailer.submit(*job);reserved=False
        finally:
            if reserved:self.mailer.release()
        return {'message':'Jeśli operacja jest możliwa, otrzymasz wiadomość. Sprawdź pocztę.'}

    def request_reset(self,body,ip):
        address=self.address(body['email'])
        self.limits.take('RESET_EMAIL',address,3,3600000)
        self.limits.take('RESET_IP',ip,10,3600000)
        reserved=self.mailer.reserve();job=None
        try:
            with self.repo.database.transaction() as c:
                user=c.execute('SELECT * FROM users WHERE email_normalized=?',(address,)).fetchone()
                if user and reserved and user['status'] in {'ACTIVE','PENDING_VERIFICATION'}:
                    purpose='RESET' if user['status']=='ACTIVE' else 'VERIFY_EMAIL'
                    raw=secret();tid=self.issue(c,user,purpose,raw);job=(tid,address,purpose,raw)
            if job:self.mailer.submit(*job);reserved=False
        finally:
            if reserved:self.mailer.release()
        return {'message':'Jeśli operacja jest możliwa, otrzymasz wiadomość. Sprawdź pocztę.'}

    def revoke_all(self,c,user_id,now):
        for table in ['browser_sessions','account_tokens']:
            c.execute(f'UPDATE {table} SET revoked_at=COALESCE(revoked_at,?) WHERE user_id=?',(now,user_id))
        c.execute("UPDATE devices SET token_hash=NULL,status='REVOKED',revoked_at=COALESCE(revoked_at,?) WHERE owner_id=?",(now,user_id))
        c.execute('UPDATE pairing_challenges SET revoked_at=COALESCE(revoked_at,?) WHERE owner_id=?',(now,user_id))

    def use_token(self,body,ip,purpose):
        self.limits.take('TOKEN_USE_IP',ip,10,900000)
        key=token_hash(body['token'])
        encoded=None
        if purpose=='RESET':
            password(body['password'],body['password_confirmation'])
            encoded=self.passwords.hash(body['password'])
        with self.repo.database.transaction() as c:
            row=c.execute("SELECT t.*,u.status FROM account_tokens t JOIN users u ON u.id=t.user_id WHERE t.secret_hash=? AND t.purpose=? AND t.used_at IS NULL AND t.revoked_at IS NULL AND t.expiry>? AND t.security_version=u.security_version AND ((t.purpose='RESET' AND u.status='ACTIVE') OR (t.purpose='VERIFY_EMAIL' AND u.status='PENDING_VERIFICATION'))",(key,purpose,self.repo.clock())).fetchone()
            if not row:raise AuthError(422,'INVALID_TOKEN')
            now=self.repo.clock()
            c.execute('UPDATE account_tokens SET used_at=? WHERE id=?',(now,row['id']))
            if purpose=='VERIFY_EMAIL':
                c.execute("UPDATE users SET status='ACTIVE',verified_email_at=?,updated_at=?,revision=revision+1 WHERE id=?",(now,now,row['user_id']))
            else:
                c.execute('UPDATE users SET password_hash=?,security_version=security_version+1,revision=revision+1,updated_at=? WHERE id=?',(encoded,now,row['user_id']))
                self.revoke_all(c,row['user_id'],now)
            self.repo.audit(c,Actor(row['user_id']),'AUTH_'+purpose,'USER',row['user_id'])
        return {'message':'Operacja zakończona. Zaloguj się ponownie.'}

    def login(self,body,ip):
        address=self.address(body['email'])
        if not isinstance(body['password'],str):raise AuthError(422,'VALIDATION',{'password':'Podaj hasło.'})
        self.limits.take('LOGIN_IP',ip,30,900000)
        self.limits.take('LOGIN_EMAIL',address,5,900000)
        user=self.find(address)
        good,rehash=self.passwords.verify(body['password'],user['password_hash'] if user else self.passwords.dummy)
        if not good or not user or user['status']!='ACTIVE':raise AuthError(401,'UNAUTHORIZED')
        replacement=self.passwords.hash(body['password']) if rehash else None
        with self.repo.database.transaction() as c:
            fresh=c.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
            if fresh['status']!='ACTIVE' or fresh['security_version']!=user['security_version'] or fresh['password_hash']!=user['password_hash']:
                raise AuthError(401,'UNAUTHORIZED')
            if replacement:c.execute('UPDATE users SET password_hash=? WHERE id=?',(replacement,user['id']))
            raw=self.sessions.create(c,fresh)
            self.repo.audit(c,Actor(user['id']),'AUTH_LOGIN','USER',user['id'])
        self.limits.clear('LOGIN_EMAIL',address)
        row,_=self.sessions.lookup(raw,False)
        return raw,self.sessions.dto(raw,row)

    def reauth(self,body,raw,row):
        self.limits.take('REAUTH_SESSION',row['id'],5,900000)
        user=self.repo.get_user(row['user_id'])
        good,_=self.passwords.verify(body['password'],user['password_hash'])
        if not good:raise AuthError(401,'UNAUTHORIZED')
        with self.repo.database.transaction() as c:
            self.guard_current(c,row,user)
            fresh=self.sessions.rotate(c,row)
            self.repo.audit(c,Actor(user['id']),'AUTH_REAUTH','USER',user['id'])
        new_row,_=self.sessions.lookup(fresh,False)
        return fresh,{**self.sessions.dto(fresh,new_row),'authenticated_until':self.repo.clock()+300000}

    def guard_current(self,c,row,user):
        fresh=c.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
        session=c.execute('SELECT * FROM browser_sessions WHERE id=?',(row['id'],)).fetchone()
        now=self.repo.clock()
        if not fresh or fresh['status']!='ACTIVE' or fresh['security_version']!=row['security_version'] or fresh['password_hash']!=user['password_hash'] or not session or session['secret_hash']!=row['secret_hash'] or session['revoked_at'] is not None or session['absolute_expiry']<=now or session['last_activity_at']+1800000<=now:
            raise AuthError(401,'UNAUTHORIZED')

    def change_password(self,body,row):
        password(body['new_password'],body['password_confirmation'])
        self.limits.take('REAUTH_SESSION',row['id'],5,900000)
        user=self.repo.get_user(row['user_id'])
        good,_=self.passwords.verify(body['current_password'],user['password_hash'])
        if not good:raise AuthError(401,'UNAUTHORIZED')
        encoded=self.passwords.hash(body['new_password'])
        with self.repo.database.transaction() as c:
            self.guard_current(c,row,user);now=self.repo.clock()
            c.execute('UPDATE users SET password_hash=?,security_version=security_version+1,revision=revision+1,updated_at=? WHERE id=?',(encoded,now,user['id']))
            self.revoke_all(c,user['id'],now)
            self.repo.audit(c,Actor(user['id']),'AUTH_PASSWORD_CHANGED','USER',user['id'])
        return {'message':'Hasło zmienione. Zaloguj się ponownie.'}

    def logout(self,row,all_sessions=False):
        with self.repo.database.transaction() as c:
            now=self.repo.clock()
            if all_sessions:self.revoke_all(c,row['user_id'],now)
            else:
                c.execute('UPDATE browser_sessions SET revoked_at=COALESCE(revoked_at,?) WHERE id=?',(now,row['id']))
                c.execute("UPDATE devices SET token_hash=NULL,status='REVOKED',revoked_at=? WHERE parent_session_id=?",(now,row['id']))
                c.execute('UPDATE pairing_challenges SET revoked_at=COALESCE(revoked_at,?) WHERE parent_session_id=?',(now,row['id']))
            self.repo.audit(c,Actor(row['user_id']),'AUTH_LOGOUT_ALL' if all_sessions else 'AUTH_LOGOUT','USER',row['user_id'])

    def bootstrap(self,address,name,value):
        address=self.address(address);text(name,1,80);encoded=self.passwords.hash(value)
        with self.repo.database.transaction() as c:
            if c.execute("SELECT 1 FROM users WHERE role='ADMIN' AND status='ACTIVE'").fetchone():
                raise AuthError(409,'ADMIN_EXISTS')
            if c.execute('SELECT 1 FROM users WHERE email_normalized=?',(address,)).fetchone():
                raise AuthError(409,'ACCOUNT_EXISTS')
            uid=self.repo.new_id();now=self.repo.clock()
            c.execute("INSERT INTO users(id,email_normalized,email_display,display_name,password_hash,role,status,verified_email_at,created_at,updated_at) VALUES (?,?,?,?,?,'ADMIN','ACTIVE',?,?,?)",(uid,address,address,name,encoded,now,now,now))
            self.repo.audit(c,None,'BOOTSTRAP_ADMIN','USER',uid,reason='Operator explicitly confirmed email ownership')
        return uid
