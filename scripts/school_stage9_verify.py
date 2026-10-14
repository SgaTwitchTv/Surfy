"""Full Python regression and stage coverage in a synthetic, isolated source export."""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--coverage-python',required=True);args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1];artifacts=repo/'artifacts';artifacts.mkdir(exist_ok=True)
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
    with tempfile.TemporaryDirectory(prefix='gw-stage9-source-') as root:
        root=Path(root)
        for name in selected:
            source=repo/name;target=root/name
            if not source.is_file():continue
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        # Only new temp files can be created by default-root M8 tests.
        env={**os.environ,'PYTHONIOENCODING':'utf-8','COVERAGE_FILE':str(artifacts/'stage9.coverage')}
        scope=','.join(['greenwave.school_accounts','greenwave.school_data','greenwave.school_resources','greenwave.school_records','greenwave.school_admin','greenwave.school_navigation','greenwave.telemetry','greenwave.application','greenwave.clocks','greenwave.gps_replay','greenwave.replay','greenwave.positioning','greenwave.map_matching','greenwave.live_navigation','greenwave.vision_capture','greenwave.vision_workbench'])
        configuration=root/'stage9-coverage.ini';configuration.write_text('[run]\nrelative_files = True\nbranch = True\nsource = '+scope+'\n',encoding='utf-8')
        command=[str(Path(args.coverage_python).resolve()),'-m','coverage','run','--rcfile='+str(configuration),'-m','unittest','discover','-s','tests','-v']
        subprocess.run([str(Path(args.coverage_python).resolve()),'-c',"import pathlib,greenwave.application;assert pathlib.Path(greenwave.application.__file__).resolve().is_relative_to(pathlib.Path.cwd());print('Exported module origin verified')"],cwd=root,env=env,check=True)
        smoke="from pathlib import Path; import threading,json,urllib.request; from greenwave.application import GreenWaveApplication;from greenwave.server import LocalServer; app=GreenWaveApplication(runs_root=Path.cwd()/'synthetic-runtime'/'runs');server=LocalServer(0,application=app);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();response=urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/api/state');state=json.load(response);assert response.status==200;response.close();server.shutdown();server.server_close();print('Base GreenWave synthetic HTTP smoke PASS')"
        subprocess.run([str(Path(args.coverage_python).resolve()),'-c',smoke],cwd=root,env=env,check=True)
        result=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (artifacts/'stage9-python-tests.txt').write_text(result.stdout,encoding='utf-8')
        print('Isolated full regression exit:',result.returncode)
        print('\n'.join(result.stdout.splitlines()[-16:]))
        (artifacts/'stage9-coverage.ini').write_text(configuration.read_text(encoding='utf-8'),encoding='utf-8')
        report=[str(Path(args.coverage_python).resolve()),'-m','coverage','json','--rcfile='+str(configuration),'-o',str(artifacts/'stage9-python-coverage.json')]
        subprocess.run(report,cwd=root,env=env,check=True)
        subprocess.run([str(Path(args.coverage_python).resolve()),'-m','coverage','report','--rcfile='+str(configuration)],cwd=root,env=env,check=True)
        raise SystemExit(result.returncode)


if __name__=='__main__':main()
