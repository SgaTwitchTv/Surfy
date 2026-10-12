import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection

from greenwave.school import SchoolServer


class SchoolHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = SchoolServer(0, root=cls.temp.name, demo=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        cls.temp.cleanup()

    def call(self, path, data=None, cookie='', csrf='', headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        base = {'Cookie': cookie, 'X-CSRF-Token': csrf, **(headers or {})}
        connection.request('GET' if data is None else 'POST', path,
                           None if data is None else json.dumps(data), base)
        response = connection.getresponse()
        raw = response.read()
        result = (response.status, json.loads(raw) if 'application/json' in response.getheader('Content-Type', '') else raw, dict(response.getheaders()))
        connection.close()
        return result

    def login(self, role='driver'):
        status, body, headers = self.call('/school/api/login', dict(email=f'{role}@demo.local', password='GreenWave-demo-2026'))
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        return headers['Set-Cookie'].split(';')[0], body['csrf']

    def test_anonymous_and_legacy_gate(self):
        for path in ['/school/api/me', '/school/api/trips', '/api/state', '/api/runs', '/api/vision/status', '/lab']:
            self.assertEqual(self.call(path)[0], 401, path)
        driver, csrf = self.login()
        self.assertEqual(self.call('/api/runs', cookie=driver)[0], 403)
        self.assertEqual(self.call('/school/api/users', cookie=driver)[0], 403)
        self.assertEqual(self.call('/school/api/trips', dict(title='Trip', route_id='synthetic_s1_s5'), driver)[0], 403)
        self.assertEqual(self.call('/school/api/trips', dict(title='Trip', route_id='synthetic_s1_s5'), driver, csrf, {'Origin': 'http://evil.local'})[0], 403)
        analyst, _ = self.login('analyst')
        self.assertEqual(self.call('/lab', cookie=analyst)[0], 403)

    def test_owner_analyst_and_admin(self):
        cookie, csrf = self.login()
        status, trip, _ = self.call('/school/api/trips', dict(title='Private Trip', route_id='synthetic_s1_s5'), cookie, csrf)
        self.assertEqual(status, 201)
        other, other_csrf = self.login('other')
        rows = self.call('/school/api/trips?q=Private', cookie=other)[1]
        self.assertEqual(rows, [])
        self.assertEqual(self.call('/school/api/trips/update', dict(id=trip['id'], title='Stolen', note=''), other, other_csrf)[0], 404)
        analyst, _ = self.login('analyst')
        self.assertEqual(len(self.call('/school/api/trips?q=Private', cookie=analyst)[1]), 1)
        admin, _ = self.login('admin')
        self.assertEqual(self.call('/school/api/users', cookie=admin)[0], 200)
        self.assertEqual(self.call('/api/state', cookie=admin)[0], 200)
        self.assertEqual(self.call('/school/api/reset-requests', cookie=admin)[0], 200)

    def test_recording_and_export(self):
        cookie, csrf = self.login()
        trip = self.call('/school/api/trips', dict(title='Recorded', route_id='synthetic_s1_s5'), cookie, csrf)[1]
        command = lambda value: self.call('/school/api/navigation', dict(command=value, trip_id=trip['id']), cookie, csrf)
        self.assertEqual(command('start')[0], 200)
        state = self.call('/school/api/navigation', cookie=cookie)[1]
        self.assertEqual(state['active_trip_id'], trip['id'])
        self.assertTrue(state['recording']['active'])
        self.assertEqual(command('pause')[0], 200)
        self.assertEqual(command('finish')[0], 200)
        status, raw, _ = self.call('/school/api/export?id=' + trip['id'], cookie=cookie)
        self.assertEqual(status, 200)
        self.assertTrue(raw.startswith(b'PK'))
        self.assertEqual(command('start')[0], 400)

    def test_pairing_bound_to_account(self):
        cookie, csrf = self.login('other')
        code = self.call('/school/api/pair-code', {}, cookie, csrf)[1]['code']
        status, device, _ = self.call('/api/pair', {'code': code})
        self.assertEqual(status, 200)
        self.assertEqual(self.call('/api/pair', {'code': code})[0], 403)
        self.assertEqual(self.call('/school/api/me', cookie='gw_session=' + device['token'])[0], 403)
        self.assertEqual(self.call('/api/position', dict(session_id=device['session_id'], timestamp_seconds=100, latitude=52.2,
                            longitude=20.9, speed_mps=4, gps_accuracy_m=3), headers={'X-GreenWave-Token': device['token']})[0], 200)
        snapshot = self.call('/school/api/navigation', cookie=cookie)[1]
        self.assertEqual(snapshot['external_position']['speed_mps'], 4)
        self.assertFalse(snapshot['mapping']['recommendation_eligibility']['allowed'])

    def test_observation_correction_and_role_mutation(self):
        cookie, csrf = self.login()
        trip = self.call('/school/api/trips', dict(title='Evidence', route_id='synthetic_s1_s5'), cookie, csrf)[1]
        status, observation, _ = self.call('/school/api/observations', dict(trip_id=trip['id'], signal='S1', state='GREEN', kind='STATE_SEEN'), cookie, csrf)
        self.assertEqual(status, 201)
        other, other_csrf = self.login('other')
        self.assertEqual(self.call('/school/api/corrections', dict(id=observation['id'], state='RED', reason='Other account'), other, other_csrf)[0], 404)
        analyst, analyst_csrf = self.login('analyst')
        self.assertEqual(self.call('/school/api/corrections', dict(id=observation['id'], state='RED', reason='Verified correction'), analyst, analyst_csrf)[0], 201)
        history = self.call('/school/api/corrections?id='+observation['id'], cookie=cookie)[1]
        self.assertEqual(history[0]['actor'], 'Analityk Demo')
        self.assertEqual(self.call('/school/api/observations?state=RED', cookie=cookie)[1][0]['state'], 'GREEN')
        admin, admin_csrf = self.login('admin')
        users = self.call('/school/api/users', cookie=admin)[1]
        target = next(u for u in users if u['email']=='other@demo.local')
        self.assertEqual(self.call('/school/api/users', dict(id=target['id'], role='ANALYST', active=True), admin, admin_csrf)[0], 200)
        self.assertEqual(self.call('/school/api/me', cookie=other)[0], 401)
        self.call('/school/api/users', dict(id=target['id'], role='DRIVER', active=True), admin, admin_csrf)

    def test_host_and_android_session_refresh(self):
        self.assertEqual(self.call('/health', headers={'Host':'evil.local:'+str(self.server.server_port)})[0], 403)
        cookie, csrf = self.login('other')
        code = self.call('/school/api/pair-code', {}, cookie, csrf)[1]['code']
        device = self.call('/api/pair', {'code':code})[1]
        status, state, _ = self.call('/api/state', headers={'X-GreenWave-Token':device['token']})
        self.assertEqual(status, 200)
        self.assertEqual(set(state), {'session_id'})
        self.assertEqual(state['session_id'], device['session_id'])
        self.assertEqual(self.call('/school/api/export?id=missing', cookie=cookie)[0], 404)

    def test_bad_json_fields_reset_and_logout(self):
        self.assertEqual(self.call('/school/api/register', [1])[0], 400)
        self.assertEqual(self.call('/school/api/register', dict(email='bad'))[0], 400)
        self.assertEqual(self.call('/school/api/reset-password', dict(token='bad', password='a-long-password'))[0], 400)
        status, body, _ = self.call('/school/api/request-reset', dict(email='none@test.local'))
        self.assertEqual(status, 200)
        self.assertNotIn('token', body)
        cookie, csrf = self.login()
        self.assertEqual(self.call('/school/api/logout', {}, cookie, csrf)[0], 200)
        self.assertEqual(self.call('/school/api/me', cookie=cookie)[0], 401)


if __name__ == '__main__':
    unittest.main()
