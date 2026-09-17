"""Offline local UI. One server thread serializes all application events."""
import argparse
from dataclasses import asdict
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import time
import webbrowser

from greenwave.application import DATA, GreenWaveApplication
from greenwave.replay import ReplaySession
from greenwave.analysis import RunAnalysis

STATIC = Path(__file__).resolve().parent / 'web'


class LocalServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, port=8765, application=None, host='127.0.0.1'):
        self.application = application if application is not None else GreenWaveApplication()
        self.token = secrets.token_hex(32)
        self.replay = ReplaySession(self.application.logger)
        self.analysis = RunAnalysis(self.application.logger)
        self.replay_tick = time.monotonic()
        self.bind_host = host
        self.allow_network = host not in ('127.0.0.1', 'localhost')
        super().__init__((host, port), Handler)

    def server_close(self):
        try:
            self.application.close()
        finally:
            super().server_close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send(self, status, content, content_type='application/json; charset=utf-8', download=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if download:
            self.send_header('Content-Disposition', f'attachment; filename="{download}"')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(content)

    def _valid_host(self):
        host = self.headers.get('Host', '')
        if self.server.allow_network:
            return host.rsplit(':', 1)[-1] == str(self.server.server_port)
        return host in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self._valid_host():
            return self._send(403, {'error': 'Invalid local Host header'})
        route = self.path.split('?', 1)[0]
        if route == '/api/state':
            return self._send(200, self.server.application.snapshot())
        if route == '/mobile':
            content = (STATIC / 'mobile.html').read_bytes().replace(b'__GREENWAVE_TOKEN__', self.server.token.encode('ascii'))
            return self._send(200, content, 'text/html; charset=utf-8')
        if route == '/api/replay/state':
            now=time.monotonic(); self.server.replay.advance(now-self.server.replay_tick); self.server.replay_tick=now
            return self._send(200, self.server.replay.state())
        if route.startswith('/api/analysis/'):
            try:
                path=route.removeprefix('/api/analysis/')
                if path=='compare':
                    from urllib.parse import parse_qs, urlparse
                    query=parse_qs(urlparse(self.path).query)
                    return self._send(200,self.server.analysis.compare(query['baseline'][0],query['greenwave'][0]))
                return self._send(200,self.server.analysis.analyze(path))
            except (OSError,ValueError,KeyError,IndexError) as error:
                return self._send(400,{'error':str(error)})
        if route == '/api/runs' or route.startswith('/api/runs/'):
            try:
                logger = self.server.application.logger
                if route.startswith('/api/runs/') and self.headers.get('X-GreenWave-Token') != self.server.token:
                    return self._send(403, {'error': 'Unauthorized local request'})
                if route == '/api/runs':
                    return self._send(200, logger.list_runs())
                run_id = route.removeprefix('/api/runs/').removesuffix('.zip')
                return self._send(200, logger.export(run_id), 'application/zip', f'greenwave-{run_id}.zip')
            except (OSError, ValueError) as error:
                return self._send(400, {'error':str(error)})
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/mobile.js': ('mobile.js', 'text/javascript; charset=utf-8')}
        if route == '/map-data.json':
            return self._send(200, (DATA / 'maps/warsaw.json').read_bytes())
        if route not in files:
            return self._send(404, {'error': 'Not found'})
        filename, content_type = files[route]
        content = (STATIC / filename).read_bytes()
        if route in ('/', '/mobile.js'):
            content = content.replace(b'__GREENWAVE_TOKEN__', self.server.token.encode('ascii'))
        self._send(200, content, content_type)

    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
        except ValueError:
            return self._send(400,{'error':'Invalid Content-Length'})
        if length<=0 or length>8192:
            return self._send(413,{'error':'Request body must be 1–8192 bytes'})
        self.connection.settimeout(5)
        payload=self.rfile.read(length)
        if not self._valid_host() or self.headers.get('X-GreenWave-Token') != self.server.token:
            return self._send(403, {'error': 'Unauthorized local request'})
        origin = self.headers.get('Origin')
        allowed_origin = origin in (None, f'http://127.0.0.1:{self.server.server_port}',
                                    f'http://localhost:{self.server.server_port}')
        if self.server.allow_network:
            allowed_origin = origin is None or origin.rsplit(':', 1)[-1] == str(self.server.server_port)
        if not allowed_origin:
            return self._send(403, {'error': 'Cross-origin requests are not allowed'})
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object')
            app = self.server.application
            if data.pop('session_id', None) != app.session_id:
                return self._send(409, {'error': 'Sesja zmieniła się. Odśwież widok i ponów działanie.'})
            if self.path == '/api/control':
                app.control(**data)
            elif self.path == '/api/reset':
                app.reset(**data)
            elif self.path == '/api/observe':
                app.observe(**data)
            elif self.path == '/api/recording':
                app.recording(**data)
            elif self.path == '/api/position':
                sample = app.ingest_external_position(**data)
                self._send(200, {'external_position': asdict(sample),
                                 'external_status': app.external_position.status()})
                return
            elif self.path == '/api/replay':
                command=data.pop('command',None); value=data.pop('value',None)
                self.server.replay_tick=time.monotonic(); self.server.replay.command(command,value)
                self._send(200,self.server.replay.state()); return
            else:
                return self._send(404, {'error': 'Not found'})
            self._send(200, app.snapshot())
        except (ValueError, TypeError, KeyError) as error:
            self._send(400, {'error': str(error)})


def main():
    parser = argparse.ArgumentParser(description='GreenWave local navigation laboratory')
    parser.add_argument('--lab', action='store_true', help='Open the legacy Tkinter P02 laboratory')
    parser.add_argument('--port', type=int, default=8765, help='Port (0 chooses a free port)')
    parser.add_argument('--host', default='127.0.0.1', help='Bind address; use 0.0.0.0 only on a trusted private network')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if args.lab:
        from greenwave.ui import main as lab_main
        return lab_main()
    with LocalServer(args.port, host=args.host) as server:
        display_host = '127.0.0.1' if args.host in ('0.0.0.0', '') else args.host
        url = f'http://{display_host}:{server.server_port}'
        print(f'GreenWave M7: {url}\nRecordings, replay and analysis enabled. Ctrl+C closes an active recording.', flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
