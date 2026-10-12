import base64
import hashlib
import hmac
import re
import secrets
import threading
from .errors import AuthError


def secret():
    return secrets.token_urlsafe(32)


def token_hash(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}",value):
        raise AuthError(422,"INVALID_TOKEN")
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def csrf(key, raw, identifier, purpose):
    return hmac.new(key,(purpose+'|'+raw+'|'+identifier).encode(),hashlib.sha256).hexdigest()


_UNSET=object()

def password(value, confirmation=_UNSET):
    try:
        valid=isinstance(value,str) and 12<=len(value)<=128 and len(value.encode('utf-8'))<=512
    except UnicodeError:
        valid=False
    if not valid:
        raise AuthError(422,"VALIDATION",{'password':'12–128 znaków, maksymalnie 512 bajtów UTF-8.'})
    if confirmation is not _UNSET and (not isinstance(confirmation,str) or value!=confirmation):
        raise AuthError(422,"VALIDATION",{'password_confirmation':'Hasła muszą być identyczne.'})
    return value


class Passwords:
    """Production always uses default N=131072. Lower constructor N is test injection only."""
    def __init__(self, n=131072):
        if n not in {1024,65536,131072}:
            raise ValueError('Unsupported scrypt policy')
        self.n=n
        self.slots=threading.BoundedSemaphore(2)
        self.dummy=self.hash(secret())

    def derive(self, value, salt, n):
        if not self.slots.acquire(blocking=False):
            raise AuthError(503,'KDF_BUSY')
        try:
            return hashlib.scrypt(value.encode('utf-8'),salt=salt,n=n,r=8,p=1,dklen=32,maxmem=256*1024*1024)
        finally:
            self.slots.release()

    def hash(self,value):
        password(value)
        salt=secrets.token_bytes(16)
        derived=self.derive(value,salt,self.n)
        return f'scrypt$v1${self.n}$8$1$32$'+salt.hex()+'$'+derived.hex()

    def verify(self,value,encoded):
        if not isinstance(value,str) or len(value)>128:
            return False,False
        try:
            if len(value.encode('utf-8'))>512:
                return False,False
            parts=encoded.split('$') if isinstance(encoded,str) and len(encoded)<=256 else []
            if len(parts)!=8 or parts[0]!='scrypt' or parts[1] not in {'v0','v1'} or parts[3:6]!=['8','1','32']:
                raise ValueError('Unsupported format')
            n=int(parts[2])
            if n not in {65536,131072,self.n} or not re.fullmatch(r'[0-9a-f]{32}',parts[6]) or not re.fullmatch(r'[0-9a-f]{64}',parts[7]):
                raise ValueError('Unsupported parameters')
            salt,expected=bytes.fromhex(parts[6]),bytes.fromhex(parts[7])
            actual=self.derive(value,salt,n)
            return hmac.compare_digest(expected,actual),n!=self.n or parts[1]!='v1'
        except (ValueError,UnicodeError):
            # Malformed stored hashes still perform bounded dummy verification.
            actual=self.derive(value if value.isascii() else 'invalid-credential',bytes.fromhex(self.dummy.split('$')[6]),self.n)
            return False,False
