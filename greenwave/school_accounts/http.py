import ipaddress
import json
import secrets
import ssl
import sqlite3
import threading
from http.cookies import SimpleCookie,CookieError
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from greenwave.school_data.errors import DataError, Denied, Invalid, Conflict
from .errors import AuthError

PREFIX='/school/api/v1'
FORMS={
 '/auth/register':{'email','display_name','password','password_confirmation'},
 '/auth/login':{'email','password'},'/auth/verify-email':{'token'},
 '/auth/request-reset':{'email'},'/auth/reset-password':{'token','password','password_confirmation'},
 '/auth/reauth':{'password'},'/auth/change-password':{'current_password','new_password','password_confirmation'},
 '/auth/logout':set(),'/auth/logout-all':set()}
STATIC={'/':'index.html','/school/static/account.js':'account.js','/school/static/account.css':'account.css'}
STATIC.update({
    '/school/static/portal/state.mjs':'portal/state.mjs',
    '/school/static/portal/dates.mjs':'portal/dates.mjs',
    '/school/static/portal/validation.mjs':'portal/validation.mjs',
    '/school/static/portal/api.mjs':'portal/api.mjs',
    '/school/static/portal/filters.mjs':'portal/filters.mjs',
    '/school/static/portal/dom.mjs':'portal/dom.mjs',
    '/school/static/portal/auth.mjs':'portal/auth.mjs',
    '/school/static/portal/records.mjs':'portal/records.mjs',
    '/school/static/portal/lists.mjs':'portal/lists.mjs',
    '/school/static/portal/forms.mjs':'portal/forms.mjs',
    '/school/static/portal/details.mjs':'portal/details.mjs',
    '/school/static/portal/navigation.mjs':'portal/navigation.mjs',
})


