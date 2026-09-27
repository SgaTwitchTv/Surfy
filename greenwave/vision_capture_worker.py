"""OpenCV capture subprocess. Original video and frame timeline stay outside Git."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from queue import Queue, Empty, Full
import threading
import time

from greenwave.vision_contracts import CameraFrameRef


def atomic_json(path, value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    # Windows readers can briefly hold the destination without delete sharing.
    for attempt in range(20):
        try:temporary.replace(path);return
        except PermissionError:
            if attempt==19:raise
            time.sleep(.01)


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):digest.update(chunk)
    return digest.hexdigest()


def offer_latest(queue, item):
    """Bounded live pipeline: discard an old unconsumed frame, never block."""
    dropped=0
    try:queue.put_nowait(item)
    except Full:
        try:queue.get_nowait();dropped=1
        except Empty:pass
        try:queue.put_nowait(item)
        except Full:dropped+=1
    return dropped


def run(directory):
    config=json.loads((directory/'config.json').read_text(encoding='utf-8'))
    started=datetime.now(timezone.utc).isoformat()
    manifest=dict(schema_version=1,session_id=config['session_id'],started_utc=started,configuration=config,
        run_id=config.get('run_id'),replay_of=config.get('replay_of'),complete=False,artifacts=[],segments=[],
        synchronization=dict(status='UNVERIFIED',clock_quality='HOST_READ_ESTIMATE_NOT_SENSOR_CAPTURE',
         uncertainty_seconds=config['clock_uncertainty_seconds'],uncertainty_is_assumed=True,
         note='Host monotonic/UTC pairs and media PTS are recorded. No automatic synchronization with historical GPS.'),
        live_prediction_eligible=False)
    atomic_json(directory/'manifest.json',manifest)
    shared=dict(status='STARTING',session_id=config['session_id'],source_type=config['source_type'],
                frames_captured=0,preview_dropped=0,reconnects=0,frame=None,error=None)
    atomic_json(directory/'status.json',shared)
    try:
        import cv2
    except ImportError:
        shared.update(status='FAILED',error='OpenCV is missing. Use --vision-python with the .venv-cv Python.')
        atomic_json(directory/'status.json',shared);return 1
    source=config['source'];camera=config['source_type']=='CAMERA'
    try:
        if not camera:
            original=Path(source);copied=directory/('source-video'+original.suffix.lower())
            # Copy is performed off the HTTP thread. The copied bytes are replay input.
            with original.open('rb') as src,copied.open('wb') as dst:
                while chunk:=src.read(1024*1024):
                    if (directory/'stop.flag').exists():raise ValueError('Stopped while copying source video')
                    dst.write(chunk)
            copied_hash=sha256(copied)
            if config.get('expected_source_sha256') and copied_hash!=config['expected_source_sha256']:
                raise ValueError('Recording checksum mismatch')
            source=str(copied)
            manifest['artifacts'].append(dict(kind='VIDEO',filename=copied.name,sha256=copied_hash))
            atomic_json(directory/'manifest.json',manifest)
    except (OSError,ValueError) as error:
        shared.update(status='FAILED',error=str(error));atomic_json(directory/'status.json',shared);return 1
    queue=Queue(maxsize=1);stop=threading.Event();finished=threading.Event();lock=threading.Lock()
    detector=None;tracker=None;vision_stream=None;event_stream=None
    if config.get('detection'):
        try:
            from greenwave.vision_detector import YoloLampDetector
            from greenwave.vision_tracking import LampTracker
            detector=YoloLampDetector(config['weights'],directory);tracker=LampTracker()
            manifest['detector']=detector.metadata
            manifest['tracker']=dict(algorithm='MUTUAL_UNAMBIGUOUS_IOU_V1',min_iou=.25,ambiguity_margin=.15,
                min_frames=tracker.min_frames,min_duration=tracker.min_duration,max_gap=tracker.max_gap,lifetime=tracker.lifetime)
            atomic_json(directory/'manifest.json',manifest)
            vision_stream=(directory/'vision.jsonl').open('w',encoding='utf-8')
            event_stream=(directory/'events.jsonl').open('w',encoding='utf-8')
        except Exception as error:
            shared.update(status='FAILED',error='Cannot initialize detector: '+str(error));atomic_json(directory/'status.json',shared);return 1
    offline=not camera and not config['realtime'] and detector is not None
    def update(**fields):
        with lock:shared.update(fields)
    def produce():
        capture=None;writer=None;segment=-1;frame_id=0
        try:
            with (directory/'frames.jsonl').open('w',encoding='utf-8') as journal:
                while not stop.is_set():
                    capture=cv2.VideoCapture(source,cv2.CAP_DSHOW) if camera else cv2.VideoCapture(source)
                    if not capture.isOpened():
                        capture.release();capture=None
                        if not camera:raise ValueError('Cannot decode local video')
                        update(status='RECONNECTING',frame=None,error='Cannot open camera; retrying')
                        stop.wait(1);continue
                    if camera:
                        capture.set(cv2.CAP_PROP_FRAME_WIDTH,config['width']);capture.set(cv2.CAP_PROP_FRAME_HEIGHT,config['height']);capture.set(cv2.CAP_PROP_FPS,config['fps'])
                    segment+=1;segment_index=0
                    source_index=0
                    if not camera and config.get('seek_seconds'):
                        if not capture.set(cv2.CAP_PROP_POS_MSEC,config['seek_seconds']*1000):raise ValueError('Decoder does not support seeking')
                        source_index=max(0,int(capture.get(cv2.CAP_PROP_POS_FRAMES)))
                    fps=capture.get(cv2.CAP_PROP_FPS)
                    if not 1<=fps<=120:fps=config['fps']
                    media=directory/f'camera-segment-{segment}.avi' if camera else Path(source)
                    manifest['segments'].append(dict(segment=segment,media_ref=media.name,fps=fps,frames=0))
                    start=time.monotonic()
                    while not stop.is_set():
                        if (directory/'stop.flag').exists():stop.set();break
                        if config['realtime'] and not camera:
                            stop.wait(max(0.,start+segment_index/fps-time.monotonic()))
                        if stop.is_set():break
                        ok,image=capture.read();monotonic=time.monotonic_ns();utc=datetime.now(timezone.utc).isoformat()
                        if not ok:
                            if not camera and segment_index==0:raise ValueError('Video contains no decodable frames')
                            if camera:
                                update(status='RECONNECTING',frame=None,error='Camera image lost; retrying')
                                with lock:shared['reconnects']+=1
                            else:update(status='DRAINING',frame=None)
                            break
                        height,width=image.shape[:2]
                        if camera and writer is None:
                            writer=cv2.VideoWriter(str(media),cv2.VideoWriter_fourcc(*'MJPG'),fps,(width,height))
                            if not writer.isOpened():raise ValueError('Cannot create camera recording')
                            manifest['artifacts'].append(dict(kind='VIDEO',filename=media.name,encoding='MJPG'))
                        entry=manifest['segments'][-1]
                        if segment_index==0:entry.update(width=width,height=height)
                        if (width,height)!=(entry['width'],entry['height']):raise ValueError('Camera dimensions changed within a segment')
                        if camera:writer.write(image)
                        pts=segment_index/fps if camera else capture.get(cv2.CAP_PROP_POS_MSEC)/1000
                        pts_status='AVAILABLE' if math.isfinite(pts) and pts>=0 else 'UNAVAILABLE'
                        if pts_status=='UNAVAILABLE':pts=None
                        frame=CameraFrameRef(str(config['source']),f"{config['session_id']}:{segment}",frame_id,
                            monotonic,utc,config['clock_uncertainty_seconds'],width,height,str(media),pts)
                        row=dict(frame=frame.to_dict(),segment=segment,encoded_frame_index=source_index+segment_index,
                            pts_kind='ENCODED_CONSTANT_FPS' if camera else 'DECODER_PTS',pts_status=pts_status,
                            clock_quality='HOST_READ_ESTIMATE_NOT_SENSOR_CAPTURE',synchronization_verified=False)
                        journal.write(json.dumps(row)+'\n');journal.flush()
                        with lock:shared.update(status='RUNNING',error=None,frames_captured=frame_id+1,capture_segment=segment)
                        if offline:
                            while not stop.is_set():
                                try:queue.put((image,row),timeout=.1);break
                                except Full:pass
                            dropped=0
                        else:dropped=offer_latest(queue,(image,row))
                        with lock:shared['preview_dropped']+=dropped
                        segment_index+=1;frame_id+=1;entry['frames']=segment_index
                    capture.release();capture=None
                    if writer is not None:writer.release();writer=None
                    if not camera:break
                    if not stop.is_set():stop.wait(1)
            if stop.is_set():update(status='STOPPED',frame=None)
        except Exception as error:
            update(status='FAILED',error=str(error),frame=None)
        finally:
            if capture is not None:capture.release()
            if writer is not None:writer.release()
            finished.set()
    thread=threading.Thread(target=produce,daemon=True);thread.start()
    previews=[];last_preview=0.;last_publish=0.
    try:
        while not finished.is_set() or not queue.empty():
            if (directory/'stop.flag').exists():stop.set()
            try:
                image,row=queue.get(timeout=.1)
                vision=None
                if detector is not None:
                    frame=CameraFrameRef(**row['frame']['data']);started_inference=time.perf_counter()
                    detections=detector.detect(image,frame)
                    # Media time remains authoritative during accelerated replay.
                    clock=frame.captured_monotonic_ns/1e9 if camera else frame.pts_seconds
                    if clock is None:
                        tracker=LampTracker();tracks=[];events=[]
                    else:tracks,events=tracker.update(frame,detections,clock)
                    vision=dict(frame=row['frame'],detections=[d.to_dict() for d in detections],tracks=tracks,events=events,
                        inference_ms=(time.perf_counter()-started_inference)*1000,time_basis='HOST_MONOTONIC' if camera else 'MEDIA_PTS',
                        sampled_rss_mb=detector.process.memory_info().rss/1024**2,
                        host_frame_age_ms=(time.monotonic_ns()-frame.captured_monotonic_ns)/1e6,
                        live_prediction_eligible=False,quality_validated=False)
                    vision_stream.write(json.dumps(vision)+'\n');vision_stream.flush()
                    for event in events:event_stream.write(json.dumps(dict(events=[event]))+'\n')
                    event_stream.flush()
                    with lock:
                        shared['frames_analyzed']=shared.get('frames_analyzed',0)+1
                        shared['events_detected']=shared.get('events_detected',0)+len(events)
                    # Annotate a copy; original recording stays untouched.
                    image=image.copy()
                    for track in tracks:
                        x1,y1,x2,y2=map(int,track['bbox_xyxy'])
                        color={'RED':(0,0,255),'GREEN':(0,255,0),'YELLOW':(0,255,255)}.get(track['state'],(160,160,160))
                        cv2.rectangle(image,(x1,y1),(x2,y2),color,2)
                        cv2.putText(image,f"{track['track_id'].split(':')[-1]} {track['state']} / unassigned",(x1,max(15,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
                if time.monotonic()-last_preview>=.1:
                    ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,75])
                    if not ok:raise ValueError('Cannot encode preview')
                    frame_id=row['frame']['data']['frame_id'];path=directory/f'preview-{frame_id}.jpg'
                    temporary=path.with_suffix('.tmp');temporary.write_bytes(jpeg.tobytes());temporary.replace(path)
                    previews.append(path)
                    if len(previews)>32:previews.pop(0).unlink(missing_ok=True)
                    with lock:
                        if shared['status']=='RUNNING' and shared.get('capture_segment')==row['segment']:shared.update(frame=row['frame'],segment=row['segment'],preview_frame_id=frame_id,vision=vision)
                    last_preview=time.monotonic()
                else:
                    with lock:shared['preview_dropped']+=1
            except Empty:pass
            if time.monotonic()-last_publish>=.2:
                with lock:status=dict(shared)
                atomic_json(directory/'status.json',status);last_publish=time.monotonic()
        thread.join(timeout=1)
        with lock:status=dict(shared)
        if status['status'] in ('RUNNING','DRAINING'):status['status']='ENDED'
        final_status=status['status'];status['status']='FINALIZING';status['frame']=None
        atomic_json(directory/'status.json',status)
        if vision_stream is not None:
            vision_stream.close()
            manifest['artifacts'].append(dict(kind='VISION_TIMELINE',filename='vision.jsonl'))
            event_stream.close();manifest['artifacts'].append(dict(kind='VISION_EVENTS',filename='events.jsonl'))
        for item in manifest['artifacts']:item['sha256']=sha256(directory/item['filename'])
        timeline=directory/'frames.jsonl'
        manifest['artifacts'].append(dict(kind='FRAME_TIMELINE',filename=timeline.name,sha256=sha256(timeline)))
        manifest.update(complete=final_status in ('STOPPED','ENDED'),status=final_status,
            finished_utc=datetime.now(timezone.utc).isoformat(),frames_captured=status['frames_captured'],
            preview_dropped=status['preview_dropped'],reconnects=status['reconnects'],error=status.get('error'))
        manifest.update(frames_analyzed=status.get('frames_analyzed',0),events_detected=status.get('events_detected',0),analysis_mode='ALL_FRAMES' if offline else 'LATEST_FRAME')
        atomic_json(directory/'manifest.json',manifest)
        status['status']=final_status;atomic_json(directory/'status.json',status)
        return 0 if manifest['complete'] else 1
    except Exception as error:
        stop.set();update(status='FAILED',error=str(error),frame=None)
        atomic_json(directory/'status.json',shared);return 1
    finally:
        if vision_stream is not None:vision_stream.close()
        if event_stream is not None:event_stream.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    raise SystemExit(run(parser.parse_args().directory))
