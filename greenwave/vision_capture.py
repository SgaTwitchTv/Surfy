"""Non-blocking supervisor for an opt-in capture subprocess, without ML imports."""
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from uuid import uuid4

VIDEO_EXTENSIONS={'.mp4','.avi','.mov','.mkv','.webm','.m4v'}


def validate_source(kind, value):
    if kind == 'CAMERA':
        if type(value) is not int or not 0 <= value <= 16:
            raise ValueError('Camera index must be an integer from 0 to 16')
        return value
    if kind != 'FILE' or not isinstance(value, str):
        raise ValueError('Choose CAMERA or FILE')
    path=Path(value).expanduser().resolve()
    if path.suffix.lower() not in VIDEO_EXTENSIONS or not path.is_file():
        raise ValueError('Choose an existing local video file (.mp4/.avi/.mov/.mkv/.webm/.m4v)')
    return str(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return None


class CaptureController:
    def __init__(self, root, python=None):
        self.root=Path(root).resolve()
        repo=Path(__file__).resolve().parents[1]
        candidate=repo/'.venv-cv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        self.python=str(python or (candidate if candidate.is_file() else sys.executable))
        self.process=None;self.directory=None;self.log=None;self.stop_requested=None;self.forced=False

    def status(self):
        if self.directory is None:
            return dict(status='IDLE',session_id=None,preview_fresh=False,live_prediction_eligible=False)
        result=read_json(self.directory/'status.json') or dict(status='STARTING',session_id=self.directory.name)
        if self.stop_requested is not None and self.process.poll() is None and time.monotonic()-self.stop_requested>3 and result.get('status')!='FINALIZING':
            self.process.terminate();self.forced=True
        code=self.process.poll()
        if code is not None:
            # The worker can finalize between the first read and poll().
            result=read_json(self.directory/'status.json') or result
            if self.log is not None:self.log.close();self.log=None
            if self.forced or code!=0 or result.get('status') not in ('STOPPED','ENDED','FAILED'):
                result.update(status='FAILED',error=result.get('error') or 'Capture worker terminated; recording may be incomplete',forced_stop=self.forced)
                manifest=read_json(self.directory/'manifest.json')
                if manifest and manifest.get('complete'):
                    manifest.update(complete=False,status='FAILED',error=result['error'])
                    (self.directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        frame=(result.get('frame') or {}).get('data',{})
        age=max(0.,time.monotonic()-frame['captured_monotonic_ns']/1e9) if frame else None
        result.update(frame_age_seconds=age,preview_fresh=result.get('status')=='RUNNING' and age is not None and age<2,
                      live_prediction_eligible=False)
        return result

    def start(self, *, source_type, source, width=1280, height=720, fps=30, realtime=True, run_id=None, replay_of=None, expected_source_sha256=None, detection=False,seek_seconds=0,weights_path=None):
        if self.process is not None and self.process.poll() is None and self.status()['status'] in ('ENDED','STOPPED','FAILED'):
            try:self.process.wait(timeout=.3)
            except subprocess.TimeoutExpired:pass
        if self.process is not None and self.process.poll() is None:
            raise ValueError('Stop the active capture before starting another')
        source=validate_source(source_type,source)
        if any(type(value) is not int for value in (width,height,fps)) or not (160<=width<=3840 and 120<=height<=2160 and 1<=fps<=60):
            raise ValueError('Invalid requested dimensions or FPS')
        if type(realtime) is not bool:raise ValueError('realtime must be boolean')
        if type(detection) is not bool:raise ValueError('detection must be boolean')
        if isinstance(seek_seconds,bool) or not isinstance(seek_seconds,(int,float)) or not math.isfinite(seek_seconds) or not 0<=seek_seconds<=86400 or (source_type=='CAMERA' and seek_seconds):raise ValueError('Invalid video seek time')
        weights=Path(weights_path) if weights_path is not None else Path(__file__).resolve().parents[1]/'data/derived/vision-probe/best_traffic_nano_yolo.pt'
        if detection and not weights.is_file():raise ValueError('Local model missing; run tools/prepare_vision_probe.py first')
        session=uuid4().hex;self.root.mkdir(parents=True,exist_ok=True)
        directory=self.root/session;directory.mkdir()
        config=dict(session_id=session,source_type=source_type,source=source,width=width,height=height,fps=fps,
                    realtime=realtime,run_id=run_id,replay_of=replay_of,expected_source_sha256=expected_source_sha256,clock_uncertainty_seconds=1.0,
                    detection=detection,weights=str(weights) if detection else None,seek_seconds=seek_seconds)
        (directory/'config.json').write_text(json.dumps(config),encoding='utf-8')
        if self.log is not None:self.log.close()
        self.log=(directory/'worker.log').open('wb')
        try:
            process=subprocess.Popen([self.python,'-m','greenwave.vision_capture_worker','--directory',str(directory)],
                cwd=Path(__file__).resolve().parents[1],stdin=subprocess.DEVNULL,stdout=self.log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        except OSError as error:
            self.log.close();self.log=None
            raise ValueError('Cannot launch CV runtime: '+str(error)) from error
        self.directory=directory;self.process=process;self.stop_requested=None;self.forced=False
        return self.status()

    def stop(self):
        if self.directory and self.process.poll() is None:
            (self.directory/'stop.flag').touch()
            if self.stop_requested is None:
                self.stop_requested=time.monotonic()
                process,directory=self.process,self.directory
                def watchdog():
                    status=read_json(directory/'status.json') or {}
                    if process.poll() is None and status.get('status')!='FINALIZING':
                        process.terminate()
                        if self.process is process:self.forced=True
                timer=threading.Timer(3,watchdog);timer.daemon=True;timer.start()
        result=self.status()
        if self.process is not None and self.process.poll() is None:result['status']='STOPPING'
        return result

    def preview(self, session_id, frame_id):
        current=self.status()
        if session_id!=current.get('session_id') or type(frame_id) is not int or frame_id<0:
            raise ValueError('Preview does not belong to the current capture')
        if current.get('status') not in ('RUNNING','ENDED','STOPPED') or not current.get('frame'):
            raise ValueError('No current frame')
        try:return (self.directory/f'preview-{frame_id}.jpg').read_bytes()
        except OSError as error:raise ValueError('Preview frame expired; refresh status') from error

    def recordings(self):
        if not self.root.exists():return []
        entries=[]
        for directory in sorted(self.root.iterdir(),key=lambda path:path.name):
            if not directory.is_dir() or not re.fullmatch('[0-9a-f]{32}',directory.name):continue
            manifest=read_json(directory/'manifest.json')
            if manifest:entries.append(manifest)
        return sorted(entries,key=lambda entry:entry.get('started_utc',''),reverse=True)

    def replay_source(self, session, segment=0):
        if not isinstance(session,str) or not re.fullmatch('[0-9a-f]{32}',session):raise ValueError('Invalid capture ID')
        if type(segment) is not int or segment<0:raise ValueError('Invalid segment')
        manifest=read_json(self.root/session/'manifest.json')
        videos=[item for item in (manifest or {}).get('artifacts',[]) if item.get('kind')=='VIDEO']
        if not manifest or not manifest.get('complete') or segment>=len(videos):raise ValueError('Recording or segment is not complete')
        path=(self.root/session/videos[segment]['filename']).resolve()
        if path.parent!=self.root/session:raise ValueError('Invalid recording path')
        return str(path),videos[segment]['sha256']

    def close(self):
        self.stop()
        if self.process is not None and self.process.poll() is None:
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=2);self.forced=True
        if self.log is not None:self.log.close();self.log=None
