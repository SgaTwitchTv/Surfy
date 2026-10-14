"""Owner-only diagnostic capture; sources are operator configuration, never user paths."""
import json
import re
import subprocess
from greenwave.vision_capture import CaptureController
from greenwave.school_accounts.errors import AuthError
from greenwave.school_records.writes import fields,revision
from greenwave.school_data.validation import text, operation_key, request_hash
from greenwave.school_resources.policy import resource_id
from greenwave.school_resources.files import Transfer


class Vision:
    def __init__(self,recorder,files,sources=None):
        self.recorder,self.policy,self.repo,self.files=recorder,recorder.policy,recorder.repo,files
        self.sources=dict(getattr(self.policy.accounts.config,'cv_sources',())) if sources is None else dict(sources)
        if len(self.sources)>32:raise ValueError('Too many configured CV sources')
        for name,source in self.sources.items():
            if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9._:-]{1,80}',name):raise ValueError('Invalid source label')
            if name.startswith('camera:'):
                if type(source) is not int or not 0<=source<=16:raise ValueError('Invalid configured camera')
            else:
                from pathlib import Path
                self.repo.database.storage._safe(Path(source))
        self.captures={}
        config=self.policy.accounts.config
        self.model=None
        if config.cv_model:
            from pathlib import Path
            if config.cv_license_ack!='operator-verified-license':raise ValueError('Operator license acknowledgement required')
            self.model=self.repo.database.storage._safe(Path(config.cv_model))
            if self.model.suffix!='.pt' or not self.model.is_file():raise ValueError('Configured local model unavailable')

    def close_trip(self,tid):
        for ctx in self.captures.values():
            if ctx['trip_id']==tid:ctx['capture'].close()

    def start(self,raw,tid,body):
        fields(body,{'source_type'},{'source_ref','camera_index','width','height','fps','detection','realtime'})
        with self.recorder.lock:
            row,_=self.policy.session(raw);_,_,trip,_=self.policy.trip(raw,tid,True)
            nav=self.recorder.own_context(row,tid)
            if trip['status']!='RECORDING' or not nav.get('drive') or nav['drive'].closed:raise AuthError(409,'ACTIVE_NAVIGATION_REQUIRED')
            if body['source_type']=='CAMERA':
                self.recorder.devices.real();name='camera:'+str(body.get('camera_index'))
                if type(body.get('camera_index')) is not int:raise AuthError(422,'VALIDATION')
            elif body['source_type']=='FILE':name=body.get('source_ref')
            else:raise AuthError(422,'VALIDATION')
            if not isinstance(name,str) or name not in self.sources:raise AuthError(422,'SOURCE_UNAVAILABLE')
            if type(body.get('detection',False)) is not bool:raise AuthError(422,'VALIDATION')
            if body.get('detection',False) and self.model is None:raise AuthError(422,'DETECTOR_NOT_CONFIGURED')
            if any(v['trip_id']==tid and v['capture'].process.poll() is None for v in self.captures.values()):raise AuthError(409,'CAPTURE_BUSY')
            root=self.repo.database.storage._safe(self.repo.database.storage.trip(trip['owner_id'],tid)/'cv')
            controller=CaptureController(root,python=self.policy.accounts.config.cv_python or None)
            try:
                # Optional imports happen in the capture worker, never synchronously
                # in a portal request. Missing dependencies become a bounded FAILED
                # diagnostic state rather than blocking navigation or authentication.
                result=controller.start(source_type=body['source_type'],source=self.sources[name],run_id=trip['run_id'],detection=body.get('detection',False),weights_path=None if self.model is None else str(self.model),
                    **{k:body[k] for k in ('width','height','fps','realtime') if k in body})
            except (OSError,ValueError,subprocess.SubprocessError):
                controller.close();raise AuthError(503,'CAPTURE_UNAVAILABLE') from None
            cid=result['session_id']
            from greenwave.vision_workbench import VisionWorkbench
            reviews=self.repo.database.storage._safe(root/'reviews.sqlite3')
            self.captures[cid]={'trip_id':tid,'capture':controller,'navigation':nav['id'],'workbench':VisionWorkbench(controller,nav['drive'].app,path=reviews)}
            return self.status(raw,tid,cid)

    def status(self,raw,tid,cid):
        self.policy.trip(raw,tid,True);resource_id(cid)
        ctx=self.captures.get(cid)
        if ctx is None or ctx['trip_id']!=tid:return self.files.capture_dto(self.files.capture(raw,tid,cid)[2])
        self.repo.database.storage._safe(ctx['capture'].directory)
        state=ctx['capture'].status()
        frame=(state.get('frame') or {}).get('data')
        return {'id':cid,'status':state.get('status'),'frames_captured':state.get('frames_captured',0),
            'error_code':'CV_RUNTIME_UNAVAILABLE' if state.get('status')=='FAILED' else None,
            'frame_id':None if frame is None else frame['frame_id'],'preview_fresh':state.get('preview_fresh',False),
            'diagnostic_only':True,'live_prediction_eligible':False}

    def stop(self,raw,tid,cid,body):
        fields(body,set());self.policy.trip(raw,tid,True)
        ctx=self.captures.get(resource_id(cid))
        if not ctx or ctx['trip_id']!=tid:raise AuthError(404,'NOT_FOUND')
        ctx['capture'].stop();return self.status(raw,tid,cid)

    def frame(self,raw,tid,cid,frame):
        _,_,trip,_=self.policy.trip(raw,tid,True)
        if not re.fullmatch('[0-9]{1,9}',frame):raise AuthError(404,'NOT_FOUND')
        root=self.repo.database.storage.cv(trip['owner_id'],tid,resource_id(cid))
        path=self.files.path(root,'preview-'+str(int(frame))+'.jpg')
        if not path.is_file():raise AuthError(404,'FRAME_EXPIRED')
        if path.stat().st_size>1048576:raise AuthError(409,'FRAME_TOO_LARGE')
        return Transfer(path.open('rb'),path.stat().st_size,lambda:self.policy.trip(raw,tid,True),'image/jpeg')

    def events(self,raw,tid,cid,q):
        self.policy.trip(raw,tid,True);resource_id(cid)
        ctx=self.captures.get(cid)
        if not ctx or ctx['trip_id']!=tid:return self.files.events(raw,tid,cid,q)
        self.repo.database.storage._safe(ctx['capture'].directory)
        from greenwave.school_resources.reads import pagination
        from greenwave.vision_contracts import decode_vision,VisionObservation
        from contextlib import closing
        limit,offset=pagination(q)
        workbench=ctx['workbench'];self.repo.database.storage._safe(workbench.path)
        workbench.ingest(cid)
        with closing(workbench.connect()) as db:
            rows=db.execute('SELECT id,payload FROM events WHERE capture_id=? ORDER BY rowid LIMIT ? OFFSET ?',(cid,limit,offset)).fetchall()
        items=[]
        for eid,payload in rows:
            event=decode_vision(json.loads(payload)['observation'])
            if not isinstance(event,VisionObservation):raise AuthError(409,'ARTIFACT_INVALID')
            items.append({'id':eid,'state':event.detection.state,'event_type':event.event_type,'track_id':event.detection.track_id,'frame_id':event.detection.frame.frame_id,'diagnostic_only':True})
        return {'items':items,'page':{'limit':limit,'offset':offset}}

    def associate(self,raw,tid,cid,body,remove=False):
        fields(body,{'track_id'} if remove else {'track_id','route_version_id','stop_line_id','movement'})
        text(body['track_id'],1,120)
        with self.recorder.lock:
            row,actor=self.policy.session(raw);_,_,trip,_=self.policy.trip(raw,tid,True)
            nav=self.recorder.own_context(row,tid)
            ctx=self.captures.get(resource_id(cid))
            if not ctx or ctx['trip_id']!=tid or ctx['navigation']!=nav['id']:raise AuthError(404,'NOT_FOUND')
            if remove:result=ctx['workbench'].unassign(body['track_id'])
            else:
                if body['route_version_id']!=trip['route_version_id']:raise AuthError(409,'ROUTE_CHANGED')
                route=nav['drive'].app.selected_route
                if route is None:raise AuthError(409,'GEOMETRY_UNAVAILABLE')
                line=next((l for l in route.stop_lines if l.stop_line_id==body['stop_line_id']),None)
                if line is None or line.movement!=body['movement']:raise AuthError(422,'VALIDATION')
                try:result=ctx['workbench'].assign(body['track_id'],route.route_id,route.geometry_hash,line.stop_line_id)
                except ValueError:raise AuthError(409,'TRACK_NOT_FRESH') from None
            with self.repo.database.transaction() as c:
                self.repo.audit(c,actor,'CV_ASSOCIATION_REMOVED' if remove else 'CV_ASSOCIATION','TRIP',tid,json.dumps({'capture_id':cid,'track_id':body['track_id'],'server_at':self.repo.clock()}))
            return result

    def review(self,raw,tid,cid,body,request_id):
        fields(body,{'event_id','status','reason','expected_revision','client_operation_id'})
        if body['status'] not in {'ACCEPTED','REJECTED'}:raise AuthError(422,'VALIDATION')
        text(body['event_id'],1,256);text(body['reason'],3,500);revision(body['expected_revision']);operation_key(body['client_operation_id'])
        # Evidence remains immutable; review is an append-only audited separate fact.
        self.policy.trip(raw,tid,True)
        ctx=self.captures.get(resource_id(cid))
        if ctx and ctx['trip_id']==tid:
            from contextlib import closing
            workbench=ctx['workbench'];self.repo.database.storage._safe(workbench.path);workbench.ingest(cid)
            with closing(workbench.connect()) as index:exists=index.execute('SELECT 1 FROM events WHERE capture_id=? AND id=?',(cid,body['event_id'])).fetchone() is not None
        else:exists=self.files.event_exists(raw,tid,cid,body['event_id'])
        if not exists:raise AuthError(404,'EVENT_NOT_FOUND')
        with self.repo.atomic(request_id) as (repo,c):
            _,actor,trip,_=self.policy.basis_trip(raw,tid,owner_only=True,connection=c)
            entries=c.execute("SELECT reason FROM audit_events WHERE resource_id=? AND action='CV_REVIEW' ORDER BY server_at,sequence",(tid,)).fetchall()
            records=[json.loads(r[0]) for r in entries]
            fingerprint=request_hash(body)
            existing=next((r for r in records if r['client_operation_id']==body['client_operation_id'] and r['actor_id']==actor.user_id),None)
            if existing:
                if existing['request_hash']!=fingerprint:raise AuthError(409,'IDEMPOTENCY_CONFLICT')
                return {k:v for k,v in existing.items() if k!='request_hash'}
            previous=[r for r in records if r['capture_id']==cid and r['event_id']==body['event_id']]
            if len(previous)!=body['expected_revision']:raise AuthError(409,'REVISION_CONFLICT')
            data={**body,'capture_id':cid,'actor_id':actor.user_id,'server_at':repo.clock(),'revision':len(previous)+1,'request_hash':fingerprint,'live_prediction_eligible':False}
            repo.audit(c,actor,'CV_REVIEW','TRIP',tid,json.dumps(data,separators=(',',':')))
            return {k:v for k,v in data.items() if k!='request_hash'}
