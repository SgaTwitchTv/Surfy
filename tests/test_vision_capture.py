import json
from pathlib import Path
from queue import Queue
import tempfile
import unittest

from greenwave.vision_capture import CaptureController, validate_source
from greenwave.vision_capture_worker import offer_latest, atomic_json, sha256


class CaptureTests(unittest.TestCase):
    def test_atomic_status_recovers_from_transient_windows_file_lock(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'status.json';original=Path.replace;attempts=[]
            def replace(source,target):
                attempts.append(source)
                if len(attempts)==1:raise PermissionError('temporary reader lock')
                return original(source,target)
            with patch.object(Path,'replace',replace):atomic_json(path,dict(status='RUNNING'))
            self.assertEqual(json.loads(path.read_text())['status'],'RUNNING')
            self.assertEqual(len(attempts),2)

    def test_latest_queue_is_bounded_and_replaces_old_frame(self):
        queue=Queue(maxsize=1)
        self.assertEqual(offer_latest(queue,'old'),0)
        self.assertEqual(offer_latest(queue,'new'),1)
        self.assertEqual(queue.qsize(),1)
        self.assertEqual(queue.get(),'new')

    def test_source_validation_rejects_network_and_invalid_camera(self):
        for value in (-1,17,True,'0'):
            with self.assertRaises(ValueError):validate_source('CAMERA',value)
        self.assertEqual(validate_source('CAMERA',0),0)
        with self.assertRaises(ValueError):validate_source('FILE','https://example.org/video.mp4')

    def test_replay_requires_complete_manifest_and_contained_path(self):
        with tempfile.TemporaryDirectory() as temp:
            controller=CaptureController(temp);session='a'*32;directory=Path(temp)/session;directory.mkdir()
            video=directory/'video.avi';video.write_bytes(b'video')
            manifest=dict(complete=False,artifacts=[dict(kind='VIDEO',filename='video.avi',sha256=sha256(video))])
            atomic_json(directory/'manifest.json',manifest)
            with self.assertRaises(ValueError):controller.replay_source(session)
            manifest['complete']=True;atomic_json(directory/'manifest.json',manifest)
            self.assertEqual(controller.replay_source(session),(str(video),sha256(video)))
            manifest['artifacts'][0]['filename']='../escape.avi';atomic_json(directory/'manifest.json',manifest)
            with self.assertRaises(ValueError):controller.replay_source(session)

    def test_idle_never_eligible_and_preview_rejects_unknown_session(self):
        with tempfile.TemporaryDirectory() as temp:
            controller=CaptureController(temp)
            self.assertFalse(controller.status()['live_prediction_eligible'])
            with self.assertRaises(ValueError):controller.preview('wrong',0)
            controller.close()

    def test_camera_reconnect_starts_new_segment_and_keeps_all_frame_refs(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from greenwave.vision_capture_worker import run
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);opens=[]
            class Capture:
                def __init__(self,*args):self.index=len(opens);opens.append(self);self.count=0
                def isOpened(self):return True
                def set(self,*args):pass
                def get(self,*args):return 10
                def read(self):
                    self.count+=1
                    if self.count>2:return False,None
                    if self.index==1 and self.count==2:(directory/'stop.flag').touch()
                    return True,SimpleNamespace(shape=(240,320,3))
                def release(self):pass
            class Writer:
                def __init__(self,path,*args):self.path=Path(path);self.path.write_bytes(b'')
                def isOpened(self):return True
                def write(self,image):
                    with self.path.open('ab') as stream:stream.write(b'frame')
                def release(self):pass
            fake=SimpleNamespace(VideoCapture=Capture,VideoWriter=Writer,VideoWriter_fourcc=lambda *args:0,
                CAP_DSHOW=0,CAP_PROP_FRAME_WIDTH=1,CAP_PROP_FRAME_HEIGHT=2,CAP_PROP_FPS=3,IMWRITE_JPEG_QUALITY=4,
                imencode=lambda *args:(True,SimpleNamespace(tobytes=lambda:b'jpeg')))
            atomic_json(directory/'config.json',dict(session_id='a'*32,source_type='CAMERA',source=0,width=320,height=240,fps=10,realtime=True,clock_uncertainty_seconds=1))
            with patch.dict('sys.modules',{'cv2':fake}):self.assertEqual(run(directory),0)
            manifest=json.loads((directory/'manifest.json').read_text())
            rows=[json.loads(row) for row in (directory/'frames.jsonl').read_text().splitlines()]
            self.assertTrue(manifest['complete']);self.assertEqual(manifest['reconnects'],1)
            self.assertEqual([row['segment'] for row in rows],[0,0,1,1])
            self.assertNotEqual(rows[0]['frame']['data']['session_id'],rows[2]['frame']['data']['session_id'])
            self.assertEqual([row['encoded_frame_index'] for row in rows],[0,1,0,1])
