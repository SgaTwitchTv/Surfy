import dataclasses
import json
import threading
import unittest
from unittest.mock import patch
from test_school_records import RecordsTests
from test_school_accounts import PREFIX


class NavigationTests(RecordsTests):
    # Reuse only fixture helpers, not inherited test methods (loader below).
    def setUp(self):
        super().setUp()
        self.rec=self.server.resources.recorder

    def test_engine_pause_resume_config_finish_simulation_replay(self):
        trip=self.new_trip();nav=self.start(trip)
        self.assertEqual(nav['dataset'],'synthetic_s1_s5')
        self.assertTrue(nav['synthetic']);self.assertTrue(nav['running'])
        self.assertIsNone(nav['live_recommendation'])
        status,data,_=self.post('/navigation/'+nav['id']+'/control',{'command':'PAUSE','expected_revision':nav['control_revision']})
        self.assertEqual(status,200,data);self.assertFalse(data['data']['running'])
        rev=data['data']['control_revision']
        status,data,_=self.request('PATCH',PREFIX+'/navigation/'+nav['id']+'/simulation',{'rate':10,'expected_revision':rev})
        self.assertEqual(status,200,data);self.assertEqual(data['data']['rate'],10)
        self.assertEqual(self.post('/navigation/'+nav['id']+'/control',{'command':'RESUME','expected_revision':rev+1})[0],200)
        self.assertEqual(self.finish(nav)[0],200)
        self.assertEqual(self.get('/navigation/'+nav['id'])[0],409)
        self.assertEqual(self.get('/trips/'+trip['id']+'/export')[0],200)
        status,data,_=self.post('/trips/'+trip['id']+'/replays',{'mode':'SIMULATION'})
        self.assertEqual(status,201,data);hid=data['data']['id']
        self.assertEqual(self.post('/replays/'+hid+'/control',{'command':'RATE','value':10})[0],200)
        self.assertIsNone(self.get('/replays/'+hid)[1]['data']['live_recommendation'])

    def real_proxy(self):
        # Real HTTPS edge modeled as an explicitly trusted local reverse proxy.
        # HTTP fixture supplies X-Forwarded-Proto; production never disables HTTPS.
        self.cfg=dataclasses.replace(self.cfg,profile='real',base_url=self.cfg.base_url.replace('http:','https:'),smtp_mode='starttls',trusted_proxy='127.0.0.1')
        self.cfg.validate();self.service.config=self.cfg
        original=self.request
        def request(method,path,body=None,headers=None):
            return original(method,path,body,{'X-Forwarded-Proto':'https',**(headers or {})})
        self.request=request

    def test_demo_devices_and_foreign_navigation_denied(self):
        self.assertEqual(self.post('/pairing-challenges',{'label':'Phone'})[0],403)
        nav=self.start(self.new_trip())
        for who in ['other','analyst','admin']:
            self.use(who);self.assertEqual(self.get('/navigation/'+nav['id'])[0],404)
        self.use(None);self.assertEqual(self.get('/navigation/'+nav['id'])[0],401)

    def pair(self):
        status,data,_=self.post('/pairing-challenges',{'label':'Synthetic phone'})
        self.assertEqual(status,201,data)
        request={'code':data['data']['code'],'client_device_id':'synthetic-phone','label':'Synthetic phone'}
        status,data,_=self.request('POST',PREFIX+'/device/pair',request,{'Origin':'','X-CSRF-Token':''})
        self.assertEqual(status,200,data)
        return data['data'],request

    def test_pair_one_use_parent_ttl_and_revoke(self):
        self.real_proxy();device,request=self.pair()
        self.assertEqual(self.request('POST',PREFIX+'/device/pair',request)[0],403)
        header={'Authorization':'Bearer '+device['device_token']}
        self.assertEqual(self.request('GET',PREFIX+'/device/session',headers=header)[0],200)
        self.assertEqual(self.request('GET',PREFIX+'/trips',headers={'Cookie':'',**header})[0],401)
        with self.db.connection() as c:
            d=c.execute('SELECT * FROM devices WHERE id=?',(device['device_id'],)).fetchone()
            parent=c.execute('SELECT * FROM browser_sessions WHERE id=?',(d['parent_session_id'],)).fetchone()
            self.assertLessEqual(d['expiry'],parent['absolute_expiry']);self.assertNotEqual(d['token_hash'],device['device_token'])
        self.use('driver')
        self.assertEqual(self.request('DELETE',PREFIX+'/devices/'+device['device_id'],{'reason':'Synthetic revoke'})[0],204)
        self.assertEqual(self.request('GET',PREFIX+'/device/session',headers=header)[0],403)

    def test_live_missing_sample_never_fabricates_speed_or_recommendation(self):
        self.real_proxy();device,_=self.pair()
        from greenwave.school_data import Actor
        import pathlib
        route=json.loads(pathlib.Path('data/routes/zwirki_wigury_draft.json').read_text(encoding='utf-8'))
        cfg=self.repo.create_config(Actor(self.users['admin']['id']),'ROUTE','synthetic-live-test',route)
        cfg=self.repo.publish_config(Actor(self.users['admin']['id'],self.now),cfg['id'],cfg['revision'])
        status,data,_=self.post('/trips',{'title':'Synthetic GPS transport test','mode':'LIVE','route_version_id':cfg['id']})
        self.assertEqual(status,201,data)
        status,data,_=self.request('POST',PREFIX+'/navigation',{'trip_id':data['data']['id'],'device_id':device['device_id']},{'Idempotency-Key':'L'*32})
        self.assertEqual(status,201,data);nav=data['data'];self.assertIsNone(nav['speed_mps']);self.assertIsNone(nav['live_recommendation'])
        self.assertFalse(nav['eligibility']['allowed'])
        self.assertEqual(self.finish(nav)[0],200)

    def test_live_ingest_dedupe_validation_logout_and_missing_speed(self):
        self.real_proxy();device,_=self.pair()
        from greenwave.school_data import Actor
        from pathlib import Path
        route=json.loads(Path('data/routes/zwirki_wigury_draft.json').read_text(encoding='utf-8'))
        cfg=self.repo.create_config(Actor(self.users['admin']['id']),'ROUTE','gps-transport-test',route)
        cfg=self.repo.publish_config(Actor(self.users['admin']['id'],self.now),cfg['id'],cfg['revision'])
        trip=self.post('/trips',{'title':'Synthetic location','mode':'LIVE','route_version_id':cfg['id']})[1]['data']
        nav=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id'],'device_id':device['device_id']},{'Idempotency-Key':'G'*32})[1]['data']
        point=route['coordinates'][0]
        payload={'session_id':nav['id'],'timestamp_seconds':self.now/1000,'latitude':point[1],'longitude':point[0],
            'gps_accuracy_m':5,'speed_mps':None,'speed_accuracy_mps':None,'heading_deg':None,'heading_accuracy_deg':None,
            'altitude_m':None,'vertical_accuracy_m':None,'is_mock':False,'source':'ANDROID_FUSED','device_id':'synthetic-phone',
            'stream_id':'synthetic-stream','sample_sequence':1,'elapsed_realtime_nanos':1000000000,'sent_elapsed_realtime_nanos':1000000000}
        header={'Authorization':'Bearer '+device['device_token'],'Origin':'','X-CSRF-Token':''}
        status,data,_=self.request('POST',PREFIX+'/device/position',payload,header)
        self.assertEqual(status,200,data);self.assertTrue(data['data']['accepted'])
        self.assertTrue(self.request('POST',PREFIX+'/device/position',payload,header)[1]['data']['duplicate'])
        self.assertEqual(self.request('POST',PREFIX+'/device/position',{**payload,'sample_sequence':True},header)[0],422)
        self.assertEqual(self.request('POST',PREFIX+'/device/position',{**payload,'session_id':'0'*32},header)[0],409)
        self.assertEqual(self.request('POST',PREFIX+'/device/position',{**payload,'owner_id':self.users['admin']['id']},header)[0],422)
        state=self.get('/navigation/'+nav['id'])[1]['data'];self.assertIsNone(state['live_recommendation']);self.assertIsNone(state['speed_mps'])
        self.assertEqual(self.auth('logout',{})[0],204)
        self.assertEqual(self.request('GET',PREFIX+'/device/session',headers=header)[0],403)
        self.assertEqual(self.request('POST',PREFIX+'/device/position',payload,header)[0],403)
        with self.db.connection() as c:self.assertEqual(c.execute('SELECT status FROM trips WHERE id=?',(trip['id'],)).fetchone()[0],'COMPLETE')

    def test_cv_review_is_separate_owner_only_and_idempotent(self):
        body={'event_id':self.fixture['vision_event_id'] if 'vision_event_id' in self.fixture else 'missing','status':'REJECTED','reason':'Synthetic review','expected_revision':0,'client_operation_id':'C'*32}
        events=self.get('/trips/'+self.tid+'/cv/captures/'+self.fixture['captures']['shared']+'/events')[1]['data']['items']
        body['event_id']=events[0]['id']
        path='/trips/'+self.tid+'/cv/captures/'+self.fixture['captures']['shared']+'/reviews'
        status,data,_=self.post(path,body);self.assertEqual(status,201,data)
        self.assertFalse(data['data']['live_prediction_eligible'])
        self.assertEqual(self.post(path,body)[1]['data'],data['data'])
        self.assertEqual(self.post(path,{**body,'reason':'Different payload'})[0],409)
        for who in ['other','analyst','admin']:
            self.use(who);self.assertEqual(self.post(path,body)[0],404)


    def test_pause_retains_sql_slot_and_failed_start_retry_stays_failed(self):
        trip=self.new_trip();nav=self.start(trip)
        self.assertEqual(self.post('/navigation/'+nav['id']+'/control',{'command':'PAUSE','expected_revision':0})[0],200)
        self.use('other');other=self.new_trip()
        self.assertEqual(self.request('POST',PREFIX+'/navigation',{'trip_id':other['id']},{'Idempotency-Key':'B'*32})[0],409)
        self.use('driver');self.assertEqual(self.finish(nav)[0],200)
        self.rec.reconcile_credentials()
        self.assertEqual(self.finish(nav)[0],200)
        self.use('other');self.start(other,key='B'*32)

    def test_simulation_validation_and_csrf(self):
        nav=self.start(self.new_trip());path=PREFIX+'/navigation/'+nav['id']+'/simulation'
        for payload in [{'rate':True},{'rate':3},{'speed_kmh':True},{'speed_kmh':51},{'follow_recommendation':1},{'owner_id':'0'*32}]:
            self.assertEqual(self.request('PATCH',path,{'expected_revision':0,**payload})[0],422)
        self.assertEqual(self.request('PATCH',path,{'expected_revision':1,'rate':1})[0],409)
        self.assertEqual(self.request('PATCH',path,{'expected_revision':0,'rate':1},{'X-CSRF-Token':''})[0],403)
        self.assertEqual(self.request('PATCH',path,{'expected_revision':0,'rate':1},{'Origin':'https://other.test'})[0],403)

    def test_pair_atomic_race_expiry_limits_and_spoof(self):
        self.real_proxy()
        result=self.post('/pairing-challenges',{'label':'Synthetic phone'})[1]['data']
        body={'code':result['code'],'client_device_id':'synthetic-race','label':'Synthetic'}
        ready=threading.Barrier(2)
        def pair():
            ready.wait();return self.request('POST',PREFIX+'/device/pair',body)[0]
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:pair(),range(2)))
        self.assertEqual(sorted(results),[200,403])
        result=self.post('/pairing-challenges',{'label':'Expired'})[1]['data'];self.now+=300000
        self.assertEqual(self.request('POST',PREFIX+'/device/pair',{**body,'code':result['code']})[0],403)
        self.assertEqual(self.request('POST',PREFIX+'/device/pair',{**body,'owner_id':self.users['admin']['id']})[0],422)
        for _ in range(6):status=self.request('POST',PREFIX+'/device/pair',{**body,'code':'999999'})[0]
        self.assertEqual(status,429)

    def test_device_edits_foreign_ids_boot_and_absolute_expiry(self):
        self.real_proxy();device,_=self.pair();did=device['device_id'];header={'Authorization':'Bearer '+device['device_token']}
        for who in ['other','analyst','admin']:
            self.use(who);self.assertEqual(self.request('PATCH',PREFIX+'/devices/'+did,{'label':'Spoof'})[0],404)
        self.use('driver');self.assertEqual(self.request('PATCH',PREFIX+'/devices/'+did,{'label':'New label'})[0],200)
        self.assertEqual(self.get('/devices?status=ACTIVE&limit=1')[0],200)
        self.assertEqual(self.get('/devices?status=invalid')[0],422)
        self.assertEqual(self.request('GET','/api/state',headers=header)[0],200)
        self.assertEqual(self.request('GET','/api/state',headers={'Authorization':''})[0],403)
        oldboot=self.rec.boot;self.rec.boot='f'*32
        self.assertEqual(self.request('GET',PREFIX+'/device/session',headers=header)[0],403)
        self.rec.boot=oldboot;self.now+=28800000
        self.assertEqual(self.request('GET',PREFIX+'/device/session',headers=header)[0],403)

    def test_capture_source_and_private_matrix(self):
        nav=self.start(self.new_trip());path='/trips/'+nav['trip_id']+'/cv/captures'
        for who,status in [(None,401),('other',404),('analyst',404),('admin',404)]:
            self.use(who);self.assertEqual(self.post(path,{'source_type':'FILE','source_ref':'not-configured'})[0],status)
        self.use('driver');self.assertEqual(self.post(path,{'source_type':'FILE','source_ref':'../secret'})[0],422)
        self.assertEqual(self.post(path,{'source_type':'CAMERA','camera_index':0})[0],403)
        self.assertEqual(self.get('/maps/../../school.sqlite3')[0],404)
        self.assertEqual(self.get('/maps/warsaw')[0],200)
        self.use(None);self.assertEqual(self.get('/maps/warsaw')[0],401)


    def test_scoped_capture_frames_stop_range_and_missing_model(self):
        import hashlib,types
        from pathlib import Path
        source=self.storage.root/'synthetic-source.avi';source.write_bytes(b'SYNTHETIC SOURCE')
        vision=self.server.resources.vision;vision.sources={'synthetic':str(source)}
        captured=[]
        class Capture:
            def __init__(inner,root,python=None):
                inner.root=Path(root);inner.python=python;inner.running=True;inner.process=types.SimpleNamespace(poll=lambda:None if inner.running else 0);captured.append(inner)
            def start(inner,**kw):
                inner.id='e'*32;inner.directory=inner.root/inner.id;inner.directory.mkdir(parents=True)
                (inner.directory/'preview-0.jpg').write_bytes(b'SYNTHETIC FRAME')
                media=inner.directory/'video.avi';media.write_bytes(b'SYNTHETIC MEDIA')
                (inner.directory/'manifest.json').write_text(json.dumps({'session_id':inner.id,'run_id':kw['run_id'],'complete':True,'status':'ENDED','artifacts':[{'kind':'VIDEO','filename':'video.avi','sha256':hashlib.sha256(media.read_bytes()).hexdigest()}]}))
                return inner.status()
            def status(inner):return {'session_id':inner.id,'status':'RUNNING' if inner.running else 'ENDED','frame':{'data':{'frame_id':0}},'preview_fresh':True,'frames_captured':1}
            def stop(inner):inner.running=False;return inner.status()
            def close(inner):inner.running=False
        trip=self.new_trip();nav=self.start(trip);base='/trips/'+trip['id']+'/cv/captures'
        self.assertEqual(self.post(base,{'source_type':'FILE','source_ref':'synthetic','detection':True})[0],422)
        with patch('greenwave.school_navigation.cv.CaptureController',Capture):
            status,data,_=self.post(base,{'source_type':'FILE','source_ref':'synthetic','detection':False})
        self.assertEqual(status,201,data);cid=data['data']['id'];path=base+'/'+cid
        for suffix in ['', '/frames/0','/events','/media/0']:
            for who,expected in [(None,401),('other',404),('analyst',404),('admin',404),('driver',200)]:
                self.use(who);self.assertEqual(self.get(path+suffix)[0],expected)
        self.assertEqual(self.request('GET',PREFIX+path+'/media/0',headers={'Range':'bytes=0-3'})[0],206)
        self.assertEqual(self.request('GET',PREFIX+path+'/media/0',headers={'Range':'bytes=9999-'})[0],416)
        self.assertEqual(self.get(path+'/frames/%2e%2e')[0],404)
        self.assertEqual(self.post(path+'/stop',{},)[0],200)
        self.assertFalse(captured[0].running)
        self.assertEqual(self.finish(nav)[0],200)

    def test_simulation_clock_is_separate_and_predictor_does_not_peek(self):
        nav=self.start(self.new_trip());drive=self.rec.contexts[nav['id']]['drive'];clock=drive.app.clock
        clock.set_running(False);clock._monotonic=lambda:100;clock._anchor=100;clock.set_running(True)
        original=drive.app.simulator.state_at;observed=[]
        def state_at(signal,seconds):
            observed.append(seconds);self.assertLessEqual(seconds,clock.read().simulation_seconds+1e-6)
            return original(signal,seconds)
        with patch.object(drive.app.simulator,'state_at',side_effect=state_at):
            drive.app._plan();clock._monotonic=lambda:102;drive.tick()
        self.assertTrue(observed);self.assertGreaterEqual(drive.app.position.elapsed,1.9)
        state=self.get('/navigation/'+nav['id'])[1]['data']
        self.assertEqual(state['response_at'],self.now);self.assertGreaterEqual(state['simulation_seconds'],2)
        self.assertIsNone(state['live_recommendation'])


    def test_repair_does_not_rebind_an_old_active_navigation(self):
        self.real_proxy();device,_=self.pair()
        from greenwave.school_data import Actor
        from pathlib import Path
        cfg=self.repo.create_config(Actor(self.users['admin']['id']),'ROUTE','repair-test',json.loads(Path('data/routes/zwirki_wigury_draft.json').read_text(encoding='utf-8')))
        cfg=self.repo.publish_config(Actor(self.users['admin']['id'],self.now),cfg['id'],cfg['revision'])
        trip=self.post('/trips',{'title':'First credential epoch','mode':'LIVE','route_version_id':cfg['id']})[1]['data']
        nav=self.request('POST',PREFIX+'/navigation',{'trip_id':trip['id'],'device_id':device['device_id']},{'Idempotency-Key':'E'*32})[1]['data']
        replacement,_=self.pair();self.assertEqual(replacement['device_id'],device['device_id'])
        self.assertEqual(self.get('/navigation/'+nav['id'])[0],404)
        self.assertEqual(self.get('/trips/'+trip['id'])[1]['data']['status'],'COMPLETE')
        self.assertEqual(self.request('GET',PREFIX+'/device/session',headers={'Authorization':'Bearer '+device['device_token']})[0],403)
        status,data,_=self.request('GET',PREFIX+'/device/session',headers={'Authorization':'Bearer '+replacement['device_token']})
        self.assertEqual(status,200);self.assertFalse(data['data']['active']);self.assertIsNone(data['data']['app_session_id'])



def load_tests(loader, tests, pattern):
    suite=unittest.TestSuite()
    for name in NavigationTests.__dict__:
        if name.startswith('test_'):suite.addTest(NavigationTests(name))
    return suite
