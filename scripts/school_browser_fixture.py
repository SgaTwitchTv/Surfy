"""Synthetic test harness with production KDF; prints only local server addresses."""
import json
import os
import socket
import tempfile
import threading
from http.server import ThreadingHTTPServer
from greenwave.school_data import Storage,Database,Repository
from greenwave.school_data.migrations import migrate
from greenwave.school_accounts.config import Config
from greenwave.school_accounts.demo_mail import Inbox,SMTPServer,InboxHandler
from greenwave.school_accounts.http import AccountsHTTPServer
from greenwave.school_accounts.service import AccountsService


def main():
    with tempfile.TemporaryDirectory() as root:
        storage=Storage(root);migrate(storage)
        inbox=Inbox();smtp=SMTPServer(('127.0.0.1',0),inbox)
        mailbox=ThreadingHTTPServer(('127.0.0.1',0),InboxHandler);mailbox.inbox=inbox
        threads=[]
        for server in [smtp,mailbox]:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();threads.append(thread)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        cfg=Config(f'http://127.0.0.1:{port}',(f'127.0.0.1:{port}',),b'a'*32,b'b'*32,port=port,smtp_port=smtp.server_address[1])
        with Database(storage) as db:
            service=AccountsService(Repository(db),cfg)  # real N131072, never test injection
            fixture=None
            if os.environ.get('GW_RESOURCE_FIXTURE')=='1':
                from scripts.school_resource_fixtures import populate
                fixture=populate(service.repo,service.passwords.hash('Browser password 123!'))
                if os.environ.get('GW_SCHOOL_ROLE_FIXTURE')=='1':
                    service.repo.create_user('synthetic-long-email-'+('x'*40)+'@example.test','Długa nazwa '+('W'*68),fixture['users']['driver']['password_hash'],status='ACTIVE',verified_at=service.repo.clock())
                if os.environ.get('GW_SCHOOL_UI_FIXTURE')=='1':
                    from greenwave.school_data import Actor
                    actor=Actor(fixture['users']['driver']['id'])
                    admin=Actor(fixture['users']['admin']['id'],service.repo.clock())
                    from greenwave.school_admin.validation import payload
                    route_payload={'schema_version':1,'route_id':'Warszawa-demo','geometry_version':'v1','name':'Warszawa demo','direction_description':'North','source':{'attribution':'Synthetic'},'coordinates':[[21,52],[21.001,52.001]],'stop_lines':[{'stop_line_id':'synthetic-light','segment_index':0,'coordinates':[[21.0004,52.0006],[21.0006,52.0004]],'position_uncertainty_m':1,'source':{'attribution':'Synthetic'}}]}
                    route=service.repo.create_config(admin,'ROUTE','Warszawa-demo',payload('ROUTE',route_payload))
                    service.repo.publish_config(admin,route['id'],route['revision'])
                    for index in range(28):
                        trip=service.repo.create_trip(actor,'Historia demonstracyjna '+str(index),note='Tylko syntetyczne dane testowe.')
                        obs=service.repo.add_observation(actor,fixture['trips']['private']['id'],'synthetic-light','RED','STATE_SEEN','ui-history-'+str(index),historical=True)
                        with db.transaction() as c:c.execute("UPDATE observations SET journaling_state='APPLIED' WHERE id=?",(obs['id'],))

            server=AccountsHTTPServer(('127.0.0.1',port),service)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            print(json.dumps({'url':cfg.base_url,'mailbox':f'http://127.0.0.1:{mailbox.server_port}', 'trips':None if fixture is None else {k:v['id'] for k,v in fixture['trips'].items()}}),flush=True)
            try:input()
            finally:
                server.shutdown();server.server_close();service.close()
                for receiver in [smtp,mailbox]:receiver.shutdown();receiver.server_close()


if __name__=='__main__':main()
