"""All persistence and trusted context timestamps use integer UTC milliseconds."""
import time
from decimal import Decimal, ROUND_FLOOR
from .errors import Invalid

MAX_TIMESTAMP_MS = 253402300799999  # last millisecond of RFC3339 year 9999


def timestamp_ms(value):
    if type(value) is not int or not 0 <= value <= MAX_TIMESTAMP_MS:
        raise Invalid("Expected integer UTC epoch milliseconds in years 1970..9999")
    return value


def seconds_to_ms(value):
    """Legacy/clock adapter: floor(Decimal(str(seconds))*1000), no binary rounding.
    NULL is preserved by migration; invalid, negative and out-of-range values fail.
    """
    if value is None:
        return None
    if type(value) not in {int, float}:
        raise Invalid("Expected finite legacy epoch seconds")
    seconds = Decimal(str(value))
    if not seconds.is_finite() or seconds < 0 or seconds * 1000 > MAX_TIMESTAMP_MS:
        raise Invalid("Legacy epoch seconds are outside the supported range")
    return timestamp_ms(int((seconds * 1000).to_integral_value(rounding=ROUND_FLOOR)))


def now_ms():
    return seconds_to_ms(time.time())


def date_range(after, before):
    if after is not None:
        timestamp_ms(after)
    if before is not None:
        timestamp_ms(before)
    if after is not None and before is not None and after >= before:
        raise Invalid("Date interval must satisfy from < to")
