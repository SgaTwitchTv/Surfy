"""Independent CV review journal; never imports events into phase learning."""
from contextlib import closing
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sqlite3
import time
from greenwave.vision_contracts import decode_vision,SignalAssociation
from greenwave.vision_capture import read_json


class VisionWorkbench:
    def __init__(self,capture,application,path=None):
        self.capture=capture;self.app=application;self.path=Path(path or capture.root/'reviews.sqlite3')
        self.assignments={};self.assignment_epochs={};self.last_scope=None

    def connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(self.path)
        db.executescript('''CREATE TABLE IF NOT EXISTS events(capture_id TEXT,id TEXT,payload TEXT,PRIMARY KEY(capture_id,id));
        CREATE TABLE IF NOT EXISTS cursors(capture_id TEXT PRIMARY KEY,position INTEGER);
        CREATE TABLE IF NOT EXISTS decisions(sequence INTEGER PRIMARY KEY,event_capture TEXT,event_id TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS assignments(sequence INTEGER PRIMARY KEY,payload TEXT);
        CREATE INDEX IF NOT EXISTS decisions_by_event ON decisions(event_capture,event_id,sequence);''')
        return db

    def directory(self,capture_id):
        if not isinstance(capture_id,str) or not re.fullmatch('[a-f0-9]{32}',capture_id):raise ValueError('Invalid capture ID')
        directory=self.capture.root/capture_id
        if not directory.is_dir() or directory.resolve().parent!=self.capture.root.resolve():raise ValueError('Capture does not exist or escapes capture root')
        return directory

    def ingest(self,capture_id):
        directory=self.directory(capture_id);path=directory/'events.jsonl'
        if not path.exists():path=directory/'vision.jsonl'
        if not path.exists():return dict(imported=0,pending=False)
        imported=0
        with closing(self.connect()) as db,db:
            cursor=db.execute('SELECT position FROM cursors WHERE capture_id=?',(capture_id,)).fetchone()
            position=cursor[0] if cursor else 0
            with path.open('rb') as stream:
                stream.seek(position);read=0
                while read<256*1024:
                    start=stream.tell();line=stream.readline(65537)
                    if not line:break
                    if len(line)>65536:raise ValueError('Oversized vision journal row')
                    if not line.endswith(b'\n'):stream.seek(start);break
                    row=json.loads(line);read+=len(line)
                    for item in row.get('events',[]):
                        observation=decode_vision(item['observation'])
                        if observation.__class__.__name__!='VisionObservation':raise ValueError('Invalid observation')
                        previous=db.execute('SELECT payload FROM events WHERE capture_id=? AND id=?',(capture_id,observation.observation_id)).fetchone()
                        if previous and json.loads(previous[0])!=item:raise ValueError('Immutable event evidence changed')
                        result=db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(capture_id,observation.observation_id,json.dumps(item)))
                        imported+=result.rowcount
                position=stream.tell()
            db.execute('INSERT OR REPLACE INTO cursors VALUES(?,?)',(capture_id,position))
        return dict(imported=imported,pending=position<path.stat().st_size)

    def line(self,route_id,geometry_hash,line_id):
        route=self.app.routes.load(route_id)
        if route.geometry_hash!=geometry_hash:raise ValueError('Route geometry changed')
        line=next((line for line in route.stop_lines if line.stop_line_id==line_id),None)
        if line is None or not line.movement:raise ValueError('Directional stop line required')
        return route,line

    def association(self,session,track,route,line):
        return SignalAssociation(session,track,'CONFIRMED','MANUAL',route.route_id,route.geometry_hash,line.stop_line_id,
            line.direction,line.movement,line.source.get('label',line.stop_line_id),
            sum(p[1] for p in line.coordinates)/2,sum(p[0] for p in line.coordinates)/2).to_dict()

    def status(self):
        status=self.capture.status();route=self.app.selected_route
        frame=(status.get('frame') or {}).get('data',{})
        scope=(status.get('session_id'),frame.get('session_id'),None if route is None else (route.route_id,route.geometry_hash),self.app.session_id,self.app.view_mode)
        if scope!=self.last_scope:self.assignments={};self.assignment_epochs={};self.last_scope=scope
        tracks=(status.get('vision') or {}).get('tracks',[]) if status.get('preview_fresh') else []
        visible={track['track_id']:track for track in tracks}
        self.assignments={k:a for k,a in self.assignments.items() if k in visible and self.assignment_epochs.get(k)==visible[k].get('continuity_generation',0)}
        self.assignment_epochs={k:epoch for k,epoch in self.assignment_epochs.items() if k in self.assignments}
        associations=[];groups={}
        for key,a in self.assignments.items():
            associations.append(a);groups.setdefault(a['data']['stop_line_id'],[]).append(visible[key])
        signals=[]
        for line,lamps in groups.items():
            stop=next(item for item in route.stop_lines if item.stop_line_id==line)
            states={lamp['state'] for lamp in lamps};known=states-{'UNKNOWN','OFF'}
            state='CONFLICT' if len(known)>1 else next(iter(known)) if len(states)==1 and known else 'UNKNOWN'
            signals.append(dict(stop_line_id=line,state=state,source='CV_MANUAL_ASSOCIATION',
                direction=stop.direction,movement=stop.movement,
                track_ids=[lamp['track_id'] for lamp in lamps],route_id=route.route_id,geometry_hash=route.geometry_hash,
                historical=status.get('source_type')!='CAMERA',live_prediction_eligible=False))
        mapping=self.app.mapping_snapshot();result=mapping.get('result',{});candidates=[]
        for signal in signals:
            manual=next((event for event in reversed(mapping.get('route_observations',[])) if event.get('route_id')==route.route_id and event.get('geometry_hash')==route.geometry_hash and event.get('stop_line_id')==signal['stop_line_id']),None)
            if manual and status.get('source_type')=='CAMERA':
                try:
                    age=abs((datetime.fromisoformat(frame['captured_utc'])-datetime.fromisoformat(manual['timestamp'])).total_seconds())
                    if age<=2 and signal['state'] not in ('UNKNOWN',manual['state']):
                        signal.update(state='CONFLICT',manual_state=manual['state'],conflict_reason='MANUAL_CV_DISAGREEMENT',comparison_uncertainty_seconds=1)
                except (ValueError,KeyError,TypeError):pass
        if route and result.get('status')=='MATCHED' and result.get('direction')=='FORWARD' and result.get('accepted_s_m') is not None:
            candidates=[dict(stop_line_id=line.stop_line_id,name=line.source.get('label',line.stop_line_id),distance_m=line.s_m-result['accepted_s_m'],confirmed=False)
                for line in route.stop_lines if line.s_m>=result['accepted_s_m']][:5]
        status.update(associations=associations,signals=signals,candidates=candidates)
        return status

    def assign(self,track_id,route_id,geometry_hash,stop_line_id):
        status=self.status();route,line=self.line(route_id,geometry_hash,stop_line_id)
        if self.app.selected_route is None or (self.app.selected_route.route_id,self.app.selected_route.geometry_hash)!=(route_id,geometry_hash):raise ValueError('Select this route first')
        tracks=(status.get('vision') or {}).get('tracks',[])
        if not status.get('preview_fresh') or not any(t['track_id']==track_id for t in tracks):raise ValueError('Track is no longer visible')
        track=next(t for t in tracks if t['track_id']==track_id)
        pictogram=track.get('pictogram','UNKNOWN')
        expected={'ARROW_LEFT':'LEFT','ARROW_RIGHT':'RIGHT','ARROW_STRAIGHT':'STRAIGHT'}.get(pictogram)
        if pictogram=='PEDESTRIAN' or (expected and line.movement!=expected):raise ValueError('Lamp pictogram conflicts with vehicle movement')
        frame=status['frame']['data'];a=self.association(frame['session_id'],track_id,route,line)
        self.assignments[track_id]=a
        self.assignment_epochs[track_id]=next(t.get('continuity_generation',0) for t in tracks if t['track_id']==track_id)
        with closing(self.connect()) as db,db:db.execute('INSERT INTO assignments(payload) VALUES(?)',(json.dumps(dict(capture_id=status['session_id'],frame_id=frame['frame_id'],association=a,utc=datetime.now(timezone.utc).isoformat())),))
        return a

    def unassign(self,track_id):
        self.assignments.pop(track_id,None)
        return dict(unassigned=track_id)

    def history(self,capture_id,before=None):
        if before is not None and (type(before) is not int or not 0<before<2**63):raise ValueError('Invalid history cursor')
        progress=self.ingest(capture_id)
        manifest=read_json(self.directory(capture_id)/'manifest.json') or {}
        videos=[a for a in manifest.get('artifacts',[]) if a.get('kind')=='VIDEO']
        with closing(self.connect()) as db:
            rows=db.execute('SELECT rowid,id,payload FROM events WHERE capture_id=? AND rowid<? ORDER BY rowid DESC LIMIT 201',(capture_id,before or 2**63-1)).fetchall()
            next_cursor=rows[199][0] if len(rows)>200 else None
            rows=rows[:200]
            entries=[]
            for _,event_id,payload in rows:
                decisions=[json.loads(row[0]) for row in db.execute('SELECT payload FROM decisions WHERE event_capture=? AND event_id=? ORDER BY sequence',(capture_id,event_id))]
                evidence=json.loads(payload);frame=evidence['observation']['data']['detection']['frame']
                segment=next((index for index,video in enumerate(videos) if video['filename']==Path(frame.get('media_ref') or '').name),None)
                entries.append(dict(event_id=event_id,evidence=evidence,media_segment=segment,media_pts_seconds=frame.get('pts_seconds'),decisions=decisions,review_status=decisions[-1]['status'] if decisions else 'PENDING'))
        manual=[]
        if manifest.get('run_id') and getattr(self.app,'logger',None):
            from greenwave.observation_history import ObservationHistory
            index=ObservationHistory(self.app.logger,self.app.routes).path
            if index.is_file():
                with closing(sqlite3.connect(index)) as db:
                    manual=[json.loads(row[0]) for row in db.execute('SELECT content FROM observations WHERE run_id=? ORDER BY timestamp DESC LIMIT 200',(manifest['run_id'],))]
        return dict(capture_id=capture_id,entries=entries,before=before,next_cursor=next_cursor,manual_entries=manual,run_id=manifest.get('run_id'),synchronization=manifest.get('synchronization'),import_progress=progress,live_prediction_eligible=False)

    def review(self,capture_id,event_id,status,reviewer,route_id=None,geometry_hash=None,stop_line_id=None):
        if not isinstance(event_id,str) or not event_id or len(event_id)>256:raise ValueError('Invalid event ID')
        if status not in ('ACCEPTED','REJECTED') or not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>100:raise ValueError('Decision and reviewer required')
        self.ingest(capture_id)
        with closing(self.connect()) as db,db:
            row=db.execute('SELECT payload FROM events WHERE capture_id=? AND id=?',(capture_id,event_id)).fetchone()
            if not row:raise ValueError('Event not found')
            evidence=json.loads(row[0]);observation=decode_vision(evidence['observation']);association=None
            if status=='ACCEPTED':
                route,line=self.line(route_id,geometry_hash,stop_line_id)
                pictogram=observation.detection.pictogram
                expected={'ARROW_LEFT':'LEFT','ARROW_RIGHT':'RIGHT','ARROW_STRAIGHT':'STRAIGHT'}.get(pictogram)
                if pictogram=='PEDESTRIAN' or (expected and line.movement!=expected):raise ValueError('Lamp pictogram conflicts with vehicle movement')
                association=self.association(observation.detection.frame.session_id,observation.detection.track_id,route,line)
            decision=dict(status=status,reviewer=reviewer.strip(),association=association,utc=datetime.now(timezone.utc).isoformat(),phase_learning_eligible=False)
            decision=json.loads(json.dumps(decision))
            last=db.execute('SELECT payload FROM decisions WHERE event_capture=? AND event_id=? ORDER BY sequence DESC LIMIT 1',(capture_id,event_id)).fetchone()
            if last:
                previous=json.loads(last[0])
                if all(previous.get(k)==decision.get(k) for k in ('status','reviewer','association')):return previous
            db.execute('INSERT INTO decisions(event_capture,event_id,payload) VALUES(?,?,?)',(capture_id,event_id,json.dumps(decision)))
        return decision

    def media(self,capture_id,segment=0):
        path,_=self.capture.replay_source(capture_id,segment)
        return Path(path)
