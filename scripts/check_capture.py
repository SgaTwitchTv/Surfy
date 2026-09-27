"""Run with .venv-cv Python: actual decoder, subprocess, stop/replay/checksum tests."""
import json
from pathlib import Path
import tempfile
import time
import cv2
import numpy as np
from greenwave.vision_capture import CaptureController, read_json
from greenwave.vision_capture_worker import sha256


def await_status(controller, wanted):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        status=controller.status()
        if status['status'] in wanted:return status
        if status['status']=='FAILED':raise AssertionError(status)
        time.sleep(.05)
    raise AssertionError(controller.status())


with tempfile.TemporaryDirectory() as temp:
    source=Path(temp)/'source.avi'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),10,(320,240))
    assert writer.isOpened()
    for i in range(40):writer.write(np.full((240,320,3),i*5,dtype=np.uint8))
    writer.release()
    controller=CaptureController(Path(temp)/'captures')
    try:
        controller.start(source_type='FILE',source=str(source),realtime=False)
        await_status(controller,{'ENDED'})
        original=controller.directory
        manifest=read_json(original/'manifest.json')
        rows=[json.loads(line) for line in (original/'frames.jsonl').read_text().splitlines()]
        assert manifest['complete'] and len(rows)==40
        assert [row['frame']['data']['frame_id'] for row in rows]==list(range(40))
        assert all(not row['synchronization_verified'] for row in rows)
        assert all(sha256(original/a['filename'])==a['sha256'] for a in manifest['artifacts'])
        assert len(list(original.glob('preview-*.jpg')))<=32
        replay,checksum=controller.replay_source(original.name)
        controller.start(source_type='FILE',source=replay,expected_source_sha256=checksum,replay_of=original.name)
        await_status(controller,{'RUNNING'})
        with __import__('unittest').TestCase().assertRaises(ValueError):controller.start(source_type='CAMERA',source=0)
        controller.stop();await_status(controller,{'STOPPED'})
        assert read_json(controller.directory/'manifest.json')['complete']
        controller.start(source_type='FILE',source=replay,expected_source_sha256=checksum,realtime=False,seek_seconds=1)
        await_status(controller,{'ENDED'})
        sought=[json.loads(line) for line in (controller.directory/'frames.jsonl').read_text().splitlines()]
        assert len(sought)==30 and sought[0]['encoded_frame_index']==10
        assert sought[0]['frame']['data']['pts_seconds']>=.99
        Path(replay).write_bytes(b'corrupted')
        controller.start(source_type='FILE',source=replay,expected_source_sha256=checksum)
        deadline=time.monotonic()+10
        while controller.status()['status']!='FAILED' and time.monotonic()<deadline:time.sleep(.05)
        assert controller.status()['status']=='FAILED'
        assert not read_json(controller.directory/'manifest.json')['complete']
        print('PASS: 40 frames, artifact hashes, bounded preview, replay, positive seek, stop and corrupted-source rejection')
    finally:controller.close()
