"""Account records, not password authentication or public registration."""
from .errors import Invalid, Conflict, Denied
from .validation import email, text
from .time_units import timestamp_ms


class Accounts:
    def create_user(self, email_address, display_name, password_hash, *, role="DRIVER", status="PENDING_VERIFICATION", verified_at=None):
        # Internal provisioning only. Future register ignores any caller-supplied role.
        if verified_at is not None:
            timestamp_ms(verified_at)
        normalized = email(email_address)
        text(display_name,1,80)
        text(password_hash,1,4096)  # opaque future KDF result; fixtures explicitly labelled
        if role not in {"DRIVER","ANALYST","ADMIN"} or status not in {"ACTIVE","PENDING_VERIFICATION","BLOCKED"}:
            raise Invalid("Invalid account role/state")
        if status=="ACTIVE" and verified_at is None:
            raise Invalid("An active account requires verified email")
        with self.database.transaction() as c:
            user_id = self.new_id()
            now = self.clock()
            c.execute("INSERT INTO users(id,email_normalized,email_display,display_name,password_hash,role,status,verified_email_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (user_id, normalized,email_address.strip(),display_name,password_hash,role,status,verified_at,now,now))
            self.audit(c,None,"ACCOUNT_PROVISIONED","USER",user_id)
            return dict(c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone())

    def get_user(self, user_id):
        """Trusted authentication lookup; not an endpoint or user directory."""
        with self.database.transaction(False) as c:
            row=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
            return dict(row) if row else None

    def change_account(self, actor, user_id, expected_revision, *, role=None, status=None, password_hash=None):
        with self.database.transaction() as c:
            admin=self.user(c,actor,{"ADMIN"},reauth=True)
            target=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
            if not target:
                raise Denied("Account unavailable")
            new_role=target["role"] if role is None else role
            new_status=target["status"] if status is None else status
            if new_role not in {"DRIVER","ANALYST","ADMIN"} or new_status not in {"ACTIVE","BLOCKED","PENDING_VERIFICATION"}:
                raise Invalid("Invalid account state")
            if target["revision"]!=expected_revision:
                raise Conflict("Account revision conflict")
            if target["role"]=="ADMIN" and target["status"]=="ACTIVE" and (new_role!="ADMIN" or new_status!="ACTIVE"):
                if c.execute("SELECT count(*) FROM users WHERE role='ADMIN' AND status='ACTIVE'").fetchone()[0]<=1:
                    raise Conflict("The last active administrator cannot be disabled or demoted")
            password_hash=target["password_hash"] if password_hash is None else text(password_hash,1,4096)
            now=self.clock()
            c.execute("UPDATE users SET role=?,status=?,password_hash=?,security_version=security_version+1,revision=revision+1,updated_at=? WHERE id=?",
                      (new_role,new_status,password_hash,now,user_id))
            for table in ("browser_sessions","account_tokens"):
                c.execute(f"UPDATE {table} SET revoked_at=COALESCE(revoked_at,?) WHERE user_id=?",(now,user_id))
            c.execute("UPDATE devices SET revoked_at=?,status='REVOKED',token_hash=NULL WHERE owner_id=?",(now,user_id))
            c.execute("UPDATE pairing_challenges SET revoked_at=COALESCE(revoked_at,?) WHERE owner_id=?",(now,user_id))
            if new_role!="ANALYST" or new_status!="ACTIVE":
                c.execute("UPDATE trip_shares SET revoked_at=COALESCE(revoked_at,?) WHERE analyst_id=?",(now,user_id))
            self.audit(c,actor,"ADMIN_ACCOUNT_CHANGED","USER",user_id)
            return dict(c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone())
