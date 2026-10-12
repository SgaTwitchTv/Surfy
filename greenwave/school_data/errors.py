class DataError(Exception):
    """Controlled persistence failure; callers must not expose SQL to clients."""

class Conflict(DataError):
    pass

class Denied(DataError):
    pass

class Invalid(DataError):
    pass

class SchemaError(DataError):
    pass

class Busy(DataError):
    pass
