"""Re-evaluate session and DB permissions; no role/owner supplied by HTTP clients."""
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.storage import identifier
from greenwave.school_data.errors import Invalid


def resource_id(value):
    try: return identifier(value)
    except Invalid: raise AuthError(404, 'NOT_FOUND') from None


class Policy:
    def __init__(self, accounts):
        self.accounts = accounts
        self.repo = accounts.repo

    def session(self, raw):
        return self.accounts.sessions.lookup(raw)

    def role(self, raw, roles, reauth=False):
        row, actor = self.session(raw)
        if row['role'] not in roles:
            raise AuthError(403, 'FORBIDDEN')
        if reauth and not 0 <= self.repo.clock() - actor.reauthenticated_at <= 300000:
            raise AuthError(403, 'REAUTH_REQUIRED')
        return row, actor

    def trip(self, raw, trip_id, owner_only=False, closed=False):
        row, actor = self.session(raw)
        with self.repo.database.transaction(False) as c:
            trip = c.execute('SELECT * FROM trips WHERE id=?', (resource_id(trip_id),)).fetchone()
            own = trip is not None and trip['owner_id'] == actor.user_id
            shared = (not owner_only and row['role'] == 'ANALYST' and trip is not None
                      and trip['status'] == 'COMPLETE' and trip['archived_at'] is None
                      and c.execute('SELECT 1 FROM trip_shares WHERE trip_id=? AND analyst_id=? AND revoked_at IS NULL',
                                    (trip_id, actor.user_id)).fetchone() is not None)
            if not own and not shared:
                raise AuthError(404, 'NOT_FOUND')
            if closed and (trip['status'] != 'COMPLETE' or trip['archived_at'] is not None):
                raise AuthError(409, 'TRIP_NOT_AVAILABLE')
            return row, actor, dict(trip), own

    def observation(self, raw, observation_id):
        self.session(raw)
        with self.repo.database.connection() as c:
            observation = c.execute('SELECT * FROM observations WHERE id=?', (resource_id(observation_id),)).fetchone()
        if observation is None: raise AuthError(404, 'NOT_FOUND')
        context = self.trip(raw, observation['trip_id'])
        return context, dict(observation)
