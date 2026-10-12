"""School accounts and owned records; no access to legacy GPS directories."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

ROLES = ('DRIVER', 'ANALYST', 'ADMIN')
STATES = ('GREEN', 'YELLOW', 'RED', 'UNKNOWN')
KINDS = ('STATE_SEEN', 'STATE_START')


class AccessError(Exception):
    def __init__(self, message='Brak uprawnień', status=403):
        super().__init__(message)
        self.status = status


def text(value, label, maximum=120, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f'{label}: wymagane {minimum}–{maximum} znaków')
    return value.strip()


def email(value):
    value = text(value, 'Email', 254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise ValueError('Nieprawidłowy email')
    return value


def password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        raise ValueError('Hasło musi mieć 12–128 znaków')
    return value


def password_hash(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'


def matches(value, encoded):
    salt, _ = encoded.split(':')
    return hmac.compare_digest(password_hash(value, salt), encoded)


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


class SchoolStore:
    def __init__(self, path, clock=time.time):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.migrate()
        self.dummy_hash = password_hash(secrets.token_hex(20))

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self):
        with self.db() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version > 2:
                raise ValueError('Baza danych wymaga nowszej wersji aplikacji')
            if version == 0:
                db.executescript('''
                    BEGIN;
                    CREATE TABLE users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL
                        CHECK(role IN ('DRIVER','ANALYST','ADMIN')), active INTEGER NOT NULL DEFAULT 1);
                    CREATE TABLE sessions(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                        csrf TEXT NOT NULL, expires REAL NOT NULL);
                    CREATE TABLE resets(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                        expires REAL NOT NULL);
                    CREATE TABLE reset_requests(email TEXT PRIMARY KEY, requested REAL NOT NULL);
                    CREATE TABLE attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, start REAL NOT NULL);
                    CREATE TABLE trips(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
                        title TEXT NOT NULL, route_id TEXT NOT NULL, created REAL NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('PLANNED','RECORDING','COMPLETE')),
                        run_id TEXT UNIQUE, note TEXT NOT NULL DEFAULT '');
                    CREATE TABLE observations(id TEXT PRIMARY KEY, trip_id TEXT NOT NULL REFERENCES trips(id),
                        owner_id TEXT NOT NULL REFERENCES users(id), signal TEXT NOT NULL,
                        state TEXT NOT NULL, kind TEXT NOT NULL, created REAL NOT NULL);
                    CREATE TABLE corrections(id TEXT PRIMARY KEY, observation_id TEXT NOT NULL REFERENCES observations(id),
                        actor_id TEXT NOT NULL REFERENCES users(id), state TEXT NOT NULL,
                        reason TEXT NOT NULL, created REAL NOT NULL);
                    CREATE TABLE account_audit(id INTEGER PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES users(id),
                        subject_id TEXT NOT NULL REFERENCES users(id), role TEXT NOT NULL, active INTEGER NOT NULL, created REAL NOT NULL);
                    PRAGMA user_version=1;
                    COMMIT;
                ''')

            if version < 2:
                db.execute('ALTER TABLE trips ADD COLUMN interrupted INTEGER NOT NULL DEFAULT 0')
                db.execute('PRAGMA user_version=2')

    def register(self, payload, role='DRIVER'):
        if set(payload) != {'email', 'name', 'password'} or role not in ROLES:
            raise ValueError('Nieprawidłowe pola konta')
        address = email(payload['email'])
        name = text(payload['name'], 'Imię', 80)
        encoded = password_hash(password(payload['password']))
        uid = secrets.token_hex(16)
        try:
            with self.db() as db:
                db.execute('INSERT INTO users(id,email,name,password,role) VALUES(?,?,?,?,?)',
                           (uid, address, name, encoded, role))
        except sqlite3.IntegrityError:
            raise ValueError('Nie można utworzyć konta z tym adresem') from None
        return uid

    def throttle(self, key, limit=8, window=300):
        now = self.clock()
        with self.db() as db:
            row = db.execute('SELECT * FROM attempts WHERE key=?', (key,)).fetchone()
            if row is None or now - row['start'] > window:
                db.execute('INSERT OR REPLACE INTO attempts VALUES(?,1,?)', (key, now))
            elif row['count'] >= limit:
                raise AccessError('Za dużo prób. Spróbuj za kilka minut.', 429)
            else:
                db.execute('UPDATE attempts SET count=count+1 WHERE key=?', (key,))

    def login(self, payload, peer):
        if set(payload) != {'email', 'password'}:
            raise ValueError('Nieprawidłowe pola logowania')
        self.throttle('login-ip:' + peer, 30)
        address = email(payload['email'])
        self.throttle('login-account:' + address)
        value = password(payload['password'])
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE email=?', (address,)).fetchone()
            valid = matches(value, row['password'] if row else self.dummy_hash)
            if not valid or row is None or not row['active']:
                raise AccessError('Nieprawidłowy email lub hasło', 401)
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<?', (self.clock(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)',
                       (token_hash(token), row['id'], csrf, self.clock() + 28800))
            db.execute('DELETE FROM attempts WHERE key=?', ('login-account:' + address,))
        return token, csrf

    def session(self, token):
        if not isinstance(token, str) or len(token) > 100:
            raise AccessError('Zaloguj się', 401)
        with self.db() as db:
            row = db.execute('''SELECT users.id, email, name, role, csrf FROM sessions
                JOIN users ON users.id=sessions.user_id
                WHERE token=? AND expires>? AND active=1''', (token_hash(token), self.clock())).fetchone()
        if row is None:
            raise AccessError('Zaloguj się', 401)
        return dict(row)

    def logout(self, token):
        with self.db() as db:
            db.execute('DELETE FROM sessions WHERE token=?', (token_hash(token),))

    def request_reset(self, payload, peer):
        if set(payload) != {'email'}:
            raise ValueError('Nieprawidłowe pola resetu')
        self.throttle('reset:' + peer, 5)
        address = email(payload['email'])
        with self.db() as db:
            # Same response/storage behavior for existing and nonexistent addresses.
            db.execute('INSERT OR REPLACE INTO reset_requests VALUES(?,?)', (address, self.clock()))
        return {'message': 'Jeżeli konto istnieje, administrator dostarczy jednorazowy link prywatnym kanałem.'}

    def issue_reset(self, address):
        address = email(address)
        with self.db() as db:
            row = db.execute('SELECT id FROM users WHERE email=? AND active=1', (address,)).fetchone()
            if row is None:
                raise ValueError('Nie znaleziono aktywnego konta')
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM resets WHERE user_id=?', (row['id'],))
            db.execute('INSERT INTO resets VALUES(?,?,?)', (token_hash(token), row['id'], self.clock() + 900))
            db.execute('DELETE FROM reset_requests WHERE email=?', (address,))
        return token

    def reset_password(self, payload):
        if set(payload) != {'token', 'password'}:
            raise ValueError('Nieprawidłowe pola resetu')
        token = text(payload['token'], 'Token', 100)
        encoded = password_hash(password(payload['password']))
        with self.db() as db:
            row = db.execute('SELECT * FROM resets WHERE token=? AND expires>?',
                             (token_hash(token), self.clock())).fetchone()
            if row is None:
                raise ValueError('Link jest nieważny lub wygasł')
            db.execute('UPDATE users SET password=? WHERE id=?', (encoded, row['user_id']))
            db.execute('DELETE FROM sessions WHERE user_id=?', (row['user_id'],))
            db.execute('DELETE FROM resets WHERE user_id=?', (row['user_id'],))
        return {'message': 'Hasło zmienione. Zaloguj się ponownie.'}

    @staticmethod
    def scope(user, owner):
        if user['role'] == 'DRIVER' and user['id'] != owner:
            raise AccessError('Nie znaleziono rekordu', 404)

    def get_trip(self, user, tid):
        with self.db() as db:
            row = db.execute('SELECT * FROM trips WHERE id=?', (tid,)).fetchone()
        if row is None:
            raise AccessError('Nie znaleziono rekordu', 404)
        self.scope(user, row['owner_id'])
        return dict(row)

    def trips(self, user, query):
        q = text(query.get('q', ''), 'Filtr', 120, 0)
        status = query.get('status', '')
        if status not in ('', 'PLANNED', 'RECORDING', 'COMPLETE'):
            raise ValueError('Nieprawidłowy status')
        with self.db() as db:
            return [dict(row) for row in db.execute('''SELECT trips.*, users.name AS owner FROM trips
                JOIN users ON users.id=trips.owner_id WHERE (?!='DRIVER' OR owner_id=?)
                AND (?='' OR status=?) AND (instr(lower(title),lower(?))>0 OR instr(lower(route_id),lower(?))>0)
                ORDER BY created DESC LIMIT 500''', (user['role'], user['id'], status, status, q, q))]

    def create_trip(self, user, payload, routes):
        if set(payload) != {'title', 'route_id'}:
            raise ValueError('Nieprawidłowe pola przejazdu')
        title = text(payload['title'], 'Nazwa przejazdu')
        route = text(payload['route_id'], 'Trasa')
        if route not in routes:
            raise ValueError('Nieznana trasa')
        tid = secrets.token_hex(16)
        with self.db() as db:
            db.execute('INSERT INTO trips(id,owner_id,title,route_id,created,status) VALUES(?,?,?,?,?,?)',
                       (tid, user['id'], title, route, self.clock(), 'PLANNED'))
        return self.get_trip(user, tid)

    def update_trip(self, user, payload):
        if set(payload) != {'id', 'title', 'note'}:
            raise ValueError('Nieprawidłowe pola przejazdu')
        row = self.get_trip(user, text(payload['id'], 'ID', 32))
        if row['owner_id'] != user['id'] and user['role'] != 'ADMIN':
            raise AccessError()
        title, note = text(payload['title'], 'Nazwa'), text(payload['note'], 'Notatka', 1000, 0)
        with self.db() as db:
            db.execute('UPDATE trips SET title=?,note=? WHERE id=?', (title, note, row['id']))
        return self.get_trip(user, row['id'])

    def mark_recording(self, user, tid, run_id, status):
        row = self.get_trip(user, tid)
        if row['owner_id'] != user['id'] or status not in ('RECORDING', 'COMPLETE'):
            raise AccessError()
        with self.db() as db:
            db.execute('UPDATE trips SET run_id=?,status=?,interrupted=0 WHERE id=?', (run_id, status, tid))

    def add_observation(self, user, payload, signals):
        if set(payload) != {'trip_id', 'signal', 'state', 'kind'}:
            raise ValueError('Nieprawidłowe pola obserwacji')
        trip = self.get_trip(user, text(payload['trip_id'], 'Przejazd', 32))
        if trip['owner_id'] != user['id']:
            raise AccessError()
        signal = text(payload['signal'], 'Światło')
        if signal not in signals or payload['state'] not in STATES or payload['kind'] not in KINDS:
            raise ValueError('Nieprawidłowe światło, kolor lub rodzaj zdarzenia')
        oid = secrets.token_hex(16)
        with self.db() as db:
            db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',
                       (oid, trip['id'], user['id'], signal, payload['state'], payload['kind'], self.clock()))
        return {'id': oid}

    def observations(self, user, query):
        q = text(query.get('q', ''), 'Filtr', 120, 0)
        state = query.get('state', '')
        if state not in ('', *STATES):
            raise ValueError('Nieprawidłowy kolor')
        with self.db() as db:
            return [dict(row) for row in db.execute('''SELECT o.*, t.title AS trip, u.name AS owner,
                COALESCE((SELECT c.state FROM corrections c WHERE c.observation_id=o.id ORDER BY c.rowid DESC LIMIT 1),o.state) AS effective_state,
                (SELECT count(*) FROM corrections c WHERE c.observation_id=o.id) AS correction_count
                FROM observations o JOIN trips t ON t.id=o.trip_id JOIN users u ON u.id=o.owner_id
                WHERE (?!='DRIVER' OR o.owner_id=?) AND instr(lower(o.signal),lower(?))>0
                AND (?='' OR COALESCE((SELECT c.state FROM corrections c WHERE c.observation_id=o.id ORDER BY c.rowid DESC LIMIT 1),o.state)=?)
                ORDER BY o.created DESC LIMIT 500''', (user['role'], user['id'], q, state, state))]

    def correct(self, user, payload):
        if set(payload) != {'id', 'state', 'reason'} or payload['state'] not in STATES:
            raise ValueError('Nieprawidłowe pola korekty')
        reason = text(payload['reason'], 'Powód korekty', 500, 3)
        with self.db() as db:
            row = db.execute('SELECT * FROM observations WHERE id=?', (payload['id'],)).fetchone()
            if row is None:
                raise AccessError('Nie znaleziono rekordu', 404)
            self.scope(user, row['owner_id'])
            db.execute('INSERT INTO corrections VALUES(?,?,?,?,?,?)',
                       (secrets.token_hex(16), row['id'], user['id'], payload['state'], reason, self.clock()))
        return {'message': 'Dopisano korektę. Oryginał pozostaje bez zmian.'}

    def correction_history(self, user, oid):
        with self.db() as db:
            row = db.execute('SELECT owner_id FROM observations WHERE id=?', (oid,)).fetchone()
            if row is None:
                raise AccessError('Nie znaleziono rekordu', 404)
            self.scope(user, row['owner_id'])
            return [dict(r) for r in db.execute('''SELECT c.state,c.reason,c.created,u.name AS actor
                FROM corrections c JOIN users u ON u.id=c.actor_id WHERE observation_id=? ORDER BY c.rowid''', (oid,))]

    def users(self, user):
        if user['role'] != 'ADMIN':
            raise AccessError()
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT id,email,name,role,active FROM users ORDER BY email')]

    def change_user(self, user, payload):
        if user['role'] != 'ADMIN':
            raise AccessError()
        if set(payload) != {'id', 'role', 'active'} or payload['role'] not in ROLES or type(payload['active']) is not bool:
            raise ValueError('Nieprawidłowe pola uprawnień')
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?', (payload['id'],)).fetchone()
            if row is None:
                raise AccessError('Nie znaleziono konta', 404)
            if row['role'] == 'ADMIN' and row['active'] and (payload['role'] != 'ADMIN' or not payload['active']):
                if db.execute("SELECT count(*) FROM users WHERE role='ADMIN' AND active=1").fetchone()[0] <= 1:
                    raise ValueError('Nie można usunąć ostatniego administratora')
            db.execute('UPDATE users SET role=?,active=? WHERE id=?', (payload['role'], payload['active'], payload['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?', (payload['id'],))
            db.execute('INSERT INTO account_audit(actor_id,subject_id,role,active,created) VALUES(?,?,?,?,?)',
                       (user['id'], payload['id'], payload['role'], payload['active'], self.clock()))
        return {'message': 'Uprawnienia zmienione, sesje konta unieważnione.'}

