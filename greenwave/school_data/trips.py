from .errors import Invalid, Conflict, Denied
from .validation import text, email, digest, operation_key
from .storage import identifier


class Trips:
    def create_trip(self, actor, title, note="", mode="SIMULATION", route_version_id=None):
        text(title,1,120); text(note,0,1000)
        if mode not in {"SIMULATION","LIVE"}: raise Invalid("Invalid trip mode")
        with self.database.transaction() as c:
            self.user(c,actor)
            if route_version_id:
                identifier(route_version_id)
                if not c.execute("SELECT id FROM config_versions WHERE id=? AND kind='ROUTE' AND status='PUBLISHED'",(route_version_id,)).fetchone():
                    raise Invalid("A trip must reference a published route snapshot")
            trip_id=self.new_id()
            c.execute("INSERT INTO trips(id,owner_id,title,note,mode,route_version_id,status,created_at) VALUES (?,?,?,?,?,?,'PLANNED',?)",(trip_id,actor.user_id,title,note,mode,route_version_id,self.clock()))
            self.audit(c,actor,"TRIP_CREATED","TRIP",trip_id)
            return dict(c.execute("SELECT * FROM trips WHERE id=?",(trip_id,)).fetchone())

    def get_trip(self, actor, trip_id):
        with self.database.transaction(False) as c:
            return dict(self.own_trip(c,actor,trip_id))

    def list_trips(self, actor, *, after=None, before=None, route=None, status=None, limit=25, offset=0):
        if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0:
            raise Invalid("Invalid pagination")
        if status and status not in {"PLANNED","STARTING","RECORDING","FINALIZING","COMPLETE","INTERRUPTED"}:
            raise Invalid("Invalid status filter")
        if after is not None and before is not None and after>before: raise Invalid("Invalid date interval")
        with self.database.transaction(False) as c:
            self.user(c,actor)
            clauses=["owner_id=?"]; values=[actor.user_id]
            for column,operator,value in [("created_at",">=",after),("created_at","<=",before),("route_version_id","=",route),("status","=",status)]:
                if value is not None:
                    clauses.append(column+operator+"?"); values.append(value)
            return [dict(r) for r in c.execute("SELECT * FROM trips WHERE "+" AND ".join(clauses)+" ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",(*values,limit,offset))]

    def edit_trip(self, actor, trip_id, expected_revision, *, title, note):
        text(title,1,120); text(note,0,1000)
        with self.database.transaction() as c:
            trip=self.own_trip(c,actor,trip_id)
            if trip["revision"]!=expected_revision: raise Conflict("Trip revision conflict")
            c.execute("UPDATE trips SET title=?,note=?,revision=revision+1 WHERE id=?",(title,note,trip_id))
            self.audit(c,actor,"TRIP_METADATA_CHANGED","TRIP",trip_id)
            return dict(c.execute("SELECT * FROM trips WHERE id=?",(trip_id,)).fetchone())

    def archive_trip(self, actor, trip_id, expected_revision):
        with self.database.transaction() as c:
            trip=self.own_trip(c,actor,trip_id)
            if trip["revision"]!=expected_revision: raise Conflict("Trip revision conflict")
            if trip["status"] not in {"PLANNED","COMPLETE","INTERRUPTED"}: raise Conflict("Trip must be closed")
            if trip["archived_at"] is None:
                c.execute("UPDATE trips SET archived_at=?,revision=revision+1 WHERE id=?",(self.clock(),trip_id))
                c.execute("UPDATE trip_shares SET revoked_at=COALESCE(revoked_at,?) WHERE trip_id=?",(self.clock(),trip_id))
                self.audit(c,actor,"TRIP_ARCHIVED","TRIP",trip_id)

    def transition_trip(self, actor, trip_id, expected_revision, status, *, run_id=None, raw_ref=None, raw_hash=None, manifest_hash=None):
        """Trusted future recording coordinator. Does NOT verify raw files or run a logger."""
        allowed={"PLANNED":{"STARTING"},"STARTING":{"RECORDING","INTERRUPTED"},"RECORDING":{"FINALIZING","INTERRUPTED"},"FINALIZING":{"COMPLETE","INTERRUPTED"}}
        with self.database.transaction() as c:
            trip=self.own_trip(c,actor,trip_id)
            if trip["revision"]!=expected_revision: raise Conflict("Trip revision conflict")
            if trip["archived_at"] or status not in allowed.get(trip["status"],set()): raise Conflict("Invalid trip transition")
            now=self.clock()
            if status=="STARTING":
                identifier(run_id)
                c.execute("UPDATE trips SET status=?,run_id=?,started_at=?,revision=revision+1 WHERE id=?",(status,run_id,now,trip_id))
            elif status=="COMPLETE":
                digest(raw_hash); digest(manifest_hash)
                expected=self.database.storage.run(actor.user_id,trip_id,trip["run_id"])/"gps.jsonl"
                relative=expected.relative_to(self.database.storage.root).as_posix()
                if raw_ref!=relative: raise Invalid("Raw reference must belong to this trip")
                c.execute("UPDATE trips SET status=?,ended_at=?,raw_ref=?,raw_hash=?,manifest_hash=?,revision=revision+1 WHERE id=?",(status,now,raw_ref,raw_hash,manifest_hash,trip_id))
            else:
                c.execute("UPDATE trips SET status=?,ended_at=?,revision=revision+1 WHERE id=?",(status,now if status=="INTERRUPTED" else None,trip_id))
            self.audit(c,actor,"TRIP_TRANSITION","TRIP",trip_id)
            return dict(c.execute("SELECT * FROM trips WHERE id=?",(trip_id,)).fetchone())

    def share_trip(self, actor, trip_id, analyst_email):
        normalized=email(analyst_email)
        with self.database.transaction() as c:
            trip=self.own_trip(c,actor,trip_id)
            if trip["status"]!="COMPLETE" or trip["archived_at"] is not None: raise Conflict("Only completed nonarchived trips may be shared")
            analyst=c.execute("SELECT id FROM users WHERE email_normalized=? AND role='ANALYST' AND status='ACTIVE'",(normalized,)).fetchone()
            if not analyst or analyst[0]==actor.user_id: raise Denied("Sharing recipient unavailable")
            share_id=self.new_id()
            c.execute("INSERT INTO trip_shares(id,trip_id,analyst_id,grantor_id,created_at) VALUES (?,?,?,?,?)",(share_id,trip_id,analyst[0],actor.user_id,self.clock()))
            self.audit(c,actor,"TRIP_SHARED","TRIP",trip_id)
            return share_id

    def revoke_share(self, actor, trip_id, expected_share_id):
        with self.database.transaction() as c:
            self.own_trip(c,actor,trip_id)
            row=c.execute("SELECT * FROM trip_shares WHERE id=? AND trip_id=?",(expected_share_id,trip_id)).fetchone()
            if not row: raise Conflict("Share identifier conflict")
            if row["revoked_at"] is None:
                c.execute("UPDATE trip_shares SET revoked_at=? WHERE id=?",(self.clock(),expected_share_id))
                self.audit(c,actor,"TRIP_SHARE_REVOKED","TRIP",trip_id)

    def shared_trip(self, c, actor, trip_id):
        self.user(c,actor,{"ANALYST"})
        row=c.execute("SELECT t.* FROM trips t JOIN trip_shares s ON s.trip_id=t.id WHERE t.id=? AND s.analyst_id=? AND s.revoked_at IS NULL AND t.status='COMPLETE' AND t.archived_at IS NULL",(identifier(trip_id),actor.user_id)).fetchone()
        if not row: raise Denied("Shared trip unavailable")
        return row

    def get_shared_trip(self, actor, trip_id):
        with self.database.transaction(False) as c:
            return dict(self.shared_trip(c,actor,trip_id))

    def recording_intent(self, actor, trip_id, kind, key, request_hash):
        operation_key(key); digest(request_hash)
        if kind not in {"START","FINISH","JOURNAL_OBSERVATION"}: raise Invalid("Invalid recording operation")
        with self.database.transaction() as c:
            self.own_trip(c,actor,trip_id)
            existing=c.execute("SELECT * FROM recording_operations WHERE actor_id=? AND kind=? AND idempotency_key=?",(actor.user_id,kind,key)).fetchone()
            if existing:
                if existing["request_hash"]!=request_hash or existing["trip_id"]!=trip_id: raise Conflict("Idempotency key reused with different content")
                return dict(existing)
            op=self.new_id()
            c.execute("INSERT INTO recording_operations VALUES (?,?,?,?,?,?,'PENDING',NULL,?)",(op,trip_id,actor.user_id,kind,key,request_hash,self.clock()))
            return dict(c.execute("SELECT * FROM recording_operations WHERE id=?",(op,)).fetchone())

    def finish_intent(self, actor, operation_id, state, result_ref=None):
        if state not in {"APPLIED","FAILED"}: raise Invalid("Invalid intent result")
        with self.database.transaction() as c:
            row=c.execute("SELECT * FROM recording_operations WHERE id=? AND actor_id=?",(operation_id,actor.user_id)).fetchone()
            if not row: raise Denied("Operation unavailable")
            self.own_trip(c,actor,row["trip_id"])
            if result_ref is not None:
                if not isinstance(result_ref,str) or "\\" in result_ref or ":" in result_ref:
                    raise Invalid("Invalid result reference")
                path=self.database.storage._safe(self.database.storage.root/result_ref)
                try:
                    path.relative_to(self.database.storage.trip(actor.user_id,row["trip_id"]))
                except ValueError as exc:
                    raise Invalid("Result reference belongs to a different trip") from exc
            if row["state"]!='PENDING':
                if row["state"]!=state or row["result_ref"]!=result_ref: raise Conflict("Intent already finalized")
                return
            c.execute("UPDATE recording_operations SET state=?,result_ref=? WHERE id=?",(state,result_ref,operation_id))
