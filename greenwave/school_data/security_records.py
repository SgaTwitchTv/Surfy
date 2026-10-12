"""Persistence of already-hashed credentials; cryptography/SMTP belong to stage 4."""
from .validation import digest, text
from .errors import Denied, Invalid


class SecurityRecords:
    def create_session(self, actor, secret_hash, csrf_hash):
        digest(secret_hash); digest(csrf_hash)
        with self.database.transaction() as c:
            user=self.user(c,actor)
            sid,now=self.new_id(),self.clock()
            c.execute("INSERT INTO browser_sessions VALUES (?,?,?,?,?,?,?,?,?,NULL)",
                      (sid,user["id"],secret_hash,csrf_hash,user["security_version"],now,now,now,now+28800))
            return sid

    def session(self, c, session_id, owner_id):
        row=c.execute("SELECT s.* FROM browser_sessions s JOIN users u ON u.id=s.user_id WHERE s.id=? AND s.user_id=? AND s.revoked_at IS NULL AND u.status='ACTIVE' AND s.security_version=u.security_version",(session_id,owner_id)).fetchone()
        now=self.clock()
        if not row or row["absolute_expiry"]<=now or row["last_activity_at"]+1800<=now:
            raise Denied("Session unavailable or expired")
        return row

    def touch_session(self, actor, session_id):
        with self.database.transaction() as c:
            self.user(c,actor); self.session(c,session_id,actor.user_id)
            c.execute("UPDATE browser_sessions SET last_activity_at=? WHERE id=?",(self.clock(),session_id))

    def revoke_session(self, actor, session_id):
        with self.database.transaction() as c:
            self.user(c,actor)
            row=c.execute("SELECT id FROM browser_sessions WHERE id=? AND user_id=?",(session_id,actor.user_id)).fetchone()
            if not row: raise Denied("Session unavailable")
            now=self.clock()
            c.execute("UPDATE browser_sessions SET revoked_at=COALESCE(revoked_at,?) WHERE id=?",(now,session_id))
            c.execute("UPDATE devices SET status='REVOKED',token_hash=NULL,revoked_at=? WHERE parent_session_id=?",(now,session_id))
            c.execute("UPDATE pairing_challenges SET revoked_at=COALESCE(revoked_at,?) WHERE parent_session_id=?",(now,session_id))
            self.audit(c,actor,"SESSION_REVOKED","SESSION",session_id)
            # Recording shutdown is an integration requirement for stage 6, not implemented here.

    def issue_account_token(self, user_id, purpose, secret_hash):
        digest(secret_hash)
        if purpose not in {"RESET","VERIFY_EMAIL"}: raise Invalid("Invalid account token purpose")
        with self.database.transaction() as c:
            user=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
            if not user or (purpose=="RESET" and user["status"]!="ACTIVE") or (purpose=="VERIFY_EMAIL" and user["status"]!="PENDING_VERIFICATION"):
                raise Denied("Account token cannot be issued")
            now=self.clock(); token_id=self.new_id()
            c.execute("UPDATE account_tokens SET revoked_at=? WHERE user_id=? AND purpose=? AND used_at IS NULL AND revoked_at IS NULL",(now,user_id,purpose))
            c.execute("INSERT INTO account_tokens VALUES (?,?,?,?,?,?,?,NULL,NULL,'PENDING')",(token_id,user_id,purpose,secret_hash,user["security_version"],now,now+(900 if purpose=="RESET" else 86400)))
            return token_id

    def consume_account_token(self, secret_hash, purpose, *, apply=None):
        digest(secret_hash)
        with self.database.transaction() as c:
            row=c.execute("SELECT t.* FROM account_tokens t JOIN users u ON u.id=t.user_id WHERE t.secret_hash=? AND t.purpose=? AND t.used_at IS NULL AND t.revoked_at IS NULL AND t.expiry>? AND t.security_version=u.security_version AND ((t.purpose='RESET' AND u.status='ACTIVE') OR (t.purpose='VERIFY_EMAIL' AND u.status='PENDING_VERIFICATION'))",(secret_hash,purpose,self.clock())).fetchone()
            if not row: raise Denied("Account token unavailable")
            c.execute("UPDATE account_tokens SET used_at=? WHERE id=?",(self.clock(),row["id"]))
            if apply is not None:
                apply(c, dict(row))  # trusted stage-4 service callback, rollback includes token use
            return dict(row)

    def pairing_challenge(self, actor, session_id, code_hmac, boot_id, label):
        digest(code_hmac); text(boot_id,1,80); text(label,1,80)
        with self.database.transaction() as c:
            self.user(c,actor); self.session(c,session_id,actor.user_id)
            now=self.clock(); challenge=self.new_id()
            c.execute("UPDATE pairing_challenges SET revoked_at=? WHERE used_at IS NULL AND revoked_at IS NULL AND (expiry<=? OR parent_session_id=?)",(now,now,session_id))
            c.execute("INSERT INTO pairing_challenges VALUES (?,?,?,?,?,?,?,?,0,NULL,NULL)",(challenge,code_hmac,actor.user_id,session_id,boot_id,label,now,now+300))
            return challenge

    def bind_device(self, actor, challenge_id, client_device_id, token_hash, boot_id):
        digest(token_hash); text(client_device_id,1,128)
        with self.database.transaction() as c:
            user=self.user(c,actor)
            challenge=c.execute("SELECT * FROM pairing_challenges WHERE id=? AND owner_id=? AND boot_id=? AND expiry>? AND used_at IS NULL AND revoked_at IS NULL AND attempts<5",(challenge_id,actor.user_id,boot_id,self.clock())).fetchone()
            if not challenge: raise Denied("Pairing unavailable")
            self.session(c,challenge["parent_session_id"],actor.user_id)
            now=self.clock(); did=self.new_id()
            existing=c.execute("SELECT id FROM devices WHERE owner_id=? AND client_device_id=?",(actor.user_id,client_device_id)).fetchone()
            if existing:
                did=existing[0]
                c.execute("UPDATE devices SET token_hash=?,parent_session_id=?,boot_id=?,security_version=?,expiry=?,status='ACTIVE',revoked_at=NULL,label=? WHERE id=?",(token_hash,challenge["parent_session_id"],boot_id,user["security_version"],now+28800,challenge["label"],did))
            else:
                c.execute("INSERT INTO devices VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL)",(did,actor.user_id,client_device_id,challenge["label"],'ACTIVE',token_hash,challenge["parent_session_id"],boot_id,user["security_version"],now+28800))
            c.execute("UPDATE pairing_challenges SET used_at=? WHERE id=?",(now,challenge_id))
            self.audit(c,actor,"DEVICE_BOUND","DEVICE",did)
            return did

    def device_owner(self, token_hash, boot_id):
        digest(token_hash)
        with self.database.transaction(False) as c:
            row=c.execute("SELECT d.* FROM devices d JOIN users u ON u.id=d.owner_id WHERE d.token_hash=? AND d.boot_id=? AND d.status='ACTIVE' AND d.revoked_at IS NULL AND d.expiry>? AND u.status='ACTIVE' AND d.security_version=u.security_version",(token_hash,boot_id,self.clock())).fetchone()
            if not row: raise Denied("Device unavailable")
            self.session(c,row["parent_session_id"],row["owner_id"])
            return row["owner_id"]

    def rate_attempt(self, key_hash, purpose, window_seconds=60, limit=5):
        digest(key_hash); text(purpose,1,40)
        if not isinstance(limit,int) or limit<1 or not isinstance(window_seconds,int) or not 1<=window_seconds<=86400:
            raise Invalid("Invalid rate policy")
        with self.database.transaction() as c:
            now=self.clock()
            row=c.execute("SELECT * FROM auth_rate_limits WHERE key_hash=?",(key_hash,)).fetchone()
            if row and row["purpose"]!=purpose: raise Invalid("Rate key purpose mismatch")
            start=row["window_start"] if row and row["window_start"]+window_seconds>now else now
            count=row["attempts"]+1 if start!=now or (row and row["window_start"]==now) else 1
            blocked=start+window_seconds if count>=limit else None
            c.execute("INSERT INTO auth_rate_limits VALUES (?,?,?,?,?,?) ON CONFLICT(key_hash) DO UPDATE SET window_start=excluded.window_start,attempts=excluded.attempts,blocked_until=excluded.blocked_until,expires_at=excluded.expires_at",(key_hash,purpose,start,count,blocked,start+window_seconds*2))
            return {"attempts":count,"blocked_until":blocked}
