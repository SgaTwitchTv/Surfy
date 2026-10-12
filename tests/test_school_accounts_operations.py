import contextlib
import dataclasses
import io
import json
import os
import tempfile
import threading
import unittest
from email.message import EmailMessage
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch,MagicMock
from greenwave.school_accounts.__main__ import main
from greenwave.school_accounts.demo_mail import InboxHandler
from greenwave.school_accounts.errors import AuthError
from greenwave.school_accounts.crypto import Passwords
from test_school_accounts import Fixture,PASS,PREFIX


class OperationsTests(Fixture):
    def test_local_demo_receiver_http_and_smtp_error_paths(self):
        self.active()
        server=ThreadingHTTPServer(('127.0.0.1',0),InboxHandler);server.inbox=self.inbox
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            import http.client
            for path,status in [('/',200),('/messages',200),('/unknown',404)]:
                c=http.client.HTTPConnection('127.0.0.1',server.server_port);c.request('GET',path);r=c.getresponse();r.read();self.assertEqual(r.status,status);c.close()
            c=http.client.HTTPConnection('127.0.0.1',server.server_port);c.request('GET','/',headers={'Host':'evil.test'});r=c.getresponse();r.read();self.assertEqual(r.status,403);c.close()
        finally:server.shutdown();server.server_close()
        # Actual local SMTP rejects non-synthetic recipients. Never contacts real SMTP.
        import smtplib
        with smtplib.SMTP('127.0.0.1',self.smtp.server_address[1]) as smtp:
            smtp.ehlo();smtp.mail('greenwave@example.test');self.assertEqual(smtp.rcpt('nobody@example.org')[0],550)
            self.assertEqual(smtp.docmd('DATA')[0],550);self.assertEqual(smtp.noop()[0],250);self.assertEqual(smtp.rset()[0],250)
            self.assertEqual(smtp.docmd('UNKNOWN')[0],502)

    def test_real_smtp_tls_transport_configuration_without_external_send(self):
        message=EmailMessage();message['To']='synthetic@example.test';message['From']='greenwave@example.test';message.set_content('synthetic')
        for mode in ['starttls','smtps']:
            self.service.mailer.config=dataclasses.replace(self.cfg,smtp_mode=mode,smtp_user='fixture',smtp_password='fixture')
            with patch('greenwave.school_accounts.mail.smtplib.SMTP') as plain,patch('greenwave.school_accounts.mail.smtplib.SMTP_SSL') as secure:
                self.service.mailer.smtp(message)
                factory=secure if mode=='smtps' else plain
                client=factory.return_value
                if mode=='starttls':client.starttls.assert_called_once()
                client.login.assert_called_once();client.send_message.assert_called_once()
                context=secure.call_args.kwargs['context'] if mode=='smtps' else client.starttls.call_args.kwargs['context']
                self.assertTrue(context.check_hostname)

    def test_cli_secrets_environment_bootstrap_no_password_argv(self):
        target=self.storage.root/'deployment-keys.json'
        env={'SCHOOL_SECRET_FILE':str(target),'SCHOOL_PUBLIC_BASE_URL':self.cfg.base_url,'SCHOOL_ALLOWED_HOSTS':','.join(self.cfg.hosts),'SCHOOL_PROFILE':'demo','SCHOOL_SMTP_PORT':str(self.smtp.server_address[1])}
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(['secrets','--output',str(target)]),0)
        with self.assertRaises(FileExistsError):main(['secrets','--output',str(target)])
        self.db.close()
        with patch.dict(os.environ,env,clear=True),patch('greenwave.school_accounts.__main__.getpass.getpass',side_effect=[PASS,PASS,PASS,PASS]),patch('greenwave.school_accounts.service.Passwords',return_value=Passwords(n=1024)),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['bootstrap-admin','--root',str(self.storage.root),'--email','bootstrap@example.test','--name','Bootstrap','--confirm-email-ownership']),0)
            with self.assertRaises(AuthError):main(['bootstrap-admin','--root',str(self.storage.root),'--email','second@example.test','--name','Second','--confirm-email-ownership'])
        self.assertEqual(set(json.loads(target.read_text(encoding='utf-8'))),{'csrf_key','rate_key'})

    def test_preauth_rotation_expiry_and_block_no_secret_exposure(self):
        self.preflight();first=self.cookies['gw_preauth'];old=self.csrf;self.preflight()
        self.assertEqual(self.request('POST',PREFIX+'/auth/request-reset',{'email':'x@example.test'},{'X-CSRF-Token':old})[0],403)
        current=dict(self.cookies)
        self.cookies['gw_preauth']=first
        self.assertEqual(self.request('POST',PREFIX+'/auth/request-reset',{'email':'x@example.test'},{'X-CSRF-Token':old})[0],403)
        self.cookies=current
        self.now+=900000
        self.assertEqual(self.auth('request-reset',{'email':'x@example.test'})[0],403)
        self.now=1700000000000;self.active();self.login()
        with self.db.transaction() as c:c.execute("UPDATE users SET status='BLOCKED'")
        status,data,_=self.request('GET',PREFIX+'/auth/me');self.assertEqual(status,401)
        serialized=json.dumps(data)
        for fragment in ['password_hash','secret_hash','school.sqlite3','Traceback','SELECT']:self.assertNotIn(fragment,serialized)
        with self.db.connection() as c:
            rows=' '.join(str(tuple(r)) for r in c.execute('SELECT * FROM audit_events'))
            self.assertNotIn(PASS,rows);self.assertNotIn(first,rows)

    def test_kdf_work_does_not_block_independent_http_request(self):
        entered=threading.Event();release=threading.Event();original=self.service.passwords.hash
        def slow(value):entered.set();release.wait(3);return original(value)
        result=[]
        with patch.object(self.service.passwords,'hash',side_effect=slow):
            thread=threading.Thread(target=lambda:result.append(self.service.register({'email':'slow@example.test','display_name':'Slow','password':PASS,'password_confirmation':PASS},'fixture-ip')));thread.start()
            self.assertTrue(entered.wait(1))
            try:self.assertEqual(self.request('GET',PREFIX+'/health')[0],200)
            finally:release.set();thread.join(5)
        self.assertEqual(len(result),1)

    def test_request_rate_ip_does_not_trust_unconfigured_forwarding(self):
        self.preflight()
        for index in range(10):
            response=self.request('POST',PREFIX+'/auth/request-reset',{'email':str(index)+'@example.test'},{'X-Forwarded-For':'192.0.2.'+str(index)})
            self.assertEqual(response[0],202)
        self.assertEqual(self.request('POST',PREFIX+'/auth/request-reset',{'email':'last@example.test'},{'X-Forwarded-For':'198.51.100.1'})[0],429)

    def test_key_rotation_invalidates_session_and_actual_starttls_failure(self):
        self.active();self.login();raw=self.cookies['gw_session']
        self.service.sessions.key=b'c'*32
        with self.assertRaises(AuthError):self.service.sessions.lookup(raw)
        self.service.sessions.key=self.cfg.csrf_key
        # Local receiver has no STARTTLS; worker must revoke, not mark SENT.
        self.service.mailer.config=dataclasses.replace(self.cfg,smtp_mode='starttls')
        self.service.request_reset({'email':'driver@example.test'},'synthetic-ip')
        self.service.mailer.queue.join()
        with self.db.connection() as c:
            row=c.execute("SELECT * FROM account_tokens WHERE purpose='RESET'").fetchone()
            self.assertEqual(row['delivery_state'],'FAILED');self.assertIsNotNone(row['revoked_at'])

    def test_neutral_http_transaction_error_and_strict_unicode(self):
        self.register();token=self.mail_token('verify')
        with patch.object(self.repo,'audit',side_effect=OSError('synthetic private exception')):
            status,data,_=self.auth('verify-email',{'token':token})
            self.assertEqual(status,503);self.assertNotIn('synthetic private',json.dumps(data))
        with self.db.connection() as c:
            self.assertIsNone(c.execute('SELECT used_at FROM account_tokens').fetchone()[0])
            self.assertEqual(c.execute('SELECT status FROM users').fetchone()[0],'PENDING_VERIFICATION')
        self.assertEqual(self.auth('verify-email',{'token':token})[0],200)
        self.assertEqual(self.auth('request-reset',{'email':'x@example.test','extra':'no'})[0],422)
        self.assertEqual(self.request('POST',PREFIX+'/auth/register',{'email':'x@example.test','display_name':'bad\ud800','password':PASS,'password_confirmation':PASS})[0],422)

    def test_wrong_current_password_and_limit_before_kdf(self):
        self.active();self.login()
        body={'current_password':'Wrong password 123','new_password':'New valid password 456','password_confirmation':'New valid password 456'}
        self.assertEqual(self.auth('change-password',body)[0],401)
        self.preflight()
        for index in range(3):self.assertEqual(self.auth('request-reset',{'email':'missing@example.test'})[0],202)
        with patch.object(self.service.passwords,'hash',side_effect=AssertionError('KDF must not run')):
            self.assertEqual(self.auth('request-reset',{'email':'missing@example.test'})[0],429)

    def test_cli_real_benchmark_reports_no_hashes_or_salts(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(main(['benchmark']),0)
        result=json.loads(output.getvalue())
        self.assertEqual(result['n'],131072);self.assertEqual(result['max_parallel'],2)
        self.assertGreater(result['median_seconds'],0)
        self.assertNotIn('scrypt$',output.getvalue());self.assertNotIn(PASS,output.getvalue())

    def test_kdf_capacity_does_not_consume_wrong_password_budget(self):
        self.active()
        self.service.passwords.slots.acquire();self.service.passwords.slots.acquire()
        try:
            for _ in range(6):self.assertEqual(self.login()[0],503)
        finally:self.service.passwords.slots.release();self.service.passwords.slots.release()
        self.assertEqual(self.login()[0],200)