def duplicate_checked(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON field')
        result[key]=value
    return result


class AccountsHTTPServer(ThreadingHTTPServer):
    daemon_threads=False
    block_on_close=True
    def __init__(self,address,service):
        self.service=service
        from greenwave.school_resources.api import ResourceAPI
        self.resources=ResourceAPI(service)
        self.request_slots=threading.BoundedSemaphore(64)
        self.tls_context=None
        super().__init__(address,Handler)
        if service.config.tls_cert:
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(service.config.tls_cert,service.config.tls_key)
            self.tls_context=context

    def server_close(self):
        super().server_close()
        self.resources.close()

    def get_request(self):
        connection,address=super().get_request()
        if self.tls_context:
            connection=self.tls_context.wrap_socket(connection,server_side=True,do_handshake_on_connect=False)
        return connection,address

    def process_request(self,request,address):
        if not self.request_slots.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\nContent-Security-Policy: default-src \'none\'\r\n\r\n')
            except OSError:pass
            self.shutdown_request(request);return
        try:super().process_request(request,address)
        except Exception:
            self.request_slots.release();raise

    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.request_slots.release()

    def handle_error(self,*args):
        pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # No URLs, request bodies, tokens, cookies or SMTP exceptions in logs.

    def setup(self):
        self.request.settimeout(5)
        if isinstance(self.request,ssl.SSLSocket):self.request.do_handshake()
        super().setup()

    def cookie(self,name,raw='',age=0):
        value=SimpleCookie();value[name]=raw
        value[name]['httponly']=True;value[name]['samesite']='Strict';value[name]['path']='/'
        value[name]['max-age']=max(0,int(age))
        if self.server.service.config.secure:value[name]['secure']=True
        return value.output(header='').strip()

    def cookies(self):
        try:
            if len(self.headers.get('Cookie',''))>4096:raise CookieError('Cookie too long')
            values=SimpleCookie();values.load(self.headers.get('Cookie',''))
            return {key:value.value for key,value in values.items()}
        except CookieError:return {}

    def reply(self,status,data=None,cookies=(),headers=None,content=None,mime='application/json; charset=utf-8'):
        body=content if content is not None else (b'' if status==204 else json.dumps(data,ensure_ascii=True,allow_nan=False).encode())
        self.send_response(status)
        self.send_header('Connection','close');self.close_connection=True
        self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if self.server.service.config.secure:self.send_header('Strict-Transport-Security','max-age=31536000')
        for value in cookies:self.send_header('Set-Cookie',value)
        for key,value in (headers or {}).items():self.send_header(key,str(value))
        self.end_headers();self.wfile.write(body)

    def check_request(self,mutation=False):
        cfg=self.server.service.config
        for header in ['Host','Origin','Content-Length','X-CSRF-Token']:
            if len(self.headers.get_all(header,[]))>1:raise AuthError(400,'BAD_REQUEST')
        if self.headers.get('Host') not in cfg.hosts:raise AuthError(403,'HOST')
        peer=self.client_address[0]
        if cfg.profile=='real' and not cfg.tls_cert:
            if peer!=cfg.trusted_proxy or self.headers.get('X-Forwarded-Proto')!='https':raise AuthError(403,'HTTPS_REQUIRED')
        if mutation and self.headers.get('Origin')!=cfg.origin:raise AuthError(403,'ORIGIN')
        if cfg.trusted_proxy and peer==cfg.trusted_proxy:
            forwarded=self.headers.get('X-Forwarded-For',peer)
            try:ipaddress.ip_address(forwarded)
            except ValueError:raise AuthError(400,'BAD_REQUEST') from None
            return forwarded
        return peer

    def resource_body(self):
        return self.body(None)

    def body(self,fields):
        if self.headers.get('Transfer-Encoding'):raise AuthError(400,'BAD_REQUEST')
        if self.headers.get('Content-Type','').lower() not in {'application/json','application/json; charset=utf-8'}:raise AuthError(415,'CONTENT_TYPE')
        try:size=int(self.headers.get('Content-Length','-1'))
        except ValueError:raise AuthError(400,'BAD_REQUEST') from None
        if size>8192:raise AuthError(413,'BODY_TOO_LARGE')
        if size<0:raise AuthError(400,'BAD_REQUEST')
        self.body_read=True
        try:
            value=json.loads(self.rfile.read(size).decode('utf-8'),object_pairs_hook=duplicate_checked,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        except (ValueError,UnicodeError):raise AuthError(400,'BAD_REQUEST') from None
        if not isinstance(value,dict) or (fields is not None and set(value)!=fields):raise AuthError(422,'VALIDATION',{'form':'Brakujące lub niedozwolone pola.'})
        if fields is None:
            return value
        if any(not isinstance(v,str) for v in value.values()):raise AuthError(422,'VALIDATION',{'form':'Pola muszą być tekstem.'})
        try:
            for field in value.values():field.encode('utf-8')
        except UnicodeError:raise AuthError(422,'VALIDATION',{'form':'Nieprawidłowy tekst Unicode.'}) from None
        return value

    def do_GET(self):self.dispatch(False)
    def do_POST(self):self.dispatch(True)
    def do_PATCH(self):self.dispatch(True)
    def do_unavailable(self):self.reply(404,{'error':{'code':'NOT_FOUND'}})
    def do_DELETE(self):self.dispatch(True)
    do_PUT=do_unavailable
    do_OPTIONS=do_unavailable
    do_HEAD=do_unavailable

    def dispatch(self,mutation):
        self.body_read=False
        request_id=secrets.token_hex(8)
        self.request_id=request_id
        try:
            ip=self.check_request(mutation)
            parsed=urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.fragment:raise AuthError(400,'BAD_REQUEST')
            path=parsed.path;svc=self.server.service;cookies=self.cookies()
            if not mutation and path in STATIC:
                asset=Path(__file__).parent/'web'/STATIC[path]
                mime='text/html; charset=utf-8' if path=='/' else ('application/javascript; charset=utf-8' if path.endswith(('.js','.mjs')) else 'text/css; charset=utf-8')
                self.reply(200,content=asset.read_bytes(),mime=mime);return
            if not mutation and path==PREFIX+'/health':
                self.reply(200,{'data':{'ok':True,'deployment_mode':svc.config.profile},'request_id':request_id});return
            if not path.startswith(PREFIX):raise AuthError(404,'NOT_FOUND')
            route=path[len(PREFIX):]
            handled,data,status=self.server.resources.dispatch(self,route,parsed.query,cookies.get('gw_session',''))
            if handled:
                from greenwave.school_resources.files import Transfer
                if isinstance(data,Transfer):self.transfer(data,request_id)
                else:self.reply(status,{'data':data,'request_id':request_id})
                return
            if parsed.query:raise AuthError(400,'BAD_REQUEST')
            if self.command not in {'GET','POST'}:raise AuthError(404,'NOT_FOUND')
            if not mutation:
                if route=='/auth/preflight':
                    svc.limits.take('PREFLIGHT_IP',ip,100,900000)
                    if cookies.get('gw_preauth'):
                        try:svc.sessions.forget_preauth(cookies['gw_preauth'])
                        except AuthError:pass
                    raw,data=svc.sessions.preflight()
                    self.reply(200,{'data':data,'request_id':request_id},[self.cookie('gw_preauth',raw,900)]);return
                if route=='/auth/me':
                    raw=cookies.get('gw_session','');row,_=svc.sessions.lookup(raw)
                    self.reply(200,{'data':{**svc.sessions.dto(raw,row),'demo':svc.config.profile=='demo'},'request_id':request_id});return
                raise AuthError(404,'NOT_FOUND')
            if route not in FORMS:raise AuthError(404,'NOT_FOUND')
            body=self.body(FORMS[route]);csrf_value=self.headers.get('X-CSRF-Token','')
            protected=route in {'/auth/logout','/auth/logout-all','/auth/reauth','/auth/change-password'}
            raw=cookies.get('gw_session','')
            row=None
            if protected:
                try:row,_=svc.sessions.lookup(raw)
                except AuthError:
                    if route=='/auth/logout':
                        self.reply(204,cookies=[self.cookie('gw_session')]);return
                    raise
                svc.sessions.check_csrf(raw,row,csrf_value)
            else:svc.sessions.check_preauth(cookies.get('gw_preauth',''),csrf_value)
            data=None;out_cookies=[];status=200
            if route=='/auth/register':data=svc.register(body,ip);status=202
            elif route=='/auth/request-reset':data=svc.request_reset(body,ip);status=202
            elif route in {'/auth/verify-email','/auth/reset-password'}:
                data=svc.use_token(body,ip,'VERIFY_EMAIL' if route.endswith('verify-email') else 'RESET')
                if route.endswith('reset-password'):out_cookies.append(self.cookie('gw_session'))
            elif route=='/auth/login':
                fresh,data=svc.login(body,ip)
                # Revoke a previously authenticated current session on account switch.
                if raw:
                    try:old,_=svc.sessions.lookup(raw,False);svc.logout(old)
                    except AuthError:pass
                svc.sessions.forget_preauth(cookies['gw_preauth'])
                out_cookies=[self.cookie('gw_session',fresh,28800),self.cookie('gw_preauth')]
            elif route=='/auth/reauth':
                fresh,data=svc.reauth(body,raw,row)
                out_cookies=[self.cookie('gw_session',fresh,(row['absolute_expiry']-svc.repo.clock())//1000)]
            elif route=='/auth/change-password':
                data=svc.change_password(body,row);out_cookies=[self.cookie('gw_session')]
            else:
                svc.logout(row,route=='/auth/logout-all');status=204;out_cookies=[self.cookie('gw_session')]
            self.reply(status,{'data':data,'request_id':request_id},out_cookies)
        except AuthError as exc:
            # Consume bounded rejected payload before close to avoid TCP reset erasing
            # a neutral response on Windows. Never parse/use rejected form data.
            if mutation and not self.body_read and not self.headers.get('Transfer-Encoding'):
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if 0<size<=1048576:self.rfile.read(size)
                except (ValueError,OSError):pass
            extra={'Retry-After':exc.retry_after} if exc.retry_after else None
            error={'code':exc.code,'message':'Operacja nie jest dostępna.'}
            if exc.fields:error['fields']=exc.fields
            self.reply(exc.status,{'error':error,'request_id':request_id},[self.cookie('gw_session')] if exc.status==401 else [],extra)
        except (Denied,Invalid,Conflict) as exc:
            status=404 if isinstance(exc,Denied) else 409 if isinstance(exc,Conflict) else 422
            self.reply(status,{'error':{'code':'NOT_FOUND' if status==404 else 'CONFLICT' if status==409 else 'VALIDATION'},'request_id':request_id})
        except (ValueError,TypeError):
            self.reply(422,{'error':{'code':'VALIDATION'},'request_id':request_id})
        except (DataError,sqlite3.Error,OSError):
            self.reply(503,{'error':{'code':'UNAVAILABLE','message':'Spróbuj ponownie później.'},'request_id':request_id})
        except Exception:
            self.reply(500,{'error':{'code':'SERVER_ERROR','message':'Operacja nie powiodła się.'},'request_id':request_id})


    def transfer(self, transfer, request_id):
        # No buffering of large files. Authorize before headers and every <=64KiB.
        try:
            transfer.validate()
            self.send_response(transfer.status)
            self.send_header('Connection','close');self.close_connection=True
            self.send_header('X-Request-ID',request_id)
            for key,value in {'Content-Length':str(transfer.size),'Content-Type':transfer.mime,
                              'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                              'Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'",
                              **(transfer.headers or {})}.items():self.send_header(key,value)
            if self.server.service.config.secure:self.send_header('Strict-Transport-Security','max-age=31536000')
            self.end_headers()
            remaining=transfer.size
            while remaining:
                try:
                    transfer.validate()
                    block=transfer.stream.read(min(65536,remaining))
                    if not block:break
                    self.wfile.write(block);remaining-=len(block)
                except (AuthError,DataError,OSError):
                    # Headers already sent: terminate transfer, never append a JSON error.
                    break
        finally:transfer.close()
