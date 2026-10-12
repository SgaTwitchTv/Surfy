import tempfile
import unittest
from pathlib import Path

from greenwave.school_store import SchoolStore, AccessError, password_hash, matches


class SchoolStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 1000
        self.store = SchoolStore(Path(self.temp.name) / 'test.db', lambda: self.now)
        self.uid = self.store.register(dict(email='driver@test.local', name='Driver', password='long-password-123'))
        self.token, self.csrf = self.store.login(dict(email='driver@test.local', password='long-password-123'), 'test')
        self.user = self.store.session(self.token)
        self.other = dict(id=self.store.register(dict(email='other@test.local', name='Other', password='long-password-123')), role='DRIVER')
        self.analyst = dict(id=self.store.register(dict(email='analyst@test.local', name='Analyst', password='long-password-123'), 'ANALYST'), role='ANALYST')
        self.admin = dict(id=self.store.register(dict(email='admin@test.local', name='Admin', password='long-password-123'), 'ADMIN'), role='ADMIN')
        self.trip = self.store.create_trip(self.user, dict(title='Trip', route_id='demo'), ['demo'])

    def tearDown(self):
        self.temp.cleanup()

    def test_hashes_and_sessions(self):
        first = password_hash('long-password-123')
        self.assertNotEqual(first, password_hash('long-password-123'))
        self.assertTrue(matches('long-password-123', first))
        self.assertFalse(matches('other-password', first))
        self.store.logout(self.token)
        with self.assertRaises(AccessError): self.store.session(self.token)

    def test_reset_one_use_expiry_and_revocation(self):
        self.store.request_reset({'email': 'missing@test.local'}, 'test')
        token = self.store.issue_reset('driver@test.local')
        self.store.reset_password(dict(token=token, password='new-password-123'))
        with self.assertRaises(AccessError): self.store.session(self.token)
        with self.assertRaises(ValueError): self.store.reset_password(dict(token=token, password='new-password-123'))
        new, _ = self.store.login(dict(email='driver@test.local', password='new-password-123'), 'new')
        self.assertEqual(self.store.session(new)['id'], self.uid)
        token = self.store.issue_reset('driver@test.local')
        self.now += 901
        with self.assertRaises(ValueError): self.store.reset_password(dict(token=token, password='new-password-123'))
        with self.assertRaises(ValueError): self.store.issue_reset('missing@test.local')

    def test_roles_filters_and_ownership(self):
        self.assertEqual(len(self.store.trips(self.user, {'q': 'trip'})), 1)
        self.assertEqual(self.store.trips(self.other, {}), [])
        self.assertEqual(len(self.store.trips(self.analyst, {})), 1)
        with self.assertRaises(AccessError): self.store.get_trip(self.other, self.trip['id'])
        with self.assertRaises(AccessError): self.store.get_trip(self.user, 'missing')
        with self.assertRaises(ValueError): self.store.trips(self.user, {'status': 'BAD'})
        with self.assertRaises(AccessError): self.store.update_trip(self.analyst, dict(id=self.trip['id'], title='bad', note=''))
        self.store.update_trip(self.user, dict(id=self.trip['id'], title='New', note='Own note'))
        self.assertEqual(self.store.get_trip(self.user, self.trip['id'])['note'], 'Own note')

    def test_correction_preserves_original_and_actor(self):
        oid = self.store.add_observation(self.user, dict(trip_id=self.trip['id'], signal='S1', state='GREEN', kind='STATE_SEEN'), ['S1'])['id']
        with self.assertRaises(AccessError): self.store.correct(self.other, dict(id=oid, state='RED', reason='Correction'))
        self.store.correct(self.analyst, dict(id=oid, state='RED', reason='Correction'))
        rows = self.store.observations(self.user, {'state': 'RED'})
        self.assertEqual(rows[0]['state'], 'GREEN')
        self.assertEqual(rows[0]['effective_state'], 'RED')
        self.assertEqual(rows[0]['correction_count'], 1)
        self.assertEqual(self.store.correction_history(self.user, oid)[0]['actor'], 'Analyst')
        with self.assertRaises(AccessError): self.store.correction_history(self.other, oid)
        with self.assertRaises(AccessError): self.store.correct(self.user, dict(id='missing', state='RED', reason='Correction'))
        with self.assertRaises(ValueError): self.store.correct(self.user, dict(id=oid, state='BAD', reason='Correction'))
        with self.assertRaises(ValueError): self.store.observations(self.user, {'state': 'BAD'})
        self.assertEqual(self.store.observations(self.other, {}), [])

    def test_admin_and_last_admin(self):
        with self.assertRaises(AccessError): self.store.users(self.user)
        with self.assertRaises(AccessError): self.store.change_user(self.analyst, dict(id=self.uid, role='ANALYST', active=True))
        with self.assertRaises(ValueError): self.store.change_user(self.admin, dict(id=self.admin['id'], role='DRIVER', active=True))
        self.store.change_user(self.admin, dict(id=self.uid, role='ANALYST', active=True))
        with self.assertRaises(AccessError): self.store.session(self.token)
        self.assertEqual(len(self.store.users(self.admin)), 4)
        with self.assertRaises(AccessError): self.store.change_user(self.admin, dict(id='missing', role='DRIVER', active=True))
        with self.assertRaises(ValueError): self.store.change_user(self.admin, dict(id=self.uid, role='ROOT', active=True))

    def test_validation_and_throttle(self):
        for data in [dict(email='invalid', name='Name', password='long-password-123'),
                     dict(email='valid@test.local', name='', password='long-password-123'),
                     dict(email='valid@test.local', name='Name', password='short'),
                     dict(email='valid@test.local', name='Name', password='long-password-123', role='ADMIN')]:
            with self.assertRaises(ValueError): self.store.register(data)
        with self.assertRaises(ValueError): self.store.register(dict(email='driver@test.local', name='Name', password='long-password-123'))
        for _ in range(8):
            with self.assertRaises(AccessError): self.store.login(dict(email='none@test.local', password='long-password-123'), 'x')
        with self.assertRaises(AccessError) as error: self.store.login(dict(email='none@test.local', password='long-password-123'), 'x')
        self.assertEqual(error.exception.status, 429)
        self.now += 301
        self.store.throttle('login-account:none@test.local')
        with self.assertRaises(ValueError): self.store.create_trip(self.user, dict(title='Trip', route_id='bad'), ['demo'])
        with self.assertRaises(ValueError): self.store.add_observation(self.user, dict(trip_id=self.trip['id'], signal='bad', state='GREEN', kind='STATE_START'), ['S1'])
        with self.assertRaises(AccessError): self.store.add_observation(self.other, dict(trip_id=self.trip['id'], signal='S1', state='GREEN', kind='STATE_START'), ['S1'])
        self.store.mark_recording(self.user, self.trip['id'], 'a'*32, 'RECORDING')
        with self.assertRaises(AccessError): self.store.mark_recording(self.analyst, self.trip['id'], 'a'*32, 'COMPLETE')

    def test_migration_is_repeatable_and_sessions_expire(self):
        self.store.migrate()
        self.now += 28801
        with self.assertRaises(AccessError): self.store.session(self.token)
        with self.assertRaises(AccessError): self.store.session(None)
        with self.store.db() as db: db.execute('PRAGMA user_version=99')
        with self.assertRaises(ValueError): self.store.migrate()


if __name__ == '__main__':
    unittest.main()
