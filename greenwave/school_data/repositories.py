"""Small repository facade; implementation is split by domain responsibility."""
from .repository_base import Actor, RepositoryBase
from .accounts import Accounts
from .security_records import SecurityRecords
from .trips import Trips
from .observations import Observations
from .configurations import Configurations


class Repository(Accounts, SecurityRecords, Trips, Observations, Configurations, RepositoryBase):
    pass
