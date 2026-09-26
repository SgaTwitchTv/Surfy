"""Synthetic UI scenarios; no camera, model, GPS or phase-engine mutations."""
from dataclasses import replace
from greenwave.vision_contracts import CameraFrameRef, VisionDetection, VisionTrack, SignalAssociation, VisionObservation


def vision_demo(name):
    names=('no_camera','good_detection','multiple_lamps','unknown_color','conflict',
           'lost_image','stale_gps','wrong_direction','phone_disconnected')
    if name not in names: raise ValueError('Unknown vision demo')
    frame=CameraFrameRef('demo-camera','demo-session',1,1_000_000_000,
                         '2026-09-26T12:00:00+00:00',.05,1920,1080)
    detection=VisionDetection('demo-detection',frame,(800,200,840,300),'GREEN',.9,
                              'synthetic-not-a-trained-model','0'*64,track_id='demo-track')
    association=SignalAssociation('demo-session','demo-track','CANDIDATE','GPS_PROPOSAL',
        route_id='demo-route',geometry_hash='1'*64,stop_line_id='demo-line',direction='FORWARD',
        movement='STRAIGHT',display_name='Przykładowa / Testowa',
        stop_line_latitude=52.0,stop_line_longitude=21.0,candidate_line_ids=('demo-line',))
    detections=[detection]; tracks=[VisionTrack('demo-track',detection,detection)]
    associations=[association]
    if name=='good_detection': associations=[replace(association,status='CONFIRMED',method='MANUAL')]
    if name=='unknown_color':
        detection=replace(detection,state='UNKNOWN',model_score=.3)
        detections=[detection];tracks=[VisionTrack('demo-track',detection,detection)]
    if name in ('multiple_lamps','conflict'):
        second=replace(detection,detection_id='demo-detection-2',track_id='demo-track-2',
                       bbox_xyxy=(1100,210,1140,310),state='RED' if name=='conflict' else 'GREEN')
        detections.append(second);tracks.append(VisionTrack('demo-track-2',second,second))
        associations.append(replace(association,track_id='demo-track-2'))
        if name=='conflict': associations=[replace(a,status='CONFLICT') for a in associations]
    if name in ('lost_image','no_camera'): detections=[];associations=[]
    if name=='no_camera':tracks=[]
    if name=='lost_image':tracks=[replace(track,visibility='LOST') for track in tracks]
    if name=='wrong_direction': associations=[replace(association,status='UNASSIGNED',method='NONE',
        stop_line_id=None,direction='REVERSE',candidate_line_ids=())]
    observations=[VisionObservation('demo-observation-'+str(i),d,a).to_dict()
                  for i,(d,a) in enumerate(zip(detections,associations))]
    return dict(schema_version=1,synthetic=True,scenario=name,
        camera_status='DISCONNECTED' if name in ('no_camera','lost_image') else 'CONNECTED',
        gps_status='STALE' if name=='stale_gps' else 'FRESH',
        phone_status='DISCONNECTED' if name=='phone_disconnected' else 'CONNECTED',
        detections=[d.to_dict() for d in detections],tracks=[t.to_dict() for t in tracks],
        associations=[a.to_dict() for a in associations],observations=observations,
        live_prediction_eligible=False)


def all_vision_demos():
    return [vision_demo(name) for name in ('no_camera','good_detection','multiple_lamps',
        'unknown_color','conflict','lost_image','stale_gps','wrong_direction','phone_disconnected')]


if __name__ == '__main__':
    import json
    print(json.dumps(all_vision_demos(), ensure_ascii=False, indent=2))
