"""Offline annotated-frame evaluation. A smoke run cannot accept road quality."""
import argparse
import json
from pathlib import Path
from greenwave.vision_tracking import iou
from greenwave.vision_probe import file_sha256,percentile


def evaluate(rows,labels,source_hash):
    if labels.get('source_sha256')!=source_hash:raise ValueError('Labels belong to a different video')
    if labels.get('split') not in ('TUNING','ACCEPTANCE'):raise ValueError('Choose TUNING or ACCEPTANCE')
    if labels['split']=='ACCEPTANCE' and source_hash in labels.get('tuning_source_sha256',[]):raise ValueError('Tuning video cannot be acceptance data')
    frames={row['frame']['data']['frame_id']:row for row in rows};identities={};switches=0
    total=matched=missed=extra=correct=false_green=false_green_unmatched=unknown=0;assignment_cases=wrong_line=unassigned=0
    used_frames=set()
    for label in sorted(labels.get('frames',[]),key=lambda item:item['frame_id']):
        frame_id=label['frame_id']
        if frame_id in used_frames:raise ValueError('Duplicate labeled frame')
        used_frames.add(frame_id)
        if frame_id not in frames:raise ValueError('Labeled frame not analyzed')
        truth=label['lamps'];tracks=frames[frame_id]['tracks'];total+=len(truth)
        candidates=sorted([(iou(t['bbox_xyxy'],p['bbox_xyxy']),i,j) for i,t in enumerate(truth) for j,p in enumerate(tracks)],reverse=True)
        seen_truth=set();seen_pred=set()
        for overlap,i,j in candidates:
            if overlap<.5:break
            if i in seen_truth or j in seen_pred:continue
            seen_truth.add(i);seen_pred.add(j);matched+=1;t=truth[i];p=tracks[j]
            correct+=p['state']==t['state'];false_green+=p['state']=='GREEN' and t['state']!='GREEN';unknown+=p['state']=='UNKNOWN'
            key=(frames[frame_id]['frame']['data'].get('session_id'),t['lamp_id']) if t.get('lamp_id') is not None else None
            if key is not None:
                if key in identities and identities[key]!=p['track_id']:switches+=1
                identities[key]=p['track_id']
            if t.get('stop_line_id'):
                assignment_cases+=1
                if not p.get('stop_line_id'):unassigned+=1
                elif p['stop_line_id']!=t['stop_line_id']:wrong_line+=1
        missed+=len(truth)-len(seen_truth);extra+=len(tracks)-len(seen_pred)
        false_green_unmatched+=sum(p['state']=='GREEN' for j,p in enumerate(tracks) if j not in seen_pred)
    timing=[];transition_missing=0
    events=[event for row in rows for event in row.get('events',[]) if event['observation']['data']['event_type']=='STATE_START']
    used_events=set()
    for truth in labels.get('transitions',[]):
        candidates=[(index,event) for index,event in enumerate(events) if index not in used_events and event['observation']['data']['detection']['track_id']==truth['track_id'] and event['observation']['data']['detection']['state']==truth['state'] and event.get('interval_seconds')]
        if not candidates:transition_missing+=1;continue
        index,event=min(candidates,key=lambda candidate:abs(candidate[1]['interval_seconds'][1]-truth['interval_seconds'][1]))
        used_events.add(index);interval=event['interval_seconds']
        timing.append(max(abs(interval[i]-truth['interval_seconds'][i]) for i in (0,1)))
    latency=[row['inference_ms'] for row in rows if 'inference_ms' in row]
    return dict(split=labels['split'],source_sha256=source_hash,labeled_frames=len(used_frames),expected_lamps=total,
        matched=matched,missed=missed,unmatched_predictions=extra,correct_states=correct,false_green_matched=false_green,
        green_without_matching_label=false_green_unmatched,unknown_matched=unknown,track_switches=switches,
        assignment_cases=assignment_cases,wrong_line=wrong_line,unassigned=unassigned,
        transition_cases=len(labels.get('transitions',[])),transition_missing=transition_missing,
        transition_interval_error_seconds=dict(p95=percentile(timing,.95),maximum=max(timing,default=None)),
        inference_ms=dict(p50=percentile(latency,.5),p95=percentile(latency,.95)),
        host_frame_age_ms_p95=percentile([row['host_frame_age_ms'] for row in rows if 'host_frame_age_ms' in row],.95),
        peak_sampled_rss_mb=max((row['sampled_rss_mb'] for row in rows if 'sampled_rss_mb' in row),default=None),
        road_quality_accepted=False,note='Metrics on labeled frames only; coverage, labels and thresholds require human acceptance.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--labels',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    manifest=json.loads((args.capture/'manifest.json').read_text(encoding='utf-8'))
    if not manifest.get('complete'):parser.error('Capture must be complete')
    videos=[a for a in manifest['artifacts'] if a['kind']=='VIDEO']
    if len(videos)!=1:parser.error('Evaluate one video segment per labeled dataset')
    video=args.capture/videos[0]['filename'];source_hash=file_sha256(video)
    if source_hash!=videos[0]['sha256']:parser.error('Video checksum mismatch')
    rows=[json.loads(line) for line in (args.capture/'vision.jsonl').read_text(encoding='utf-8').splitlines()]
    report=evaluate(rows,json.loads(args.labels.read_text(encoding='utf-8')),source_hash)
    report.update(labels_sha256=file_sha256(args.labels),detector=manifest.get('detector'),tracker=manifest.get('tracker'))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
