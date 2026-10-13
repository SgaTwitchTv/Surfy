"""Operators/test-only synthetic fixture; never an HTTP provisioning route."""
import argparse
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import json
from greenwave.school_data import Actor, Database, Repository, Storage
from greenwave.school_accounts.crypto import Passwords
from greenwave.telemetry import RunLogger
from greenwave.vision_contracts import CameraFrameRef, VisionDetection, SignalAssociation, VisionObservation


def populate(repo, password_hash):
    with repo.database.connection() as c:
        if c.execute('SELECT 1 FROM users LIMIT 1').fetchone(): raise ValueError('Fixture requires an EMPTY synthetic database')
    users = {}
    for name, role in [('driver','DRIVER'),('other','DRIVER'),('analyst','ANALYST'),('admin','ADMIN')]:
        users[name] = repo.create_user(name+'@example.test', name, password_hash, role=role,
                                     status='ACTIVE', verified_at=repo.clock())
    trips, observations, captures = {}, {}, {}
    storage = repo.database.storage
    for label, who in [('shared','driver'),('private','driver'),('other','other'),('analyst','analyst'),('admin','admin')]:
        actor = Actor(users[who]['id'])
        trip = repo.create_trip(actor, 'Synthetic '+label)
        logger = RunLogger(storage.trip(actor.user_id, trip['id'])/'runs')
        now = datetime(2026,10,13,tzinfo=timezone.utc)
        logger.start({'start_time':now,'corridor_id':'synthetic','timebase':'LIVE','dataset':'SYNTHETIC'})
        logger.append('RUN_START',timestamp=now,simulation_seconds=0,model_seconds=0)
        for index in range(3):
            logger.append('EXTERNAL_TELEMETRY',timestamp=now+timedelta(seconds=index),simulation_seconds=0,
                model_seconds=index,source='ANDROID_FUSED',latitude=52+index*.00001,longitude=21,
                speed_mps=1,gps_accuracy=4,payload={'phone_timestamp_seconds':100+index,
                'device_id':'synthetic-phone','stream_id':'synthetic-stream','sample_sequence':index,
                'elapsed_realtime_nanos':(10+index)*1000000000,'usable_for_live':False})
        logger.finish('SYNTHETIC',timestamp=now+timedelta(seconds=3),simulation_seconds=0,model_seconds=3)
        root = storage.run(actor.user_id,trip['id'],logger.run_id)
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        for status in ['STARTING','RECORDING','FINALIZING','COMPLETE']:
            kwargs = {'run_id':logger.run_id} if status=='STARTING' else {}
            if status=='COMPLETE': kwargs={'raw_ref':(root/'raw.csv').relative_to(storage.root).as_posix(),
                'raw_hash':sha(root/'raw.csv'),'manifest_hash':sha(root/'complete.json')}
            trip=repo.transition_trip(actor,trip['id'],trip['revision'],status,**kwargs)
        trips[label]=trip
        obs=repo.add_observation(actor,trip['id'],'synthetic-light','RED','STATE_SEEN','event-'+label)
        repo.correct_observation(actor,obs['id'],0,{'state':'GREEN','event_type':'STATE_SEEN','valid':True},'Synthetic correction',repo.new_id())
        observations[label]=obs
        cid=repo.new_id();captures[label]=cid
        cv=storage.cv(actor.user_id,trip['id'],cid);cv.mkdir(parents=True)
        (cv/'video.avi').write_bytes(b'SYNTHETIC VIDEO FIXTURE - NOT CAMERA DATA')
        frame=CameraFrameRef('synthetic-camera',cid+':0',0,1,now.isoformat(),.1,640,480,'private-source-path',0)
        detection=VisionDetection('synthetic-detection',frame,(1.,1.,10.,20.),'RED',.9,'synthetic-model','b'*64,track_id='lamp')
        association=SignalAssociation(frame.session_id,'lamp','UNASSIGNED','NONE')
        event=VisionObservation('synthetic-observation',detection,association)
        (cv/'events.jsonl').write_text(json.dumps({'events':[{'observation':event.to_dict()}]})+'\n',encoding='utf-8')
        manifest={'schema_version':1,'session_id':cid,'run_id':trip['run_id'],'complete':True,'status':'ENDED',
                  'frames_captured':1,'configuration':{'source':'private-source-path'},'artifacts':[
                  {'kind':'VIDEO','filename':'video.avi','sha256':sha(cv/'video.avi')},
                  {'kind':'VISION_EVENTS','filename':'events.jsonl','sha256':sha(cv/'events.jsonl')}]}
        (cv/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    share=repo.share_trip(Actor(users['driver']['id']),trips['shared']['id'],'analyst@example.test')
    draft=repo.create_config(Actor(users['analyst']['id']),'MODEL','synthetic',{'diagnostic_only':True})
    published=repo.create_config(Actor(users['admin']['id']),'MODEL','synthetic-public',{'diagnostic_only':True})
    published=repo.publish_config(Actor(users['admin']['id'],repo.clock()),published['id'],published['revision'])
    return {'users':users,'trips':trips,'observations':observations,'captures':captures,'share':share,
            'draft':draft,'published':published}


def main():
    parser=argparse.ArgumentParser(description='EMPTY synthetic database only, server stopped; example.test')
    parser.add_argument('--root',required=True);parser.add_argument('--confirm-synthetic',action='store_true',required=True)
    args=parser.parse_args();password=getpass.getpass('Synthetic fixture password (all four accounts): ')
    confirmation=getpass.getpass('Confirm: ')
    if password != confirmation: parser.error('Passwords differ')
    hashed=Passwords().hash(password)
    with Database(Storage(args.root)) as db:
        fixture=populate(Repository(db),hashed)
        print(json.dumps({'accounts':[name+'@example.test' for name in fixture['users']],
                          'trips':{k:v['id'] for k,v in fixture['trips'].items()},
                          'observations':{k:v['id'] for k,v in fixture['observations'].items()},
                          'captures':fixture['captures']}))


if __name__=='__main__':main()
