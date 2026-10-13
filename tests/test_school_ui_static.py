from test_school_accounts import Fixture

class StaticUITests(Fixture):
    def test_explicit_modules_public_and_no_filesystem_fallback(self):
        for name in ['state','dates','validation','api','filters','dom','auth','records','lists','forms','details','navigation']:
            status,data,headers=self.request('GET','/school/static/portal/'+name+'.mjs')
            self.assertEqual(status,200,name)
            self.assertIn('application/javascript',dict(headers)['Content-Type'])
            self.assertNotIn('unsafe-inline',dict(headers)['Content-Security-Policy'])
        for path in ['/school/static/portal/missing.mjs','/school/static/portal/../../school.sqlite3','/school/static/portal/%2e%2e/secret','/school/static/portal/','/school/static/school.sqlite3','/runtime/school.sqlite3','/api/state']:
            self.assertEqual(self.request('GET',path)[0],404,path)
        self.assertEqual(self.request('GET','/school/api/v1/trips')[0],401)

    def test_shell_uses_external_modules_and_retains_security_headers(self):
        status,html,headers=self.request('GET','/')
        self.assertEqual(status,200);self.assertIn('type="module"',html)
        self.assertNotIn('onclick=',html);self.assertNotIn('localStorage',html)
        h=dict(headers);self.assertEqual(h['Cache-Control'],'no-store');self.assertEqual(h['X-Content-Type-Options'],'nosniff')
        self.assertEqual(h['Referrer-Policy'],'no-referrer');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
