"""Account-protected GreenWave portal and isolated per-driver M8 applications."""
import argparse
from dataclasses import asdict
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.parse import parse_qs, urlsplit

from greenwave.application import GreenWaveApplication, DATA
from greenwave.server import LocalServer, Handler, STATIC
from greenwave.school_store import SchoolStore, AccessError, token_hash


class SchoolServer(LocalServer):
    def __init__(self, port=8765, host='127.0.0.1', root='runtime/school', demo=False, secure=False, public_origin=None):
        self.root = Path(root)
        self.store = SchoolStore(self.root / 'school.sqlite3')
        self.apps = {}
        self.pair_codes = {}
        self.secure = secure
        self.public_origin = public_origin
        self.demo = demo
        # Never open private legacy data/runs through this server.
        super().__init__(port, GreenWaveApplication(runs_root=self.root / 'laboratory/runs'), host)
        self.RequestHandlerClass = SchoolHandler
        if demo:
            self.seed_demo()

    def app_for(self, user):
        if user['id'] not in self.apps:
            self.apps[user['id']] = GreenWaveApplication(runs_root=self.root / 'users' / user['id'] / 'runs')
        return self.apps[user['id']]

    def seed_demo(self):
        for name, address, role in [('Kierowca Demo', 'driver@demo.local', 'DRIVER'),
                                    ('Drugi Kierowca', 'other@demo.local', 'DRIVER'),
                                    ('Analityk Demo', 'analyst@demo.local', 'ANALYST'),
                                    ('Administrator Demo', 'admin@demo.local', 'ADMIN')]:
            with self.store.db() as db:
                exists = db.execute('SELECT id FROM users WHERE email=?', (address,)).fetchone()
            if exists:
                continue
            uid = self.store.register(dict(email=address, name=name, password='GreenWave-demo-2026'), role)
            user = dict(id=uid, role=role)
            trip = self.store.create_trip(user, dict(title='Przejazd demonstracyjny', route_id='synthetic_s1_s5'), ['synthetic_s1_s5'])
            self.store.add_observation(user, dict(trip_id=trip['id'], signal='S1', state='GREEN', kind='STATE_SEEN'), ['S1'])

    def server_close(self):
        for app in self.apps.values():
            app.close()
        super().server_close()


