"""Standalone CPU YOLO probe. Optional ML imports occur only when running CLI."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import time
from uuid import uuid4

from greenwave.vision_contracts import CameraFrameRef, VisionDetection


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def class_semantics(name):
    name = str(name).strip().lower().replace('-', '_').replace(' ', '_')
    if 'red_yellow' in name or 'redyellow' in name: state = 'RED_YELLOW'
    elif 'green' in name: state = 'GREEN'
    elif 'yellow' in name or 'amber' in name: state = 'YELLOW'
    elif 'red' in name: state = 'RED'
    elif name == 'off': state = 'OFF'
    else: state = 'UNKNOWN'
    pictogram = ('PEDESTRIAN' if 'pedestrian' in name else
                 'ARROW_LEFT' if 'arrow_left' in name and 'straight' not in name else
                 'ARROW_RIGHT' if 'arrow_right' in name and 'straight' not in name else
                 'ARROW_STRAIGHT' if 'arrow_straight' in name and 'left' not in name else
                 'CIRCLE' if 'circle' in name else 'UNKNOWN')
    return state, pictogram


def make_detection(frame, bbox, score, class_name, model_id, model_hash, index,
                   *, state_score=.5, min_height=12, min_width=4):
    if not math.isfinite(float(score)): raise ValueError('Non-finite model score')
    x1,y1,x2,y2 = map(float,bbox)
    if not all(math.isfinite(value) for value in (x1,y1,x2,y2)):
        raise ValueError('Non-finite bounding box')
    bbox = (max(0.,x1),max(0.,y1),min(float(frame.width),x2),min(float(frame.height),y2))
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]: raise ValueError('Empty clipped bbox')
    state,pictogram = class_semantics(class_name)
    if score < state_score or bbox[3]-bbox[1] < min_height or bbox[2]-bbox[0] < min_width:
        state = 'UNKNOWN'
    return VisionDetection(f'{frame.session_id}:{frame.frame_id}:{index}',frame,bbox,state,
                           float(score),model_id,model_hash,pictogram=pictogram)


def percentile(values, fraction):
    if not values: return None
    ordered=sorted(values); position=(len(ordered)-1)*fraction
    low=math.floor(position); high=math.ceil(position)
    return ordered[low]+(ordered[high]-ordered[low])*(position-low)


def evaluate_boxes(detections, labels, min_iou=.5):
    def iou(a,b):
        intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
        union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
        return intersection/union if union>0 else 0
    candidates=sorted([(iou(d['data']['bbox_xyxy'],label['bbox_xyxy']),i,j)
        for i,d in enumerate(detections) for j,label in enumerate(labels)],reverse=True)
    used_d=set();used_l=set();pairs=[]
    for overlap,i,j in candidates:
        if overlap<min_iou:break
        if i in used_d or j in used_l:continue
        used_d.add(i);used_l.add(j)
        pairs.append(dict(iou=overlap,expected=labels[j]['state'],predicted=detections[i]['data']['state']))
    return dict(labels=len(labels),predictions=len(detections),matched=len(pairs),
        missed=len(labels)-len(used_l),unmatched_predictions=len(detections)-len(used_d),
        correct_states=sum(p['expected']==p['predicted'] for p in pairs),
        false_green_matched=sum(p['predicted']=='GREEN' and p['expected']!='GREEN' for p in pairs),
        pairs=pairs,note='Single-image smoke comparison; not held-out accuracy or calibrated false-green rate.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights',type=Path,required=True)
    parser.add_argument('--source',required=True,help='Image, video or camera:0')
    parser.add_argument('--output',type=Path,default=Path('data/derived/vision-probe'))
    parser.add_argument('--imgsz',type=int,default=640)
    parser.add_argument('--repeat',type=int,default=10,help='Measured repeats for a still image')
    parser.add_argument('--max-frames',type=int,default=60)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--labels',type=Path,help='Optional single-image JSON labels: [{bbox_xyxy:[...],state:...}]')
    parser.add_argument('--detection-score',type=float,default=.25)
    parser.add_argument('--state-score',type=float,default=.5)
    parser.add_argument('--min-height',type=int,default=12)
    parser.add_argument('--min-width',type=int,default=4)
    parser.add_argument('--clock-uncertainty',type=float,default=1.0,
                        help='Assumed host dequeue clock uncertainty, not measured sensor latency')
    args=parser.parse_args(argv)
    if not args.weights.is_file(): parser.error('Weights must be an existing local file')
    if min(args.imgsz,args.repeat,args.max_frames,args.threads,args.min_height,args.min_width)<=0:
        parser.error('Sizes, counts and threads must be positive')
    if not (0<=args.detection_score<=1 and 0<=args.state_score<=1 and
            math.isfinite(args.clock_uncertainty) and args.clock_uncertainty>=0):
        parser.error('Invalid thresholds or clock uncertainty')
    config_dir = args.output.resolve() / '.ultralytics'
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ['YOLO_CONFIG_DIR'] = str(config_dir)
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    try:
        import cv2
        import torch
        import ultralytics
        import psutil
    except ImportError as error:
        parser.error(f'Missing CV dependency: {error}. Install requirements-vision.txt in .venv-cv.')
    ultralytics.settings.update({'sync': False, 'hub': False})
    from ultralytics import YOLO
    torch.set_num_threads(args.threads)
    session=uuid4().hex; output=args.output/session;output.mkdir(parents=True,exist_ok=False)
    model_hash=file_sha256(args.weights)
    model=YOLO(str(args.weights))
    supported_states=sorted({class_semantics(name)[0] for name in model.names.values()})
    still = not args.source.startswith('camera:') and Path(args.source).suffix.lower() in {'.jpg','.jpeg','.png','.bmp'}
    if args.labels and not still:parser.error('Labels in this probe apply only to a still image')
    labels=None if args.labels is None else json.loads(args.labels.read_text(encoding='utf-8'))
    camera=args.source.startswith('camera:')
    capture=None
    image=cv2.imread(args.source) if still else None
    if still and image is None: raise ValueError('Cannot read image')
    if not still:
        capture=cv2.VideoCapture(int(args.source.split(':',1)[1]) if camera else args.source)
        if not capture.isOpened(): raise ValueError('Cannot open source')
    latencies=[]; ages=[]; memory=[]; counts=Counter();detected=[]
    process=psutil.Process();warmup=False;index=0; quality=None
    source_sha=None if camera else file_sha256(args.source)
    try:
        with (output/'detections.jsonl').open('w',encoding='utf-8') as stream:
            while index < (args.repeat if still else args.max_frames):
                ok,current=(True,image) if still else capture.read()
                if not ok: break
                captured=time.monotonic_ns(); utc=datetime.now(timezone.utc).isoformat()
                if not warmup:
                    model.predict(current,imgsz=args.imgsz,device='cpu',verbose=False,conf=args.detection_score)
                    warmup=True
                    # Warmup time is not part of this frame's measured latency.
                    captured=time.monotonic_ns();utc=datetime.now(timezone.utc).isoformat()
                pts=None if still or camera else max(0.,capture.get(cv2.CAP_PROP_POS_MSEC)/1000)
                frame=CameraFrameRef(args.source,session,index,captured,utc,args.clock_uncertainty,
                    current.shape[1],current.shape[0],None if camera else str(Path(args.source).resolve()),pts)
                start=time.perf_counter()
                result=model.predict(current,imgsz=args.imgsz,device='cpu',verbose=False,conf=args.detection_score)[0]
                latencies.append((time.perf_counter()-start)*1000)
                rows=[]; raw_outputs=[]
                if result.boxes is not None:
                    for number,box in enumerate(result.boxes):
                        class_name=result.names[int(box.cls.item())]
                        detection=make_detection(frame,box.xyxy[0].tolist(),box.conf.item(),class_name,
                            args.weights.name,model_hash,number,state_score=args.state_score,
                            min_height=args.min_height,min_width=args.min_width)
                        counts[detection.state]+=1;rows.append(detection.to_dict())
                        raw_outputs.append(dict(detection_id=detection.detection_id,
                            class_name=class_name,raw_state=class_semantics(class_name)[0],
                            filtered_state=detection.state,model_score=detection.model_score))
                age=(time.monotonic_ns()-captured)/1e6;ages.append(age)
                memory.append(process.memory_info().rss/1024**2);detected.append(len(rows))
                stream.write(json.dumps(dict(frame=frame.to_dict(),detections=rows,raw_model_outputs=raw_outputs,
                    inference_ms=latencies[-1],host_frame_age_ms=age,live_prediction_eligible=False))+'\n')
                if index==0:
                    if labels is not None:quality=evaluate_boxes(rows,labels)
                    annotated=current.copy()
                    for row in rows:
                        data=row['data'];x1,y1,x2,y2=map(int,data['bbox_xyxy'])
                        color={'RED':(0,0,255),'GREEN':(0,255,0),'YELLOW':(0,255,255)}.get(data['state'],(180,180,180))
                        cv2.rectangle(annotated,(x1,y1),(x2,y2),color,2)
                        cv2.putText(annotated,f"{data['state']} {data['model_score']:.2f}",
                            (x1,max(15,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
                    cv2.imwrite(str(output/'annotated-first.jpg'),annotated)
                index+=1
    finally:
        if capture is not None:capture.release()
    mean_latency = sum(latencies) / len(latencies) if latencies else 0
    report=dict(schema_version=1,session_id=session,frames=index,source=args.source,source_sha256=source_sha,
        labels_sha256=None if args.labels is None else file_sha256(args.labels),
        model=dict(path=str(args.weights.resolve()),sha256=model_hash,classes=model.names,
                   supported_states=supported_states,
                   missing_states=sorted({'RED','GREEN','YELLOW','RED_YELLOW','OFF'}-set(supported_states))),
        environment=dict(python=platform.python_version(),runtime_arch=platform.machine(),
            torch=torch.__version__,ultralytics=ultralytics.__version__,opencv=cv2.__version__,
            device='cpu',threads=args.threads),configuration=vars(args),
        inference_ms=dict(p50=percentile(latencies,.5),p95=percentile(latencies,.95),maximum=max(latencies,default=None)),
        inference_fps=1000/mean_latency if mean_latency else None,
        host_frame_age_ms=dict(p50=percentile(ages,.5),p95=percentile(ages,.95)),
        peak_sampled_rss_mb=max(memory,default=None),detected_per_frame=detected,state_counts=dict(counts),
        warmup_excluded=True,live_prediction_eligible=False,
        clock_quality='HOST_DEQUEUE_ESTIMATE_NOT_ORIGINAL_VIDEO_CAPTURE',
        quality_validated=False,smoke_comparison=quality,
        note='Repeated still images measure speed, not independent accuracy. Thresholds are provisional. No tracking or point assignment.')
    (output/'report.json').write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(output.resolve()),frames=index,inference_ms=report['inference_ms'],
                         state_counts=dict(counts)),indent=2))
    return 0 if index else 2


if __name__=='__main__':
    raise SystemExit(main())
