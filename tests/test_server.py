import http.client
import json
import threading
import time
import unittest

from greenwave.server import LocalServer


class ServerTests(unittest.TestCase):
    def test_observation_history_requires_auth_and_sync_requires_session(self):
        from unittest.mock import patch
        self.assertEqual(self.request('GET','/api/observation-history')[0],403)
        self.assertEqual(self.request('GET','/api/observation-history/completeness')[0],403)
        headers={'X-GreenWave-Token':self.server.token}
        with patch.object(self.server.observation_history,'read',return_value={'points':[]}) as read:
            status,payload=self.request('GET','/api/observation-history?route_id=north',headers=headers)
            self.assertEqual(status,200);read.assert_called_once_with('north')
        with patch.object(self.server.observation_history,'completeness',return_value={'points':[]}) as report:
            status,_=self.request('GET','/api/observation-history/completeness?route_id=north',headers=headers)
            self.assertEqual(status,200);report.assert_called_once_with('north')
        self.assertEqual(self.request('POST','/api/observation-history/sync',{},headers)[0],409)
        with patch.object(self.server.observation_history,'sync',return_value={'observation_count':18}) as sync:
            status,payload=self.request('POST','/api/observation-history/sync',
                {'session_id':self.server.application.session_id},headers)
            self.assertEqual(status,200);sync.assert_called_once()

    def test_phone_transmission_and_status(self):
        from unittest.mock import patch
        headers={'X-GreenWave-Token':self.server.token}
        body=dict(session_id=self.server.application.session_id,timestamp_seconds=12,
                  latitude=52.2,longitude=20.9,speed_mps=None,gps_accuracy_m=4)
        status,payload=self.request('POST','/api/position',body,headers)
        self.assertEqual(status,200)
        result=json.loads(payload)
        self.assertIsNone(result['external_position']['speed_mps'])
        self.assertEqual(result['external_status']['received_count'],1)
        provider=self.server.application.external_position
        with patch('greenwave.positioning.time.monotonic',return_value=provider.received_at+6):
            self.assertEqual(provider.status()['state'],'STALE')

    def test_android_pairs_and_duplicate_retry_is_acknowledged(self):
        status,payload=self.request('POST','/api/pair',{'code':self.server.pairing_code},
                                    {'Content-Type':'application/json'})
        self.assertEqual(status,200)
        paired=json.loads(payload)
        self.assertEqual(paired['token'],self.server.token)
        body=dict(session_id=paired['session_id'],timestamp_seconds=12,
                  latitude=52.2,longitude=20.9,speed_mps=3,gps_accuracy_m=4,
                  source='ANDROID_FUSED',device_id='phone-1',stream_id='drive-1',
                  sample_sequence=1,elapsed_realtime_nanos=123,is_mock=False)
        headers={'X-GreenWave-Token':paired['token'],'Content-Type':'application/json'}
        first=json.loads(self.request('POST','/api/position',body,headers)[1])
        second=json.loads(self.request('POST','/api/position',body,headers)[1])
        self.assertTrue(first['accepted'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(second['external_status']['received_count'],1)
        self.assertEqual(second['external_status']['transmission_count'],2)

    def test_pairing_rejects_wrong_code_and_locks_after_five_attempts(self):
        for _ in range(4):
            self.assertEqual(self.request('POST','/api/pair',{'code':'wrong'})[0],403)
        self.assertEqual(self.request('POST','/api/pair',{'code':'wrong'})[0],429)
        self.assertEqual(self.request('POST','/api/pair',{'code':self.server.pairing_code})[0],429)

    def setUp(self):
        try:
            self.server=LocalServer(0)
        except PermissionError as error:
            self.skipTest(f'Loopback unavailable: {error}')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self,method,path,body=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        data=None if body is None else json.dumps(body)
        connection.request(method,path,body=data,headers=headers or {})
        response=connection.getresponse()
        status,payload=response.status,response.read()
        connection.close()
        return status,payload

    def test_vision_ui_demos_are_read_only_and_independent_of_session(self):
        before=self.server.application.snapshot()
        status,payload=self.request('GET','/api/vision-demos')
        demos=json.loads(payload)
        self.assertEqual(status,200)
        self.assertEqual(len(demos),9)
        self.assertTrue(all(item['synthetic'] and not item['live_prediction_eligible'] for item in demos))
        after=self.server.application.snapshot()
        self.assertEqual(before['session_id'],after['session_id'])
        self.assertEqual(before['model_version'],after['model_version'])
        self.assertEqual(before['history_total'],after['history_total'])
        self.assertEqual(self.request('GET','/driver-ui.js')[0],200)

    def test_local_ui_and_observation_api(self):
        status,html=self.request('GET','/')
        self.assertEqual(status,200)
        self.assertIn(self.server.token.encode(),html)
        status,payload=self.request('GET','/api/state')
        state=json.loads(payload)
        headers={'X-GreenWave-Token':self.server.token,'Content-Type':'application/json'}
        status,payload=self.request('POST','/api/observe',dict(session_id=state['session_id'],signal_id='S3',state='GREEN',event_type='STATE_START'),headers)
        self.assertEqual(status,200)
        result=json.loads(payload)
        self.assertEqual(result['model_version'],1)
        self.assertEqual(result['last_change']['signal_ids'],['S3'])
        self.assertEqual(result['history_total'],1)

    def test_radom_map_and_route_observation_api(self):
        status, payload = self.request('GET', '/map-data/radom.json')
        self.assertEqual(status, 200)
        self.assertIn(b'OpenStreetMap contributors', payload)
        app = self.server.application
        headers = {'X-GreenWave-Token': self.server.token, 'Content-Type': 'application/json'}
        common = {'session_id': app.session_id}
        select = {**common, 'route_id': 'radom_limanowskiego_25_czerwca_draft'}
        self.assertEqual(self.request('POST', '/api/mapping/select', select, headers)[0], 200)
        line_id = app.selected_route.stop_lines[0].stop_line_id
        body = {**common, 'stop_line_id': line_id, 'state': 'RED', 'event_type': 'STATE_SEEN'}
        self.assertEqual(self.request('POST', '/api/observe-route', body, headers)[0], 400)
        self.assertEqual(self.request('POST', '/api/view', {**common, 'mode': 'LIVE'}, headers)[0], 200)
        status, payload = self.request('POST', '/api/observe-route', body, headers)
        self.assertEqual(status, 200)
        saved = json.loads(payload)['mapping']['route_observations'][-1]
        self.assertEqual(saved['stop_line_id'], line_id)
        self.assertEqual(saved['state'], 'RED')
        self.assertEqual(saved['event_type'], 'STATE_SEEN')
        self.assertEqual(self.request('POST', '/api/observe-route', {**body, 'stop_line_id': 'S1'}, headers)[0], 400)

    def test_unauthorized_cross_origin_and_old_sessions_are_rejected(self):
        app=self.server.application
        data=dict(session_id=app.session_id,running=True)
        self.assertEqual(self.request('POST','/api/control',data)[0],403)
        headers={'X-GreenWave-Token':self.server.token,'Origin':'https://example.com'}
        self.assertEqual(self.request('POST','/api/control',data,headers)[0],403)
        headers.pop('Origin')
        app.reset()
        self.assertEqual(self.request('POST','/api/control',data,headers)[0],409)
        self.assertFalse(app.clock.running)

    def test_paths_and_malformed_input(self):
        for path in ('/../README.md','/data/corridors/zwirki_wigury.json','/not-found'):
            self.assertEqual(self.request('GET',path)[0],404)
        self.assertEqual(self.request('GET','/api/state',headers={'Host':'evil.example'})[0],403)
        headers={'X-GreenWave-Token':self.server.token}
        self.assertEqual(self.request('POST','/api/control',[],headers)[0],400)
        status,_=self.request('POST','/api/control',dict(session_id=self.server.application.session_id,rate=99),headers)
        self.assertEqual(status,400)

    def test_recording_endpoint_lists_and_exports_completed_run(self):
        app=self.server.application
        headers={'X-GreenWave-Token':self.server.token,'Content-Type':'application/json'}
        state=json.loads(self.request('GET','/api/state')[1])
        status,_=self.request('POST','/api/recording',dict(session_id=state['session_id'],command='start'),headers)
        self.assertEqual(status,200)
        state=json.loads(self.request('GET','/api/state')[1])
        self.assertTrue(state['recording']['active'])
        status,_=self.request('POST','/api/recording',dict(session_id=state['session_id'],command='stop'),headers)
        self.assertEqual(status,200)
        runs=json.loads(self.request('GET','/api/runs')[1])
        self.assertEqual(runs[0]['status'],'COMPLETED')
        status,payload=self.request('GET','/api/runs/'+runs[0]['run_id']+'.zip',headers={'X-GreenWave-Token':self.server.token})
        self.assertEqual(status,200); self.assertTrue(payload.startswith(b'PK'))

    def test_replay_state_endpoint_is_available(self):
        status,payload=self.request('GET','/api/replay/state')
        self.assertEqual(status,200)
        self.assertFalse(json.loads(payload)['loaded'])

    def test_mapping_routes_view_and_gps_replay_endpoints(self):
        routes=json.loads(self.request('GET','/api/routes')[1])
        self.assertTrue(any(route['route_id']=='zwirki_wigury_draft' for route in routes))
        arkadia=next(route for route in routes if route['route_id']=='arkadia_maczka_okopowa_v1')
        self.assertEqual(arkadia['geometry_verification']['status'],'DESK_CHECKED')
        self.assertEqual(arkadia['stop_line_count'],10)
        status,payload=self.request('GET','/map-data/arkadia.json')
        self.assertEqual(status,200)
        self.assertIn(b'OpenStreetMap contributors',payload)
        state=json.loads(self.request('GET','/api/state')[1])
        headers={'X-GreenWave-Token':self.server.token,'Content-Type':'application/json'}
        status,payload=self.request('POST','/api/mapping/select',
            dict(session_id=state['session_id'],route_id='zwirki_wigury_draft'),headers)
        self.assertEqual(status,200)
        selected=json.loads(payload)
        self.assertEqual(selected['mapping']['selected_route']['route_id'],'zwirki_wigury_draft')
        status,payload=self.request('POST','/api/view',
            dict(session_id=state['session_id'],mode='LIVE'),headers)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(payload)['view_mode'],'LIVE')
        self.assertEqual(self.request('GET','/api/gps-replay/state')[0],200)
        self.assertEqual(self.request('POST','/api/mapping/select',
            dict(session_id=state['session_id'],route_id='../bad'),headers)[0],400)

    def test_mapping_analysis_is_an_authenticated_background_job(self):
        state=json.loads(self.request('GET','/api/state')[1])
        headers={'X-GreenWave-Token':self.server.token,'Content-Type':'application/json'}
        session=state['session_id']
        self.assertEqual(self.request('POST','/api/recording',
            dict(session_id=session,command='start'),headers)[0],200)
        self.assertEqual(self.request('POST','/api/position',dict(session_id=session,
            timestamp_seconds=100,latitude=52.2,longitude=20.9,speed_mps=0,
            gps_accuracy_m=4),headers)[0],200)
        self.assertEqual(self.request('POST','/api/recording',
            dict(session_id=session,command='stop'),headers)[0],200)
        run_id=json.loads(self.request('GET','/api/runs')[1])[0]['run_id']
        status,payload=self.request('POST','/api/mapping/analyze',
            dict(session_id=session,run_id=run_id,write=False),headers)
        self.assertEqual(status,202)
        job=json.loads(payload)
        job_path='/api/mapping/jobs/'+job['job_id']
        self.assertEqual(self.request('GET',job_path)[0],403)
        deadline=time.monotonic()+2
        while job['status']=='RUNNING' and time.monotonic()<deadline:
            time.sleep(.01)
            job=json.loads(self.request('GET',job_path,headers={'X-GreenWave-Token':self.server.token})[1])
        self.assertEqual(job['status'],'COMPLETED')
        self.assertEqual(job['result']['sample_count'],1)
