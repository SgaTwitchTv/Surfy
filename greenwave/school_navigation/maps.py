"""Only bundled allowlisted maps and immutable authorized route snapshots."""
import json
from pathlib import Path
from greenwave.route_geometry import load_route
from greenwave.school_accounts.errors import AuthError
from greenwave.school_data.validation import request_hash


def snapshot_route(storage, snapshot):
    if snapshot is None:raise AuthError(422,'ROUTE_REQUIRED')
    if request_hash(snapshot['payload'])!=snapshot['payload_hash']:raise AuthError(409,'CONFIG_INVALID')
    root=storage.config(snapshot['version_id']);root.mkdir(parents=True,exist_ok=True)
    target=storage._safe(root/'route.json')
    if not target.exists():
        try:
            with target.open('x',encoding='utf-8') as out:json.dump(snapshot['payload'],out)
        except FileExistsError:pass
    if request_hash(json.loads(target.read_text(encoding='utf-8')))!=snapshot['payload_hash']:raise AuthError(409,'CONFIG_INVALID')
    return load_route(target)


def bundled_map(policy,raw,name):
    policy.session(raw)
    assets={name:name+'.json' for name in ('warsaw','radom','chomiczowka','arkadia')}
    if name not in assets:raise AuthError(404,'NOT_FOUND')
    path=Path(__file__).resolve().parents[2]/'data'/'maps'/assets[name]
    if not path.is_file():raise AuthError(404,'MAP_UNAVAILABLE')
    if path.stat().st_size>8*1024*1024:raise AuthError(409,'MAP_TOO_LARGE')
    return json.loads(path.read_text(encoding='utf-8'))


class BoundRoutes:
    """A frozen, DB-authorized route; workbench cannot choose another filesystem source."""
    def __init__(self,route):self.route=route
    def load(self,rid):
        if self.route is None or self.route.route_id!=rid:raise ValueError('Route unavailable')
        return self.route
    def list(self):return [] if self.route is None else [self.route.public_dict()]
