"""Versioned vision DTOs. No ML dependency and no live prediction side effects."""
from dataclasses import asdict, dataclass, fields
from datetime import datetime
import json
import math

SCHEMA_VERSION = 1
STATES = {'RED', 'YELLOW', 'GREEN', 'RED_YELLOW', 'OFF', 'UNKNOWN'}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be nonempty text')


def _number(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'{name} outside range')


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')


def _sha256(value, name):
    if not isinstance(value,str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(f'{name} requires a lowercase SHA-256')


class VisionDTO:
    def to_dict(self):
        return dict(schema_version=SCHEMA_VERSION, type=type(self).__name__, data=asdict(self))

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class CameraFrameRef(VisionDTO):
    camera_id: str
    session_id: str
    frame_id: int
    captured_monotonic_ns: int
    captured_utc: str
    clock_uncertainty_seconds: float
    width: int
    height: int
    media_ref: str | None = None
    pts_seconds: float | None = None

    def __post_init__(self):
        _text(self.camera_id, 'camera_id'); _text(self.session_id, 'session_id')
        _integer(self.frame_id, 'frame_id'); _integer(self.captured_monotonic_ns, 'captured_monotonic_ns')
        _integer(self.width, 'width', 1); _integer(self.height, 'height', 1)
        stamp = datetime.fromisoformat(self.captured_utc)
        if stamp.utcoffset() is None:
            raise ValueError('captured_utc requires timezone')
        _number(self.clock_uncertainty_seconds, 'clock_uncertainty_seconds')
        if self.pts_seconds is not None: _number(self.pts_seconds, 'pts_seconds')
        if self.media_ref is not None: _text(self.media_ref, 'media_ref')


@dataclass(frozen=True)
class VisionDetection(VisionDTO):
    detection_id: str
    frame: CameraFrameRef
    bbox_xyxy: tuple[float, float, float, float]
    state: str
    model_score: float
    model_id: str
    model_sha256: str
    pictogram: str = 'UNKNOWN'
    flashing: str = 'UNKNOWN'
    track_id: str | None = None

    def __post_init__(self):
        _text(self.detection_id, 'detection_id'); _text(self.model_id, 'model_id')
        if self.track_id is not None: _text(self.track_id,'track_id')
        if not isinstance(self.frame, CameraFrameRef): raise ValueError('frame requires CameraFrameRef')
        if self.state not in STATES: raise ValueError('Invalid signal state')
        if self.pictogram not in {'UNKNOWN','CIRCLE','ARROW_LEFT','ARROW_RIGHT','ARROW_STRAIGHT','PEDESTRIAN'}:
            raise ValueError('Invalid pictogram')
        if self.flashing not in {'UNKNOWN','YES','NO'}: raise ValueError('Invalid flashing')
        _number(self.model_score, 'model_score', maximum=1)
        _sha256(self.model_sha256,'model_sha256')
        if not isinstance(self.bbox_xyxy, tuple) or len(self.bbox_xyxy) != 4:
            raise ValueError('bbox must be a four-value tuple in original frame pixels')
        x1,y1,x2,y2 = self.bbox_xyxy
        for value in self.bbox_xyxy: _number(value, 'bbox')
        if not (x1 < x2 <= self.frame.width and y1 < y2 <= self.frame.height):
            raise ValueError('bbox outside original frame or empty')


@dataclass(frozen=True)
class VisionTrack(VisionDTO):
    track_id: str
    first: VisionDetection
    latest: VisionDetection
    visibility: str = 'VISIBLE'

    def __post_init__(self):
        _text(self.track_id, 'track_id')
        if not isinstance(self.first, VisionDetection) or not isinstance(self.latest, VisionDetection):
            raise ValueError('track requires detections')
        _ordered_frames(self.first.frame, self.latest.frame, allow_equal=True)
        if any(d.track_id != self.track_id for d in (self.first,self.latest)):
            raise ValueError('Track detections require matching track identity')
        if self.visibility not in {'VISIBLE','OCCLUDED','LOST'}: raise ValueError('Invalid visibility')


@dataclass(frozen=True)
class SignalAssociation(VisionDTO):
    session_id: str
    track_id: str
    status: str
    method: str
    route_id: str | None = None
    geometry_hash: str | None = None
    stop_line_id: str | None = None
    direction: str | None = None
    movement: str | None = None
    display_name: str | None = None
    stop_line_latitude: float | None = None
    stop_line_longitude: float | None = None
    candidate_line_ids: tuple[str, ...] = ()

    def __post_init__(self):
        _text(self.session_id, 'session_id'); _text(self.track_id, 'track_id')
        if self.status not in {'UNASSIGNED','CANDIDATE','CONFIRMED','AMBIGUOUS','CONFLICT'}:
            raise ValueError('Invalid association status')
        if self.method not in {'NONE','MANUAL','GPS_PROPOSAL','GEOMETRY_PROPOSAL'}:
            raise ValueError('Invalid association method')
        for name in ('route_id','geometry_hash','stop_line_id','direction','movement','display_name'):
            value = getattr(self,name)
            if value is not None: _text(value,name)
        if self.geometry_hash is not None: _sha256(self.geometry_hash,'geometry_hash')
        if not isinstance(self.candidate_line_ids, tuple): raise ValueError('candidates require tuple')
        for value in self.candidate_line_ids: _text(value,'candidate')
        if self.status == 'CONFIRMED':
            if self.method != 'MANUAL': raise ValueError('Automatic proposals cannot confirm association in v1')
            if not all((self.route_id,self.geometry_hash,self.stop_line_id,self.direction,self.movement)):
                raise ValueError('Confirmed association requires directional route identity')
        if self.direction is not None and self.direction not in {'FORWARD','REVERSE'}:
            raise ValueError('Invalid direction')
        if (self.stop_line_latitude is None) != (self.stop_line_longitude is None):
            raise ValueError('Coordinates require both latitude and longitude')
        if self.stop_line_latitude is not None:
            _number(self.stop_line_latitude,'latitude',-90,90)
            _number(self.stop_line_longitude,'longitude',-180,180)


def _ordered_frames(first, last, allow_equal=False):
    if (first.camera_id,first.session_id) != (last.camera_id,last.session_id):
        raise ValueError('Frames must share camera/session')
    if first.frame_id > last.frame_id or first.captured_monotonic_ns > last.captured_monotonic_ns:
        raise ValueError('Frames must be ordered')
    if not allow_equal and (first.frame_id == last.frame_id or first.captured_monotonic_ns == last.captured_monotonic_ns):
        raise ValueError('Transition needs distinct ordered frames')


@dataclass(frozen=True)
class VisionObservation(VisionDTO):
    observation_id: str
    detection: VisionDetection
    association: SignalAssociation
    event_type: str = 'STATE_SEEN'
    previous_detection: VisionDetection | None = None
    continuity_confirmed: bool = False
    review_status: str = 'PENDING'
    reviewer: str | None = None

    def __post_init__(self):
        _text(self.observation_id,'observation_id')
        if not isinstance(self.detection,VisionDetection) or not isinstance(self.association,SignalAssociation):
            raise ValueError('Observation requires detection and association')
        if self.detection.frame.session_id != self.association.session_id:
            raise ValueError('Association session mismatch')
        if self.detection.track_id != self.association.track_id:
            raise ValueError('Observation track mismatch')
        if type(self.continuity_confirmed) is not bool: raise ValueError('continuity_confirmed requires boolean')
        if self.event_type not in {'STATE_SEEN','STATE_START'}: raise ValueError('Invalid event type')
        if self.review_status not in {'PENDING','ACCEPTED','REJECTED'}: raise ValueError('Invalid review status')
        if self.review_status != 'PENDING': _text(self.reviewer,'reviewer')
        if self.review_status == 'ACCEPTED' and self.association.status != 'CONFIRMED':
            raise ValueError('Accepting a point observation requires confirmed association')
        if self.event_type == 'STATE_START':
            if not isinstance(self.previous_detection,VisionDetection) or not self.continuity_confirmed:
                raise ValueError('Phase start requires continuous previous-state evidence')
            _ordered_frames(self.previous_detection.frame,self.detection.frame)
            if self.previous_detection.track_id != self.association.track_id:
                raise ValueError('Transition evidence must belong to the same track')
            if (self.previous_detection.model_id,self.previous_detection.model_sha256) != (self.detection.model_id,self.detection.model_sha256):
                raise ValueError('Transition evidence must use the same model version')
            if (self.previous_detection.state in {'UNKNOWN','OFF'} or self.detection.state in {'UNKNOWN','OFF'}
                    or self.previous_detection.state == self.detection.state):
                raise ValueError('Phase start requires distinct known active states')

    @property
    def live_prediction_eligible(self):
        return False

    @property
    def transition_monotonic_interval_ns(self):
        if self.event_type != 'STATE_START': return None
        return (self.previous_detection.frame.captured_monotonic_ns,
                self.detection.frame.captured_monotonic_ns)


_TYPES = {cls.__name__: cls for cls in (CameraFrameRef,VisionDetection,VisionTrack,SignalAssociation,VisionObservation)}
_NESTED = {VisionDetection:{'frame':CameraFrameRef}, VisionTrack:{'first':VisionDetection,'latest':VisionDetection},
           VisionObservation:{'detection':VisionDetection,'association':SignalAssociation,'previous_detection':VisionDetection}}


def _decode(cls, data):
    if not isinstance(data,dict) or set(data)-{f.name for f in fields(cls)}:
        raise ValueError('Invalid DTO fields')
    values=dict(data)
    for name,nested in _NESTED.get(cls,{}).items():
        if values.get(name) is not None: values[name]=_decode(nested,values[name])
    for name in ('bbox_xyxy','candidate_line_ids'):
        if name in values and isinstance(values[name],list): values[name]=tuple(values[name])
    try: return cls(**values)
    except TypeError as error: raise ValueError(str(error)) from error


def decode_vision(value):
    if isinstance(value,str): value=json.loads(value)
    if not isinstance(value,dict) or set(value) != {'schema_version','type','data'}:
        raise ValueError('Invalid vision envelope')
    if type(value['schema_version']) is not int or value['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Unsupported vision schema')
    cls=_TYPES.get(value['type'])
    if cls is None: raise ValueError('Unknown vision DTO')
    return _decode(cls,value['data'])