class SchoolHandler(Handler):
    def cookie(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            return ''
        return cookie['gw_session'].value if 'gw_session' in cookie else ''

    def user(self):
        user = self.server.store.session(self.cookie())
        if user['csrf'] == 'DEVICE':
            raise AccessError('Token telefonu nie daje dostępu do portalu')
        return user

    def cookie_header(self, token, age=28800):
        return {'Set-Cookie': f'gw_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={age}' +
                ('; Secure' if self.server.secure else '')}

    def valid_origin(self):
        origin = self.headers.get('Origin')
        expected = self.server.public_origin or f'http://{self.headers.get("Host", "")}'
        return origin is None or origin == expected

    def do_GET(self):
        try:
            if not self._valid_host():
                raise AccessError('Nieprawidłowy Host')
            path = urlsplit(self.path).path
            if path in ('/', '/school.js', '/school.css'):
                file, content_type = {'/': ('school.html', 'text/html; charset=utf-8'),
                                      '/school.js': ('school.js', 'text/javascript; charset=utf-8'),
                                      '/school.css': ('school.css', 'text/css; charset=utf-8')}[path]
                return self._send(200, (STATIC / file).read_bytes(), content_type)
            if path == '/health':
                return self._send(200, {'ok': True, 'demo': self.server.demo})
            user = self.user()
            store = self.server.store
            query = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query, keep_blank_values=True).items()}
            if path == '/school/api/me':
                return self._send(200, dict(user=user, demo=self.server.demo))
            if path == '/school/api/trips':
                return self._send(200, store.trips(user, query))
            if path == '/school/api/observations':
                return self._send(200, store.observations(user, query))
            if path == '/school/api/corrections':
                return self._send(200, store.correction_history(user, query.get('id', '')))
            if path == '/school/api/users':
                return self._send(200, store.users(user))
            if path == '/school/api/reset-requests':
                if user['role'] != 'ADMIN':
                    raise AccessError()
                with store.db() as db:
                    return self._send(200, [dict(r) for r in db.execute('SELECT * FROM reset_requests ORDER BY requested DESC LIMIT 100')])
            if path == '/school/api/routes':
                return self._send(200, [{'route_id': 'synthetic_s1_s5', 'name': 'S1–S5 • symulacja'}] + self.server.application.routes.list())
            if path == '/school/api/navigation':
                app = self.server.app_for(user)
                snapshot = app.snapshot()
                snapshot['active_trip_id'] = getattr(app, 'school_trip', None)
                return self._send(200, snapshot)
            if path == '/school/api/map':
                return self._send(200, (DATA / 'maps/warsaw.json').read_bytes())
            if path == '/school/api/export':
                trip = store.get_trip(user, query.get('id', ''))
                if not trip['run_id'] or trip['status'] != 'COMPLETE':
                    raise ValueError('Brak zakończonego nagrania')
                owner_app = self.server.app_for(dict(id=trip['owner_id']))
                return self._send(200, owner_app.logger.export(trip['run_id']), 'application/zip', 'greenwave-trip.zip')
            # All pre-existing laboratory APIs/assets require ADMIN session.
            if user['role'] != 'ADMIN':
                raise AccessError()
            if path == '/lab':
                self.path = '/'
            return super().do_GET()
        except AccessError as error:
            self._send(error.status, {'error': str(error)})
        except (ValueError, TypeError, KeyError) as error:
            self._send(400, {'error': str(error)})
        except (OSError, sqlite3.Error):
            self._send(503, {'error': 'Dane są chwilowo niedostępne'})

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValueError('Nieprawidłowa długość żądania') from None
        if not 0 < length <= 8192:
            raise AccessError('Żądanie musi mieć 1–8192 bajtów', 413)
        self.connection.settimeout(5)
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError('Oczekiwano obiektu JSON')
        return value

    def do_POST(self):
        try:
            path = urlsplit(self.path).path
            parsed = self.read_json() if path.startswith('/school/api/') or path in ('/api/pair', '/api/position') else None
            if not self._valid_host() or not self.valid_origin():
                raise AccessError('Niedozwolone pochodzenie żądania')
            store = self.server.store
            peer = self.client_address[0]
            # Native Android pairing remains separate from browser login.
            if path == '/api/pair':
                store.throttle('pair:' + peer, 5)
                data = parsed
                if set(data) != {'code'} or not isinstance(data['code'], str):
                    raise ValueError('Nieprawidłowy kod')
                pair = self.server.pair_codes.pop(data['code'], None)
                if pair is None or pair['expires'] < time.time():
                    raise AccessError('Nieprawidłowy kod parowania')
                owner = store.session(pair['browser_token'])
                token = secrets.token_urlsafe(32)
                with store.db() as db:
                    db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (token_hash(token), owner['id'], 'DEVICE', time.time() + 28800))
                return self._send(200, dict(token=token, session_id=self.server.app_for(owner).session_id, server_version='school-M8-1'))
            if path == '/api/position':
                user = store.session(self.headers.get('X-GreenWave-Token', ''))
                if user['csrf'] != 'DEVICE':
                    raise AccessError()
                app = self.server.app_for(user)
                data = parsed
                if data.pop('session_id', None) != app.session_id:
                    raise AccessError('Sesja pomiarowa wygasła. Sparuj telefon ponownie.', 409)
                sample = app.ingest_external_position(**data)
                return self._send(200, dict(external_position=asdict(sample), external_status=app.external_position.status(),
                                           accepted=app.external_position.last_update_accepted,
                                           duplicate=not app.external_position.last_update_accepted))
            public = ('/school/api/register', '/school/api/login', '/school/api/request-reset', '/school/api/reset-password')
            if path not in public:
                user = self.user()
                if user['csrf'] == 'DEVICE' or not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), user['csrf']):
                    raise AccessError('Odśwież sesję (CSRF)')
                if not path.startswith('/school/api/'):
                    if user['role'] != 'ADMIN':
                        raise AccessError()
                    return super().do_POST()
            data = parsed
            if path == '/school/api/register':
                store.throttle('register:' + peer, 5)
                store.register(data)
                return self._send(201, {'message': 'Konto utworzone. Zaloguj się.'})
            if path == '/school/api/login':
                token, csrf = store.login(data, peer)
                return self._send(200, {'csrf': csrf}, headers=self.cookie_header(token))
            if path == '/school/api/request-reset':
                return self._send(200, store.request_reset(data, peer))
            if path == '/school/api/reset-password':
                store.throttle('reset-use:' + peer, 8)
                return self._send(200, store.reset_password(data), headers=self.cookie_header('', 0))
            if path == '/school/api/logout':
                if data:
                    raise ValueError('Nieprawidłowe pola')
                store.logout(self.cookie())
                return self._send(200, {'message': 'Wylogowano'}, headers=self.cookie_header('', 0))
            if path == '/school/api/trips':
                routes = ['synthetic_s1_s5'] + [r['route_id'] for r in self.server.application.routes.list()]
                return self._send(201, store.create_trip(user, data, routes))
            if path == '/school/api/trips/update':
                return self._send(200, store.update_trip(user, data))
            if path == '/school/api/observations':
                trip = store.get_trip(user, data.get('trip_id', ''))
                app = self.server.app_for(user)
                signals = ['S1', 'S2', 'S3', 'S4', 'S5'] if trip['route_id'] == 'synthetic_s1_s5' else [line.stop_line_id for line in app.routes.load(trip['route_id']).stop_lines]
                return self._send(201, store.add_observation(user, data, signals))
            if path == '/school/api/corrections':
                return self._send(201, store.correct(user, data))
            if path == '/school/api/users':
                return self._send(200, store.change_user(user, data))
            if path == '/school/api/pair-code':
                if data:
                    raise ValueError('Nieprawidłowe pola')
                code = f'{secrets.randbelow(1000000):06d}'
                self.server.pair_codes = {k: v for k, v in self.server.pair_codes.items() if v['expires'] > time.time() and v['browser_token'] != self.cookie()}
                self.server.pair_codes[code] = dict(browser_token=self.cookie(), expires=time.time() + 300)
                return self._send(200, {'code': code, 'expires_seconds': 300})
            if path == '/school/api/navigation':
                app = self.server.app_for(user)
                command = data.get('command')
                if set(data) != {'command', 'trip_id'} or command not in ('start', 'pause', 'finish', 'live'):
                    raise ValueError('Nieprawidłowe sterowanie')
                trip = store.get_trip(user, data['trip_id'])
                if trip['owner_id'] != user['id']:
                    raise AccessError()
                if command in ('start', 'live'):
                    if app.logger.active:
                        raise ValueError('Najpierw zakończ bieżące nagranie')
                    if trip['status'] != 'PLANNED':
                        raise ValueError('Utwórz nowy przejazd dla nowego nagrania')
                    if command == 'live' and trip['route_id'] == 'synthetic_s1_s5':
                        raise ValueError('GPS wymaga rzeczywistej trasy')
                    if command == 'start' and trip['route_id'] != 'synthetic_s1_s5':
                        raise ValueError('Symulacja wymaga trasy S1–S5')
                    app.select_route(None if command == 'start' else trip['route_id'])
                    app.set_view_mode('SIMULATION' if command == 'start' else 'LIVE')
                    app.school_trip = trip['id']
                    app.recording('start')
                    store.mark_recording(user, trip['id'], app.logger.run_id, 'RECORDING')
                    if command == 'start':
                        app.control(running=True)
                elif command == 'pause':
                    if getattr(app, 'school_trip', None) != trip['id']:
                        raise ValueError('Ten przejazd nie jest aktywny')
                    app.control(running=False)
                else:
                    if getattr(app, 'school_trip', None) != trip['id'] or not app.logger.active:
                        raise ValueError('Ten przejazd nie jest nagrywany')
                    app.control(running=False)
                    app.recording('stop')
                    store.mark_recording(user, trip['id'], app.logger.run_id, 'COMPLETE')
                    app.school_trip = None
                return self._send(200, {'message': 'Zaktualizowano przejazd'})
            self._send(404, {'error': 'Nie znaleziono endpointu'})
        except AccessError as error:
            self._send(error.status, {'error': str(error)})
        except (ValueError, TypeError, KeyError) as error:
            self._send(400, {'error': str(error)})
        except (OSError, sqlite3.Error):
            self._send(503, {'error': 'Nie można zapisać danych. Spróbuj ponownie.'})


def main():
    parser = argparse.ArgumentParser(description='GreenWave: portal szkolny z kontami')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--root', default=os.environ.get('GW_SCHOOL_ROOT', 'runtime/school'))
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--secure-cookie', action='store_true')
    parser.add_argument('--public-origin')
    parser.add_argument('--create-admin', metavar='EMAIL')
    parser.add_argument('--issue-reset', metavar='EMAIL')
    args = parser.parse_args()
    if args.create_admin or args.issue_reset:
        import getpass
        store = SchoolStore(Path(args.root) / 'school.sqlite3')
        if args.create_admin:
            uid = store.register(dict(email=args.create_admin, name='Administrator', password=getpass.getpass('Nowe hasło (12–128 znaków): ')), 'ADMIN')
            print('Utworzono administratora:', uid)
        else:
            token = store.issue_reset(args.issue_reset)
            print('Dostarcz prywatnie, ważny 15 minut: /#reset=' + token)
        return
    with SchoolServer(args.port, args.host, args.root, args.demo, args.secure_cookie, args.public_origin) as server:
        print(f'GreenWave School: http://127.0.0.1:{server.server_port} (demo={args.demo})', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()


