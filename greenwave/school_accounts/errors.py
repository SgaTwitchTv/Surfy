class AuthError(Exception):
    def __init__(self, status, code, fields=None, retry_after=None):
        self.status, self.code, self.fields, self.retry_after = status, code, fields, retry_after
        super().__init__(code)
