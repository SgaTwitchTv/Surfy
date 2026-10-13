"""Re-evaluate session and DB permissions; no role/owner supplied by HTTP clients."""
from contextlib import nullcontext
from dataclasses import dataclass
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.storage import identifier
from greenwave.school_data.errors import Invalid


def resource_id(value):
    try: return identifier(value)
    except Invalid: raise AuthError(404, 'NOT_FOUND') from None


@dataclass(frozen=True)
class AuthorizationBasis:
    kind: str
    actor_id: str
    trip_id: str
    share_id: str | None = None


class Policy:
    def __init__(self, accounts):
        self.accounts = accounts
        self.repo = accounts.repo

    def session(self, raw, connection=None):
        return self.accounts.sessions.lookup(raw, connection=connection)

    def role(self, raw, roles, reauth=False):
        row, actor = self.session(raw)
        if row['role'] not in roles:
            raise AuthError(403, 'FORBIDDEN')
        if reauth and not 0 <= self.repo.clock() - actor.reauthenticated_at <= 300000:
            raise AuthError(403, 'REAUTH_REQUIRED')
        return row, actor

    def basis_trip(self, raw, trip_id, *, basis=None, owner_only=False, closed=False, connection=None):
        row, actor = self.session(raw, connection)
        with nullcontext(connection) if connection is not None else self.repo.database.transaction(False) as c:
            trip = c.execute('SELECT * FROM trips WHERE id=?', (resource_id(trip_id),)).fetchone()
            if trip is None: raise AuthError(404, 'NOT_FOUND')
            if basis is None:
                if trip['owner_id'] == actor.user_id:
                    basis = AuthorizationBasis('OWN', actor.user_id, trip_id)
                elif not owner_only and row['role'] == 'ANALYST':
                    share = c.execute('SELECT id FROM trip_shares WHERE trip_id=? AND analyst_id=? AND revoked_at IS NULL',
                                      (trip_id, actor.user_id)).fetchone()
                    if share: basis = AuthorizationBasis('SHARE', actor.user_id, trip_id, share['id'])
            if basis is None or basis.actor_id != actor.user_id:
                raise AuthError(404, 'NOT_FOUND')
            self.check_basis(c, basis, trip)
            if owner_only and basis.kind != 'OWN': raise AuthError(404, 'NOT_FOUND')
            if closed and (trip['status'] != 'COMPLETE' or trip['archived_at'] is not None):
                raise AuthError(409, 'TRIP_NOT_AVAILABLE')
            return row, actor, dict(trip), basis

    def check_basis(self, c, basis, trip):
        """Validate exactly the captured grant; never select a replacement/fallback."""
        if not isinstance(basis, AuthorizationBasis) or basis.trip_id != trip['id']:
            raise AuthError(404, 'NOT_FOUND')
        subject = c.execute('SELECT role,status FROM users WHERE id=?', (basis.actor_id,)).fetchone()
        if not subject or subject['status'] != 'ACTIVE': raise AuthError(404, 'NOT_FOUND')
        if basis.kind == 'OWN' and basis.share_id is None and trip['owner_id'] == basis.actor_id:
            return
        if (basis.kind == 'SHARE' and subject['role'] == 'ANALYST' and trip['status'] == 'COMPLETE'
                and trip['archived_at'] is None and c.execute(
                    "SELECT 1 FROM trip_shares WHERE id=? AND trip_id=? AND analyst_id=? AND permission='READ_ANALYZE' AND revoked_at IS NULL",
                    (basis.share_id, basis.trip_id, basis.actor_id)).fetchone()):
            return
        raise AuthError(404, 'NOT_FOUND')

    def trip(self, raw, trip_id, owner_only=False, closed=False):
        row, actor, trip, basis = self.basis_trip(raw, trip_id, owner_only=owner_only, closed=closed)
        return row, actor, trip, basis.kind == 'OWN'

    def bound_trip(self, raw, basis, connection=None):
        return self.basis_trip(raw, basis.trip_id, basis=basis, closed=True, connection=connection)

    def observation(self, raw, observation_id):
        self.session(raw)
        with self.repo.database.connection() as c:
            observation = c.execute('SELECT * FROM observations WHERE id=?', (resource_id(observation_id),)).fetchone()
        if observation is None: raise AuthError(404, 'NOT_FOUND')
        context = self.trip(raw, observation['trip_id'])
        return context, dict(observation)
