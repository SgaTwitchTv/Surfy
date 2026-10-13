import concurrent.futures
import contextlib
import dataclasses
import hashlib
import http.client
import io
import json
import socket
import tempfile
import threading
import time
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch
from greenwave.school_data import Actor,Database,Repository,Storage
from greenwave.school_data.migrations import migrate
from greenwave.school_accounts.config import Config
from greenwave.school_accounts.crypto import Passwords,password,token_hash
from greenwave.school_accounts.demo_mail import Inbox,SMTPServer
from greenwave.school_accounts.errors import AuthError
from greenwave.school_accounts.http import AccountsHTTPServer
from greenwave.school_accounts.service import AccountsService

PASS='Valid password 123!'
NEW='New valid password 456!'
PREFIX='/school/api/v1'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.storage=Storage(self.tmp.name);migrate(self.storage)
        self.db=Database(self.storage).__enter__();self.addCleanup(self.db.close)
        self.now=1700000000000
        self.repo=Repository(self.db,clock=lambda:self.now)
        self.inbox=Inbox();self.smtp=SMTPServer(('127.0.0.1',0),self.inbox)
        threading.Thread(target=self.smtp.serve_forever,daemon=True).start()
        self.addCleanup(self.smtp.server_close);self.addCleanup(self.smtp.shutdown)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.cfg=Config(f'http://127.0.0.1:{port}',(f'127.0.0.1:{port}',),b'a'*32,b'b'*32,port=port,smtp_port=self.smtp.server_address[1])
        self.service=AccountsService(self.repo,self.cfg,passwords=Passwords(n=1024))
        self.addCleanup(self.service.close)
        self.server=AccountsHTTPServer(('127.0.0.1',port),self.service)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.cookies={};self.csrf=''

    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.cfg.port,timeout=10)
        h={'Cookie':'; '.join(k+'='+v for k,v in self.cookies.items())}
        payload=None
        if method in {'POST','DELETE','PATCH'}:
            payload=json.dumps(body if body is not None else {})
            h.update({'Content-Type':'application/json','Origin':self.cfg.origin,'X-CSRF-Token':self.csrf})
        h.update(headers or {})
        c.request(method,path,payload,h);r=c.getresponse();raw=r.read();response_headers=r.getheaders()
        for k,v in response_headers:
            if k.lower()=='set-cookie':
                cookie=SimpleCookie();cookie.load(v)
                for name,morsel in cookie.items():
                    if morsel['max-age']=='0':self.cookies.pop(name,None)
                    else:self.cookies[name]=morsel.value
        try:data=json.loads(raw) if raw else None
        except ValueError:data=raw.decode()
        status=r.status;c.close();return status,data,response_headers

    def auth(self,path,body=None):return self.request('POST',PREFIX+'/auth/'+path,body)
    def preflight(self):
        status,data,_=self.request('GET',PREFIX+'/auth/preflight');self.assertEqual(status,200)
        self.csrf=data['data']['csrf']
    def register(self,address='driver@example.test'):
        self.preflight();return self.auth('register',{'email':address,'display_name':'Kierowca','password':PASS,'password_confirmation':PASS})
    def mail_token(self,purpose):
        self.service.mailer.queue.join()
        with self.inbox.lock:messages=list(self.inbox.messages)
        matching=[m for m in messages if '#'+purpose+'=' in m['body']]
        self.assertTrue(matching,'Expected an actual SMTP message')
        return matching[-1]['body'].split('#'+purpose+'=')[1].split()[0]
    def active(self):
        self.assertEqual(self.register()[0],202);token=self.mail_token('verify')
        self.preflight();self.assertEqual(self.auth('verify-email',{'token':token})[0],200)
        return token
    def login(self,value=PASS):
        self.preflight();status,data,headers=self.auth('login',{'email':'driver@example.test','password':value})
        if status==200:self.csrf=data['data']['csrf']
        return status,data,headers


