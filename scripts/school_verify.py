"""Final fixed-scope regression; never executes default-root M8 tests in checkout."""
import argparse, json, os, shutil, subprocess, sys, tempfile, traceback
from pathlib import Path


def run_captured(command, *, cwd=None, env=None):
    """Children emit UTF-8 regardless of the Windows parent's locale."""
    return subprocess.run(command,cwd=cwd,env=env,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='strict')


def show(message):
    # Preserve UTF-8 in artifacts; a legacy terminal must not abort the runner.
    encoding=getattr(sys.stdout,'encoding',None) or 'utf-8'
    print(message.encode(encoding,errors='backslashreplace').decode(encoding),flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--pattern',default='test_*.py',help='diagnostic subset; final acceptance uses default')
    parser.add_argument('--output',default='artifacts/stage10')
    args=parser.parse_args(argv);repo=Path(__file__).resolve().parents[1]
    artifacts=(repo/args.output).resolve();artifacts.mkdir(parents=True,exist_ok=True)
    progress=artifacts/'runner-progress.txt'
    progress.write_text('START\n',encoding='utf-8')
    try:return verify(args,repo,artifacts,progress)
    except Exception:
        (artifacts/'runner-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        show('Verification runner failed; see runner-error.txt (no environment secrets logged).')
        return 1


def verify(args,repo,artifacts,progress):
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=repo).decode().split('\0')
    new=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=repo).decode().split('\0')
    selected=[]
    for name in sorted(set(tracked+new)):
        if not name or not name.startswith(('greenwave/','tests/','scripts/','data/')):continue
        if name.startswith(('data/runs/','data/derived/','runtime/','artifacts/')):continue
        if name.startswith('data/') and not name.startswith(('data/corridors/','data/maps/','data/routes/','data/prediction/')) and name not in {'data/solver.json','data/trajectory.json'}:continue
        path=Path(name)
        if path.suffix.lower() in {'.db','.sqlite','.sqlite3','.pt','.onnx','.avi','.mp4','.mkv','.pem','.key','.png','.jpg'} or '__pycache__' in path.parts:continue
        selected.append(name)
    with progress.open('a',encoding='utf-8') as log:log.write('EXPORT\n')
    with tempfile.TemporaryDirectory(prefix='gw-stage10-source-') as temporary:
        root=Path(temporary)
        for name in selected:
            source=repo/name;target=root/name
            if not source.is_file():continue
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        shutil.copyfile(repo/'.coveragerc',root/'.coveragerc')
        env={k:v for k,v in os.environ.items() if not k.startswith(('SCHOOL_','GW_','COVERAGE_'))}
        env.update(PYTHONIOENCODING='utf-8',COVERAGE_FILE=str(artifacts/'python.coverage'),GW_TEST_RESULT=str(artifacts/'python-tests.json'))
        origin="import pathlib,greenwave.application;assert pathlib.Path(greenwave.application.__file__).resolve().is_relative_to(pathlib.Path.cwd());print('Isolated source origin PASS')"
        subprocess.run([sys.executable,'-c',origin],cwd=root,env=env,check=True)
        with progress.open('a',encoding='utf-8') as log:log.write('TESTS\n')
        command=[sys.executable,'-m','coverage','run','--rcfile=.coveragerc','-m','scripts.school_unittest','--pattern',args.pattern]
        result=run_captured(command,cwd=root,env=env)
        (artifacts/'python-tests.txt').write_text(result.stdout,encoding='utf-8')
        show('\n'.join(result.stdout.splitlines()[-18:]))
        statuses=[result.returncode]
        for fmt,output in [('json','python-coverage.json'),('xml','python-coverage.xml'),('html','python-html')]:
            flag='-d' if fmt=='html' else '-o'
            statuses.append(subprocess.run([sys.executable,'-m','coverage',fmt,'--rcfile=.coveragerc',flag,str(artifacts/output)],cwd=root,env=env).returncode)
        report=run_captured([sys.executable,'-m','coverage','report','--rcfile=.coveragerc'],cwd=root,env=env)
        (artifacts/'python-coverage.txt').write_text(report.stdout,encoding='utf-8');show(report.stdout);statuses.append(report.returncode)
        smoke="from pathlib import Path;import threading,json,urllib.request;from greenwave.application import GreenWaveApplication;from greenwave.server import LocalServer;app=GreenWaveApplication(runs_root=Path.cwd()/'synthetic-smoke'/'runs');s=LocalServer(0,application=app);t=threading.Thread(target=s.serve_forever,daemon=True);t.start();r=urllib.request.urlopen('http://127.0.0.1:'+str(s.server_port)+'/api/state');assert r.status==200;json.load(r);r.close();s.shutdown();s.server_close();print('Base HTTP smoke PASS')"
        statuses.append(subprocess.run([sys.executable,'-c',smoke],cwd=root,env=env).returncode)
        with progress.open('a',encoding='utf-8') as log:log.write('DONE codes='+','.join(map(str,statuses))+'\n')
        return 1 if any(statuses) else 0

if __name__=='__main__':raise SystemExit(main())
