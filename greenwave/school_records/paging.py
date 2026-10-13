import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.time_units import timestamp_ms

DAY = 86400000


def rfc3339(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',value):
        raise AuthError(422,'VALIDATION')
    try:
        date=datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
        delta=date-datetime(1970,1,1,tzinfo=timezone.utc)
        return timestamp_ms(delta.days*DAY+delta.seconds*1000+delta.microseconds//1000)
    except (ValueError,OverflowError):raise AuthError(422,'VALIDATION') from None


def dates(q):
    after=rfc3339(q['from']) if 'from' in q else None
    before=rfc3339(q['to']) if 'to' in q else None
    if after is not None or before is not None:
        if after is None:after=max(0,before-366*DAY)
        if before is None:before=min(253402300799999,after+366*DAY)
        if not after<before or before-after>366*DAY:raise AuthError(422,'VALIDATION')
    return after,before


class Paging:
    def __init__(self,repo,key):self.repo,self.key=repo,key
    def encode(self,value):
        data=base64.urlsafe_b64encode(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).rstrip(b'=')
        sig=hmac.new(self.key,b'school-list-v1:'+data,hashlib.sha256).hexdigest().encode()
        return (data+b'.'+sig).decode()
    def page(self,actor,kind,q):
        try:limit=int(q.get('limit','25'))
        except ValueError:raise AuthError(422,'VALIDATION') from None
        if not re.fullmatch('[0-9]{1,3}',q.get('limit','25')) or not 1<=limit<=100:raise AuthError(422,'VALIDATION')
        order=q.get('sort','desc')
        if order not in {'asc','desc'}:raise AuthError(422,'VALIDATION')
        filters={k:v for k,v in q.items() if k not in {'cursor','limit'}}
        fingerprint=hashlib.sha256(json.dumps(filters,sort_keys=True).encode()).hexdigest()
        value={'actor':actor.user_id,'kind':kind,'filter':fingerprint,'sort':order,'as_of':self.repo.clock(),'expiry':self.repo.clock()+900000,'last':None}
        if 'cursor' in q:
            try:
                if len(q['cursor'])>1600:raise ValueError()
                data,sig=q['cursor'].encode('ascii').split(b'.')
                if not hmac.compare_digest(sig,hmac.new(self.key,b'school-list-v1:'+data,hashlib.sha256).hexdigest().encode()):raise ValueError()
                saved=json.loads(base64.urlsafe_b64decode(data+b'='*(-len(data)%4)))
                if set(saved)!=set(value) or any(saved[k]!=value[k] for k in ['actor','kind','filter','sort']) or type(saved['expiry']) is not int or saved['expiry']<=self.repo.clock():raise ValueError()
                timestamp_ms(saved['as_of'])
                if not isinstance(saved['last'],list) or len(saved['last'])!=2 or type(saved['last'][0]) is not int or not re.fullmatch('[0-9a-f]{32}',saved['last'][1]):raise ValueError()
                value=saved
            except (ValueError,TypeError,KeyError,UnicodeError):raise AuthError(400,'INVALID_CURSOR') from None
        return limit,order,value
    def result(self,rows,limit,value,time_column):
        more=len(rows)>limit;rows=rows[:limit]
        cursor=None
        if more:
            value={**value,'last':[rows[-1][time_column],rows[-1]['id']]};cursor=self.encode(value)
        return rows,{'limit':limit,'next_cursor':cursor}