class HTTPTests(Fixture):
    def test_actual_smtp_full_register_verify_login_logout(self):
        self.assertEqual(self.register(' DRIVER@EXAMPLE.TEST ')[0],202)
        self.assertEqual(self.login()[0],401)
        token=self.mail_token('verify')
        before=self.request('GET','/')[0];self.assertEqual(before,200)
        with self.db.connection() as c:self.assertIsNone(c.execute('SELECT used_at FROM account_tokens').fetchone()[0])
        self.preflight();self.assertEqual(self.auth('verify-email',{'token':token})[0],200)
        status,data,headers=self.login();self.assertEqual(status,200)
        cookie=[v for k,v in headers if k.lower()=='set-cookie' and v.startswith('gw_session=')][0]
        for flag in ['HttpOnly','SameSite=Strict','Path=/']:self.assertIn(flag,cookie)
        self.assertNotIn('Domain=',cookie);self.assertNotIn('Secure',cookie)
        status,data,headers=self.request('GET',PREFIX+'/auth/me');self.assertEqual(status,200)
        self.assertEqual(data['data']['user']['role'],'DRIVER')
        self.assertEqual(set(data['data']['user']),{'id','email','display_name','role','status','revision'})
        self.assertEqual(self.auth('logout',{})[0],204)
        self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],401)
        self.assertEqual(self.auth('logout',{})[0],204)

    def test_reset_flow_single_use_purpose_and_no_token_response(self):
        self.active();self.assertEqual(self.login()[0],200)
        self.preflight();status,data,_=self.auth('request-reset',{'email':'driver@example.test'})
        self.assertEqual(status,202);token=self.mail_token('reset')
        self.assertNotIn(token,json.dumps(data))
        self.assertEqual(self.auth('verify-email',{'token':token})[0],422)
        self.assertEqual(self.auth('reset-password',{'token':token,'password':NEW,'password_confirmation':NEW})[0],200)
        self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],401)
        self.preflight();self.assertEqual(self.auth('reset-password',{'token':token,'password':NEW,'password_confirmation':NEW})[0],422)
        self.assertEqual(self.login()[0],401);self.assertEqual(self.login(NEW)[0],200)

    def test_json_strict_fields_types_duplicates_size_and_nan(self):
        self.preflight()
        variants=[('[1]',422),('{"email":"a@example.test","email":"b@example.test"}',400),('{"email":NaN}',400),('{"email":Infinity}',400),('{"email":null}',422),('{"email":1}',422),('{"email":"a@example.test","role":"ADMIN"}',422)]
        for payload,expected in variants:
            c=http.client.HTTPConnection('127.0.0.1',self.cfg.port)
            c.request('POST',PREFIX+'/auth/request-reset',payload,{'Content-Type':'application/json','Origin':self.cfg.origin,'Cookie':'; '.join(k+'='+v for k,v in self.cookies.items()),'X-CSRF-Token':self.csrf})
            r=c.getresponse();r.read();self.assertEqual(r.status,expected);c.close()
        self.assertEqual(self.request('POST',PREFIX+'/auth/request-reset',{'email':'a@example.test'},headers={'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.request('POST',PREFIX+'/auth/request-reset',{'email':'x'*9000})[0],413)
        body={'email':'driver@example.test','display_name':'Driver','password':PASS,'password_confirmation':PASS,'role':'ADMIN'}
        self.assertEqual(self.auth('register',body)[0],422)
        with self.db.connection() as c:self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0],0)

    def test_host_origin_csrf_and_no_legacy_storage_access(self):
        self.preflight()
        for header in [{'Origin':'http://evil.test'},{'X-CSRF-Token':'wrong'},{'Host':'evil.test'}]:
            self.assertEqual(self.request('POST',PREFIX+'/auth/request-reset',{'email':'x@example.test'},header)[0],403)
        for path in ['/api/state','/api/control','/api/recordings','/runtime/school.sqlite3','/backups/v1.sqlite3','/school/api/v1/admin/users','/school/static/../../runtime/school.sqlite3']:
            self.assertEqual(self.request('GET',path)[0],404)
        self.assertEqual(self.request('GET',PREFIX+'/trips')[0],401)
        status,data,headers=self.request('GET',PREFIX+'/health');self.assertEqual(status,200);self.assertEqual(data['data'],{'ok':True,'deployment_mode':'demo'})
        response=dict(headers)
        self.assertEqual(response['Cache-Control'],'no-store');self.assertEqual(response['X-Content-Type-Options'],'nosniff')
        self.assertNotIn('unsafe-inline',response['Content-Security-Policy'])

    def test_fixation_preauth_and_reauth_rotation_old_secret_denied(self):
        self.active();self.cookies['gw_session']='fixed-unknown-secret'
        self.assertEqual(self.login()[0],200);old=self.cookies['gw_session'];old_csrf=self.csrf
        self.assertEqual(self.auth('reauth',{'password':PASS})[0],200)
        new=self.cookies['gw_session'];self.assertNotEqual(new,old)
        self.assertEqual(self.request('GET',PREFIX+'/auth/me',headers={'Cookie':'gw_session='+old})[0],401)
        self.cookies['gw_session']=new
        self.assertEqual(self.request('POST',PREFIX+'/auth/logout',{},headers={'X-CSRF-Token':old_csrf})[0],403)
        status,data,_=self.request('GET',PREFIX+'/auth/me');self.csrf=data['data']['csrf']
        self.assertEqual(self.auth('logout',{})[0],204)

    def test_idle_absolute_activity_and_security_version(self):
        self.active();self.login()
        raw=self.cookies['gw_session'];key=token_hash(raw)
        self.now+=59999;self.request('GET',PREFIX+'/auth/me')
        with self.db.connection() as c:self.assertEqual(c.execute('SELECT last_activity_at FROM browser_sessions WHERE secret_hash=?',(key,)).fetchone()[0],1700000000000)
        self.now+=1;self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],200)
        self.now+=1800000;self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],401)
        self.login();self.now+=28800000
        self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],401)
        self.login()
        with self.db.transaction() as c:c.execute('UPDATE users SET security_version=security_version+1')
        self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],401)

    def test_change_password_and_logout_all_revoke_other_sessions_and_devices(self):
        self.active();self.login();first=self.cookies['gw_session'];self.login();second=self.cookies['gw_session']
        row,actor=self.service.sessions.lookup(second)
        challenge=self.repo.pairing_challenge(actor,row['id'],'a'*64,'boot','Phone')
        self.repo.bind_device(actor,challenge,'phone','b'*64,'boot')
        self.assertEqual(self.auth('change-password',{'current_password':PASS,'new_password':NEW,'password_confirmation':NEW})[0],200)
        for raw in [first,second]:
            with self.assertRaises(AuthError):self.service.sessions.lookup(raw)
        with self.db.connection() as c:self.assertIsNone(c.execute('SELECT token_hash FROM devices').fetchone()[0])
        self.assertEqual(self.login(NEW)[0],200)
        self.assertEqual(self.auth('logout-all',{})[0],204)
        self.assertEqual(self.request('GET',PREFIX+'/auth/me')[0],401)

    def test_neutral_existing_missing_and_rate_limits_retry_after(self):
        self.active()
        self.preflight();existing=self.auth('request-reset',{'email':'driver@example.test'})
        missing=self.auth('request-reset',{'email':'missing@example.test'})
        self.assertEqual(existing[0],202);self.assertEqual(existing[1]['data'],missing[1]['data'])
        for i in range(5):self.assertEqual(self.login('wrong password')[0],401)
        status,data,headers=self.login();self.assertEqual(status,429);self.assertIn('Retry-After',dict(headers))
        self.now+=900001;self.assertEqual(self.login()[0],200)
        self.assertNotIn('driver@example.test',str(self.repo.database.storage.root))

    def test_verify_and_reset_expiry_block_and_invalid_common_error(self):
        self.register();token=self.mail_token('verify');self.now+=86400000
        self.preflight();status,data,_=self.auth('verify-email',{'token':token});self.assertEqual(status,422)
        invalid=self.auth('verify-email',{'token':'x'*43})[1]['error'];self.assertEqual(data['error'],invalid)
        self.register();token=self.mail_token('verify')
        with self.db.transaction() as c:c.execute("UPDATE users SET status='BLOCKED'")
        self.assertEqual(self.auth('verify-email',{'token':token})[0],422)
        self.assertEqual(self.login()[0],401)


