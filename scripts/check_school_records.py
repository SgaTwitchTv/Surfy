"""Repeatable real HTTP demo. Password from getpass, cookies/CSRF only in memory."""
import argparse
from getpass import getpass
import http.cookiejar
import json
from urllib.parse import urlparse,urlencode
from urllib.request import build_opener,HTTPCookieProcessor,Request
from urllib.error import HTTPError
from uuid import uuid4


class Client:
    def __init__(self,base):
        self.base=base.rstrip('/');self.origin=self.base
        self.http=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()));self.csrf=''
    def call(self,method,path,body=None,key=None,expected=200):
        headers={'Origin':self.origin,'X-CSRF-Token':self.csrf}
        data=None
        if body is not None:headers['Content-Type']='application/json';data=json.dumps(body).encode()
        if key:headers['Idempotency-Key']=key
        request=Request(self.base+'/school/api/v1'+path,data=data,headers=headers,method=method)
        try:r=self.http.open(request,timeout=15)
        except HTTPError as error:r=error
        status=r.status;content=r.read();r.close()
        if status!=expected:raise RuntimeError('Unexpected HTTP status '+str(status)+' for '+method+' '+path.split('?')[0])
        if not content:return None
        return json.loads(content).get('data') if content[:1]==b'{' else content
    def login(self,email,password):
        self.csrf=self.call('GET','/auth/preflight')['csrf']
        self.csrf=self.call('POST','/auth/login',{'email':email,'password':password})['csrf']


def run(base,password):
    owner=Client(base);analyst=Client(base)
    owner.login('driver@example.test',password);analyst.login('analyst@example.test',password)
    trip=owner.call('POST','/trips',{'title':'Stage 6 synthetic '+uuid4().hex[:8],'note':'HTTP acceptance','mode':'SIMULATION'},expected=201)
    nav=owner.call('POST','/navigation',{'trip_id':trip['id']},key=uuid4().hex,expected=201)
    observation=owner.call('POST','/trips/'+trip['id']+'/observations',{'signal_id':'synthetic-light','state':'RED','event_type':'STATE_SEEN','source_event_id':uuid4().hex},expected=201)
    nav=owner.call('POST','/navigation/'+nav['id']+'/control',{'command':'FINISH','expected_revision':nav['revision']},key=uuid4().hex)
    archive=owner.call('GET','/trips/'+trip['id']+'/export');assert archive[:2]==b'PK'
    trip=owner.call('PATCH','/trips/'+trip['id'],{'expected_revision':nav['revision'],'title':'Stage 6 edited'})
    owner.call('POST','/observations/'+observation['id']+'/corrections',{'expected_revision':0,'client_operation_id':uuid4().hex,'changes':{'state':'GREEN','valid':True},'reason':'Synthetic correction'},expected=201)
    assert owner.call('GET','/observations?'+urlencode({'trip_id':trip['id'],'state':'GREEN','valid':'true','limit':1}))['items'][0]['effective']['state']=='GREEN'
    page=owner.call('GET','/trips?limit=1')
    if page['page']['next_cursor']:owner.call('GET','/trips?'+urlencode({'limit':1,'cursor':page['page']['next_cursor']}))
    share=owner.call('POST','/trips/'+trip['id']+'/share',{'analyst_email':'analyst@example.test'},expected=201)
    analyst.call('GET','/trips/'+trip['id'])
    owner.call('DELETE','/trips/'+trip['id']+'/share',{'expected_share_id':share['id']},expected=204)
    analyst.call('GET','/trips/'+trip['id'],expected=404)
    owner.call('DELETE','/trips/'+trip['id'],{'expected_revision':trip['revision'],'reason':'Synthetic acceptance archive'},expected=204)
    assert any(item['id']==trip['id'] for item in owner.call('GET','/trips?archived=true')['items'])
    print('PASS fixture login/create/start/observe/finish/export/edit/correct/filter/cursor/share/revoke/archive')
    print('Synthetic trip for restart read: '+trip['id'])
    return trip['id']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8770');parser.add_argument('--read-trip')
    args=parser.parse_args();url=urlparse(args.base_url)
    if url.scheme!='http' or url.hostname not in {'127.0.0.1','localhost','::1'} or url.path not in {'','/'}:parser.error('Local synthetic demo URL required')
    password=getpass('Synthetic fixture password: ')
    if args.read_trip:
        from greenwave.school_data.storage import identifier
        identifier(args.read_trip);client=Client(args.base_url);client.login('driver@example.test',password)
        assert client.call('GET','/trips/'+args.read_trip)['archived_at'] is not None
        print('PASS restart login/read archived trip')
    else:run(args.base_url,password)


if __name__=='__main__':main()
