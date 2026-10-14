from test_school_accounts import Fixture

class StaticUITests(Fixture):
    def test_explicit_modules_public_and_no_filesystem_fallback(self):
        for name in ['state','dates','validation','api','filters','dom','auth','records','lists','forms','details','navigation','roles','role_views','laboratory']:
            status,data,headers=self.request('GET','/school/static/portal/'+name+'.mjs')
            self.assertEqual(status,200,name)
            self.assertIn('application/javascript',dict(headers)['Content-Type'])
            self.assertNotIn('unsafe-inline',dict(headers)['Content-Security-Policy'])
        for path in ['/school/static/portal/missing.mjs','/school/static/portal/../../school.sqlite3','/school/static/portal/%2e%2e/secret','/school/static/portal/','/school/static/school.sqlite3','/runtime/school.sqlite3','/api/state']:
            self.assertEqual(self.request('GET',path)[0],403 if path=='/api/state' else 404,path)
        self.assertEqual(self.request('GET','/school/api/v1/trips')[0],401)

    def test_shell_uses_external_modules_and_retains_security_headers(self):
        status,html,headers=self.request('GET','/')
        self.assertEqual(status,200);self.assertIn('type="module"',html)
        self.assertNotIn('onclick=',html);self.assertNotIn('localStorage',html)
        h=dict(headers);self.assertEqual(h['Cache-Control'],'no-store');self.assertEqual(h['X-Content-Type-Options'],'nosniff')
        self.assertEqual(h['Referrer-Policy'],'no-referrer');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])


class ExportHeadTests(Fixture):
    def setUp(self):
        super().setUp()
        from scripts.school_resource_fixtures import populate
        self.fixture=populate(self.repo,self.service.passwords.hash('Valid password 123!'))

    def login_as(self,who):
        self.cookies={};self.preflight()
        status,data,_=self.auth('login',{'email':who+'@example.test','password':'Valid password 123!'})
        self.assertEqual(status,200);self.csrf=data['data']['csrf']

    def test_head_uses_owner_policy_and_no_zip_or_body(self):
        from unittest.mock import patch
        tid=self.fixture['trips']['shared']['id'];path='/school/api/v1/trips/'+tid+'/export'
        self.assertEqual(self.request('HEAD',path)[0],401)
        for who,expected in [('driver',200),('other',404),('analyst',404),('admin',404)]:
            self.login_as(who)
            with patch.object(self.server.resources.files,'export',side_effect=AssertionError('HEAD must not build ZIP')):
                status,data,headers=self.request('HEAD',path)
            self.assertEqual(status,expected);self.assertIsNone(data)
            if expected==200:self.assertEqual(dict(headers)['Content-Type'],'application/zip')
            else:self.assertEqual(dict(headers)['X-School-Error'],'NOT_FOUND')
        self.login_as('driver');self.auth('logout',{})
        self.assertEqual(self.request('HEAD',path)[0],401)
        for path in ['/school/api/v1/auth/me','/api/state','/runtime/school.sqlite3','/']:
            self.assertEqual(self.request('HEAD',path)[0],404)

    def test_head_integrity_and_host_are_enforced(self):
        self.login_as('driver');trip=self.fixture['trips']['shared'];path='/school/api/v1/trips/'+trip['id']+'/export'
        self.assertEqual(self.request('HEAD',path,headers={'Host':'evil.test'})[0],403)
        raw=self.storage.run(trip['owner_id'],trip['id'],trip['run_id'])/'raw.csv'
        raw.write_bytes(raw.read_bytes()+b'corrupt synthetic proof')
        status,data,headers=self.request('HEAD',path)
        self.assertEqual(status,409);self.assertIsNone(data);self.assertEqual(dict(headers)['X-School-Error'],'ARTIFACT_INVALID')
