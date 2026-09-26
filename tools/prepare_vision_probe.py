"""Download pinned public evaluation assets, never into tracked model folders."""
import hashlib
import json
from pathlib import Path
import urllib.request


ROOT=Path(__file__).resolve().parents[1]/'data'/'derived'/'vision-probe'
ASSETS=(
    ('best_traffic_nano_yolo.pt',
     'https://raw.githubusercontent.com/Syazvinski/Traffic-Light-Detection-Color-Classification/c2c5bfcad8bb6f168712426fa071022e3b8832cb/models/best_traffic_nano_yolo.pt',
     '6b7fc4adf8af46500d10666d7c5917b3a98a627353b8aa07bbe4155f04f172bb'),
    ('red-yellow.jpg',
     'https://raw.githubusercontent.com/KASTEL-MobilityLab/traffic-light-detection/ace09cb5d0dca4cb048d078f0f33cf868954e465/inference/inference_images/red-yellow.jpg',
     '986aad5b5c166c39c264b500a76e07fbeebddf809ee7971429432e6d7c383af4'),
)


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,url,expected in ASSETS:
        path=ROOT/name
        if not path.exists():
            partial=path.with_suffix(path.suffix+'.partial')
            with urllib.request.urlopen(url,timeout=30) as response,partial.open('wb') as stream:
                while chunk:=response.read(65536):stream.write(chunk)
            actual=hashlib.sha256(partial.read_bytes()).hexdigest()
            if expected and actual!=expected:raise ValueError('Asset checksum mismatch: '+name)
            partial.replace(path)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected and actual!=expected:raise ValueError('Existing asset checksum mismatch: '+name)
        manifest.append(dict(path=name,url=url,sha256=actual))
    (ROOT/'prepared-assets.json').write_text(json.dumps(dict(files=manifest,
        model_license='No explicit license found in model repository; evaluation candidate, not redistributable production selection',
        sample_repository_license='AGPL-3.0',sample_role='public example, not independent validation'),indent=2)+'\n',encoding='utf-8')
    print(ROOT)


if __name__=='__main__':main()
