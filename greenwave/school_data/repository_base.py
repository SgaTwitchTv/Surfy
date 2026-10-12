"""Actor is supplied only by a future trusted server authentication context.
Constructing it is not authentication. Browser DTOs must never supply this object.
Roles and account state are fetched afresh inside each transaction.
"""
import time
import uuid
from dataclasses import dataclass
from .errors import Denied, Conflict, Invalid
from .storage import identifier


@dataclass(frozen=True)
class Actor:
    user_id: str
    reauthenticated_at: float | None = None


class RepositoryBase:
    def __init__(self, database, clock=time.time, ids=lambda: uuid.uuid4().hex):
        self.database, self.clock, self.ids = database, clock, ids

    def new_id(self):
        return identifier(self.ids())

    def user(self, c, actor, roles=None, reauth=False):
        if not isinstance(actor, Actor):
            raise Denied("Trusted actor required")
        identifier(actor.user_id)
        user = c.execute("SELECT * FROM users WHERE id=?", (actor.user_id,)).fetchone()
        if not user or user["status"]!="ACTIVE" or (roles and user["role"] not in roles):
            raise Denied("Active authorized account required")
        if reauth and (actor.reauthenticated_at is None or not 0<=self.clock()-actor.reauthenticated_at<=300):
            raise Denied("Recent trusted reauthentication required")
        return user

    def own_trip(self, c, actor, trip_id):
        self.user(c, actor)
        row = c.execute("SELECT * FROM trips WHERE id=? AND owner_id=?", (identifier(trip_id), actor.user_id)).fetchone()
        if not row:
            raise Denied("Trip is unavailable")
        return row

    def audit(self, c, actor, action, resource_type, resource_id, reason="", request_id="internal", outcome="OK"):
        # Deliberately no arbitrary payload/GPS/token field.
        c.execute("INSERT INTO audit_events(actor_id,actor_type,action,resource_type,resource_id,reason,server_at,request_id,outcome) VALUES (?,?,?,?,?,?,?,?,?)",
                  (actor.user_id if actor else None,"USER" if actor else "SYSTEM",action,resource_type,resource_id,reason,self.clock(),request_id,outcome))
