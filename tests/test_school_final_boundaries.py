"""Risk-based final acceptance: failure boundaries, never private recordings."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from test_school_navigation import NavigationTests

class FinalHTTPTests(NavigationTests):
    def source(self):
        source=self.storage.root/'synthetic.avi';source.write_bytes(b'SYNTHETIC')
        self.server.resources.vision.sources={'synthetic':str(source)}
        nav=self.start(self.new_trip())
        return '/trips/'+nav['trip_id']+'/cv/captures',nav

    def test_cv_bad_capture_parameters_are_form_errors_not_runtime_failure(self):
        route,nav=self.source()
        from greenwave.vision_capture import CaptureController
        for values in [{'width':True},{'width':159},{'height':119},{'fps':61},{'realtime':1}]:
            with self.subTest(values=values),patch('greenwave.school_navigation.cv.CaptureController',wraps=CaptureController) as factory:
                self.assertEqual(self.post(route,{'source_type':'FILE','source_ref':'synthetic',**values})[0],422)
                factory.assert_not_called()
        self.assertEqual(self.finish(nav)[0],200)

    def test_cv_registration_failure_closes_started_controller_without_manifest(self):
        route,nav=self.source();controller=Mock();controller.start.return_value={'session_id':'e'*32}
        with patch('greenwave.school_navigation.cv.CaptureController',return_value=controller),patch('greenwave.vision_workbench.VisionWorkbench',side_effect=OSError('synthetic index unavailable')):
            self.assertEqual(self.post(route,{'source_type':'FILE','source_ref':'synthetic'})[0],503)
        controller.close.assert_called_once()
        self.assertFalse(self.server.resources.vision.captures)
        self.assertEqual(self.finish(nav)[0],200)

    def test_missing_runtime_does_not_occupy_capture_slot_or_stop_navigation(self):
        route,nav=self.source()
        with patch('greenwave.school_navigation.cv.CaptureController') as factory:
            factory.return_value.start.side_effect=ValueError('synthetic launch failure')
            self.assertEqual(self.post(route,{'source_type':'FILE','source_ref':'synthetic'})[0],503)
            factory.return_value.close.assert_called_once()
        self.assertFalse(self.server.resources.vision.captures)
        self.assertEqual(self.get('/navigation/'+nav['id'])[0],200)
        self.assertEqual(self.finish(nav)[0],200)

    def test_protected_map_exact_allowlist_and_missing_oversized_assets(self):
        # Redirect only the map module's bundled root. Actual pathlib.stat/is_file
        # semantics remain intact on Python 3.12 as well as 3.14; no real map changes.
        with tempfile.TemporaryDirectory(prefix='gw-map-fixture-') as temporary:
            root=Path(temporary)
            asset=root/'data'/'maps'/'warsaw.json';asset.parent.mkdir(parents=True)
            module=root/'greenwave'/'school_navigation'/'maps.py'
            def expect(name,status,code):
                actual,body,_=self.get('/maps/'+name)
                self.assertEqual(actual,status,body)
                self.assertEqual(body['error']['code'],code)
            with patch('greenwave.school_navigation.maps.__file__',str(module)):
                expect('not-a-map',404,'NOT_FOUND')
                expect('warsaw',404,'MAP_UNAVAILABLE')
                with asset.open('wb') as stream:stream.truncate(8*1024*1024+1)
                self.assertTrue(asset.is_file())
                self.assertEqual(asset.stat().st_size,8*1024*1024+1)
                expect('warsaw',409,'MAP_TOO_LARGE')



class SupervisorTests(unittest.TestCase):
    def controller(self,temp,status='RUNNING',code=None):
        from greenwave.vision_capture import CaptureController
        controller=CaptureController(temp);controller.directory=Path(temp)/('a'*32);controller.directory.mkdir()
        controller.process=Mock();controller.process.poll.return_value=code
        (controller.directory/'status.json').write_text(json.dumps({'session_id':'a'*32,'status':status}),encoding='utf-8')
        return controller

    def test_abnormal_exit_invalidates_complete_manifest_and_closes_log(self):
        with tempfile.TemporaryDirectory() as temp:
            controller=self.controller(temp,code=3);controller.log=Mock();log=controller.log
            manifest=controller.directory/'manifest.json';manifest.write_text(json.dumps({'complete':True,'status':'ENDED'}),encoding='utf-8')
            state=controller.status();self.assertEqual(state['status'],'FAILED');self.assertFalse(state['live_prediction_eligible'])
            self.assertFalse(json.loads(manifest.read_text())['complete']);log.close.assert_called_once();self.assertIsNone(controller.log)

    def test_stop_watchdog_terminates_stalled_worker_but_not_finalizing(self):
        for status,terminated in [('RUNNING',True),('FINALIZING',False)]:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as temp:
                controller=self.controller(temp,status=status);callbacks=[]
                with patch('greenwave.vision_capture.threading.Timer',side_effect=lambda _,fn:callbacks.append(fn) or Mock()):
                    self.assertEqual(controller.stop()['status'],'STOPPING')
                self.assertTrue((controller.directory/'stop.flag').is_file());callbacks[0]()
                self.assertEqual(controller.process.terminate.called,terminated)

    def test_close_wait_timeout_terminates_and_releases_log(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            controller=self.controller(temp);controller.log=Mock();log=controller.log
            controller.process.wait.side_effect=[subprocess.TimeoutExpired('synthetic',2),0]
            with patch('greenwave.vision_capture.threading.Timer'):
                controller.close()
            controller.process.terminate.assert_called_once();log.close.assert_called_once();self.assertTrue(controller.forced)

    def test_failed_spawn_keeps_diagnostic_files_and_closes_log(self):
        from greenwave.vision_capture import CaptureController
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.avi';source.write_bytes(b'SYNTHETIC')
            controller=CaptureController(Path(temp)/'captures',python='synthetic-missing-python')
            with patch('greenwave.vision_capture.subprocess.Popen',side_effect=OSError('synthetic missing executable')):
                with self.assertRaises(ValueError):controller.start(source_type='FILE',source=str(source))
            self.assertIsNone(controller.log);self.assertIsNone(controller.process)
            files=list((Path(temp)/'captures').glob('*/config.json'));self.assertEqual(len(files),1)
            self.assertFalse(list((Path(temp)/'captures').glob('*/manifest.json')))

    def test_worker_missing_opencv_writes_explicit_failed_status(self):
        from greenwave.vision_capture_worker import run
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'config.json').write_text(json.dumps({'session_id':'a'*32,'source_type':'FILE','source':'synthetic.avi','clock_uncertainty_seconds':1}),encoding='utf-8')
            with patch.dict('sys.modules',{'cv2':None}):self.assertEqual(run(root),1)
            self.assertEqual(json.loads((root/'status.json').read_text())['status'],'FAILED')
            self.assertFalse(json.loads((root/'manifest.json').read_text())['complete'])

    def test_snapshot_corruption_is_rejected_and_frozen_route_cannot_switch(self):
        from greenwave.school_navigation.maps import snapshot_route,BoundRoutes
        from greenwave.school_data import Storage
        from greenwave.school_accounts.errors import AuthError
        with tempfile.TemporaryDirectory() as temp:
            storage=Storage(temp)
            with self.assertRaises(AuthError):snapshot_route(storage,None)
            with self.assertRaises(AuthError):snapshot_route(storage,{'payload':{},'payload_hash':'bad'})
            empty=BoundRoutes(None);self.assertEqual(empty.list(),[])
            with self.assertRaises(ValueError):empty.load('unrelated')


def load_tests(loader,tests,pattern):
    suite=unittest.TestSuite()
    suite.addTests(FinalHTTPTests(name) for name in sorted(FinalHTTPTests.__dict__) if name.startswith('test_'))
    suite.addTests(loader.loadTestsFromTestCase(SupervisorTests))
    return suite
