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
            server=AccountsHTTPServer(('127.0.0.1',port),service)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            print(json.dumps({'url':cfg.base_url,'mailbox':f'http://127.0.0.1:{mailbox.server_port}', 'trips':None if fixture is None else {k:v['id'] for k,v in fixture['trips'].items()}}),flush=True)
            try:input()
            finally:
                server.shutdown();server.server_close();service.close()
                for receiver in [smtp,mailbox]:receiver.shutdown();receiver.server_close()


if __name__=='__main__':main()
