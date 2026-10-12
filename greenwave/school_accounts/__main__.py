import argparse
import getpass
import json
import os
import secrets
import statistics
import time
from pathlib import Path
from greenwave.school_data import Storage,Database,Repository
from .config import Config
from .crypto import Passwords
from .service import AccountsService
from .http import AccountsHTTPServer
from .errors import AuthError


def main(argv=None):
    parser=argparse.ArgumentParser(description='GreenWave School accounts only; no legacy API')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('secrets').add_argument('--output',required=True)
    commands.add_parser('benchmark')
    serve=commands.add_parser('serve');serve.add_argument('--root',required=True);serve.add_argument('--host',default='127.0.0.1');serve.add_argument('--port',type=int,default=8770)
    bootstrap=commands.add_parser('bootstrap-admin');bootstrap.add_argument('--root',required=True);bootstrap.add_argument('--email',required=True);bootstrap.add_argument('--name',required=True);bootstrap.add_argument('--confirm-email-ownership',action='store_true',required=True)
    args=parser.parse_args(argv)
    if args.command=='secrets':
        path=Path(args.output).absolute();Storage(path.parent)._safe(path)
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'w',encoding='utf-8') as f:json.dump({'csrf_key':secrets.token_hex(32),'rate_key':secrets.token_hex(32)},f)
        print('Deployment keys created. Protect the file; never commit it.');return 0
    if args.command=='benchmark':
        kdf=Passwords();durations=[];cpus=[]
        for _ in range(3):
            started=time.perf_counter();cpu=time.process_time();kdf.hash('synthetic-benchmark-password')
            durations.append(time.perf_counter()-started);cpus.append(time.process_time()-cpu)
        peak=None
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
            counters=Counters();counters.cb=ctypes.sizeof(counters)
            ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
            ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
            if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(counters),ctypes.sizeof(counters)):peak=counters.PeakWorkingSetSize
        else:
            import resource
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        print(json.dumps({'n':131072,'r':8,'p':1,'dklen':32,'max_parallel':2,'maxmem_bytes':268435456,'core_memory_bytes':134217728,'seconds':durations,'median_seconds':statistics.median(durations),'cpu_seconds':cpus,'process_peak_rss_bytes':peak}));return 0
    cfg=Config.environment(getattr(args,'host','127.0.0.1'),getattr(args,'port',8770))
    with Database(Storage(args.root)) as db:
        service=AccountsService(Repository(db),cfg)
        try:
            if args.command=='bootstrap-admin':
                value=getpass.getpass('Administrator password: ');confirmation=getpass.getpass('Repeat password: ')
                if value!=confirmation:raise AuthError(422,'CONFIRMATION')
                service.bootstrap(args.email,args.name,value)
                print('First ADMIN created ACTIVE. Operator confirmed email ownership.');return 0
            server=AccountsHTTPServer((cfg.bind,cfg.port),service)
            print('GreenWave accounts at '+cfg.base_url+' (accounts only; explicit prepared database required)')
            try:server.serve_forever()
            except KeyboardInterrupt:pass
            finally:server.server_close()
        finally:service.close()
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('Startup/operation refused. Check prepared schema, explicit configuration and operator permissions; no secrets are logged.')
        raise SystemExit(1)
