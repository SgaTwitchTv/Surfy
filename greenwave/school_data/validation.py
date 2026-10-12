import hashlib
import json
import re
from .errors import Invalid


def text(value, minimum, maximum):
    if not isinstance(value, str) or value != value.strip() or not minimum <= len(value) <= maximum or any(ord(c)<32 or ord(c)==127 for c in value):
        raise Invalid("Invalid text length, whitespace or control character")
    return value


def email(value):
    if not isinstance(value, str):
        raise Invalid("Invalid email")
    value = value.strip()
    if not value.isascii() or len(value)>254 or value.count("@")!=1:
        raise Invalid("Invalid email")
    local, domain = value.split("@")
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}", local) or local.startswith(".") or local.endswith(".") or ".." in local:
        raise Invalid("Invalid email")
    if "." not in domain or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part) for part in domain.split(".")):
        raise Invalid("Invalid email")
    return value.lower()


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise Invalid("Expected a SHA-256/HMAC hex digest, never a raw secret")
    return value


def operation_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", value):
        raise Invalid("Invalid operation key")
    return value


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise Invalid("Invalid JSON value") from exc


def request_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def observation(value):
    if set(value)!={"state", "event_type", "valid"} or value["state"] not in {"RED","YELLOW","GREEN","RED_YELLOW","OFF","UNKNOWN"} or value["event_type"] not in {"STATE_SEEN","STATE_START"} or type(value["valid"]) is not bool or (value["state"]=="UNKNOWN" and value["event_type"]=="STATE_START"):
        raise Invalid("Invalid effective observation")
    return value
