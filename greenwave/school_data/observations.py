import json
from .errors import Conflict, Denied, Invalid
from .validation import text, observation, canonical, request_hash, operation_key, digest


class Observations:
    def add_observation(self, actor, trip_id, signal_id, state, event_type, source_event_id, *, source="MANUAL", measured_at=None, geometry_hash=None):
        text(signal_id,1,120); text(source_event_id,1,128)
        observation({"state":state,"event_type":event_type,"valid":True})
        if source not in {"MANUAL","CV"}: raise Invalid("Invalid observation source")
        if geometry_hash is not None: digest(geometry_hash)
        if measured_at is not None and (type(measured_at) not in {int,float} or not 0<=measured_at<=self.clock()+300):
            raise Invalid("Invalid measurement timestamp")
        with self.database.transaction() as c:
            trip=self.own_trip(c,actor,trip_id)
            if trip["archived_at"] is not None: raise Conflict("Archived trip is immutable")
            existing=c.execute("SELECT * FROM observations WHERE trip_id=? AND source=? AND source_event_id=?",(trip_id,source,source_event_id)).fetchone()
            values={"actor_id":actor.user_id,"signal_id":signal_id,"state":state,"event_type":event_type,"measured_at":measured_at,"geometry_hash":geometry_hash}
            if existing:
                if any(existing[k]!=v for k,v in values.items()): raise Conflict("Observation operation content changed")
                return dict(existing)
            oid=self.new_id()
            c.execute("INSERT INTO observations(id,trip_id,actor_id,signal_id,source,state,event_type,server_received_at,measured_at,geometry_hash,source_event_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(oid,trip_id,actor.user_id,signal_id,source,state,event_type,self.clock(),measured_at,geometry_hash,source_event_id))
            self.audit(c,actor,"OBSERVATION_ADDED","OBSERVATION",oid)
            return dict(c.execute("SELECT * FROM observations WHERE id=?",(oid,)).fetchone())

    def effective(self, c, row):
        latest=c.execute("SELECT * FROM observation_corrections WHERE observation_id=? ORDER BY sequence DESC LIMIT 1",(row["id"],)).fetchone()
        return (json.loads(latest["after_json"]),latest["sequence"]) if latest else ({"state":row["state"],"event_type":row["event_type"],"valid":True},0)

    def list_observations(self, actor, trip_id, *, shared=False, after=None, before=None, signal=None, state=None, event_type=None, limit=25, offset=0):
        if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0: raise Invalid("Invalid pagination")
        if state is not None and state not in {"RED","YELLOW","GREEN","RED_YELLOW","OFF","UNKNOWN"}: raise Invalid("Invalid state filter")
        if event_type is not None and event_type not in {"STATE_SEEN","STATE_START"}: raise Invalid("Invalid event filter")
        if after is not None and before is not None and after>before: raise Invalid("Invalid date interval")
        with self.database.transaction(False) as c:
            self.shared_trip(c,actor,trip_id) if shared else self.own_trip(c,actor,trip_id)
            # Effective values are derived from the immutable original and its latest correction.
            clauses=["o.trip_id=?"]; values=[trip_id]
            fields=[("o.server_received_at",">=",after),("o.server_received_at","<=",before),("o.signal_id","=",signal),
                    ("COALESCE(json_extract(k.after_json,'$.state'),o.state)","=",state),
                    ("COALESCE(json_extract(k.after_json,'$.event_type'),o.event_type)","=",event_type)]
            for column,operator,value in fields:
                if value is not None: clauses.append(column+operator+"?"); values.append(value)
            rows=c.execute("SELECT o.* FROM observations o LEFT JOIN observation_corrections k ON k.observation_id=o.id AND k.sequence=(SELECT max(sequence) FROM observation_corrections WHERE observation_id=o.id) WHERE "+" AND ".join(clauses)+" ORDER BY o.server_received_at DESC,o.id DESC LIMIT ? OFFSET ?",(*values,limit,offset)).fetchall()
            result=[]
            for row in rows:
                effective,revision=self.effective(c,row)
                result.append({**dict(row),"effective":effective,"correction_revision":revision})
            return result

    def correct_observation(self, actor, observation_id, expected_revision, after, reason, operation_id):
        observation(after); text(reason,3,500); operation_key(operation_id)
        if type(expected_revision) is not int or expected_revision<0: raise Invalid("Invalid revision")
        fingerprint=request_hash({"observation":observation_id,"revision":expected_revision,"after":after,"reason":reason})
        with self.database.transaction() as c:
            row=c.execute("SELECT * FROM observations WHERE id=?",(observation_id,)).fetchone()
            if not row: raise Denied("Observation unavailable")
            trip=self.own_trip(c,actor,row["trip_id"])
            if trip["archived_at"] is not None: raise Conflict("Archived trip is immutable")
            previous=c.execute("SELECT * FROM observation_corrections WHERE actor_id=? AND client_operation_id=?",(actor.user_id,operation_id)).fetchone()
            if previous:
                if previous["request_hash"]!=fingerprint: raise Conflict("Correction idempotency conflict")
                return dict(previous)
            before,revision=self.effective(c,row)
            if revision!=expected_revision: raise Conflict("Observation revision conflict")
            cid=self.new_id()
            c.execute("INSERT INTO observation_corrections VALUES (?,?,?,?,?,?,?,?,?,?,?)",(cid,observation_id,actor.user_id,revision+1,revision,canonical(before),canonical(after),reason,self.clock(),operation_id,fingerprint))
            self.audit(c,actor,"OBSERVATION_CORRECTED","OBSERVATION",observation_id)
            return dict(c.execute("SELECT * FROM observation_corrections WHERE id=?",(cid,)).fetchone())

    def correction_history(self, actor, observation_id, *, shared=False):
        with self.database.transaction(False) as c:
            row=c.execute("SELECT trip_id FROM observations WHERE id=?",(observation_id,)).fetchone()
            if not row: raise Denied("Observation unavailable")
            self.shared_trip(c,actor,row[0]) if shared else self.own_trip(c,actor,row[0])
            return [dict(r) for r in c.execute("SELECT * FROM observation_corrections WHERE observation_id=? ORDER BY sequence",(observation_id,))]

    def journal_observation(self, actor, observation_id, raw_sequence, state):
        if type(raw_sequence) is not int or raw_sequence<0 or state not in {"APPLIED","FAILED"}: raise Invalid("Invalid journal result")
        with self.database.transaction() as c:
            row=c.execute("SELECT trip_id FROM observations WHERE id=?",(observation_id,)).fetchone()
            if not row: raise Denied("Observation unavailable")
            self.own_trip(c,actor,row[0])
            c.execute("UPDATE observations SET raw_sequence=?,journaling_state=? WHERE id=?",(raw_sequence,state,observation_id))