class ServiceTests(Fixture):
    def test_concurrent_registration_and_driver_only(self):
        body={'email':' Race@Example.Test ','display_name':'Race','password':PASS,'password_confirmation':PASS}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.service.register(body,'synthetic-ip'),range(2)))
        self.assertEqual(results[0],results[1]);self.service.mailer.queue.join()
        with self.db.connection() as c:
            rows=c.execute('SELECT * FROM users').fetchall();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['role'],'DRIVER')

    def test_parallel_reset_one_success_and_transaction_rollback(self):
        self.active();self.service.request_reset({'email':'driver@example.test'},'synthetic-ip');token=self.mail_token('reset')
        body={'token':token,'password':NEW,'password_confirmation':NEW}
        def apply(_):
            try:self.service.use_token(body,'synthetic-ip','RESET');return 'OK'
            except AuthError as e:return e.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:self.assertCountEqual(list(pool.map(apply,range(2))),['OK','INVALID_TOKEN'])
        self.service.request_reset({'email':'driver@example.test'},'synthetic-ip');token=self.mail_token('reset');body['token']=token
        with patch.object(self.service,'revoke_all',side_effect=RuntimeError('synthetic transaction failure')):
            with self.assertRaises(RuntimeError):self.service.use_token(body,'synthetic-ip','RESET')
        with self.db.connection() as c:self.assertIsNone(c.execute('SELECT used_at FROM account_tokens WHERE secret_hash=?',(token_hash(token),)).fetchone()[0])
        self.assertEqual(self.service.use_token(body,'synthetic-ip','RESET')['message'],'Operacja zakończona. Zaloguj się ponownie.')

    def test_mail_failure_queue_capacity_restart_and_no_secret_logs(self):
        self.service.mailer.transport=lambda message:(_ for _ in ()).throw(RuntimeError('secret exception never printed'))
        output=io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            self.register();self.service.mailer.queue.join()
        self.assertEqual(output.getvalue(),'')
        with self.db.connection() as c:
            row=c.execute('SELECT * FROM account_tokens').fetchone();self.assertEqual(row['delivery_state'],'FAILED');self.assertIsNotNone(row['revoked_at'])
        held=[]
        while self.service.mailer.reserve():held.append(True)
        self.register('queue@example.test')
        for _ in held:self.service.mailer.release()
        with self.db.connection() as c:self.assertEqual(c.execute("SELECT count(*) FROM account_tokens t JOIN users u ON u.id=t.user_id WHERE u.email_normalized='queue@example.test'").fetchone()[0],0)
        user=self.repo.create_user('pending@example.test','Pending','fixture')
        self.repo.issue_account_token(user['id'],'VERIFY_EMAIL','d'*64)
        restarted=AccountsService(self.repo,self.cfg,passwords=Passwords(n=1024));restarted.close()
        with self.db.connection() as c:
            row=c.execute("SELECT * FROM account_tokens WHERE secret_hash=?",('d'*64,)).fetchone();self.assertEqual(row['delivery_state'],'FAILED');self.assertIsNotNone(row['revoked_at'])

    def test_bootstrap_conflict_audit_and_rehash(self):
        uid=self.service.bootstrap('admin@example.test','Admin',PASS)
        with self.assertRaises(AuthError):self.service.bootstrap('second@example.test','Admin2',PASS)
        self.assertEqual(self.repo.get_user(uid)['status'],'ACTIVE')
        with self.db.connection() as c:self.assertEqual(c.execute("SELECT count(*) FROM audit_events WHERE action='BOOTSTRAP_ADMIN'").fetchone()[0],1)
        self.active()
        user=self.service.find('driver@example.test')
        old=self.service.passwords.hash(PASS).replace('$v1$','$v0$')
        with self.db.transaction() as c:c.execute('UPDATE users SET password_hash=? WHERE id=?',(old,user['id']))
        self.login();self.assertIn('$v1$',self.repo.get_user(user['id'])['password_hash'])

    def test_slow_smtp_does_not_block_http_health(self):
        entered=threading.Event();release=threading.Event()
        def slow(message):entered.set();release.wait(3)
        self.service.mailer.transport=slow;self.register();self.assertTrue(entered.wait(2))
        try:self.assertEqual(self.request('GET',PREFIX+'/health')[0],200)
        finally:release.set();self.service.mailer.queue.join()


