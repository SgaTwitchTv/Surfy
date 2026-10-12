import hashlib
import hmac
import math
from .errors import AuthError


class Limits:
    def __init__(self,repo,key):
        self.repo,self.key=repo,key

    def bucket(self,purpose,identity):
        return hmac.new(self.key,(purpose+'|'+identity).encode(),hashlib.sha256).hexdigest()

    def take(self,purpose,identity,limit,window_ms):
        key=self.bucket(purpose,identity)
        with self.repo.database.transaction() as c:
            now=self.repo.clock()
            c.execute('DELETE FROM auth_rate_limits WHERE expires_at<=?',(now,))
            row=c.execute('SELECT * FROM auth_rate_limits WHERE key_hash=?',(key,)).fetchone()
            active=row and now<row['window_start']+window_ms
            count=row['attempts'] if active else 0
            start=row['window_start'] if active else now
            if count>=limit:
                raise AuthError(429,'RATE_LIMIT',retry_after=max(1,math.ceil((start+window_ms-now)/1000)))
            c.execute('INSERT INTO auth_rate_limits VALUES (?,?,?,?,?,?) ON CONFLICT(key_hash) DO UPDATE SET window_start=excluded.window_start,attempts=excluded.attempts,blocked_until=excluded.blocked_until,expires_at=excluded.expires_at',
                      (key,purpose,start,count+1,start+window_ms if count+1>=limit else None,start+window_ms*2))
            return start

    def clear(self,purpose,identity):
        with self.repo.database.transaction() as c:
            c.execute('DELETE FROM auth_rate_limits WHERE key_hash=?',(self.bucket(purpose,identity),))

    def refund(self,purpose,identity,window_start):
        # An overload rejection is not a wrong-password failure. Do not refund a
        # different/new window if the clock advanced while KDF was running.
        with self.repo.database.transaction() as c:
            c.execute('UPDATE auth_rate_limits SET attempts=max(0,attempts-1),blocked_until=NULL WHERE key_hash=? AND window_start=?',(self.bucket(purpose,identity),window_start))
