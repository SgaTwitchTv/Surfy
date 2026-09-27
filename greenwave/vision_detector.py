"""Optional local CPU adapter. Imports ML only inside the capture worker."""
import os
from pathlib import Path
from greenwave.vision_probe import file_sha256, make_detection, class_semantics


class YoloLampDetector:
    def __init__(self, weights, directory, imgsz=960):
        config_directory=Path(directory)/'.ultralytics'
        config_directory.mkdir(parents=True,exist_ok=True)
        os.environ['YOLO_CONFIG_DIR']=str(config_directory)
        os.environ['YOLO_AUTOINSTALL']='false'
        import torch
        import ultralytics
        from ultralytics import YOLO
        torch.set_num_threads(4)
        ultralytics.settings.update({'sync':False,'hub':False})
        self.model=YOLO(str(weights));self.imgsz=imgsz
        self.hash=file_sha256(weights);self.name=Path(weights).name
        self.metadata=dict(model_id=self.name,sha256=self.hash,classes=self.model.names,
            supported_states=sorted({class_semantics(n)[0] for n in self.model.names.values()}),
            missing_states=sorted({'RED','GREEN','YELLOW','RED_YELLOW','OFF'}-{class_semantics(n)[0] for n in self.model.names.values()}),
            quality_validated=False,device='cpu',imgsz=imgsz,ultralytics=ultralytics.__version__,
            thresholds=dict(detection_score=.25,state_score=.5,min_height=12,min_width=4))

    def detect(self,image,frame):
        result=self.model.predict(image,imgsz=self.imgsz,device='cpu',verbose=False,conf=.25,max_det=100,agnostic_nms=True)[0]
        detections=[]
        for index,box in enumerate(result.boxes if result.boxes is not None else []):
            detections.append(make_detection(frame,box.xyxy[0].tolist(),box.conf.item(),result.names[int(box.cls.item())],self.name,self.hash,index))
        return detections
