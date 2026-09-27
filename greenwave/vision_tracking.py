"""Conservative experimental IoU tracking; no route or prediction side effects."""
from dataclasses import replace
import math
from greenwave.vision_contracts import SignalAssociation, VisionObservation


def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union else 0


class LampTracker:
    def __init__(self, min_frames=3, min_duration=.15, max_gap=.5, lifetime=1.5):
        self.min_frames=min_frames;self.min_duration=min_duration;self.max_gap=max_gap;self.lifetime=lifetime
        self.tracks={};self.session=None;self.counter=0;self.last_time=None;self.last_frame=None

    def update(self, frame, detections, timestamp):
        if not math.isfinite(timestamp):raise ValueError('Invalid tracking clock')
        if any(d.frame!=frame for d in detections):raise ValueError('Detection frame mismatch')
        if self.session!=frame.session_id or (self.last_time is not None and (timestamp<=self.last_time or frame.frame_id<=self.last_frame)):
            self.tracks={}
        self.session=frame.session_id;self.last_time=timestamp;self.last_frame=frame.frame_id
        self.tracks={k:t for k,t in self.tracks.items() if timestamp-t['time']<=self.lifetime}
        # Mutual unique match. Close competitors invalidate identity rather than
        # silently swapping tracks at crossings or duplicate boxes.
        scores={(k,j):iou(t['latest'].bbox_xyxy,d.bbox_xyxy) for k,t in self.tracks.items() for j,d in enumerate(detections)
                if t['latest'].pictogram==d.pictogram}
        proposals={}
        for j in range(len(detections)):
            ranked=sorted([(score,k) for (k,n),score in scores.items() if n==j and score>=.25],reverse=True)
            if not ranked:continue
            score,k=ranked[0]
            competitors=sorted([v for (track,n),v in scores.items() if track==k and n!=j and v>=.25],reverse=True)
            if (len(ranked)>1 and score-ranked[1][0]<.15) or (competitors and score-competitors[0]<.15):continue
            proposals[j]=k
        used=set(proposals.values());output=[];events=[]
        for k,t in self.tracks.items():
            if k not in used:t.update(stable='UNKNOWN',candidate=None,count=0,previous=None,visibility='OCCLUDED')
        for j,detection in enumerate(detections):
            k=proposals.get(j)
            if k is None:
                self.counter+=1;k=f'{self.session}:lamp-{self.counter}'
                self.tracks[k]=dict(stable='UNKNOWN',candidate=None,count=0,previous=None,time=timestamp,latest=detection,visibility='VISIBLE')
            t=self.tracks[k];d=replace(detection,track_id=k)
            if timestamp-t['time']>self.max_gap:t.update(stable='UNKNOWN',candidate=None,count=0,previous=None)
            t.update(latest=d,time=timestamp,visibility='VISIBLE')
            if d.state in ('UNKNOWN','OFF'):
                t.update(stable='UNKNOWN',candidate=None,count=0,previous=None)
            elif d.state==t['stable']:
                t.update(previous=d,candidate=None,count=0)
            else:
                if t['candidate']!=d.state:t.update(candidate=d.state,count=0,first=d,start=timestamp)
                t['count']+=1
                if t['count']>=self.min_frames and timestamp-t['start']>=self.min_duration:
                    previous=t['previous'];first=t['first']
                    transition=previous is not None and t['stable']!='UNKNOWN'
                    association=SignalAssociation(frame.session_id,k,'UNASSIGNED','NONE')
                    observation=VisionObservation(f'{k}:{first.frame.frame_id}:{d.state}',first,association,
                        'STATE_START' if transition else 'STATE_SEEN',previous if transition else None,transition)
                    events.append(dict(observation=observation.to_dict(),time_basis='TRACKING_CLOCK',
                        interval_seconds=[t.get('previous_time'),t['start']] if transition else None,
                        live_prediction_eligible=False))
                    t.update(stable=d.state,previous=d,candidate=None,count=0)
            if t.get('previous') is d:t['previous_time']=timestamp
            output.append(dict(track_id=k,bbox_xyxy=d.bbox_xyxy,state=t['stable'] if d.state==t['stable'] else 'UNKNOWN',
                raw_state=d.state,model_score=d.model_score,pictogram=d.pictogram,visibility='VISIBLE',assigned=False))
        return output,events
