"""Generate operator-controlled synthetic CV material, outside Git and legacy storage."""
import argparse,json
from greenwave.school_data import Storage


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--confirm-synthetic',action='store_true');args=parser.parse_args()
    if not args.confirm_synthetic:parser.error('Explicit synthetic confirmation required')
    storage=Storage(args.root);storage.prepare();directory=storage._safe(storage.root/'operator');directory.mkdir(exist_ok=True)
    source=storage._safe(directory/'synthetic.avi');config=storage._safe(directory/'cv-sources.json')
    if source.exists() or config.exists():parser.error('Refusing to overwrite existing operator files')
    import cv2,numpy as np
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),20,(320,240))
    if not writer.isOpened():raise RuntimeError('Synthetic encoder unavailable')
    try:
        for index in range(600):
            image=np.zeros((240,320,3),dtype=np.uint8)
            cv2.circle(image,(160,85),22,(0,0,255) if index%200<100 else (0,255,0),-1);writer.write(image)
    finally:writer.release()
    with config.open('x',encoding='utf-8') as stream:json.dump({'synthetic-clip':str(source)},stream)
    print('Synthetic clip and operator/cv-sources.json created. No camera, GPS or detector used.')


if __name__=='__main__':main()
