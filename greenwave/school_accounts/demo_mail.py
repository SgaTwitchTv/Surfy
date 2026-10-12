"""Local-only synthetic SMTP sink + operator inbox. No persistent mailbox."""
import argparse
import html
import json
import socketserver
import threading
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer


class Inbox:
    def __init__(self):self.messages=[];self.lock=threading.Lock()
    def append(self,data):
        message=BytesParser(policy=policy.default).parsebytes(data)
        with self.lock:
            self.messages.append({'to':str(message['To']),'subject':str(message['Subject']),'body':message.get_body(preferencelist=('plain',)).get_content()})
            self.messages=self.messages[-100:]


class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        def reply(text):self.wfile.write((text+'\r\n').encode());self.wfile.flush()
        reply('220 GreenWave synthetic local inbox')
        recipient=False
        while True:
            line=self.rfile.readline(8193)
            if not line or len(line)>8192:return
            command=line.decode('ascii',errors='replace').strip()
            upper=command.upper()
            if upper.startswith(('EHLO','HELO')):reply('250 localhost')
            elif upper.startswith('MAIL FROM:'):reply('250 sender accepted')
            elif upper.startswith('RCPT TO:'):
                address=command.split(':',1)[1].strip().split(' ')[0].strip('<>')
                recipient=address.lower().endswith('@example.test')
                reply('250 synthetic recipient accepted' if recipient else '550 only example.test recipients')
            elif upper=='DATA':
                if not recipient:reply('550 recipient required');continue
                reply('354 end with dot')
                lines=[];size=0
                while True:
                    data=self.rfile.readline(8193)
                    if not data:return
                    if data==b'.\r\n':break
                    size+=len(data)
                    if size>65536:return
                    lines.append(data[1:] if data.startswith(b'..') else data)
                self.server.inbox.append(b''.join(lines));reply('250 stored in volatile synthetic inbox')
            elif upper=='QUIT':reply('221 goodbye');return
            elif upper in {'RSET','NOOP'}:reply('250 OK')
            else:reply('502 unsupported')


class SMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
    def __init__(self,address,inbox):self.inbox=inbox;super().__init__(address,SMTPHandler)
    def handle_error(self,*args):pass


class InboxHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.headers.get('Host') not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}:
            self.send_error(403);return
        with self.server.inbox.lock:messages=list(self.server.inbox.messages)
        if self.path=='/messages':
            body=json.dumps(messages).encode();mime='application/json'
        elif self.path=='/':
            items=''.join('<article><h2>'+html.escape(m['subject'])+'</h2><p>'+html.escape(m['to'])+'</p><pre>'+html.escape(m['body'])+'</pre></article>' for m in reversed(messages))
            body=('<!doctype html><html lang="pl"><meta charset="utf-8"><title>Poczta syntetyczna GreenWave</title><h1>Poczta demo — tylko example.test</h1><p>Odśwież stronę. Skopiuj link z wiadomości. Skrzynka jest wyłącznie lokalna i znika po restarcie.</p>'+items+'</html>').encode();mime='text/html; charset=utf-8'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)


def main():
    parser=argparse.ArgumentParser(description='Volatile LOCAL synthetic inbox; never a production mail service')
    parser.add_argument('--smtp-port',type=int,default=1025);parser.add_argument('--web-port',type=int,default=8771)
    args=parser.parse_args();inbox=Inbox()
    smtp=SMTPServer(('127.0.0.1',args.smtp_port),inbox)
    web=ThreadingHTTPServer(('127.0.0.1',args.web_port),InboxHandler);web.inbox=inbox
    thread=threading.Thread(target=smtp.serve_forever,daemon=True);thread.start()
    print(f'SYNTHETIC ONLY SMTP 127.0.0.1:{args.smtp_port}; inbox http://127.0.0.1:{args.web_port}')
    try:web.serve_forever()
    except KeyboardInterrupt:pass
    finally:smtp.shutdown();smtp.server_close();web.server_close()


if __name__=='__main__':main()
