"""Real local YOLO pipeline smoke; repeated-still clip is not road validation."""
import json
from pathlib import Path
import tempfile
import time
from greenwave.vision_capture import CaptureController,read_json
from greenwave.vision_capture_worker import sha256

source=Path('data/derived/vision-probe/decoder-smoke.avi').resolve()
with tempfile.TemporaryDirectory() as root:
    controller=CaptureController(root)
    try:
        controller.start(source_type='FILE',source=str(source),realtime=False,detection=True)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            status=controller.status()
            if status['status'] in ('ENDED','FAILED'):break
            time.sleep(.1)
        assert status['status']=='ENDED',(status,(controller.directory/'worker.log').read_text(errors='replace'))
        manifest=read_json(controller.directory/'manifest.json')
        rows=[json.loads(line) for line in (controller.directory/'vision.jsonl').read_text().splitlines()]
        assert manifest['complete'] and manifest['analysis_mode']=='ALL_FRAMES'
        assert len(rows)==manifest['frames_captured']==manifest['frames_analyzed']
        assert len(rows)>0 and any(row['detections'] for row in rows)
        assert all(not row['live_prediction_eligible'] for row in rows)
        assert all(not track['assigned'] for row in rows for track in row['tracks'])
        assert all(event['observation']['data']['event_type']!='STATE_START' for row in rows for event in row['events'])
        assert all(sha256(controller.directory/a['filename'])==a['sha256'] for a in manifest['artifacts'])
        print('PASS: actual YOLO,',len(rows),'frames, media clock, tracker, events and hashes; road quality unvalidated')
    finally:controller.close()
