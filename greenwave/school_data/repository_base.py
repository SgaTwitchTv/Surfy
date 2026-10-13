"""Actor is supplied only by a future trusted server authentication context.
Constructing it is not authentication. Browser DTOs must never supply this object.
Roles and account state are fetched afresh inside each transaction.
"""
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from .errors import Denied, Conflict, Invalid
from .storage import identifier
from .time_units import now_ms, timestamp_ms


@dataclass(frozen=True)
class Actor:
    user_id: str
    reauthenticated_at: int | None = None

    def __post_init__(self):
        if self.reauthenticated_at is not None:
            timestamp_ms(self.reauthenticated_at)


class RepositoryBase:
    def __init__(self, database, clock=now_ms, ids=lambda: uuid.uuid4().hex):
        self.database, self.ids = database, ids
        self.clock = lambda: timestamp_ms(clock())

    def new_id(self):
        return identifier(self.ids())

    def user(self, c, actor, roles=None, reauth=False):
        if not isinstance(actor, Actor):
            raise Denied("Trusted actor required")
        identifier(actor.user_id)
        user = c.execute("SELECT * FROM users WHERE id=?", (actor.user_id,)).fetchone()
        if not user or user["status"]!="ACTIVE" or (roles and user["role"] not in roles):
            raise Denied("Active authorized account required")
        if actor.reauthenticated_at is not None:
            timestamp_ms(actor.reauthenticated_at)
        if reauth and (actor.reauthenticated_at is None or not 0<=self.clock()-actor.reauthenticated_at<=300000):
            raise Denied("Recent trusted reauthentication required")
        return user

    def own_trip(self, c, actor, trip_id):
        self.user(c, actor)
        row = c.execute("SELECT * FROM trips WHERE id=? AND owner_id=?", (identifier(trip_id), actor.user_id)).fetchone()
        if not row:
            raise Denied("Trip is unavailable")
        return row

    @contextmanager
    def atomic(self, request_id='internal'):
        with self.database.transaction() as connection:
            class BoundDatabase:
                storage = self.database.storage
                @contextmanager
                def transaction(inner, write=True): yield connection
                @contextmanager
                def connection(inner): yield connection
            unit = type(self)(BoundDatabase(), clock=self.clock, ids=self.ids)
            unit.audit_request_id = request_id
            yield unit, connection

    def audit(self, c, actor, action, resource_type, resource_id, reason="", request_id="internal", outcome="OK"):
        if request_id == 'internal': request_id = getattr(self,'audit_request_id','internal')
        # Deliberately no arbitrary payload/GPS/token field.
        c.execute("INSERT INTO audit_events(actor_id,actor_type,action,resource_type,resource_id,reason,server_at,request_id,outcome) VALUES (?,?,?,?,?,?,?,?,?)",
                  (actor.user_id if actor else None,"USER" if actor else "SYSTEM",action,resource_type,resource_id,reason,self.clock(),request_id,outcome))
