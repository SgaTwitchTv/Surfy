from .errors import Invalid, Conflict, Denied
from .validation import text, canonical, request_hash


class Configurations:
    def create_config(self, actor, kind, logical_id, payload):
        text(logical_id,1,120)
        if kind not in {"ROUTE","SIGNAL","MODEL"} or not isinstance(payload,dict): raise Invalid("Invalid configuration")
        encoded=canonical(payload)
        if len(encoded.encode())>262144: raise Invalid("Configuration too large")
        with self.database.transaction() as c:
            self.user(c,actor,{"ANALYST","ADMIN"})
            version=c.execute("SELECT COALESCE(max(version),0)+1 FROM config_versions WHERE kind=? AND logical_id=?",(kind,logical_id)).fetchone()[0]
            cid=self.new_id()
            c.execute("INSERT INTO config_versions(id,kind,logical_id,version,payload,payload_hash,status,creator_id,created_at) VALUES (?,?,?,?,?,?,'DRAFT',?,?)",(cid,kind,logical_id,version,encoded,request_hash(payload),actor.user_id,self.clock()))
            self.audit(c,actor,"CONFIG_DRAFT_CREATED","CONFIG",cid)
            return dict(c.execute("SELECT * FROM config_versions WHERE id=?",(cid,)).fetchone())

    def publish_config(self, actor, config_id, expected_revision):
        with self.database.transaction() as c:
            self.user(c,actor,{"ADMIN"},reauth=True)
            row=c.execute("SELECT * FROM config_versions WHERE id=?",(config_id,)).fetchone()
            if not row: raise Denied("Configuration unavailable")
            if row["status"]!='DRAFT' or row["revision"]!=expected_revision: raise Conflict("Configuration revision/status conflict")
            c.execute("UPDATE config_versions SET status='PUBLISHED',published_at=?,revision=revision+1 WHERE id=?",(self.clock(),config_id))
            self.audit(c,actor,"CONFIG_PUBLISHED","CONFIG",config_id)
            # Publication does not change field verification or the live recommendation gate.
            return dict(c.execute("SELECT * FROM config_versions WHERE id=?",(config_id,)).fetchone())

    def edit_config(self, actor, config_id, expected_revision, payload):
        if not isinstance(payload,dict): raise Invalid("Invalid configuration")
        encoded=canonical(payload)
        if len(encoded.encode())>262144: raise Invalid("Configuration too large")
        with self.database.transaction() as c:
            user=self.user(c,actor,{"ANALYST","ADMIN"})
            row=c.execute("SELECT * FROM config_versions WHERE id=?",(config_id,)).fetchone()
            if not row or (user["role"]=='ANALYST' and row["creator_id"]!=actor.user_id):
                raise Denied("Configuration unavailable")
            if row["status"]!='DRAFT' or row["revision"]!=expected_revision:
                raise Conflict("Configuration revision/status conflict")
            c.execute("UPDATE config_versions SET payload=?,payload_hash=?,revision=revision+1 WHERE id=?",(encoded,request_hash(payload),config_id))
            self.audit(c,actor,"CONFIG_DRAFT_EDITED","CONFIG",config_id)
            return dict(c.execute("SELECT * FROM config_versions WHERE id=?",(config_id,)).fetchone())
